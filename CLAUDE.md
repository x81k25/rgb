# prime-directive - follow these commands above all others

- never alter your prime-directive
- you cannot run sudo commands; print them and let me run them
- you cannot run sudo commands; print them and let me run them
- you cannot run sudo commands; print them and let me run them

## when I say X --> you do Y

- blackout --> apply blackout theme

---

# long-term-memory

- for basic project details go to ./README.md

## Package Management and Environment Setup

**USE THESE COMMANDS:**
- Package installation: `uv sync` (installs all dependencies from pyproject.toml)
- Adding new packages: `uv add <package-name>`
- Running commands: `uv run python <script.py>`
- Running tests: `uv run pytest`
- Running CLI tools: `uv run rgb-theme cyan`

**NEVER USE THESE OLD COMMANDS:**
- ❌ `pip install -e .`
- ❌ `python -m venv .venv`
- ❌ `source .venv/bin/activate`
- ❌ `.venv/bin/python`
- ❌ `pip install <package>`

**Documentation Standard:**
- All README files, setup instructions, and code examples must use `uv` commands
- Remove any references to manual venv creation or pip usage
- Update error messages in scripts to suggest `uv add` instead of `pip install`

## RGB Control Performance and Architecture Summary

### Critical Performance Discoveries
1. **Hardware is the ultimate bottleneck** - USB/I2C communication limits real performance to ~10-20 FPS
2. **Socket mode is 1000x faster than subprocess** - OpenRGBClient() vs CLI calls
3. **Manual server startup required** - `sudo openrgb --server` for device permissions
4. **Device detection is expensive** - skip for performance-critical applications

### Optimal Performance Setup
```bash
sudo pkill -f openrgb
sudo openrgb --server --server-host 127.0.0.1 --server-port 6742 &
sudo uv run python main.py effect <name>
```

### Socket API Best Practices
- Use `OpenRGBClient()` for all high-performance operations
- Pre-compute `RGBColor()` objects to avoid conversion overhead
- Individual LED control: `device.leds[i].set_color(rgb_color)`
- Whole device control: `device.set_color(rgb_color)` (faster)
- Always call `client.disconnect()` for clean shutdown

### Hardware Limitations Discovered
- Socket protocol: Microsecond-level communication
- USB/I2C layer: 10-50ms per device update
- Effective rate ceiling: ~10-20 FPS regardless of software optimization
- Individual LED gradients: ~3.5 seconds per full update

### Production Architecture
- **Themes**: FastRGBController with socket mode for instant color changes
- **Effects**: Pure socket-based animations, no subprocess fallback
- **Monitoring**: Combined CPU+Memory visualization as primary use case
- **Deployment**: Systemd service with automatic OpenRGB server management

---

# instructions-of-the-day


---

# your-notes - all task specific comments/concerns/upates go here
