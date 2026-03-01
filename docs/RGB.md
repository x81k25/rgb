# RGB Hardware Reference

## Detected Devices

### Corsair Dominator Platinum RAM (x4)
- **Type**: DDR4 RGB memory modules (CMH128GX4M4E3200C16)
- **Bus**: I2C (i2c-0)
- **I2C Addresses**: 0x58, 0x59, 0x5a, 0x5b
- **LEDs per stick**: 12
- **OpenRGB device indices**: 0, 1, 2, 3

#### Physical Position Mapping (Left to Right)

| Physical Position | OpenRGB Device Index | I2C Address |
|:-:|:-:|:-:|
| 0 (leftmost) | 1 | 0x59 |
| 1 | 3 | 0x5B |
| 2 | 0 | 0x58 |
| 3 (rightmost) | 2 | 0x5A |

> **Convention**: "Stick X" always refers to physical position (0-3, left to right), not the OpenRGB device index.

### ASUS TUF GAMING X570-PRO (WI-FI) Motherboard
- **Type**: Motherboard RGB (ASUS Aura)
- **Bus**: USB (ID 0b05:1939)
- **LEDs**: 5 total (3 visible onboard + 2 RGB headers, unplugged)
- **OpenRGB device index**: 4
- **Physical location**: Below Stick 3 (rightmost RAM stick) — treated as a vertical extension of Stick 3 in per-LED effects
- **LED index inversion**: OpenRGB LED 0 is physically at the **top** (nearest RAM), LED 2 is at the **bottom**. Per-LED effects reverse the mapping so the wave flows top→bottom correctly.

### Disconnected Devices (not currently in use)
- **ASUS ROG SPATHA X** (ID 0b05:1979) — RGB gaming mouse
- **Logitech G910 Orion Spark** (ID 046d:c32b) — RGB mechanical keyboard

## OpenRGB Setup

### Prerequisites

1. **Udev rules**: Installed at `/usr/lib/udev/rules.d/60-openrgb.rules`
2. **I2C kernel modules**:
   ```bash
   sudo modprobe i2c_dev
   sudo modprobe i2c-piix4
   ```
3. **Permissions**: Run `sudo bash fix-openrgb-permissions.sh` (one-time)

### Server

OpenRGB runs as a systemd service on port **6743**:
```bash
sudo bash install-service.sh   # install and start
sudo systemctl status openrgb-server
```

### Control Modes

| Mode | OpenRGB API | Notes |
|------|-------------|-------|
| Uniform color | `device.set_color(color)` | Sets all LEDs on a device to one color |
| Per-LED batch | `device.set_colors(list, fast=True)` | 1 packet per device (fast path) |
| Per-LED individual | `device.leds[i].set_color()` | 1 packet per LED (slow, avoid) |

**Important quirks:**
- `device.set_custom_mode()` is required before per-LED control works
- `set_custom_mode()` causes Corsair RAM to enter firmware gradient mode — do NOT use for static/uniform themes
- `fast=True` skips the `device.update()` round-trip (major performance gain)

## Waveforms

### Standard Sine (used by most effects)

```
Brightness
1.0 │      ╭──────╮
    │    ╭─╯      ╰─╮
    │  ╭─╯            ╰─╮
    │╭─╯                ╰─╮
0.0 │╯                    ╰──
    └──────────────────────────
    0%        50%        100%   (cycle position)
```

### Multi-Stutter Sine (simple-breathing & heartbeat effects)

Smooth sine with 1-4 randomized sharp dips per cycle, creating an organic
heartbeat rhythm. Each cycle re-randomizes the number, position, intensity,
and width of every stutter — never repeats the same pattern twice.

```
Brightness
1.0 │      ╭──╮              ╭─╮
    │    ╭─╯  │ ╭╮         ╭─╯ │╭╮  ╭╮
    │  ╭─╯    ╰─╯╰─╮     ╭╯   ╰╯╰──╯╰─╮
    │╭─╯              ╰─╮╭╯              ╰─╮
0.0 │╯                  ╰╯                ╰──
    └──────────────────────────────────────────
         cycle 1                cycle 2
         1 stutter @55%         2 stutters @35%,70%
```

Parameters (randomized per cycle):
- `_STUTTER_COUNT_MIN/MAX` — how many dips per cycle (1-3 for simple-breathing, 1-4 for heartbeat)
- `_STUTTER_POS_MIN/MAX` — range for dip placement within the cycle
- `_STUTTER_DIP_MIN/MAX` — range for dip depth (fraction of brightness)
- `_STUTTER_WIDTH_MIN/MAX` — range for dip width (fraction of cycle)

## Performance

- Hardware can handle 16,000+ FPS
- `device.set_colors(list, fast=True)`: ~0.1ms per device
- CPU sampling interval: 10ms (`psutil.cpu_percent(interval=0.01)`)
- End-to-end latency (CPU change → LED update): ~15-20ms
