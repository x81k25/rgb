"""System monitoring utilities for RGB effects."""

import psutil
from typing import Tuple

try:
    import pynvml
    pynvml.nvmlInit()
    _NVML_AVAILABLE = True
except Exception:
    _NVML_AVAILABLE = False


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


def get_gpu_usage(gpu_index: int = 0) -> float:
    """Get GPU utilization percentage.

    Args:
        gpu_index: GPU device index (default 0).

    Returns:
        GPU utilization percentage, or 0.0 if unavailable.
    """
    if not _NVML_AVAILABLE:
        return 0.0
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return float(util.gpu)
    except Exception:
        return 0.0


def get_gpu_vram_usage(gpu_index: int = 0) -> float:
    """Get GPU VRAM utilization percentage.

    Args:
        gpu_index: GPU device index (default 0).

    Returns:
        VRAM usage percentage, or 0.0 if unavailable.
    """
    if not _NVML_AVAILABLE:
        return 0.0
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return float(mem.used / mem.total * 100.0)
    except Exception:
        return 0.0


