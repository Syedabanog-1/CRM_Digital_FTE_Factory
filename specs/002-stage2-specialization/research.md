# Research: Stage 2 Specialization

**Feature**: 002-stage2-specialization | **Date**: 2026-02-09
**Phase**: 0 (Research) | **Status**: Complete

## Research Tasks

### R1: OpenAI Agents SDK - Tool Migration Pattern

**Decision**: Use `@function_tool` decorator with Pydantic `BaseModel` input schemas, replacing MCP `@server.tool()` decorators.

**Rationale**: The OpenAI Agents SDK provides a clean decorator pattern that maps 1:1 with existing MCP tools. Each tool gets a Pydantic input model for validation, a detailed docstring for LLM consumption, and try/catch error handling. The `Agent()` class wraps all tools with a system prompt and model selection (`gpt-4o`).

**Alternatives considered**:
- Raw OpenAI function calling API: Lower-level, requires manual tool dispatch. Rejected because Agents SDK provides higher-level abstraction with built-in tool execution.
- LangChain tools: Additional dependency with unnecessary abstraction. Rejected because hackathon explicitly requires OpenAI Agents SDK.

**Key pattern** (from hackathon templates):
```python
from agents import Agent, function_tool
from pydantic import BaseModel

class SearchInput(BaseModel):
    query: str
    max_results: int = 3

@function_tool
async def search_knowledge_base(input: SearchInput) -> str:
    """Search the knowledge base for relevant articles."""
    try:
        # implementation
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### R2: asyncpg with PostgreSQL + pgvector

**Decision**: Use asyncpg for all database access with direct SQL queries in `queries.py`. pgvector extension for semantic search with IVFFlat index.

**Rationale**: asyncpg is the fastest Python async PostgreSQL driver. Direct queries with parameterized inputs prevent SQL injection without ORM overhead. pgvector's IVFFlat index provides approximate nearest neighbor search suitable for knowledge base queries at this scale.

**Alternatives considered**:
- SQLAlchemy async with asyncpg backend: Adds ORM complexity. Rejected because 8 well-defined tables don't need dynamic query building.
- psycopg3 async: Viable but asyncpg has better benchmark performance for this use case.
- Pinecone/Weaviate for vectors: External vector DB adds cost and complexity. Rejected because pgvector keeps everything in PostgreSQL per constitution (Principle III).

**Key findings**:
- Connection pooling: asyncpg.create_pool() with min_size=5, max_size=20
- Vector search: `ORDER BY embedding <=> $1 LIMIT $2` for cosine distance
- Embeddings: text-embedding-3-small (1536 dimensions) at ~$0.02/1M tokens
- IVFFlat index: `CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`

### R3: aiokafka - Event Streaming Best Practices

**Decision**: Use aiokafka for async Kafka producer/consumer. 9 topics with `fte.` prefix per constitution.

**Rationale**: aiokafka is the standard async Python Kafka client, compatible with asyncio event loops used by FastAPI and the worker. Topic naming follows constitution Principle IV.

**Alternatives considered**:
- confluent-kafka-python: C-based, faster but blocking. Rejected because async consistency is more important than raw throughput at this scale.
- Redis Streams: Simpler but doesn't meet constitution requirement for Apache Kafka.

**Key findings**:
- Producer: `AIOKafkaProducer(bootstrap_servers=KAFKA_BROKERS, value_serializer=json_serializer)`
- Consumer: `AIOKafkaConsumer(topic, group_id="fte-workers", auto_offset_reset="earliest")`
- Error handling: Catch `KafkaError`, publish to `fte.dlq` on failure
- Message format: JSON with `channel`, `customer_identifier`, `content`, `metadata`, `timestamp`
- Partitioning: Default (round-robin) sufficient for initial scale

### R4: FastAPI - Webhook Integration Patterns

**Decision**: FastAPI with channel-specific routers. Twilio signature validation via `RequestValidator`. Gmail via Pub/Sub push with base64 message decoding.

**Rationale**: FastAPI's async-first design, automatic OpenAPI docs, and Pydantic integration make it ideal. Separate routers per channel maintain clean separation.

**Alternatives considered**:
- Flask: Synchronous by default. Rejected for async requirements.
- Django: Too heavyweight for a webhook service.
- Starlette directly: FastAPI adds Pydantic integration and OpenAPI for free.

**Key findings**:
- Twilio signature validation: `RequestValidator(auth_token).validate(url, params, signature)`
- Gmail Pub/Sub: Base64 decode notification, then use Gmail API to fetch full message
- CORS: Allow web form origin only, not `*`
- Health check: Return channel statuses, DB connectivity, Kafka connectivity

### R5: Gmail API + Pub/Sub Integration

**Decision**: Gmail API v1 with OAuth2 service account. Pub/Sub push notifications to `/webhooks/gmail`. Polling fallback via `users.messages.list` with `after:` query.

**Rationale**: Pub/Sub push is real-time and serverless. Gmail API provides thread management for in-thread replies. Service account avoids user-interactive OAuth flow.

**Alternatives considered**:
- IMAP polling: Older protocol, less reliable, no thread management. Rejected.
- Gmail API with polling only: Works but higher latency. Keep as fallback.
- Microsoft Graph (Outlook): Different platform. Out of scope.

**Key findings**:
- Watch setup: `gmail.users().watch(userId='me', body={'topicName': topic, 'labelIds': ['INBOX']})`
- Message parsing: Extract `From`, `Subject`, plain-text body from multipart MIME
- Reply: Use `threadId` from original message, set `In-Reply-To` and `References` headers
- Refresh: Watch expires after 7 days, needs periodic renewal

### R6: Twilio WhatsApp Sandbox

**Decision**: Twilio WhatsApp Sandbox for development. Webhook receives POST with `Body`, `From`, `ProfileName`. Reply via `client.messages.create()`.

**Rationale**: Sandbox provides full API functionality without business verification. Sufficient for hackathon demonstration.

**Key findings**:
- Webhook fields: `Body`, `From` (whatsapp:+1234...), `ProfileName`, `WaId`, `NumMedia`
- Signature validation: `X-Twilio-Signature` header with HMAC-SHA1
- Response: TwiML or REST API `client.messages.create(from_='whatsapp:+14155238886', to=from_number, body=response)`
- Message splitting: If >1600 chars, split at sentence boundaries

### R7: React Web Support Form - Standalone Component

**Decision**: React component with Tailwind CSS, no Next.js framework required. Standalone JSX that can be embedded in any page via script tag or npm package.

**Rationale**: Hackathon requires "standalone, embeddable component" - a full Next.js app adds unnecessary complexity. A single React component with Tailwind is simpler and more portable.

**Alternatives considered**:
- Full Next.js application: Overkill for a single form component.
- Web Components (vanilla): Less ecosystem support. React specified in constitution.
- Vue.js: Not in constitution technology stack.

**Key findings**:
- Validation: name >= 2 chars, email regex, subject >= 5 chars, message >= 10 chars
- Categories: ["Technical Support", "Billing", "Feature Request", "Bug Report", "General Inquiry"]
- Priorities: ["low", "medium", "high", "urgent"]
- API call: POST `/support/submit` with JSON body
- Status check: GET `/support/ticket/{id}`

### R8: Kubernetes Deployment Patterns

**Decision**: Single namespace `fte-production`, separate Deployments for API and worker, HPA on CPU 70%, Ingress with TLS via cert-manager annotations.

**Rationale**: Standard K8s patterns. Separate deployments allow independent scaling (API is I/O bound, worker is CPU bound). HPA prevents over-provisioning.

**Key findings**:
- Liveness probe: HTTP GET `/health` every 30s, timeout 5s
- Readiness probe: HTTP GET `/health` every 10s, timeout 3s
- Resource limits: API (256Mi-512Mi RAM, 250m-500m CPU), Worker (512Mi-1Gi RAM, 500m-1000m CPU)
- Image pull: Single image, different CMD for API vs worker
- Secrets: Opaque type for API keys, DB credentials

## Summary

All research items resolved. No NEEDS CLARIFICATION markers remain. All technology choices align with constitution principles and hackathon requirements.

| Item | Decision | Constitution Principle |
|------|----------|----------------------|
| Agent SDK | OpenAI Agents SDK @function_tool | II (Agent Factory) |
| Database | asyncpg + pgvector | III (PostgreSQL as CRM) |
| Streaming | aiokafka, 9 topics | IV (Event-Driven) |
| API | FastAPI with routers | V (Production-Grade) |
| Email | Gmail API + Pub/Sub | I (Multi-Channel) |
| WhatsApp | Twilio Sandbox | I (Multi-Channel) |
| Web Form | React + Tailwind | I (Multi-Channel) |
| Deployment | K8s + Docker | V (Production-Grade) |
