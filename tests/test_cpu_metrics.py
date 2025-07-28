#!/usr/bin/env python3
"""Test different CPU usage measurement methods."""

import psutil
import time
import subprocess

def test_psutil_methods():
    """Test various psutil CPU measurement methods."""
    print("=== PSUTIL CPU MEASUREMENTS ===")
    
    # Method 1: psutil with different intervals
    print("1. psutil.cpu_percent(interval=1.0):")
    cpu1 = psutil.cpu_percent(interval=1.0)
    print(f"   {cpu1:.1f}%")
    
    print("\n2. psutil.cpu_percent(interval=0.5):")
    cpu2 = psutil.cpu_percent(interval=0.5)
    print(f"   {cpu2:.1f}%")
    
    print("\n3. psutil.cpu_percent(interval=None) [non-blocking]:")
    # Initialize
    psutil.cpu_percent()
    time.sleep(1)
    cpu3 = psutil.cpu_percent()
    print(f"   {cpu3:.1f}%")
    
    print("\n4. psutil.cpu_percent(percpu=True) [per-core average]:")
    cpu_cores = psutil.cpu_percent(interval=1.0, percpu=True)
    cpu4 = sum(cpu_cores) / len(cpu_cores)
    print(f"   {cpu4:.1f}% (avg of {len(cpu_cores)} cores)")
    print(f"   Individual cores: {[f'{c:.1f}%' for c in cpu_cores]}")

def test_system_commands():
    """Test system command-based CPU measurements."""
    print("\n=== SYSTEM COMMAND MEASUREMENTS ===")
    
    # Method 1: top command
    print("5. top -bn1 (1 iteration):")
    try:
        result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'Cpu(s):' in line or '%Cpu(s):' in line:
                print(f"   {line.strip()}")
                break
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 2: htop if available
    print("\n6. htop --version (checking if available):")
    try:
        result = subprocess.run(['htop', '--version'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print("   htop is available")
        else:
            print("   htop not available")
    except Exception:
        print("   htop not available")
    
    # Method 3: /proc/stat
    print("\n7. /proc/stat method:")
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            print(f"   {line.strip()}")
            # Parse CPU times
            fields = line.split()[1:8]
            total_time = sum(int(f) for f in fields)
            idle_time = int(fields[3])  # idle is 4th field
            cpu_percent = (1 - idle_time / total_time) * 100
            print(f"   Calculated: {cpu_percent:.1f}%")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 4: vmstat
    print("\n8. vmstat 1 2 (2 samples, 1 second apart):")
    try:
        result = subprocess.run(['vmstat', '1', '2'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 3:
            print(f"   {lines[-1]}")  # Last line has the measurement
    except Exception as e:
        print(f"   Error: {e}")

def test_load_average():
    """Test load average as alternative metric."""
    print("\n=== LOAD AVERAGE ===")
    
    print("9. Load average:")
    load1, load5, load15 = psutil.getloadavg()
    cpu_count = psutil.cpu_count()
    print(f"   1min: {load1:.2f}, 5min: {load5:.2f}, 15min: {load15:.2f}")
    print(f"   CPU cores: {cpu_count}")
    print(f"   Load as % of capacity (1min): {(load1/cpu_count)*100:.1f}%")

if __name__ == "__main__":
    print("Testing different CPU usage measurement methods...")
    print("Compare these with your system monitor to see which is most accurate.\n")
    
    test_psutil_methods()
    test_system_commands()
    test_load_average()
    
    print("\n=== RECOMMENDATIONS ===")
    print("- Methods 1-4 use psutil library")
    print("- Method 5 uses top command")
    print("- Method 7 uses /proc/stat directly")
    print("- Method 8 uses vmstat")
    print("- Method 9 shows load average (different metric)")