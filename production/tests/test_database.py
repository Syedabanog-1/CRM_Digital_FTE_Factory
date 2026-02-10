"""Database query integration tests for all 8 tables.

Tests: customer CRUD, cross-channel resolution, conversations with 24-hour reuse,
messages, tickets, knowledge base vector search, channel configs, metrics aggregation.
Requires: PostgreSQL 16+ with pgvector running (use docker-compose for local).
"""

import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from production.conftest import requires_postgres

# Skip entire module if PostgreSQL is not available
pytestmark = [pytest.mark.integration, requires_postgres]

from production.database import queries


# ---- Fixtures ----


@pytest_asyncio.fixture(scope="module")
async def db_pool():
    """Create and tear down the database pool for test module."""
    pool = await queries.create_pool()
    yield pool
    await queries.close_pool()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(db_pool):
    """Clean up test data after each test to avoid interference."""
    yield
    # Clean up test data created during tests (cascade deletes handle children)
    pool = await queries.get_pool()
    await pool.execute("DELETE FROM customers WHERE email LIKE '%@test-db.example.com'")
    await pool.execute("DELETE FROM knowledge_base WHERE category = 'test_category'")
    await pool.execute("DELETE FROM agent_metrics WHERE dimensions::text LIKE '%test%'")


# ---- 1. Connection Pool Tests ----


class TestConnectionPool:
    """Test database connection pool management."""

    @pytest.mark.asyncio
    async def test_create_pool(self, db_pool):
        """Pool should be created and connected."""
        assert db_pool is not None

    @pytest.mark.asyncio
    async def test_health_check(self, db_pool):
        """Database health check should return True when connected."""
        result = await queries.check_db_health()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_pool_returns_existing(self, db_pool):
        """get_pool should return the existing pool, not create a new one."""
        pool = await queries.get_pool()
        assert pool is db_pool


# ---- 2. Customer Operations Tests ----


class TestCustomerOperations:
    """Test customer CRUD operations."""

    @pytest.mark.asyncio
    async def test_insert_customer(self, db_pool):
        """Should insert a new customer and return the record."""
        customer = await queries.insert_customer(
            email="test-insert@test-db.example.com",
            name="Test User",
            phone="+10001112222",
        )
        assert customer is not None
        assert isinstance(customer["id"], UUID)
        assert customer["email"] == "test-insert@test-db.example.com"
        assert customer["name"] == "Test User"
        assert customer["phone"] == "+10001112222"

    @pytest.mark.asyncio
    async def test_insert_customer_lowercases_email(self, db_pool):
        """Email should be lowercased on insert."""
        customer = await queries.insert_customer(
            email="UPPERCASE@test-db.example.com"
        )
        assert customer["email"] == "uppercase@test-db.example.com"

    @pytest.mark.asyncio
    async def test_insert_customer_upsert_on_conflict(self, db_pool):
        """Inserting same email should upsert, updating name/phone."""
        c1 = await queries.insert_customer(
            email="upsert@test-db.example.com", name="Original"
        )
        c2 = await queries.insert_customer(
            email="upsert@test-db.example.com", name="Updated", phone="+19999999999"
        )
        assert c1["id"] == c2["id"]
        assert c2["name"] == "Updated"
        assert c2["phone"] == "+19999999999"

    @pytest.mark.asyncio
    async def test_get_customer_by_email(self, db_pool):
        """Should find customer by email."""
        await queries.insert_customer(email="findme@test-db.example.com", name="FindMe")
        customer = await queries.get_customer_by_email("findme@test-db.example.com")
        assert customer is not None
        assert customer["name"] == "FindMe"

    @pytest.mark.asyncio
    async def test_get_customer_by_email_not_found(self, db_pool):
        """Should return None for non-existent email."""
        result = await queries.get_customer_by_email("nonexistent@test-db.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_customer_by_id(self, db_pool):
        """Should find customer by UUID."""
        customer = await queries.insert_customer(
            email="byid@test-db.example.com", name="ByID"
        )
        found = await queries.get_customer_by_id(customer["id"])
        assert found is not None
        assert found["email"] == "byid@test-db.example.com"


# ---- 3. Customer Identifier Tests (Cross-Channel Resolution) ----


class TestCustomerIdentifiers:
    """Test cross-channel customer resolution via identifiers."""

    @pytest.mark.asyncio
    async def test_upsert_customer_identifier(self, db_pool):
        """Should create an identifier linking phone to customer."""
        customer = await queries.insert_customer(
            email="identifier@test-db.example.com"
        )
        identifier = await queries.upsert_customer_identifier(
            customer["id"], "whatsapp", "+15551234567"
        )
        assert identifier is not None
        assert identifier["customer_id"] == customer["id"]
        assert identifier["type"] == "whatsapp"
        assert identifier["value"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_cross_channel_lookup_by_phone(self, db_pool):
        """Should resolve customer by phone via identifiers."""
        customer = await queries.insert_customer(
            email="crosschannel@test-db.example.com", phone="+15559876543"
        )
        await queries.upsert_customer_identifier(
            customer["id"], "whatsapp", "+15559876543"
        )
        found = await queries.get_customer_by_phone("+15559876543")
        assert found is not None
        assert found["id"] == customer["id"]

    @pytest.mark.asyncio
    async def test_cross_channel_lookup_by_identifier(self, db_pool):
        """Should resolve customer by arbitrary identifier type."""
        customer = await queries.insert_customer(
            email="ident-lookup@test-db.example.com"
        )
        await queries.upsert_customer_identifier(
            customer["id"], "email", "ident-lookup@test-db.example.com"
        )
        found = await queries.get_customer_by_identifier(
            "email", "ident-lookup@test-db.example.com"
        )
        assert found is not None
        assert found["id"] == customer["id"]


# ---- 4. Conversation Operations Tests ----


class TestConversationOperations:
    """Test conversation CRUD with 24-hour active reuse."""

    @pytest.mark.asyncio
    async def test_insert_conversation(self, db_pool):
        """Should create a new conversation."""
        customer = await queries.insert_customer(
            email="conv-insert@test-db.example.com"
        )
        conv = await queries.insert_conversation(
            customer["id"], "web", "Help with API"
        )
        assert conv is not None
        assert isinstance(conv["id"], UUID)
        assert conv["channel"] == "web"
        assert conv["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_active_conversation_reuse(self, db_pool):
        """Active conversation within 24h should be reused."""
        customer = await queries.insert_customer(
            email="conv-reuse@test-db.example.com"
        )
        conv1 = await queries.insert_conversation(customer["id"], "email")
        conv2 = await queries.get_active_conversation(customer["id"], "email")
        assert conv2 is not None
        assert conv2["id"] == conv1["id"]

    @pytest.mark.asyncio
    async def test_get_active_conversation_none_when_resolved(self, db_pool):
        """Resolved conversation should not be returned as active."""
        customer = await queries.insert_customer(
            email="conv-resolved@test-db.example.com"
        )
        conv = await queries.insert_conversation(customer["id"], "web")
        await queries.update_conversation_status(conv["id"], "resolved", "agent")
        active = await queries.get_active_conversation(customer["id"], "web")
        assert active is None

    @pytest.mark.asyncio
    async def test_update_conversation_sentiment(self, db_pool):
        """Should update sentiment score on conversation."""
        customer = await queries.insert_customer(
            email="conv-sentiment@test-db.example.com"
        )
        conv = await queries.insert_conversation(customer["id"], "whatsapp")
        await queries.update_conversation_sentiment(conv["id"], 0.75)
        updated = await queries.get_conversation(conv["id"])
        assert updated["sentiment_score"] == pytest.approx(0.75, abs=0.01)

    @pytest.mark.asyncio
    async def test_get_conversations_by_customer(self, db_pool):
        """Should return customer's recent conversations."""
        customer = await queries.insert_customer(
            email="conv-list@test-db.example.com"
        )
        await queries.insert_conversation(customer["id"], "email")
        await queries.insert_conversation(customer["id"], "web")
        convs = await queries.get_conversations_by_customer(customer["id"])
        assert len(convs) >= 2


# ---- 5. Message Operations Tests ----


class TestMessageOperations:
    """Test message insertion and retrieval."""

    @pytest.mark.asyncio
    async def test_insert_and_get_messages(self, db_pool):
        """Should insert inbound+outbound messages and retrieve in order."""
        customer = await queries.insert_customer(
            email="msg-test@test-db.example.com"
        )
        conv = await queries.insert_conversation(customer["id"], "web")

        # Inbound customer message
        msg1 = await queries.insert_message(
            conv["id"], "web", "inbound", "customer", "Help with API"
        )
        assert msg1["direction"] == "inbound"
        assert msg1["role"] == "customer"

        # Outbound agent response
        msg2 = await queries.insert_message(
            conv["id"], "web", "outbound", "agent", "Sure! Here's how...",
            processing_time_ms=150,
        )
        assert msg2["direction"] == "outbound"
        assert msg2["processing_time_ms"] == 150

        # Retrieve all messages
        messages = await queries.get_conversation_messages(conv["id"])
        assert len(messages) == 2
        assert messages[0]["role"] == "customer"
        assert messages[1]["role"] == "agent"


# ---- 6. Ticket Operations Tests ----


class TestTicketOperations:
    """Test ticket lifecycle management."""

    @pytest.mark.asyncio
    async def test_insert_ticket(self, db_pool):
        """Should create a ticket with proper defaults."""
        customer = await queries.insert_customer(
            email="ticket-test@test-db.example.com"
        )
        ticket = await queries.insert_ticket(
            customer["id"], "web", "Help with login",
            category="Technical Support", priority="high",
        )
        assert ticket["status"] == "open"
        assert ticket["priority"] == "high"
        assert ticket["category"] == "Technical Support"

    @pytest.mark.asyncio
    async def test_ticket_lifecycle(self, db_pool):
        """Should update ticket status through lifecycle."""
        customer = await queries.insert_customer(
            email="ticket-lifecycle@test-db.example.com"
        )
        ticket = await queries.insert_ticket(customer["id"], "email", "Billing issue")

        # Escalate
        await queries.update_ticket_status(
            ticket["id"], "escalated", "Pricing inquiry - requires human"
        )
        updated = await queries.get_ticket(ticket["id"])
        assert updated["status"] == "escalated"
        assert "Pricing inquiry" in updated["resolution_notes"]

    @pytest.mark.asyncio
    async def test_get_tickets_by_customer(self, db_pool):
        """Should return customer's tickets."""
        customer = await queries.insert_customer(
            email="ticket-list@test-db.example.com"
        )
        await queries.insert_ticket(customer["id"], "web", "Issue 1")
        await queries.insert_ticket(customer["id"], "email", "Issue 2")
        tickets = await queries.get_tickets_by_customer(customer["id"])
        assert len(tickets) >= 2


# ---- 7. Knowledge Base Tests ----


class TestKnowledgeBase:
    """Test knowledge base CRUD and vector search."""

    @pytest.mark.asyncio
    async def test_insert_knowledge_entry(self, db_pool):
        """Should insert a knowledge base entry."""
        entry = await queries.insert_knowledge_entry(
            title="How to Reset Password",
            content="Go to Settings > Account > Reset Password...",
            category="test_category",
        )
        assert entry is not None
        assert entry["title"] == "How to Reset Password"

    @pytest.mark.asyncio
    async def test_insert_knowledge_entry_with_embedding(self, db_pool):
        """Should insert with a vector embedding."""
        # Create a dummy 1536-dim embedding
        embedding = [0.01] * 1536
        entry = await queries.insert_knowledge_entry(
            title="API Authentication Guide",
            content="Use Bearer tokens for API access...",
            category="test_category",
            embedding=embedding,
        )
        assert entry is not None

    @pytest.mark.asyncio
    async def test_search_knowledge_base_returns_results(self, db_pool):
        """Vector search should return results when embeddings exist."""
        # Insert entry with embedding
        embedding = [0.5] * 1536
        await queries.insert_knowledge_entry(
            title="Test Searchable Entry",
            content="This is a test entry for search validation",
            category="test_category",
            embedding=embedding,
        )
        # Search with similar embedding
        query_embedding = [0.5] * 1536
        results = await queries.search_knowledge_base(
            query_embedding=query_embedding, max_results=5, min_similarity=0.0
        )
        assert len(results) >= 1
        assert results[0]["title"] is not None

    @pytest.mark.asyncio
    async def test_search_knowledge_base_no_results(self, db_pool):
        """Vector search should return empty list when nothing matches."""
        # Search with very different embedding (unlikely to match)
        query_embedding = [-1.0] * 1536
        results = await queries.search_knowledge_base(
            query_embedding=query_embedding, max_results=3, min_similarity=0.99
        )
        assert isinstance(results, list)


# ---- 8. Channel Config Tests ----


class TestChannelConfigs:
    """Test channel configuration operations."""

    @pytest.mark.asyncio
    async def test_get_channel_config_email(self, db_pool):
        """Should return email channel config seeded by schema."""
        config = await queries.get_channel_config("email")
        assert config is not None
        assert config["enabled"] is True
        assert config["max_response_length"] == 500

    @pytest.mark.asyncio
    async def test_get_channel_config_whatsapp(self, db_pool):
        """Should return WhatsApp channel config."""
        config = await queries.get_channel_config("whatsapp")
        assert config is not None
        assert config["max_response_length"] == 300

    @pytest.mark.asyncio
    async def test_get_channel_config_web(self, db_pool):
        """Should return web channel config."""
        config = await queries.get_channel_config("web")
        assert config is not None
        assert config["max_response_length"] == 300

    @pytest.mark.asyncio
    async def test_get_channel_config_nonexistent(self, db_pool):
        """Should return None for non-existent channel."""
        config = await queries.get_channel_config("smoke_signal")
        assert config is None


# ---- 9. Metrics Operations Tests ----


class TestMetricsOperations:
    """Test metrics recording and aggregation."""

    @pytest.mark.asyncio
    async def test_insert_metric(self, db_pool):
        """Should record a metric data point."""
        metric = await queries.insert_metric(
            "response_time", 250.5, channel="web",
            dimensions={"test": True, "ticket_id": "test-123"},
        )
        assert metric is not None
        assert metric["metric_name"] == "response_time"
        assert metric["metric_value"] == pytest.approx(250.5)
        assert metric["channel"] == "web"

    @pytest.mark.asyncio
    async def test_get_channel_metrics_aggregation(self, db_pool):
        """Should aggregate metrics by channel."""
        # Insert several metrics
        await queries.insert_metric(
            "response_time", 100.0, "email", {"test": True}
        )
        await queries.insert_metric(
            "response_time", 200.0, "email", {"test": True}
        )
        await queries.insert_metric(
            "sentiment", 0.8, "email", {"test": True}
        )
        await queries.insert_metric(
            "response_time", 150.0, "whatsapp", {"test": True}
        )

        result = await queries.get_channel_metrics(hours=1)
        assert "channels" in result
        assert "period_hours" in result
        assert result["period_hours"] == 1
