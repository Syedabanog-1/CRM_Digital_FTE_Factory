"""Unified message processor worker - Kafka consumer that processes all channels.

Consumes from fte.tickets.incoming, resolves customers, manages conversations,
runs the OpenAI agent, stores results, and publishes metrics.
"""

import asyncio
import json
import time

from production.config import settings
from production.database import queries
from production.logging_config import setup_logging, get_logger, bind_correlation_id
from production.metrics import MESSAGES_PROCESSED, PROCESSING_DURATION, METRICS_AVAILABLE

logger = get_logger(__name__)


async def process_message(message_data: dict) -> None:
    """Process a single incoming message through the agent pipeline.

    Flow:
    1. Resolve customer by email (primary) or phone (secondary)
    2. Get or create active conversation (reuse within 24 hours)
    3. Store inbound message
    4. Load conversation history for context
    5. Run the OpenAI agent
    6. Store agent response with metadata
    7. Publish processing metrics
    """
    correlation_id = bind_correlation_id()
    start_time = time.time()

    channel = message_data.get("channel", "web")
    content = message_data.get("content", "")
    customer_email = message_data.get("customer_email", "")
    customer_name = message_data.get("customer_name", "")
    customer_phone = message_data.get("customer_phone", "")
    subject = message_data.get("subject", "Support Request")

    logger.info(
        "processing_message",
        channel=channel,
        customer_email=customer_email,
        correlation_id=correlation_id,
    )

    try:
        # 1. Resolve customer
        customer = None
        if customer_email:
            customer = await queries.get_customer_by_email(customer_email)
        if not customer and customer_phone:
            customer = await queries.get_customer_by_phone(customer_phone)
        if not customer:
            customer = await queries.insert_customer(
                email=customer_email or f"unknown_{int(time.time())}@placeholder.com",
                name=customer_name,
                phone=customer_phone,
            )
            # Register identifiers
            if customer_email:
                await queries.upsert_customer_identifier(
                    customer["id"], "email", customer_email
                )
            if customer_phone:
                await queries.upsert_customer_identifier(
                    customer["id"], "phone", customer_phone
                )
                if channel == "whatsapp":
                    await queries.upsert_customer_identifier(
                        customer["id"], "whatsapp", customer_phone
                    )

        # 2. Get or create conversation
        conversation = await queries.get_active_conversation(
            customer["id"], channel
        )
        if not conversation:
            conversation = await queries.insert_conversation(
                customer_id=customer["id"],
                channel=channel,
                subject=subject,
            )

        # 3. Store inbound message
        await queries.insert_message(
            conversation_id=conversation["id"],
            channel=channel,
            direction="inbound",
            role="customer",
            content=content,
            external_id=message_data.get("message_id"),
        )

        # 4. Load conversation history
        history_messages = await queries.get_conversation_messages(
            conversation["id"], limit=10
        )
        conversation_context = "\n".join(
            f"{m['role']}: {m['content'][:200]}" for m in history_messages[-5:]
        )

        # 5. Run the OpenAI agent
        agent_response = await _run_agent(
            content=content,
            channel=channel,
            customer_email=customer_email or customer.get("email", ""),
            customer_name=customer_name or customer.get("name", ""),
            conversation_context=conversation_context,
            ticket_id=message_data.get("ticket_id"),
        )

        processing_time = int((time.time() - start_time) * 1000)

        # 6. Store agent response (if not already stored by send_response tool)
        if agent_response and not agent_response.get("stored_by_tool"):
            await queries.insert_message(
                conversation_id=conversation["id"],
                channel=channel,
                direction="outbound",
                role="agent",
                content=agent_response.get("content", ""),
                processing_time_ms=processing_time,
                tool_calls=agent_response.get("tool_calls"),
                token_usage=agent_response.get("token_usage"),
            )

        # 7. Record Prometheus metrics
        if METRICS_AVAILABLE:
            if MESSAGES_PROCESSED:
                MESSAGES_PROCESSED.labels(channel=channel).inc()
            if PROCESSING_DURATION:
                PROCESSING_DURATION.observe(processing_time / 1000.0)

        # 8. Publish metrics to database
        await queries.insert_metric(
            "response_time",
            float(processing_time),
            channel=channel,
            dimensions={
                "customer_email": customer_email,
                "correlation_id": correlation_id,
            },
        )

        logger.info(
            "message_processed",
            channel=channel,
            processing_time_ms=processing_time,
            correlation_id=correlation_id,
        )

    except Exception as e:
        logger.error(
            "message_processing_failed",
            error=str(e),
            channel=channel,
            correlation_id=correlation_id,
        )

        # Send apologetic response
        try:
            await _send_error_response(message_data, str(e))
        except Exception:
            pass

        # Publish to DLQ
        try:
            from production.kafka_client import publish_to_dlq
            await publish_to_dlq(message_data, str(e), "fte.tickets.incoming")
        except Exception:
            pass


async def _run_agent(
    content: str,
    channel: str,
    customer_email: str,
    customer_name: str,
    conversation_context: str,
    ticket_id: str | None = None,
) -> dict:
    """Run the OpenAI Agents SDK agent on the customer message."""
    try:
        from agents import Runner
        from production.agent.customer_success_agent import customer_success_agent

        # Build the input message with context
        input_message = f"""Customer Message:
Channel: {channel}
Customer Email: {customer_email}
Customer Name: {customer_name}
Message: {content}

Previous Conversation:
{conversation_context}
"""

        result = await Runner.run(customer_success_agent, input_message)

        return {
            "content": result.final_output if hasattr(result, 'final_output') else str(result),
            "stored_by_tool": True,  # send_response tool stores the message
        }

    except Exception as e:
        logger.error("agent_run_failed", error=str(e))
        # Fallback response
        return {
            "content": f"Thank you for contacting TechCorp support. We've received your message and are working on it. Reference: {ticket_id or 'pending'}",
            "stored_by_tool": False,
        }


async def _send_error_response(message_data: dict, error: str) -> None:
    """Send an apologetic response when processing fails."""
    logger.info("sending_error_response", channel=message_data.get("channel"))
    # The actual sending is handled by the channel-specific outbound handlers


async def run_consumer() -> None:
    """Main consumer loop - consumes from fte.tickets.incoming."""
    setup_logging(settings.log_level)
    logger.info("worker_starting")

    await queries.create_pool()

    from production.kafka_client import create_consumer, TOPIC_INCOMING

    consumer = await create_consumer(TOPIC_INCOMING)
    if not consumer:
        logger.error("worker_no_consumer")
        # Fallback: poll mode without Kafka
        logger.info("worker_running_in_standalone_mode")
        while True:
            await asyncio.sleep(10)
        return

    logger.info("worker_consuming", topic=TOPIC_INCOMING)

    try:
        async for msg in consumer:
            try:
                await process_message(msg.value)
            except Exception as e:
                logger.error("consumer_message_error", error=str(e))
    finally:
        await consumer.stop()
        await queries.close_pool()
