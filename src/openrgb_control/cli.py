"""Command-line interface for OpenRGB Control."""

import sys
from typing import Optional

from .static import apply_theme, THEMES
from .dynamic import (
    breathing_effect,
    wave_effect,
    rainbow_cycle,
    pulse_effect,
    breathing_ripple,
    memory_usage_effect
)


def theme_main() -> None:
    """Main entry point for rgb-theme command."""
    if len(sys.argv) < 2:
        print("Usage: rgb-theme [theme]")
        print("Available themes:")
        for name, theme in THEMES.items():
            print(f"  {name:<8} - {theme['description']}")
        return
    
    theme_name = sys.argv[1].lower()
    
    try:
        apply_theme(theme_name)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def effects_main() -> None:
    """Main entry point for rgb-effects command."""
    if len(sys.argv) < 2:
        print("Usage: rgb-effects [effect]")
        print("Available effects:")
        print("  breathing - Breathing effect between black and cyan")
        print("  wave      - Wave effect with blue-cyan gradient")
        print("  rainbow   - Rainbow color cycle")
        print("  pulse     - Pulsing cyan effect")
        print("  ocean     - Ocean-themed breathing (blue to cyan)")
        print("  memory    - Memory usage display on RAM sticks")
        return
    
    effect = sys.argv[1].lower()
    
    if effect == "breathing":
        breathing_effect()
    elif effect == "wave":
        wave_effect()
    elif effect == "rainbow":
        rainbow_cycle()
    elif effect == "pulse":
        pulse_effect()
    elif effect == "ocean":
        breathing_effect("0000FF", "00FFFF", 3.0)
    elif effect == "memory":
        memory_usage_effect()
    else:
        print(f"Unknown effect: {effect}")
        sys.exit(1)


def breathing_ripple_main() -> None:
    """Main entry point for rgb-breathing-ripple command."""
    breathing_ripple()


if __name__ == "__main__":
    # For direct script execution
    if len(sys.argv) > 0 and "theme" in sys.argv[0]:
        theme_main()
    elif len(sys.argv) > 0 and "breathing-ripple" in sys.argv[0]:
        breathing_ripple_main()
    else:
        effects_main()
