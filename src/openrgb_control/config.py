"""Shared configuration constants for RGB control.

This module centralizes all configuration values that were previously
scattered across multiple files.
"""

# OpenRGB server settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 6743


# Device configuration
# Maps physical RAM stick position (left to right) to OpenRGB device index
DEVICE_MAPPING = {
    "ram": {
        0: 1,  # Leftmost RAM stick
        1: 3,
        2: 0,
        3: 2,  # Rightmost RAM stick
    },
    "motherboard": {
        "device_index": 4,
        "visible_leds": 3,  # LEDs 0-2 are visible; 3-4 are unplugged RGB headers
    },
}

# Flat list of RAM device indices for quick access
RAM_DEVICE_INDICES = [1, 3, 0, 2]
MOTHERBOARD_DEVICE_INDEX = 4
MOTHERBOARD_VISIBLE_LEDS = 3

# For system monitoring: split RAM sticks between CPU and memory display
CPU_DEVICE_INDICES = [0, 2]     # Sticks 2-3 (right side)
MEMORY_DEVICE_INDICES = [1, 3]  # Sticks 0-1 (left side)

# LED counts per device type
LEDS_PER_RAM_STICK = 12

# Status gradient colors (cyan->green->yellow->orange->red, bottom to top)
# Used for CPU/memory usage visualization
STATUS_GRADIENT_HEX = [
    "00FFFF",  # LED 0 (bottom) - Cyan
    "00FFFF",  # LED 1 - Cyan
    "00FFAA",  # LED 2 - Cyan-Green
    "00FF55",  # LED 3 - Green-Cyan
    "00FF00",  # LED 4 - Pure Green
    "55FF00",  # LED 5 - Green-Yellow
    "AAFF00",  # LED 6 - Yellow-Green
    "FFFF00",  # LED 7 - Yellow
    "FFCC00",  # LED 8 - Yellow-Orange
    "FFAA00",  # LED 9 - Orange
    "FF5500",  # LED 10 - Red-Orange
    "FF0000",  # LED 11 (top) - Red
]

# High contrast colors for dramatic effects
HIGH_CONTRAST_COLORS = [
    "FF0000",  # Red
    "00FF00",  # Green
    "0000FF",  # Blue
    "FFFF00",  # Yellow
    "FF00FF",  # Magenta
    "00FFFF",  # Cyan
    "FFFFFF",  # White
    "FF8800",  # Orange
    "8800FF",  # Purple
    "000000",  # Black (off)
]

# Animation timing defaults
DEFAULT_BREATHING_DURATION = 4.0
DEFAULT_BREATHING_STEPS = 20
DEFAULT_UPDATE_INTERVAL = 5.0  # For monitoring effects
CPU_SAMPLE_INTERVAL = 0.01    # 10ms for non-blocking CPU sampling
