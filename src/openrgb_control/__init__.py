"""OpenRGB Control - Dynamic RGB lighting control for Linux."""

__version__ = "0.1.0"

from .core import RGBController, RGBDevice
from .dynamic import (
    breathing_effect,
    wave_effect,
    rainbow_cycle,
    pulse_effect,
    breathing_ripple,
    memory_usage_effect
)
from .static import apply_theme, THEMES

__all__ = [
    'RGBController',
    'RGBDevice',
    'breathing_effect',
    'wave_effect',
    'rainbow_cycle',
    'pulse_effect',
    'breathing_ripple',
    'memory_usage_effect',
    'apply_theme',
    'THEMES'
]
