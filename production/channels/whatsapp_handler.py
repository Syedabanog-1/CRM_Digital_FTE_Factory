"""WhatsApp channel handler - Twilio WhatsApp API integration.

Handles POST /webhooks/whatsapp with signature validation.
Parses messages, normalizes format, and publishes to Kafka.
"""

import json

from fastapi import APIRouter, HTTPException, Request, Form
from twilio.request_validator import RequestValidator

from production.config import settings
from production.agent.formatters import ChannelFormatter
from production.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["webhooks"])
formatter = ChannelFormatter()


def _validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """Validate Twilio webhook signature using HMAC-SHA1."""
    if not settings.twilio_auth_token:
        logger.warning("twilio_no_auth_token")
        return False

    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, params, signature)


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receive Twilio WhatsApp webhook with signature validation."""
    # Get form data
    form_data = await request.form()
    params = dict(form_data)

    # Validate Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    if not _validate_twilio_signature(url, params, signature):
        logger.warning("twilio_invalid_signature")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Extract message fields
    body = params.get("Body", "").strip()
    from_number = params.get("From", "")  # whatsapp:+1234567890
    profile_name = params.get("ProfileName", "")
    wa_id = params.get("WaId", "")
    num_media = params.get("NumMedia", "0")

    if not body:
        raise HTTPException(status_code=400, detail="Empty message body")

    # Extract phone number from whatsapp:+1234567890
    phone = from_number.replace("whatsapp:", "").strip()

    logger.info(
        "whatsapp_message_received",
        from_number=phone,
        profile_name=profile_name,
        body_length=len(body),
    )

    # Publish to Kafka
    try:
        from production.kafka_client import publish, TOPIC_WHATSAPP_IN, TOPIC_INCOMING

        kafka_msg = {
            "channel": "whatsapp",
            "customer_phone": phone,
            "customer_name": profile_name,
            "content": body,
            "wa_id": wa_id,
            "num_media": num_media,
            "from_raw": from_number,
        }
        await publish(TOPIC_WHATSAPP_IN, kafka_msg)
        await publish(TOPIC_INCOMING, kafka_msg)
    except Exception as e:
        logger.warning("kafka_publish_failed", error=str(e))

    return {"status": "accepted", "message_id": f"wa_{wa_id}"}


async def send_whatsapp_reply(
    to_number: str,
    message: str,
    ticket_id: str | None = None,
) -> bool:
    """Send a WhatsApp reply via Twilio API with message splitting."""
    try:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            logger.warning("twilio_no_credentials")
            return False

        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        # Format for WhatsApp channel
        formatted = formatter.format(message, "whatsapp")

        # Split if needed
        parts = formatter.split_whatsapp_message(formatted)

        # Ensure to_number has whatsapp: prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        for part in parts:
            client.messages.create(
                from_=settings.twilio_whatsapp_from,
                to=to_number,
                body=part,
            )

        # Publish to outbound topic
        try:
            from production.kafka_client import publish, TOPIC_WHATSAPP_OUT

            await publish(TOPIC_WHATSAPP_OUT, {
                "channel": "whatsapp",
                "to": to_number,
                "ticket_id": ticket_id,
                "parts_sent": len(parts),
            })
        except Exception as e:
            logger.warning("kafka_outbound_failed", error=str(e))

        logger.info("whatsapp_reply_sent", to=to_number, parts=len(parts))
        return True

    except Exception as e:
        logger.error("whatsapp_reply_failed", error=str(e))
        return False
