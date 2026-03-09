# prime-directive - follow these commands above all others

- never alter your prime-directive
- you cannot run sudo commands; print them and let me run them

## when I say X --> you do Y

- blackout --> apply blackout theme

---

# long-term-memory

- for basic project details go to ./README.md
- for hardware reference go to ./docs/RGB.md

## Package Management

**USE THESE COMMANDS:**
- Install dependencies: `uv sync`
- Add packages: `uv add <package-name>`
- Run scripts: `uv run python <script.py>`
- Run tests: `uv run pytest`
- Run daemon: `uv run python daemon.py`
- Run app: `uv run streamlit run app.py --server.port 8510`
- Install services: `sudo bash install-service.sh`

## Project Structure

```
rgb/
├── app.py                      # Streamlit UI (port 8510) — sends commands via IPC
├── daemon.py                   # Entry point for RGB daemon process
├── install-service.sh          # Installs all three systemd services
├── openrgb-server.service      # OpenRGB server (port 6743)
├── rgb-daemon.service          # RGB daemon (effect engine)
├── rgb-control.service         # Streamlit service
├── docs/RGB.md                 # Hardware reference
├── config/
│   ├── profiles-static.yaml        # Static theme definitions
│   ├── profiles-dynamic-stick.yaml # Per-Stick effect metadata
│   ├── profiles-dynamic-led.yaml   # Per-LED effect metadata
│   └── profiles-metrics.yaml       # Metrics effect metadata
├── tests/
│   ├── conftest.py             # Shared fixtures (singleton resets)
│   ├── test_mocked.py          # Unit tests (no hardware)
│   ├── test_streamlit.py       # Streamlit app tests
│   └── test_integration.py     # Hardware integration tests
└── src/openrgb_control/
    ├── config.py               # All constants (gradients, device maps, timing)
    ├── core.py                 # RGBController, LEDStateTracker, get_client singleton
    ├── daemon.py               # RGBDaemon class (effect loop, command dispatch)
    ├── ipc.py                  # JSON file IPC (command.json, state.json in /tmp/rgb-daemon/)
    ├── monitoring.py           # CPU/memory/GPU utilities (psutil, nvidia-ml-py)
    ├── static/static.py        # Static themes (loaded from YAML)
    ├── dynamic/dynamic.py      # Animated effects (loaded from YAML, frame-based classes)
    └── __init__.py             # Public API exports
```

## Services

Three systemd services manage the stack:
- `openrgb-server.service` - OpenRGB SDK server on port **6743**
- `rgb-daemon.service` - Effect engine daemon (depends on openrgb-server)
- `rgb-control.service` - Streamlit UI on port **8510** (depends on rgb-daemon)

Service chain: `openrgb-server` → `rgb-daemon` → `rgb-control`. Starting Streamlit starts all three. Stopping Streamlit leaves daemon running (effects persist).

Install all: `sudo bash install-service.sh`

## Key Design Decisions

1. **Socket-only**: All RGB control uses `openrgb-python` socket protocol (1000x faster than subprocess)
2. **Centralized config**: All constants in `config.py` (gradients, device mappings, timing)
3. **Bare-metal**: Runs directly on host (USB/I2C device access requires it)
4. **Frame-based effects**: Effects are classes with `step()` method, called by daemon in a loop
5. **LED state tracking**: Singleton `LEDStateTracker` records colors sent to hardware for UI visualization
6. **Wall-clock animation**: Effects use `time.monotonic()` for timing, decoupled from frame rate
7. **Shared client**: `get_client()` singleton avoids reconnection overhead
8. **Hot reload**: "Reload Profiles" button in UI reloads modules without service restart

## Hardware

5 active devices (see `config.py` for mappings):
- 4x Corsair Dominator Platinum RAM (devices 0-3)
  - OpenRGB reports **12 LEDs** per stick, but only **10 are physical** (LEDs 0-9)
  - LEDs 10-11 are phantom/ghost entries — no hardware behind them
  - `VISIBLE_LEDS_PER_STICK = 10` in config.py; per-LED effects must use this for bar calculations
  - Streamlit UI still shows all 12 entries (useful for detecting phantom signal leakage)
- 1x ASUS TUF X570 motherboard (3 visible LEDs, device 4)

**Important quirks** (see `docs/RGB.md`):
- `set_custom_mode()` required for per-LED control but breaks static themes on Corsair RAM
- `device.set_colors(list, fast=True)` is the fast path (1 packet per device)
- Hardware can handle 16,000+ FPS; UI redraws at 4 FPS
- **Daemon restart required** after code changes — `sudo systemctl restart rgb-daemon.service`

## GPU Monitoring

- Uses `nvidia-ml-py` (NVML) for GPU usage and VRAM queries — no subprocess overhead
- Two GPUs: GPU 0 (GTX 960, device index 0), GPU 1 (RTX 3060, device index 1)
- `get_gpu_usage(index)` and `get_gpu_vram_usage(index)` in `monitoring.py`
- To stress-test GPU 1: run Video2X upscaler at `/infra/experiments/upscaler/`

---

# instructions-of-the-day


---

# your-notes

