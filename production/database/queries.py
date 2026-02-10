"""Async database access functions using asyncpg for Stage 2 production system."""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from production.config import settings

# Module-level connection pool
_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    """Create and return the database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_min_pool_size,
            max_size=settings.db_max_pool_size,
        )
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Get the existing pool or create one."""
    if _pool is None:
        return await create_pool()
    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ---- Customer Operations ----


async def insert_customer(
    email: str,
    name: str | None = None,
    phone: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Insert a new customer and return the record."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO customers (email, name, phone, metadata)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (email) DO UPDATE SET
            name = COALESCE(EXCLUDED.name, customers.name),
            phone = COALESCE(EXCLUDED.phone, customers.phone),
            updated_at = NOW()
        RETURNING id, email, name, phone, metadata, created_at, updated_at
        """,
        email.lower(),
        name,
        phone,
        json.dumps(metadata or {}),
    )
    return dict(row)


async def get_customer_by_email(email: str) -> dict[str, Any] | None:
    """Lookup customer by email address."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM customers WHERE email = $1", email.lower()
    )
    return dict(row) if row else None


async def get_customer_by_phone(phone: str) -> dict[str, Any] | None:
    """Lookup customer by phone via customer_identifiers."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT c.* FROM customers c
        JOIN customer_identifiers ci ON c.id = ci.customer_id
        WHERE ci.type IN ('phone', 'whatsapp') AND ci.value = $1
        """,
        phone,
    )
    return dict(row) if row else None


async def get_customer_by_id(customer_id: UUID) -> dict[str, Any] | None:
    """Lookup customer by ID."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
    return dict(row) if row else None


# ---- Customer Identifier Operations ----


async def upsert_customer_identifier(
    customer_id: UUID, id_type: str, value: str
) -> dict[str, Any]:
    """Create or update a customer identifier for cross-channel resolution."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO customer_identifiers (customer_id, type, value)
        VALUES ($1, $2, $3)
        ON CONFLICT (type, value) DO UPDATE SET
            customer_id = EXCLUDED.customer_id
        RETURNING id, customer_id, type, value, verified, created_at
        """,
        customer_id,
        id_type,
        value,
    )
    return dict(row)


async def get_customer_by_identifier(
    id_type: str, value: str
) -> dict[str, Any] | None:
    """Resolve customer by identifier type and value."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT c.* FROM customers c
        JOIN customer_identifiers ci ON c.id = ci.customer_id
        WHERE ci.type = $1 AND ci.value = $2
        """,
        id_type,
        value,
    )
    return dict(row) if row else None


# ---- Conversation Operations ----


async def insert_conversation(
    customer_id: UUID,
    channel: str,
    subject: str | None = None,
) -> dict[str, Any]:
    """Create a new conversation."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO conversations (customer_id, channel, subject)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        customer_id,
        channel,
        subject,
    )
    return dict(row)


async def get_active_conversation(
    customer_id: UUID, channel: str | None = None
) -> dict[str, Any] | None:
    """Get active conversation within 24 hours, optionally filtered by channel."""
    pool = await get_pool()
    if channel:
        row = await pool.fetchrow(
            """
            SELECT * FROM conversations
            WHERE customer_id = $1
              AND status = 'active'
              AND channel = $2
              AND updated_at > NOW() - INTERVAL '24 hours'
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            customer_id,
            channel,
        )
    else:
        row = await pool.fetchrow(
            """
            SELECT * FROM conversations
            WHERE customer_id = $1
              AND status = 'active'
              AND updated_at > NOW() - INTERVAL '24 hours'
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            customer_id,
        )
    return dict(row) if row else None


async def get_conversation(conversation_id: UUID) -> dict[str, Any] | None:
    """Get a conversation by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM conversations WHERE id = $1", conversation_id
    )
    return dict(row) if row else None


async def get_conversations_by_customer(
    customer_id: UUID, limit: int = 5
) -> list[dict[str, Any]]:
    """Get recent conversations for a customer."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT * FROM conversations
        WHERE customer_id = $1
        ORDER BY updated_at DESC
        LIMIT $2
        """,
        customer_id,
        limit,
    )
    return [dict(row) for row in rows]


async def update_conversation_status(
    conversation_id: UUID, status: str, resolution_type: str | None = None
) -> None:
    """Update conversation status."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE conversations
        SET status = $2, resolution_type = $3, updated_at = NOW()
        WHERE id = $1
        """,
        conversation_id,
        status,
        resolution_type,
    )


async def update_conversation_sentiment(
    conversation_id: UUID, score: float
) -> None:
    """Update conversation sentiment score."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE conversations SET sentiment_score = $2, updated_at = NOW()
        WHERE id = $1
        """,
        conversation_id,
        score,
    )


# ---- Message Operations ----


async def insert_message(
    conversation_id: UUID,
    channel: str,
    direction: str,
    role: str,
    content: str,
    token_usage: int | None = None,
    processing_time_ms: int | None = None,
    tool_calls: dict | None = None,
    external_id: str | None = None,
    delivery_status: str = "pending",
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Insert a message into a conversation."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO messages (conversation_id, channel, direction, role, content,
                              token_usage, processing_time_ms, tool_calls,
                              external_id, delivery_status, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
        """,
        conversation_id,
        channel,
        direction,
        role,
        content,
        token_usage,
        processing_time_ms,
        json.dumps(tool_calls) if tool_calls else None,
        external_id,
        delivery_status,
        json.dumps(metadata or {}),
    )
    # Update conversation timestamp
    await pool.execute(
        "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
        conversation_id,
    )
    return dict(row)


async def get_conversation_messages(
    conversation_id: UUID, limit: int = 50
) -> list[dict[str, Any]]:
    """Get messages for a conversation ordered by creation time."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT * FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        LIMIT $2
        """,
        conversation_id,
        limit,
    )
    return [dict(row) for row in rows]


# ---- Ticket Operations ----


async def insert_ticket(
    customer_id: UUID,
    channel: str,
    subject: str,
    category: str | None = None,
    priority: str = "medium",
    conversation_id: UUID | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Create a new support ticket."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO tickets (customer_id, channel, subject, category, priority,
                             conversation_id, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        customer_id,
        channel,
        subject,
        category,
        priority,
        conversation_id,
        json.dumps(metadata or {}),
    )
    return dict(row)


async def get_ticket(ticket_id: UUID) -> dict[str, Any] | None:
    """Get a ticket by ID."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
    return dict(row) if row else None


async def update_ticket_status(
    ticket_id: UUID, status: str, resolution_notes: str | None = None
) -> None:
    """Update ticket status and optional resolution notes."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE tickets SET status = $2, resolution_notes = $3, updated_at = NOW()
        WHERE id = $1
        """,
        ticket_id,
        status,
        resolution_notes,
    )


async def get_tickets_by_customer(
    customer_id: UUID, limit: int = 10
) -> list[dict[str, Any]]:
    """Get tickets for a customer."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT * FROM tickets WHERE customer_id = $1
        ORDER BY created_at DESC LIMIT $2
        """,
        customer_id,
        limit,
    )
    return [dict(row) for row in rows]


# ---- Knowledge Base Operations ----


async def search_knowledge_base(
    query_embedding: list[float], max_results: int = 3, min_similarity: float = 0.5
) -> list[dict[str, Any]]:
    """Search knowledge base using pgvector cosine similarity."""
    pool = await get_pool()
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    rows = await pool.fetch(
        """
        SELECT id, title, content, category,
               1 - (embedding <=> $1::vector) AS similarity_score
        FROM knowledge_base
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $2
        """,
        embedding_str,
        max_results,
    )
    results = [dict(row) for row in rows]
    return [r for r in results if r.get("similarity_score", 0) >= min_similarity]


async def insert_knowledge_entry(
    title: str,
    content: str,
    category: str | None = None,
    embedding: list[float] | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Insert a knowledge base entry with optional vector embedding."""
    pool = await get_pool()
    embedding_str = None
    if embedding:
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    row = await pool.fetchrow(
        """
        INSERT INTO knowledge_base (title, content, category, embedding, metadata)
        VALUES ($1, $2, $3, $4::vector, $5)
        RETURNING id, title, content, category, created_at
        """,
        title,
        content,
        category,
        embedding_str,
        json.dumps(metadata or {}),
    )
    return dict(row)


# ---- Channel Config Operations ----


async def get_channel_config(channel: str) -> dict[str, Any] | None:
    """Get configuration for a specific channel."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM channel_configs WHERE channel = $1", channel
    )
    return dict(row) if row else None


# ---- Metrics Operations ----


async def insert_metric(
    metric_name: str,
    metric_value: float,
    channel: str | None = None,
    dimensions: dict | None = None,
) -> dict[str, Any]:
    """Record a metric data point."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO agent_metrics (metric_name, metric_value, channel, dimensions)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        metric_name,
        metric_value,
        channel,
        json.dumps(dimensions or {}),
    )
    return dict(row)


async def get_channel_metrics(
    hours: int = 24, channel: str | None = None
) -> dict[str, Any]:
    """Get aggregated per-channel metrics for the given time period."""
    pool = await get_pool()

    channel_filter = ""
    params: list = [hours]
    if channel:
        channel_filter = "AND channel = $2"
        params.append(channel)

    rows = await pool.fetch(
        f"""
        SELECT
            channel,
            COUNT(*) FILTER (WHERE metric_name = 'response_time') AS total_conversations,
            AVG(metric_value) FILTER (WHERE metric_name = 'response_time') AS avg_response_time_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY metric_value)
                FILTER (WHERE metric_name = 'response_time') AS p95_response_time_ms,
            AVG(metric_value) FILTER (WHERE metric_name = 'sentiment') AS avg_sentiment,
            COUNT(*) FILTER (WHERE metric_name = 'escalation') AS escalation_count,
            AVG(metric_value) FILTER (WHERE metric_name = 'resolution') AS resolution_rate
        FROM agent_metrics
        WHERE recorded_at > NOW() - INTERVAL '1 hour' * $1
            {channel_filter}
        GROUP BY channel
        """,
        *params,
    )

    channels = {}
    for row in rows:
        ch = row["channel"] or "unknown"
        total = row["total_conversations"] or 0
        channels[ch] = {
            "total_conversations": total,
            "average_response_time_ms": round(row["avg_response_time_ms"] or 0, 1),
            "p95_response_time_ms": round(row["p95_response_time_ms"] or 0, 1),
            "average_sentiment": round(row["avg_sentiment"] or 0.5, 2),
            "escalation_count": row["escalation_count"] or 0,
            "escalation_rate": round(
                (row["escalation_count"] or 0) / max(total, 1), 3
            ),
            "resolution_rate": round(row["resolution_rate"] or 0, 2),
        }

    return {
        "period_hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channels": channels,
    }


# ---- Health Check ----


async def check_db_health() -> bool:
    """Check database connectivity."""
    try:
        pool = await get_pool()
        await pool.fetchval("SELECT 1")
        return True
    except Exception:
        return False
