"""IPC via JSON files for daemon <-> Streamlit communication.

Command flow:  Streamlit writes command.json → daemon reads and deletes it.
State flow:    Daemon writes state.json → Streamlit reads it.

All writes are atomic (tempfile + os.rename) to prevent partial reads.
"""

import json
import os
import tempfile
import time

IPC_DIR = "/tmp/rgb-daemon"
COMMAND_FILE = os.path.join(IPC_DIR, "command.json")
STATE_FILE = os.path.join(IPC_DIR, "state.json")


def _ensure_dir():
    os.makedirs(IPC_DIR, exist_ok=True)


def _atomic_write(path: str, data: dict):
    """Write JSON atomically via tempfile + rename."""
    _ensure_dir()
    fd, tmp = tempfile.mkstemp(dir=IPC_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(path: str) -> dict | None:
    """Read a JSON file, returning None if missing or corrupt."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# --- Command API (Streamlit → Daemon) ---

def write_command(action: str, **kwargs):
    """Write a command for the daemon to pick up.

    Actions: start_effect, apply_theme, stop, blackout
    """
    cmd = {"action": action, "timestamp": time.time(), **kwargs}
    _atomic_write(COMMAND_FILE, cmd)


def read_command() -> dict | None:
    """Read and consume a pending command (returns None if none)."""
    data = _read_json(COMMAND_FILE)
    if data is not None:
        try:
            os.unlink(COMMAND_FILE)
        except OSError:
            pass
    return data


# --- State API (Daemon → Streamlit) ---

def write_state(status: str, effect_name: str = "", speed: float = 0.0, leds: dict = None):
    """Publish daemon state for Streamlit to read."""
    state = {
        "status": status,
        "effect_name": effect_name,
        "speed": speed,
        "leds": leds or {},
        "timestamp": time.time(),
    }
    _atomic_write(STATE_FILE, state)


def read_state() -> dict | None:
    """Read the current daemon state."""
    return _read_json(STATE_FILE)
