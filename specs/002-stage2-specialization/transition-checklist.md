# Transition Checklist: General Agent (Stage 1) to Custom Agent (Stage 2)

**Feature Branch**: `002-stage2-specialization`
**Created**: 2026-02-10
**Predecessor**: Stage 1 Incubation (`001-stage1-incubation`) - 48/48 tasks, 128/128 tests, 8/8 success criteria PASS

## 1. Discovered Requirements

Requirements discovered during Stage 1 incubation exploration:

- [x] Multi-channel message normalization (email, WhatsApp, web form) with unified internal format
- [x] Channel-specific response formatting: email formal (greeting+signature), WhatsApp concise (<300 chars), web semi-formal
- [x] Customer identification by email (primary key) with cross-channel resolution via phone/WhatsApp
- [x] Conversation threading with 24-hour active window reuse
- [x] Escalation triggers: legal terms, profanity (sentiment < 0.3), pricing, failed KB search (2+), explicit human request
- [x] Guardrails: never discuss competitors, never promise undocumented features, always create ticket before responding
- [x] Sentiment analysis must run before closing any conversation
- [x] Knowledge base search using semantic similarity (difflib in Stage 1, pgvector in Stage 2)
- [x] Ticket lifecycle: open -> in_progress -> escalated/resolved/closed
- [x] WhatsApp messages >1600 chars must be split at sentence boundaries
- [x] Email replies must maintain thread context (threadId, Re: prefix)
- [x] Empty messages need clarification prompts, not crashes
- [x] Concurrent messages from same customer on different channels need unified handling

## 2. Working Prompts

### System Prompt That Worked (Stage 1 -> Formalized in Stage 2)

Stage 1 prototype used a simple instruction: "You are a helpful customer support agent for TechCorp SaaS."

Stage 2 formalized system prompt in `production/agent/prompts.py` includes:
- Hard constraints (never discuss competitors, never promise undocumented features)
- Escalation triggers with specific keywords and conditions
- Channel awareness rules with response length limits
- Required tool execution order: create_ticket -> get_customer_history -> search_knowledge_base -> analyze_sentiment -> [escalate] -> send_response

### Tool Descriptions That Worked

- `search_knowledge_base`: "Search product documentation for relevant information" - worked well with detailed docstring about when to use
- `create_ticket`: "Create a support ticket" - MUST be called first per constitution
- `get_customer_history`: "Get customer's interaction history across ALL channels" - key for cross-channel continuity
- `escalate_to_human`: "Escalate conversation to human support" - with explicit trigger list
- `send_response`: "Send response via the appropriate channel" - MUST be called last
- `analyze_sentiment`: "Analyze customer message sentiment" - returns score + label

## 3. Edge Cases Found

| Edge Case | How It Was Handled | Test Case in Stage 2 |
|-----------|-------------------|---------------------|
| Empty message | Return clarification prompt | test_transition.py::test_empty_message |
| Pricing inquiry | Immediate escalation, never answer | test_transition.py::test_pricing_escalation |
| Legal language ("lawyer", "sue") | Immediate escalation | test_transition.py::test_legal_escalation |
| Profanity / angry customer | Sentiment check -> escalate if < 0.3 | test_transition.py::test_profanity_escalation |
| Explicit human request | Immediate escalation | test_transition.py::test_human_request_escalation |
| WhatsApp message too long | Split at 1600-char sentence boundaries | test_channels.py::test_whatsapp_message_splitting |
| Unknown product question | Return "no relevant docs found" gracefully | test_agent.py::test_kb_no_results |
| Customer contacts via email then WhatsApp | Resolve by email primary, phone secondary | test_e2e.py::test_cross_channel_recognition |
| Simultaneous multi-channel contact | 24-hour conversation window reuse | test_database.py::test_conversation_reuse |
| Email with no subject | Default to "Support Request" | test_channels.py::test_gmail_no_subject |
| Invalid Twilio signature | Return 403 Forbidden | test_channels.py::test_whatsapp_invalid_signature |
| Database temporarily unavailable | Graceful error + apologetic response | test_e2e.py::test_db_unavailable_handling |
| Kafka broker down | Log warning, continue without streaming | kafka_client.py graceful fallback |
| OpenAI rate limit (429) | Retry with backoff, escalate if persistent | tools.py try/catch handlers |

## 4. Response Patterns

### Email
- Formal tone with "Dear [Name]," greeting
- Detailed body (up to 500 words)
- Signature with team name and ticket reference
- Thread maintained via threadId and "Re:" prefix

### WhatsApp
- Conversational, no formal greeting
- Concise (preferred 300 chars, absolute max 1600)
- Includes prompt: "Reply for more help or type 'human' for live support"
- Long messages split at sentence boundaries

### Web Form
- Semi-formal with "Hi [Name]," greeting
- Balanced detail (up to 300 words)
- Footer with support center link and ticket reference

## 5. Escalation Rules (Finalized)

Non-negotiable escalation triggers (from Constitution):

1. **Legal language**: Customer mentions "lawyer", "attorney", "lawsuit", "sue", "litigation", "legal"
2. **Profanity/aggression**: Sentiment score < 0.3 (using keyword-based scoring)
3. **Pricing/billing**: Customer asks about pricing, costs, refunds, or billing
4. **Failed KB search**: Cannot find relevant information after 2 search attempts
5. **Explicit human request**: Customer says "human", "agent", "representative", "speak to a person"

## 6. Performance Baseline (Stage 1)

From Stage 1 prototype testing:

| Metric | Stage 1 Value | Stage 2 Target |
|--------|--------------|----------------|
| Response accuracy | ~80% (difflib text match) | >85% (pgvector semantic) |
| Escalation rate | ~25% | <20% |
| Knowledge search | String matching (difflib) | Vector similarity (pgvector) |
| Storage | In-memory (lost on restart) | PostgreSQL (persistent) |
| Channels | Simulated (all via CLI) | Real (Gmail API, Twilio, Web Form) |
| Processing time | <1s (in-memory) | <3s p95 (with DB + Kafka) |

## 7. API Gotchas (From Stage 1 - Avoid Re-discovering)

- `ChannelFormatter.format()` NOT `format_response()` - method name matters
- `SentimentAnalyzer` in Stage 1 used `analyze()` returning float; Stage 2 uses `_compute_sentiment()` returning (float, str) tuple
- `KnowledgeBaseService.search()` requires `load_from_file()` first in Stage 1; Stage 2 uses DB seeding via `seed.py`
- `ConversationStore.get_customer_by_email()` in Stage 1; Stage 2 uses `queries.get_customer_by_email()`
- `validate_skills()` returned `dict[str, bool]` in Stage 1; Stage 2 skills are formalized as `@function_tool`
- Escalation phrase matching uses "speak to a human" (full phrase), not "speak to human"

## 8. MCP Tools -> OpenAI Agents SDK Mapping

| Stage 1 (MCP Server) | Stage 2 (OpenAI SDK) | Changes |
|----------------------|---------------------|---------|
| `@server.tool("search_knowledge_base")` | `@function_tool search_knowledge_base(SearchKBInput)` | Pydantic schema, pgvector search, error handling |
| `@server.tool("create_ticket")` | `@function_tool create_ticket(CreateTicketInput)` | DB persistence, customer resolution, conversation linking |
| `@server.tool("get_customer_history")` | `@function_tool get_customer_history(GetHistoryInput)` | Cross-channel via customer_identifiers, conversation history |
| `@server.tool("escalate_to_human")` | `@function_tool escalate_to_human(EscalateInput)` | DB update + Kafka event, conversation status update |
| `@server.tool("send_response")` | `@function_tool send_response(SendResponseInput)` | Channel formatting, DB storage, Kafka outbound, metrics |
| `@server.tool("analyze_sentiment")` | `@function_tool analyze_sentiment(SentimentInput)` | Same keyword algorithm, adds metric recording |

## Pre-Transition Verification

- [x] Working prototype handles basic queries (Stage 1: 128/128 tests)
- [x] Documented edge cases (14 documented, see table above)
- [x] Working system prompt (extracted and formalized in prompts.py)
- [x] MCP tools defined and tested (6 tools, all transformed to @function_tool)
- [x] Channel-specific response patterns identified (email/whatsapp/web formatting)
- [x] Escalation rules finalized (5 triggers, non-negotiable per constitution)
- [x] Performance baseline measured (see table above)

## Post-Transition Verification

- [x] Created production/ folder structure
- [x] Extracted prompts to prompts.py
- [x] Converted MCP tools to @function_tool (6 tools)
- [x] Added Pydantic input validation to all tools (6 BaseModel schemas)
- [x] Added error handling to all tools (try/catch with JSON error response)
- [x] Created transition test suite (test_transition.py)
- [x] Transition tests cover all edge cases
