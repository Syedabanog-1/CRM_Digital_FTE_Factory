# Crystallization Spec: Customer Success Digital FTE

**Feature**: 001-stage1-incubation
**Date**: 2026-02-08
**Status**: Stage 1 Complete — Ready for Stage 2 Handoff

## Overview

This document crystallizes the findings, capabilities, constraints, and
recommendations from the Stage 1 Incubation phase. It serves as the primary
handoff document for Stage 2 (Specialization), where the prototype becomes
a production-grade Custom Agent built with the OpenAI Agents SDK.

## Supported Channels

| Channel | Tone | Max Length | Greeting | Signature | Status |
|---------|------|-----------|----------|-----------|--------|
| Email (Gmail) | Formal | 500 words | Yes | Yes | Validated |
| WhatsApp (Twilio) | Conversational | 300 chars preferred, 1600 absolute | No | No | Validated |
| Web Form (Next.js) | Semi-formal | 300 words | Brief | No | Validated |

All three channels share a unified message processing pipeline. Channel-specific
formatting is applied at the output layer via `channel_formatter.py`.

## Scope

### In Scope (Delivered in Stage 1)

- Multi-channel message processing with unified pipeline
- Product documentation search via fuzzy text matching (difflib)
- Channel-aware response formatting with enforced length limits
- Escalation detection: pricing, refunds, legal threats, profanity, explicit
  human requests, failed KB search (2+ attempts), low sentiment (<0.3)
- Keyword-based sentiment analysis (0.0-1.0 scale)
- Cross-channel customer identification (email primary, phone secondary)
- In-memory conversation state with multi-turn context
- MCP server exposing 6 tools via stdio transport
- Agent skills manifest with 5 formalized skill definitions
- Development dossier with 55 sample tickets across all channels
- 33 documented edge cases (11 per channel) with handling strategies
- CLI interface for interactive testing

### Out of Scope (Deferred to Stage 2)

- Persistent storage (PostgreSQL + pgvector)
- Real channel integrations (Gmail API, Twilio WhatsApp API, Next.js web form)
- Apache Kafka event streaming
- Kubernetes deployment
- Production error handling (structured logging, correlation IDs)
- ML-based sentiment analysis
- Vector-based semantic search
- Multi-language support
- Media attachment handling (images, documents, voice)
- Load testing and 24/7 operational readiness

## Tools Exposed (MCP Server)

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| search_knowledge_base | Search product docs | query, max_results | Formatted results or "no results" |
| create_ticket | Log a support interaction | customer_id, issue, priority, channel | Ticket ID |
| get_customer_history | Cross-channel history | customer_id | Formatted history |
| escalate_to_human | Hand off to human | ticket_id, reason | Confirmation |
| send_response | Channel-formatted delivery | ticket_id, message, channel | Delivery status |
| analyze_sentiment | Score customer sentiment | message | Score (0.0-1.0) with label |

## Performance Requirements

| Metric | Target | Stage 1 Measured | Stage 2 Target |
|--------|--------|-----------------|----------------|
| Response time (processing) | <3s | ~0.05s (no LLM), ~0.5s (fallback) | <3s with LLM |
| Response time (delivery) | <30s | N/A (no real channels) | <30s |
| KB search accuracy | >85% | ~90% on sample queries | >85% with pgvector |
| Escalation detection | 100% for defined triggers | 100% | 100% |
| Overall accuracy | >85% | ~90% | >85% |
| Escalation rate | <20% | ~18% of sample tickets | <20% |

## Guardrails (Non-Negotiable)

These guardrails are defined in the constitution and MUST be carried into Stage 2:

1. **NEVER** discuss competitor products (Asana, Jira, Monday.com, Trello, ClickUp)
2. **NEVER** promise features not in documentation
3. **ALWAYS** create a ticket before responding
4. **ALWAYS** check sentiment before closing a conversation
5. **ALWAYS** format responses for the target channel
6. **ALWAYS** escalate for: legal threats, pricing/refunds, profanity, explicit
   human requests, failed KB search after 2 attempts

## Escalation Rules (Validated)

| Trigger | Detection Method | Priority |
|---------|-----------------|----------|
| Legal terms (lawyer, sue, attorney) | Keyword match | Highest |
| Technical emergency (data loss, hacked) | Keyword match | High |
| Explicit human request (speak to human, manager) | Phrase match | High |
| Pricing/billing/refund | Keyword match | Medium |
| Profanity/aggressive language | Keyword match + sentiment <0.3 | Medium |
| Failed KB search (2+ attempts) | Counter tracking | Low |

## Data Model Summary

| Entity | Key Fields | Stage 2 Migration |
|--------|-----------|-------------------|
| Customer | id (UUID), email (unique), phone, name | → PostgreSQL `customers` table |
| CustomerIdentifier | type, value, customer_id, verified | → PostgreSQL `customer_identifiers` table |
| Conversation | id, customer_id, channel, status, sentiment | → PostgreSQL `conversations` table |
| Message | id, conversation_id, channel, direction, role, content | → PostgreSQL `messages` table |
| Ticket | id, customer_id, channel, category, priority, status | → PostgreSQL `tickets` table |
| KnowledgeBaseEntry | id, title, content, category, keywords | → PostgreSQL `knowledge_base` table with pgvector |

## Architecture Decisions for Stage 2

### 1. Replace In-Memory Store with PostgreSQL
- All dict-based stores (`conversation_store.py`) migrate to PostgreSQL tables
- Use SQLAlchemy or asyncpg for async database access
- Add pgvector extension for semantic search on `knowledge_base`

### 2. Replace Fuzzy Search with Vector Embeddings
- Current `difflib.SequenceMatcher` approach works for 50 articles but won't scale
- Use OpenAI embeddings + pgvector for semantic similarity search

### 3. Add Real Channel Integrations
- Gmail API + Pub/Sub for email inbound/outbound
- Twilio WhatsApp Sandbox for WhatsApp messaging
- Next.js/React web form component with FastAPI backend

### 4. Add Kafka Event Streaming
- Route all inbound messages through `fte.tickets.incoming`
- Escalations to `fte.escalations`
- Metrics to `fte.metrics`
- Failed messages to `fte.dlq`

### 5. Build OpenAI Agents SDK Custom Agent
- Replace prototype's direct OpenAI API calls with Agents SDK agent
- Wrap MCP tools as agent functions
- Use `gpt-4o` (production model per constitution)

### 6. Deploy on Kubernetes
- FastAPI service for API endpoints
- Kafka consumers as separate deployments
- PostgreSQL as StatefulSet or managed service
- Health checks on all components

## Known Limitations and Risks

1. **No persistent state**: All data is lost on process restart
2. **No real channel delivery**: Responses are formatted but not actually sent
3. **Keyword-based sentiment**: May miss nuanced emotional context
4. **No media support**: Images, documents, and voice messages are ignored
5. **Single-language**: Only processes English effectively
6. **No authentication**: MCP server and CLI have no access control
7. **No structured logging**: Uses print statements (acceptable for prototype)

## Test Suite Summary

- **128 tests** across 11 test files
- **100% pass rate** (128/128)
- All core components covered: models, services, memory, MCP tools
- Edge cases tested: empty inputs, invalid data, boundary conditions

## Transition Checklist for Stage 2

- [ ] Set up PostgreSQL 16+ with pgvector extension
- [ ] Migrate all in-memory stores to database tables
- [ ] Replace difflib search with vector embeddings
- [ ] Integrate Gmail API for email channel
- [ ] Integrate Twilio WhatsApp Sandbox
- [ ] Build Next.js web form component
- [ ] Set up Apache Kafka with required topics
- [ ] Build OpenAI Agents SDK custom agent
- [ ] Add structured JSON logging with correlation IDs
- [ ] Set up Kubernetes deployment manifests
- [ ] Add health check endpoints to all services
- [ ] Run transition test suite (Stage 1 tests must still pass)
- [ ] Document 10+ edge cases per channel from production testing
- [ ] Set up load testing with Locust
