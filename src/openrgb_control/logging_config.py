"""Logging configuration for OpenRGB Control."""

import os
import sys
from pathlib import Path

try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    
    # Fallback logger when loguru isn't available
    class FallbackLogger:
        def remove(self): pass
        def add(self, *args, **kwargs): pass
        def bind(self, **kwargs): return self
        def debug(self, msg): print(f"🔧 {msg}")
        def info(self, msg): print(f"ℹ️  {msg}")
        def warning(self, msg): print(f"⚠️  {msg}")
        def error(self, msg): print(f"❌ {msg}")
        def success(self, msg): print(f"✅ {msg}")
    
    logger = FallbackLogger()

def setup_logging(level: str = "INFO", log_file: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Whether to enable file logging
    """
    # Remove default handler
    logger.remove()
    
    # Get log level from environment or parameter
    log_level = os.getenv("OPENRGB_LOG_LEVEL", level).upper()
    
    # Console handler with colored output
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True
    )
    
    # File handler if enabled
    if log_file:
        log_dir = Path.home() / ".openrgb-control" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_dir / "openrgb-control.log",
            level="DEBUG",  # Always debug level for file
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="7 days",
            compression="gz",  # Use 'gz' instead of 'gzip'
            enqueue=True
        )
        
        logger.debug(f"Logging to file: {log_dir / 'openrgb-control.log'}")

def get_logger(name: str = None):
    """Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger

def set_log_level(level: str) -> None:
    """Set the log level for all handlers.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # This is a simplified approach - in production you'd want to track handlers
    logger.remove()
    setup_logging(level=level)

# Default setup
setup_logging()