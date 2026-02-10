"""Shared pytest fixtures and infrastructure skip conditions for production tests.

Automatically skips database, E2E, and load tests when infrastructure is not available.
This prevents test collection crashes on machines without Docker/PostgreSQL/Kafka.
"""

import socket

import pytest


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


# Infrastructure availability flags
POSTGRES_AVAILABLE = _is_port_open("localhost", 5432)
KAFKA_AVAILABLE = _is_port_open("localhost", 9092)
API_AVAILABLE = _is_port_open("localhost", 8000)

# Skip reasons
requires_postgres = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL not available on localhost:5432 (start with docker-compose up -d)",
)
requires_kafka = pytest.mark.skipif(
    not KAFKA_AVAILABLE,
    reason="Kafka not available on localhost:9092 (start with docker-compose up -d)",
)
requires_api = pytest.mark.skipif(
    not API_AVAILABLE,
    reason="API not available on localhost:8000 (start with docker-compose up -d)",
)
requires_stack = pytest.mark.skipif(
    not (POSTGRES_AVAILABLE and KAFKA_AVAILABLE and API_AVAILABLE),
    reason="Full stack not available (start with docker-compose up -d)",
)
