"""Streamlit UI for RGB lighting control.

Sends commands to the RGB daemon via IPC and displays LED state.
"""

import importlib
import time
import streamlit as st

import src.openrgb_control
import src.openrgb_control.dynamic.dynamic
import src.openrgb_control.static.static
import src.openrgb_control.config

from src.openrgb_control import LEDStateTracker
from src.openrgb_control import ipc
from src.openrgb_control.config import (
    LEDS_PER_RAM_STICK, DEVICE_MAPPING,
    MOTHERBOARD_DEVICE_INDEX, MOTHERBOARD_VISIBLE_LEDS,
)

st.set_page_config(page_title="RGB Control", layout="wide")

# Ordered category list for display
CATEGORY_ORDER = ["Per Stick", "Per LED", "Metrics"]


def _load_profiles():
    """Reload modules and rebuild effect/theme registries."""
    importlib.reload(src.openrgb_control.config)
    importlib.reload(src.openrgb_control.static.static)
    importlib.reload(src.openrgb_control.dynamic.dynamic)
    importlib.reload(src.openrgb_control)

    from src.openrgb_control import THEMES, EFFECTS
    effect_categories = {}
    for name, info in EFFECTS.items():
        cat = info["category"]
        if cat not in effect_categories:
            effect_categories[cat] = {}
        effect_categories[cat][name] = info
    return THEMES, EFFECTS, effect_categories


def _reload_globals():
    global THEMES, EFFECTS, EFFECT_CATEGORIES
    THEMES, EFFECTS, EFFECT_CATEGORIES = _load_profiles()

_reload_globals()


def _render_led_block(label: str, r: int, g: int, b: int):
    """Render a single LED as a colored div."""
    hex_color = f"#{r:02X}{g:02X}{b:02X}"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    text_color = "#000000" if luminance > 128 else "#FFFFFF"
    st.markdown(
        f'<div style="background-color:{hex_color};color:{text_color};'
        f'padding:6px 12px;margin:1px 0;border-radius:3px;'
        f'font-family:monospace;font-size:12px;text-align:center;">'
        f'{label} &nbsp; {hex_color}</div>',
        unsafe_allow_html=True,
    )


def render_devices(tracker: LEDStateTracker):
    """Render the 4 RAM sticks and motherboard as colored LED columns."""
    cols = st.columns([1, 1, 1, 1], gap="large")

    mb_leds = tracker.get_device_leds(MOTHERBOARD_DEVICE_INDEX)

    for stick_pos in range(4):
        device_idx = DEVICE_MAPPING["ram"][stick_pos]
        leds = tracker.get_device_leds(device_idx)

        with cols[stick_pos]:
            st.markdown(
                f'<div style="text-align:center;font-weight:bold;margin-bottom:4px;">ram_{stick_pos}</div>',
                unsafe_allow_html=True,
            )
            for led_idx in range(LEDS_PER_RAM_STICK):
                r, g, b = leds.get(led_idx, (0, 0, 0))
                _render_led_block(f"LED {led_idx}", r, g, b)

            # Motherboard LEDs below stick 3
            if stick_pos == 3:
                st.markdown(
                    '<div style="text-align:center;font-weight:bold;margin-top:8px;margin-bottom:4px;">mobo</div>',
                    unsafe_allow_html=True,
                )
                for led_idx in range(MOTHERBOARD_VISIBLE_LEDS):
                    r, g, b = mb_leds.get(led_idx, (0, 0, 0))
                    _render_led_block(f"MB {led_idx}", r, g, b)


def _get_daemon_state():
    """Read daemon state and determine if an effect is running."""
    state = ipc.read_state()
    if state is None:
        return "offline", "", 0.0, {}
    return (
        state.get("status", "idle"),
        state.get("effect_name", ""),
        state.get("speed", 0.0),
        state.get("leds", {}),
    )


def main():
    tracker = LEDStateTracker()

    # Read daemon state
    daemon_status, daemon_effect, daemon_speed, daemon_leds = _get_daemon_state()
    daemon_running = daemon_status == "running"

    # Populate tracker from daemon's LED state
    if daemon_leds:
        tracker.from_dict(daemon_leds)

    # --- Top: status indicators ---
    if daemon_status == "offline":
        st.warning("Daemon: offline")
    elif daemon_status == "running":
        st.success(f"Daemon: running — {daemon_effect}")
    elif daemon_status == "stopped":
        st.info("Daemon: stopped")
    else:
        st.info(f"Daemon: {daemon_status}")

    # --- Middle: LED visualization ---
    render_devices(tracker)

    # --- Bottom: controls ---
    st.divider()

    ctrl_left, ctrl_right = st.columns(2)

    with ctrl_right:
        mode = st.selectbox("Mode", ["Static", "Per Stick", "Per LED", "Metrics"])

    with ctrl_left:
        if mode == "Static":
            theme_options = list(THEMES.keys())
            selected_theme = st.selectbox("Theme", theme_options, key="theme_select")

            # Auto-apply on selection change
            if "prev_theme" not in st.session_state:
                st.session_state.prev_theme = None
            if selected_theme != st.session_state.prev_theme:
                st.session_state.prev_theme = selected_theme
                ipc.write_command("apply_theme", name=selected_theme)

        elif mode in EFFECT_CATEGORIES:
            category_effects = EFFECT_CATEGORIES[mode]

            effect_options = list(category_effects.keys())
            selected_effect = st.selectbox("Effect", effect_options, key="effect_select")

            effect_info = category_effects[selected_effect]
            speed = 4.0
            if effect_info.get("speed_toggleable", True):
                speed = st.slider("Speed", 0.1, 20.0, 4.0, 0.1,
                                  help="Animation cycle duration in seconds (lower = faster)")

            # Auto-start on selection change
            if "prev_effect" not in st.session_state:
                st.session_state.prev_effect = None
            if selected_effect != st.session_state.prev_effect:
                st.session_state.prev_effect = selected_effect
                ipc.write_command("start_effect", name=selected_effect, speed=speed)

            if st.button("Stop", disabled=not daemon_running):
                ipc.write_command("stop")
                st.session_state.prev_effect = None
                time.sleep(0.5)
                st.rerun()

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reload Profiles"):
            _reload_globals()
            st.success("Profiles reloaded")
            st.rerun()
    with col2:
        if st.button("Blackout"):
            ipc.write_command("blackout")
            st.success("Sent: blackout")
            time.sleep(0.5)
            st.rerun()

    # Auto-refresh when daemon is running (must be last to avoid skipping controls)
    if daemon_running:
        time.sleep(1.0)
        st.rerun()


if __name__ == "__main__":
    main()
