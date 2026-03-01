# OpenRGB Control

RGB lighting control for Linux using OpenRGB with a Streamlit web UI.

## Features

- **Streamlit UI**: Real-time LED visualization and control at `http://localhost:8510`
- **Static themes**: Solid colors (cyan, blue, red, green, white, blackout) and gradients
- **Per-stick effects**: Breathing, rainbow, pulse, wave, contrast — each stick phase-offset
- **Per-LED effects**: Ocean wave and ocean breath with individual LED animation
- **System monitoring**: CPU and memory usage visualization on RAM sticks
- **Hot reload**: Update effects without restarting the service

## Quick Start

### As systemd services (recommended)

```bash
uv sync
sudo bash install-service.sh
# Access the UI at http://localhost:8510
```

### Manual

```bash
uv sync
sudo openrgb --server --server-port 6743
uv run streamlit run app.py --server.port 8510
```

## Themes

| Theme | Description |
|-------|-------------|
| `cyan` | Solid cyan |
| `blue` | Solid blue |
| `red` | Solid red |
| `green` | Solid green |
| `white` | Solid white |
| `status-gradient` | Cyan to red gradient |
| `blackout` | All lights off |

## Effects

### Per Stick
| Effect | Description |
|--------|-------------|
| `simple-breathing` | Solid blue fade expanding from center sticks outward |
| `breathing` | Cyan fade rolling L→R across sticks |
| `rainbow` | Hue spread across sticks, rotating through spectrum |
| `pulse` | Brightness wave rolling across sticks |
| `wave` | Color palette cycling with per-stick offset |
| `contrast` | Each stick on a different high-contrast color |

### Per LED
| Effect | Description |
|--------|-------------|
| `heartbeat` | Blue moving band expanding from top center with multi-stutter |
| `ocean-wave` | Blue-cyan wave animating per LED |
| `ocean-breath` | Gentle ocean breathing gradient per LED |

### System Monitor
| Effect | Description |
|--------|-------------|
| `cpu` | CPU usage on all RAM sticks |
| `memory` | Memory usage on all RAM sticks |
| `system` | CPU (right sticks) + Memory (left sticks) |
| `breathing-metrics` | Heartbeat overlay on CPU + Memory |

## Hardware

- 4x Corsair Dominator Platinum RAM (12 LEDs each)
- 1x ASUS TUF GAMING X570-PRO motherboard (3 visible LEDs)

Device mappings are in `src/openrgb_control/config.py`. Hardware details in `docs/RGB.md`.

## Service Management

```bash
sudo systemctl status openrgb-server rgb-control
sudo systemctl restart rgb-control
sudo journalctl -u rgb-control -f
sudo systemctl stop rgb-control openrgb-server
```

## Development

```bash
uv sync
uv run pytest                # all tests (mocked + streamlit)
uv run pytest -v             # verbose
uv run streamlit run app.py --server.port 8510
```

## Dependencies

- `openrgb-python`: Socket communication with OpenRGB
- `psutil`: System monitoring
- `streamlit`: Web UI
- `loguru`: Logging
