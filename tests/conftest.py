"""Shared test configuration."""

import pytest
from src.openrgb_control.core import get_client, LEDStateTracker


@pytest.fixture(autouse=True)
def reset_led_tracker():
    """Reset LED tracker between tests to prevent state leakage."""
    if LEDStateTracker._instance is not None:
        LEDStateTracker._instance._state.clear()
        LEDStateTracker._instance = None
    yield
    if LEDStateTracker._instance is not None:
        LEDStateTracker._instance._state.clear()
        LEDStateTracker._instance = None
