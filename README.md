# OpenRGB Control

High-performance Python package for controlling RGB lighting devices on Linux using OpenRGB.

## Features

- **Fast Socket Communication**: Uses `openrgb-python` for high-speed device control
- **Static Color Themes**: Predefined color schemes (cyan, blue, ocean, wave, blackout)
- **Dynamic Effects**: Animated lighting effects (breathing, rainbow, pulse, ripple)
- **CLI Tools**: Command-line utilities for easy RGB control
- **Fallback Support**: Automatic fallback to subprocess calls if socket fails

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd rgb

# Install using uv (recommended)
uv sync
```

### Basic Usage

```bash
# Using uv run (automatically manages environment)
uv run python main.py theme cyan
uv run python main.py theme blackout
uv run python main.py theme ocean

# Dynamic effects with uv
uv run python main.py effect breathing
uv run python main.py effect rainbow
```

### Using Installed Commands

After installation with `uv sync`, you can use the CLI commands:

```bash
# With uv run
uv run rgb-theme cyan
uv run rgb-theme blackout
uv run rgb-effects breathing
uv run rgb-effects rainbow
```

## Performance

This package provides two control methods:

1. **Fast Socket Mode** (default): Uses `openrgb-python` for direct socket communication
2. **Subprocess Fallback**: Falls back to OpenRGB CLI calls if socket fails

### Performance Characteristics
- **Socket Mode**: Can achieve 375,000+ FPS when uncapped, but limited by hardware to ~10-20 FPS
- **Hardware Bottleneck**: USB/I2C communication with RGB devices is the limiting factor
- **Individual LED Control**: Takes ~3.5 seconds per gradient update due to hardware limitations
- **Optimal Update Intervals**: 0.1s for simple color changes, 5s for complex gradient patterns
- **OpenRGB Server**: Runs on port 6742 using socket protocol (not HTTP REST API)

## Available Themes & Effects

### Static Themes
- `cyan` - Solid cyan for all devices
- `blue` - Solid blue for all devices
- `ocean` - Multi-color ocean theme with device-specific blues
- `wave` - Blue gradient wave across devices
- `blackout` - Turn off all lights

### Dynamic Effects
- `breathing` - Smooth breathing effect
- `rainbow` - Rainbow color cycle
- `pulse` - Pulsing effect
- `wave` - Wave animation
- `ocean` - Ocean breathing effect
- `ripple` - Advanced breathing ripple
- `memory` - Memory usage visualization on RAM sticks
- `cpu` - CPU usage visualization on RAM sticks
- `contrast` - High-contrast color cycling (dramatic effect)
- `system` - Combined CPU + Memory monitoring (sticks 0-1: CPU, sticks 2-3: Memory)

## Architecture

The project uses a modular architecture:

```
src/openrgb_control/
├── core.py          # Device controllers (RGBController, FastRGBController)
├── static/          # Static color themes
├── dynamic/         # Animated effects
└── cli.py           # Command-line interfaces
```

### Device Support

Configured for 8 RGB devices via OpenRGB:
- 4x Corsair RAM sticks (12 LEDs each)
- ASUS motherboard controller
- ASUS mouse
- Logitech keyboard
- Additional peripherals

## Development

### Testing

```bash
# Run tests with uv
uv run pytest
uv run pytest -v
uv run pytest tests/test_effects.py::TestStaticThemes
```

### Adding New Themes

1. Add theme definition to `THEMES` dict in `src/openrgb_control/static/static.py`
2. Test with `uv run python main.py theme <name>`

### Adding New Effects

1. Create effect function in `src/openrgb_control/dynamic/dynamic.py`
2. Add to `EFFECTS` dict
3. Test with `uv run python main.py effect <name>`

## Technical Details

For detailed technical information about device configuration, RGB indexing conventions, and advanced usage, see [RGB.md](RGB.md).

## Requirements

- Linux with OpenRGB installed and configured
- Python 3.8+
- OpenRGB server running on port 6742
- uv for package management

## Setup

1. Install OpenRGB and ensure devices are detected
2. Run permissions setup: `sudo bash scripts/setup/fix-openrgb-permissions.sh`
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Start OpenRGB server: `sudo openrgb --server`
5. Test: `sudo uv run python main.py theme cyan`

## Production Deployment

For always-on system monitoring, use the included systemd service:

```bash
# Install service
sudo cp scripts/rgb-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rgb-monitor
sudo systemctl start rgb-monitor

# Check status
sudo systemctl status rgb-monitor
sudo journalctl -u rgb-monitor -f
```

The service automatically starts the OpenRGB server and runs the system monitoring effect on boot.

## Dependencies

The project uses `pyproject.toml` for dependency management. Key dependencies:
- `openrgb-python`: For fast socket-based RGB control
- `click`: CLI framework
- `loguru`: Advanced logging
- `psutil`: System monitoring (for memory/CPU effects)

All dependencies are automatically installed with `uv sync`.

## License

[License information]