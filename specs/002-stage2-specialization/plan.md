# Implementation Plan: Stage 2 Specialization - Production-Grade Customer Success Digital FTE

**Branch**: `002-stage2-specialization` | **Date**: 2026-02-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-stage2-specialization/spec.md`
**Predecessor**: Stage 1 Incubation (`001-stage1-incubation`) - COMPLETE (48/48 tasks, 128/128 tests)

## Summary

Transform the Stage 1 incubation prototype into a production-grade 24/7 Customer
Success Digital FTE. This stage replaces in-memory storage with PostgreSQL + pgvector,
converts MCP tools to OpenAI Agents SDK `@function_tool` functions, adds real channel
integrations (Gmail API, Twilio WhatsApp, React Web Form), connects everything through
Apache Kafka event streaming, wraps it in a FastAPI service, and deploys to Kubernetes.

Technical approach: New `production/` directory alongside existing `src/` (Stage 1
preserved for reference). Python async throughout with asyncpg for database, aiokafka
for streaming, FastAPI for HTTP, and the OpenAI Agents SDK for the Custom Agent.
React/Next.js for the standalone web support form component.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/React (web form)
**Primary Dependencies**: openai + agents SDK, fastapi, asyncpg, aiokafka, pydantic, twilio, google-api-python-client, google-cloud-pubsub, httpx
**Storage**: PostgreSQL 16+ with pgvector extension (8 tables)
**Testing**: pytest + pytest-asyncio + httpx (unit/integration), locust (load)
**Target Platform**: Kubernetes (production), Docker Compose (local dev), minikube (K8s dev)
**Project Type**: Web application (Python backend + React frontend component)
**Performance Goals**: <3s p95 processing latency, >99.9% uptime, >85% accuracy
**Constraints**: <$1,000/year operating cost, gpt-4o model, Twilio Sandbox for WhatsApp, no external CRM
**Scale/Scope**: 3 API pods + 3 worker pods, 100+ web form submissions/day, 50+ emails/day, 50+ WhatsApp messages/day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Multi-Channel First | PASS | Gmail API, Twilio WhatsApp, React Web Form - all three channels with real integrations |
| II. Agent Factory Paradigm | PASS | This IS the specialization stage - transforming prototype to Custom Agent via OpenAI Agents SDK |
| III. PostgreSQL as CRM | PASS | Full 8-table schema with pgvector; PostgreSQL IS the CRM |
| IV. Event-Driven Architecture | PASS | Apache Kafka with 9 topics for all async message routing |
| V. Production-Grade Quality | PASS | Pydantic validation, try/catch on all tools, structured JSON logging, /health endpoints, env vars + ConfigMaps |
| VI. Test-First Development | PASS | Transition tests, E2E multi-channel tests, load tests with locust |

No violations. All six principles are fully addressed in Stage 2.

## Project Structure

### Documentation (this feature)

```text
specs/002-stage2-specialization/
├── spec.md              # Feature specification (11 user stories, 23 FRs)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (8 tables)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
│   ├── api-endpoints.md # FastAPI endpoint contracts
│   └── agent-tools.md   # OpenAI SDK tool contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
# Stage 1 (preserved for reference)
src/                              # Stage 1 prototype (in-memory, MCP server)
context/                          # Development dossier (shared with Stage 2)
tests/                            # Stage 1 test suite

# Stage 2 (new production code)
production/
├── agent/
│   ├── __init__.py
│   ├── customer_success_agent.py # OpenAI Agents SDK Agent() definition
│   ├── tools.py                  # @function_tool definitions (6 tools)
│   ├── prompts.py                # Production system prompt (formalized)
│   └── formatters.py             # Channel-specific response formatting
├── channels/
│   ├── __init__.py
│   ├── gmail_handler.py          # Gmail API + Pub/Sub integration
│   ├── whatsapp_handler.py       # Twilio WhatsApp API integration
│   └── web_form_handler.py       # FastAPI router for web form
├── workers/
│   ├── __init__.py
│   ├── message_processor.py      # Kafka consumer + agent runner
│   └── metrics_collector.py      # Background metrics aggregation
├── api/
│   ├── __init__.py
│   └── main.py                   # FastAPI application (all endpoints)
├── database/
│   ├── schema.sql                # PostgreSQL schema (8 tables + indexes)
│   ├── seed.py                   # Load context/ data into knowledge_base
│   ├── migrations/               # Schema migration scripts
│   │   └── 001_initial.sql
│   └── queries.py                # Async database access functions (asyncpg)
├── kafka_client.py               # Kafka producer/consumer classes + topics
├── config.py                     # Environment variable configuration
├── logging_config.py             # Structured JSON logging setup
├── tests/
│   ├── __init__.py
│   ├── test_transition.py        # Transition tests (Stage 1 → Stage 2)
│   ├── test_agent.py             # Agent tool tests
│   ├── test_channels.py          # Channel handler tests
│   ├── test_database.py          # Database query tests
│   ├── test_e2e.py               # Multi-channel E2E tests
│   └── load_test.py              # Locust load test
├── Dockerfile                    # Multi-stage Python build
├── docker-compose.yml            # Local dev (API, worker, PG, Kafka, ZK)
└── requirements.txt              # Production Python dependencies

# Web Support Form (separate frontend)
web-form/
├── package.json
├── src/
│   ├── SupportForm.jsx           # Main form component
│   └── index.js                  # Entry point
└── README.md                     # Form integration guide

# Kubernetes manifests
k8s/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml
├── postgres/
│   ├── deployment.yaml
│   └── service.yaml
├── kafka/
│   ├── deployment.yaml
│   └── service.yaml
├── deployment-api.yaml           # 3 replicas, liveness/readiness probes
├── deployment-worker.yaml        # 3 replicas
├── service.yaml
├── ingress.yaml                  # TLS with cert-manager
└── hpa.yaml                      # Auto-scaling (API + worker)

# Transition artifacts
specs/002-stage2-specialization/
└── transition-checklist.md       # Stage 1 → Stage 2 discoveries
```

**Structure Decision**: Web application layout with separate `production/` directory
for backend (Python), `web-form/` for frontend (React), and `k8s/` for deployment.
Stage 1 code in `src/` preserved as reference. Shared `context/` dossier for both stages.

## Design Decisions

### D1: Separate production/ directory vs modifying src/

**Decision**: Create new `production/` directory, preserve `src/` as Stage 1 reference.
**Rationale**: Clean separation between prototype and production code. Stage 1 tests
remain runnable. Production code follows hackathon-specified folder structure. No risk
of breaking Stage 1 artifacts during Stage 2 development.
**Alternative rejected**: Modifying src/ in-place - rejected because it would break
Stage 1 test suite and make it hard to demonstrate the incubation-to-specialization
evolution required by the hackathon.

### D2: asyncpg vs SQLAlchemy for database access

**Decision**: Direct asyncpg with query functions in `database/queries.py`.
**Rationale**: Simpler, lower overhead, aligns with hackathon code templates. Asyncpg
provides native async support and parameterized queries (SQL injection safe). No ORM
complexity needed for 8 well-defined tables.
**Alternative rejected**: SQLAlchemy async - adds unnecessary abstraction layer for
this scope; hackathon templates use direct asyncpg.

### D3: Single Docker image for API and worker

**Decision**: One Dockerfile, different CMD for API vs worker.
**Rationale**: Both share the same codebase and dependencies. Simpler CI/CD. K8s
deployments differentiate via command override (uvicorn vs python worker).
**Alternative rejected**: Separate images - unnecessary duplication; same Python
environment needed for both.

### D4: Kafka topic design with 9 topics

**Decision**: Unified incoming + channel-specific + operations topics per constitution.
**Rationale**: Constitution Principle IV mandates specific topic names. Channel-specific
topics enable independent monitoring and replay. DLQ ensures no message loss.
**Topics**: `fte.tickets.incoming`, `fte.channels.email.inbound`,
`fte.channels.whatsapp.inbound`, `fte.channels.webform.inbound`,
`fte.channels.email.outbound`, `fte.channels.whatsapp.outbound`,
`fte.escalations`, `fte.metrics`, `fte.dlq`

### D5: pgvector for knowledge base search

**Decision**: Use OpenAI embeddings API (text-embedding-3-small) to generate 1536-dim
vectors stored in pgvector. IVFFlat index for approximate nearest neighbor search.
**Rationale**: Constitution Principle III mandates pgvector. Embeddings are generated
when seeding knowledge base from `context/product-docs.md`. Semantic search replaces
Stage 1's difflib text matching.
**Alternative rejected**: Full-text search (tsvector) - less accurate for natural
language queries; pgvector explicitly required.

### D6: Web form as standalone React component

**Decision**: Create a self-contained React component in `web-form/` that can be
embedded in any page. Uses Tailwind CSS for styling. Communicates with backend via
REST API.
**Rationale**: Hackathon requires "standalone, embeddable component" - not a full
website. React/Next.js specified in constitution technology stack.

## Phases

### Phase 0: Transition (maps to US1)
- Extract Stage 1 discoveries into transition-checklist.md
- Create production/ folder structure
- Write production requirements.txt

### Phase 1: Foundation (maps to US2)
- PostgreSQL schema (schema.sql + seed.py)
- Database query functions (queries.py)
- Configuration and logging modules

### Phase 2: Agent Core (maps to US1)
- Transform MCP tools to @function_tool (tools.py)
- Formalize system prompt (prompts.py)
- Channel formatters (formatters.py)
- Agent definition (customer_success_agent.py)
- Transition test suite

### Phase 3: API Layer (maps to US4, US3)
- FastAPI application (api/main.py)
- Web form backend handler (web_form_handler.py)
- Web form React component (web-form/)

### Phase 4: Channel Integrations (maps to US5, US6)
- Gmail handler (gmail_handler.py)
- WhatsApp handler (whatsapp_handler.py)

### Phase 5: Event Streaming (maps to US7, US8)
- Kafka client (kafka_client.py)
- Unified message processor worker (message_processor.py)
- Metrics collector (metrics_collector.py)

### Phase 6: Containerization (maps to US10)
- Dockerfile (multi-stage)
- docker-compose.yml (full local stack)

### Phase 7: Kubernetes (maps to US9)
- All K8s manifests
- HPA configuration

### Phase 8: Testing & Monitoring (maps to US11, Stage 3 prep)
- E2E multi-channel tests
- Load tests with locust
- Channel metrics and monitoring

## Dependencies & Execution Order

```
Phase 0 (Transition)
  └─→ Phase 1 (Foundation: DB + Config)
       └─→ Phase 2 (Agent Core: Tools + Prompt + Formatter)
            ├─→ Phase 3 (API + Web Form)
            │    └─→ Phase 4 (Gmail + WhatsApp handlers)
            │         └─→ Phase 5 (Kafka + Worker)
            ├─→ Phase 6 (Docker) ─────────────────────┐
            └─→ Phase 7 (K8s) ────────────────────────┤
                                                       └─→ Phase 8 (E2E + Load Tests)
```

### Critical Path
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 8

### Parallel Opportunities
- Phase 6 (Docker) can start after Phase 2
- Phase 7 (K8s manifests) can start after Phase 2 (static YAML)
- Web form React component (Phase 3) can be built in parallel with backend
- Gmail and WhatsApp handlers (Phase 4) can be built in parallel with each other

## Complexity Tracking

> No violations. All complexity is within constitution bounds.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Summary

| Metric | Value |
|--------|-------|
| **Phases** | 9 (0-8) |
| **User Stories covered** | 11 |
| **Functional Requirements** | 23 |
| **Database Tables** | 8 |
| **API Endpoints** | 8 |
| **Agent Tools** | 6 |
| **Kafka Topics** | 9 |
| **K8s Manifests** | ~10 |
| **New Python files** | ~20 |
| **New React files** | ~3 |
| **Test files** | 6 |
