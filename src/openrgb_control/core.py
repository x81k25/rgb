"""Core RGB control functionality using OpenRGB socket protocol."""

import threading
from typing import Dict, List, Tuple

from .config import SERVER_HOST, SERVER_PORT, LEDS_PER_RAM_STICK

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
    OPENRGB_AVAILABLE = True
except ImportError:
    OPENRGB_AVAILABLE = False
    OpenRGBClient = None
    RGBColor = None


class LEDStateTracker:
    """Singleton that tracks the current color of every LED.

    Stores state as {device_index: {led_index: (r, g, b)}}.
    Thread-safe for concurrent access from effects and Streamlit.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._state: Dict[int, Dict[int, Tuple[int, int, int]]] = {}
        return cls._instance

    @property
    def state(self) -> Dict[int, Dict[int, Tuple[int, int, int]]]:
        return self._state

    def set_led(self, device_index: int, led_index: int, r: int, g: int, b: int):
        """Record a single LED color."""
        if device_index not in self._state:
            self._state[device_index] = {}
        self._state[device_index][led_index] = (r, g, b)

    def set_device(self, device_index: int, r: int, g: int, b: int, num_leds: int = LEDS_PER_RAM_STICK):
        """Record all LEDs on a device to the same color."""
        self._state[device_index] = {i: (r, g, b) for i in range(num_leds)}

    def clear(self):
        """Reset all tracked state."""
        self._state.clear()

    def get_device_leds(self, device_index: int) -> Dict[int, Tuple[int, int, int]]:
        """Get LED states for a specific device."""
        return self._state.get(device_index, {})

    def to_dict(self) -> Dict[str, Dict[str, list]]:
        """Serialize state to JSON-safe dict: {dev_idx: {led_idx: [r,g,b]}}."""
        return {
            str(dev): {str(led): list(rgb) for led, rgb in leds.items()}
            for dev, leds in self._state.items()
        }

    def from_dict(self, data: Dict[str, Dict[str, list]]):
        """Populate state from a dict produced by to_dict()."""
        self._state.clear()
        for dev_str, leds in data.items():
            dev_idx = int(dev_str)
            self._state[dev_idx] = {}
            for led_str, rgb in leds.items():
                self._state[dev_idx][int(led_str)] = tuple(rgb)


def get_client(host: str = SERVER_HOST, port: int = SERVER_PORT) -> 'OpenRGBClient':
    """Get a shared OpenRGB client connection (singleton).

    Reuses the same connection across all callers to avoid
    spawning a new server handshake on every action.
    """
    if not OPENRGB_AVAILABLE:
        raise ImportError(
            "openrgb-python not available. Install with: uv add openrgb-python"
        )

    if not hasattr(get_client, '_instance') or get_client._instance is None:
        try:
            get_client._instance = OpenRGBClient(host, port)
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to OpenRGB server at {host}:{port}. "
                f"Ensure server is running: sudo openrgb --server\nError: {e}"
            )
    return get_client._instance


class RGBController:
    """Socket-based RGB controller using openrgb-python.

    Uses the shared singleton client connection.
    """

    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.client = get_client(host, port)

    @property
    def devices(self):
        """Get list of connected devices."""
        return self.client.devices if self.client else []

    def set_all_color(self, color: str) -> None:
        """Set color for all devices."""
        r, g, b = hex_to_rgb(color)
        rgb_color = RGBColor(r, g, b)

        for device in self.client.devices:
            try:
                device.set_color(rgb_color)
            except Exception as e:
                logger.debug(f"Failed to set color on {device.name}: {e}")

    def blackout(self) -> None:
        """Turn off all devices."""
        self.set_all_color("000000")

    def disconnect(self):
        """No-op: connection is managed by the shared singleton."""
        pass


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex string."""
    return f"{r:02X}{g:02X}{b:02X}"


def interpolate_colors(color1: str, color2: str, steps: int) -> List[str]:
    """Generate color gradient between two colors."""
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)

    colors = []
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 0
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * t)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * t)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * t)
        colors.append(rgb_to_hex(r, g, b))

    return colors


