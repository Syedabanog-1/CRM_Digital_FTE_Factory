# CRM Digital FTE Factory - System Architecture

## High-Level Architecture

```
                        ┌─────────────────────────────────────────────────┐
                        │              CHANNEL INTAKE                      │
                        │                                                  │
    ┌──────────┐        │  ┌──────────────┐  ┌───────────────┐            │
    │  Gmail   │──Pub/Sub──│ Gmail Handler │  │ WhatsApp      │            │
    │  (Email) │        │  │ /webhooks/    │  │ Handler       │            │
    └──────────┘        │  │ gmail        │  │ /webhooks/    │            │
                        │  └──────┬───────┘  │ whatsapp      │            │
    ┌──────────┐        │         │          └───────┬───────┘            │
    │ WhatsApp │─Twilio──         │                  │                    │
    │ (Twilio) │        │         │                  │                    │
    └──────────┘        │         ▼                  ▼                    │
                        │  ┌──────────────────────────────┐               │
    ┌──────────┐        │  │       FastAPI (port 8000)     │               │
    │ Web Form │─HTTP────  │                               │               │
    │ (React)  │        │  │  /health    /support/submit   │               │
    └──────────┘        │  │  /metrics   /support/status   │               │
                        │  │  /customers /conversations    │               │
                        │  │  /metrics/channels            │               │
                        │  └──────────────┬────────────────┘               │
                        └─────────────────┼────────────────────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────────────────────┐
                        │            APACHE KAFKA (port 9092)             │
                        │                                                  │
                        │  Topics:                                         │
                        │  ├── fte.tickets.incoming    (new messages)      │
                        │  ├── fte.tickets.email       (email channel)     │
                        │  ├── fte.tickets.whatsapp    (whatsapp channel)  │
                        │  ├── fte.tickets.web         (web form channel)  │
                        │  ├── fte.agent.responses     (agent replies)     │
                        │  ├── fte.escalations         (escalated tickets) │
                        │  ├── fte.metrics             (performance data)  │
                        │  ├── fte.notifications       (status updates)    │
                        │  └── fte.dlq                 (dead letter queue) │
                        └─────────────────┬───────────────────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────────────────────┐
                        │            MESSAGE PROCESSOR (Worker)            │
                        │                                                  │
                        │  1. Consume from fte.tickets.incoming            │
                        │  2. Resolve customer (cross-channel)             │
                        │  3. Create/reuse conversation (24h window)       │
                        │  4. Create ticket                                │
                        │  5. Run OpenAI Agent:                            │
                        │     ├── search_knowledge_base                    │
                        │     ├── get_customer_history                     │
                        │     ├── analyze_sentiment                        │
                        │     ├── create_ticket                            │
                        │     ├── escalate_to_human                        │
                        │     └── send_response                            │
                        │  6. Format response for channel                  │
                        │  7. Publish to fte.agent.responses               │
                        │  8. Record metrics                               │
                        └─────────────────┬───────────────────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────────────────────┐
                        │       POSTGRESQL 16 + pgvector (port 5432)      │
                        │                                                  │
                        │  Tables:                                         │
                        │  ├── customers              (unified profiles)   │
                        │  ├── customer_identifiers   (cross-channel IDs)  │
                        │  ├── conversations           (thread tracking)   │
                        │  ├── messages               (all messages)       │
                        │  ├── tickets                (lifecycle mgmt)     │
                        │  ├── knowledge_base         (vector search)      │
                        │  ├── channel_configs        (per-channel rules)  │
                        │  └── agent_metrics          (performance data)   │
                        └─────────────────────────────────────────────────┘

                        ┌─────────────────────────────────────────────────┐
                        │              MONITORING STACK                     │
                        │                                                  │
                        │  Prometheus (port 9090) ──scrape──> /metrics     │
                        │       │                                          │
                        │       ▼                                          │
                        │  Grafana (port 3001) ──dashboard──> Panels       │
                        │                                                  │
                        │  Alerting Rules:                                 │
                        │  ├── HighLatency (p95 > 3s)                     │
                        │  ├── HighErrorRate (> 1%)                       │
                        │  ├── KafkaLagHigh (> 1000)                      │
                        │  └── ServiceDown (health fail)                  │
                        └─────────────────────────────────────────────────┘
```

## Kubernetes Deployment

```
Namespace: fte-crm
├── Deployment: fte-api (3 replicas, HPA 3-10)
│   ├── Container: fte-crm-api
│   ├── Port: 8000
│   └── Resources: 250m CPU, 256Mi Memory
├── Deployment: fte-worker (3 replicas, HPA 3-10)
│   ├── Container: fte-crm-worker
│   └── Resources: 250m CPU, 256Mi Memory
├── Service: fte-api (ClusterIP, port 80 -> 8000)
├── Ingress: fte-ingress (TLS, host: support.techcorp.com)
├── ConfigMap: fte-config (env vars)
├── Secret: fte-secrets (API keys, DB password)
├── HPA: fte-api-hpa (target: 70% CPU)
└── HPA: fte-worker-hpa (target: 70% CPU)
```

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| API Framework | FastAPI | Latest |
| Agent SDK | OpenAI Agents SDK | Latest |
| LLM Model | gpt-4o | Latest |
| Database | PostgreSQL + pgvector | 16+ |
| Streaming | Apache Kafka (aiokafka) | Latest |
| Orchestration | Kubernetes | 1.28+ |
| Web Form | React + Tailwind | Latest |
| Email | Gmail API + Pub/Sub | v1 |
| WhatsApp | Twilio WhatsApp API | Latest |
| Monitoring | Prometheus + Grafana | Latest |
| CI/CD | GitHub Actions | Latest |
| Testing | pytest + locust | Latest |
