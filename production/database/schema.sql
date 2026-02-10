-- Stage 2 Specialization: PostgreSQL CRM Schema
-- 8 tables + pgvector extension for semantic search
-- Per Constitution Principle III: PostgreSQL IS the CRM

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. customers: Unified customer record across all channels
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    phone VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_email ON customers (email);

-- 2. customer_identifiers: Cross-channel customer resolution
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('email', 'phone', 'whatsapp')),
    value VARCHAR(255) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (type, value)
);

CREATE INDEX IF NOT EXISTS idx_ci_customer_id ON customer_identifiers (customer_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ci_type_value ON customer_identifiers (type, value);

-- 3. conversations: Thread tracking for customer-agent interactions
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL CHECK (channel IN ('email', 'whatsapp', 'web')),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'escalated')),
    subject VARCHAR(500),
    sentiment_score FLOAT,
    resolution_type VARCHAR(50) CHECK (resolution_type IN ('agent', 'human', 'timeout') OR resolution_type IS NULL),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_customer_id ON conversations (customer_id);
CREATE INDEX IF NOT EXISTS idx_conv_status ON conversations (status);
CREATE INDEX IF NOT EXISTS idx_conv_channel ON conversations (channel);

-- 4. messages: Individual communications within conversations
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL CHECK (channel IN ('email', 'whatsapp', 'web')),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    role VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'agent', 'system')),
    content TEXT NOT NULL,
    token_usage INTEGER,
    processing_time_ms INTEGER,
    tool_calls JSONB,
    external_id VARCHAR(255),
    delivery_status VARCHAR(50) DEFAULT 'pending' CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_msg_conversation_id ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_msg_channel ON messages (channel);
CREATE INDEX IF NOT EXISTS idx_msg_created_at ON messages (created_at);

-- 5. tickets: Support ticket lifecycle management
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL CHECK (channel IN ('email', 'whatsapp', 'web')),
    subject VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'escalated', 'resolved', 'closed')),
    resolution_notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticket_customer_id ON tickets (customer_id);
CREATE INDEX IF NOT EXISTS idx_ticket_status ON tickets (status);
CREATE INDEX IF NOT EXISTS idx_ticket_channel ON tickets (channel);

-- 6. knowledge_base: Product documentation with vector embeddings
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base (category);
-- IVFFlat index for approximate nearest neighbor search
-- Note: Requires at least 100 rows before creating; create after seeding
-- CREATE INDEX IF NOT EXISTS idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 7. channel_configs: Per-channel settings and configuration
CREATE TABLE IF NOT EXISTS channel_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(50) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    response_template TEXT,
    max_response_length INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cc_channel ON channel_configs (channel);

-- 8. agent_metrics: Time-series performance metrics
CREATE TABLE IF NOT EXISTS agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    channel VARCHAR(50),
    dimensions JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_am_metric_name ON agent_metrics (metric_name);
CREATE INDEX IF NOT EXISTS idx_am_channel ON agent_metrics (channel);
CREATE INDEX IF NOT EXISTS idx_am_recorded_at ON agent_metrics (recorded_at);

-- Seed channel configurations
INSERT INTO channel_configs (channel, enabled, max_response_length, config) VALUES
    ('email', TRUE, 500, '{"tone": "formal", "unit": "words"}'),
    ('whatsapp', TRUE, 300, '{"tone": "conversational", "unit": "characters", "absolute_limit": 1600}'),
    ('web', TRUE, 300, '{"tone": "semi-formal", "unit": "words"}')
ON CONFLICT (channel) DO NOTHING;
