# Data Model: Stage 1 Incubation

**Feature**: 001-stage1-incubation
**Date**: 2026-02-07

## Entities

### Channel (Enum)

Represents the communication channel.

| Value | Description |
|-------|-------------|
| `email` | Gmail email channel |
| `whatsapp` | WhatsApp via Twilio |
| `web_form` | Web support form |

### Customer

Represents a person contacting support, unified across channels.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique identifier |
| email | string | Yes | Primary identifier (unique) |
| phone | string | No | Secondary identifier (WhatsApp) |
| name | string | No | Customer display name |
| created_at | datetime | Yes | First contact timestamp |
| metadata | dict | No | Additional customer data |

**Validation**:
- Email must be valid format
- Phone must include country code if provided

**Relationships**: Has many Conversations, has many Tickets

### Conversation

Represents a thread of messages between customer and agent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique identifier |
| customer_id | string | Yes | References Customer.id |
| initial_channel | Channel | Yes | Channel where conversation started |
| started_at | datetime | Yes | Conversation start time |
| ended_at | datetime | No | Conversation end time |
| status | string | Yes | active, resolved, escalated |
| sentiment_score | float | No | 0.0 (negative) to 1.0 (positive) |
| resolution_type | string | No | resolved, escalated, abandoned |
| topics | list[string] | No | Topics discussed |
| metadata | dict | No | Additional conversation data |

**State transitions**:
- active → resolved (agent resolves issue)
- active → escalated (escalation triggered)
- active → abandoned (no response after timeout)

**Relationships**: Belongs to Customer, has many Messages

### Message

Represents a single communication unit.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique identifier |
| conversation_id | string | Yes | References Conversation.id |
| channel | Channel | Yes | Channel this message was sent on |
| direction | string | Yes | inbound (customer) or outbound (agent) |
| role | string | Yes | customer, agent, or system |
| content | string | Yes | Message text content |
| created_at | datetime | Yes | Message timestamp |
| tokens_used | int | No | LLM tokens consumed |
| latency_ms | int | No | Processing time in milliseconds |

**Validation**:
- Content must not be empty (edge case: handle gracefully)
- Direction must be inbound or outbound

**Relationships**: Belongs to Conversation

### Ticket

Represents a logged support interaction.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique identifier |
| conversation_id | string | No | References Conversation.id |
| customer_id | string | Yes | References Customer.id |
| source_channel | Channel | Yes | Channel where ticket originated |
| category | string | No | general, technical, billing, feedback, bug_report |
| priority | string | Yes | low, medium, high |
| status | string | Yes | open, in_progress, escalated, resolved, closed |
| created_at | datetime | Yes | Ticket creation time |
| resolved_at | datetime | No | Resolution timestamp |
| resolution_notes | string | No | How the issue was resolved |
| escalation_reason | string | No | Why escalated (if applicable) |

**State transitions**:
- open → in_progress (agent starts working)
- in_progress → resolved (issue fixed)
- in_progress → escalated (needs human)
- resolved → closed (confirmed by customer or timeout)

**Relationships**: Belongs to Customer, belongs to Conversation

### KnowledgeBaseEntry

Represents a product documentation article.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique identifier |
| title | string | Yes | Article title |
| content | string | Yes | Full article text |
| category | string | No | Product area category |
| keywords | list[string] | No | Search keywords |
| created_at | datetime | Yes | Creation timestamp |

**Relationships**: Standalone (queried by search service)

### CustomerIdentifier

Maps alternative identifiers to a primary customer.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| identifier_type | string | Yes | email, phone, whatsapp |
| identifier_value | string | Yes | The actual identifier value |
| customer_id | string | Yes | References Customer.id |
| verified | bool | Yes | Whether identity is confirmed |

**Validation**:
- (identifier_type, identifier_value) must be unique

**Relationships**: Belongs to Customer
