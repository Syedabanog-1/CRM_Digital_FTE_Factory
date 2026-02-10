# Agent Tool Contracts: Stage 2 Specialization

**Feature**: 002-stage2-specialization | **Date**: 2026-02-09
**Phase**: 1 (Design) | **Status**: Complete

## Overview

6 tools exposed to the OpenAI Agents SDK Agent via `@function_tool` decorator. Each tool has a Pydantic input model, a detailed docstring (consumed by the LLM), and try/catch error handling.

These tools are the production equivalents of the Stage 1 MCP tools:

| Stage 1 (MCP) | Stage 2 (Agents SDK) | Changes |
|----------------|----------------------|---------|
| `search_knowledge_base` | `search_knowledge_base` | pgvector semantic search replaces difflib |
| `create_ticket` | `create_ticket` | PostgreSQL persistence, UUID ticket IDs |
| `get_customer_history` | `get_customer_history` | Cross-channel unified history from DB |
| `escalate_to_human` | `escalate_to_human` | Kafka escalation event, DB status update |
| `send_response` | `send_response` | Channel-specific formatting, outbound Kafka |
| `analyze_sentiment` | `analyze_sentiment` | Same logic, DB metric recording |

## Tool Contracts

### 1. search_knowledge_base

Search the product knowledge base using semantic similarity.

**Input Schema**:
```python
class SearchKBInput(BaseModel):
    query: str  # The search query from the customer
    max_results: int = 3  # Maximum number of results to return (1-10)
```

**Output** (JSON string):
```json
{
  "results": [
    {
      "title": "Getting Started with CloudSync Pro",
      "content": "CloudSync Pro is our flagship...",
      "category": "product",
      "similarity_score": 0.89
    }
  ],
  "total_found": 1
}
```

**Error output**:
```json
{
  "error": "Knowledge base search failed: connection timeout",
  "results": [],
  "total_found": 0
}
```

**Behavior**:
- Generates embedding for query using text-embedding-3-small
- Performs pgvector cosine similarity search
- Returns top N results with similarity scores
- If no results found (or similarity < 0.5), returns empty results
- Agent should escalate after 2 failed searches per constitution

---

### 2. create_ticket

Create a support ticket for the current customer interaction.

**Input Schema**:
```python
class CreateTicketInput(BaseModel):
    subject: str  # Brief description of the issue
    category: str  # One of: Technical Support, Billing, Feature Request, Bug Report, General Inquiry
    priority: str = "medium"  # One of: low, medium, high, urgent
    customer_email: str  # Customer's email address
    channel: str  # Source channel: email, whatsapp, web
```

**Output** (JSON string):
```json
{
  "ticket_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "status": "open",
  "created_at": "2026-02-09T12:00:00Z"
}
```

**Error output**:
```json
{
  "error": "Failed to create ticket: database connection error"
}
```

**Behavior**:
- MUST be called before send_response (constitution guardrail)
- Creates ticket in PostgreSQL with UUID
- Links to existing customer and active conversation
- Records channel source for metrics

---

### 3. get_customer_history

Get unified customer history across all channels.

**Input Schema**:
```python
class GetHistoryInput(BaseModel):
    customer_email: str  # Customer's email address
    max_conversations: int = 5  # Maximum conversations to return
```

**Output** (JSON string):
```json
{
  "customer": {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "channels_used": ["email", "whatsapp", "web"]
  },
  "conversations": [
    {
      "id": "conv-uuid",
      "channel": "web",
      "status": "resolved",
      "subject": "Dashboard access issue",
      "message_count": 4,
      "created_at": "2026-02-08T10:00:00Z",
      "last_message": "Thank you, that resolved my issue!"
    }
  ],
  "total_tickets": 3,
  "total_conversations": 5
}
```

**Error output**:
```json
{
  "error": "Customer lookup failed",
  "customer": null,
  "conversations": []
}
```

**Behavior**:
- Resolves customer by email across all channels via customer_identifiers
- Returns unified history regardless of which channel interactions occurred on
- Sorted by most recent first

---

### 4. escalate_to_human

Escalate the current conversation to a human agent.

**Input Schema**:
```python
class EscalateInput(BaseModel):
    reason: str  # Why escalation is needed
    ticket_id: str  # The ticket ID to escalate
    urgency: str = "normal"  # normal, high, critical
```

**Output** (JSON string):
```json
{
  "escalated": true,
  "escalation_id": "esc-uuid",
  "message": "This conversation has been escalated to our support team. Reference: ESC-123"
}
```

**Error output**:
```json
{
  "error": "Escalation failed: Kafka unavailable",
  "escalated": false
}
```

**Behavior**:
- Updates ticket status to "escalated" in database
- Updates conversation status to "escalated"
- Publishes escalation event to `fte.escalations` Kafka topic
- Records escalation metric in agent_metrics
- Non-negotiable triggers per constitution: legal, profanity, pricing, failed KB (2+), human request

---

### 5. send_response

Send a channel-formatted response to the customer.

**Input Schema**:
```python
class SendResponseInput(BaseModel):
    message: str  # The response message content
    channel: str  # Target channel: email, whatsapp, web
    ticket_id: str  # Associated ticket ID
```

**Output** (JSON string):
```json
{
  "sent": true,
  "channel": "email",
  "formatted_length": 245,
  "message_id": "msg-uuid"
}
```

**Error output**:
```json
{
  "error": "Failed to send response: channel handler unavailable",
  "sent": false
}
```

**Behavior**:
- MUST be called after create_ticket (constitution guardrail)
- Applies channel-specific formatting:
  - **Email**: Formal greeting, body, signature, ticket reference. Max 500 words.
  - **WhatsApp**: Concise, conversational. Max 300 chars preferred, 1600 absolute. Split if needed.
  - **Web**: Semi-formal, balanced detail. Max 300 words.
- Stores outbound message in database
- Publishes to channel-specific outbound Kafka topic (`fte.channels.{channel}.outbound`)
- Records response time metric

---

### 6. analyze_sentiment

Analyze the sentiment of a customer message.

**Input Schema**:
```python
class SentimentInput(BaseModel):
    text: str  # The text to analyze for sentiment
```

**Output** (JSON string):
```json
{
  "score": 0.35,
  "label": "negative",
  "confidence": 0.82
}
```

**Error output**:
```json
{
  "error": "Sentiment analysis failed",
  "score": 0.5,
  "label": "neutral"
}
```

**Behavior**:
- Returns score 0.0 (very negative) to 1.0 (very positive)
- Labels: very_negative (<0.2), negative (<0.4), neutral (<0.6), positive (<0.8), very_positive (>=0.8)
- If sentiment < 0.3, agent MUST escalate (constitution rule)
- Records sentiment metric in agent_metrics
- Sentiment MUST be checked before closing conversation (constitution guardrail)

## Tool Execution Order

Per constitution, the agent's tool execution workflow is:

```
1. create_ticket       (ALWAYS first - guardrail)
2. get_customer_history (context gathering)
3. search_knowledge_base (answer finding)
4. analyze_sentiment   (customer state check)
5. [escalate_to_human] (if triggers detected)
6. send_response       (ALWAYS last - guardrail)
```

## Agent Definition

```python
from agents import Agent

customer_success_agent = Agent(
    name="TechCorp Customer Success Agent",
    model="gpt-4o",
    instructions=SYSTEM_PROMPT,  # from prompts.py
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
        analyze_sentiment,
    ],
)
```
