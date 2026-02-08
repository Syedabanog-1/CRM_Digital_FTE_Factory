# MCP Tool Contracts: Stage 1 Incubation

**Feature**: 001-stage1-incubation
**Date**: 2026-02-07

## Tool 1: search_knowledge_base

**Purpose**: Search product documentation for relevant information.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search query text |
| max_results | int | No (default: 5) | Maximum results to return |

**Output**: String containing formatted search results with titles and content
snippets, or a "no results found" message.

**Error cases**:
- Empty query → return "Please provide a search query"
- No matches → return "No relevant documentation found. Consider escalating."

---

## Tool 2: create_ticket

**Purpose**: Create a support ticket for tracking an interaction.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| customer_id | string | Yes | Customer identifier (email) |
| issue | string | Yes | Description of the issue |
| priority | string | No (default: "medium") | low, medium, high |
| channel | Channel | Yes | email, whatsapp, web_form |

**Output**: String "Ticket created: {ticket_id}"

**Error cases**:
- Missing customer_id → error message
- Invalid channel → error message

---

## Tool 3: get_customer_history

**Purpose**: Get customer's interaction history across all channels.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| customer_id | string | Yes | Customer identifier (email) |

**Output**: String containing formatted history with channel, date, topic,
and resolution for each past interaction. Returns "No prior history found"
if customer is new.

**Error cases**:
- Unknown customer_id → return "No prior history found"

---

## Tool 4: escalate_to_human

**Purpose**: Escalate a conversation to human support.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticket_id | string | Yes | ID of the ticket to escalate |
| reason | string | Yes | Reason for escalation |

**Output**: String "Escalated to human support. Reference: {ticket_id}"

**Error cases**:
- Unknown ticket_id → error message
- Empty reason → error message

---

## Tool 5: send_response

**Purpose**: Send a response to the customer via the appropriate channel.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticket_id | string | Yes | Ticket this response belongs to |
| message | string | Yes | Response message content |
| channel | Channel | Yes | Target channel for formatting |

**Output**: String "Response sent via {channel}: {delivery_status}"

**Error cases**:
- Unknown ticket_id → error message
- Empty message → error message
- Message exceeds channel limit → truncate with "..." indicator

---

## Tool 6: analyze_sentiment

**Purpose**: Analyze the sentiment of a customer message.

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| message | string | Yes | Customer message text |

**Output**: String "Sentiment: {score} ({label})" where score is 0.0-1.0
and label is negative/neutral/positive.

**Error cases**:
- Empty message → return "Sentiment: 0.5 (neutral)"
