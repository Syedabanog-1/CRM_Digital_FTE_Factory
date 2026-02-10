# Feature Specification: Stage 2 Specialization - Production-Grade Customer Success Digital FTE

**Feature Branch**: `002-stage2-specialization`
**Created**: 2026-02-09
**Status**: Complete
**Input**: User description: "Transform the Stage 1 incubation prototype into a production-grade Custom Agent using OpenAI Agents SDK, FastAPI, PostgreSQL, Kafka, real channel integrations (Gmail, WhatsApp, Web Form), and Kubernetes deployment."
**Predecessor**: Stage 1 Incubation (`001-stage1-incubation`) - COMPLETE

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Transition from Prototype to Production Agent (Priority: P1)

As a developer, I need to transform the Stage 1 prototype's MCP tools into production-grade OpenAI Agents SDK tools with strict input validation, error handling, and a formalized system prompt, so that the agent operates autonomously with explicit constraints and guardrails.

The transition involves extracting all working prompts, edge cases, and response patterns discovered during incubation into a documented transition checklist. Each MCP tool becomes an OpenAI Agents SDK `@function_tool` with Pydantic input schemas. The system prompt is formalized with hard constraints, escalation triggers, channel awareness rules, and a required tool execution workflow (create ticket first, check history, search KB, then respond).

**Why this priority**: The agent is the core of the entire system. Without a working production agent, no channel integration or infrastructure matters. This is the foundation all other stories build upon.

**Independent Test**: Can be tested by running the transition test suite against the new agent - verifying edge case handling, escalation decisions, channel-appropriate response lengths, and tool execution order all match or exceed Stage 1 behavior.

**Acceptance Scenarios**:

1. **Given** the Stage 1 prototype's 6 MCP tools, **When** they are transformed to `@function_tool` functions, **Then** each tool has a Pydantic input schema, try/catch error handling, and a detailed docstring for LLM consumption
2. **Given** the production system prompt, **When** it is reviewed, **Then** it contains explicit hard constraints (never discuss pricing, never promise undocumented features), escalation triggers, channel awareness rules, and the required tool execution order
3. **Given** the transition test suite, **When** all tests are run, **Then** they pass: empty message handling, pricing escalation, angry customer escalation, channel-appropriate response lengths (email formal, WhatsApp concise), and correct tool execution order (create_ticket first, send_response last)
4. **Given** the transition checklist, **When** reviewed, **Then** it documents all discovered requirements, working prompts, edge cases, response patterns, escalation rules, and performance baseline from Stage 1

---

### User Story 2 - PostgreSQL CRM Database (Priority: P1)

As a developer, I need all customer data, conversations, tickets, and knowledge base entries persisted in a PostgreSQL database with pgvector for semantic search, so that the system maintains state across restarts, supports concurrent access, and enables intelligent knowledge retrieval.

The database replaces the Stage 1 in-memory dictionaries with eight production tables: customers (unified across channels), customer_identifiers (cross-channel matching), conversations (thread tracking), messages (with channel and delivery tracking), tickets (lifecycle management), knowledge_base (with vector embeddings for semantic search), channel_configs (per-channel settings), and agent_metrics (performance tracking). All tables use UUID primary keys, timestamps with timezone, and JSONB for flexible metadata.

**Why this priority**: Every other component (agent tools, channel handlers, message processor) depends on persistent storage. The database IS the CRM system.

**Independent Test**: Can be tested by running schema creation, inserting sample data across all tables, performing vector similarity searches on the knowledge base, and verifying cross-channel customer resolution via the customer_identifiers table.

**Acceptance Scenarios**:

1. **Given** the database schema, **When** applied to a fresh PostgreSQL 16+ instance with pgvector, **Then** all eight tables are created with proper foreign keys, indexes, and constraints
2. **Given** a customer who contacts via email, **When** their record is created, **Then** they can be found by email in the customers table and by phone via the customer_identifiers table
3. **Given** product documentation loaded into the knowledge_base table with embeddings, **When** a semantic search query is executed, **Then** relevant results are returned ranked by vector similarity
4. **Given** messages from multiple channels for the same conversation, **When** queried, **Then** each message retains its channel, direction, role, delivery status, and external channel message ID
5. **Given** the agent_metrics table, **When** metrics are recorded per channel, **Then** they can be aggregated for daily reports showing response times, escalation rates, and sentiment by channel

---

### User Story 3 - Web Support Form (Priority: P1)

As a customer visiting TechCorp's website, I need a standalone support form where I can submit my name, email, subject, category, priority, and detailed message, so that I receive a ticket ID and can check my ticket status while the AI agent processes my request.

The form is a complete, embeddable component with client-side validation (name >= 2 chars, valid email, subject >= 5 chars, message >= 10 chars, valid category), a submission flow that creates a ticket and publishes to the processing queue, a success confirmation with ticket ID, and a ticket status checking endpoint. The backend validates all inputs with Pydantic models and returns structured error responses.

**Why this priority**: The web support form is explicitly marked as REQUIRED by the hackathon. It is a complete deliverable that demonstrates the full request-to-response pipeline and scores 10 points independently.

**Independent Test**: Can be tested by submitting the form with valid data and verifying a ticket ID is returned, submitting with invalid data and verifying validation errors, and checking ticket status after submission.

**Acceptance Scenarios**:

1. **Given** a customer fills out the form with valid data (name, email, subject, category, message), **When** they submit, **Then** they receive a ticket ID and confirmation message with estimated response time
2. **Given** a customer submits with invalid data (short name, bad email, empty message), **When** the form validates, **Then** specific error messages appear for each invalid field without submitting
3. **Given** a ticket ID from a previous submission, **When** the customer checks status, **Then** they see the current ticket status (open/processing/resolved) and any agent responses
4. **Given** the form component, **When** embedded in any page, **Then** it renders as a self-contained widget with consistent styling and no external dependencies beyond the API endpoint
5. **Given** a successful submission, **When** the customer wants to submit another request, **Then** the form resets to its initial state with a clear call-to-action

---

### User Story 4 - Multi-Channel Intake via FastAPI (Priority: P1)

As the system, I need a FastAPI service that receives customer messages from all three channels (Gmail webhooks, WhatsApp/Twilio webhooks, and the web support form), normalizes them into a unified format, and publishes them to the event streaming queue for agent processing.

The API exposes a health check endpoint, channel-specific webhook endpoints (Gmail via Pub/Sub notifications, WhatsApp via Twilio with signature validation), the web form submission endpoint, a customer lookup endpoint, a conversation history endpoint, and a channel metrics endpoint. Each incoming message is normalized with channel, content, customer identifier, and metadata before publishing.

**Why this priority**: The API is the entry point for ALL customer interactions. Without it, no channel can reach the agent.

**Independent Test**: Can be tested by sending HTTP requests to each endpoint and verifying correct responses: health check returns status, form submission returns ticket ID, Gmail webhook processes notification, WhatsApp webhook validates Twilio signature.

**Acceptance Scenarios**:

1. **Given** the FastAPI service is running, **When** a GET request hits `/health`, **Then** it returns status "healthy" with channel statuses and current timestamp
2. **Given** a Gmail Pub/Sub notification, **When** it hits `/webhooks/gmail`, **Then** the email is parsed (sender, subject, body) and published to the unified ticket queue
3. **Given** a Twilio WhatsApp webhook with valid signature, **When** it hits `/webhooks/whatsapp`, **Then** the message is parsed (phone, body, metadata) and published to the unified ticket queue
4. **Given** a Twilio WhatsApp webhook with invalid signature, **When** it hits `/webhooks/whatsapp`, **Then** it returns 403 Forbidden
5. **Given** a customer email, **When** `/customers/lookup?email=x` is called, **Then** the customer's unified profile with cross-channel history is returned
6. **Given** the past 24 hours of interactions, **When** `/metrics/channels` is called, **Then** per-channel metrics (total conversations, average sentiment, escalation count) are returned

---

### User Story 5 - Gmail Channel Integration (Priority: P2)

As a customer sending an email to TechCorp's support address, I need my email to be automatically received, processed by the AI agent, and replied to in the same email thread with a formal, detailed response, so that I get help without waiting for business hours.

The Gmail integration uses the Gmail API with Pub/Sub push notifications (or polling as fallback) to detect new incoming emails. It parses the From header for customer email, extracts the subject and plain-text body, and normalizes the message. Replies are sent in the same thread with proper "Re:" subject prefix and formal formatting (greeting, body, signature, ticket reference).

**Why this priority**: Email is the most common business channel and demonstrates real-world channel integration. It builds on the API layer from US4.

**Independent Test**: Can be tested using Gmail API sandbox - sending a test email, verifying it is received and parsed, and checking that a reply appears in the same thread.

**Acceptance Scenarios**:

1. **Given** a new email arrives in the support inbox, **When** the Pub/Sub notification fires, **Then** the handler extracts sender email, subject, and body into the normalized message format
2. **Given** a parsed email message, **When** the agent generates a response, **Then** the reply is sent in the same email thread with "Re:" prefix, formal greeting, body, signature, and ticket reference
3. **Given** an email about a product feature, **When** processed, **Then** the response is detailed (up to 500 words), formal in tone, and includes the relevant documentation
4. **Given** an email mentioning pricing, **When** processed, **Then** the agent escalates and the reply acknowledges the escalation with a reference number

---

### User Story 6 - WhatsApp Channel Integration (Priority: P2)

As a customer messaging TechCorp on WhatsApp, I need my message to be received, processed by the AI agent, and replied to on WhatsApp with a concise, conversational response, so that I get quick help in a familiar messaging format.

The WhatsApp integration uses the Twilio WhatsApp API. Incoming messages arrive as Twilio webhooks with signature validation. The handler extracts the phone number, message body, and metadata. Responses are sent back via the Twilio API, kept concise (under 300 characters preferred, max 1600 absolute), and include a prompt for further help or human escalation.

**Why this priority**: WhatsApp is the second real channel integration, proving multi-channel capability. Twilio Sandbox is sufficient for development.

**Independent Test**: Can be tested using Twilio WhatsApp Sandbox - sending a message, verifying webhook receipt and parsing, and checking the concise reply.

**Acceptance Scenarios**:

1. **Given** a WhatsApp message arrives via Twilio webhook, **When** the signature is validated, **Then** the handler extracts phone number, body, profile name, and WhatsApp ID into normalized format
2. **Given** a product question via WhatsApp, **When** the agent responds, **Then** the reply is under 300 characters, conversational in tone, and includes a prompt to type "human" for live support
3. **Given** a response longer than 1600 characters, **When** sent, **Then** it is split into multiple WhatsApp messages at sentence boundaries
4. **Given** a WhatsApp customer sends "human" or "agent", **When** processed, **Then** the conversation is escalated immediately with the customer notified

---

### User Story 7 - Event Streaming with Kafka (Priority: P2)

As the system, I need all channel messages to flow through an event streaming layer so that message processing is asynchronous, decoupled from channel intake, resilient to failures (dead letter queue), and observable (metrics topic).

Nine Kafka topics handle the message lifecycle: a unified incoming topic, three channel-specific inbound topics, two channel-specific outbound topics, an escalations topic, a metrics topic, and a dead letter queue for failed processing. Producers publish from channel handlers; consumers in the message processor worker pull and process through the agent.

**Why this priority**: Kafka decouples intake from processing, enabling independent scaling and failure isolation. It is required by the constitution (Principle IV).

**Independent Test**: Can be tested by publishing a message to the incoming topic and verifying the consumer picks it up, processes it, and publishes metrics. Dead letter queue can be tested by injecting a malformed message.

**Acceptance Scenarios**:

1. **Given** a message published to `fte.tickets.incoming`, **When** the consumer processes it, **Then** the agent generates a response and metrics are published to `fte.metrics`
2. **Given** a message that fails processing, **When** the error is caught, **Then** it is published to `fte.dlq` with the error details and original message preserved
3. **Given** an escalation decision, **When** the agent escalates, **Then** an event is published to `fte.escalations` with ticket ID, reason, and urgency
4. **Given** channel-specific topics, **When** messages flow through, **Then** they can be monitored and replayed independently per channel

---

### User Story 8 - Unified Message Processor Worker (Priority: P2)

As the system, I need a background worker that consumes messages from all channels via Kafka, resolves or creates customers, manages conversations, runs the agent, stores results, and publishes metrics, so that all channels are processed through a single consistent pipeline.

The worker resolves customers by email (primary) or phone (secondary via customer_identifiers), gets or creates conversations (active within 24 hours reuses existing), stores inbound messages, loads conversation history for context, runs the OpenAI agent, stores agent responses with latency and tool call metadata, and publishes processing metrics per channel.

**Why this priority**: This is the glue between channels and the agent. Without it, messages sit in Kafka unprocessed.

**Independent Test**: Can be tested by publishing a test message to Kafka, verifying the worker processes it end-to-end, and checking that customer, conversation, message, and metric records are created in the database.

**Acceptance Scenarios**:

1. **Given** a web form message in Kafka, **When** the worker processes it, **Then** the customer is resolved by email, conversation is created/reused, message is stored, agent response is generated and stored, and metrics are published
2. **Given** a WhatsApp message from a new phone number, **When** the worker processes it, **Then** a new customer is created with a linked WhatsApp identifier in customer_identifiers
3. **Given** a returning customer (same email, different channel), **When** the worker processes it, **Then** the existing customer is resolved and the new message is added to their active conversation
4. **Given** a processing error, **When** the worker catches it, **Then** an apologetic response is sent to the customer via their channel and the error is published for human review

---

### User Story 9 - Kubernetes Deployment (Priority: P3)

As an operator, I need the complete system deployed on Kubernetes with multi-pod scaling, health checks, auto-scaling, and secure secret management, so that the Digital FTE runs 24/7 with high availability.

The deployment includes a dedicated namespace, ConfigMaps for environment settings, Secrets for API keys and credentials, separate Deployments for the API (3 replicas) and worker (3 replicas), a Service and Ingress with TLS, and Horizontal Pod Autoscalers targeting 70% CPU utilization with max 20 API pods and 30 worker pods.

**Why this priority**: Kubernetes deployment is the final infrastructure layer. The system must be functionally complete before deploying.

**Independent Test**: Can be tested by applying all manifests to a local minikube cluster, verifying pods start and pass health checks, and confirming the service is reachable via the ingress.

**Acceptance Scenarios**:

1. **Given** all Kubernetes manifests, **When** applied to a cluster, **Then** the namespace, ConfigMap, Secrets, Deployments, Service, Ingress, and HPAs are all created successfully
2. **Given** running API pods, **When** the health endpoint is probed, **Then** liveness and readiness probes pass
3. **Given** increased CPU load, **When** utilization exceeds 70%, **Then** the HPA scales up additional pods (up to max)
4. **Given** a pod crash, **When** Kubernetes restarts it, **Then** the replacement pod joins the service within 30 seconds and resumes processing

---

### User Story 10 - Docker and Local Development (Priority: P3)

As a developer, I need a Dockerfile and docker-compose.yml that brings up the entire system locally (API, worker, PostgreSQL, Kafka, Zookeeper) with a single command, so that I can develop and test without cloud infrastructure.

**Why this priority**: Local development environment is essential for productivity but not required for the core system to function.

**Independent Test**: Can be tested by running `docker-compose up` and verifying all services start, the API is reachable, and a message can be processed end-to-end.

**Acceptance Scenarios**:

1. **Given** a fresh checkout, **When** `docker-compose up` is run, **Then** all services (API, worker, PostgreSQL with pgvector, Kafka, Zookeeper) start and become healthy
2. **Given** the running docker-compose stack, **When** a web form submission is sent to localhost, **Then** it flows through the full pipeline and produces a response
3. **Given** the Dockerfile, **When** built, **Then** it produces a single image that can run as either the API (uvicorn) or worker (python message_processor) based on the command

---

### User Story 11 - Monitoring and Channel Metrics (Priority: P3)

As an operator, I need channel-specific performance metrics, structured JSON logging with correlation IDs, and a metrics endpoint, so that I can monitor the Digital FTE's health and performance across all channels.

**Why this priority**: Monitoring is essential for production operation but the system works without it.

**Independent Test**: Can be tested by processing messages across channels and verifying metrics are recorded, logs are structured JSON, and the metrics endpoint returns per-channel breakdowns.

**Acceptance Scenarios**:

1. **Given** messages processed across three channels over 24 hours, **When** `/metrics/channels` is called, **Then** per-channel metrics show total conversations, average sentiment, and escalation counts
2. **Given** a log entry, **When** examined, **Then** it is structured JSON with timestamp, level, correlation ID, channel, and message
3. **Given** agent_metrics table records, **When** queried for daily report, **Then** response time p95, accuracy, escalation rate, and channel distribution are available

---

### Edge Cases

- What happens when Gmail API credentials expire or Pub/Sub subscription lapses?
- How does the system handle a Twilio webhook with valid signature but empty message body?
- What happens when PostgreSQL is temporarily unavailable during message processing?
- How does the system handle Kafka broker unavailability (connection refused)?
- What happens when the OpenAI API returns a rate limit error (429)?
- How does the system handle a customer who exists by phone (WhatsApp) but later contacts by email with no existing email record?
- What happens when the knowledge base has no embeddings yet (empty table)?
- How does the system handle concurrent messages from the same customer on different channels simultaneously?
- What happens when a Kubernetes pod is killed mid-processing of a message?
- How does the system handle an email with attachments (images, PDFs)?
- What happens when the web form receives a submission with XSS in the message field?
- How does the system handle a WhatsApp message containing only emojis or media?
- What happens when the docker-compose PostgreSQL container runs out of disk space?
- How does the system handle timezone differences across channels (email headers vs WhatsApp UTC)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST transform all Stage 1 MCP tools into OpenAI Agents SDK `@function_tool` functions with Pydantic input validation and try/catch error handling
- **FR-002**: System MUST use a formalized system prompt with explicit hard constraints, escalation triggers, channel awareness rules, and required tool execution order
- **FR-003**: System MUST persist all data in PostgreSQL 16+ with pgvector extension for semantic search on the knowledge base
- **FR-004**: System MUST maintain eight database tables: customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics
- **FR-005**: System MUST receive Gmail messages via Gmail API with Pub/Sub push notifications and reply in the same email thread
- **FR-006**: System MUST receive WhatsApp messages via Twilio webhook with signature validation and reply via Twilio API
- **FR-007**: System MUST provide a complete, standalone web support form with client-side and server-side validation, ticket creation, and status checking
- **FR-008**: System MUST route all incoming messages through Kafka event streaming with nine topics (incoming, 3 channel inbound, 2 channel outbound, escalations, metrics, DLQ)
- **FR-009**: System MUST process all channel messages through a unified worker that resolves customers, manages conversations, runs the agent, and stores results
- **FR-010**: System MUST expose a FastAPI service with endpoints for health check, channel webhooks, form submission, customer lookup, conversation history, and channel metrics
- **FR-011**: System MUST deploy to Kubernetes with separate API and worker deployments, horizontal pod autoscaling, health probes, and TLS ingress
- **FR-012**: System MUST provide a Dockerfile and docker-compose.yml for local development with all dependencies (PostgreSQL, pgvector, Kafka, Zookeeper)
- **FR-013**: System MUST enforce channel-specific response formatting: email (formal, greeting, signature, max 500 words), WhatsApp (concise, max 300 chars preferred / 1600 absolute), web (semi-formal, max 300 words)
- **FR-014**: System MUST identify customers across channels using email as primary key and phone as secondary via the customer_identifiers table
- **FR-015**: System MUST enforce all escalation rules from the constitution: legal terms, profanity/sentiment < 0.3, pricing/refunds, failed KB search after 2 attempts, explicit human requests
- **FR-016**: System MUST enforce all guardrails: never discuss competitors, never promise undocumented features, always create ticket before responding, always check sentiment before closing, always use channel-appropriate formatting
- **FR-017**: System MUST use structured JSON logging with correlation IDs for all components
- **FR-018**: System MUST record per-channel metrics (response time, escalation rate, sentiment) in the agent_metrics table
- **FR-019**: System MUST use the `gpt-4o` model via OpenAI Agents SDK for the production agent
- **FR-020**: System MUST handle processing errors gracefully by sending an apologetic response to the customer and publishing the error for human review
- **FR-021**: System MUST create a transition checklist documenting all discoveries, working prompts, edge cases, and performance baselines from Stage 1
- **FR-022**: System MUST validate Twilio webhook signatures on all WhatsApp endpoints to prevent unauthorized access
- **FR-023**: System MUST store all secrets (API keys, credentials) in environment variables or Kubernetes Secrets, never in source code

### Key Entities

- **Customer**: A person contacting support, identified by email (primary) and phone (secondary), with name, metadata, and creation timestamp. Unified across all channels via the customer_identifiers table.
- **Customer Identifier**: A link between an identifier (email, phone, whatsapp) and a customer record, enabling cross-channel resolution. Unique constraint on (type, value).
- **Conversation**: A thread of messages between a customer and the agent, with initial channel, status (active/resolved/escalated), sentiment score, resolution type, and metadata. Active conversations within 24 hours are reused.
- **Message**: A single communication unit with conversation reference, channel, direction (inbound/outbound), role (customer/agent/system), content, timestamps, token usage, latency, tool calls, external channel message ID, and delivery status.
- **Ticket**: A support interaction record with conversation and customer references, source channel, category, priority, status (open/in_progress/escalated/resolved/closed), and resolution notes.
- **Knowledge Base Entry**: A product documentation article with title, content, category, vector embedding (1536 dimensions), and timestamps. Searchable by semantic similarity.
- **Channel Config**: Per-channel settings including enabled status, configuration (API keys, webhook URLs), response template, and max response length.
- **Agent Metric**: A time-series performance record with metric name, value, optional channel, flexible dimensions, and timestamp.

### Assumptions

- Twilio WhatsApp Sandbox is sufficient for development and demonstration; production Twilio account is not required
- Gmail API sandbox credentials are available for development; actual Gmail sending is tested manually
- PostgreSQL 16+ with pgvector extension is available (via Docker for local, managed service for production)
- Apache Kafka is available (via Docker for local, Confluent Cloud or similar for production)
- Kubernetes cluster is available (minikube for local, any cloud provider for production)
- The web support form is a React/Next.js component but can be adapted to any frontend framework
- OpenAI API key with gpt-4o access is available via environment variable
- Stage 1 prototype code, tests, and context files are available and passing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All transition tests pass, confirming agent behavior matches or exceeds Stage 1 prototype (edge cases, escalation, channel formatting)
- **SC-002**: The production agent correctly answers product questions for at least 85% of test queries using vector-based knowledge search
- **SC-003**: All three channels (email, WhatsApp, web form) produce correctly formatted responses: email formal with greeting/signature, WhatsApp concise under 300 chars, web semi-formal
- **SC-004**: Escalation triggers are correctly detected for 100% of pricing, refund, legal, profanity, and explicit human-request scenarios
- **SC-005**: Cross-channel customer identification works with >95% accuracy - a customer contacting via email then WhatsApp is recognized as the same person
- **SC-006**: The web support form validates all inputs, creates tickets, and shows ticket status with zero server errors on valid submissions
- **SC-007**: End-to-end message processing latency is under 3 seconds (p95) from message receipt to agent response stored
- **SC-008**: The system maintains >99.9% uptime over a 24-hour test period with pod restarts and scaling events
- **SC-009**: All Kubernetes manifests apply cleanly and pods pass health checks within 30 seconds of startup
- **SC-010**: Docker-compose brings up the full local stack (API, worker, PostgreSQL, Kafka) and processes a test message end-to-end
- **SC-011**: No message is lost during processing - failed messages are routed to the dead letter queue with full context preserved
- **SC-012**: Operating cost projection for the Digital FTE is under $1,000/year based on resource usage during the 24-hour test
