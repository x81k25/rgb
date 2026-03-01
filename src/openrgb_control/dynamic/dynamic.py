"""Dynamic RGB effects using OpenRGB socket protocol.

Effects are implemented as stateful classes with a step() method that computes
one animation frame. Animation speed is driven by wall-clock time via
cycle_duration (seconds per full cycle), fully decoupled from frame rate.

Performance notes:
- Use device.set_colors(list, fast=True) for per-LED batch updates (1 packet)
- Use device.set_color(color, fast=True) for uniform color (1 packet)
- Never loop device.leds[i].set_color() — that's 1 packet per LED
- fast=True skips expensive state refresh round-trip
"""

import math
import random
import time
from typing import List, Optional

from ..core import LEDStateTracker, get_client, hex_to_rgb
from ..monitoring import get_memory_usage, get_cpu_usage
from ..config import (
    SERVER_HOST,
    SERVER_PORT,
    STATUS_GRADIENT_HEX,
    HIGH_CONTRAST_COLORS,
    RAM_DEVICE_INDICES,
    CPU_DEVICE_INDICES,
    MEMORY_DEVICE_INDICES,
    MOTHERBOARD_DEVICE_INDEX,
    MOTHERBOARD_VISIBLE_LEDS,
    LEDS_PER_RAM_STICK,
    DEFAULT_BREATHING_DURATION,
    DEFAULT_UPDATE_INTERVAL,
    CPU_SAMPLE_INTERVAL,
)

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
except ImportError:
    OpenRGBClient = None
    RGBColor = None


def _get_client():
    """Get shared OpenRGB client."""
    return get_client()


def _precompute_gradient() -> List:
    """Pre-compute status gradient as RGBColor objects."""
    return [RGBColor(*hex_to_rgb(c)) for c in STATUS_GRADIENT_HEX]


def _usage_to_leds(percent: float, max_leds: int = LEDS_PER_RAM_STICK) -> int:
    """Convert usage percentage to number of LEDs to light."""
    if percent <= 0:
        return 0
    return min(int((percent / 100.0) * max_leds) + 1, max_leds)


def _build_gradient_colors(num_leds: int, leds_to_light: int, gradient: List, black: 'RGBColor') -> List:
    """Build a list of colors for gradient pattern (bottom-up LEDs based on usage)."""
    colors = []
    for led_idx in range(num_leds):
        bottom_up_idx = num_leds - 1 - led_idx
        if bottom_up_idx < leds_to_light:
            grad_idx = int(bottom_up_idx * (len(gradient) - 1) / (num_leds - 1))
            colors.append(gradient[grad_idx])
        else:
            colors.append(black)
    return colors


def _apply_gradient_to_device(device, device_index: int, leds_to_light: int, gradient: List, black: 'RGBColor'):
    """Apply gradient pattern to a device using batch update."""
    tracker = LEDStateTracker()
    num_leds = len(device.leds)
    colors = _build_gradient_colors(num_leds, leds_to_light, gradient, black)

    device.set_colors(colors, fast=True)

    for led_idx, color in enumerate(colors):
        tracker.set_led(device_index, led_idx, color.red, color.green, color.blue)


def _get_motherboard(client):
    """Get the motherboard device if available."""
    if MOTHERBOARD_DEVICE_INDEX < len(client.devices):
        return client.devices[MOTHERBOARD_DEVICE_INDEX]
    return None


def _set_motherboard_color(client, r: int, g: int, b: int):
    """Set motherboard LEDs to a solid color and update tracker."""
    mb = _get_motherboard(client)
    if mb is None:
        return
    mb.set_color(RGBColor(r, g, b), fast=True)
    tracker = LEDStateTracker()
    tracker.set_device(MOTHERBOARD_DEVICE_INDEX, r, g, b, MOTHERBOARD_VISIBLE_LEDS)


class SimpleBreathingEffect:
    """Simple breathing with stutter — expands from center outward with a heartbeat rhythm.

    Uses a stutter waveform instead of pure sine: advances smoothly, quick retract,
    then continues. Creates a push-pull feel like a heartbeat.

    Sticks ordered L→R: [0, 1, 2, 3] — center pair is 1,2.
    Distance from center: stick 1=0, stick 2=0, stick 0=1, stick 3=1.
    Motherboard is far right (dist=2).
    """

    # Stutter randomization ranges
    _STUTTER_COUNT_MIN = 1     # Min stutters per cycle
    _STUTTER_COUNT_MAX = 3     # Max stutters per cycle
    _STUTTER_DIP_MIN = 0.25    # Min dip intensity
    _STUTTER_DIP_MAX = 0.55    # Max dip intensity
    _STUTTER_WIDTH_MIN = 0.05  # Min dip width (fraction of cycle)
    _STUTTER_WIDTH_MAX = 0.10  # Max dip width
    _STUTTER_POS_MIN = 0.25    # Earliest a stutter can occur
    _STUTTER_POS_MAX = 0.75    # Latest a stutter can occur

    def __init__(self, color: str = "0000FF",
                 duration: float = 8.0):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.r_base, self.g_base, self.b_base = hex_to_rgb(color)
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self._stick_distance = {0: 1, 1: 0, 2: 0, 3: 1}
        self._phase_spread = 0.15
        self.cycle_duration = duration
        self._start_time = time.monotonic()
        self._stutters = self._generate_stutters()
        self._last_cycle = -1

    def _generate_stutters(self):
        """Generate a random set of stutters for one cycle."""
        count = random.randint(self._STUTTER_COUNT_MIN, self._STUTTER_COUNT_MAX)
        stutters = []
        for _ in range(count):
            pos = random.uniform(self._STUTTER_POS_MIN, self._STUTTER_POS_MAX)
            dip = random.uniform(self._STUTTER_DIP_MIN, self._STUTTER_DIP_MAX)
            width = random.uniform(self._STUTTER_WIDTH_MIN, self._STUTTER_WIDTH_MAX)
            stutters.append((pos, dip, width))
        stutters.sort(key=lambda s: s[0])
        return stutters

    def _stutter_wave(self, t):
        """Sine wave with multiple randomized stutter dips.

        The base is a smooth sine (0→1→0). At randomized positions,
        brightness dips sharply then snaps back up. Count, intensity,
        width, and position are all re-randomized each cycle.
        """
        base = (math.sin(t * 2 * math.pi - math.pi / 2) + 1) / 2
        for pos, dip_intensity, width in self._stutters:
            dist_from_stutter = abs(t - pos)
            if dist_from_stutter < width:
                dip_t = dist_from_stutter / width
                dip = dip_intensity * (math.cos(dip_t * math.pi) + 1) / 2
                base = max(0.0, base - dip)
        return base

    def step(self):
        elapsed = time.monotonic() - self._start_time
        current_cycle = int(elapsed / self.cycle_duration)
        t = (elapsed % self.cycle_duration) / self.cycle_duration

        # Re-randomize stutters each new cycle
        if current_cycle != self._last_cycle:
            self._stutters = self._generate_stutters()
            self._last_cycle = current_cycle

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            dist = self._stick_distance[stick_idx]
            stick_t = (t - dist * self._phase_spread) % 1.0
            brightness = self._stutter_wave(stick_t)

            r = int(self.r_base * brightness)
            g = int(self.g_base * brightness)
            b = int(self.b_base * brightness)

            device.set_color(RGBColor(r, g, b), fast=True)
            self.tracker.set_device(dev_idx, r, g, b, len(device.leds))

        # Motherboard is far right (outermost, dist=2)
        mb_t = (t - 2 * self._phase_spread) % 1.0
        brightness = self._stutter_wave(mb_t)
        r = int(self.r_base * brightness)
        g = int(self.g_base * brightness)
        b = int(self.b_base * brightness)
        _set_motherboard_color(self.client, r, g, b)

    def cleanup(self):
        pass


class BreathingEffect:
    """Breathing effect with phase offset per stick — brightness wave rolls L→R."""

    def __init__(self, color1: str = "000000", color2: str = "00FFFF",
                 duration: float = DEFAULT_BREATHING_DURATION):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.rgb1 = hex_to_rgb(color1)
        self.rgb2 = hex_to_rgb(color2)
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.num_sticks = len(self.ram_devices)
        self.cycle_duration = duration
        self._start_time = time.monotonic()

    def step(self):
        t = ((time.monotonic() - self._start_time) % self.cycle_duration) / self.cycle_duration

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            # Each stick offset by 1/num_sticks of the cycle
            stick_t = (t + stick_idx / self.num_sticks) % 1.0
            blend = 1 - abs(2 * stick_t - 1)

            r = int(self.rgb1[0] + (self.rgb2[0] - self.rgb1[0]) * blend)
            g = int(self.rgb1[1] + (self.rgb2[1] - self.rgb1[1]) * blend)
            b = int(self.rgb1[2] + (self.rgb2[2] - self.rgb1[2]) * blend)

            device.set_color(RGBColor(r, g, b), fast=True)
            self.tracker.set_device(dev_idx, r, g, b, len(device.leds))

        # Motherboard as position 4 (far right, after last stick)
        mb_t = (t + self.num_sticks / (self.num_sticks + 1)) % 1.0
        blend_mb = 1 - abs(2 * mb_t - 1)
        r = int(self.rgb1[0] + (self.rgb2[0] - self.rgb1[0]) * blend_mb)
        g = int(self.rgb1[1] + (self.rgb2[1] - self.rgb1[1]) * blend_mb)
        b = int(self.rgb1[2] + (self.rgb2[2] - self.rgb1[2]) * blend_mb)
        _set_motherboard_color(self.client, r, g, b)

    def cleanup(self):
        pass


class ContrastCycleEffect:
    """High contrast color cycling — each stick on a different color, rotating."""

    def __init__(self, interval: float = 1.0):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.rgb_colors = [RGBColor(*hex_to_rgb(c)) for c in HIGH_CONTRAST_COLORS]
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.cycle_duration = interval * len(self.rgb_colors)
        self._start_time = time.monotonic()

    def step(self):
        elapsed = (time.monotonic() - self._start_time) % self.cycle_duration
        base_idx = int(elapsed / self.cycle_duration * len(self.rgb_colors))
        base_idx = min(base_idx, len(self.rgb_colors) - 1)

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            color_idx = (base_idx + stick_idx) % len(self.rgb_colors)
            c = self.rgb_colors[color_idx]
            device.set_color(c, fast=True)
            self.tracker.set_device(dev_idx, c.red, c.green, c.blue, len(device.leds))

        # Motherboard as far right (next offset after last stick)
        mb_idx = (base_idx + len(self.ram_devices)) % len(self.rgb_colors)
        c = self.rgb_colors[mb_idx]
        _set_motherboard_color(self.client, c.red, c.green, c.blue)

    def cleanup(self):
        pass


class RainbowCycleEffect:
    """Rainbow spread across sticks — each stick at a different hue."""

    def __init__(self):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.num_sticks = len(self.ram_devices)
        self.cycle_duration = 4.0
        self._start_time = time.monotonic()

    def _hue_to_rgb(self, hue):
        r = int((math.cos(math.radians(hue)) + 1) * 127.5)
        g = int((math.cos(math.radians(hue + 120)) + 1) * 127.5)
        b = int((math.cos(math.radians(hue + 240)) + 1) * 127.5)
        return r, g, b

    def step(self):
        t = ((time.monotonic() - self._start_time) % self.cycle_duration) / self.cycle_duration
        base_hue = t * 360

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            # Spread 90 degrees of hue across the 4 sticks
            hue = base_hue + stick_idx * (90 / self.num_sticks)
            r, g, b = self._hue_to_rgb(hue)
            device.set_color(RGBColor(r, g, b), fast=True)
            self.tracker.set_device(dev_idx, r, g, b, len(device.leds))

        # Motherboard as far right (next hue offset after last stick)
        mb_hue = base_hue + self.num_sticks * (90 / self.num_sticks)
        r, g, b = self._hue_to_rgb(mb_hue)
        _set_motherboard_color(self.client, r, g, b)

    def cleanup(self):
        pass


class PulseEffect:
    """Pulsing brightness — wave of brightness rolls across sticks."""

    def __init__(self, color: str = "00FFFF", min_brightness: float = 0.1):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.num_sticks = len(self.ram_devices)
        self.r_base, self.g_base, self.b_base = hex_to_rgb(color)
        self.min_brightness = min_brightness
        self.cycle_duration = 4.0
        self._start_time = time.monotonic()

    def step(self):
        t = ((time.monotonic() - self._start_time) % self.cycle_duration) / self.cycle_duration

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            stick_t = (t + stick_idx / self.num_sticks) % 1.0
            brightness = (math.sin(stick_t * 2 * math.pi) + 1) / 2
            brightness = self.min_brightness + (1 - self.min_brightness) * brightness

            r = int(self.r_base * brightness)
            g = int(self.g_base * brightness)
            b = int(self.b_base * brightness)

            device.set_color(RGBColor(r, g, b), fast=True)
            self.tracker.set_device(dev_idx, r, g, b, len(device.leds))

        # Motherboard as far right (next phase after last stick)
        mb_t = (t + self.num_sticks / (self.num_sticks + 1)) % 1.0
        brightness = (math.sin(mb_t * 2 * math.pi) + 1) / 2
        brightness = self.min_brightness + (1 - self.min_brightness) * brightness
        r = int(self.r_base * brightness)
        g = int(self.g_base * brightness)
        b = int(self.b_base * brightness)
        _set_motherboard_color(self.client, r, g, b)

    def cleanup(self):
        pass


class CpuUsageEffect:
    """Display CPU usage as LED gradient on all RAM sticks."""

    def __init__(self, update_interval: float = DEFAULT_UPDATE_INTERVAL):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.gradient = _precompute_gradient()
        self.black = RGBColor(0, 0, 0)
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        for _, device in self.ram_devices:
            device.set_custom_mode()
        self.cycle_duration = update_interval

    def step(self):
        cpu_percent = get_cpu_usage(CPU_SAMPLE_INTERVAL)
        leds_to_light = _usage_to_leds(cpu_percent)
        for dev_idx, device in self.ram_devices:
            _apply_gradient_to_device(device, dev_idx, leds_to_light, self.gradient, self.black)
        # Motherboard shows usage level color
        if leds_to_light > 0:
            grad_idx = min(leds_to_light - 1, len(self.gradient) - 1)
            c = self.gradient[grad_idx]
            _set_motherboard_color(self.client, c.red, c.green, c.blue)
        else:
            _set_motherboard_color(self.client, 0, 0, 0)

    def cleanup(self):
        for dev_idx, device in self.ram_devices:
            device.set_color(self.black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


class MemoryUsageEffect:
    """Display memory usage as LED gradient on all RAM sticks."""

    def __init__(self, update_interval: float = DEFAULT_UPDATE_INTERVAL):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.gradient = _precompute_gradient()
        self.black = RGBColor(0, 0, 0)
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        for _, device in self.ram_devices:
            device.set_custom_mode()
        self.cycle_duration = update_interval

    def step(self):
        memory_percent, _, _ = get_memory_usage()
        leds_to_light = _usage_to_leds(memory_percent)
        for dev_idx, device in self.ram_devices:
            _apply_gradient_to_device(device, dev_idx, leds_to_light, self.gradient, self.black)
        if leds_to_light > 0:
            grad_idx = min(leds_to_light - 1, len(self.gradient) - 1)
            c = self.gradient[grad_idx]
            _set_motherboard_color(self.client, c.red, c.green, c.blue)
        else:
            _set_motherboard_color(self.client, 0, 0, 0)

    def cleanup(self):
        for dev_idx, device in self.ram_devices:
            device.set_color(self.black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


class SystemMonitoringEffect:
    """Combined CPU and memory display on RAM sticks."""

    def __init__(self, update_interval: float = DEFAULT_UPDATE_INTERVAL):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.gradient = _precompute_gradient()
        self.black = RGBColor(0, 0, 0)
        self.cpu_devices = [(i, self.client.devices[i]) for i in CPU_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.memory_devices = [(i, self.client.devices[i]) for i in MEMORY_DEVICE_INDICES
                               if i < len(self.client.devices)]
        for _, device in self.cpu_devices + self.memory_devices:
            device.set_custom_mode()
        self.cycle_duration = update_interval

    def step(self):
        cpu_percent = get_cpu_usage(CPU_SAMPLE_INTERVAL)
        memory_percent, _, _ = get_memory_usage()
        cpu_leds = _usage_to_leds(cpu_percent)
        memory_leds = _usage_to_leds(memory_percent)

        for dev_idx, device in self.cpu_devices:
            _apply_gradient_to_device(device, dev_idx, cpu_leds, self.gradient, self.black)
        for dev_idx, device in self.memory_devices:
            _apply_gradient_to_device(device, dev_idx, memory_leds, self.gradient, self.black)
        # Motherboard always shows CPU (physically near CPU)
        if cpu_leds > 0:
            grad_idx = min(cpu_leds - 1, len(self.gradient) - 1)
            c = self.gradient[grad_idx]
            _set_motherboard_color(self.client, c.red, c.green, c.blue)
        else:
            _set_motherboard_color(self.client, 0, 0, 0)

    def cleanup(self):
        for dev_idx, device in self.cpu_devices + self.memory_devices:
            device.set_color(self.black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


class BreathingMetricsEffect:
    """Heartbeat overlay on system monitor — two effects composited per LED.

    Layer 0 (background): SystemMonitoringEffect — CPU gradient on right sticks,
    memory gradient on left sticks, motherboard follows CPU. Unmodified.

    Layer 1 (foreground): HeartbeatEffect — blue moving band expanding from top
    center with multi-stutter. Unmodified.

    Compositing rule: heartbeat wins wherever it has brightness > 0.
    Both layers run on independent timing (metrics = 10ms CPU sampling,
    heartbeat = 8s wall-clock cycle).
    """

    # Heartbeat parameters (same as HeartbeatEffect)
    _STUTTER_COUNT_MIN = 1
    _STUTTER_COUNT_MAX = 4
    _STUTTER_DIP_MIN = 0.20
    _STUTTER_DIP_MAX = 0.65
    _STUTTER_WIDTH_MIN = 0.04
    _STUTTER_WIDTH_MAX = 0.10
    _STUTTER_POS_MIN = 0.15
    _STUTTER_POS_MAX = 0.85
    _EDGE_WIDTH = 2.0
    _TRAIL_WIDTH = 4.0

    def __init__(self, heartbeat_color: str = "0000FF", heartbeat_duration: float = 8.0):
        self.client = _get_client()
        self.tracker = LEDStateTracker()

        # --- Metrics layer setup ---
        self.gradient = _precompute_gradient()
        self.black = RGBColor(0, 0, 0)
        self.cpu_devices = [(i, self.client.devices[i]) for i in CPU_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.memory_devices = [(i, self.client.devices[i]) for i in MEMORY_DEVICE_INDICES
                               if i < len(self.client.devices)]
        # Need all RAM devices for per-LED compositing
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        for _, device in self.ram_devices:
            device.set_custom_mode()

        # Which devices show CPU vs memory (as sets for fast lookup)
        self._cpu_set = set(CPU_DEVICE_INDICES)
        self._memory_set = set(MEMORY_DEVICE_INDICES)

        # --- Heartbeat layer setup ---
        self.r_hb, self.g_hb, self.b_hb = hex_to_rgb(heartbeat_color)
        self._stick_lateral = {0: 3, 1: 0, 2: 0, 3: 3}
        max_led_idx = max(len(d.leds) - 1 for _, d in self.ram_devices) if self.ram_devices else 11
        self._mb_lateral = self._stick_lateral[3]
        self._mb_led_start = max_led_idx + 1
        self._max_dist = float(self._mb_lateral + self._mb_led_start + MOTHERBOARD_VISIBLE_LEDS - 1)

        # Motherboard per-LED
        mb = _get_motherboard(self.client)
        if mb:
            mb.set_custom_mode()

        # Heartbeat timing
        self.cycle_duration = heartbeat_duration
        self._start_time = time.monotonic()
        self._stutters = self._generate_stutters()
        self._last_cycle = -1

    # --- Heartbeat wave (identical to HeartbeatEffect) ---

    def _generate_stutters(self):
        count = random.randint(self._STUTTER_COUNT_MIN, self._STUTTER_COUNT_MAX)
        stutters = []
        for _ in range(count):
            pos = random.uniform(self._STUTTER_POS_MIN, self._STUTTER_POS_MAX)
            dip = random.uniform(self._STUTTER_DIP_MIN, self._STUTTER_DIP_MAX)
            width = random.uniform(self._STUTTER_WIDTH_MIN, self._STUTTER_WIDTH_MAX)
            stutters.append((pos, dip, width))
        stutters.sort(key=lambda s: s[0])
        return stutters

    def _stutter_wave(self, t):
        base = (math.sin(t * 2 * math.pi - math.pi / 2) + 1) / 2
        for pos, dip_intensity, width in self._stutters:
            dist = abs(t - pos)
            if dist < width:
                dip_t = dist / width
                dip = dip_intensity * (math.cos(dip_t * math.pi) + 1) / 2
                base = max(0.0, base - dip)
        return base

    def _led_brightness(self, dist, reach):
        if reach <= 0:
            return 0.0
        offset = dist - reach
        if offset > self._EDGE_WIDTH:
            return 0.0
        elif offset > 0:
            return (math.cos(offset / self._EDGE_WIDTH * math.pi) + 1) / 2
        elif offset > -self._TRAIL_WIDTH:
            trail_t = -offset / self._TRAIL_WIDTH
            return (math.cos(trail_t * math.pi) + 1) / 2
        else:
            return 0.0

    def step(self):
        # --- Heartbeat timing ---
        elapsed = time.monotonic() - self._start_time
        current_cycle = int(elapsed / self.cycle_duration)
        t = (elapsed % self.cycle_duration) / self.cycle_duration

        if current_cycle != self._last_cycle:
            self._stutters = self._generate_stutters()
            self._last_cycle = current_cycle

        reach = self._stutter_wave(t) * self._max_dist

        # --- Metrics sampling ---
        cpu_percent = get_cpu_usage(CPU_SAMPLE_INTERVAL)
        memory_percent, _, _ = get_memory_usage()
        cpu_leds = _usage_to_leds(cpu_percent)
        memory_leds = _usage_to_leds(memory_percent)

        # --- Composite per LED on each RAM stick ---
        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            lateral = self._stick_lateral[stick_idx]
            num_leds = len(device.leds)

            # Metrics background for this stick
            leds_to_light = cpu_leds if dev_idx in self._cpu_set else memory_leds
            metric_colors = _build_gradient_colors(num_leds, leds_to_light, self.gradient, self.black)

            colors = []
            for led_idx in range(num_leds):
                # Heartbeat foreground
                hb_brightness = self._led_brightness(lateral + led_idx, reach)

                if hb_brightness > 0:
                    r = int(self.r_hb * hb_brightness)
                    g = int(self.g_hb * hb_brightness)
                    b = int(self.b_hb * hb_brightness)
                else:
                    mc = metric_colors[led_idx]
                    r, g, b = mc.red, mc.green, mc.blue

                colors.append(RGBColor(r, g, b))
                self.tracker.set_led(dev_idx, led_idx, r, g, b)

            device.set_colors(colors, fast=True)

        # --- Motherboard: heartbeat extension of stick 3, metrics fallback = CPU ---
        mb = _get_motherboard(self.client)
        if mb:
            mb_colors = []
            for i in range(len(mb.leds)):
                if i < MOTHERBOARD_VISIBLE_LEDS:
                    physical_pos = MOTHERBOARD_VISIBLE_LEDS - 1 - i
                    dist = self._mb_lateral + self._mb_led_start + physical_pos
                    hb_brightness = self._led_brightness(dist, reach)

                    if hb_brightness > 0:
                        r = int(self.r_hb * hb_brightness)
                        g = int(self.g_hb * hb_brightness)
                        b = int(self.b_hb * hb_brightness)
                    elif cpu_leds > 0:
                        grad_idx = min(cpu_leds - 1, len(self.gradient) - 1)
                        c = self.gradient[grad_idx]
                        r, g, b = c.red, c.green, c.blue
                    else:
                        r, g, b = 0, 0, 0
                else:
                    r, g, b = 0, 0, 0

                mb_colors.append(RGBColor(r, g, b))
                self.tracker.set_led(MOTHERBOARD_DEVICE_INDEX, i, r, g, b)
            mb.set_colors(mb_colors, fast=True)

    def cleanup(self):
        for _, device in self.ram_devices:
            device.set_color(self.black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


class WaveEffect:
    """Wave effect — color palette cycles across sticks with per-stick offset."""

    def __init__(self, colors: Optional[List[str]] = None):
        if colors is None:
            colors = ["0000FF", "0033FF", "0066FF", "0099FF", "00CCFF", "00FFFF"]
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.rgb_colors = [RGBColor(*hex_to_rgb(c)) for c in colors]
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        self.cycle_duration = 4.0
        self._start_time = time.monotonic()

    def step(self):
        t = ((time.monotonic() - self._start_time) % self.cycle_duration) / self.cycle_duration
        offset = int(t * len(self.rgb_colors))

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            color_idx = (offset + stick_idx) % len(self.rgb_colors)
            c = self.rgb_colors[color_idx]
            device.set_color(c, fast=True)
            self.tracker.set_device(dev_idx, c.red, c.green, c.blue, len(device.leds))

        # Motherboard as far right (next offset after last stick)
        mb_idx = (offset + len(self.ram_devices)) % len(self.rgb_colors)
        c = self.rgb_colors[mb_idx]
        _set_motherboard_color(self.client, c.red, c.green, c.blue)

    def cleanup(self):
        pass


class HeartbeatEffect:
    """Per-LED heartbeat — lit region expands from top center outward, then contracts.

    Starts dark. The stutter wave controls how far the lit region reaches (0→1→0).
    LEDs within reach are lit at full color; LEDs beyond reach are off.
    A soft edge (2 LEDs wide) blends the boundary.

    Origin: LED 0 (top) on center sticks (positions 1 and 2).
    Distance = lateral_distance + led_index:
      - Center sticks (1,2): lateral 0 → distance 0-11
      - Outer sticks (0,3): lateral 3 → distance 3-14
      - Motherboard: extension of stick 3 (lateral 3, LEDs 12-14) → distance 15-17
    """

    # Stutter randomization ranges
    _STUTTER_COUNT_MIN = 1     # Min stutters per cycle
    _STUTTER_COUNT_MAX = 4     # Max stutters per cycle
    _STUTTER_DIP_MIN = 0.20    # Min dip intensity
    _STUTTER_DIP_MAX = 0.65    # Max dip intensity
    _STUTTER_WIDTH_MIN = 0.04  # Min dip width (fraction of cycle)
    _STUTTER_WIDTH_MAX = 0.10  # Max dip width
    _STUTTER_POS_MIN = 0.15    # Earliest a stutter can occur
    _STUTTER_POS_MAX = 0.85    # Latest a stutter can occur
    _EDGE_WIDTH = 2.0          # LEDs of soft falloff at the leading edge
    _TRAIL_WIDTH = 4.0         # LEDs of trail behind the wavefront before going dark

    def __init__(self, color: str = "0000FF", duration: float = 8.0):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.r_base, self.g_base, self.b_base = hex_to_rgb(color)
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        for _, device in self.ram_devices:
            device.set_custom_mode()

        # Lateral distance: center sticks = 0, outer sticks = 3 (gap for visual separation)
        self._stick_lateral = {0: 3, 1: 0, 2: 0, 3: 3}

        # Motherboard as extension of stick 3: continues below its last LED
        max_led_idx = max(len(d.leds) - 1 for _, d in self.ram_devices) if self.ram_devices else 11
        self._mb_lateral = self._stick_lateral[3]
        self._mb_led_start = max_led_idx + 1  # first MB LED index (12)

        # Set up motherboard for per-LED control
        mb = _get_motherboard(self.client)
        if mb:
            mb.set_custom_mode()

        # Max distance includes motherboard extension
        self._max_dist = float(self._mb_lateral + self._mb_led_start + MOTHERBOARD_VISIBLE_LEDS - 1)

        self.cycle_duration = duration
        self._start_time = time.monotonic()
        self._stutters = self._generate_stutters()
        self._last_cycle = -1
        self._black = RGBColor(0, 0, 0)

    def _generate_stutters(self):
        """Generate a random set of stutters for one cycle.

        Each stutter is (position, dip_intensity, width). Positions are
        spaced apart so they don't overlap.
        """
        count = random.randint(self._STUTTER_COUNT_MIN, self._STUTTER_COUNT_MAX)
        stutters = []
        for _ in range(count):
            pos = random.uniform(self._STUTTER_POS_MIN, self._STUTTER_POS_MAX)
            dip = random.uniform(self._STUTTER_DIP_MIN, self._STUTTER_DIP_MAX)
            width = random.uniform(self._STUTTER_WIDTH_MIN, self._STUTTER_WIDTH_MAX)
            stutters.append((pos, dip, width))
        # Sort by position so they play out in order
        stutters.sort(key=lambda s: s[0])
        return stutters

    def _stutter_wave(self, t):
        """Returns 0→1→0 with multiple randomized stutter dips."""
        base = (math.sin(t * 2 * math.pi - math.pi / 2) + 1) / 2
        for pos, dip_intensity, width in self._stutters:
            dist_from_stutter = abs(t - pos)
            if dist_from_stutter < width:
                dip_t = dist_from_stutter / width
                dip = dip_intensity * (math.cos(dip_t * math.pi) + 1) / 2
                base = max(0.0, base - dip)
        return base

    def _led_brightness(self, dist, reach):
        """Compute LED brightness as a moving band of light.

        The wavefront is at `reach`. LEDs are brightest right at the wavefront,
        with a soft leading edge ahead and a trailing fade behind. LEDs far
        behind the wavefront go dark — the origin blacks out as the wave passes.
        """
        if reach <= 0:
            return 0.0

        # Distance from the wavefront (negative = behind, positive = ahead)
        offset = dist - reach

        if offset > self._EDGE_WIDTH:
            # Too far ahead of wavefront — dark
            return 0.0
        elif offset > 0:
            # Leading edge — fading in ahead of wavefront
            return (math.cos(offset / self._EDGE_WIDTH * math.pi) + 1) / 2
        elif offset > -self._TRAIL_WIDTH:
            # Trail — still lit, fading out behind wavefront
            trail_t = -offset / self._TRAIL_WIDTH
            return (math.cos(trail_t * math.pi) + 1) / 2
        else:
            # Far behind wavefront — dark (origin has blacked out)
            return 0.0

    def step(self):
        elapsed = time.monotonic() - self._start_time
        current_cycle = int(elapsed / self.cycle_duration)
        t = (elapsed % self.cycle_duration) / self.cycle_duration

        if current_cycle != self._last_cycle:
            self._stutters = self._generate_stutters()
            self._last_cycle = current_cycle

        # reach: how far the lit region extends (0 = nothing, _max_dist = everything)
        reach = self._stutter_wave(t) * self._max_dist

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            lateral = self._stick_lateral[stick_idx]
            num_leds = len(device.leds)
            colors = []

            for led_idx in range(num_leds):
                dist = lateral + led_idx
                brightness = self._led_brightness(dist, reach)

                r = int(self.r_base * brightness)
                g = int(self.g_base * brightness)
                b = int(self.b_base * brightness)
                colors.append(RGBColor(r, g, b))
                self.tracker.set_led(dev_idx, led_idx, r, g, b)

            device.set_colors(colors, fast=True)

        # Motherboard — per-LED, extending below stick 3
        # MB LED indices are physically inverted: LED 0 is top (nearest stick 3),
        # LED 2 is bottom (furthest). Reverse so the wave flows top→bottom.
        mb = _get_motherboard(self.client)
        if mb:
            tracker = self.tracker
            mb_colors = []
            for i in range(len(mb.leds)):
                if i < MOTHERBOARD_VISIBLE_LEDS:
                    physical_pos = MOTHERBOARD_VISIBLE_LEDS - 1 - i  # flip: 0→2, 1→1, 2→0
                    dist = self._mb_lateral + self._mb_led_start + physical_pos
                    brightness = self._led_brightness(dist, reach)
                    r = int(self.r_base * brightness)
                    g = int(self.g_base * brightness)
                    b = int(self.b_base * brightness)
                else:
                    r, g, b = 0, 0, 0
                mb_colors.append(RGBColor(r, g, b))
                tracker.set_led(MOTHERBOARD_DEVICE_INDEX, i, r, g, b)
            mb.set_colors(mb_colors, fast=True)

    def cleanup(self):
        black = RGBColor(0, 0, 0)
        for _, device in self.ram_devices:
            device.set_color(black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


class OceanWaveEffect:
    """Ocean wave effect with per-LED control using wall-clock time."""

    def __init__(self, wave_length: float = 2.0, direction: str = "up"):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        for _, device in self.ram_devices:
            device.set_custom_mode()
        self.color_deep = (0, 0, 255)
        self.color_bright = (0, 255, 255)
        self.stick_phase_offset = 45
        self.led_phase_offset = (360 * wave_length) / LEDS_PER_RAM_STICK
        self.dir_mult = 1 if direction == "up" else -1
        self.direction = direction
        self.cycle_duration = 4.0
        self._start_time = time.monotonic()

    def step(self):
        t = ((time.monotonic() - self._start_time) % self.cycle_duration) / self.cycle_duration
        angle = t * 360

        for stick_idx, (dev_idx, device) in enumerate(self.ram_devices):
            stick_phase = stick_idx * self.stick_phase_offset
            colors = []
            num_leds = len(device.leds)
            for led_idx in range(num_leds):
                led_position = (num_leds - 1 - led_idx) if self.direction == "up" else led_idx
                led_phase = led_position * self.led_phase_offset
                phase = angle + stick_phase + (led_phase * self.dir_mult)
                t_led = (math.sin(math.radians(phase)) + 1) / 2

                r = int(self.color_deep[0] + (self.color_bright[0] - self.color_deep[0]) * t_led)
                g = int(self.color_deep[1] + (self.color_bright[1] - self.color_deep[1]) * t_led)
                b = int(self.color_deep[2] + (self.color_bright[2] - self.color_deep[2]) * t_led)

                colors.append(RGBColor(r, g, b))
                self.tracker.set_led(dev_idx, led_idx, r, g, b)

            device.set_colors(colors, fast=True)

        # Motherboard follows the average color of the wave
        t_mb = (math.sin(math.radians(angle)) + 1) / 2
        mb_r = int(self.color_deep[0] + (self.color_bright[0] - self.color_deep[0]) * t_mb)
        mb_g = int(self.color_deep[1] + (self.color_bright[1] - self.color_deep[1]) * t_mb)
        mb_b = int(self.color_deep[2] + (self.color_bright[2] - self.color_deep[2]) * t_mb)
        _set_motherboard_color(self.client, mb_r, mb_g, mb_b)

    def cleanup(self):
        black = RGBColor(0, 0, 0)
        for _, device in self.ram_devices:
            device.set_color(black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


class OceanBreathEffect:
    """Gentle ocean breathing with per-LED blue gradient using wall-clock time."""

    def __init__(self):
        self.client = _get_client()
        self.tracker = LEDStateTracker()
        self.ram_devices = [(i, self.client.devices[i]) for i in RAM_DEVICE_INDICES
                            if i < len(self.client.devices)]
        for _, device in self.ram_devices:
            device.set_custom_mode()
        self.color_bottom_dim = (0, 0, 80)
        self.color_bottom_bright = (0, 0, 255)
        self.color_top_dim = (0, 80, 100)
        self.color_top_bright = (0, 255, 255)
        self.cycle_duration = 8.0
        self._start_time = time.monotonic()

    def step(self):
        t = ((time.monotonic() - self._start_time) % self.cycle_duration) / self.cycle_duration
        brightness = (math.sin(t * 2 * math.pi) + 1) / 2

        for dev_idx, device in self.ram_devices:
            colors = []
            num_leds = len(device.leds)
            for led_idx in range(num_leds):
                pos = (num_leds - 1 - led_idx) / (num_leds - 1)

                dim_r = int(self.color_bottom_dim[0] + (self.color_top_dim[0] - self.color_bottom_dim[0]) * pos)
                dim_g = int(self.color_bottom_dim[1] + (self.color_top_dim[1] - self.color_bottom_dim[1]) * pos)
                dim_b = int(self.color_bottom_dim[2] + (self.color_top_dim[2] - self.color_bottom_dim[2]) * pos)

                bright_r = int(self.color_bottom_bright[0] + (self.color_top_bright[0] - self.color_bottom_bright[0]) * pos)
                bright_g = int(self.color_bottom_bright[1] + (self.color_top_bright[1] - self.color_bottom_bright[1]) * pos)
                bright_b = int(self.color_bottom_bright[2] + (self.color_top_bright[2] - self.color_bottom_bright[2]) * pos)

                r = int(dim_r + (bright_r - dim_r) * brightness)
                g = int(dim_g + (bright_g - dim_g) * brightness)
                b = int(dim_b + (bright_b - dim_b) * brightness)

                colors.append(RGBColor(r, g, b))
                self.tracker.set_led(dev_idx, led_idx, r, g, b)

            device.set_colors(colors, fast=True)

        # Motherboard follows the breathing brightness at mid-gradient
        mid_r = int(self.color_bottom_dim[0] + (self.color_bottom_bright[0] - self.color_bottom_dim[0]) * brightness)
        mid_g = int(self.color_top_dim[1] + (self.color_top_bright[1] - self.color_top_dim[1]) * brightness)
        mid_b = int(self.color_bottom_dim[2] + (self.color_top_bright[2] - self.color_bottom_dim[2]) * brightness)
        _set_motherboard_color(self.client, mid_r, mid_g, mid_b)

    def cleanup(self):
        black = RGBColor(0, 0, 0)
        for _, device in self.ram_devices:
            device.set_color(black, fast=True)
        _set_motherboard_color(self.client, 0, 0, 0)


# Effect categories
CATEGORY_PER_STICK = "Per Stick"
CATEGORY_PER_LED = "Per LED"
CATEGORY_SYSTEM = "System Monitor"

# Effect registry for easy lookup
EFFECTS = {
    "simple-breathing": {"class": SimpleBreathingEffect, "category": CATEGORY_PER_STICK, "description": "Solid blue fade in/out (all sticks together)"},
    "breathing":   {"class": BreathingEffect,        "category": CATEGORY_PER_STICK, "description": "Cyan fade rolling L→R across sticks"},
    "contrast":    {"class": ContrastCycleEffect,     "category": CATEGORY_PER_STICK, "description": "High contrast color cycling"},
    "rainbow":     {"class": RainbowCycleEffect,      "category": CATEGORY_PER_STICK, "description": "Color spectrum cycle"},
    "pulse":       {"class": PulseEffect,             "category": CATEGORY_PER_STICK, "description": "Pulsing brightness effect"},
    "wave":        {"class": WaveEffect,              "category": CATEGORY_PER_STICK, "description": "Color wave across devices"},
    "heartbeat":   {"class": HeartbeatEffect,          "category": CATEGORY_PER_LED,   "description": "Stutter pulse expanding from top center per LED"},
    "ocean-wave":  {"class": OceanWaveEffect,         "category": CATEGORY_PER_LED,   "description": "Blue-cyan wave per LED"},
    "ocean-breath":{"class": OceanBreathEffect,       "category": CATEGORY_PER_LED,   "description": "Gentle ocean breathing gradient"},
    "cpu":         {"class": CpuUsageEffect,          "category": CATEGORY_SYSTEM,    "description": "CPU usage on all RAM sticks"},
    "memory":      {"class": MemoryUsageEffect,       "category": CATEGORY_SYSTEM,    "description": "Memory usage on all RAM sticks"},
    "system":      {"class": SystemMonitoringEffect,  "category": CATEGORY_SYSTEM,    "description": "CPU (left) + Memory (right)"},
    "breathing-metrics": {"class": BreathingMetricsEffect, "category": CATEGORY_SYSTEM, "description": "Heartbeat overlay on CPU + Memory"},
}
