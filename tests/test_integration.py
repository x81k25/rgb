"""Integration tests that connect to the real OpenRGB server.

Run with: uv run pytest tests/test_integration.py -v
Requires: sudo openrgb --server --server-port 6743
"""

import math
import time
import pytest
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

from src.openrgb_control.config import SERVER_HOST, SERVER_PORT, RAM_DEVICE_INDICES, DEVICE_MAPPING


@pytest.fixture(scope="session")
def client():
    """Connect to the real OpenRGB server (shared across all tests)."""
    try:
        c = OpenRGBClient(SERVER_HOST, SERVER_PORT)
    except Exception:
        pytest.skip("OpenRGB server not running")
    yield c
    c.disconnect()


@pytest.fixture
def exclusive_hardware(client):
    """Verify no other process is controlling the hardware.

    Sets a known color, waits, reads back. If the color changed,
    another process has control and we skip instead of failing.
    """
    canary = RGBColor(42, 42, 42)
    device = client.devices[0]
    device.set_color(canary)
    time.sleep(0.15)
    device.update()
    actual = device.colors[0]
    if abs(actual.red - 42) > 2 or abs(actual.green - 42) > 2 or abs(actual.blue - 42) > 2:
        pytest.skip(
            "Another process is controlling the hardware "
            f"(set (42,42,42), read back ({actual.red},{actual.green},{actual.blue})). "
            "Stop Streamlit or other RGB apps before running integration tests."
        )


@pytest.fixture
def ram_devices(client):
    """Get the 4 RAM stick devices."""
    return [(i, client.devices[i]) for i in RAM_DEVICE_INDICES if i < len(client.devices)]


class TestStaticColors:
    """Test that static colors are correctly applied and readable."""

    @pytest.mark.parametrize("r,g,b,name", [
        (255, 0, 0, "red"),
        (0, 255, 0, "green"),
        (0, 0, 255, "blue"),
        (0, 255, 255, "cyan"),
        (0, 0, 0, "black"),
    ])
    def test_set_color_readback(self, client, exclusive_hardware, r, g, b, name):
        """Set a color on all devices and verify readback."""
        color = RGBColor(r, g, b)
        for d in client.devices:
            d.set_color(color)
        time.sleep(0.05)

        for d in client.devices:
            d.update()

        for i, d in enumerate(client.devices):
            for led_idx, led_color in enumerate(d.colors):
                assert abs(led_color.red - r) <= 1, \
                    f"Dev {i} LED {led_idx}: expected R={r}, got {led_color.red}"
                assert abs(led_color.green - g) <= 1, \
                    f"Dev {i} LED {led_idx}: expected G={g}, got {led_color.green}"
                assert abs(led_color.blue - b) <= 1, \
                    f"Dev {i} LED {led_idx}: expected B={b}, got {led_color.blue}"


class TestPerLEDControl:
    """Test per-LED batch color setting."""

    def test_set_colors_batch(self, exclusive_hardware, ram_devices):
        """Verify set_colors() sets each LED independently."""
        for dev_idx, device in ram_devices:
            device.set_custom_mode()

        # Set a gradient: LED 0 = full red, last LED = full blue
        for dev_idx, device in ram_devices:
            num_leds = len(device.leds)
            colors = []
            for i in range(num_leds):
                t = i / (num_leds - 1)
                colors.append(RGBColor(int(255 * (1 - t)), 0, int(255 * t)))
            device.set_colors(colors, fast=True)

        time.sleep(0.05)

        # Readback
        for dev_idx, device in ram_devices:
            device.update()
            num_leds = len(device.leds)
            # First LED should be mostly red
            assert device.colors[0].red > 200, \
                f"Dev {dev_idx} LED 0 should be red, got R={device.colors[0].red}"
            assert device.colors[0].blue < 50
            # Last LED should be mostly blue
            assert device.colors[num_leds - 1].blue > 200, \
                f"Dev {dev_idx} LED {num_leds-1} should be blue, got B={device.colors[num_leds-1].blue}"
            assert device.colors[num_leds - 1].red < 50

    def test_static_overrides_per_led(self, client, exclusive_hardware, ram_devices):
        """After per-LED effect, static set_color should reset all LEDs."""
        # First set per-LED gradient
        for dev_idx, device in ram_devices:
            device.set_custom_mode()
            num_leds = len(device.leds)
            colors = [RGBColor(i * 20, 0, 255 - i * 20) for i in range(num_leds)]
            device.set_colors(colors, fast=True)

        time.sleep(0.05)

        # Now override with solid green
        green = RGBColor(0, 255, 0)
        for d in client.devices:
            d.set_color(green)

        time.sleep(0.05)

        for dev_idx, device in ram_devices:
            device.update()
            for led_idx, c in enumerate(device.colors):
                assert c.green > 250, \
                    f"Dev {dev_idx} LED {led_idx}: expected green, got ({c.red},{c.green},{c.blue})"
                assert c.red < 5 and c.blue < 5


class TestOceanWaveEffect:
    """Test the ocean wave effect produces varying per-LED colors."""

    def test_ocean_wave_single_frame(self, exclusive_hardware, ram_devices):
        """One frame of ocean wave should produce non-uniform LED colors."""
        for dev_idx, device in ram_devices:
            device.set_custom_mode()

        angle = 45
        for stick_idx, (dev_idx, device) in enumerate(ram_devices):
            colors = []
            for led_idx in range(len(device.leds)):
                phase = angle + stick_idx * 45 + led_idx * 72
                t = (math.sin(math.radians(phase)) + 1) / 2
                r = 0
                g = int(255 * t)
                b = int(255 * (0.5 + 0.5 * t))
                colors.append(RGBColor(r, g, b))
            device.set_colors(colors, fast=True)

        time.sleep(0.05)

        # Verify LEDs are not all the same color (wave creates variation)
        for dev_idx, device in ram_devices:
            device.update()
            unique_colors = set()
            for c in device.colors:
                unique_colors.add((c.red, c.green, c.blue))
            assert len(unique_colors) > 1, \
                f"Dev {dev_idx}: all LEDs same color, wave effect didn't work"


class TestEffectClasses:
    """Test the effect class framework works end-to-end."""

    def test_breathing_effect_step(self, client, exclusive_hardware):
        """BreathingEffect.step() should change device colors."""
        from src.openrgb_control.dynamic.dynamic import BreathingEffect
        effect = BreathingEffect()

        # Run a few frames
        for _ in range(5):
            effect.step()
            time.sleep(0.01)

        # Read back - should not be black (breathing starts from black, moves to cyan)
        for d in client.devices:
            d.update()

        # After 5 frames we should have moved off pure black
        any_nonblack = False
        for d in client.devices:
            for c in d.colors:
                if c.red > 0 or c.green > 0 or c.blue > 0:
                    any_nonblack = True
                    break
        assert any_nonblack, "After 5 breathing frames, should have moved off black"
        effect.cleanup()

    def test_ocean_wave_effect_step(self, client, exclusive_hardware):
        """OceanWaveEffect.step() should produce per-LED variation."""
        from src.openrgb_control.dynamic.dynamic import OceanWaveEffect
        effect = OceanWaveEffect()

        # Run several frames
        for _ in range(10):
            effect.step()
            time.sleep(0.01)

        # Read back RAM sticks
        for dev_idx in RAM_DEVICE_INDICES:
            if dev_idx < len(client.devices):
                client.devices[dev_idx].update()
                unique = set((c.red, c.green, c.blue) for c in client.devices[dev_idx].colors)
                assert len(unique) > 1, \
                    f"Dev {dev_idx}: ocean wave should produce per-LED variation"

        effect.cleanup()


class TestLEDStateTracker:
    """Test that LEDStateTracker records match hardware state."""

    def test_tracker_matches_hardware(self, client, exclusive_hardware, ram_devices):
        """After applying a static theme, tracker should match device readback."""
        from src.openrgb_control import apply_theme, LEDStateTracker

        apply_theme("cyan")
        tracker = LEDStateTracker()

        time.sleep(0.05)

        for dev_idx, device in ram_devices:
            device.update()
            tracked = tracker.get_device_leds(dev_idx)
            for led_idx in range(len(device.leds)):
                hw_color = device.colors[led_idx]
                tr_color = tracked.get(led_idx, (0, 0, 0))
                assert abs(hw_color.red - tr_color[0]) <= 1 and \
                       abs(hw_color.green - tr_color[1]) <= 1 and \
                       abs(hw_color.blue - tr_color[2]) <= 1, \
                    f"Dev {dev_idx} LED {led_idx}: tracker={tr_color} hw=({hw_color.red},{hw_color.green},{hw_color.blue})"


# Cleanup: blackout after all tests
@pytest.fixture(autouse=True, scope="session")
def cleanup_after_tests():
    yield
    try:
        c = OpenRGBClient(SERVER_HOST, SERVER_PORT)
        black = RGBColor(0, 0, 0)
        for d in c.devices:
            d.set_color(black)
        c.disconnect()
    except Exception:
        pass
