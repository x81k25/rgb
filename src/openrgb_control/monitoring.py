"""System monitoring utilities for RGB effects."""

import psutil
import time
from typing import Tuple


def get_memory_usage() -> Tuple[float, float, float]:
    """Get current memory usage statistics.
    
    Returns:
        Tuple of (used_percent, used_gb, total_gb)
    """
    memory = psutil.virtual_memory()
    used_gb = memory.used / (1024**3)  # Convert bytes to GB
    total_gb = memory.total / (1024**3)
    return memory.percent, used_gb, total_gb


def get_cpu_usage(interval: float = 1.0) -> float:
    """Get current CPU usage percentage.
    
    Args:
        interval: Measurement interval in seconds. Use None for non-blocking.
    
    Returns:
        CPU usage percentage
    """
    return psutil.cpu_percent(interval=interval)


def get_system_stats() -> dict:
    """Get comprehensive system statistics.
    
    Returns:
        Dict with memory and CPU usage information
    """
    memory_percent, memory_used_gb, memory_total_gb = get_memory_usage()
    cpu_percent = get_cpu_usage()
    
    return {
        'memory': {
            'percent': memory_percent,
            'used_gb': memory_used_gb,
            'total_gb': memory_total_gb,
        },
        'cpu': {
            'percent': cpu_percent,
        },
        'timestamp': time.time()
    }