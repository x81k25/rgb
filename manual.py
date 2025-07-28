#!/usr/bin/env python3
"""Manual RGB control - bare bones direct device communication"""

import random
import sys
import time
try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
except ImportError:
    print("Error: openrgb-python not installed")
    print("Run: uv add openrgb-python")
    sys.exit(1)


def connect():
    """Connect to OpenRGB server"""
    try:
        client = OpenRGBClient('127.0.0.1', 6742)
        return client
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("Make sure OpenRGB server is running:")
        print("sudo openrgb --server --server-host 127.0.0.1 --server-port 6742")
        return None

# Create client object first:
client = connect()


def list_devices(client):
    """List all RGB devices"""
    print(f"\nFound {len(client.devices)} devices:")
    for i, device in enumerate(client.devices):
        print(f"  [{i}] {device.name} - {len(device.leds)} LEDs")

# list_devices(client)

def set_device_color(client, device_id, r, g, b):
    """Set entire device to single color"""
    if device_id >= len(client.devices):
        print(f"Invalid device ID {device_id}")
        return
    
    device = client.devices[device_id]
    color = RGBColor(r, g, b)
    device.set_color(color, fast=True)
    print(f"Set {device.name} to RGB({r},{g},{b})")

# set_device_color(client, 4, 255, 0, 0)  # Set first device to red

def manual_wave():
    for j in range(0,3):    
        interval = 0.1
        for i in [1, 3, 0, 2, 5, 6, 7]:  
            set_device_color(client, i, 255, 0, 0)
            time.sleep(interval)
            set_device_color(client, i, 0, 255, 0)
            time.sleep(interval)
            set_device_color(client, i, 0, 0, 255)
            time.sleep(interval)

manual_wave()

colors = [
    RGBColor(255, 0, 0),    # LED 0: Red
    RGBColor(0, 255, 0),    # LED 1: Green  
    RGBColor(0, 0, 255),    # LED 2: Blue
    # ... continue for all LEDs
]

def set_device_color_array(device, colors_rgb_list):
   """Set device using color array - efficient batch update"""
   colors = [RGBColor(r, g, b) for r, g, b in colors_rgb_list]
   device.colors = colors

# Usage examples:
# Single color for all LEDs
red_array = [(255, 0, 0)] * len(device.leds)
set_device_color_array(device, red_array)

# Different color per LED
rainbow_array = [
   (255, 0, 0),    # LED 0: Red
   (255, 127, 0),  # LED 1: Orange
   (255, 255, 0),  # LED 2: Yellow
   (0, 255, 0),    # LED 3: Green
   # ... continue for all LEDs
]
set_device_color_array(device, rainbow_array)




def set_led_color(client, device_id, led_id, r, g, b):
    """Set individual LED color"""
    if device_id >= len(client.devices):
        print(f"Invalid device ID {device_id}")
        return
    
    device = client.devices[device_id]
    if led_id >= len(device.leds):
        print(f"Invalid LED ID {led_id} for {device.name}")
        return
    
    color = RGBColor(r, g, b)
    device.leds[led_id].set_color(color)
    print(f"Set {device.name} LED[{led_id}] to RGB({r},{g},{b})")

# set_led_color(client, 0, 0, 0, 255, 0)  # Set first LED of first device to green

# see how many simalteaneous led color changes you can make
def set_led_colors():
    set_led_color(client, 0, 0, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 1, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 2, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 3, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 4, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 5, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 6, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 7, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 8, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 0, 9, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 0, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 1, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 2, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 3, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 4, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 5, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 6, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 7, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 8, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    set_led_color(client, 1, 9, random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

set_led_colors()

def set_all_devices(client, r, g, b):
    """Set all devices to same color"""
    color = RGBColor(r, g, b)
    for device in client.devices:
        device.set_color(color)
    print(f"Set all devices to RGB({r},{g},{b})")

# set_all_devices(client, 0, 0, 255)  # Set all devices to blue

def strobe_blue_black():
    i = 0
    interval = 0.1
    while i < 10:
        set_all_devices(client, 0, 0, 255)
        #time.sleep(interval)
        set_all_devices(client, 0, 0, 0)
        #time.sleep(interval)
        i += 1
        
strobe_blue_black()

def rainbow_gradient(client, device_id):
    """Apply rainbow gradient to device LEDs"""
    if device_id >= len(client.devices):
        print(f"Invalid device ID {device_id}")
        return
    
    device = client.devices[device_id]
    led_count = len(device.leds)
    
    for i in range(led_count):
        hue = (i * 360) // led_count
        # Simple HSV to RGB conversion
        h = hue / 60
        c = 1.0
        x = c * (1 - abs((h % 2) - 1))
        
        if h < 1:
            r, g, b = c, x, 0
        elif h < 2:
            r, g, b = x, c, 0
        elif h < 3:
            r, g, b = 0, c, x
        elif h < 4:
            r, g, b = 0, x, c
        elif h < 5:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        color = RGBColor(int(r * 255), int(g * 255), int(b * 255))
        device.leds[i].set_color(color)
    
    print(f"Applied rainbow gradient to {device.name}")

# rainbow_gradient(client, 0)  # Apply rainbow to first device


def turn_off_all(client):
    """Turn off all RGB devices"""
    black = RGBColor(0, 0, 0)
    for device in client.devices:
        device.set_color(black)
    print("Turned off all devices")

# turn_off_all(client)


def demo():
    """Run a simple demo"""
    client = connect()
    if not client:
        return
    
    list_devices(client)
    
    print("\nRunning demo...")
    
    # Red on all
    print("1. Setting all to red")
    set_all_devices(client, 255, 0, 0)
    input("Press Enter to continue...")
    
    # Green on first device
    if len(client.devices) > 0:
        print("2. Setting first device to green")
        set_device_color(client, 0, 0, 255, 0)
        input("Press Enter to continue...")
    
    # Rainbow on first device with LEDs
    for i, device in enumerate(client.devices):
        if len(device.leds) > 1:
            print(f"3. Rainbow gradient on {device.name}")
            rainbow_gradient(client, i)
            input("Press Enter to continue...")
            break
    
    # Turn off
    print("4. Turning off all devices")
    turn_off_all(client)
    
    client.disconnect()

# demo()


# Usage: Uncomment any function call above to use it
# Don't forget to disconnect when done:
# if client: client.disconnect()