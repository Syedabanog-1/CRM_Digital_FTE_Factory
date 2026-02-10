# Quickstart Guide: Stage 2 Specialization

**Feature**: 002-stage2-specialization | **Date**: 2026-02-09

## Prerequisites

- Python 3.11+
- Node.js 18+ (for web form)
- Docker & Docker Compose
- PostgreSQL 16+ with pgvector (or use Docker)
- Apache Kafka (or use Docker)
- OpenAI API key (gpt-4o access)
- Gmail API credentials (for email channel)
- Twilio account with WhatsApp Sandbox (for WhatsApp channel)

## Quick Start (Docker Compose - Recommended)

### 1. Clone and setup environment

```bash
cd CRM_Digital_FTE_Factory
git checkout 002-stage2-specialization

# Copy environment template
cp production/.env.example production/.env

# Fill in required values:
# OPENAI_API_KEY=sk-...
# TWILIO_ACCOUNT_SID=AC...
# TWILIO_AUTH_TOKEN=...
# GMAIL_CREDENTIALS_JSON=...
# DATABASE_URL=postgresql://fte:fte_password@postgres:5432/fte_crm
# KAFKA_BROKERS=kafka:9092
```

### 2. Start all services

```bash
cd production
docker-compose up -d
```

This starts: API (port 8000), Worker, PostgreSQL (port 5432), Kafka (port 9092), Zookeeper (port 2181)

### 3. Initialize database

```bash
# Apply schema
docker-compose exec api python -m database.seed

# This creates all 8 tables and loads knowledge base with embeddings
```

### 4. Verify health

```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

### 5. Test web form submission

```bash
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test submission",
    "category": "General Inquiry",
    "message": "This is a test message to verify the system works end to end."
  }'
# Should return: {"ticket_id": "...", "status": "open", ...}
```

## Local Development (Without Docker)

### 1. Install Python dependencies

```bash
cd production
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Start PostgreSQL and Kafka

```bash
# PostgreSQL with pgvector
docker run -d --name fte-postgres \
  -e POSTGRES_DB=fte_crm \
  -e POSTGRES_USER=fte \
  -e POSTGRES_PASSWORD=fte_password \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Kafka + Zookeeper
docker run -d --name fte-zookeeper -p 2181:2181 confluentinc/cp-zookeeper:7.5.0
docker run -d --name fte-kafka -p 9092:9092 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:7.5.0
```

### 3. Set environment variables

```bash
export DATABASE_URL=postgresql://fte:fte_password@localhost:5432/fte_crm
export KAFKA_BROKERS=localhost:9092
export OPENAI_API_KEY=sk-your-key-here
```

### 4. Run the API

```bash
cd production
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Run the Worker (separate terminal)

```bash
cd production
python -m workers.message_processor
```

## Web Form Development

```bash
cd web-form
npm install
npm start
# Opens at http://localhost:3000
```

## Running Tests

```bash
cd production

# Unit tests
pytest tests/test_agent.py -v
pytest tests/test_database.py -v
pytest tests/test_channels.py -v

# Transition tests (Stage 1 → Stage 2 verification)
pytest tests/test_transition.py -v

# E2E tests (requires running services)
pytest tests/test_e2e.py -v

# Load tests
locust -f tests/load_test.py --host=http://localhost:8000
```

## Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/kafka/
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Verify
kubectl get pods -n fte-production
```

## Key Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key with gpt-4o access | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `KAFKA_BROKERS` | Kafka broker addresses | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | For WhatsApp |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For WhatsApp |
| `GMAIL_CREDENTIALS_JSON` | Gmail API credentials path | For Email |
| `GMAIL_PUBSUB_TOPIC` | Pub/Sub topic name | For Email |
| `LOG_LEVEL` | Logging level (INFO/DEBUG) | No (default: INFO) |
| `CORS_ORIGINS` | Allowed CORS origins | No (default: localhost) |
