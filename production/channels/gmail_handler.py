"""Gmail channel handler - Gmail API + Pub/Sub integration.

Handles POST /webhooks/gmail for Pub/Sub push notifications.
Parses emails, normalizes messages, and publishes to Kafka.
"""

import base64
import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from production.config import settings
from production.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["webhooks"])


class PubSubMessage(BaseModel):
    """Google Pub/Sub push notification message."""

    message: dict
    subscription: str = ""


@router.post("/webhooks/gmail")
async def gmail_webhook(request: Request):
    """Receive Gmail Pub/Sub push notification and process new email."""
    try:
        body = await request.json()
        pub_sub_msg = PubSubMessage(**body)

        # Decode the Pub/Sub message data
        raw_data = pub_sub_msg.message.get("data", "")
        if not raw_data:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub notification format")

        decoded = base64.b64decode(raw_data).decode("utf-8")
        notification = json.loads(decoded)

        email_address = notification.get("emailAddress", "")
        history_id = notification.get("historyId", "")

        logger.info(
            "gmail_webhook_received",
            email=email_address,
            history_id=history_id,
        )

        # Fetch the actual email using Gmail API
        email_data = await _fetch_gmail_message(history_id)

        if email_data:
            # Publish to Kafka
            try:
                from production.kafka_client import publish, TOPIC_EMAIL_IN, TOPIC_INCOMING

                kafka_msg = {
                    "channel": "email",
                    "customer_email": email_data.get("from_email", ""),
                    "customer_name": email_data.get("from_name", ""),
                    "subject": email_data.get("subject", ""),
                    "content": email_data.get("body", ""),
                    "thread_id": email_data.get("thread_id", ""),
                    "message_id": email_data.get("message_id", ""),
                }
                await publish(TOPIC_EMAIL_IN, kafka_msg)
                await publish(TOPIC_INCOMING, kafka_msg)
            except Exception as e:
                logger.warning("kafka_publish_failed", error=str(e))

        return {"status": "accepted", "message_id": f"gmail_{history_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("gmail_webhook_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid Pub/Sub notification format")


async def _fetch_gmail_message(history_id: str) -> dict | None:
    """Fetch new email message using Gmail API based on history ID."""
    try:
        if not settings.gmail_credentials_json:
            logger.warning("gmail_no_credentials")
            return None

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            settings.gmail_credentials_json,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        service = build("gmail", "v1", credentials=credentials)

        # Get history since the notification
        history = (
            service.users()
            .history()
            .list(
                userId=settings.gmail_user_id,
                startHistoryId=history_id,
                historyTypes=["messageAdded"],
            )
            .execute()
        )

        messages_added = []
        for record in history.get("history", []):
            for msg in record.get("messagesAdded", []):
                messages_added.append(msg["message"]["id"])

        if not messages_added:
            return None

        # Fetch the latest message
        msg_id = messages_added[-1]
        message = (
            service.users()
            .messages()
            .get(userId=settings.gmail_user_id, id=msg_id, format="full")
            .execute()
        )

        return _parse_email(message)

    except Exception as e:
        logger.error("gmail_fetch_failed", error=str(e))
        return None


def _parse_email(message: dict) -> dict:
    """Parse Gmail API message into normalized format."""
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}

    from_header = headers.get("from", "")
    # Parse "Name <email@example.com>" format
    from_name = ""
    from_email = from_header
    if "<" in from_header:
        parts = from_header.split("<")
        from_name = parts[0].strip().strip('"')
        from_email = parts[1].rstrip(">").strip()

    subject = headers.get("subject", "")
    thread_id = message.get("threadId", "")
    message_id = message.get("id", "")

    # Extract plain text body
    body = _extract_body(message.get("payload", {}))

    return {
        "from_email": from_email.lower(),
        "from_name": from_name,
        "subject": subject,
        "body": body,
        "thread_id": thread_id,
        "message_id": message_id,
    }


def _extract_body(payload: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        # Recurse into multipart
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result

    return ""


async def send_email_reply(
    thread_id: str,
    to_email: str,
    subject: str,
    body: str,
    ticket_id: str | None = None,
) -> bool:
    """Send a reply in the same email thread via Gmail API."""
    try:
        if not settings.gmail_credentials_json:
            logger.warning("gmail_no_credentials_for_reply")
            return False

        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        import email.mime.text

        credentials = service_account.Credentials.from_service_account_file(
            settings.gmail_credentials_json,
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )

        service = build("gmail", "v1", credentials=credentials)

        # Build reply message
        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"
        mime_message = email.mime.text.MIMEText(body)
        mime_message["To"] = to_email
        mime_message["Subject"] = reply_subject

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

        send_body = {"raw": raw, "threadId": thread_id}

        service.users().messages().send(
            userId=settings.gmail_user_id, body=send_body
        ).execute()

        # Publish to outbound topic
        try:
            from production.kafka_client import publish, TOPIC_EMAIL_OUT

            await publish(TOPIC_EMAIL_OUT, {
                "channel": "email",
                "to": to_email,
                "subject": reply_subject,
                "ticket_id": ticket_id,
            })
        except Exception as e:
            logger.warning("kafka_outbound_failed", error=str(e))

        logger.info("email_reply_sent", to=to_email, thread_id=thread_id)
        return True

    except Exception as e:
        logger.error("email_reply_failed", error=str(e))
        return False


async def setup_gmail_watch() -> dict | None:
    """Set up Gmail Pub/Sub watch for INBOX label. Renew every 7 days."""
    try:
        if not settings.gmail_credentials_json or not settings.gmail_pubsub_topic:
            return None

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            settings.gmail_credentials_json,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        service = build("gmail", "v1", credentials=credentials)

        result = (
            service.users()
            .watch(
                userId=settings.gmail_user_id,
                body={
                    "topicName": settings.gmail_pubsub_topic,
                    "labelIds": ["INBOX"],
                },
            )
            .execute()
        )

        logger.info("gmail_watch_setup", expiration=result.get("expiration"))
        return result

    except Exception as e:
        logger.error("gmail_watch_failed", error=str(e))
        return None
