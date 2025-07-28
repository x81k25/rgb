#!/usr/bin/env python3
"""CPU stress test to test RGB effect responsiveness."""

import multiprocessing
import time
import math
import random
import argparse

def cpu_intensive_task(duration: int, worker_id: int):
    """CPU-intensive task that runs for specified duration."""
    print(f"Worker {worker_id}: Starting CPU stress for {duration} seconds")
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Mix of different CPU-intensive operations
        
        # 1. Mathematical calculations
        for i in range(10000):
            math.sqrt(random.randint(1, 1000000))
            math.factorial(random.randint(1, 100))
        
        # 2. String operations
        text = "cpu stress test " * 1000
        text.upper().lower().replace("test", "TEST")
        
        # 3. List operations
        numbers = [random.randint(1, 1000) for _ in range(1000)]
        sorted(numbers)
        
        # 4. Prime number calculation
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(math.sqrt(n)) + 1):
                if n % i == 0:
                    return False
            return True
        
        primes = [n for n in range(1000, 1100) if is_prime(n)]
    
    print(f"Worker {worker_id}: Finished CPU stress")

def stress_test(workers: int = None, duration: int = 30):
    """Run CPU stress test with multiple workers."""
    if workers is None:
        workers = multiprocessing.cpu_count()
    
    print(f"Starting CPU stress test:")
    print(f"  Workers: {workers}")
    print(f"  Duration: {duration} seconds")
    print(f"  CPU cores: {multiprocessing.cpu_count()}")
    print("\nThis should drive CPU usage high to test RGB responsiveness!")
    print("Run 'sudo python3 main.py effect cpu' in another terminal to see the effect.\n")
    
    # Create and start worker processes
    processes = []
    for i in range(workers):
        p = multiprocessing.Process(target=cpu_intensive_task, args=(duration, i))
        processes.append(p)
        p.start()
    
    # Wait for all processes to complete
    for p in processes:
        p.join()
    
    print(f"\nCPU stress test completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU stress test for RGB effect testing")
    parser.add_argument("--workers", "-w", type=int, default=None,
                       help="Number of worker processes (default: number of CPU cores)")
    parser.add_argument("--duration", "-d", type=int, default=30,
                       help="Duration in seconds (default: 30)")
    
    args = parser.parse_args()
    
    try:
        stress_test(args.workers, args.duration)
    except KeyboardInterrupt:
        print("\nStopped by user")