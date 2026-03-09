"""Entry point for the RGB daemon process."""

from src.openrgb_control.daemon import RGBDaemon

if __name__ == "__main__":
    daemon = RGBDaemon()
    daemon.run()
