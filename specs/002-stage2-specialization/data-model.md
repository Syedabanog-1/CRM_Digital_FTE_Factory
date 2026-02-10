# Data Model: Stage 2 Specialization

**Feature**: 002-stage2-specialization | **Date**: 2026-02-09
**Phase**: 1 (Design) | **Status**: Complete

## Overview

8 PostgreSQL tables serving as the CRM system per Constitution Principle III. All tables use UUID primary keys, `TIMESTAMPTZ` for timestamps, and `JSONB` for flexible metadata. pgvector extension enables semantic search on the knowledge_base table.

## Entity Relationship Diagram

```
customers 1──┬──* customer_identifiers
             │
             ├──* conversations 1──* messages
             │
             └──* tickets ──1 conversations

knowledge_base (standalone, vector-indexed)
channel_configs (standalone, per-channel settings)
agent_metrics (standalone, time-series)
```

## Tables

### 1. customers

The unified customer record across all channels.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique customer ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Primary identifier |
| name | VARCHAR(255) | | Customer display name |
| phone | VARCHAR(50) | | Phone number (optional) |
| metadata | JSONB | DEFAULT '{}' | Flexible additional data |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

**Indexes**: `idx_customers_email` (UNIQUE on email)
**Validation**: Email format validated at application layer (Pydantic)

### 2. customer_identifiers

Cross-channel customer resolution. Links identifiers (email, phone, whatsapp) to customer records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier ID |
| customer_id | UUID | FK → customers(id), NOT NULL | Parent customer |
| type | VARCHAR(50) | NOT NULL | Identifier type: email, phone, whatsapp |
| value | VARCHAR(255) | NOT NULL | The identifier value |
| verified | BOOLEAN | DEFAULT FALSE | Whether verified |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

**Indexes**: `idx_ci_type_value` (UNIQUE on type, value), `idx_ci_customer_id`
**Validation**: Type must be one of: email, phone, whatsapp

### 3. conversations

Thread tracking for customer-agent interactions. Active conversations within 24 hours are reused.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique conversation ID |
| customer_id | UUID | FK → customers(id), NOT NULL | Customer reference |
| channel | VARCHAR(50) | NOT NULL | Initial channel: email, whatsapp, web |
| status | VARCHAR(50) | DEFAULT 'active' | active, resolved, escalated |
| subject | VARCHAR(500) | | Conversation subject/topic |
| sentiment_score | FLOAT | | Latest sentiment (0.0-1.0) |
| resolution_type | VARCHAR(50) | | agent, human, timeout |
| metadata | JSONB | DEFAULT '{}' | Flexible data |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Conversation start time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last activity time |

**Indexes**: `idx_conv_customer_id`, `idx_conv_status`, `idx_conv_channel`
**State transitions**: active → resolved | escalated; escalated → resolved
**24-hour rule**: Query `WHERE customer_id=$1 AND status='active' AND updated_at > NOW() - INTERVAL '24 hours'`

### 4. messages

Individual communications within conversations. Tracks both customer and agent messages.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique message ID |
| conversation_id | UUID | FK → conversations(id), NOT NULL | Parent conversation |
| channel | VARCHAR(50) | NOT NULL | Channel: email, whatsapp, web |
| direction | VARCHAR(10) | NOT NULL | inbound or outbound |
| role | VARCHAR(20) | NOT NULL | customer, agent, system |
| content | TEXT | NOT NULL | Message content |
| token_usage | INTEGER | | LLM tokens used (outbound) |
| processing_time_ms | INTEGER | | Processing latency in ms |
| tool_calls | JSONB | | Tool calls made by agent |
| external_id | VARCHAR(255) | | Channel-specific message ID |
| delivery_status | VARCHAR(50) | DEFAULT 'pending' | pending, sent, delivered, failed |
| metadata | JSONB | DEFAULT '{}' | Channel-specific metadata |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Message timestamp |

**Indexes**: `idx_msg_conversation_id`, `idx_msg_channel`, `idx_msg_created_at`
**Validation**: direction ∈ {inbound, outbound}, role ∈ {customer, agent, system}

### 5. tickets

Support ticket lifecycle management. Links to conversations and customers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique ticket ID |
| conversation_id | UUID | FK → conversations(id) | Associated conversation |
| customer_id | UUID | FK → customers(id), NOT NULL | Customer reference |
| channel | VARCHAR(50) | NOT NULL | Source channel |
| subject | VARCHAR(500) | NOT NULL | Ticket subject |
| category | VARCHAR(100) | | Support category |
| priority | VARCHAR(20) | DEFAULT 'medium' | low, medium, high, urgent |
| status | VARCHAR(50) | DEFAULT 'open' | open, in_progress, escalated, resolved, closed |
| resolution_notes | TEXT | | How ticket was resolved |
| metadata | JSONB | DEFAULT '{}' | Additional data |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Ticket creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

**Indexes**: `idx_ticket_customer_id`, `idx_ticket_status`, `idx_ticket_channel`
**State transitions**: open → in_progress → resolved → closed; any → escalated

### 6. knowledge_base

Product documentation with vector embeddings for semantic search.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique entry ID |
| title | VARCHAR(500) | NOT NULL | Article title |
| content | TEXT | NOT NULL | Full article content |
| category | VARCHAR(100) | | Article category |
| embedding | vector(1536) | | OpenAI text-embedding-3-small |
| metadata | JSONB | DEFAULT '{}' | Additional data |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

**Indexes**: `idx_kb_embedding` (IVFFlat, vector_cosine_ops, lists=100), `idx_kb_category`
**Semantic search**: `SELECT * FROM knowledge_base ORDER BY embedding <=> $1 LIMIT $2`
**Seeding**: Load from `context/product-docs.md`, generate embeddings via OpenAI API

### 7. channel_configs

Per-channel settings and configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique config ID |
| channel | VARCHAR(50) | UNIQUE, NOT NULL | Channel name |
| enabled | BOOLEAN | DEFAULT TRUE | Whether channel is active |
| config | JSONB | DEFAULT '{}' | Channel-specific settings |
| response_template | TEXT | | Response format template |
| max_response_length | INTEGER | | Maximum response length |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

**Indexes**: `idx_cc_channel` (UNIQUE)
**Seed data**: email (500 words), whatsapp (300 chars), web (300 words)

### 8. agent_metrics

Time-series performance metrics per channel.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique metric ID |
| metric_name | VARCHAR(100) | NOT NULL | e.g., response_time, escalation, sentiment |
| metric_value | FLOAT | NOT NULL | Numeric metric value |
| channel | VARCHAR(50) | | Optional channel filter |
| dimensions | JSONB | DEFAULT '{}' | Flexible dimensions (ticket_id, etc.) |
| recorded_at | TIMESTAMPTZ | DEFAULT NOW() | Metric timestamp |

**Indexes**: `idx_am_metric_name`, `idx_am_channel`, `idx_am_recorded_at`
**Aggregation**: Daily rollups via SQL for metrics endpoint

## Relationships Summary

| From | To | Type | FK Column |
|------|----|------|-----------|
| customer_identifiers | customers | Many-to-One | customer_id |
| conversations | customers | Many-to-One | customer_id |
| messages | conversations | Many-to-One | conversation_id |
| tickets | conversations | Many-to-One | conversation_id |
| tickets | customers | Many-to-One | customer_id |

## Migration Strategy

- `001_initial.sql`: Full schema creation (all 8 tables + indexes + pgvector extension)
- Future migrations: Numbered sequentially (002_, 003_, etc.)
- Rollback: Each migration includes DROP statements in reverse order
- Seed: `seed.py` loads `context/product-docs.md` into knowledge_base with embeddings
