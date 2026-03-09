"""Static RGB color themes."""

import os
import yaml

from ..core import RGBController, LEDStateTracker, hex_to_rgb, OPENRGB_AVAILABLE

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from openrgb.utils import RGBColor
except ImportError:
    RGBColor = None


def _load_themes() -> dict:
    """Load static theme definitions from config/profiles-static.yaml."""
    # Project root is 3 levels up: static/ -> openrgb_control/ -> src/ -> rgb/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    yaml_path = os.path.join(project_root, "config", "profiles-static.yaml")
    with open(yaml_path, "r") as f:
        profiles = yaml.safe_load(f)
    return profiles.get("profiles", {})


THEMES = _load_themes()


def apply_theme(theme_name: str) -> None:
    """Apply a color theme to all RGB devices.

    Args:
        theme_name: Name of the theme to apply (see THEMES dict)

    Raises:
        ValueError: If theme_name is not found
        RuntimeError: If unable to connect to OpenRGB server
    """
    if theme_name not in THEMES:
        available = ", ".join(THEMES.keys())
        raise ValueError(f"Unknown theme '{theme_name}'. Available: {available}")

    theme = THEMES[theme_name]
    controller = RGBController()
    tracker = LEDStateTracker()

    try:
        if theme.get("type") == "gradient":
            _apply_gradient_theme(controller, theme, tracker)
        else:
            r, g, b = hex_to_rgb(theme["color"])
            controller.set_all_color(theme["color"])
            for idx, device in enumerate(controller.devices):
                num_leds = len(device.leds) if hasattr(device, 'leds') else LEDS_PER_RAM_STICK
                tracker.set_device(idx, r, g, b, num_leds)

    finally:
        controller.disconnect()


def _apply_gradient_theme(controller: RGBController, theme: dict, tracker: LEDStateTracker) -> None:
    """Apply a gradient theme to RAM devices."""
    colors = theme["colors"]

    rgb_colors = []
    for hex_color in colors:
        r, g, b = hex_to_rgb(hex_color)
        rgb_colors.append(RGBColor(r, g, b))

    for i, device in enumerate(controller.devices):
        if i >= 4:
            device.set_color(rgb_colors[-1])
            c = rgb_colors[-1]
            num_leds = len(device.leds) if hasattr(device, 'leds') else 10
            tracker.set_device(i, c.red, c.green, c.blue, num_leds)
        else:
            try:
                for led_idx, rgb_color in enumerate(rgb_colors):
                    if led_idx < len(device.leds):
                        device.leds[led_idx].set_color(rgb_color)
                        tracker.set_led(i, led_idx, rgb_color.red, rgb_color.green, rgb_color.blue)
            except Exception:
                device.set_color(rgb_colors[0])
                c = rgb_colors[0]
                num_leds = len(device.leds) if hasattr(device, 'leds') else 10
                tracker.set_device(i, c.red, c.green, c.blue, num_leds)
