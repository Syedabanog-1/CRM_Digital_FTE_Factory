"""Channel handler integration tests for Gmail, WhatsApp, and Web Form.

Tests webhook processing, signature validation, message parsing,
response formatting, and message splitting.
"""

import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from production.agent.formatters import ChannelFormatter


# ---- Formatter Tests (no external deps) ----


class TestChannelFormatter:
    """Test channel-specific response formatting."""

    def setup_method(self):
        self.formatter = ChannelFormatter()

    def test_email_format_has_greeting_and_signature(self):
        """Email response should have formal greeting and signature."""
        result = self.formatter.format(
            "Here is your answer.", "email", "Alice", "TKT-001"
        )
        assert "Dear Alice" in result
        assert "Best regards" in result
        assert "TechCorp Support" in result
        assert "TKT-001" in result

    def test_email_format_default_name(self):
        """Email with no name should use 'Valued Customer'."""
        result = self.formatter.format("Hello.", "email")
        assert "Dear Valued Customer" in result

    def test_email_format_respects_word_limit(self):
        """Email response should not exceed 500 words."""
        long_message = " ".join(["word"] * 600)
        result = self.formatter.format(long_message, "email")
        word_count = len(result.split())
        assert word_count <= 520  # small margin for greeting/signature

    def test_whatsapp_format_short_message(self):
        """Short WhatsApp message should pass through."""
        result = self.formatter.format("Quick answer!", "whatsapp")
        assert result == "Quick answer!"

    def test_whatsapp_format_respects_limit(self):
        """WhatsApp should truncate at absolute limit."""
        long_message = "A" * 2000
        result = self.formatter.format(long_message, "whatsapp")
        assert len(result) <= 1600

    def test_web_format_has_greeting_and_footer(self):
        """Web response should have semi-formal greeting and footer."""
        result = self.formatter.format(
            "Here is your answer.", "web", "Bob", "TKT-002"
        )
        assert "Hi Bob" in result
        assert "Support Center" in result
        assert "TKT-002" in result

    def test_web_format_default_name(self):
        """Web with no name should use 'there'."""
        result = self.formatter.format("Hello.", "web")
        assert "Hi there" in result

    def test_unknown_channel_passthrough(self):
        """Unknown channel should return message as-is."""
        result = self.formatter.format("Hello.", "smoke_signal")
        assert result == "Hello."


class TestWhatsAppMessageSplitting:
    """Test WhatsApp message splitting at sentence boundaries."""

    def setup_method(self):
        self.formatter = ChannelFormatter()

    def test_short_message_not_split(self):
        """Messages under 1600 chars should not be split."""
        parts = self.formatter.split_whatsapp_message("Short message.")
        assert len(parts) == 1

    def test_long_message_split(self):
        """Messages over 1600 chars should be split into multiple parts."""
        sentences = ["This is sentence number {i}. " for i in range(100)]
        long_message = "".join(sentences)
        parts = self.formatter.split_whatsapp_message(long_message)
        assert len(parts) >= 2
        for part in parts:
            assert len(part) <= 1600

    def test_split_at_sentence_boundaries(self):
        """Split should happen at sentence boundaries, not mid-word."""
        message = ("First sentence. " * 50) + ("Second sentence. " * 50)
        parts = self.formatter.split_whatsapp_message(message)
        for part in parts:
            # Each part should end with a sentence terminator or be the last part
            stripped = part.strip()
            assert (
                stripped.endswith(".")
                or stripped.endswith("!")
                or stripped.endswith("?")
                or stripped.endswith("...")
                or part == parts[-1]  # last part can end anywhere
            )


# ---- Gmail Handler Tests ----


class TestGmailWebhook:
    """Test Gmail webhook endpoint processing."""

    def _make_pubsub_payload(self, email: str = "user@example.com", history_id: str = "12345"):
        """Create a valid Pub/Sub notification payload."""
        notification = json.dumps({
            "emailAddress": email,
            "historyId": history_id,
        })
        encoded = base64.b64encode(notification.encode("utf-8")).decode("utf-8")
        return {
            "message": {"data": encoded, "messageId": "msg-001"},
            "subscription": "projects/test/subscriptions/gmail-push",
        }

    @pytest.mark.asyncio
    async def test_gmail_webhook_accepts_valid_pubsub(self):
        """Gmail webhook should accept a valid Pub/Sub notification."""
        from production.channels.gmail_handler import gmail_webhook
        from fastapi import Request
        from unittest.mock import AsyncMock

        payload = self._make_pubsub_payload()

        mock_request = AsyncMock(spec=Request)
        mock_request.json = AsyncMock(return_value=payload)

        with patch("production.channels.gmail_handler._fetch_gmail_message", return_value=None):
            result = await gmail_webhook(mock_request)
        assert result["status"] == "accepted"
        assert "gmail_12345" in result["message_id"]

    @pytest.mark.asyncio
    async def test_gmail_webhook_rejects_empty_data(self):
        """Gmail webhook should reject notification with empty data."""
        from production.channels.gmail_handler import gmail_webhook
        from fastapi import Request, HTTPException

        payload = {
            "message": {"data": "", "messageId": "msg-002"},
            "subscription": "projects/test/subscriptions/gmail-push",
        }
        mock_request = AsyncMock(spec=Request)
        mock_request.json = AsyncMock(return_value=payload)

        with pytest.raises(HTTPException) as exc_info:
            await gmail_webhook(mock_request)
        assert exc_info.value.status_code == 400

    def test_gmail_parse_email_extracts_fields(self):
        """Email parser should extract from, subject, body correctly."""
        from production.channels.gmail_handler import _parse_email

        message = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice <alice@example.com>"},
                    {"name": "Subject", "value": "Need help with API"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        b"I need help with API authentication"
                    ).decode("utf-8")
                },
            },
            "threadId": "thread_123",
            "id": "msg_456",
        }
        result = _parse_email(message)
        assert result["from_email"] == "alice@example.com"
        assert result["from_name"] == "Alice"
        assert result["subject"] == "Need help with API"
        assert "API authentication" in result["body"]
        assert result["thread_id"] == "thread_123"

    def test_gmail_parse_email_no_name(self):
        """Should handle From header with email only (no name)."""
        from production.channels.gmail_handler import _parse_email

        message = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "plain@example.com"},
                    {"name": "Subject", "value": "Test"},
                ],
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(b"Hello").decode("utf-8")},
            },
            "threadId": "t1",
            "id": "m1",
        }
        result = _parse_email(message)
        assert result["from_email"] == "plain@example.com"

    def test_gmail_extract_body_multipart(self):
        """Should extract plain text from multipart email."""
        from production.channels.gmail_handler import _extract_body

        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            b"Plain text content"
                        ).decode("utf-8")
                    },
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            b"<p>HTML content</p>"
                        ).decode("utf-8")
                    },
                },
            ],
        }
        body = _extract_body(payload)
        assert body == "Plain text content"


# ---- WhatsApp Handler Tests ----


class TestWhatsAppWebhook:
    """Test WhatsApp/Twilio webhook processing and signature validation."""

    @pytest.mark.asyncio
    async def test_whatsapp_rejects_invalid_signature(self):
        """WhatsApp webhook should return 403 for invalid Twilio signature."""
        from production.channels.whatsapp_handler import whatsapp_webhook
        from fastapi import HTTPException

        mock_request = AsyncMock()
        mock_request.form = AsyncMock(return_value={
            "Body": "Hello",
            "From": "whatsapp:+1234567890",
        })
        mock_request.headers = {"X-Twilio-Signature": "invalid_sig"}
        mock_request.url = "https://example.com/webhooks/whatsapp"

        with patch(
            "production.channels.whatsapp_handler._validate_twilio_signature",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await whatsapp_webhook(mock_request)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_whatsapp_rejects_empty_body(self):
        """WhatsApp webhook should return 400 for empty message body."""
        from production.channels.whatsapp_handler import whatsapp_webhook
        from fastapi import HTTPException

        mock_request = AsyncMock()
        mock_request.form = AsyncMock(return_value={
            "Body": "",
            "From": "whatsapp:+1234567890",
        })
        mock_request.headers = {"X-Twilio-Signature": "valid"}
        mock_request.url = "https://example.com/webhooks/whatsapp"

        with patch(
            "production.channels.whatsapp_handler._validate_twilio_signature",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await whatsapp_webhook(mock_request)
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_whatsapp_accepts_valid_message(self):
        """WhatsApp webhook should process valid message and return accepted."""
        from production.channels.whatsapp_handler import whatsapp_webhook

        mock_request = AsyncMock()
        mock_request.form = AsyncMock(return_value={
            "Body": "Hello, I need help",
            "From": "whatsapp:+1234567890",
            "ProfileName": "Test User",
            "WaId": "1234567890",
            "NumMedia": "0",
        })
        mock_request.headers = {"X-Twilio-Signature": "valid"}
        mock_request.url = "https://example.com/webhooks/whatsapp"

        with patch(
            "production.channels.whatsapp_handler._validate_twilio_signature",
            return_value=True,
        ):
            with patch("production.kafka_client.publish", new_callable=AsyncMock):
                result = await whatsapp_webhook(mock_request)
        assert result["status"] == "accepted"
        assert "wa_1234567890" in result["message_id"]

    def test_whatsapp_phone_extraction(self):
        """Should strip whatsapp: prefix from phone number."""
        raw = "whatsapp:+1234567890"
        phone = raw.replace("whatsapp:", "").strip()
        assert phone == "+1234567890"


# ---- Web Form Handler Tests ----


class TestWebFormValidation:
    """Test web form Pydantic validation."""

    def test_valid_submission(self):
        """Valid form data should pass validation."""
        from production.channels.web_form_handler import SupportFormInput

        form = SupportFormInput(
            name="Alice Smith",
            email="alice@example.com",
            subject="Help with API key",
            category="Technical Support",
            priority="high",
            message="I cannot generate an API key from my dashboard.",
        )
        assert form.name == "Alice Smith"
        assert form.email == "alice@example.com"
        assert form.priority == "high"

    def test_rejects_short_name(self):
        """Name shorter than 2 chars should fail validation."""
        from production.channels.web_form_handler import SupportFormInput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SupportFormInput(
                name="A",
                email="alice@example.com",
                subject="Valid subject",
                category="General Inquiry",
                message="Valid message content here",
            )

    def test_rejects_invalid_email(self):
        """Invalid email format should fail validation."""
        from production.channels.web_form_handler import SupportFormInput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SupportFormInput(
                name="Alice",
                email="not-an-email",
                subject="Valid subject",
                category="General Inquiry",
                message="Valid message content here",
            )

    def test_rejects_short_subject(self):
        """Subject shorter than 5 chars should fail validation."""
        from production.channels.web_form_handler import SupportFormInput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SupportFormInput(
                name="Alice",
                email="alice@example.com",
                subject="Hi",
                category="General Inquiry",
                message="Valid message content here",
            )

    def test_rejects_short_message(self):
        """Message shorter than 10 chars should fail validation."""
        from production.channels.web_form_handler import SupportFormInput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SupportFormInput(
                name="Alice",
                email="alice@example.com",
                subject="Valid subject",
                category="General Inquiry",
                message="Short",
            )

    def test_rejects_invalid_category(self):
        """Invalid category should fail validation."""
        from production.channels.web_form_handler import SupportFormInput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SupportFormInput(
                name="Alice",
                email="alice@example.com",
                subject="Valid subject",
                category="InvalidCategory",
                message="Valid message content here",
            )

    def test_rejects_invalid_priority(self):
        """Invalid priority should fail validation."""
        from production.channels.web_form_handler import SupportFormInput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SupportFormInput(
                name="Alice",
                email="alice@example.com",
                subject="Valid subject",
                category="General Inquiry",
                priority="super_urgent",
                message="Valid message content here",
            )

    def test_email_lowercased(self):
        """Email should be lowercased by validator."""
        from production.channels.web_form_handler import SupportFormInput

        form = SupportFormInput(
            name="Alice",
            email="Alice@Example.COM",
            subject="Valid subject",
            category="General Inquiry",
            message="Valid message content here",
        )
        assert form.email == "alice@example.com"
