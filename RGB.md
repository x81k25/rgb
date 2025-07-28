# RGB Device Configuration and Control

## Detected RGB Devices

### 1. ASUS AURA LED Controller (ID 0b05:1939)
- Type: Motherboard RGB controller
- Bus: USB
- Control method: ASUS Aura SDK/OpenRGB

### 2. ASUS ROG SPATHA X (ID 0b05:1979)
- Type: RGB gaming mouse
- Bus: USB
- Control method: ASUS Armoury Crate/OpenRGB

### 3. Logitech G910 Orion Spark (ID 046d:c32b)
- Type: RGB mechanical keyboard
- Bus: USB
- Control method: Logitech G HUB/OpenRGB/g810-led

### 4. Corsair Vengeance RAM (CMH128GX4M4E3200C16)
- Type: 4x RGB memory modules
- Bus: i2c-0
- Addresses: 0x58, 0x59, 0x5a, 0x5b
- Control method: Corsair iCUE/OpenRGB/liquidctl

#### RAM Stick Physical Mapping (Left to Right)
- **Physical Position 0** (leftmost): Device 1 (I2C address 0x59)
- **Physical Position 1**: Device 3 (I2C address 0x5B) 
- **Physical Position 2**: Device 0 (I2C address 0x58)
- **Physical Position 3** (rightmost): Device 2 (I2C address 0x5A)

> **IMPORTANT INDEXING CONVENTION**: When referring to "RAM stick X" in this documentation, X refers to the PHYSICAL position index (0-3, left to right), NOT the OpenRGB device index. For example, "RAM stick 1" means the second stick from the left, which is controlled by OpenRGB Device 3.

## RGB Control Tools for Linux

### OpenRGB
Universal RGB control software supporting multiple manufacturers.

### Device-Specific Tools
- **ASUS**: aura-cli, rogauracore
- **Logitech**: g810-led, keyleds
- **Corsair**: ckb-next, liquidctl

## Color Schemes

### Cyan and Blue Theme
- Primary: #00FFFF (Cyan)
- Secondary: #0000FF (Blue)
- Accent variations:
  - #00BFFF (Deep Sky Blue)
  - #00CED1 (Dark Turquoise)
  - #4169E1 (Royal Blue)
  - #1E90FF (Dodger Blue)

## RGB Control Setup - TESTED AND WORKING

### OpenRGB Configuration

**Setup completed successfully!** OpenRGB is now working without sudo.

1. **Udev rules**: Already installed at `/usr/lib/udev/rules.d/60-openrgb.rules`

2. **i2c kernel modules**: Both modules loaded successfully
   ```bash
   sudo modprobe i2c_dev
   sudo modprobe i2c-piix4
   ```

3. **Fix permissions** (one-time setup):
   ```bash
   # Run the fix-openrgb-permissions.sh script with sudo
   sudo bash fix-openrgb-permissions.sh
   ```

### Starting OpenRGB Server

For best performance, run OpenRGB in server mode:
```bash
openrgb --server --server-port 6742 > /tmp/openrgb-server.log 2>&1 &
```

### Tested Working Color Commands

#### Static Colors (All Devices)
```bash
# Cyan
openrgb --mode direct --color 00FFFF

# Blue
openrgb --mode direct --color 0000FF

# Blue gradient (deep blue to cyan)
openrgb --mode direct --color 0000FF,0033FF,0066FF,0099FF,00CCFF,00FFFF
```

#### Per-Device Colors
```bash
# Device 0 - Corsair RAM: Dodger Blue
openrgb --device 0 --mode direct --color 1E90FF

# Device 1 - ASUS Aura: Dark Turquoise
openrgb --device 1 --mode direct --color 00CED1

# Device 2 - ASUS Mouse: Cyan
openrgb --device 2 --mode direct --color 00FFFF

# Device 3 - Logitech Keyboard: Royal Blue
openrgb --device 3 --mode direct --color 4169E1
```

### Color Theme Script

Create `rgb-theme.sh` for easy theme switching:
```bash
#!/bin/bash
# RGB theme switcher

case "$1" in
    "cyan")
        openrgb --mode direct --color 00FFFF
        ;;
    "blue")
        openrgb --mode direct --color 0000FF
        ;;
    "ocean")
        # Ocean theme - various blues and cyans
        openrgb --device 0 --mode direct --color 1E90FF
        openrgb --device 1 --mode direct --color 00CED1
        openrgb --device 2 --mode direct --color 00FFFF
        openrgb --device 3 --mode direct --color 4169E1
        ;;
    "wave")
        openrgb --mode direct --color 0000FF,0033FF,0066FF,0099FF,00CCFF,00FFFF
        ;;
    *)
        echo "Usage: $0 {cyan|blue|ocean|wave}"
        ;;
esac
```

### Working Color Palette

- **Cyan**: #00FFFF
- **Blue**: #0000FF
- **Dodger Blue**: #1E90FF
- **Dark Turquoise**: #00CED1
- **Royal Blue**: #4169E1
- **Deep Sky Blue**: #00BFFF

### Dynamic Effects

Since the hardware doesn't support native dynamic modes (breathing, spectrum, etc.), we can create dynamic effects using rapid color changes:

```python
# Example: Simple breathing effect
import subprocess
import time

def breathing():
    brightness = 0
    direction = 1
    while True:
        hex_val = f"{brightness:02X}"
        color = f"00{hex_val}{hex_val}"  # Cyan with varying brightness
        subprocess.run(["openrgb", "--mode", "direct", "--color", color], capture_output=True)
        
        brightness += direction * 5
        if brightness >= 255 or brightness <= 0:
            direction *= -1
        time.sleep(0.05)
```

### Notes

- Only "direct" mode is supported across all devices
- Hardware doesn't support native dynamic modes (breathing, spectrum, rainbow)
- Dynamic effects must be created via software by rapidly changing colors
- Server mode provides better performance and cleaner output
- Device order: 0=Corsair RAM, 1=ASUS Aura, 2=ASUS Mouse, 3=Logitech Keyboard
- For smoother animations, consider using OpenRGB SDK Python bindings instead of CLI