"""RGB Daemon — runs effects independently of the Streamlit UI.

Single-threaded main loop:
  1. Poll command.json for new commands (~1s)
  2. Step the active effect (~200 FPS)
  3. Write state.json for the UI (~250ms)
"""

import signal
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

from . import ipc
from .core import LEDStateTracker
from .dynamic.dynamic import EFFECTS
from .static.static import apply_theme


class RGBDaemon:
    """Daemon that owns the OpenRGB connection and runs effects."""

    COMMAND_POLL_INTERVAL = 1.0    # seconds between command checks
    STATE_WRITE_INTERVAL = 0.25    # seconds between state publishes
    FRAME_SLEEP = 0.005            # ~200 FPS cap

    def __init__(self):
        self._running = True
        self._effect = None
        self._effect_name = ""
        self._effect_speed = 0.0
        self._tracker = LEDStateTracker()

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        self._running = False

    def _start_effect(self, name: str, speed: float):
        """Stop any running effect and start a new one."""
        self._stop_effect()
        if name not in EFFECTS:
            logger.error(f"Unknown effect: {name}")
            return
        logger.info(f"Starting effect: {name} (speed={speed}s)")
        effect_cls = EFFECTS[name]["class"]
        self._effect = effect_cls()
        self._effect.cycle_duration = speed
        self._effect_name = name
        self._effect_speed = speed

    def _stop_effect(self):
        """Stop the current effect if any."""
        if self._effect is not None:
            try:
                self._effect.cleanup()
            except Exception as e:
                logger.debug(f"Effect cleanup error: {e}")
            self._effect = None
            self._effect_name = ""
            self._effect_speed = 0.0

    def _apply_theme(self, name: str):
        """Apply a static theme (stops any running effect first)."""
        self._stop_effect()
        logger.info(f"Applying theme: {name}")
        apply_theme(name)

    def _handle_command(self, cmd: dict):
        """Dispatch a command dict."""
        action = cmd.get("action")
        if action == "start_effect":
            self._start_effect(cmd.get("name", ""), cmd.get("speed", 4.0))
        elif action == "apply_theme":
            self._apply_theme(cmd.get("name", ""))
        elif action == "stop":
            self._stop_effect()
        elif action == "blackout":
            self._stop_effect()
            apply_theme("blackout")
        else:
            logger.warning(f"Unknown command action: {action}")

    def _publish_state(self):
        """Write current state for Streamlit to read."""
        if self._effect is not None:
            status = "running"
        else:
            status = "idle"
        ipc.write_state(
            status=status,
            effect_name=self._effect_name,
            speed=self._effect_speed,
            leds=self._tracker.to_dict(),
        )

    def run(self):
        """Main daemon loop."""
        logger.info("RGB daemon starting")

        # Resume effect from last state if daemon restarts
        state = ipc.read_state()
        if state and state.get("status") == "running" and state.get("effect_name"):
            try:
                self._start_effect(state["effect_name"], state.get("speed", 4.0))
            except Exception as e:
                logger.error(f"Failed to resume effect: {e}")

        last_command_check = 0.0
        last_state_write = 0.0

        # Publish initial state
        self._publish_state()

        while self._running:
            now = time.monotonic()

            # Poll for commands
            if now - last_command_check >= self.COMMAND_POLL_INTERVAL:
                cmd = ipc.read_command()
                if cmd is not None:
                    try:
                        self._handle_command(cmd)
                    except Exception as e:
                        logger.error(f"Command error: {e}")
                last_command_check = now

            # Step effect
            if self._effect is not None:
                try:
                    self._effect.step()
                except Exception as e:
                    logger.error(f"Effect step error: {e}")
                    self._stop_effect()

            # Publish state
            if now - last_state_write >= self.STATE_WRITE_INTERVAL:
                self._publish_state()
                last_state_write = now

            # Sleep to cap frame rate (only if effect is running)
            if self._effect is not None:
                time.sleep(self.FRAME_SLEEP)
            else:
                # Idle — sleep longer to save CPU
                time.sleep(0.5)

        # Graceful shutdown
        self._stop_effect()
        ipc.write_state(status="stopped")
        logger.info("RGB daemon stopped")
