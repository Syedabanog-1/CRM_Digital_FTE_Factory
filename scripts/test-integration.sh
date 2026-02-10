#!/usr/bin/env bash
# Stage 3 Integration Test Orchestration Script (Linux/CI)
# Usage: ./scripts/test-integration.sh
#
# Automates: docker-compose up -> wait for health -> seed DB -> run tests -> report -> teardown

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$PROJECT_ROOT/production"
TEST_EXIT_CODE=0

banner() {
    echo ""
    echo "============================================================"
    echo " $1"
    echo "============================================================"
    echo ""
}

cleanup() {
    banner "TEARDOWN: Stopping docker-compose stack"
    cd "$COMPOSE_DIR"
    docker-compose down -v 2>/dev/null || true
}

trap cleanup EXIT

# 1. Start the docker-compose stack
banner "STEP 1: Starting docker-compose stack"
cd "$COMPOSE_DIR"
docker-compose up -d

# 2. Wait for services to be healthy
banner "STEP 2: Waiting for services to be healthy"
python3 "$PROJECT_ROOT/scripts/wait-for-healthy.py" --timeout 120 --interval 5

# 3. Apply database schema
banner "STEP 3: Applying database schema"
docker exec -i production-postgres-1 psql -U fte -d fte_crm < "$COMPOSE_DIR/database/schema.sql" || \
    echo "WARNING: Schema application had issues (may already exist)"

# 4. Run database seed
banner "STEP 4: Seeding database"
docker exec production-api-1 python -c \
    "from production.database.seed import seed_database; import asyncio; asyncio.run(seed_database())" 2>&1 || \
    echo "WARNING: Seeding had issues"

# 5. Run unit tests
banner "STEP 5: Running unit tests"
cd "$PROJECT_ROOT"
UNIT_EXIT=0
python -m pytest tests/ production/tests/test_agent.py production/tests/test_channels.py \
    production/tests/test_transition.py -v --tb=short || UNIT_EXIT=$?

if [ $UNIT_EXIT -ne 0 ]; then
    echo "WARNING: Some unit tests failed (exit code: $UNIT_EXIT)"
    TEST_EXIT_CODE=$UNIT_EXIT
else
    echo "Unit tests: ALL PASSED"
fi

# 6. Run database integration tests
banner "STEP 6: Running database integration tests"
DB_EXIT=0
python -m pytest production/tests/test_database.py -v --tb=short || DB_EXIT=$?

if [ $DB_EXIT -ne 0 ]; then
    echo "WARNING: Some database tests failed (exit code: $DB_EXIT)"
    TEST_EXIT_CODE=$DB_EXIT
else
    echo "Database tests: ALL PASSED"
fi

# 7. Run E2E tests
banner "STEP 7: Running end-to-end tests"
E2E_EXIT=0
python -m pytest production/tests/test_e2e.py -v --tb=short || E2E_EXIT=$?

if [ $E2E_EXIT -ne 0 ]; then
    echo "WARNING: Some E2E tests failed (exit code: $E2E_EXIT)"
    TEST_EXIT_CODE=$E2E_EXIT
else
    echo "E2E tests: ALL PASSED"
fi

# 8. Summary
banner "TEST SUMMARY"
echo "Unit tests:     $([ $UNIT_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo "Database tests: $([ $DB_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo "E2E tests:      $([ $E2E_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')"
echo ""

exit $TEST_EXIT_CODE
