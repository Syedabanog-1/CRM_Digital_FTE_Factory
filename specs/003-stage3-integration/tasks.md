# Tasks: Stage 3 Integration - E2E Testing, Load Testing & Operational Readiness

**Input**: Design documents from `/specs/003-stage3-integration/`
**Prerequisites**: plan.md, spec.md, research.md
**Branch**: `003-stage3-integration`

**Organization**: Tasks grouped by user story (6 stories from spec.md) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Scripts**: `scripts/` at repository root
- **Monitoring**: `production/monitoring/`
- **CI/CD**: `.github/workflows/`
- **Docs**: `docs/` at repository root
- **Reports**: `reports/` at repository root
- **Stage 2 tests**: `production/tests/` (read-only, already exist)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and utility scripts needed by all stories

- [ ] T001 Create directory structure: `scripts/`, `production/monitoring/`, `.github/workflows/`, `docs/runbooks/`, `reports/`
- [ ] T002 [P] Create `scripts/wait-for-healthy.py` - polling utility that checks PostgreSQL (pg_isready equivalent via asyncpg), Kafka (broker connection), and API (/health endpoint) with configurable timeout and retry interval
- [ ] T003 [P] Create `production/conftest.py` with shared pytest fixtures for integration tests: `docker_stack` (session-scoped, checks health), `seeded_db` (applies schema + seed), `api_client` (httpx client with retry)

---

## Phase 2: US1 - Docker Compose Integration Test Suite (P1)

**Goal**: Get all existing integration tests passing against the docker-compose stack

**Independent Test**: Run `scripts/test-integration.ps1` and all tests pass green

- [ ] T004 [US1] Review and fix `production/docker-compose.yml` health checks - ensure PostgreSQL has `pg_isready` healthcheck, API has `/health` curl healthcheck, add `depends_on` with `condition: service_healthy` for proper startup ordering
- [ ] T005 [US1] Create `scripts/test-integration.ps1` (Windows) - orchestration script that: (1) runs `docker-compose up -d`, (2) calls `wait-for-healthy.py`, (3) applies schema via `docker exec psql < schema.sql`, (4) runs seed via `docker exec python seed.py`, (5) runs `pytest production/tests/test_database.py production/tests/test_e2e.py -v --tb=short`, (6) captures exit code, (7) runs `docker-compose down -v`, (8) exits with test exit code
- [ ] T006 [P] [US1] Create `scripts/test-integration.sh` (Linux/CI) - same as T005 but for bash, used in GitHub Actions
- [ ] T007 [US1] Fix any test failures discovered when running `test_database.py` against live PostgreSQL - update connection strings, fix asyncpg Windows compatibility issues, handle test isolation (cleanup between tests)
- [ ] T008 [US1] Fix any test failures in `test_e2e.py` against the running stack - verify API endpoint URLs, Kafka topic creation, message processing pipeline, and response verification with appropriate timeouts
- [ ] T009 [US1] Create `scripts/run-unit-tests.ps1` and `scripts/run-unit-tests.sh` - convenience scripts that run all unit tests (no Docker needed): `pytest tests/ production/tests/test_agent.py production/tests/test_channels.py production/tests/test_transition.py -v`

**Checkpoint**: `scripts/test-integration.ps1` runs green with all database and E2E tests passing

---

## Phase 3: US2 - Load Testing & Performance Validation (P1)

**Goal**: Validate performance SLAs under realistic multi-channel load

**Independent Test**: Run Locust load test and verify p95 < 3s

- [ ] T010 [US2] Create `scripts/run-load-test.ps1` - script that: (1) ensures docker-compose stack is running, (2) runs `locust -f production/tests/load_test.py --host=http://localhost:8000 --headless --users 10 --spawn-rate 2 --run-time 5m --csv=reports/load-test`, (3) parses CSV results, (4) generates `reports/load-test-report.md` with p50/p95/p99 latencies, throughput, error rate, per-channel breakdown
- [ ] T011 [P] [US2] Create `scripts/run-load-test.sh` - Linux/CI version of T010
- [ ] T012 [US2] Create `reports/load-test-report-template.md` - template for load test results with sections: Executive Summary, Test Configuration, Results by Channel, Latency Distribution, Error Analysis, Recommendations, Raw Data Reference

**Checkpoint**: Load test completes with p95 < 3s and report is generated

---

## Phase 4: US3 - Operational Runbooks (P2)

**Goal**: Document 5 operational procedures for system management

**Independent Test**: A peer can follow each runbook without additional context

- [ ] T013 [P] [US3] Create `docs/runbooks/deployment.md` - step-by-step K8s deployment: build image, push to registry, update deployment YAML, apply with kubectl, verify rollout, smoke test endpoints
- [ ] T014 [P] [US3] Create `docs/runbooks/rollback.md` - rollback procedure: identify bad deployment, kubectl rollout undo, verify previous version, check health, notify stakeholders
- [ ] T015 [P] [US3] Create `docs/runbooks/scaling.md` - scaling guide: check current replicas, identify bottleneck (CPU/memory/Kafka lag), scale API or worker deployments, verify HPA thresholds, update resource limits
- [ ] T016 [P] [US3] Create `docs/runbooks/incident-response.md` - incident response: severity levels (P1-P4), diagnostic checklist (health endpoints, logs, metrics, Kafka lag, DB connections), escalation matrix, communication template, post-mortem template
- [ ] T017 [P] [US3] Create `docs/runbooks/database-maintenance.md` - DB ops: backup with pg_dump, restore from backup, vacuum analyze, reindex, check table sizes, manage pgvector indexes, connection pool monitoring

**Checkpoint**: 5 runbooks complete and peer-reviewable

---

## Phase 5: US4 - Monitoring & Alerting Configuration (P2)

**Goal**: Configure Prometheus metrics, Grafana dashboard, and alerting rules

**Independent Test**: `/metrics` endpoint returns valid Prometheus data

- [ ] T018 [US4] Add `prometheus-fastapi-instrumentator` to `production/requirements.txt` and instrument the FastAPI app in `production/api/main.py` - add `/metrics` endpoint with default HTTP metrics (request count, duration histogram, in-progress gauge)
- [ ] T019 [US4] Add custom Prometheus metrics to `production/api/main.py` and `production/workers/message_processor.py`: `fte_tickets_created_total` (counter by channel, category), `fte_escalations_total` (counter by reason), `fte_messages_processed_total` (counter by channel), `fte_processing_duration_seconds` (histogram)
- [ ] T020 [P] [US4] Create `production/monitoring/prometheus.yml` - Prometheus scrape config targeting the API service at `:8000/metrics` and worker metrics, with 15s scrape interval
- [ ] T021 [P] [US4] Create `production/monitoring/grafana-dashboard.json` - Grafana dashboard with 6 panels: Request Rate by Channel, p95 Latency by Endpoint, Error Rate, Kafka Consumer Lag, Active Tickets by Status, Escalation Rate
- [ ] T022 [P] [US4] Create `production/monitoring/alerting-rules.yml` - Prometheus alerting rules: HighLatency (p95 > 3s for 5min), HighErrorRate (>1% for 5min), KafkaLagHigh (>1000 for 10min), DBPoolExhausted (>90% for 5min), ServiceDown (health check fails for 1min)
- [ ] T023 [US4] Add `prometheus` and `grafana` services to `production/docker-compose.yml` with volume mounts for configs from `production/monitoring/`

**Checkpoint**: `/metrics` returns data, docker-compose includes Prometheus + Grafana

---

## Phase 6: US5 - CI/CD Pipeline Configuration (P2)

**Goal**: Automated testing and build pipeline via GitHub Actions

**Independent Test**: Push a commit and GitHub Actions runs green

- [ ] T024 [US5] Create `.github/workflows/ci.yml` - GitHub Actions workflow with 3 jobs: (1) `unit-tests` - runs on every push, installs Python 3.11, pip install deps, runs `pytest tests/ production/tests/test_agent.py production/tests/test_channels.py production/tests/test_transition.py`; (2) `integration-tests` - runs on PRs to master, uses docker-compose to start stack, runs integration tests; (3) `build` - runs on merge to master, builds Docker image
- [ ] T025 [P] [US5] Create `.github/workflows/lint.yml` - Lint workflow: runs ruff or flake8 on push, checks formatting
- [ ] T026 [US5] Update `pyproject.toml` with test markers: `unit`, `integration`, `e2e`, `load` so CI can selectively run test subsets with `-m unit` etc.

**Checkpoint**: CI runs green on push to the integration branch

---

## Phase 7: US6 - Production Readiness Documentation (P3)

**Goal**: Comprehensive readiness report summarizing all validation evidence

**Independent Test**: Document is reviewable by non-technical stakeholders

- [ ] T027 [P] [US6] Create `docs/architecture-diagram.md` - text-based system architecture showing: Channels (Gmail, WhatsApp, Web Form) -> FastAPI -> Kafka -> Worker -> OpenAI Agent -> PostgreSQL, with ports, protocols, and data flow
- [ ] T028 [US6] Create `docs/production-readiness.md` - comprehensive report with sections: Executive Summary, System Architecture, Component Inventory (all services with versions), Test Coverage Summary (unit/integration/E2E/load counts + results), Performance Benchmarks (from load test report), Security Review (secrets management, input validation, CORS, Twilio signature), Operational Procedures (runbook links), Monitoring & Alerting (dashboard + rules), Known Limitations & Future Work, Readiness Checklist (all items with evidence)
- [ ] T029 [US6] Create `specs/003-stage3-integration/checklists/requirements.md` - requirements validation checklist mapping each FR and SC from spec.md to evidence (test results, file paths, config locations)

**Checkpoint**: Production readiness document complete with all evidence linked

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Final validation and cleanup

- [ ] T030 Run full test suite (unit + integration) via orchestration script and capture final results
- [ ] T031 Update `CLAUDE.md` with Stage 3 active technologies and test commands
- [ ] T032 Update `specs/003-stage3-integration/checklists/requirements.md` with final pass/fail results for all success criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (US1 Docker Integration)**: Depends on Phase 1 - BLOCKS load testing (US2)
- **Phase 3 (US2 Load Testing)**: Depends on Phase 2 (needs running stack)
- **Phase 4 (US3 Runbooks)**: Depends on Phase 1 only - can parallel with Phase 2/3
- **Phase 5 (US4 Monitoring)**: Depends on Phase 1 - can parallel with Phase 2/3
- **Phase 6 (US5 CI/CD)**: Depends on Phase 2 (needs test commands finalized)
- **Phase 7 (US6 Readiness)**: Depends on ALL previous phases (needs all evidence)
- **Phase 8 (Polish)**: Depends on Phase 7

### Parallel Opportunities

- T002, T003 can run in parallel (different files)
- T005, T006 can overlap (Windows + Linux scripts)
- T013-T017 (all runbooks) can run in parallel
- T020, T021, T022 (monitoring configs) can run in parallel
- T024, T025 (CI workflows) can overlap
- Phase 4 (Runbooks) can parallel with Phase 2/3/5

---

## Notes

- No new application code in Stage 3 - only test infrastructure, scripts, configs, and docs
- Database and E2E tests may require fixes when run against real infrastructure (vs mocks)
- Load test results depend on local hardware - document machine specs in report
- Monitoring adds `prometheus-fastapi-instrumentator` as the only new production dependency
- CI/CD uses docker-compose in GitHub Actions which may have resource constraints
