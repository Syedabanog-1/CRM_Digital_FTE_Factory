"""Worker entrypoint - starts message processor and metrics collector."""

import asyncio
import signal
import sys

from production.logging_config import setup_logging, get_logger
from production.config import settings

logger = get_logger(__name__)

_shutdown = False


def _signal_handler(sig, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global _shutdown
    logger.info("shutdown_signal_received", signal=sig)
    _shutdown = True


async def main():
    """Start all workers as concurrent tasks."""
    setup_logging(settings.log_level)
    logger.info("workers_starting")

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    from production.workers.message_processor import run_consumer
    from production.workers.metrics_collector import run_metrics_collector

    tasks = [
        asyncio.create_task(run_consumer()),
        asyncio.create_task(run_metrics_collector()),
    ]

    logger.info("workers_running", task_count=len(tasks))

    # Wait for shutdown signal or task completion
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # Cancel remaining tasks
    for task in pending:
        task.cancel()

    logger.info("workers_stopped")


if __name__ == "__main__":
    asyncio.run(main())
