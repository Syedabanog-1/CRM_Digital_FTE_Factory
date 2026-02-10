# Research: Stage 3 Integration

**Feature**: 003-stage3-integration
**Date**: 2026-02-10

## Existing Test Infrastructure

### What Stage 2 Already Created
- `production/tests/test_database.py` - 31 tests covering all 8 PostgreSQL tables (requires live DB)
- `production/tests/test_e2e.py` - Full pipeline E2E tests (requires full docker-compose stack)
- `production/tests/load_test.py` - Locust load test with multi-channel traffic simulation
- `production/tests/test_agent.py` - 18 unit tests for agent tools (no infra needed)
- `production/tests/test_channels.py` - 28 unit tests for channel handlers (no infra needed)
- `production/tests/test_transition.py` - 28 unit tests for Stage 1->2 transition (no infra needed)
- `production/docker-compose.yml` - PostgreSQL, Kafka, Zookeeper, API, Worker services

### What Stage 3 Needs to Add
1. **Test orchestration script** - Automate: docker-compose up -> wait for health -> seed DB -> run tests -> report -> teardown
2. **Health check waiter** - Polling script to wait until all services are healthy
3. **Monitoring stack** - Prometheus metrics endpoint, Grafana dashboard, alerting rules
4. **CI/CD pipeline** - GitHub Actions workflow for automated testing
5. **Operational runbooks** - 5+ documented procedures
6. **Production readiness report** - Comprehensive validation summary

## Docker Compose Health Checks

The existing `production/docker-compose.yml` already defines 5 services:
- postgres (port 5432)
- zookeeper (port 2181)
- kafka (port 9092)
- api (port 8000)
- worker

Health checking approach:
- PostgreSQL: `pg_isready` command
- Kafka: wait for broker to accept connections
- API: `GET /health` returns 200
- Worker: process running check

## Monitoring Approach

### Prometheus Metrics
FastAPI has excellent Prometheus support via `prometheus-fastapi-instrumentator`. Key metrics:
- `http_requests_total` - Request count by method, path, status
- `http_request_duration_seconds` - Latency histogram
- `http_requests_in_progress` - Concurrent requests

Custom metrics to add:
- `fte_tickets_created_total` - Tickets by channel and category
- `fte_escalations_total` - Escalation count by reason
- `fte_kafka_consumer_lag` - Consumer group lag
- `fte_db_pool_size` - Connection pool utilization

### Grafana Dashboard
Panels:
- Request rate (per channel)
- p95 latency (per endpoint)
- Error rate
- Kafka consumer lag
- DB pool utilization
- Active tickets by status

## CI/CD Approach

GitHub Actions with:
- **Unit tests job**: Runs on every push, no Docker needed (fast, ~30s)
- **Integration tests job**: Runs on PRs to master, starts docker-compose (slower, ~3-5min)
- **Build & push job**: Runs on merge to master, builds Docker image
- Uses `services` for PostgreSQL in CI or docker-compose action

## Load Testing Strategy

Locust already configured with:
- WebFormUser (weight 5) - Form submissions + ticket status
- EmailUser (weight 3) - Gmail webhook simulation
- WhatsAppUser (weight 2) - WhatsApp webhook simulation

Target: 10 users, 5 minutes, p95 < 3s, 0% failure rate.

Note: Load tests against the docker-compose stack are limited by local resources. For true 24/7 validation, the load test should run in a staging environment. For Stage 3, we validate the pattern works locally.
