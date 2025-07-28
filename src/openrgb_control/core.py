"""Core RGB control functionality for OpenRGB devices."""

import subprocess
import time
import math
from typing import List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    # Fallback logger
    class FallbackLogger:
        def debug(self, msg): print(f"DEBUG: {msg}")
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    logger = FallbackLogger()

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
    OPENRGB_PYTHON_AVAILABLE = True
except ImportError:
    OPENRGB_PYTHON_AVAILABLE = False


class RGBDevice:
    """Represents an RGB device controllable via OpenRGB."""
    
    def __init__(self, device_id: int, name: str, led_count: Optional[int] = None):
        self.device_id = device_id
        self.name = name
        self.led_count = led_count
    
    def set_color(self, color: str) -> None:
        """Set color for this device."""
        import os
        if os.geteuid() != 0:
            cmd = ["sudo", "openrgb", "--device", str(self.device_id), "--mode", "direct", "--color", color]
        else:
            cmd = ["openrgb", "--device", str(self.device_id), "--mode", "direct", "--color", color]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to set color for device {self.device_id}: {result.stderr}")
    
    def set_mode(self, mode: str) -> None:
        """Set mode for this device."""
        import os
        if os.geteuid() != 0:
            cmd = ["sudo", "openrgb", "--device", str(self.device_id), "--mode", mode]
        else:
            cmd = ["openrgb", "--device", str(self.device_id), "--mode", mode]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to set mode for device {self.device_id}: {result.stderr}")
    
    def set_colors(self, colors: List[str]) -> None:
        """Set multiple colors for this device."""
        color_string = ",".join(colors)
        import os
        if os.geteuid() != 0:
            cmd = ["sudo", "openrgb", "--device", str(self.device_id), "--mode", "direct", "--color", color_string]
        else:
            cmd = ["openrgb", "--device", str(self.device_id), "--mode", "direct", "--color", color_string]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to set colors for device {self.device_id}: {result.stderr}")


class RGBController:
    """Main controller for RGB devices."""
    
    def __init__(self, skip_detection: bool = False):
        self.all_devices = {
            0: RGBDevice(0, "Corsair RAM Stick", 10),
            1: RGBDevice(1, "Corsair RAM Stick", 10), 
            2: RGBDevice(2, "Corsair RAM Stick", 10),
            3: RGBDevice(3, "Corsair RAM Stick", 10),
            4: RGBDevice(4, "ASUS Motherboard"),
            5: RGBDevice(5, "ASUS Mouse 2.4GHz"),
            6: RGBDevice(6, "ASUS Mouse Dock"), 
            7: RGBDevice(7, "Logitech Keyboard")
        }
        # Always assume all devices are accessible to speed up startup
        self.accessible_devices = self.all_devices.copy()
    
    
    @property
    def devices(self):
        """Get accessible devices only."""
        return self.accessible_devices
    
    def set_all_color(self, color: str) -> None:
        """Set color for all accessible devices."""
        # Batch command for all devices at once
        device_ids = ",".join(str(device_id) for device_id in self.accessible_devices.keys())
        cmd = ["openrgb", "--device", device_ids, "--mode", "direct", "--color", color]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Fall back to individual commands if batch fails
            for device_id, device in self.accessible_devices.items():
                device.set_color(color)
    
    def get_device(self, device_id: int) -> Optional[RGBDevice]:
        """Get device by ID."""
        return self.devices.get(device_id)


class FastRGBController:
    """Fast RGB controller using openrgb-python socket client."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 6742):
        if not OPENRGB_PYTHON_AVAILABLE:
            raise ImportError("openrgb-python not available")
        
        self.host = host
        self.port = port
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect to OpenRGB server."""
        try:
            self.client = OpenRGBClient(self.host, self.port)
        except Exception as e:
            raise RuntimeError(f"Failed to connect to OpenRGB server: {e}")
    
    def set_all_color(self, color: str) -> None:
        """Set color for all devices using single socket connection."""
        if not self.client:
            self._connect()
        
        # Convert hex to RGB
        r, g, b = hex_to_rgb(color)
        
        logger.debug(f"Found {len(self.client.devices)} devices")
        
        # Set all devices at once
        for i, device in enumerate(self.client.devices):
            try:
                logger.debug(f"Setting device {i}: {device.name} ({len(device.leds)} LEDs)")
                # Set device to direct mode first
                device.set_mode("direct")
                # Set color for all LEDs
                color_obj = RGBColor(r, g, b)
                colors = [color_obj for _ in range(len(device.leds))]
                device.set_colors(colors)
                logger.debug(f"Successfully set device {i}")
            except Exception as e:
                logger.error(f"Failed to set device {i}: {e}")
    
    def blackout_all(self) -> None:
        """Turn off all devices."""
        self.set_all_color("000000")
    
    def close(self):
        """Close the connection."""
        if self.client:
            self.client = None


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB tuple to hex string."""
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


def interpolate_color(color1: str, color2: str, t: float) -> str:
    """Interpolate between two colors. t = 0.0 to 1.0"""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return rgb_to_hex(r, g, b)
