# Tasks: Stage 1 Incubation - Customer Success AI Agent Prototype

**Input**: Design documents from `/specs/001-stage1-incubation/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Tests**: Included — spec Principle VI mandates test-first development; plan.md includes a full `tests/` directory.

**Organization**: Tasks grouped by user story. Each story is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency management, environment configuration

- [x] T001 Create project directory structure: `src/`, `src/models/`, `src/services/`, `src/memory/`, `tests/`, `context/` with `__init__.py` files per plan.md
- [x] T002 Create `requirements.txt` with dependencies: `mcp`, `openai`, `pydantic`, `pytest`, `pytest-asyncio`, `python-dotenv`
- [x] T003 [P] Create `.env.example` with `OPENAI_API_KEY=sk-your-key-here` placeholder and add `.env` to `.gitignore`
- [x] T004 [P] Create `pyproject.toml` or `setup.cfg` with Python 3.11+ requirement and project metadata

**Checkpoint**: Project skeleton exists, dependencies installable via `pip install -r requirements.txt`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and shared services that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Implement Channel enum in `src/models/channel.py` — values: `email`, `whatsapp`, `web_form` with display labels and formatting config (max length, tone, greeting/signature toggles per research.md R4)
- [x] T006 [P] Implement Customer model in `src/models/customer.py` — fields: id (UUID), email (unique, validated), phone (optional, country code), name, created_at, metadata per data-model.md
- [x] T007 [P] Implement Conversation model in `src/models/conversation.py` — fields: id, customer_id, initial_channel, started_at, ended_at, status (active/resolved/escalated), sentiment_score, resolution_type, topics, metadata with state transitions per data-model.md
- [x] T008 [P] Implement Message model in `src/models/message.py` — fields: id, conversation_id, channel, direction (inbound/outbound), role (customer/agent/system), content (non-empty validated), created_at, tokens_used, latency_ms per data-model.md
- [x] T009 [P] Implement Ticket model in `src/models/ticket.py` — fields: id, conversation_id, customer_id, source_channel, category, priority, status (open/in_progress/escalated/resolved/closed), created_at, resolved_at, resolution_notes, escalation_reason with state transitions per data-model.md
- [x] T010 [P] Implement KnowledgeBaseEntry model in `src/models/knowledge_base.py` — fields: id, title, content, category, keywords (list), created_at per data-model.md
- [x] T011 [P] Implement CustomerIdentifier model in `src/models/customer.py` (same file as Customer) — fields: identifier_type, identifier_value, customer_id, verified; unique constraint on (type, value) per data-model.md
- [x] T012 Create `src/models/__init__.py` with re-exports of all models: Channel, Customer, CustomerIdentifier, Conversation, Message, Ticket, KnowledgeBaseEntry
- [x] T013 Write foundational model tests in `tests/test_models.py` — test Pydantic validation, required fields, enum values, state transitions, edge cases (empty content, invalid email, invalid channel)

**Checkpoint**: All data models defined and validated. User story implementation can now begin.

---

## Phase 3: User Story 1 — Development Dossier Creation (Priority: P1) 🎯 MVP

**Goal**: Create complete context dossier with 5 files so the AI agent has all background information for TechCorp customer support.

**Independent Test**: Verify all five context files exist with sufficient content; sample-tickets.json contains 50+ entries with balanced channel distribution.

### Tests for User Story 1

- [x] T014 [P] [US1] Write dossier validation tests in `tests/test_dossier.py` — verify 5 files exist in `context/`, sample-tickets.json has 50+ entries, channels balanced, product-docs covers 5+ features, escalation-rules defines all triggers

### Implementation for User Story 1

- [x] T015 [P] [US1] Create company profile in `context/company-profile.md` — TechCorp SaaS company description: products (project management, analytics, integrations), pricing tiers, team size, founding story, mission
- [x] T016 [P] [US1] Create product documentation in `context/product-docs.md` — at least 5 product features with detailed descriptions: account management, project boards, analytics dashboard, integrations, notification system, API access
- [x] T017 [P] [US1] Create escalation rules in `context/escalation-rules.md` — triggers: pricing/refund questions, legal threats (lawyer/sue/attorney), profanity/aggressive language (sentiment < 0.3), failed KB search after 2 attempts, explicit human requests per constitution
- [x] T018 [P] [US1] Create brand voice guide in `context/brand-voice.md` — TechCorp communication style: professional but friendly, channel-specific tone (formal email, casual WhatsApp, balanced web), prohibited phrases, emoji policy
- [x] T019 [US1] Create sample tickets dataset in `context/sample-tickets.json` — 50+ entries with balanced email/whatsapp/web_form distribution; include product questions, billing inquiries, bug reports, feature requests, escalation-worthy messages, multi-language attempts, edge cases (empty, emoji-only, very long)

**Checkpoint**: `context/` directory complete with 5 files. Dossier validation tests pass. Agent has all background context.

---

## Phase 4: User Story 2 — Core Interaction Prototype (Priority: P1) 🎯 MVP

**Goal**: Working Python prototype that processes customer messages from any channel, searches KB, generates responses with correct channel formatting, and detects escalation triggers.

**Independent Test**: Pass 20+ sample messages from different channels; verify appropriate responses and correct escalation decisions.

### Tests for User Story 2

- [x] T020 [P] [US2] Write knowledge base search tests in `tests/test_knowledge_base.py` — test fuzzy matching with difflib, empty query, no matches, partial matches, result ranking, max_results limit per research.md R1
- [x] T021 [P] [US2] Write channel formatter tests in `tests/test_channel_formatter.py` — test email (formal, greeting, signature, ≤500 words), WhatsApp (concise, ≤300 chars, no greeting), web form (semi-formal, ≤300 words, next-step suggestion) per research.md R4
- [x] T022 [P] [US2] Write escalation engine tests in `tests/test_escalation_engine.py` — test pricing trigger, refund trigger, legal threats, profanity, explicit human request, no-match after 2 attempts, edge cases (disguised pricing question)
- [x] T023 [P] [US2] Write message processor tests in `tests/test_message_processor.py` — test end-to-end: message in → KB search → response generation → channel formatting → escalation check; test all 3 channels

### Implementation for User Story 2

- [x] T024 [P] [US2] Implement knowledge base service in `src/services/knowledge_base.py` — load `context/product-docs.md`, parse into entries, fuzzy search via `difflib.SequenceMatcher` + keyword extraction, return top-N results per research.md R1
- [x] T025 [P] [US2] Implement channel formatter service in `src/services/channel_formatter.py` — format responses per channel: email (greeting + body + signature, ≤500 words), WhatsApp (body only, ≤300 chars, truncate with "..."), web form (brief greeting + body + help link, ≤300 words) per research.md R4
- [x] T026 [P] [US2] Implement escalation engine in `src/services/escalation_engine.py` — check triggers: pricing keywords, refund keywords, legal terms (lawyer/sue/attorney), profanity list, sentiment < 0.3, explicit human request phrases, failed KB search count per constitution escalation rules
- [x] T027 [US2] Implement message processor in `src/services/message_processor.py` — core interaction loop: accept message + channel metadata → normalize → search KB → generate response (OpenAI gpt-4o-mini with KB context injection per research.md R6) → format for channel → check escalation → return result
- [x] T028 [US2] Create CLI entry point in `src/main.py` — interactive loop: select channel → enter message → display formatted response → show escalation status; support multi-turn within session per quickstart.md

**Checkpoint**: Core interaction loop works end-to-end. 20+ sample messages processed correctly. Channel formatting verified. Escalation triggers detected. Tests pass.

---

## Phase 5: User Story 3 — Conversation Memory and State Tracking (Priority: P2)

**Goal**: Prototype remembers conversation context across messages; handles follow-ups, cross-channel customer identification, and sentiment tracking.

**Independent Test**: Simulate multi-turn conversation where customer asks follow-up questions; verify agent references prior context.

### Tests for User Story 3

- [x] T029 [P] [US3] Write conversation store tests in `tests/test_conversation_store.py` — test add/get/update conversations, message append, lookup by customer, cross-session persistence (within runtime), concurrent conversations per research.md R5
- [x] T030 [P] [US3] Write sentiment analyzer tests in `tests/test_sentiment_analyzer.py` — test positive words → high score, negative words → low score, profanity → steep drop, legal terms → steep drop, neutral message → ~0.5, empty/emoji-only → neutral, threshold crossing per research.md R3
- [x] T031 [P] [US3] Write customer resolver tests in `tests/test_customer_resolver.py` — test email lookup, phone-to-email mapping, new customer creation, same customer different channels, unknown identifier handling per data-model.md CustomerIdentifier

### Implementation for User Story 3

- [x] T032 [P] [US3] Implement conversation store in `src/memory/conversation_store.py` — singleton class with dicts: `customers` (by email), `conversations` (by id), `tickets` (by id), `customer_identifiers` (phone/alt-email → primary email); CRUD operations for all entities per research.md R5
- [x] T033 [P] [US3] Implement sentiment analyzer in `src/services/sentiment_analyzer.py` — keyword dictionary: positive words (+0.1), negative words (-0.1), profanity (-0.3), legal terms (-0.5); aggregate and normalize to 0.0-1.0 scale per research.md R3
- [x] T034 [P] [US3] Implement customer resolver in `src/services/customer_resolver.py` — resolve customer by email (primary) or phone (secondary via CustomerIdentifier lookup); create new customer if unknown; link identifiers across channels per FR-006
- [x] T035 [US3] Integrate memory into message processor in `src/services/message_processor.py` — update process_message to: resolve customer identity → load/create conversation → append message to history → update sentiment score → inject conversation context into LLM prompt → track resolution status
- [x] T036 [US3] Update CLI in `src/main.py` to support multi-turn conversations — prompt for customer email at start, maintain conversation across messages, display sentiment score and conversation status

**Checkpoint**: Multi-turn conversations work. Follow-up questions reference prior context. Cross-channel identity resolution works. Sentiment tracking triggers escalation at threshold. Tests pass.

---

## Phase 6: User Story 4 — MCP Server with Agent Tools (Priority: P2)

**Goal**: Expose all prototype capabilities as an MCP server with 6 callable tools per contracts/mcp-tools.md.

**Independent Test**: Connect MCP client, invoke each tool, verify correct inputs/outputs and error handling.

### Tests for User Story 4

- [x] T037 [P] [US4] Write MCP server tests in `tests/test_mcp_server.py` — test each tool: search_knowledge_base (query, max_results, empty, no-match), create_ticket (valid, missing fields, invalid channel), get_customer_history (known, unknown), escalate_to_human (valid, unknown ticket, empty reason), send_response (valid, truncation, unknown ticket), analyze_sentiment (valid, empty) per contracts/mcp-tools.md

### Implementation for User Story 4

- [x] T038 [US4] Implement MCP server in `src/mcp_server.py` — create `mcp.Server` instance with `@server.tool()` decorators for 6 tools per research.md R2: search_knowledge_base, create_ticket, get_customer_history, escalate_to_human, send_response, analyze_sentiment; wire each tool to corresponding service; stdio transport per contracts/mcp-tools.md
- [x] T039 [US4] Add MCP server entry point — ensure `python -m src.mcp_server` starts the server on stdio transport per quickstart.md

**Checkpoint**: MCP server starts, exposes 6 tools, all tools callable with correct I/O per contracts. Tests pass.

---

## Phase 7: User Story 5 — Agent Skills Manifest (Priority: P3)

**Goal**: Formalize five agent skill definitions with triggers, inputs, outputs, and constraints for production transition.

**Independent Test**: Verify each skill definition is complete and maps to a working prototype function.

### Implementation for User Story 5

- [x] T040 [P] [US5] Create skills manifest in `src/skills_manifest.py` — define 5 skills as structured data (Pydantic models or dicts): Knowledge Retrieval, Sentiment Analysis, Escalation Decision, Channel Adaptation, Customer Identification; each with: name, description, triggers, inputs, outputs, constraints, mapped_function per FR-012
- [x] T041 [US5] Add skill validation in `src/skills_manifest.py` — verify each skill's mapped_function exists and signature matches declared inputs/outputs; expose `get_skills()` and `validate_skills()` functions

**Checkpoint**: Skills manifest defines 5 skills. Each maps to a prototype function. Validation passes.

---

## Phase 8: User Story 6 — Discovery Documentation and Edge Cases (Priority: P3)

**Goal**: Comprehensive documentation of discovered requirements, 30+ edge cases (10 per channel), channel patterns, refined escalation rules, and performance baseline.

**Independent Test**: Verify discovery log exists with all required sections and edge case count meets minimums.

### Implementation for User Story 6

- [x] T042 [P] [US6] Create discovery log in `specs/001-stage1-incubation/discovery-log.md` — sections: discovered requirements, channel-specific patterns (email/whatsapp/web form), refined escalation rules, 30+ edge cases (10 per channel) with handling strategies, response templates that worked well per FR-011
- [x] T043 [P] [US6] Record performance baseline in `specs/001-stage1-incubation/discovery-log.md` — measure and document: average response time, accuracy percentage on test dataset, escalation accuracy, channel formatting correctness per SC-008
- [x] T044 [US6] Create crystallization spec in `specs/001-stage1-incubation/customer-success-fte-spec.md` — document: supported channels, scope (in/out), tools exposed, performance requirements, guardrails, transition recommendations for Stage 2

**Checkpoint**: Discovery log complete with 30+ edge cases. Performance baseline recorded. Crystallization spec ready for Stage 2 handoff.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, validation, and final quality checks

- [x] T045 [P] Run full test suite `pytest tests/ -v` and fix any failures
- [x] T046 [P] Validate quickstart.md flow end-to-end per `specs/001-stage1-incubation/quickstart.md` — verify setup, CLI mode, MCP server mode, test commands all work
- [x] T047 Verify all success criteria per spec.md: SC-001 (85% accuracy), SC-002 (3 channels format correctly), SC-003 (100% escalation detection), SC-004 (50+ tickets), SC-005 (5+ MCP tools), SC-006 (multi-turn memory), SC-007 (30+ edge cases), SC-008 (<3s response)
- [x] T048 [P] Verify `.env.example` documented, no secrets in code, OpenAI key via environment only

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 Dossier (Phase 3)**: Depends on Phase 2 — No dependencies on other stories
- **US2 Core Prototype (Phase 4)**: Depends on Phase 2 + Phase 3 (needs context/ files for KB)
- **US3 Conversation Memory (Phase 5)**: Depends on Phase 4 (extends message processor)
- **US4 MCP Server (Phase 6)**: Depends on Phase 4 + Phase 5 (wraps all services)
- **US5 Skills Manifest (Phase 7)**: Depends on Phase 4 (maps to prototype functions)
- **US6 Discovery Docs (Phase 8)**: Depends on Phase 4 + Phase 5 (documents prototype findings)
- **Polish (Phase 9)**: Depends on all desired phases complete

### User Story Dependencies

```
Phase 1 (Setup)
  └─→ Phase 2 (Foundational Models)
       └─→ Phase 3 (US1: Dossier) ──────────────────────────┐
            └─→ Phase 4 (US2: Core Prototype) ──────────────┤
                 ├─→ Phase 5 (US3: Memory) ────────────────┤
                 │    └─→ Phase 6 (US4: MCP Server) ───────┤
                 ├─→ Phase 7 (US5: Skills Manifest) ───────┤
                 └─→ Phase 8 (US6: Discovery Docs) ────────┤
                                                            └─→ Phase 9 (Polish)
```

### Within Each User Story

1. Tests written FIRST, verified to FAIL
2. Models/data before services
3. Services before integration
4. Core implementation before CLI/server wiring
5. Story complete and tested before moving to next priority

### Parallel Opportunities

**Phase 1**: T003, T004 can run in parallel
**Phase 2**: T005–T011 can ALL run in parallel (separate files); T013 after T012
**Phase 3**: T015–T018 can ALL run in parallel; T019 (sample-tickets) is sequential (complex content)
**Phase 4**: T020–T023 tests in parallel; T024–T026 services in parallel; T027–T028 sequential
**Phase 5**: T029–T031 tests in parallel; T032–T034 services in parallel; T035–T036 sequential
**Phase 6**: T037 test first; T038–T039 sequential
**Phase 9**: T045, T046, T048 in parallel

---

## Parallel Example: Phase 4 (User Story 2)

```bash
# Launch all tests in parallel:
Task: "Write KB search tests in tests/test_knowledge_base.py"            # T020
Task: "Write channel formatter tests in tests/test_channel_formatter.py"  # T021
Task: "Write escalation engine tests in tests/test_escalation_engine.py"  # T022
Task: "Write message processor tests in tests/test_message_processor.py"  # T023

# Launch independent services in parallel:
Task: "Implement KB service in src/services/knowledge_base.py"           # T024
Task: "Implement channel formatter in src/services/channel_formatter.py" # T025
Task: "Implement escalation engine in src/services/escalation_engine.py" # T026

# Then sequential integration:
Task: "Implement message processor in src/services/message_processor.py" # T027 (depends on T024-T026)
Task: "Create CLI entry point in src/main.py"                            # T028 (depends on T027)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational models
3. Complete Phase 3: US1 — Development Dossier
4. Complete Phase 4: US2 — Core Interaction Prototype
5. **STOP and VALIDATE**: Test core loop with 20+ messages
6. Demo: Agent answers product questions with correct channel formatting

### Incremental Delivery

1. Setup + Foundational → Models ready
2. US1 (Dossier) → Context files created → Validate 50+ tickets
3. US2 (Core Prototype) → End-to-end interaction loop → **MVP Demo!**
4. US3 (Memory) → Multi-turn + sentiment → Demo conversational context
5. US4 (MCP Server) → Formal tool exposure → Demo MCP client integration
6. US5 (Skills Manifest) → Formalized skill definitions
7. US6 (Discovery) → Comprehensive documentation → **Stage 1 Complete**

### Suggested MVP Scope

**US1 + US2** (Phases 1–4, tasks T001–T028): 28 tasks delivering a working prototype that processes customer messages with channel formatting and escalation detection.

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tasks** | 48 |
| **Phase 1 (Setup)** | 4 tasks |
| **Phase 2 (Foundational)** | 9 tasks |
| **Phase 3 (US1 Dossier)** | 6 tasks |
| **Phase 4 (US2 Core)** | 9 tasks |
| **Phase 5 (US3 Memory)** | 8 tasks |
| **Phase 6 (US4 MCP)** | 3 tasks |
| **Phase 7 (US5 Skills)** | 2 tasks |
| **Phase 8 (US6 Discovery)** | 3 tasks |
| **Phase 9 (Polish)** | 4 tasks |
| **Parallel opportunities** | 30 tasks marked [P] |
| **MVP scope** | T001–T028 (28 tasks) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to user story for traceability
- Each user story is independently testable at its checkpoint
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Constitution Principle VI (Test-First): write tests before implementation within each story
