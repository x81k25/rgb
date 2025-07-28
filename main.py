#!/usr/bin/env python3
"""
Main entry point for OpenRGB Control
Provides a unified interface to run themes and effects
"""

import sys
import argparse
from typing import List, Optional
from pathlib import Path

# Setup logging first
from src.openrgb_control.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

# Add scripts directory to path for server management
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from src.openrgb_control.static import apply_theme, THEMES
from src.openrgb_control.dynamic import (
    breathing_effect,
    wave_effect,
    rainbow_cycle,
    pulse_effect,
    breathing_ripple,
    memory_usage_effect,
    cpu_usage_effect,
    contrast_cycle
)

try:
    from openrgb_server import ensure_openrgb_server, get_server_status
    SERVER_AVAILABLE = True
except ImportError:
    logger.warning("Server management not available - openrgb_server module not found")
    SERVER_AVAILABLE = False


def list_themes() -> None:
    """List available themes."""
    logger.info("Available themes:")
    for name, theme in THEMES.items():
        logger.info(f"  {name:<8} - {theme['description']}")


def list_effects() -> None:
    """List available effects."""
    logger.info("Available effects:")
    logger.info("  breathing     - Breathing effect between black and cyan")
    logger.info("  wave          - Wave effect with blue-cyan gradient")
    logger.info("  rainbow       - Rainbow color cycle")
    logger.info("  pulse         - Pulsing cyan effect")
    logger.info("  ocean         - Ocean-themed breathing (blue to cyan)")
    logger.info("  ripple        - Advanced breathing ripple across devices")
    logger.info("  memory        - Memory usage display on RAM sticks")
    logger.info("  cpu           - CPU usage display on RAM sticks")
    logger.info("  contrast      - High contrast color cycling for dramatic effect")
    logger.info("  system        - Combined CPU (sticks 0-1) + Memory (sticks 2-3) monitoring")


def run_theme(theme_name: str) -> None:
    """Run a specific theme."""
    try:
        logger.info(f"Applying theme: {theme_name}")
        apply_theme(theme_name)
        logger.success(f"Theme '{theme_name}' applied successfully")
    except ValueError as e:
        logger.error(f"Theme error: {e}")
        sys.exit(1)


def run_effect(effect_name: str, args=None) -> None:
    """Run a specific effect."""
    effect = effect_name.lower()
    
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
    elif effect == "ripple":
        breathing_ripple()
    elif effect == "memory":
        memory_usage_effect()
    elif effect == "cpu":
        cpu_usage_effect()
    elif effect == "contrast":
        contrast_cycle(0.01)  # 0.01 second intervals (100 FPS)
    elif effect == "system":
        from src.openrgb_control.dynamic.dynamic import system_monitoring_effect
        if args and args.speed:
            system_monitoring_effect(args.speed)
        else:
            system_monitoring_effect()
    else:
        logger.error(f"Unknown effect: {effect}")
        list_effects()
        sys.exit(1)


def test_server_devices() -> int:
    """Test OpenRGB server device connectivity."""
    try:
        from openrgb import OpenRGBClient
        client = OpenRGBClient()
        device_count = len(client.devices)
        client.disconnect()
        return device_count
    except ImportError:
        logger.warning("openrgb-python not available for device testing")
        return -1
    except Exception as e:
        logger.warning(f"Device test failed: {e}")
        return 0

def ensure_server() -> bool:
    """Ensure OpenRGB server is running with rigorous testing."""
    if not SERVER_AVAILABLE:
        logger.warning("Server management not available")
        return False
    
    logger.info("Checking OpenRGB server status...")
    
    # Check if server is already running
    status = get_server_status()
    if status['status'] == 'healthy':
        logger.success(f"OpenRGB server already running on {status['host']}:{status['port']}")
        
        # Test device connectivity
        device_count = test_server_devices()
        if device_count > 0:
            logger.success(f"Server has {device_count} devices accessible")
            return True
        elif device_count == 0:
            logger.warning("Server running but no devices detected - restarting server")
            # Kill and restart server
            import subprocess
            subprocess.run(["sudo", "pkill", "-f", "openrgb"], capture_output=True)
            import time
            time.sleep(2)
        else:
            logger.warning("Cannot test devices - proceeding with caution")
            return True
    
    # Try to start server
    logger.info("Starting OpenRGB server...")
    success = ensure_openrgb_server()
    
    if success:
        # Wait for server to fully initialize
        import time
        time.sleep(3)
        
        # Test device connectivity after startup
        device_count = test_server_devices()
        if device_count > 0:
            logger.success(f"OpenRGB server started successfully with {device_count} devices")
            return True
        elif device_count == 0:
            logger.error("OpenRGB server started but no devices detected")
            logger.info("This may be due to permission issues - ensure OpenRGB has device access")
            return False
        else:
            logger.success("OpenRGB server started successfully")
            return True
    else:
        logger.error("Failed to start OpenRGB server")
        logger.warning("Falling back to direct OpenRGB commands")
        return False

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OpenRGB Control - Dynamic RGB lighting for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py theme cyan          # Apply cyan theme
  python main.py effect breathing    # Run breathing effect
  python main.py --list-themes       # Show available themes
  python main.py --list-effects      # Show available effects
        """
    )
    
    # Add mutually exclusive group for main commands
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("command", nargs="?", choices=["theme", "effect"], 
                              help="Command type (theme or effect)")
    command_group.add_argument("--list-themes", action="store_true",
                              help="List available themes")
    command_group.add_argument("--list-effects", action="store_true",
                              help="List available effects")
    
    # Add server management options
    parser.add_argument("--use-server", action="store_true", default=True,
                       help="Use OpenRGB server mode for better performance (default)")
    parser.add_argument("--no-server", action="store_true",
                       help="Disable server mode, use direct commands")
    
    # Add positional argument for theme/effect name
    parser.add_argument("name", nargs="?", help="Theme or effect name")
    
    # Add optional speed argument for effects
    parser.add_argument("speed", nargs="?", type=float, help="Speed/interval for effects (seconds)")
    
    args = parser.parse_args()
    
    # Handle list commands
    if args.list_themes:
        list_themes()
        return
    
    if args.list_effects:
        list_effects()
        return
    
    # Handle theme/effect commands
    if not args.name:
        logger.error("Missing theme or effect name")
        parser.print_help()
        sys.exit(1)
    
    # Determine server usage
    use_server = args.use_server and not args.no_server
    server_ready = False
    
    if use_server:
        server_ready = ensure_server()
    
    # Set global server mode for effects/themes
    import os
    os.environ['OPENRGB_USE_SERVER'] = 'true' if server_ready else 'false'
    
    if args.command == "theme":
        run_theme(args.name)
    elif args.command == "effect":
        run_effect(args.name, args)


if __name__ == "__main__":
    main()