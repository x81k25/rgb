"""Streamlit app tests using AppTest (no hardware needed)."""

from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def mock_openrgb_for_app():
    """Mock OpenRGB client so the app can load without a server."""
    mock_client = MagicMock()
    mock_device = MagicMock()
    mock_device.leds = [MagicMock() for _ in range(12)]
    mock_device.colors = [MagicMock(red=0, green=0, blue=0) for _ in range(12)]
    mock_client.devices = [mock_device] * 5  # 4 RAM + 1 motherboard

    with patch("src.openrgb_control.core.OpenRGBClient", return_value=mock_client), \
         patch("src.openrgb_control.core.get_client", return_value=mock_client):
        from src.openrgb_control.core import get_client
        get_client._instance = mock_client
        yield mock_client
        get_client._instance = None


class TestAppLoads:
    """Test that the Streamlit app renders without errors."""

    def test_app_renders_title(self, mock_openrgb_for_app):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert not at.exception, f"App raised: {at.exception}"
        assert any("RGB Control" in el.value for el in at.title)

    def test_mode_radio_exists(self, mock_openrgb_for_app):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert not at.exception
        radios = at.radio
        assert len(radios) > 0

    def test_blackout_button_exists(self, mock_openrgb_for_app):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert not at.exception
        button_labels = [b.label for b in at.button]
        assert "Blackout" in button_labels

    def test_reload_button_exists(self, mock_openrgb_for_app):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert not at.exception
        button_labels = [b.label for b in at.button]
        assert "Reload Profiles" in button_labels


class TestAppModes:
    """Test switching between modes."""

    def test_static_mode_shows_theme_selector(self, mock_openrgb_for_app):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert not at.exception
        # Default mode is Static, should have a selectbox for themes
        assert len(at.selectbox) > 0

    def test_all_themes_present(self, mock_openrgb_for_app):
        from streamlit.testing.v1 import AppTest
        from src.openrgb_control.static.static import THEMES
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert not at.exception
        theme_select = at.selectbox[0]
        assert len(theme_select.options) == len(THEMES)

    def test_all_effect_categories_have_effects(self, mock_openrgb_for_app):
        from src.openrgb_control.dynamic.dynamic import EFFECTS
        categories = set(info["category"] for info in EFFECTS.values())
        assert "Per Stick" in categories
        assert "Per LED" in categories
        assert "System Monitor" in categories
