#!/usr/bin/env python3
"""Health check polling utility for docker-compose services.

Waits for PostgreSQL, Kafka, and the API to be healthy before returning.
Used by test orchestration scripts to ensure services are ready.

Usage:
    python scripts/wait-for-healthy.py [--timeout 120] [--interval 5]
"""

import argparse
import socket
import sys
import time
import urllib.request
import urllib.error


def check_tcp(host: str, port: int, name: str) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def check_http(url: str, name: str) -> bool:
    """Check if an HTTP endpoint returns 200."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, ConnectionRefusedError, OSError):
        return False


def wait_for_services(timeout: int = 120, interval: int = 5) -> bool:
    """Wait for all services to be healthy.

    Returns True if all services are healthy within timeout, False otherwise.
    """
    services = [
        ("PostgreSQL", lambda: check_tcp("localhost", 5432, "PostgreSQL")),
        ("Kafka", lambda: check_tcp("localhost", 9092, "Kafka")),
        ("API", lambda: check_http("http://localhost:8000/health", "API")),
    ]

    start = time.time()
    healthy = {name: False for name, _ in services}

    print(f"Waiting for services (timeout: {timeout}s, interval: {interval}s)...")

    while time.time() - start < timeout:
        all_healthy = True
        for name, check_fn in services:
            if not healthy[name]:
                if check_fn():
                    healthy[name] = True
                    elapsed = int(time.time() - start)
                    print(f"  [{elapsed:3d}s] {name}: HEALTHY")
                else:
                    all_healthy = False

        if all_healthy:
            elapsed = int(time.time() - start)
            print(f"\nAll services healthy in {elapsed}s")
            return True

        remaining = [name for name, is_healthy in healthy.items() if not is_healthy]
        elapsed = int(time.time() - start)
        print(f"  [{elapsed:3d}s] Waiting for: {', '.join(remaining)}")
        time.sleep(interval)

    # Timeout reached
    failed = [name for name, is_healthy in healthy.items() if not is_healthy]
    print(f"\nTIMEOUT after {timeout}s. Unhealthy services: {', '.join(failed)}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Wait for docker-compose services to be healthy")
    parser.add_argument("--timeout", type=int, default=120, help="Max wait time in seconds (default: 120)")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds (default: 5)")
    args = parser.parse_args()

    success = wait_for_services(timeout=args.timeout, interval=args.interval)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
