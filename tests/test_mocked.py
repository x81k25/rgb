"""Tests with mocked OpenRGB client to verify correct colors are sent."""

import pytest
from unittest.mock import MagicMock, patch, call
from typing import List, Tuple


class MockRGBColor:
    """Mock RGBColor that captures RGB values."""

    def __init__(self, red: int, green: int, blue: int):
        self.red = red
        self.green = green
        self.blue = blue

    def __eq__(self, other):
        if isinstance(other, MockRGBColor):
            return (self.red, self.green, self.blue) == (other.red, other.green, other.blue)
        return False

    def __repr__(self):
        return f"RGBColor({self.red}, {self.green}, {self.blue})"

    def as_tuple(self) -> Tuple[int, int, int]:
        return (self.red, self.green, self.blue)

    def as_hex(self) -> str:
        return f"{self.red:02X}{self.green:02X}{self.blue:02X}"


class MockLED:
    """Mock LED that records color changes."""

    def __init__(self, index: int):
        self.index = index
        self.color_history: List[MockRGBColor] = []
        self.current_color: MockRGBColor = None

    def set_color(self, color: MockRGBColor):
        self.current_color = color
        self.color_history.append(color)


class MockDevice:
    """Mock RGB device with LEDs."""

    def __init__(self, name: str, num_leds: int = 5):
        self.name = name
        self.leds = [MockLED(i) for i in range(num_leds)]
        self.color_history: List[MockRGBColor] = []
        self.current_color: MockRGBColor = None

    def set_color(self, color: MockRGBColor):
        self.current_color = color
        self.color_history.append(color)


class MockOpenRGBClient:
    """Mock OpenRGB client for testing."""

    def __init__(self, host: str = "localhost", port: int = 6742):
        self.host = host
        self.port = port
        self.devices = [
            MockDevice("RAM Stick 0", num_leds=5),
            MockDevice("RAM Stick 1", num_leds=5),
            MockDevice("RAM Stick 2", num_leds=5),
            MockDevice("RAM Stick 3", num_leds=5),
            MockDevice("Motherboard", num_leds=10),
            MockDevice("Mouse", num_leds=2),
        ]
        self._connected = True

    def disconnect(self):
        self._connected = False


@pytest.fixture
def mock_openrgb():
    """Fixture that patches OpenRGB client and RGBColor."""
    # Reset singleton so each test gets a fresh mock client
    from src.openrgb_control.core import get_client
    get_client._instance = None

    with patch.dict('sys.modules', {
        'openrgb': MagicMock(),
        'openrgb.utils': MagicMock(),
    }):
        with patch('src.openrgb_control.core.OpenRGBClient', MockOpenRGBClient), \
             patch('src.openrgb_control.core.RGBColor', MockRGBColor), \
             patch('src.openrgb_control.core.OPENRGB_AVAILABLE', True), \
             patch('src.openrgb_control.static.static.RGBColor', MockRGBColor), \
             patch('src.openrgb_control.dynamic.dynamic.OpenRGBClient', MockOpenRGBClient), \
             patch('src.openrgb_control.dynamic.dynamic.RGBColor', MockRGBColor):
            yield
    get_client._instance = None


class TestStaticThemesMocked:
    """Test static themes with mocked OpenRGB client."""

    def test_cyan_theme_sends_correct_color(self, mock_openrgb):
        """Verify cyan theme sends RGB(0, 255, 255) to all devices."""
        from src.openrgb_control.core import RGBController

        controller = RGBController()
        controller.set_all_color("00FFFF")

        # All devices should have received cyan
        for device in controller.devices:
            assert device.current_color is not None
            assert device.current_color.as_hex() == "00FFFF", \
                f"Device {device.name} got {device.current_color.as_hex()}, expected 00FFFF"

    def test_blackout_sends_black(self, mock_openrgb):
        """Verify blackout sends RGB(0, 0, 0) to all devices."""
        from src.openrgb_control.core import RGBController

        controller = RGBController()
        controller.blackout()

        for device in controller.devices:
            assert device.current_color.as_hex() == "000000", \
                f"Device {device.name} got {device.current_color.as_hex()}, expected 000000"

    def test_blue_theme_sends_correct_color(self, mock_openrgb):
        """Verify blue theme sends RGB(0, 0, 255) to all devices."""
        from src.openrgb_control.core import RGBController

        controller = RGBController()
        controller.set_all_color("0000FF")

        for device in controller.devices:
            assert device.current_color.as_hex() == "0000FF"

    def test_red_theme_sends_correct_color(self, mock_openrgb):
        """Verify red theme sends RGB(255, 0, 0) to all devices."""
        from src.openrgb_control.core import RGBController

        controller = RGBController()
        controller.set_all_color("FF0000")

        for device in controller.devices:
            assert device.current_color.as_hex() == "FF0000"


class TestColorUtilities:
    """Test color conversion utilities."""

    def test_hex_to_rgb(self, mock_openrgb):
        """Test hex to RGB conversion."""
        from src.openrgb_control.core import hex_to_rgb

        assert hex_to_rgb("00FFFF") == (0, 255, 255)
        assert hex_to_rgb("FF0000") == (255, 0, 0)
        assert hex_to_rgb("000000") == (0, 0, 0)
        assert hex_to_rgb("FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)  # With hash

    def test_rgb_to_hex(self, mock_openrgb):
        """Test RGB to hex conversion."""
        from src.openrgb_control.core import rgb_to_hex

        assert rgb_to_hex(0, 255, 255) == "00FFFF"
        assert rgb_to_hex(255, 0, 0) == "FF0000"
        assert rgb_to_hex(0, 0, 0) == "000000"

    def test_interpolate_colors(self, mock_openrgb):
        """Test color interpolation."""
        from src.openrgb_control.core import interpolate_colors

        # Black to white in 3 steps
        colors = interpolate_colors("000000", "FFFFFF", 3)
        assert len(colors) == 3
        assert colors[0] == "000000"  # Start
        assert colors[-1] == "FFFFFF"  # End
        # Middle should be gray
        assert colors[1] == "7F7F7F" or colors[1] == "808080"  # Allow rounding



class TestBreathingEffectMocked:
    """Test breathing effect color transitions."""

    def test_breathing_precomputes_correct_gradient(self, mock_openrgb):
        """Verify breathing effect creates correct color gradient."""
        from src.openrgb_control.core import interpolate_colors
        from src.openrgb_control.config import DEFAULT_BREATHING_STEPS

        colors = interpolate_colors("000000", "00FFFF", DEFAULT_BREATHING_STEPS)

        # Should have correct number of steps
        assert len(colors) == DEFAULT_BREATHING_STEPS

        # First should be black
        assert colors[0] == "000000"

        # Last should be cyan
        assert colors[-1] == "00FFFF"

        # All should be valid hex colors
        for color in colors:
            assert len(color) == 6
            int(color, 16)  # Should not raise


class TestDeviceColorHistory:
    """Test that we can track color history on mock devices."""

    def test_color_history_tracks_changes(self, mock_openrgb):
        """Verify color history is recorded."""
        from src.openrgb_control.core import RGBController

        controller = RGBController()

        # Apply multiple colors
        controller.set_all_color("FF0000")
        controller.set_all_color("00FF00")
        controller.set_all_color("0000FF")

        # Each device should have 3 colors in history
        for device in controller.devices:
            assert len(device.color_history) == 3
            assert device.color_history[0].as_hex() == "FF0000"
            assert device.color_history[1].as_hex() == "00FF00"
            assert device.color_history[2].as_hex() == "0000FF"


class TestApplyThemeMocked:
    """Test the apply_theme function with mocking."""

    def test_apply_cyan_theme(self, mock_openrgb):
        """Test applying cyan theme via apply_theme function."""
        from src.openrgb_control.static.static import apply_theme, THEMES

        # Capture the controller to inspect devices
        with patch('src.openrgb_control.static.static.RGBController') as MockController:
            mock_instance = MagicMock()
            mock_device = MockDevice("Test", num_leds=5)
            mock_instance.devices = [mock_device]
            MockController.return_value = mock_instance

            apply_theme("cyan")

            # Should have called set_all_color with cyan
            mock_instance.set_all_color.assert_called_once_with("00FFFF")
            mock_instance.disconnect.assert_called_once()

    def test_apply_invalid_theme_raises(self, mock_openrgb):
        """Test that invalid theme raises ValueError."""
        from src.openrgb_control.static.static import apply_theme

        with pytest.raises(ValueError, match="Unknown theme"):
            apply_theme("nonexistent_theme")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
