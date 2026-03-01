"""Streamlit UI for RGB lighting control."""

import importlib
import time
import streamlit as st

import src.openrgb_control
import src.openrgb_control.dynamic.dynamic
import src.openrgb_control.static.static
import src.openrgb_control.config

from src.openrgb_control import LEDStateTracker
from src.openrgb_control.config import (
    LEDS_PER_RAM_STICK, DEVICE_MAPPING,
    MOTHERBOARD_DEVICE_INDEX, MOTHERBOARD_VISIBLE_LEDS,
)

st.set_page_config(page_title="RGB Control", layout="wide")

# Ordered category list for display
CATEGORY_ORDER = ["Per Stick", "Per LED", "System Monitor"]


def _load_profiles():
    """Reload modules and rebuild effect/theme registries."""
    importlib.reload(src.openrgb_control.config)
    importlib.reload(src.openrgb_control.static.static)
    importlib.reload(src.openrgb_control.dynamic.dynamic)
    importlib.reload(src.openrgb_control)

    from src.openrgb_control import THEMES, EFFECTS
    from src.openrgb_control.static.static import apply_theme as _apply_theme
    global apply_theme
    apply_theme = _apply_theme
    effect_categories = {}
    for name, info in EFFECTS.items():
        cat = info["category"]
        if cat not in effect_categories:
            effect_categories[cat] = {}
        effect_categories[cat][name] = info
    return THEMES, EFFECTS, effect_categories


def _reload_globals():
    global THEMES, EFFECTS, EFFECT_CATEGORIES, apply_theme
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
    """Render the 4 RAM sticks and motherboard as colored LED columns.

    Motherboard LEDs are shown below Stick 3 as a physical extension.
    """
    cols = st.columns([1, 1, 1, 1], gap="large")

    mb_leds = tracker.get_device_leds(MOTHERBOARD_DEVICE_INDEX)

    for stick_pos in range(4):
        device_idx = DEVICE_MAPPING["ram"][stick_pos]
        leds = tracker.get_device_leds(device_idx)

        with cols[stick_pos]:
            st.markdown(f"**Stick {stick_pos}**")
            for led_idx in range(LEDS_PER_RAM_STICK):
                r, g, b = leds.get(led_idx, (0, 0, 0))
                _render_led_block(f"LED {led_idx}", r, g, b)

            # Motherboard LEDs below stick 3
            if stick_pos == 3:
                st.markdown("**Motherboard**")
                for led_idx in range(MOTHERBOARD_VISIBLE_LEDS):
                    r, g, b = mb_leds.get(led_idx, (0, 0, 0))
                    _render_led_block(f"MB {led_idx}", r, g, b)


def main():
    st.title("RGB Control")

    tracker = LEDStateTracker()

    # Sidebar controls
    with st.sidebar:
        st.header("Controls")

        mode = st.radio("Mode", ["Static", "Per Stick", "Per LED", "System Monitor"])

        if mode == "Static":
            st.caption("Apply a fixed color to all devices")
            theme_options = list(THEMES.keys())
            selected_theme = st.selectbox(
                "Theme",
                theme_options,
                format_func=lambda t: f"{t} - {THEMES[t]['description']}"
            )

            if st.button("Apply Theme", type="primary"):
                try:
                    apply_theme(selected_theme)
                    st.success(f"Applied: {selected_theme}")
                except Exception as e:
                    st.error(f"Error: {e}")

        elif mode in EFFECT_CATEGORIES:
            category_effects = EFFECT_CATEGORIES[mode]

            if mode == "Per Stick":
                st.caption("Animate entire sticks with one color each")
            elif mode == "Per LED":
                st.caption("Animate individual LEDs independently")
            elif mode == "System Monitor":
                st.caption("Visualize live CPU/memory usage on LEDs")

            effect_options = list(category_effects.keys())
            selected_effect = st.selectbox(
                "Effect",
                effect_options,
                format_func=lambda e: f"{e} - {category_effects[e]['description']}"
            )

            speed = st.slider("Speed", 0.1, 20.0, 4.0, 0.1,
                              help="Animation cycle duration in seconds (lower = faster)")

            if "running" not in st.session_state:
                st.session_state.running = False

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start", type="primary", disabled=st.session_state.running):
                    st.session_state.running = True
                    st.session_state.effect_name = selected_effect
                    st.session_state.effect_speed = speed
                    st.rerun()
            with col2:
                if st.button("Stop", disabled=not st.session_state.running):
                    st.session_state.running = False
                    st.rerun()

        st.divider()
        if st.button("Reload Profiles"):
            _reload_globals()
            st.success("Profiles reloaded")
            st.rerun()

        if st.button("Blackout"):
            try:
                apply_theme("blackout")
                st.session_state.running = False
                st.success("All lights off")
            except Exception as e:
                st.error(f"Error: {e}")

    # Main area: RAM stick visualization
    viz_container = st.empty()

    if st.session_state.get("running"):
        effect_cls = EFFECTS[st.session_state.effect_name]["class"]
        try:
            effect = effect_cls()
            effect.cycle_duration = st.session_state.effect_speed

            # UI refresh is slow (~100ms); update hardware every frame,
            # but only redraw the visualization periodically
            UI_REFRESH_INTERVAL = 0.25  # seconds between UI redraws
            last_ui_update = 0

            while st.session_state.get("running"):
                effect.step()
                now = time.time()
                if now - last_ui_update >= UI_REFRESH_INTERVAL:
                    with viz_container.container():
                        render_devices(tracker)
                    last_ui_update = now
                time.sleep(0.005)  # ~200 FPS max, hardware can handle it

        except Exception as e:
            st.error(f"Effect error: {e}")
            st.session_state.running = False
        finally:
            if 'effect' in dir():
                try:
                    effect.cleanup()
                except Exception:
                    pass
    else:
        with viz_container.container():
            render_devices(tracker)


if __name__ == "__main__":
    main()
