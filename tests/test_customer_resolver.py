"""Tests for US3: Customer resolver service."""

import pytest
from src.services.customer_resolver import CustomerResolver
from src.memory.conversation_store import ConversationStore


@pytest.fixture
def store():
    return ConversationStore()


@pytest.fixture
def resolver(store):
    return CustomerResolver(store)


class TestEmailLookup:
    def test_resolve_existing_customer_by_email(self, resolver, store):
        from src.models import Customer
        customer = Customer(email="alice@test.com", name="Alice")
        store.add_customer(customer)
        found = resolver.resolve(email="alice@test.com")
        assert found.email == "alice@test.com"
        assert found.name == "Alice"

    def test_create_new_customer_if_unknown(self, resolver):
        found = resolver.resolve(email="new@test.com")
        assert found.email == "new@test.com"
        assert found.id  # should have an ID

    def test_email_lookup_case_insensitive(self, resolver, store):
        from src.models import Customer
        customer = Customer(email="bob@test.com")
        store.add_customer(customer)
        found = resolver.resolve(email="BOB@TEST.COM")
        assert found.id == customer.id


class TestPhoneLookup:
    def test_resolve_by_phone(self, resolver, store):
        from src.models import Customer
        customer = Customer(email="carol@test.com", phone="+1234567890")
        store.add_customer(customer)
        store.add_identifier("phone", "+1234567890", customer.id)
        found = resolver.resolve(phone="+1234567890")
        assert found.email == "carol@test.com"

    def test_unknown_phone_returns_none(self, resolver):
        found = resolver.resolve(phone="+9999999999")
        assert found is None


class TestCrossChannelIdentification:
    def test_same_customer_different_channels(self, resolver, store):
        from src.models import Customer
        customer = Customer(email="dave@test.com", phone="+5551234")
        store.add_customer(customer)
        store.add_identifier("phone", "+5551234", customer.id)

        by_email = resolver.resolve(email="dave@test.com")
        by_phone = resolver.resolve(phone="+5551234")
        assert by_email.id == by_phone.id
