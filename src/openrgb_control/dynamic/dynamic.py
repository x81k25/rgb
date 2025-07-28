"""Dynamic RGB effects for OpenRGB devices."""

import subprocess
import time
import math
from typing import List

from ..core import RGBController, FastRGBController, interpolate_colors, interpolate_color, hex_to_rgb, OPENRGB_PYTHON_AVAILABLE
from ..monitoring import get_memory_usage, get_cpu_usage

try:
    from loguru import logger
except ImportError:
    # Fallback logger
    class FallbackLogger:
        def debug(self, msg): pass
        def info(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): pass
        def success(self, msg): pass
    logger = FallbackLogger()

try:
    from openrgb.utils import RGBColor
except ImportError:
    RGBColor = None


def breathing_effect(color1: str = "000000", color2: str = "00FFFF", duration: float = 4.0) -> None:
    """Breathing effect between two colors."""
    # Try fast controller first
    use_fast = False
    if OPENRGB_PYTHON_AVAILABLE and RGBColor:
        try:
            from openrgb import OpenRGBClient
            client = OpenRGBClient()
            use_fast = True
            logger.info(f"Breathing effect (fast mode): {color1} <-> {color2}")
            logger.info(f"Connected to OpenRGB server with {len(client.devices)} devices")
        except Exception as e:
            logger.error(f"Failed to connect to OpenRGB server: {e}")
            use_fast = False
    
    if not use_fast:
        controller = RGBController()
        logger.info(f"Breathing effect (subprocess mode): {color1} <-> {color2}")
    
    # Reduce steps for faster animation given hardware constraints
    steps = 20  # Fewer steps for faster updates
    colors = interpolate_colors(color1, color2, steps)
    delay = duration / (steps * 2)
    
    try:
        start_time = time.time()
        frame_count = 0
        while True:
            # Fade in
            for color in colors:
                loop_start = time.time()
                
                if use_fast:
                    # Convert hex to RGB
                    r, g, b = hex_to_rgb(color)
                    rgb_color = RGBColor(r, g, b)
                    
                    # Update all devices in one go
                    update_start = time.time()
                    # Update all devices
                    try:
                        for device in client.devices:
                            device.set_color(rgb_color)
                    except Exception as e:
                        print(f"\nError updating devices: {e}")
                    update_time = time.time() - update_start
                    
                    # Print timing info every 10 frames
                    frame_count += 1
                    if frame_count % 10 == 0:
                        print(f"\rFrame {frame_count}: Update time: {update_time*1000:.1f}ms", end="", flush=True)
                else:
                    controller.set_all_color(color)
                
                # Adjust delay based on actual execution time
                elapsed = time.time() - loop_start
                actual_delay = max(0, delay - elapsed)
                if actual_delay > 0:
                    time.sleep(actual_delay)
            
            # Fade out
            for color in reversed(colors):
                loop_start = time.time()
                
                if use_fast:
                    # Convert hex to RGB
                    r, g, b = hex_to_rgb(color)
                    rgb_color = RGBColor(r, g, b)
                    
                    # Update all devices
                    try:
                        for device in client.devices:
                            device.set_color(rgb_color)
                    except Exception as e:
                        print(f"\nError updating devices: {e}")
                else:
                    controller.set_all_color(color)
                
                # Adjust delay based on actual execution time
                elapsed = time.time() - loop_start
                actual_delay = max(0, delay - elapsed)
                if actual_delay > 0:
                    time.sleep(actual_delay)
    except KeyboardInterrupt:
        logger.info("Stopped")
        if use_fast and client:
            client.disconnect()


def wave_effect(colors: List[str] = None, speed: float = 0.1) -> None:
    """Wave effect cycling through colors on different devices."""
    if colors is None:
        colors = ["0000FF", "0033FF", "0066FF", "0099FF", "00CCFF", "00FFFF"]
    
    controller = RGBController()
    logger.info(f"Wave effect with {len(colors)} colors")
    device_count = 4
    
    try:
        i = 0
        while True:
            for device_id in range(device_count):
                device = controller.get_device(device_id)
                if device:
                    color_index = (i + device_id) % len(colors)
                    device.set_color(colors[color_index])
            time.sleep(speed)
            i = (i + 1) % len(colors)
    except KeyboardInterrupt:
        logger.info("Stopped")


def rainbow_cycle(speed: float = 0.05) -> None:
    """Rainbow effect cycling through spectrum."""
    controller = RGBController()
    logger.info("Rainbow cycle effect")
    try:
        hue = 0
        while True:
            # Convert HSV to RGB (simplified)
            r = int((math.cos(math.radians(hue)) + 1) * 127.5)
            g = int((math.cos(math.radians(hue + 120)) + 1) * 127.5)
            b = int((math.cos(math.radians(hue + 240)) + 1) * 127.5)
            
            color = f"{r:02X}{g:02X}{b:02X}"
            controller.set_all_color(color)
            
            hue = (hue + 2) % 360
            time.sleep(speed)
    except KeyboardInterrupt:
        logger.info("Stopped")


def contrast_cycle(interval: float = 1.0) -> None:
    """High contrast color cycling effect with dramatic color changes."""
    # Socket mode only - fail fast if not available
    try:
        from openrgb import OpenRGBClient
        from openrgb.utils import RGBColor
        client = OpenRGBClient()
        logger.info("High Contrast Cycle - Socket mode only")
        logger.info(f"Connected to {len(client.devices)} devices")
    except ImportError:
        logger.error("openrgb-python not available - socket mode required")
        return
    except Exception as e:
        logger.error(f"Socket connection failed: {e}")
        return
    
    # High contrast colors for dramatic effect
    colors = [
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
    
    logger.info(f"Cycling through {len(colors)} high-contrast colors")
    logger.info("Press Ctrl+C to stop")
    
    # Pre-compute RGB values for socket mode
    rgb_colors = []
    for color in colors:
        r, g, b = hex_to_rgb(color)
        rgb_colors.append(RGBColor(r, g, b))
    
    # Cache device list for faster access
    device_list = list(client.devices)
    logger.info(f"Cached {len(device_list)} devices for high-speed access")
    
    try:
        color_index = 0
        frame_count = 0
        start_time = time.time()
        
        while True:
            loop_start = time.time()
            
            # Socket mode - use pre-computed colors and cached device list
            rgb_color = rgb_colors[color_index]
            
            # Ultra-fast batch update using cached device list
            for device in device_list:
                device.set_color(rgb_color)
            
            # Move to next color
            color_index = (color_index + 1) % len(colors)
            frame_count += 1
            
            # Calculate remaining sleep time
            loop_time = time.time() - loop_start
            remaining_sleep = interval - loop_time
            if remaining_sleep > 0:
                time.sleep(remaining_sleep)
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed if elapsed > 0 else 0
        logger.info(f"Stopped - Average FPS: {avg_fps:.1f}")
        client.disconnect()


def pulse_effect(color: str = "00FFFF", min_brightness: float = 0.1, speed: float = 0.05) -> None:
    """Pulsing effect with varying brightness."""
    controller = RGBController()
    logger.info(f"Pulse effect with color {color}")
    
    # Convert hex to RGB
    r_base = int(color[0:2], 16)
    g_base = int(color[2:4], 16)
    b_base = int(color[4:6], 16)
    
    try:
        angle = 0
        while True:
            brightness = (math.sin(math.radians(angle)) + 1) / 2
            brightness = min_brightness + (1 - min_brightness) * brightness
            
            r = int(r_base * brightness)
            g = int(g_base * brightness)
            b = int(b_base * brightness)
            
            pulse_color = f"{r:02X}{g:02X}{b:02X}"
            controller.set_all_color(pulse_color)
            angle = (angle + 5) % 360
            time.sleep(speed)
    except KeyboardInterrupt:
        logger.info("Stopped")


def breathing_ripple() -> None:
    """Advanced breathing ripple effect across all devices."""
    controller = RGBController()
    
    # Colors
    blue = "0000FF"
    cyan = "00FFFF"
    
    # RAM configuration
    ram_sticks = 4
    leds_per_stick = 12
    
    # Animation parameters
    wave_speed = 0.01
    breathing_period = 0.5
    ripple_delay = 0.02
    
    logger.info("Starting breathing ripple effect (Ctrl+C to stop)")
    logger.info("Blue <-> Cyan breathing with ripple across devices")
    
    try:
        time_start = time.time()
        
        while True:
            elapsed = time.time() - time_start
            
            # Calculate breathing intensity (0.0 to 1.0)
            breath = (math.sin(elapsed * 2 * math.pi / breathing_period) + 1) / 2
            
            # For each RAM stick
            for stick in range(ram_sticks):
                device = controller.get_device(stick)
                if not device or device.led_count is None:
                    continue
                    
                colors = []
                
                # Calculate ripple offset for this stick
                stick_offset = elapsed + (stick * ripple_delay)
                
                # Generate colors for each LED with ripple effect
                for led in range(leds_per_stick):
                    # Create wave pattern across LEDs
                    led_offset = led / leds_per_stick * math.pi
                    
                    # Combine breathing and wave
                    wave = (math.sin(stick_offset + led_offset) + 1) / 2
                    combined = breath * 0.7 + wave * 0.3  # 70% breathing, 30% wave
                    
                    # Interpolate between blue and cyan
                    color = interpolate_color(blue, cyan, combined)
                    colors.append(color)
                
                # Apply colors to this RAM stick
                device.set_colors(colors)
            
            # For other devices, use simple breathing with ripple delays
            delays = {1: 4, 2: 5, 3: 6}
            for device_id, delay_mult in delays.items():
                device = controller.get_device(device_id)
                if device:
                    device_breath = (math.sin((elapsed + ripple_delay * delay_mult) * 2 * math.pi / breathing_period) + 1) / 2
                    device_color = interpolate_color(blue, cyan, device_breath)
                    device.set_color(device_color)
            
            time.sleep(wave_speed)
            
    except KeyboardInterrupt:
        logger.info("Stopped - setting all devices to cyan")
        controller.set_all_color("00FFFF")


def memory_usage_effect(update_interval: float = 0.5) -> None:
    """Display memory usage as LED gradient on RAM sticks.
    
    LEDs light up from bottom to top based on memory usage percentage.
    Each RAM stick shows the same usage level.
    
    Args:
        update_interval: How often to update memory readings (seconds)
    """
    controller = RGBController(skip_detection=True)
    
    # Physical RAM stick positions (left to right) to device mapping
    # RAM stick 0 (leftmost) = Device 1
    # RAM stick 1 = Device 3  
    # RAM stick 2 = Device 0
    # RAM stick 3 (rightmost) = Device 2
    physical_to_device = {0: 1, 1: 3, 2: 0, 3: 2}
    
    # Each RAM stick has 10 LEDs
    leds_per_stick = 10
    
    logger.info("Memory Usage Display - RAM LED gradient")
    logger.info("LEDs light up from bottom to top based on memory usage")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            # Get current memory usage
            memory_percent, memory_used_gb, memory_total_gb = get_memory_usage()
            
            # Calculate how many LEDs should be lit (bottom to top)
            leds_to_light = int((memory_percent / 100.0) * leds_per_stick)
            
            # Use the exact same colors as the status-gradient theme (flipped)
            gradient_colors = [
                "00FFFF",  # LED 0 (bottom) - Cyan
                "00FFFF",  # LED 1 (bottom) - Cyan
                "00FF55",  # LED 2 - Green-Cyan
                "00FF00",  # LED 3 - Pure Green
                "55FF00",  # LED 4 - Green-Yellow
                "AAFF00",  # LED 5 - Yellow-Green
                "FFFF00",  # LED 6 - Yellow
                "FFAA00",  # LED 7 - Orange
                "FF5500",  # LED 8 - Red-Orange
                "FF0000"   # LED 9 (top) - Red
            ]
            
            # Create color array for each stick (LED 0 = bottom, LED 11 = top)
            colors = []
            for led in range(leds_per_stick):
                # Reverse LED order so bottom LEDs light up first
                bottom_up_led = leds_per_stick - 1 - led
                
                if bottom_up_led < leds_to_light:
                    # LED is lit - use the appropriate gradient color
                    color = gradient_colors[bottom_up_led]
                else:
                    # LED is off
                    color = "000000"
                
                colors.append(color)
            
            # Apply colors to all RAM sticks
            for physical_pos in range(4):
                device_id = physical_to_device[physical_pos]
                device = controller.get_device(device_id)
                if device:
                    device.set_colors(colors)
            
            # Skip frequent memory logging to reduce spam
            
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print("\nStopped - clearing RAM LEDs")
        # Turn off all RAM LEDs
        for physical_pos in range(4):
            device_id = physical_to_device[physical_pos]
            device = controller.get_device(device_id)
            if device:
                device.set_color("000000")


def cpu_usage_effect(update_interval: float = 5.0) -> None:
    """Display CPU usage as LED gradient on RAM sticks with fast socket communication.
    
    LEDs light up from bottom to top based on CPU usage percentage.
    Each RAM stick shows the same usage level.
    
    Args:
        update_interval: How often to update CPU readings (seconds) - default 0.1s for responsiveness
    """
    # Socket mode only for maximum performance
    try:
        from openrgb import OpenRGBClient
        from openrgb.utils import RGBColor
        client = OpenRGBClient()
        logger.info("CPU Usage Display - Socket mode (fast)")
        logger.info(f"Connected to {len(client.devices)} devices")
    except ImportError:
        logger.error("openrgb-python not available - socket mode required")
        return
    except Exception as e:
        logger.error(f"Socket connection failed: {e}")
        return
    
    # Physical RAM stick positions (left to right) to device mapping
    # RAM stick 0 (leftmost) = Device 1
    # RAM stick 1 = Device 3  
    # RAM stick 2 = Device 0
    # RAM stick 3 (rightmost) = Device 2
    ram_device_indices = [1, 3, 0, 2]  # Direct device indices
    
    # Cache RAM devices for fast access
    ram_devices = []
    for i in ram_device_indices:
        if i < len(client.devices):
            device = client.devices[i]
            ram_devices.append(device)
            logger.info(f"RAM Device {i}: {device.name} with {len(device.leds)} LEDs")
    
    # Each RAM stick has 10 LEDs
    leds_per_stick = 10
    
    logger.info("CPU Usage Display - RAM LED gradient")
    logger.info("LEDs light up from bottom to top based on CPU usage")
    logger.info(f"Updates every {update_interval:.1f} seconds (matching hardware capabilities)")
    logger.info("Press Ctrl+C to stop")
    
    # Pre-compute gradient colors as RGBColor objects
    gradient_hex = [
        "00FFFF",  # LED 0 (bottom) - Cyan
        "00FFFF",  # LED 1 (bottom) - Cyan
        "00FF55",  # LED 2 - Green-Cyan
        "00FF00",  # LED 3 - Pure Green
        "55FF00",  # LED 4 - Green-Yellow
        "AAFF00",  # LED 5 - Yellow-Green
        "FFFF00",  # LED 6 - Yellow
        "FFAA00",  # LED 7 - Orange
        "FF5500",  # LED 8 - Red-Orange
        "FF0000"   # LED 9 (top) - Red
    ]
    
    gradient_colors = []
    for hex_color in gradient_hex:
        r, g, b = hex_to_rgb(hex_color)
        gradient_colors.append(RGBColor(r, g, b))
    
    # Pre-compute black color for off LEDs
    black = RGBColor(0, 0, 0)
    
    try:
        frame_count = 0
        start_time = time.time()
        logger.info("Starting CPU monitoring loop - Ctrl+C to exit")
        
        while True:
            loop_start = time.time()
            
            # Get CPU usage with very short interval to avoid blocking
            try:
                cpu_percent = get_cpu_usage(0.01)  # 10ms sample instead of None
            except:
                cpu_percent = 0  # Fallback if CPU sampling fails
            
            # Debug: log actual CPU values occasionally
            if frame_count % 50 == 0:
                logger.info(f"Raw CPU: {cpu_percent:.1f}%")
            
            # Calculate how many LEDs should be lit based on CPU usage
            # Map 0-100% CPU to 0-10 LEDs (bottom to top gradient)
            if cpu_percent <= 0:
                leds_to_light = 0
            else:
                # Map 1-100% CPU to 1-10 LEDs
                leds_to_light = min(int((cpu_percent / 10)) + 1, 10)
            
            # Create gradient pattern: LEDs light up from bottom to top
            led_colors = []
            for led in range(leds_per_stick):
                # Reverse LED order so bottom LEDs light up first
                bottom_up_led = leds_per_stick - 1 - led
                
                if bottom_up_led < leds_to_light:
                    # LED is lit - use the appropriate gradient color
                    led_colors.append(gradient_colors[bottom_up_led])
                else:
                    # LED is off
                    led_colors.append(black)
            
            # Apply same gradient pattern to all 4 RAM sticks
            try:
                for ram_device in ram_devices:
                    try:
                        # Set individual LED colors to create gradient
                        for i, color in enumerate(led_colors):
                            if i < len(ram_device.leds):
                                ram_device.leds[i].set_color(color)
                    except Exception as e:
                        # Fallback: set whole device to highest lit color
                        if leds_to_light > 0:
                            fallback_color = gradient_colors[min(leds_to_light-1, len(gradient_colors)-1)]
                            ram_device.set_color(fallback_color)
                        else:
                            ram_device.set_color(black)
                        logger.debug(f"LED gradient failed, using fallback: {e}")
            except KeyboardInterrupt:
                # Re-raise KeyboardInterrupt to ensure proper exit
                raise
            except Exception as e:
                logger.debug(f"Color update failed: {e}")
                pass
            
            frame_count += 1
            
            # Log performance every 50 frames to avoid spam
            if frame_count % 50 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                logger.debug(f"CPU Effect FPS: {fps:.1f} | CPU: {cpu_percent:.1f}% | LEDs: {leds_to_light}")
            
            # Calculate remaining sleep time
            loop_time = time.time() - loop_start
            remaining_sleep = update_interval - loop_time
            
            # Add timeout check - if loop takes longer than expected, something is wrong
            if loop_time > (update_interval * 0.8):  # Loop took more than 80% of interval
                logger.warning(f"Slow loop detected: {loop_time:.3f}s")
            
            if remaining_sleep > 0:
                time.sleep(remaining_sleep)
            elif remaining_sleep < -0.5:  # Loop is way behind schedule
                logger.warning(f"Loop running {-remaining_sleep:.3f}s behind schedule")
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed if elapsed > 0 else 0
        logger.info(f"Stopped - Average FPS: {avg_fps:.1f}")
        
        # Clear all RAM LEDs via socket
        for ram_device in ram_devices:
            try:
                ram_device.set_color(black)
            except:
                pass
        
        client.disconnect()


def system_monitoring_effect(update_interval: float = 5.0) -> None:
    """Combined CPU and Memory usage display on RAM sticks.
    
    RAM sticks 0-1 (leftmost): CPU usage gradient (bottom to top)
    RAM sticks 2-3 (rightmost): Memory usage gradient (bottom to top)
    
    Args:
        update_interval: How often to update readings (seconds) - default 5.0s
    """
    # Socket mode only for maximum performance
    try:
        from openrgb import OpenRGBClient
        from openrgb.utils import RGBColor
        client = OpenRGBClient()
        logger.info("System Monitoring Display - Socket mode (fast)")
        logger.info(f"Connected to {len(client.devices)} devices")
    except ImportError:
        logger.error("openrgb-python not available - socket mode required")
        return
    except Exception as e:
        logger.error(f"Socket connection failed: {e}")
        return
    
    # Physical RAM stick positions to device mapping
    # RAM stick 0 (leftmost) = Device 1 - CPU
    # RAM stick 1 = Device 3 - CPU  
    # RAM stick 2 = Device 0 - Memory
    # RAM stick 3 (rightmost) = Device 2 - Memory
    cpu_device_indices = [1, 3]  # Sticks 0-1 show CPU
    memory_device_indices = [0, 2]  # Sticks 2-3 show Memory
    
    # Cache devices for fast access
    cpu_devices = []
    memory_devices = []
    
    for i in cpu_device_indices:
        if i < len(client.devices):
            device = client.devices[i]
            cpu_devices.append(device)
            logger.info(f"CPU Device {i}: {device.name}")
    
    for i in memory_device_indices:
        if i < len(client.devices):
            device = client.devices[i]
            memory_devices.append(device)
            logger.info(f"Memory Device {i}: {device.name}")
    
    # Each RAM stick has 10 LEDs
    leds_per_stick = 10
    
    logger.info("System Monitoring - CPU (sticks 0-1) + Memory (sticks 2-3)")
    logger.info("LEDs light up from bottom to top based on usage")
    logger.info(f"Updates every {update_interval:.1f} seconds")
    logger.info("Press Ctrl+C to stop")
    
    # Pre-compute gradient colors as RGBColor objects
    # Use same gradient for both CPU and Memory (cyan to red)
    gradient_hex = [
        "00FFFF",  # LED 0 (bottom) - Cyan
        "00FFFF",  # LED 1 (bottom) - Cyan
        "00FF55",  # LED 2 - Green-Cyan
        "00FF00",  # LED 3 - Pure Green
        "55FF00",  # LED 4 - Green-Yellow
        "AAFF00",  # LED 5 - Yellow-Green
        "FFFF00",  # LED 6 - Yellow
        "FFAA00",  # LED 7 - Orange
        "FF5500",  # LED 8 - Red-Orange
        "FF0000"   # LED 9 (top) - Red
    ]
    
    # Convert to RGBColor objects (same gradient for both)
    gradient_colors = []
    for hex_color in gradient_hex:
        r, g, b = hex_to_rgb(hex_color)
        gradient_colors.append(RGBColor(r, g, b))
    
    # Pre-compute black color for off LEDs
    black = RGBColor(0, 0, 0)
    
    try:
        frame_count = 0
        start_time = time.time()
        logger.info("Starting system monitoring loop - Ctrl+C to exit")
        
        while True:
            loop_start = time.time()
            
            # Get system usage with minimal blocking
            try:
                cpu_percent = get_cpu_usage(0.01)  # 10ms sample
                memory_percent, memory_used_gb, memory_total_gb = get_memory_usage()
            except:
                cpu_percent = 0
                memory_percent = 0
            
            # Debug: log actual values occasionally
            if frame_count % 20 == 0:
                logger.info(f"CPU: {cpu_percent:.1f}% | Memory: {memory_percent:.1f}%")
            
            # Calculate LEDs to light for CPU (0-100% -> 0-10 LEDs)
            if cpu_percent <= 0:
                cpu_leds_to_light = 0
            else:
                cpu_leds_to_light = min(int((cpu_percent / 10)) + 1, 10)
            
            # Calculate LEDs to light for Memory (0-100% -> 0-10 LEDs)
            memory_leds_to_light = int((memory_percent / 100.0) * leds_per_stick)
            
            # Create CPU gradient pattern
            cpu_led_colors = []
            for led in range(leds_per_stick):
                bottom_up_led = leds_per_stick - 1 - led
                if bottom_up_led < cpu_leds_to_light:
                    cpu_led_colors.append(gradient_colors[bottom_up_led])
                else:
                    cpu_led_colors.append(black)
            
            # Create Memory gradient pattern
            memory_led_colors = []
            for led in range(leds_per_stick):
                bottom_up_led = leds_per_stick - 1 - led
                if bottom_up_led < memory_leds_to_light:
                    memory_led_colors.append(gradient_colors[bottom_up_led])
                else:
                    memory_led_colors.append(black)
            
            # Apply CPU gradient to sticks 0-1
            try:
                for cpu_device in cpu_devices:
                    try:
                        for i, color in enumerate(cpu_led_colors):
                            if i < len(cpu_device.leds):
                                cpu_device.leds[i].set_color(color)
                    except Exception as e:
                        # Fallback: set whole device to highest lit color
                        if cpu_leds_to_light > 0:
                            fallback_color = gradient_colors[min(cpu_leds_to_light-1, len(gradient_colors)-1)]
                            cpu_device.set_color(fallback_color)
                        else:
                            cpu_device.set_color(black)
                        logger.debug(f"CPU LED gradient failed, using fallback: {e}")
                
                # Apply Memory gradient to sticks 2-3
                for memory_device in memory_devices:
                    try:
                        for i, color in enumerate(memory_led_colors):
                            if i < len(memory_device.leds):
                                memory_device.leds[i].set_color(color)
                    except Exception as e:
                        # Fallback: set whole device to highest lit color
                        if memory_leds_to_light > 0:
                            fallback_color = gradient_colors[min(memory_leds_to_light-1, len(gradient_colors)-1)]
                            memory_device.set_color(fallback_color)
                        else:
                            memory_device.set_color(black)
                        logger.debug(f"Memory LED gradient failed, using fallback: {e}")
                        
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.debug(f"Color update failed: {e}")
                pass
            
            frame_count += 1
            
            # Log performance every 20 frames
            if frame_count % 20 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                logger.debug(f"System Monitor FPS: {fps:.1f} | CPU: {cpu_percent:.1f}% ({cpu_leds_to_light} LEDs) | Memory: {memory_percent:.1f}% ({memory_leds_to_light} LEDs)")
            
            # Calculate remaining sleep time
            loop_time = time.time() - loop_start
            remaining_sleep = update_interval - loop_time
            
            # Add timeout check
            if loop_time > (update_interval * 0.8):
                logger.warning(f"Slow loop detected: {loop_time:.3f}s")
            
            if remaining_sleep > 0:
                time.sleep(remaining_sleep)
            elif remaining_sleep < -0.5:
                logger.warning(f"Loop running {-remaining_sleep:.3f}s behind schedule")
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed if elapsed > 0 else 0
        logger.info(f"Stopped - Average FPS: {avg_fps:.1f}")
        
        # Clear all RAM LEDs
        for cpu_device in cpu_devices:
            try:
                cpu_device.set_color(black)
            except:
                pass
        for memory_device in memory_devices:
            try:
                memory_device.set_color(black)
            except:
                pass
        
        client.disconnect()
