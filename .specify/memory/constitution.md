<!--
  Sync Impact Report
  ===================
  Version change: 0.0.0 → 1.0.0 (MAJOR: initial ratification)
  Modified principles: N/A (first version)
  Added sections:
    - 6 Core Principles (Multi-Channel First, Agent Factory Paradigm,
      PostgreSQL as CRM, Event-Driven Architecture, Production-Grade Quality,
      Test-First Development)
    - Technology & Constraints
    - Development Workflow & Security
    - Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ compatible (Constitution Check section exists)
    - .specify/templates/spec-template.md ✅ compatible (user stories + edge cases align)
    - .specify/templates/tasks-template.md ✅ compatible (phased structure fits staged delivery)
  Follow-up TODOs: None
-->

# CRM Digital FTE Factory Constitution

## Core Principles

### I. Multi-Channel First

Every feature MUST work across all three supported channels with
channel-appropriate responses:

- **Gmail (Email)**: Formal tone, detailed responses, max 500 words,
  proper greeting and signature.
- **WhatsApp (Twilio)**: Conversational tone, concise responses,
  max 300 characters preferred, max 1600 chars absolute.
- **Web Form (Next.js/React)**: Semi-formal tone, balanced detail,
  max 300 words.

Channel support is non-negotiable. A feature that only works on one
channel is incomplete. Cross-channel customer identification MUST
maintain unified history (email address as primary key, phone as
secondary).

### II. Agent Factory Paradigm

Claude Code (General Agent) builds the Custom Agent (OpenAI Agents SDK).
Development follows the Agent Maturity Model:

- **Incubation** (Stage 1): Explore, prototype, discover requirements
  using Claude Code. Output: working prototype, MCP server, discovery log.
- **Specialization** (Stage 2): Transform prototype into production-grade
  Custom Agent. Output: OpenAI SDK agent, FastAPI service, PostgreSQL CRM,
  Kafka streaming, Kubernetes deployment.
- **Integration** (Stage 3): End-to-end testing, load testing, 24-hour
  operational validation.

The General Agent is the factory; the Custom Agent is the product.
Claude Code remains the development partner throughout all stages.

### III. PostgreSQL as CRM

The PostgreSQL database IS the CRM system. No external CRM integration
(Salesforce, HubSpot) is required or permitted in scope.

- Tables MUST include: `customers`, `customer_identifiers`,
  `conversations`, `messages`, `tickets`, `knowledge_base`,
  `channel_configs`, `agent_metrics`.
- pgvector extension MUST be used for semantic search on the
  `knowledge_base` table.
- All customer data MUST be unified across channels via the
  `customer_identifiers` table.

### IV. Event-Driven Architecture

Apache Kafka MUST be used for all asynchronous message routing:

- All channel inbound messages route through `fte.tickets.incoming`.
- Escalations publish to `fte.escalations`.
- Metrics publish to `fte.metrics`.
- Failed messages route to `fte.dlq` (dead letter queue).
- Channel-specific topics exist for debugging and replay.

Synchronous processing is only permitted for webhook acknowledgment
and health checks.

### V. Production-Grade Quality

Every component MUST meet production standards:

- **Validation**: Pydantic BaseModel for all tool inputs and API schemas.
- **Error handling**: Try/catch with graceful fallbacks on all tools;
  never expose stack traces to customers.
- **Logging**: Structured logging (JSON) with correlation IDs; no print
  statements in production code.
- **Health checks**: Every deployable component MUST expose a `/health`
  endpoint or equivalent liveness check.
- **Configuration**: Environment variables and ConfigMaps; NEVER
  hardcode values that change between environments.

### VI. Test-First Development

Edge cases discovered during incubation MUST become automated tests
during specialization:

- Minimum 10 documented edge cases per channel.
- Transition test suite MUST pass before production build begins.
- E2E tests MUST cover all three channels independently.
- Load tests MUST validate 24/7 readiness.
- Performance baseline: response time <3s processing, <30s delivery,
  accuracy >85%, escalation rate <20%.

## Technology & Constraints

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| API Framework | FastAPI | Latest |
| Agent SDK | OpenAI Agents SDK | Latest |
| Database | PostgreSQL + pgvector | 16+ |
| Streaming | Apache Kafka (aiokafka) | Latest |
| Orchestration | Kubernetes | 1.28+ |
| Web Form | React / Tailwind | Latest |
| Email | Gmail API + Pub/Sub | v1 |
| WhatsApp | Twilio WhatsApp API | Latest |
| MCP | Model Context Protocol | Latest |
| Testing | pytest + httpx + locust | Latest |

### Hard Constraints

- No external CRM integrations in scope.
- No full website build; only the standalone Web Support Form component.
- Twilio Sandbox is sufficient for WhatsApp (no production account needed).
- Response limits enforced: Email 500 words, WhatsApp 300 chars, Web 300 words.
- Operating cost target: <$1,000/year for the Digital FTE.
- Agent model: `gpt-4o` via OpenAI Agents SDK.

### Escalation Rules (Non-Negotiable)

The agent MUST escalate (never answer directly) when:
- Customer mentions "lawyer", "legal", "sue", or "attorney".
- Customer uses profanity or aggressive language (sentiment < 0.3).
- Customer asks about pricing or refunds.
- Agent cannot find relevant info after 2 knowledge base searches.
- Customer explicitly requests human help.

### Guardrails

- NEVER discuss competitor products.
- NEVER promise features not in documentation.
- ALWAYS create a ticket before responding.
- ALWAYS check sentiment before closing a conversation.
- ALWAYS format responses for the target channel.

## Development Workflow & Security

### Staged Delivery

All work MUST follow the three-stage structure:

1. **Stage 1 (Incubation)**: `specs/001-stage1-incubation/` - Prototype,
   MCP server, discovery, skills manifest.
2. **Stage 2 (Specialization)**: `specs/002-stage2-specialization/` -
   Production agent, channels, database, Kafka, Kubernetes.
3. **Stage 3 (Integration)**: `specs/003-stage3-integration/` - E2E tests,
   load tests, documentation, runbooks.

Each stage uses the full SpecifyPlus workflow: `/sp.specify` then
`/sp.plan` then `/sp.tasks` then `/sp.implement`.

### Security Requirements

- No hardcoded secrets or API keys; use `.env` files and K8s Secrets.
- Twilio webhook signature validation MUST be enforced.
- Gmail API credentials stored securely (never in source control).
- CORS configured appropriately (not `*` in production).
- Input sanitization on all user-facing endpoints.

### Code Quality Gates

- All Pydantic models MUST have validators for user-facing inputs.
- All async functions MUST have proper error handling.
- All database queries MUST use parameterized inputs (no SQL injection).
- All API endpoints MUST return proper HTTP status codes.

## Governance

This constitution supersedes all other development practices for the
CRM Digital FTE Factory project. All code, specs, plans, and tasks
MUST comply with these principles.

### Amendment Process

1. Propose amendment with rationale.
2. Document impact on existing artifacts.
3. Update constitution version (semantic versioning).
4. Propagate changes to dependent specs, plans, and tasks.

### Compliance

- Every spec MUST reference applicable constitution principles.
- Every plan MUST include a Constitution Check section.
- Every PR/review MUST verify compliance with guardrails and
  escalation rules.
- Complexity beyond these principles MUST be justified in a
  Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-02-07 | **Last Amended**: 2026-02-07
