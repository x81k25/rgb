"""OpenRGB Control - Simple RGB lighting control for Linux."""

__version__ = "0.3.0"

from .core import RGBController, LEDStateTracker, get_client, hex_to_rgb, rgb_to_hex
from .static import apply_theme, THEMES
from .dynamic import EFFECTS

__all__ = [
    "RGBController",
    "LEDStateTracker",
    "hex_to_rgb",
    "rgb_to_hex",
    "apply_theme",
    "THEMES",
    "EFFECTS",
]
