"""Static RGB color themes."""

from ..core import RGBController, FastRGBController, OPENRGB_PYTHON_AVAILABLE


THEMES = {
    "cyan": {
        "colors": ["00FFFF"],
        "description": "Solid cyan for all devices"
    },
    "blue": {
        "colors": ["0000FF"],
        "description": "Solid blue for all devices"
    },
    "ocean": {
        "device_colors": {
            0: "1E90FF",  # Corsair RAM: Dodger Blue
            1: "00CED1",  # ASUS Aura: Dark Turquoise
            2: "00FFFF",  # ASUS Mouse: Cyan
            3: "4169E1",  # Logitech Keyboard: Royal Blue
        },
        "description": "Ocean theme with different blues and cyans per device"
    },
    "wave": {
        "colors": ["0000FF", "0033FF", "0066FF", "0099FF", "00CCFF", "00FFFF"],
        "description": "Blue gradient wave across all devices"
    },
    "status-gradient": {
        "mode": "explicit_colors",
        "led_colors": [
            "FF0000",  # LED 0 (top) - Red
            "FF5500",  # LED 1 - Red-Orange
            "FFAA00",  # LED 2 - Orange
            "FFFF00",  # LED 3 - Yellow
            "AAFF00",  # LED 4 - Yellow-Green
            "55FF00",  # LED 5 - Green-Yellow
            "00FF00",  # LED 6 - Pure Green
            "00FF55",  # LED 7 - Green-Cyan
            "00FFFF",  # LED 8 - Cyan
            "00FFFF"   # LED 9 (bottom) - Cyan
        ],
        "description": "10-LED explicit gradient: red → orange → yellow → green → cyan (bottom to top)"
    },
    "blackout": {
        "mode": "off",
        "description": "All lights off (blackout)"
    }
}


def apply_theme(theme_name: str) -> None:
    """Apply a color theme to all RGB devices."""
    if theme_name not in THEMES:
        available = ", ".join(THEMES.keys())
        raise ValueError(f"Unknown theme '{theme_name}'. Available: {available}")
    
    theme = THEMES[theme_name]
    
    # Use fast controller for simple single-color themes
    if "colors" in theme and len(theme["colors"]) == 1 and OPENRGB_PYTHON_AVAILABLE:
        try:
            fast_controller = FastRGBController()
            fast_controller.set_all_color(theme["colors"][0])
            print(f"Applied theme '{theme_name}': {theme['description']}")
            return
        except Exception:
            pass  # Fall back to slow controller
    
    if "mode" in theme and theme["mode"] == "off" and OPENRGB_PYTHON_AVAILABLE:
        try:
            fast_controller = FastRGBController()
            fast_controller.blackout_all()
            print(f"Applied theme '{theme_name}': {theme['description']}")
            return
        except Exception:
            pass  # Fall back to slow controller
    
    # Fall back to slow controller for complex themes
    controller = RGBController(skip_detection=True)
    
    if "mode" in theme:
        mode = theme["mode"]
        if mode == "multi_gradient":
            # Create multi-color gradient across all LEDs for RAM sticks
            from ..core import interpolate_color
            gradient_colors_def = theme["gradient_colors"]
            
            # Generate 12 colors interpolating through all gradient colors
            gradient_colors = []
            num_leds = 12
            num_segments = len(gradient_colors_def) - 1
            
            for i in range(num_leds):
                # Calculate position (0.0 to 1.0) across entire gradient
                t = i / (num_leds - 1)
                
                # Find which segment we're in
                segment_t = t * num_segments
                segment_index = int(segment_t)
                local_t = segment_t - segment_index
                
                # Handle edge case
                if segment_index >= num_segments:
                    segment_index = num_segments - 1
                    local_t = 1.0
                
                # Interpolate between the two colors in this segment
                color1 = gradient_colors_def[segment_index]
                color2 = gradient_colors_def[segment_index + 1]
                interpolated_color = interpolate_color(color1, color2, local_t)
                gradient_colors.append(interpolated_color)
            
            # Apply to RAM sticks only (devices 0-3)
            for device_id in range(4):
                device = controller.get_device(device_id)
                if device and device.led_count == 12:
                    device.set_colors(gradient_colors)
            
            # Set other devices to first color (cyan)
            for device_id in range(4, 8):
                device = controller.get_device(device_id)
                if device:
                    device.set_color(gradient_colors_def[0])
        elif mode == "explicit_colors":
            # Use explicitly defined LED colors
            led_colors = theme["led_colors"]
            
            # Apply to RAM sticks only (devices 0-3)
            for device_id in range(4):
                device = controller.get_device(device_id)
                if device and device.led_count == 10:
                    device.set_colors(led_colors)
            
            # Set other devices to last color (cyan)
            for device_id in range(4, 8):
                device = controller.get_device(device_id)
                if device:
                    device.set_color(led_colors[-1])  # Cyan
        elif mode == "off":
            # Blackout all devices
            controller.set_all_color("000000")
    elif "device_colors" in theme:
        # Per-device colors
        for device_id, color in theme["device_colors"].items():
            device = controller.get_device(device_id)
            if device:
                device.set_color(color)
    elif "colors" in theme:
        colors = theme["colors"]
        if len(colors) == 1:
            # Single color for all devices
            controller.set_all_color(colors[0])
        else:
            # Multiple colors as gradient
            color_string = ",".join(colors)
            controller.set_all_color(color_string)
    
    print(f"Applied theme '{theme_name}': {theme['description']}")
