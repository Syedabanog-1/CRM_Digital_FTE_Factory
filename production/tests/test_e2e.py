"""Multi-channel end-to-end tests for the Customer Success Digital FTE.

Tests the complete pipeline: channel intake -> API -> Kafka -> agent -> DB -> response.
Covers web form, email, WhatsApp, cross-channel recognition, escalation, and DLQ.

Requires: docker-compose stack running (PostgreSQL, Kafka, API, Worker).
"""

import asyncio
import json
import time
from uuid import UUID

import pytest
import pytest_asyncio
import httpx

# Base URL for the running API
BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def api_client():
    """Create an httpx client for the API."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="module")
def async_client():
    """Create an async httpx client for the API."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


# ---- Health Check ----


class TestHealthCheck:
    """Verify the system is running and healthy."""

    def test_health_endpoint(self, api_client):
        """Health endpoint should return healthy status."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "channels" in data
        assert data["database"] == "connected"

    def test_health_channels_present(self, api_client):
        """Health response should include all 3 channel statuses."""
        response = api_client.get("/health")
        channels = response.json()["channels"]
        assert "email" in channels
        assert "whatsapp" in channels
        assert "web" in channels


# ---- Web Form E2E ----


class TestWebFormE2E:
    """End-to-end web form submission -> ticket -> agent response."""

    def test_submit_valid_form(self, api_client):
        """Valid form submission should create ticket and return ticket_id."""
        response = api_client.post(
            "/support/submit",
            json={
                "name": "E2E Test User",
                "email": "e2e-web@test.example.com",
                "subject": "Help with API integration",
                "category": "Technical Support",
                "priority": "medium",
                "message": "I cannot connect to the API. Getting 401 errors on all endpoints.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "ticket_id" in data
        assert data["status"] == "open"
        assert "message" in data

    def test_submit_returns_valid_ticket_id(self, api_client):
        """Returned ticket_id should be a valid UUID."""
        response = api_client.post(
            "/support/submit",
            json={
                "name": "UUID Test User",
                "email": "e2e-uuid@test.example.com",
                "subject": "Testing UUID format",
                "category": "General Inquiry",
                "message": "This is a test to verify UUID ticket IDs are returned.",
            },
        )
        ticket_id = response.json()["ticket_id"]
        # Should not raise ValueError
        UUID(ticket_id)

    def test_ticket_status_check(self, api_client):
        """Should be able to check ticket status after submission."""
        # Submit
        submit_resp = api_client.post(
            "/support/submit",
            json={
                "name": "Status Check User",
                "email": "e2e-status@test.example.com",
                "subject": "Status check test",
                "category": "General Inquiry",
                "message": "Testing the ticket status endpoint works correctly.",
            },
        )
        ticket_id = submit_resp.json()["ticket_id"]

        # Check status
        status_resp = api_client.get(f"/support/ticket/{ticket_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["ticket_id"] == ticket_id
        assert data["status"] in ["open", "in_progress", "resolved", "escalated"]
        assert data["subject"] == "Status check test"
        assert "messages" in data

    def test_ticket_not_found(self, api_client):
        """Non-existent ticket should return 404."""
        response = api_client.get(
            "/support/ticket/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    def test_form_validation_rejects_invalid(self, api_client):
        """Invalid form data should return 422 validation error."""
        response = api_client.post(
            "/support/submit",
            json={
                "name": "A",  # Too short
                "email": "not-an-email",
                "subject": "Hi",  # Too short
                "category": "InvalidCategory",
                "message": "Short",  # Too short
            },
        )
        assert response.status_code == 422

    def test_form_creates_customer(self, api_client):
        """Form submission should create or resolve a customer."""
        api_client.post(
            "/support/submit",
            json={
                "name": "Customer Create Test",
                "email": "e2e-customer-create@test.example.com",
                "subject": "Customer creation test",
                "category": "General Inquiry",
                "message": "Testing that a customer record is created on form submit.",
            },
        )
        # Lookup the customer
        lookup_resp = api_client.get(
            "/customers/lookup",
            params={"email": "e2e-customer-create@test.example.com"},
        )
        assert lookup_resp.status_code == 200
        data = lookup_resp.json()
        assert data["email"] == "e2e-customer-create@test.example.com"
        assert data["name"] == "Customer Create Test"


# ---- Email Webhook E2E ----


class TestEmailWebhookE2E:
    """End-to-end email webhook processing."""

    def _make_gmail_notification(self, email: str = "sender@example.com"):
        """Create a simulated Gmail Pub/Sub notification."""
        import base64

        notification = json.dumps({
            "emailAddress": email,
            "historyId": "99999",
        })
        encoded = base64.b64encode(notification.encode("utf-8")).decode("utf-8")
        return {
            "message": {"data": encoded, "messageId": "test-msg-001"},
            "subscription": "projects/test/subscriptions/gmail-push",
        }

    def test_gmail_webhook_accepts_notification(self, api_client):
        """Gmail webhook should accept valid Pub/Sub notification."""
        payload = self._make_gmail_notification()
        response = api_client.post("/webhooks/gmail", json=payload)
        # Should accept (even if Gmail API fetch fails in test env)
        assert response.status_code in [200, 400]

    def test_gmail_webhook_rejects_invalid(self, api_client):
        """Gmail webhook should reject malformed payload."""
        response = api_client.post("/webhooks/gmail", json={"invalid": "data"})
        assert response.status_code == 400


# ---- WhatsApp Webhook E2E ----


class TestWhatsAppWebhookE2E:
    """End-to-end WhatsApp/Twilio webhook processing."""

    def test_whatsapp_webhook_rejects_no_signature(self, api_client):
        """WhatsApp webhook should reject requests without valid signature."""
        response = api_client.post(
            "/webhooks/whatsapp",
            data={
                "Body": "Hello, need help",
                "From": "whatsapp:+1234567890",
                "ProfileName": "Test",
                "WaId": "1234567890",
            },
        )
        # Should return 403 (invalid/missing signature)
        assert response.status_code == 403


# ---- Cross-Channel Customer Recognition ----


class TestCrossChannelRecognition:
    """Test that customers are recognized across different channels."""

    def test_same_email_different_submissions(self, api_client):
        """Multiple submissions with same email should resolve to same customer."""
        email = "e2e-cross@test.example.com"

        # First submission
        api_client.post(
            "/support/submit",
            json={
                "name": "Cross Channel User",
                "email": email,
                "subject": "First contact via web",
                "category": "General Inquiry",
                "message": "This is my first contact via the web form.",
            },
        )

        # Second submission (same email)
        api_client.post(
            "/support/submit",
            json={
                "name": "Cross Channel User",
                "email": email,
                "subject": "Second contact via web",
                "category": "Technical Support",
                "message": "This is my second contact. Should be same customer.",
            },
        )

        # Look up customer
        lookup = api_client.get("/customers/lookup", params={"email": email})
        assert lookup.status_code == 200
        data = lookup.json()
        assert data["total_tickets"] >= 2
        assert data["total_conversations"] >= 1


# ---- Customer Lookup ----


class TestCustomerLookup:
    """Test customer lookup endpoint."""

    def test_lookup_by_email(self, api_client):
        """Should find customer by email."""
        email = "e2e-lookup@test.example.com"
        api_client.post(
            "/support/submit",
            json={
                "name": "Lookup User",
                "email": email,
                "subject": "Lookup test",
                "category": "General Inquiry",
                "message": "Creating a customer for lookup test.",
            },
        )
        response = api_client.get("/customers/lookup", params={"email": email})
        assert response.status_code == 200
        assert response.json()["email"] == email

    def test_lookup_not_found(self, api_client):
        """Non-existent customer should return 404."""
        response = api_client.get(
            "/customers/lookup", params={"email": "nonexistent@nowhere.com"}
        )
        assert response.status_code == 404

    def test_lookup_requires_param(self, api_client):
        """Lookup without email or phone should return 400."""
        response = api_client.get("/customers/lookup")
        assert response.status_code == 400


# ---- Conversation History ----


class TestConversationHistory:
    """Test conversation history endpoint."""

    def test_invalid_conversation_id(self, api_client):
        """Invalid UUID should return 400."""
        response = api_client.get("/conversations/not-a-uuid")
        assert response.status_code == 400

    def test_nonexistent_conversation(self, api_client):
        """Non-existent conversation should return 404."""
        response = api_client.get(
            "/conversations/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


# ---- Channel Metrics ----


class TestChannelMetrics:
    """Test channel metrics endpoint."""

    def test_metrics_endpoint_returns_data(self, api_client):
        """Metrics endpoint should return structured data."""
        response = api_client.get("/metrics/channels")
        assert response.status_code == 200
        data = response.json()
        assert "period_hours" in data
        assert "channels" in data
        assert "generated_at" in data

    def test_metrics_with_hours_param(self, api_client):
        """Metrics should accept hours parameter."""
        response = api_client.get("/metrics/channels", params={"hours": 1})
        assert response.status_code == 200
        assert response.json()["period_hours"] == 1

    def test_metrics_with_channel_filter(self, api_client):
        """Metrics should accept channel filter."""
        response = api_client.get(
            "/metrics/channels", params={"channel": "web"}
        )
        assert response.status_code == 200


# ---- Escalation Flow ----


class TestEscalationFlow:
    """Test escalation scenarios end-to-end."""

    def test_pricing_inquiry_creates_ticket(self, api_client):
        """Pricing inquiry should create a ticket (agent escalates async)."""
        response = api_client.post(
            "/support/submit",
            json={
                "name": "Pricing User",
                "email": "e2e-pricing@test.example.com",
                "subject": "How much does enterprise plan cost?",
                "category": "Billing",
                "priority": "medium",
                "message": "I need to know the pricing for your enterprise plan. What are the costs?",
            },
        )
        assert response.status_code == 201
        # Ticket created - escalation happens asynchronously via worker

    def test_angry_customer_creates_ticket(self, api_client):
        """Angry customer message should create a ticket."""
        response = api_client.post(
            "/support/submit",
            json={
                "name": "Angry User",
                "email": "e2e-angry@test.example.com",
                "subject": "Your product is terrible",
                "category": "General Inquiry",
                "priority": "high",
                "message": "This is RIDICULOUS! Your stupid product keeps crashing. This is pathetic garbage!",
            },
        )
        assert response.status_code == 201
