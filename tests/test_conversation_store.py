"""Tests for US3: Conversation store (in-memory state)."""

import pytest
from src.models import Channel, Customer, Conversation, Message, Ticket
from src.memory.conversation_store import ConversationStore


@pytest.fixture
def store():
    return ConversationStore()


class TestCustomerOperations:
    def test_add_and_get_customer(self, store):
        customer = Customer(email="alice@test.com", name="Alice")
        store.add_customer(customer)
        found = store.get_customer_by_email("alice@test.com")
        assert found is not None
        assert found.name == "Alice"

    def test_get_unknown_customer_returns_none(self, store):
        assert store.get_customer_by_email("nobody@test.com") is None

    def test_customer_email_lookup_case_insensitive(self, store):
        customer = Customer(email="alice@test.com")
        store.add_customer(customer)
        assert store.get_customer_by_email("Alice@Test.com") is not None


class TestConversationOperations:
    def test_create_conversation(self, store):
        customer = Customer(email="bob@test.com")
        store.add_customer(customer)
        conv = store.create_conversation(customer.id, Channel.EMAIL)
        assert conv.status == "active"
        assert conv.initial_channel == Channel.EMAIL

    def test_get_conversation(self, store):
        customer = Customer(email="bob@test.com")
        store.add_customer(customer)
        conv = store.create_conversation(customer.id, Channel.WHATSAPP)
        found = store.get_conversation(conv.id)
        assert found is not None
        assert found.id == conv.id

    def test_get_conversations_by_customer(self, store):
        customer = Customer(email="carol@test.com")
        store.add_customer(customer)
        store.create_conversation(customer.id, Channel.EMAIL)
        store.create_conversation(customer.id, Channel.WHATSAPP)
        convs = store.get_conversations_by_customer(customer.id)
        assert len(convs) == 2

    def test_update_conversation_status(self, store):
        customer = Customer(email="dave@test.com")
        store.add_customer(customer)
        conv = store.create_conversation(customer.id, Channel.WEB_FORM)
        store.update_conversation_status(conv.id, "resolved")
        found = store.get_conversation(conv.id)
        assert found.status == "resolved"


class TestMessageOperations:
    def test_add_message_to_conversation(self, store):
        customer = Customer(email="eve@test.com")
        store.add_customer(customer)
        conv = store.create_conversation(customer.id, Channel.EMAIL)
        msg = Message(
            conversation_id=conv.id,
            channel=Channel.EMAIL,
            direction="inbound",
            role="customer",
            content="Hello, I need help",
        )
        store.add_message(msg)
        messages = store.get_messages(conv.id)
        assert len(messages) == 1
        assert messages[0].content == "Hello, I need help"

    def test_messages_ordered_by_time(self, store):
        customer = Customer(email="frank@test.com")
        store.add_customer(customer)
        conv = store.create_conversation(customer.id, Channel.WHATSAPP)
        for i in range(3):
            store.add_message(Message(
                conversation_id=conv.id,
                channel=Channel.WHATSAPP,
                direction="inbound",
                role="customer",
                content=f"Message {i}",
            ))
        messages = store.get_messages(conv.id)
        assert len(messages) == 3


class TestTicketOperations:
    def test_create_ticket(self, store):
        ticket = Ticket(customer_id="c1", source_channel=Channel.EMAIL)
        store.add_ticket(ticket)
        found = store.get_ticket(ticket.id)
        assert found is not None
        assert found.status == "open"

    def test_update_ticket_status(self, store):
        ticket = Ticket(customer_id="c1", source_channel=Channel.WHATSAPP)
        store.add_ticket(ticket)
        store.update_ticket_status(ticket.id, "escalated", reason="Legal threat")
        found = store.get_ticket(ticket.id)
        assert found.status == "escalated"
        assert found.escalation_reason == "Legal threat"

    def test_get_tickets_by_customer(self, store):
        store.add_ticket(Ticket(customer_id="c1", source_channel=Channel.EMAIL))
        store.add_ticket(Ticket(customer_id="c1", source_channel=Channel.WHATSAPP))
        store.add_ticket(Ticket(customer_id="c2", source_channel=Channel.EMAIL))
        tickets = store.get_tickets_by_customer("c1")
        assert len(tickets) == 2


class TestIdentifierMapping:
    def test_map_phone_to_customer(self, store):
        customer = Customer(email="grace@test.com", phone="+1234567890")
        store.add_customer(customer)
        store.add_identifier("phone", "+1234567890", customer.id)
        found_id = store.resolve_customer_id("phone", "+1234567890")
        assert found_id == customer.id

    def test_unknown_identifier_returns_none(self, store):
        assert store.resolve_customer_id("phone", "+0000000000") is None
