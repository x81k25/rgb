#!/usr/bin/env python3
"""OpenRGB server management utilities."""

import subprocess
import time
import socket
import psutil
import requests
import signal
import sys
from typing import Optional, Tuple

try:
    from loguru import logger
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False
    
    # Fallback logger for when loguru isn't available
    class FallbackLogger:
        def debug(self, msg): print(f"DEBUG: {msg}")
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def success(self, msg): print(f"SUCCESS: {msg}")
    
    logger = FallbackLogger()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6742

def is_port_open(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 1.0) -> bool:
    """Check if OpenRGB server port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error, ConnectionRefusedError):
        return False

def is_openrgb_server_running() -> Tuple[bool, Optional[int]]:
    """Check if OpenRGB server process is running.
    
    Returns:
        Tuple of (is_running, pid)
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'openrgb':
                cmdline = proc.info['cmdline'] or []
                if '--server' in cmdline:
                    return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None

def start_openrgb_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, 
                        timeout: float = 10.0) -> bool:
    """Start OpenRGB server.
    
    Args:
        host: Server host
        port: Server port
        timeout: Maximum time to wait for server startup
        
    Returns:
        True if server started successfully
    """
    logger.info(f"Starting OpenRGB server on {host}:{port}...")
    
    # Start server process
    try:
        # Check if we need sudo (if running as non-root)
        import os
        if os.geteuid() != 0:
            cmd = ["sudo", "openrgb", "--server", "--server-host", host, "--server-port", str(port)]
        else:
            cmd = ["openrgb", "--server", "--server-host", host, "--server-port", str(port)]
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            if is_port_open(host, port):
                logger.success(f"OpenRGB server started successfully (PID: {process.pid})")
                return True
            time.sleep(0.1)
        
        # Server didn't start in time
        try:
            process.terminate()
            process.wait(timeout=2)
        except:
            process.kill()
        
        logger.error("OpenRGB server failed to start within timeout")
        return False
        
    except FileNotFoundError:
        logger.error("OpenRGB binary not found")
        return False
    except Exception as e:
        logger.error(f"Failed to start OpenRGB server: {e}")
        return False

def stop_openrgb_server() -> bool:
    """Stop OpenRGB server process.
    
    Returns:
        True if server stopped successfully
    """
    is_running, pid = is_openrgb_server_running()
    
    if not is_running:
        print("OpenRGB server is not running")
        return True
    
    try:
        print(f"Stopping OpenRGB server (PID: {pid})...")
        proc = psutil.Process(pid)
        proc.terminate()
        
        # Wait for graceful shutdown
        try:
            proc.wait(timeout=5)
            print("✓ OpenRGB server stopped")
            return True
        except psutil.TimeoutExpired:
            # Force kill if needed
            proc.kill()
            proc.wait(timeout=2)
            print("✓ OpenRGB server force stopped")
            return True
            
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"✗ Failed to stop OpenRGB server: {e}")
        return False

def ensure_openrgb_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Ensure OpenRGB server is running.
    
    Returns:
        True if server is running or was started successfully
    """
    # Check if server is already running
    if is_port_open(host, port):
        print(f"✓ OpenRGB server already running on {host}:{port}")
        return True
    
    # Check if process exists but port not open (startup lag)
    is_running, pid = is_openrgb_server_running()
    if is_running:
        print(f"OpenRGB server process found (PID: {pid}), waiting for port...")
        # Wait a bit for port to open
        for _ in range(20):  # 2 seconds max
            if is_port_open(host, port):
                print(f"✓ OpenRGB server ready on {host}:{port}")
                return True
            time.sleep(0.1)
        
        print("✗ OpenRGB server process exists but port not accessible")
        return False
    
    # Start new server
    return start_openrgb_server(host, port)

def test_server_connection(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Test OpenRGB server connection with a simple API call.
    
    Returns:
        True if server is accessible
    """
    try:
        response = requests.get(f"http://{host}:{port}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_server_status(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict:
    """Get detailed server status information.
    
    Returns:
        Dictionary with server status details
    """
    port_open = is_port_open(host, port)
    is_running, pid = is_openrgb_server_running()
    api_working = test_server_connection(host, port) if port_open else False
    
    return {
        'port_open': port_open,
        'process_running': is_running,
        'pid': pid,
        'api_working': api_working,
        'host': host,
        'port': port,
        'status': 'healthy' if (port_open and is_running and api_working) else 'unhealthy'
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenRGB server management")
    parser.add_argument("action", choices=["start", "stop", "status", "ensure"], 
                       help="Action to perform")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    
    args = parser.parse_args()
    
    if args.action == "start":
        success = start_openrgb_server(args.host, args.port)
        sys.exit(0 if success else 1)
    elif args.action == "stop":
        success = stop_openrgb_server()
        sys.exit(0 if success else 1)
    elif args.action == "ensure":
        success = ensure_openrgb_server(args.host, args.port)
        sys.exit(0 if success else 1)
    elif args.action == "status":
        status = get_server_status(args.host, args.port)
        print(f"OpenRGB Server Status:")
        print(f"  Host: {status['host']}")
        print(f"  Port: {status['port']}")
        print(f"  Port Open: {status['port_open']}")
        print(f"  Process Running: {status['process_running']}")
        if status['pid']:
            print(f"  PID: {status['pid']}")
        print(f"  API Working: {status['api_working']}")
        print(f"  Overall Status: {status['status']}")
        sys.exit(0 if status['status'] == 'healthy' else 1)