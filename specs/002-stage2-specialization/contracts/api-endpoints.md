# API Endpoint Contracts: Stage 2 Specialization

**Feature**: 002-stage2-specialization | **Date**: 2026-02-09
**Phase**: 1 (Design) | **Status**: Complete

## Base URL

- **Local**: `http://localhost:8000`
- **Production**: `https://fte.techcorp.com` (via K8s Ingress)

## Endpoints

### 1. GET /health

Health check for liveness and readiness probes.

**Request**: No parameters

**Response 200**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-09T12:00:00Z",
  "channels": {
    "email": "connected",
    "whatsapp": "connected",
    "web": "active"
  },
  "database": "connected",
  "kafka": "connected"
}
```

**Response 503** (unhealthy):
```json
{
  "status": "unhealthy",
  "timestamp": "2026-02-09T12:00:00Z",
  "channels": {
    "email": "disconnected",
    "whatsapp": "connected",
    "web": "active"
  },
  "database": "connected",
  "kafka": "disconnected"
}
```

---

### 2. POST /webhooks/gmail

Gmail Pub/Sub push notification endpoint. Receives base64-encoded notification when a new email arrives.

**Request Headers**:
- `Content-Type: application/json`

**Request Body**:
```json
{
  "message": {
    "data": "<base64-encoded-notification>",
    "messageId": "1234567890",
    "publishTime": "2026-02-09T12:00:00Z"
  },
  "subscription": "projects/myproject/subscriptions/gmail-push"
}
```

**Response 200**:
```json
{
  "status": "accepted",
  "message_id": "gmail_msg_abc123"
}
```

**Response 400** (invalid notification):
```json
{
  "detail": "Invalid Pub/Sub notification format"
}
```

**Side effects**: Publishes normalized message to `fte.channels.email.inbound` and `fte.tickets.incoming` Kafka topics.

---

### 3. POST /webhooks/whatsapp

Twilio WhatsApp webhook. Receives incoming messages with signature validation.

**Request Headers**:
- `Content-Type: application/x-www-form-urlencoded`
- `X-Twilio-Signature: <hmac-sha1-signature>`

**Request Body** (form data):
```
Body=Hello%20I%20need%20help
From=whatsapp%3A%2B1234567890
ProfileName=John%20Doe
WaId=1234567890
NumMedia=0
```

**Response 200**:
```json
{
  "status": "accepted",
  "message_id": "wa_msg_abc123"
}
```

**Response 403** (invalid signature):
```json
{
  "detail": "Invalid Twilio signature"
}
```

**Response 400** (empty body):
```json
{
  "detail": "Empty message body"
}
```

**Side effects**: Publishes normalized message to `fte.channels.whatsapp.inbound` and `fte.tickets.incoming` Kafka topics.

---

### 4. POST /support/submit

Web support form submission endpoint.

**Request Headers**:
- `Content-Type: application/json`

**Request Body**:
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "subject": "Cannot access dashboard",
  "category": "Technical Support",
  "priority": "high",
  "message": "I've been unable to access my dashboard since yesterday. The page shows a 500 error when I try to log in."
}
```

**Validation Rules**:
- `name`: Required, min 2 characters
- `email`: Required, valid email format
- `subject`: Required, min 5 characters
- `category`: Required, one of ["Technical Support", "Billing", "Feature Request", "Bug Report", "General Inquiry"]
- `priority`: Optional, one of ["low", "medium", "high", "urgent"], default "medium"
- `message`: Required, min 10 characters

**Response 201**:
```json
{
  "ticket_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "status": "open",
  "message": "Your support request has been received. Our AI assistant will respond within minutes.",
  "estimated_response_time": "< 5 minutes"
}
```

**Response 422** (validation error):
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Invalid email format",
      "type": "value_error"
    },
    {
      "loc": ["body", "message"],
      "msg": "Message must be at least 10 characters",
      "type": "value_error"
    }
  ]
}
```

**Side effects**: Creates customer (if new), creates ticket, publishes to `fte.channels.webform.inbound` and `fte.tickets.incoming`.

---

### 5. GET /support/ticket/{ticket_id}

Check ticket status and view agent response.

**Request Parameters**:
- `ticket_id` (path): UUID of the ticket

**Response 200**:
```json
{
  "ticket_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "status": "resolved",
  "subject": "Cannot access dashboard",
  "category": "Technical Support",
  "priority": "high",
  "created_at": "2026-02-09T12:00:00Z",
  "updated_at": "2026-02-09T12:02:30Z",
  "messages": [
    {
      "role": "customer",
      "content": "I've been unable to access my dashboard...",
      "timestamp": "2026-02-09T12:00:00Z"
    },
    {
      "role": "agent",
      "content": "Thank you for reaching out. I've looked into the dashboard issue...",
      "timestamp": "2026-02-09T12:02:30Z"
    }
  ]
}
```

**Response 404**:
```json
{
  "detail": "Ticket not found"
}
```

---

### 6. GET /customers/lookup

Look up a customer's unified profile across channels.

**Query Parameters**:
- `email` (optional): Customer email
- `phone` (optional): Customer phone number

At least one parameter required.

**Response 200**:
```json
{
  "customer_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1234567890",
  "identifiers": [
    {"type": "email", "value": "jane@example.com", "verified": true},
    {"type": "whatsapp", "value": "+1234567890", "verified": true}
  ],
  "total_conversations": 5,
  "total_tickets": 3,
  "channels_used": ["email", "whatsapp", "web"],
  "created_at": "2026-01-15T10:00:00Z"
}
```

**Response 404**:
```json
{
  "detail": "Customer not found"
}
```

**Response 400** (no parameters):
```json
{
  "detail": "At least one of email or phone is required"
}
```

---

### 7. GET /conversations/{conversation_id}

Get full conversation history with all messages.

**Request Parameters**:
- `conversation_id` (path): UUID of the conversation

**Response 200**:
```json
{
  "conversation_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
  "customer": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Jane Doe",
    "email": "jane@example.com"
  },
  "channel": "web",
  "status": "active",
  "sentiment_score": 0.7,
  "messages": [
    {
      "id": "msg-uuid-1",
      "role": "customer",
      "content": "I need help with...",
      "channel": "web",
      "direction": "inbound",
      "created_at": "2026-02-09T12:00:00Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "agent",
      "content": "Thank you for contacting...",
      "channel": "web",
      "direction": "outbound",
      "processing_time_ms": 1850,
      "created_at": "2026-02-09T12:00:02Z"
    }
  ],
  "created_at": "2026-02-09T12:00:00Z",
  "updated_at": "2026-02-09T12:00:02Z"
}
```

**Response 404**:
```json
{
  "detail": "Conversation not found"
}
```

---

### 8. GET /metrics/channels

Get per-channel performance metrics for the past 24 hours.

**Query Parameters**:
- `hours` (optional): Lookback period in hours, default 24
- `channel` (optional): Filter by specific channel

**Response 200**:
```json
{
  "period_hours": 24,
  "generated_at": "2026-02-09T12:00:00Z",
  "channels": {
    "email": {
      "total_conversations": 52,
      "average_response_time_ms": 2100,
      "p95_response_time_ms": 2800,
      "average_sentiment": 0.72,
      "escalation_count": 4,
      "escalation_rate": 0.077,
      "resolution_rate": 0.92
    },
    "whatsapp": {
      "total_conversations": 48,
      "average_response_time_ms": 1800,
      "p95_response_time_ms": 2500,
      "average_sentiment": 0.68,
      "escalation_count": 6,
      "escalation_rate": 0.125,
      "resolution_rate": 0.88
    },
    "web": {
      "total_conversations": 105,
      "average_response_time_ms": 1950,
      "p95_response_time_ms": 2700,
      "average_sentiment": 0.75,
      "escalation_count": 8,
      "escalation_rate": 0.076,
      "resolution_rate": 0.94
    }
  },
  "totals": {
    "total_conversations": 205,
    "average_response_time_ms": 1950,
    "average_sentiment": 0.72,
    "total_escalations": 18,
    "overall_escalation_rate": 0.088
  }
}
```

## Error Responses

All endpoints follow standard HTTP error codes:

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET/POST |
| 201 | Created | New resource created (ticket) |
| 400 | Bad Request | Invalid input format |
| 403 | Forbidden | Invalid webhook signature |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation failure |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Health check failure |

## Authentication

- **Gmail webhook**: Pub/Sub subscription validation (origin verification)
- **WhatsApp webhook**: Twilio `X-Twilio-Signature` HMAC-SHA1 validation
- **Web form**: No auth required (public-facing)
- **Internal endpoints** (customer lookup, metrics): API key header (optional, configurable)
