---
id: 002
title: Cross-Artifact Analysis and Test Isolation Fixes
stage: misc
date: 2026-02-10
surface: agent
model: claude-opus-4-6
feature: 003-stage3-integration
branch: 003-stage3-integration
user: Syedabanog-1
command: /sp.analyze
labels: ["analysis", "test-isolation", "pytest-markers", "conftest", "cross-artifact"]
links:
  spec: specs/003-stage3-integration/spec.md
  ticket: null
  adr: null
  pr: https://github.com/Syedabanog-1/CRM_Digital_FTE_Factory/pull/2
files:
  - production/conftest.py
  - production/tests/conftest.py
  - production/tests/test_database.py
  - production/tests/test_e2e.py
  - production/tests/load_test.py
  - specs/003-stage3-integration/tasks.md
tests:
  - "202 unit tests passed (128 Stage 1 + 74 Stage 2)"
  - "53 infrastructure tests skipped (31 database + 22 E2E)"
  - "0 errors (previously 3 collection errors + access violation crash)"
---

## Prompt

/sp.analyze analyze my app and fix these i found at app completion that's: All 3 stages of the Agent Maturity Model are now complete. Background command "Re-run Stage 2 tests with structlog installed" failed with exit code 1. That failed background task was the earlier Stage 2 test run that crashed on the database tests (asyncpg trying to connect to PostgreSQL without Docker running). This is expected - those tests require the docker-compose stack. The unit tests we ran separately all passed fine (202/202). The .env.example you have open looks correct for the Stage 2 production config. Is there anything specific you'd like to work on next?

## Response snapshot

Ran comprehensive cross-artifact analysis across all 3 stages (45 FRs, 140 tasks, 202 tests). Identified 10 findings: 2 CRITICAL (asyncpg crash, E2E connection failure), 3 HIGH (markers not applied, locust import, missing conftest), 3 MEDIUM (tasks.md status, terminology), 2 LOW (doc sync). Fixed all CRITICAL and HIGH issues by creating production/conftest.py with infrastructure skip conditions, production/tests/conftest.py with collect_ignore for locust, applying pytestmark decorators to test_database.py and test_e2e.py, guarding locust import, and updating tasks.md completion status. Result: 202 passed, 53 skipped, 0 errors.

## Outcome

- Impact: Fixed all test isolation issues - tests now run cleanly without Docker (202 pass, 53 skip, 0 errors vs previous 3 collection errors + access violation crash)
- Tests: 202 passed, 53 skipped (infrastructure-dependent), 0 errors
- Files: 7 files changed (2 new conftest.py, 3 test files updated, 1 tasks.md updated, 1 PHR)
- Next prompts: Run docker-compose stack to validate integration tests, add custom Prometheus metrics (T019)
- Reflection: pytest markers must be applied to test classes/modules, not just defined in pyproject.toml. Infrastructure-dependent tests need conftest.py with automatic skip conditions to prevent collection crashes.

## Evaluation notes (flywheel)

- Failure modes observed: asyncpg Windows access violation when PostgreSQL not running; locust ModuleNotFoundError during test collection; pytestmark defined but not applied
- Graders run and results (PASS/FAIL): Full test suite PASS (202 passed, 53 skipped, 0 errors)
- Prompt variant (if applicable): sp.analyze with fix directive
- Next experiment (smallest change to try): Add custom Prometheus metrics (T019) and run integration tests against Docker
