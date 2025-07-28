#!/usr/bin/env python3
"""OpenRGB server client for high-performance RGB control."""

import requests
import json
import time
from typing import List, Dict, Optional, Any

class OpenRGBServerClient:
    """High-performance OpenRGB client using server mode."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 6742):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.devices_cache = None
        
    def is_connected(self) -> bool:
        """Check if server is accessible."""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    def get_devices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get list of RGB devices from server.
        
        Args:
            force_refresh: Force refresh of device cache
            
        Returns:
            List of device information dictionaries
        """
        if self.devices_cache is None or force_refresh:
            try:
                response = self.session.get(f"{self.base_url}/devices", timeout=2)
                response.raise_for_status()
                self.devices_cache = response.json()
            except Exception as e:
                print(f"Failed to get devices: {e}")
                return []
        
        return self.devices_cache or []
    
    def set_device_color(self, device_id: int, color: str) -> bool:
        """Set single color for a device.
        
        Args:
            device_id: Device ID
            color: Hex color string (e.g., "FF0000")
            
        Returns:
            True if successful
        """
        try:
            data = {
                "device": device_id,
                "mode": "direct",
                "color": color
            }
            response = self.session.post(f"{self.base_url}/device/{device_id}/color", 
                                       json=data, timeout=1)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to set device {device_id} color: {e}")
            return False
    
    def set_device_colors(self, device_id: int, colors: List[str]) -> bool:
        """Set multiple colors for a device (per-LED).
        
        Args:
            device_id: Device ID
            colors: List of hex color strings
            
        Returns:
            True if successful
        """
        try:
            data = {
                "device": device_id,
                "mode": "direct",
                "colors": colors
            }
            response = self.session.post(f"{self.base_url}/device/{device_id}/colors", 
                                       json=data, timeout=1)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to set device {device_id} colors: {e}")
            return False
    
    def set_multiple_devices_colors(self, device_colors: Dict[int, List[str]]) -> bool:
        """Set colors for multiple devices in a single request.
        
        Args:
            device_colors: Dict mapping device_id to list of colors
            
        Returns:
            True if successful
        """
        try:
            data = {
                "devices": [
                    {
                        "device": device_id,
                        "mode": "direct", 
                        "colors": colors
                    }
                    for device_id, colors in device_colors.items()
                ]
            }
            response = self.session.post(f"{self.base_url}/devices/colors", 
                                       json=data, timeout=1)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to set multiple device colors: {e}")
            return False
    
    def set_all_devices_color(self, color: str, device_filter: Optional[List[int]] = None) -> bool:
        """Set single color for all devices (or filtered list).
        
        Args:
            color: Hex color string
            device_filter: Optional list of device IDs to target
            
        Returns:
            True if successful
        """
        try:
            data = {
                "color": color,
                "mode": "direct"
            }
            if device_filter:
                data["devices"] = device_filter
                
            response = self.session.post(f"{self.base_url}/devices/color", 
                                       json=data, timeout=1)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to set all devices color: {e}")
            return False
    
    def get_device_info(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device information dictionary or None
        """
        try:
            response = self.session.get(f"{self.base_url}/device/{device_id}", timeout=1)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get device {device_id} info: {e}")
            return None
    
    def close(self):
        """Close the session."""
        self.session.close()

class FastRGBController:
    """High-performance RGB controller using OpenRGB server."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 6742):
        self.client = OpenRGBServerClient(host, port)
        
        # Device mapping - same as before
        self.ram_devices = [0, 1, 2, 3]  # All RAM devices
        self.other_devices = [4, 5, 6, 7]  # Motherboard, mouse, etc.
        
        # Physical to device mapping for RAM
        self.physical_to_device = {0: 1, 1: 3, 2: 0, 3: 2}
    
    def is_connected(self) -> bool:
        """Check if connected to OpenRGB server."""
        return self.client.is_connected()
    
    def set_ram_gradient(self, colors: List[str]) -> bool:
        """Set gradient colors on all RAM sticks simultaneously.
        
        Args:
            colors: List of 10 hex color strings for LEDs
            
        Returns:
            True if successful
        """
        # Prepare colors for all RAM devices
        device_colors = {device_id: colors for device_id in self.ram_devices}
        
        # Send single batch request
        return self.client.set_multiple_devices_colors(device_colors)
    
    def set_all_ram_color(self, color: str) -> bool:
        """Set single color on all RAM sticks.
        
        Args:
            color: Hex color string
            
        Returns:
            True if successful
        """
        return self.client.set_all_devices_color(color, self.ram_devices)
    
    def set_all_devices_color(self, color: str) -> bool:
        """Set single color on all devices.
        
        Args:
            color: Hex color string
            
        Returns:
            True if successful
        """
        return self.client.set_all_devices_color(color)
    
    def blackout_all(self) -> bool:
        """Turn off all devices."""
        return self.set_all_devices_color("000000")
    
    def close(self):
        """Close the connection."""
        self.client.close()

# Convenience functions for backward compatibility
def create_fast_controller(host: str = "127.0.0.1", port: int = 6742) -> FastRGBController:
    """Create a FastRGBController instance."""
    return FastRGBController(host, port)