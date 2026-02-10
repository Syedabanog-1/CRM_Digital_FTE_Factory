"""Background metrics aggregation worker.

Consumes from fte.metrics topic and aggregates channel metrics
into the agent_metrics table for the /metrics/channels endpoint.
"""

import asyncio

from production.config import settings
from production.database import queries
from production.logging_config import get_logger

logger = get_logger(__name__)


async def run_metrics_collector() -> None:
    """Consume from fte.metrics and aggregate metrics."""
    logger.info("metrics_collector_starting")

    try:
        from production.kafka_client import create_consumer, TOPIC_METRICS

        consumer = await create_consumer(TOPIC_METRICS, group_id="fte-metrics")
        if not consumer:
            logger.warning("metrics_collector_no_consumer")
            # Run in standalone mode
            while True:
                await asyncio.sleep(60)
            return

        logger.info("metrics_collector_consuming")

        async for msg in consumer:
            try:
                data = msg.value
                if data:
                    await queries.insert_metric(
                        metric_name=data.get("metric_name", "unknown"),
                        metric_value=data.get("metric_value", 0.0),
                        channel=data.get("channel"),
                        dimensions=data.get("dimensions", {}),
                    )
            except Exception as e:
                logger.error("metrics_collector_error", error=str(e))

    except Exception as e:
        logger.error("metrics_collector_fatal", error=str(e))


async def get_daily_summary(channel: str | None = None) -> dict:
    """Get aggregated daily metrics summary."""
    return await queries.get_channel_metrics(hours=24, channel=channel)
