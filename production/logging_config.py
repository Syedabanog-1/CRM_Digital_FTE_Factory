"""Structured JSON logging setup for Stage 2 production system."""

import logging
import uuid

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging with correlation ID support."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return str(uuid.uuid4())


def bind_correlation_id(correlation_id: str | None = None) -> str:
    """Bind a correlation ID to the current context for all subsequent log calls."""
    cid = correlation_id or generate_correlation_id()
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    return cid


def clear_contextvars() -> None:
    """Clear all context variables (call at end of request)."""
    structlog.contextvars.clear_contextvars()
