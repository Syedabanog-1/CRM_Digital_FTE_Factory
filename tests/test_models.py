"""Tests for foundational Pydantic data models."""

import pytest
from src.models import (
    Channel,
    ChannelConfig,
    CHANNEL_CONFIGS,
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    KnowledgeBaseEntry,
)


# --- Channel Tests ---

class TestChannel:
    def test_channel_values(self):
        assert Channel.EMAIL == "email"
        assert Channel.WHATSAPP == "whatsapp"
        assert Channel.WEB_FORM == "web_form"

    def test_channel_configs_exist_for_all(self):
        for ch in Channel:
            assert ch in CHANNEL_CONFIGS

    def test_email_config(self):
        cfg = CHANNEL_CONFIGS[Channel.EMAIL]
        assert cfg.tone == "formal"
        assert cfg.greeting is True
        assert cfg.signature is True

    def test_whatsapp_config(self):
        cfg = CHANNEL_CONFIGS[Channel.WHATSAPP]
        assert cfg.tone == "conversational"
        assert cfg.greeting is False
        assert cfg.max_length == 300


# --- Customer Tests ---

class TestCustomer:
    def test_valid_customer(self):
        c = Customer(email="test@example.com", name="Alice")
        assert c.email == "test@example.com"
        assert c.name == "Alice"
        assert c.id  # auto-generated

    def test_email_normalized_to_lowercase(self):
        c = Customer(email="Test@Example.COM")
        assert c.email == "test@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValueError):
            Customer(email="not-an-email")

    def test_phone_requires_country_code(self):
        with pytest.raises(ValueError):
            Customer(email="a@b.com", phone="1234567890")

    def test_valid_phone(self):
        c = Customer(email="a@b.com", phone="+1234567890")
        assert c.phone == "+1234567890"

    def test_phone_optional(self):
        c = Customer(email="a@b.com")
        assert c.phone is None


# --- CustomerIdentifier Tests ---

class TestCustomerIdentifier:
    def test_valid_identifier(self):
        ci = CustomerIdentifier(
            identifier_type="phone",
            identifier_value="+1234567890",
            customer_id="abc",
        )
        assert ci.verified is False

    def test_invalid_type_rejected(self):
        with pytest.raises(ValueError):
            CustomerIdentifier(
                identifier_type="fax",
                identifier_value="123",
                customer_id="abc",
            )


# --- Conversation Tests ---

class TestConversation:
    def test_defaults(self):
        conv = Conversation(customer_id="c1", initial_channel=Channel.EMAIL)
        assert conv.status == "active"
        assert conv.sentiment_score is None
        assert conv.topics == []

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            Conversation(
                customer_id="c1",
                initial_channel=Channel.EMAIL,
                status="pending",
            )

    def test_valid_status_transitions(self):
        for s in ("active", "resolved", "escalated"):
            conv = Conversation(
                customer_id="c1", initial_channel=Channel.EMAIL, status=s
            )
            assert conv.status == s

    def test_invalid_resolution_type(self):
        with pytest.raises(ValueError):
            Conversation(
                customer_id="c1",
                initial_channel=Channel.EMAIL,
                resolution_type="unknown",
            )


# --- Message Tests ---

class TestMessage:
    def test_valid_message(self):
        m = Message(
            conversation_id="conv1",
            channel=Channel.WHATSAPP,
            direction="inbound",
            role="customer",
            content="Hello",
        )
        assert m.content == "Hello"

    def test_empty_content_rejected(self):
        with pytest.raises(ValueError):
            Message(
                conversation_id="conv1",
                channel=Channel.EMAIL,
                direction="inbound",
                role="customer",
                content="",
            )

    def test_whitespace_only_content_rejected(self):
        with pytest.raises(ValueError):
            Message(
                conversation_id="conv1",
                channel=Channel.EMAIL,
                direction="inbound",
                role="customer",
                content="   ",
            )

    def test_invalid_direction(self):
        with pytest.raises(ValueError):
            Message(
                conversation_id="conv1",
                channel=Channel.EMAIL,
                direction="sideways",
                role="customer",
                content="Hi",
            )

    def test_invalid_role(self):
        with pytest.raises(ValueError):
            Message(
                conversation_id="conv1",
                channel=Channel.EMAIL,
                direction="inbound",
                role="bot",
                content="Hi",
            )


# --- Ticket Tests ---

class TestTicket:
    def test_defaults(self):
        t = Ticket(customer_id="c1", source_channel=Channel.WEB_FORM)
        assert t.status == "open"
        assert t.priority == "medium"

    def test_valid_status_transitions(self):
        for s in ("open", "in_progress", "escalated", "resolved", "closed"):
            t = Ticket(customer_id="c1", source_channel=Channel.EMAIL, status=s)
            assert t.status == s

    def test_invalid_priority(self):
        with pytest.raises(ValueError):
            Ticket(customer_id="c1", source_channel=Channel.EMAIL, priority="urgent")

    def test_invalid_category(self):
        with pytest.raises(ValueError):
            Ticket(customer_id="c1", source_channel=Channel.EMAIL, category="spam")


# --- KnowledgeBaseEntry Tests ---

class TestKnowledgeBaseEntry:
    def test_basic_entry(self):
        entry = KnowledgeBaseEntry(title="Reset Password", content="Go to settings...")
        assert entry.title == "Reset Password"
        assert entry.keywords == []

    def test_with_keywords(self):
        entry = KnowledgeBaseEntry(
            title="API Access",
            content="Use the REST API...",
            keywords=["api", "rest", "integration"],
        )
        assert len(entry.keywords) == 3
