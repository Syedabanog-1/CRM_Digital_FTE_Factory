"""Kafka producer/consumer classes for event streaming.

9 topics per Constitution Principle IV for all async message routing.
"""

import json
from typing import AsyncGenerator

from production.config import settings
from production.logging_config import get_logger

logger = get_logger(__name__)

# Topic constants per constitution
TOPIC_INCOMING = "fte.tickets.incoming"
TOPIC_EMAIL_IN = "fte.channels.email.inbound"
TOPIC_WHATSAPP_IN = "fte.channels.whatsapp.inbound"
TOPIC_WEBFORM_IN = "fte.channels.webform.inbound"
TOPIC_EMAIL_OUT = "fte.channels.email.outbound"
TOPIC_WHATSAPP_OUT = "fte.channels.whatsapp.outbound"
TOPIC_ESCALATIONS = "fte.escalations"
TOPIC_METRICS = "fte.metrics"
TOPIC_DLQ = "fte.dlq"

ALL_TOPICS = [
    TOPIC_INCOMING,
    TOPIC_EMAIL_IN,
    TOPIC_WHATSAPP_IN,
    TOPIC_WEBFORM_IN,
    TOPIC_EMAIL_OUT,
    TOPIC_WHATSAPP_OUT,
    TOPIC_ESCALATIONS,
    TOPIC_METRICS,
    TOPIC_DLQ,
]

# Module-level instances
_producer = None
_consumer = None


def _json_serializer(value):
    """Serialize dict to JSON bytes."""
    if isinstance(value, bytes):
        return value
    return json.dumps(value).encode("utf-8")


def _json_deserializer(value):
    """Deserialize JSON bytes to dict."""
    if value is None:
        return None
    return json.loads(value.decode("utf-8"))


async def get_producer():
    """Get or create the Kafka producer."""
    global _producer
    if _producer is not None:
        return _producer

    try:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_brokers,
            value_serializer=_json_serializer,
            request_timeout_ms=5000,
            metadata_max_age_ms=5000,
        )
        await producer.start()
        _producer = producer
        logger.info("kafka_producer_started", brokers=settings.kafka_brokers)
        return _producer
    except Exception as e:
        _producer = None
        logger.warning("kafka_producer_failed", error=str(e))
        return None


async def stop_producer():
    """Stop the Kafka producer."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("kafka_producer_stopped")


async def create_consumer(
    *topics: str, group_id: str | None = None
):
    """Create a Kafka consumer for the given topics."""
    try:
        from aiokafka import AIOKafkaConsumer

        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=settings.kafka_brokers,
            group_id=group_id or settings.kafka_group_id,
            auto_offset_reset="earliest",
            value_deserializer=_json_deserializer,
        )
        await consumer.start()
        logger.info("kafka_consumer_started", topics=list(topics))
        return consumer
    except Exception as e:
        logger.error("kafka_consumer_failed", error=str(e))
        return None


async def publish(topic: str, message: dict) -> bool:
    """Publish a message to a Kafka topic."""
    producer = await get_producer()
    if producer is None:
        logger.warning("kafka_publish_skipped", topic=topic, reason="no_producer")
        return False

    try:
        await producer.send_and_wait(topic, message)
        logger.debug("kafka_published", topic=topic)
        return True
    except Exception as e:
        logger.error("kafka_publish_failed", topic=topic, error=str(e))
        return False


async def publish_to_dlq(original_message: dict, error: str, source_topic: str) -> bool:
    """Publish a failed message to the dead letter queue with error context."""
    dlq_message = {
        "original_message": original_message,
        "error": error,
        "source_topic": source_topic,
    }
    return await publish(TOPIC_DLQ, dlq_message)


async def check_kafka_health() -> bool:
    """Check Kafka connectivity."""
    try:
        producer = await get_producer()
        return producer is not None
    except Exception:
        return False
