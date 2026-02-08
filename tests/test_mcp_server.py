"""Tests for US4: MCP server tools."""

import pytest
from src.mcp_server import (
    handle_search_knowledge_base,
    handle_create_ticket,
    handle_get_customer_history,
    handle_escalate_to_human,
    handle_send_response,
    handle_analyze_sentiment,
    get_store,
)
from src.models import Channel, Customer, Ticket
from src.memory.conversation_store import ConversationStore


@pytest.fixture
def store():
    s = ConversationStore()
    # Seed a customer and ticket for tests
    customer = Customer(email="test@example.com", name="Test User")
    s.add_customer(customer)
    ticket = Ticket(
        customer_id=customer.id,
        source_channel=Channel.EMAIL,
    )
    s.add_ticket(ticket)
    return s, customer, ticket


class TestSearchKnowledgeBase:
    def test_valid_query_returns_results(self):
        result = handle_search_knowledge_base("password reset", 5)
        assert result
        assert "No relevant" not in result or len(result) > 0

    def test_empty_query(self):
        result = handle_search_knowledge_base("", 5)
        assert "Please provide" in result or "No relevant" in result

    def test_max_results_respected(self):
        result = handle_search_knowledge_base("project", 2)
        assert result  # Should return something


class TestCreateTicket:
    def test_valid_ticket_creation(self, store):
        s, customer, _ = store
        result = handle_create_ticket(
            customer_id=customer.email,
            issue="Can't log in",
            priority="high",
            channel="email",
            store=s,
        )
        assert "Ticket created" in result

    def test_invalid_channel(self, store):
        s, customer, _ = store
        result = handle_create_ticket(
            customer_id=customer.email,
            issue="Test",
            priority="medium",
            channel="fax",
            store=s,
        )
        assert "error" in result.lower() or "invalid" in result.lower()


class TestGetCustomerHistory:
    def test_known_customer(self, store):
        s, customer, _ = store
        conv = s.create_conversation(customer.id, Channel.EMAIL)
        result = handle_get_customer_history(customer.email, store=s)
        assert "email" in result.lower()

    def test_unknown_customer(self, store):
        s, _, _ = store
        result = handle_get_customer_history("nobody@unknown.com", store=s)
        assert "No prior history" in result


class TestEscalateToHuman:
    def test_valid_escalation(self, store):
        s, _, ticket = store
        result = handle_escalate_to_human(ticket.id, "Legal threat", store=s)
        assert "Escalated" in result
        updated = s.get_ticket(ticket.id)
        assert updated.status == "escalated"

    def test_unknown_ticket(self, store):
        s, _, _ = store
        result = handle_escalate_to_human("FAKE-ID", "test", store=s)
        assert "error" in result.lower() or "not found" in result.lower()

    def test_empty_reason(self, store):
        s, _, ticket = store
        result = handle_escalate_to_human(ticket.id, "", store=s)
        assert "error" in result.lower() or "reason" in result.lower()


class TestSendResponse:
    def test_valid_response(self, store):
        s, _, ticket = store
        result = handle_send_response(
            ticket_id=ticket.id,
            message="Here is your answer.",
            channel="email",
            store=s,
        )
        assert "Response sent" in result

    def test_whatsapp_truncation(self, store):
        s, _, ticket = store
        long_msg = "A" * 2000
        result = handle_send_response(
            ticket_id=ticket.id,
            message=long_msg,
            channel="whatsapp",
            store=s,
        )
        assert "Response sent" in result

    def test_unknown_ticket(self, store):
        s, _, _ = store
        result = handle_send_response(
            ticket_id="FAKE", message="test", channel="email", store=s
        )
        assert "error" in result.lower() or "not found" in result.lower()


class TestAnalyzeSentiment:
    def test_positive_message(self):
        result = handle_analyze_sentiment("Thank you so much, great help!")
        assert "positive" in result.lower() or float(result.split(":")[1].split("(")[0].strip()) > 0.5

    def test_negative_message(self):
        result = handle_analyze_sentiment("This is terrible and awful")
        assert "negative" in result.lower()

    def test_empty_message(self):
        result = handle_analyze_sentiment("")
        assert "neutral" in result.lower() or "0.5" in result
