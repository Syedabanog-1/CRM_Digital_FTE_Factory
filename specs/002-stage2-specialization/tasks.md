# Tasks: Stage 2 Specialization - Production-Grade Customer Success Digital FTE

**Input**: Design documents from `/specs/002-stage2-specialization/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, contracts/agent-tools.md, quickstart.md
**Branch**: `002-stage2-specialization`

**Organization**: Tasks grouped by user story (11 stories from spec.md) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `production/` at repository root
- **Frontend**: `web-form/` at repository root
- **K8s**: `k8s/` at repository root
- **Stage 1 reference**: `src/` (read-only, preserved)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the production directory structure, install dependencies, configure environment

- [x] T001 Create production/ directory structure with all subdirectories: agent/, channels/, workers/, api/, database/, database/migrations/, tests/
- [x] T002 Create production/requirements.txt with all Python dependencies: openai, agents, fastapi, uvicorn, asyncpg, aiokafka, pydantic, twilio, google-api-python-client, google-cloud-pubsub, httpx, python-dotenv, structlog, pytest, pytest-asyncio, locust
- [x] T003 [P] Create production/config.py with environment variable configuration using pydantic BaseSettings: DATABASE_URL, KAFKA_BROKERS, OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, GMAIL_CREDENTIALS_JSON, GMAIL_PUBSUB_TOPIC, LOG_LEVEL, CORS_ORIGINS
- [x] T004 [P] Create production/logging_config.py with structured JSON logging setup using structlog: configure processors, JSON renderer, correlation ID injection, log level from config
- [x] T005 [P] Create production/__init__.py and all sub-package __init__.py files: agent/__init__.py, channels/__init__.py, workers/__init__.py, api/__init__.py, database/__init__.py, tests/__init__.py
- [x] T006 Create .env.example at production/.env.example with all required environment variables documented

**Checkpoint**: Project structure ready, dependencies installable, configuration loadable

---

## Phase 2: Foundational - PostgreSQL Database (Blocking Prerequisites)

**Purpose**: Create the complete database layer that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create production/database/schema.sql with complete PostgreSQL schema: CREATE EXTENSION pgvector; 8 tables (customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics) with all columns, constraints, indexes per data-model.md
- [x] T008 Create production/database/migrations/001_initial.sql copying schema.sql content for migration tracking with transaction wrapper (BEGIN/COMMIT) and rollback comments
- [x] T009 Create production/database/queries.py with all async database access functions using asyncpg: create_pool(), get_pool(), close_pool(), and CRUD functions for all 8 tables - insert_customer(), get_customer_by_email(), get_customer_by_phone(), upsert_customer_identifier(), insert_conversation(), get_active_conversation(), insert_message(), get_conversation_messages(), insert_ticket(), get_ticket(), update_ticket_status(), search_knowledge_base() with pgvector cosine similarity, insert_knowledge_entry(), get_channel_config(), insert_metric(), get_channel_metrics()
- [x] T010 Create production/database/seed.py to load context/product-docs.md into knowledge_base table: parse markdown sections into articles, generate embeddings via OpenAI text-embedding-3-small API, insert with vector embeddings, seed channel_configs with response limits (email:500 words, whatsapp:300 chars, web:300 words)

**Checkpoint**: Database schema deployable, all query functions available, knowledge base seedable. Test by running schema.sql against local PostgreSQL and executing seed.py.

---

## Phase 3: User Story 1 - Transition from Prototype to Production Agent (Priority: P1) MVP

**Goal**: Transform Stage 1 MCP tools into OpenAI Agents SDK @function_tool functions with formalized system prompt and transition documentation

**Independent Test**: Run transition test suite verifying edge case handling, escalation decisions, channel-appropriate response lengths, and tool execution order match or exceed Stage 1

### Implementation for User Story 1

- [x] T011 [US1] Create specs/002-stage2-specialization/transition-checklist.md documenting all Stage 1 discoveries: working prompts from src/mcp_server.py, edge cases from tests/, response patterns, escalation rules, performance baselines, API gotchas from MEMORY.md
- [x] T012 [P] [US1] Create production/agent/prompts.py with formalized system prompt: hard constraints (never discuss competitors, never promise undocumented features), escalation triggers (legal, profanity, pricing, failed KB 2+, human request), channel awareness rules (email formal 500w, whatsapp concise 300c, web semi-formal 300w), required tool execution order (create_ticket → get_customer_history → search_knowledge_base → analyze_sentiment → [escalate] → send_response)
- [x] T013 [P] [US1] Create production/agent/formatters.py with ChannelFormatter class: format_email(message, ticket_id) adding formal greeting/signature/ticket reference max 500 words, format_whatsapp(message) concise max 300 chars with split at 1600, format_web(message, ticket_id) semi-formal max 300 words
- [x] T014 [US1] Create production/agent/tools.py with 6 @function_tool functions per contracts/agent-tools.md: search_knowledge_base (pgvector via queries.py), create_ticket (DB insert), get_customer_history (cross-channel via customer_identifiers), escalate_to_human (DB update + Kafka publish to fte.escalations), send_response (channel format + DB store + Kafka outbound), analyze_sentiment (score + label + DB metric). Each tool has Pydantic BaseModel input schema, detailed docstring, try/catch error handling
- [x] T015 [US1] Create production/agent/customer_success_agent.py with Agent() definition: name="TechCorp Customer Success Agent", model="gpt-4o", instructions=SYSTEM_PROMPT from prompts.py, tools=[all 6 tools from tools.py]
- [x] T016 [US1] Create production/tests/test_transition.py with transition test suite: test empty message handling, test pricing escalation trigger, test legal language escalation, test profanity/sentiment escalation, test explicit human request escalation, test email response format (formal, greeting, signature, <=500 words), test whatsapp response format (concise, <=300 chars), test web response format (semi-formal, <=300 words), test tool execution order (create_ticket first, send_response last), test knowledge base search returns relevant results
- [x] T017 [US1] Create production/tests/test_agent.py with agent tool unit tests: test each @function_tool independently with mocked DB, test Pydantic input validation rejects invalid input, test error handling returns graceful JSON errors, test sentiment scoring labels (very_negative <0.2, negative <0.4, neutral <0.6, positive <0.8, very_positive >=0.8)

**Checkpoint**: Production agent fully functional with all 6 tools, formalized prompt, channel formatters. Transition tests passing.

---

## Phase 4: User Story 2 - PostgreSQL CRM Database (Priority: P1)

**Goal**: Verify all 8 database tables work with proper relationships, pgvector semantic search, and cross-channel customer resolution

**Independent Test**: Run schema creation, insert sample data across all tables, perform vector similarity search on knowledge base, verify cross-channel customer resolution

### Implementation for User Story 2

- [x] T018 [US2] Create production/tests/test_database.py with database query tests: test create_pool and connection, test insert/get customer by email, test upsert customer_identifier and cross-channel lookup, test insert/get conversation with 24-hour active reuse, test insert/get messages with channel and direction, test insert/get/update ticket lifecycle, test knowledge_base vector search returns ranked results, test insert/get channel metrics aggregation, test channel_configs CRUD
- [x] T019 [US2] Verify and fix production/database/queries.py for all test scenarios: ensure get_active_conversation respects 24-hour window, ensure search_knowledge_base uses cosine similarity ORDER BY embedding <=> $1, ensure get_channel_metrics aggregates by time period

**Checkpoint**: All 8 tables fully operational, pgvector search working, cross-channel customer resolution verified via test suite.

---

## Phase 5: User Story 3 - Web Support Form (Priority: P1)

**Goal**: Complete standalone web support form with client-side validation, server-side validation, ticket creation, and status checking

**Independent Test**: Submit form with valid data → receive ticket ID. Submit with invalid data → see validation errors. Check ticket status → see current status and agent response.

### Implementation for User Story 3

- [x] T020 [US3] Create production/channels/web_form_handler.py as FastAPI router: POST /support/submit with Pydantic SupportFormInput model (name min 2 chars, email valid format, subject min 5 chars, category from enum, priority from enum default medium, message min 10 chars), creates customer if new, creates ticket, publishes to fte.channels.webform.inbound and fte.tickets.incoming Kafka topics, returns ticket_id and status
- [x] T021 [US3] Add GET /support/ticket/{ticket_id} endpoint to web_form_handler.py: query ticket from DB, include messages (customer + agent), return ticket status/subject/category/priority/timestamps, return 404 if not found
- [x] T022 [P] [US3] Create web-form/package.json with React and Tailwind CSS dependencies, build script
- [x] T023 [P] [US3] Create web-form/src/SupportForm.jsx as standalone React component: form fields (name, email, subject, category dropdown, priority dropdown, message textarea), client-side validation matching server rules, submit handler calling POST /support/submit, success state showing ticket_id with status check link, error state showing field-specific errors, reset form functionality, Tailwind CSS styling
- [x] T024 [P] [US3] Create web-form/src/index.js as entry point that renders SupportForm into a target DOM element for embedding
- [x] T025 [P] [US3] Create web-form/README.md with integration guide: embedding instructions, configuration options, API endpoint configuration

**Checkpoint**: Web form renders, validates, submits, shows ticket ID. Status endpoint returns ticket with messages. Form is embeddable standalone component.

---

## Phase 6: User Story 4 - Multi-Channel Intake via FastAPI (Priority: P1)

**Goal**: FastAPI service receiving messages from all channels, normalizing them, and publishing to Kafka

**Independent Test**: Send HTTP requests to each endpoint and verify correct responses: health returns status, form submission returns ticket ID, webhook endpoints accept valid payloads

### Implementation for User Story 4

- [x] T026 [US4] Create production/api/main.py with FastAPI application: app with title/description/version, CORS middleware with configurable origins, include web_form_handler router, include gmail/whatsapp webhook routers (placeholder imports), GET /health endpoint checking DB connectivity + Kafka connectivity + channel statuses, GET /customers/lookup endpoint with email/phone query params calling queries.get_customer_by_email or get_customer_by_phone, GET /conversations/{conversation_id} endpoint returning full conversation with messages, GET /metrics/channels endpoint with hours/channel query params calling queries.get_channel_metrics, startup event creating DB pool and Kafka producer, shutdown event closing DB pool and Kafka producer
- [x] T027 [US4] Wire web_form_handler.py router into api/main.py with prefix /support (already created in T020-T021, now mounted as router)

**Checkpoint**: FastAPI running at localhost:8000, /health returns healthy, /support/submit creates tickets, /customers/lookup returns customer profiles, /metrics/channels returns per-channel metrics.

---

## Phase 7: User Story 5 - Gmail Channel Integration (Priority: P2)

**Goal**: Receive emails via Gmail API + Pub/Sub, process through agent, reply in same thread

**Independent Test**: Send test email, verify Pub/Sub notification received and parsed, check reply appears in same thread with formal formatting

### Implementation for User Story 5

- [x] T028 [US5] Create production/channels/gmail_handler.py as FastAPI router: POST /webhooks/gmail receiving Pub/Sub push notification, decode base64 message data, extract historyId, use Gmail API to fetch new messages (users.messages.list with historyId), parse From header for email, Subject, plain-text body from multipart MIME, normalize message format, publish to fte.channels.email.inbound and fte.tickets.incoming Kafka topics
- [x] T029 [US5] Add send_email_reply() function to gmail_handler.py: create reply message with same threadId, set In-Reply-To and References headers, prefix subject with "Re:", use formal format from formatters.format_email(), send via Gmail API users.messages.send(), publish to fte.channels.email.outbound
- [x] T030 [US5] Add Gmail watch setup utility function in gmail_handler.py: setup_gmail_watch() to register Pub/Sub subscription for INBOX label, with 7-day expiry renewal logic
- [x] T031 [US5] Wire gmail_handler router into api/main.py with POST /webhooks/gmail endpoint

**Checkpoint**: Gmail webhook receives Pub/Sub notifications, parses emails, publishes to Kafka. Reply function sends in-thread with formal formatting.

---

## Phase 8: User Story 6 - WhatsApp Channel Integration (Priority: P2)

**Goal**: Receive WhatsApp messages via Twilio webhook with signature validation, process through agent, reply via Twilio API

**Independent Test**: Send test webhook with valid Twilio signature, verify message parsed and reply sent. Send with invalid signature, verify 403.

### Implementation for User Story 6

- [x] T032 [P] [US6] Create production/channels/whatsapp_handler.py as FastAPI router: POST /webhooks/whatsapp receiving Twilio form data, validate X-Twilio-Signature header using twilio.request_validator.RequestValidator(auth_token), extract Body, From (whatsapp:+number), ProfileName, WaId, NumMedia, reject empty Body with 400, normalize message format, publish to fte.channels.whatsapp.inbound and fte.tickets.incoming Kafka topics
- [x] T033 [P] [US6] Add send_whatsapp_reply() function to whatsapp_handler.py: create Twilio client, send message via client.messages.create(from_=whatsapp_from, to=customer_from, body=formatted_response), use formatters.format_whatsapp() for concise formatting, split messages >1600 chars at sentence boundaries, publish to fte.channels.whatsapp.outbound
- [x] T034 [US6] Wire whatsapp_handler router into api/main.py with POST /webhooks/whatsapp endpoint
- [x] T035 [US6] Create production/tests/test_channels.py with channel handler tests: test Gmail webhook parses valid Pub/Sub notification, test Gmail webhook rejects invalid format, test WhatsApp webhook validates Twilio signature, test WhatsApp webhook rejects invalid signature with 403, test WhatsApp webhook rejects empty body with 400, test WhatsApp message splitting at sentence boundaries for >1600 chars, test web form submission validates all fields, test web form rejects invalid email format

**Checkpoint**: WhatsApp webhook validates signatures, parses messages, publishes to Kafka. Reply function sends concise responses via Twilio. Channel test suite passing.

---

## Phase 9: User Story 7 - Event Streaming with Kafka (Priority: P2)

**Goal**: All channel messages flow through Kafka event streaming with 9 topics, DLQ for failures, metrics topic for observability

**Independent Test**: Publish message to fte.tickets.incoming, verify consumer picks it up. Inject malformed message, verify DLQ capture.

### Implementation for User Story 7

- [x] T036 [US7] Create production/kafka_client.py with KafkaProducer and KafkaConsumer classes: TOPIC_INCOMING="fte.tickets.incoming", TOPIC_EMAIL_IN="fte.channels.email.inbound", TOPIC_WHATSAPP_IN="fte.channels.whatsapp.inbound", TOPIC_WEBFORM_IN="fte.channels.webform.inbound", TOPIC_EMAIL_OUT="fte.channels.email.outbound", TOPIC_WHATSAPP_OUT="fte.channels.whatsapp.outbound", TOPIC_ESCALATIONS="fte.escalations", TOPIC_METRICS="fte.metrics", TOPIC_DLQ="fte.dlq". AIOKafkaProducer with JSON serializer, AIOKafkaConsumer with group_id="fte-workers", publish() method, consume() async generator, publish_to_dlq() with error context preservation
- [x] T037 [US7] Update production/agent/tools.py to use kafka_client for publishing: escalate_to_human publishes to TOPIC_ESCALATIONS, send_response publishes to channel-specific outbound topic, all tools publish metrics to TOPIC_METRICS on completion

**Checkpoint**: Kafka client connects to brokers, produces/consumes JSON messages across 9 topics, DLQ captures failures with full context.

---

## Phase 10: User Story 8 - Unified Message Processor Worker (Priority: P2)

**Goal**: Background worker consumes from all channels via Kafka, resolves customers, manages conversations, runs agent, stores results

**Independent Test**: Publish test message to Kafka, verify worker processes end-to-end: customer created, conversation created, message stored, agent response generated and stored, metrics published.

### Implementation for User Story 8

- [x] T038 [US8] Create production/workers/message_processor.py with unified Kafka consumer worker: consume from fte.tickets.incoming, for each message: resolve customer by email (primary) or phone (secondary) via queries.get_customer_by_email/phone or create new, get or create active conversation (reuse if within 24 hours), store inbound message via queries.insert_message, load conversation history for context, run Agent.run() with customer_success_agent passing conversation context, store agent response message with latency and tool_calls metadata, publish processing metrics to fte.metrics, on error: send apologetic response to customer channel and publish to fte.dlq
- [x] T039 [US8] Create production/workers/metrics_collector.py with background metrics aggregation: consume from fte.metrics topic, aggregate response_time, escalation_count, sentiment by channel, insert into agent_metrics table via queries.insert_metric, provide get_daily_summary() for metrics endpoint
- [x] T040 [US8] Add worker entrypoint: production/workers/__main__.py that starts message_processor and metrics_collector as async tasks with graceful shutdown on SIGTERM/SIGINT

**Checkpoint**: Worker processes messages from all channels through single pipeline. Customer resolution, conversation management, agent execution, response storage, and metrics all working end-to-end.

---

## Phase 11: User Story 9 - Kubernetes Deployment (Priority: P3)

**Goal**: Complete K8s manifests for production deployment with multi-pod scaling, health checks, auto-scaling, TLS ingress

**Independent Test**: Apply all manifests to minikube, verify pods start, pass health checks, service reachable via ingress

### Implementation for User Story 9

- [x] T041 [P] [US9] Create k8s/namespace.yaml with namespace fte-production
- [x] T042 [P] [US9] Create k8s/configmap.yaml with environment variables: DATABASE_URL, KAFKA_BROKERS, LOG_LEVEL, CORS_ORIGINS (non-secret config)
- [x] T043 [P] [US9] Create k8s/secrets.yaml with Opaque secrets: OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, GMAIL_CREDENTIALS_JSON (base64 encoded placeholders)
- [x] T044 [P] [US9] Create k8s/postgres/deployment.yaml and k8s/postgres/service.yaml: PostgreSQL 16 with pgvector image, PVC for data persistence, service on port 5432
- [x] T045 [P] [US9] Create k8s/kafka/deployment.yaml and k8s/kafka/service.yaml: Confluent Kafka + Zookeeper, services on ports 9092 and 2181
- [x] T046 [US9] Create k8s/deployment-api.yaml: 3 replicas, image from Dockerfile, command uvicorn api.main:app, envFrom configmap+secrets, resource limits (256Mi-512Mi RAM, 250m-500m CPU), liveness probe GET /health every 30s timeout 5s, readiness probe GET /health every 10s timeout 3s
- [x] T047 [US9] Create k8s/deployment-worker.yaml: 3 replicas, same image, command python -m workers, envFrom configmap+secrets, resource limits (512Mi-1Gi RAM, 500m-1000m CPU), liveness probe exec healthcheck
- [x] T048 [P] [US9] Create k8s/service.yaml exposing API deployment on port 80 → 8000
- [x] T049 [P] [US9] Create k8s/ingress.yaml with TLS via cert-manager annotations, host fte.techcorp.com, path / → api service port 80
- [x] T050 [US9] Create k8s/hpa.yaml with HorizontalPodAutoscaler for both API (min 3, max 20, target CPU 70%) and worker (min 3, max 30, target CPU 70%) deployments

**Checkpoint**: All K8s manifests apply cleanly to minikube. Pods start, pass health checks, service reachable, HPA configured.

---

## Phase 12: User Story 10 - Docker and Local Development (Priority: P3)

**Goal**: Dockerfile + docker-compose.yml that brings up entire system locally with single command

**Independent Test**: Run docker-compose up, verify all services start, API reachable, web form submission flows through full pipeline

### Implementation for User Story 10

- [x] T051 [P] [US10] Create production/Dockerfile with multi-stage build: Stage 1 (builder) installs requirements.txt, Stage 2 (runtime) copies code, exposes port 8000, default CMD uvicorn api.main:app --host 0.0.0.0 --port 8000
- [x] T052 [US10] Create production/docker-compose.yml with 5 services: api (build ., port 8000, depends_on postgres/kafka), worker (build ., command python -m workers, depends_on postgres/kafka), postgres (pgvector/pgvector:pg16, port 5432, volume for data, POSTGRES_DB=fte_crm), zookeeper (confluentinc/cp-zookeeper:7.5.0, port 2181), kafka (confluentinc/cp-kafka:7.5.0, port 9092, depends_on zookeeper). Environment variables from .env file, healthchecks for postgres and kafka

**Checkpoint**: docker-compose up starts all 5 services. API health check returns healthy. End-to-end message processing works locally.

---

## Phase 13: User Story 11 - Monitoring and Channel Metrics (Priority: P3)

**Goal**: Channel-specific performance metrics, structured JSON logging with correlation IDs, metrics endpoint

**Independent Test**: Process messages across channels, verify metrics recorded in agent_metrics, logs are structured JSON, /metrics/channels returns per-channel breakdowns

### Implementation for User Story 11

- [x] T053 [US11] Enhance production/logging_config.py to add correlation ID middleware: generate UUID per request, inject into all log entries, pass through Kafka message metadata for cross-service tracing
- [x] T054 [US11] Enhance production/workers/metrics_collector.py to aggregate daily channel metrics: response_time p95 per channel, escalation_rate per channel, average_sentiment per channel, total_conversations per channel, resolution_rate per channel
- [x] T055 [US11] Verify GET /metrics/channels in api/main.py returns correct aggregated data: total_conversations, average_response_time_ms, p95_response_time_ms, average_sentiment, escalation_count, escalation_rate, resolution_rate per channel and totals, with configurable hours lookback

**Checkpoint**: All logs are structured JSON with correlation IDs. Metrics endpoint returns per-channel performance data. Agent metrics table populated from worker processing.

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: E2E tests, load tests, final integration, validation

- [x] T056 Create production/tests/test_e2e.py with multi-channel E2E tests: test web form submission end-to-end (submit → agent processes → response stored → ticket status shows response), test email webhook end-to-end (Pub/Sub notification → parse → agent → reply in thread), test WhatsApp webhook end-to-end (Twilio webhook → validate → agent → reply via Twilio), test cross-channel customer recognition (email then WhatsApp same customer), test escalation flow end-to-end (pricing question → escalation event → ticket escalated), test DLQ capture on processing failure
- [x] T057 Create production/tests/load_test.py with locust load test: WebFormUser class hitting POST /support/submit at 10 users/sec, HealthCheckUser class hitting GET /health, MetricsUser class hitting GET /metrics/channels, assert p95 response time < 3 seconds, assert zero 500 errors, run for 5 minutes
- [x] T058 [P] Security hardening: verify CORS not set to * in production config, verify Twilio signature validation enforced on all WhatsApp endpoints, verify no hardcoded secrets in source (grep for sk-, AC, auth_token), verify SQL parameterized queries (no string concatenation in queries.py), verify XSS input sanitization on web form endpoint
- [x] T059 [P] Run quickstart.md validation: verify docker-compose up instructions work, verify manual test commands work, verify K8s apply instructions reference correct files
- [x] T060 Final integration verification: start full docker-compose stack, run seed.py to populate knowledge base, submit web form → verify response, call /metrics/channels → verify data, call /customers/lookup → verify customer profile, check logs are structured JSON

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (Foundation/DB)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3 (US1 Agent)**: Depends on Phase 2 - MVP, all stories depend on agent
- **Phase 4 (US2 DB Tests)**: Depends on Phase 2 - can run parallel with Phase 3
- **Phase 5 (US3 Web Form)**: Depends on Phase 2 - can run parallel with Phase 3
- **Phase 6 (US4 FastAPI)**: Depends on Phase 3 (agent) + Phase 5 (web form handler)
- **Phase 7 (US5 Gmail)**: Depends on Phase 6 (API mounted)
- **Phase 8 (US6 WhatsApp)**: Depends on Phase 6 (API mounted) - parallel with Phase 7
- **Phase 9 (US7 Kafka)**: Depends on Phase 3 (agent tools publish to Kafka)
- **Phase 10 (US8 Worker)**: Depends on Phase 9 (Kafka client) + Phase 3 (agent)
- **Phase 11 (US9 K8s)**: Static YAML - can start after Phase 1 (no Dockerfile dependency)
- **Phase 12 (US10 Docker)**: Depends on Phase 6 (API) + Phase 10 (worker) - needs running code
- **Phase 13 (US11 Monitoring)**: Depends on Phase 10 (worker produces metrics)
- **Phase 14 (Polish)**: Depends on all user stories complete

### User Story Dependencies

```
US1 (Agent Core) ──────────────┬──→ US4 (FastAPI) ──→ US5 (Gmail)
                               │                  ──→ US6 (WhatsApp) [parallel with US5]
                               ├──→ US7 (Kafka) ──→ US8 (Worker) ──→ US11 (Monitoring)
                               │
US2 (DB Tests) ───────────────[parallel with US1, depends only on Phase 2]
US3 (Web Form) ───────────────[parallel with US1, depends only on Phase 2]
US9  (K8s)    ────────────────[parallel after Phase 1, static YAML]
US10 (Docker) ────────────────[depends on US4 + US8, needs running code]
```

### Critical Path

Phase 1 → Phase 2 → Phase 3 (US1) → Phase 6 (US4) → Phase 9 (US7) → Phase 10 (US8) → Phase 14

### Within Each User Story

- Models/schemas before services/queries
- Services before endpoints/handlers
- Core implementation before integration
- Tests validate the story independently

### Parallel Opportunities

- **After Phase 1**: T003, T004, T005 can all run in parallel (different files)
- **After Phase 2**: US1 (Phase 3), US2 (Phase 4), US3 (Phase 5) can start in parallel
- **After Phase 3 (US1)**: US4, US7, US9, US10 can start in parallel
- **Phase 7 + Phase 8**: Gmail and WhatsApp handlers can be built in parallel
- **Phase 11 (K8s)**: T041-T045 can all run in parallel (independent YAML files)
- **Phase 12 (Docker)**: T051 can run parallel (Dockerfile independent of compose)

---

## Parallel Example: Phase 11 (Kubernetes)

```bash
# Launch all independent K8s manifests together:
Task: "Create k8s/namespace.yaml" (T041)
Task: "Create k8s/configmap.yaml" (T042)
Task: "Create k8s/secrets.yaml" (T043)
Task: "Create k8s/postgres/ manifests" (T044)
Task: "Create k8s/kafka/ manifests" (T045)
Task: "Create k8s/service.yaml" (T048)
Task: "Create k8s/ingress.yaml" (T049)

# Then sequentially (depend on above):
Task: "Create k8s/deployment-api.yaml" (T046)
Task: "Create k8s/deployment-worker.yaml" (T047)
Task: "Create k8s/hpa.yaml" (T050)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Database Foundation (T007-T010)
3. Complete Phase 3: Agent Core US1 (T011-T017)
4. **STOP and VALIDATE**: Run transition tests, verify agent works
5. Demo: Agent with 6 tools, formalized prompt, channel formatters

### Incremental Delivery

1. Setup + Foundation → Database ready
2. Add US1 (Agent) → Core agent functional → **MVP!**
3. Add US2 (DB Tests) + US3 (Web Form) → Form-to-response pipeline working
4. Add US4 (FastAPI) → Full API layer with health checks
5. Add US5 (Gmail) + US6 (WhatsApp) → All 3 channels operational
6. Add US7 (Kafka) + US8 (Worker) → Event-driven async processing
7. Add US9 (K8s) + US10 (Docker) → Deployment ready
8. Add US11 (Monitoring) → Observability complete
9. Polish → E2E tests, load tests, security hardening

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 60 |
| **Phase 1 (Setup)** | 6 tasks |
| **Phase 2 (Foundation)** | 4 tasks |
| **US1 (Agent Core)** | 7 tasks |
| **US2 (DB Tests)** | 2 tasks |
| **US3 (Web Form)** | 6 tasks |
| **US4 (FastAPI)** | 2 tasks |
| **US5 (Gmail)** | 4 tasks |
| **US6 (WhatsApp)** | 4 tasks |
| **US7 (Kafka)** | 2 tasks |
| **US8 (Worker)** | 3 tasks |
| **US9 (K8s)** | 10 tasks |
| **US10 (Docker)** | 2 tasks |
| **US11 (Monitoring)** | 3 tasks |
| **Polish** | 5 tasks |
| **Parallelizable [P] tasks** | 22 tasks |
| **Suggested MVP** | T001-T017 (17 tasks: Setup + Foundation + US1) |

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable after Phase 2
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths are relative to repository root
