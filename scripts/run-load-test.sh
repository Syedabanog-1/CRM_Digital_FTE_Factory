#!/usr/bin/env bash
# Run Locust load test and generate report
# Usage: ./scripts/run-load-test.sh [--users 10] [--duration 5m]
# Requires: docker-compose stack running

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
USERS="${1:-10}"
DURATION="${2:-5m}"
SPAWN_RATE="${3:-2}"

mkdir -p "$REPORTS_DIR"

# Check if stack is running
echo "Checking if API is healthy..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is healthy"
else
    echo "ERROR: API is not running. Start with: docker-compose up -d"
    exit 1
fi

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
CSV_PREFIX="$REPORTS_DIR/load-test-$TIMESTAMP"

echo ""
echo "Starting load test: $USERS users, $DURATION duration, spawn rate $SPAWN_RATE/s"
echo ""

cd "$PROJECT_ROOT"
locust -f production/tests/load_test.py \
    --host=http://localhost:8000 \
    --headless \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --csv="$CSV_PREFIX" \
    --html="$REPORTS_DIR/load-test-$TIMESTAMP.html"

# Generate markdown report
if [ -f "${CSV_PREFIX}_stats.csv" ]; then
    echo ""
    echo "Load test complete. Generating report..."

    cat > "$REPORTS_DIR/load-test-report.md" <<REPORT
# Load Test Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Users**: $USERS
**Duration**: $DURATION
**Spawn Rate**: $SPAWN_RATE/s

## Results

See CSV files in \`reports/\` for detailed metrics:
- \`load-test-${TIMESTAMP}_stats.csv\` - Request statistics
- \`load-test-${TIMESTAMP}_stats_history.csv\` - Time series
- \`load-test-${TIMESTAMP}_failures.csv\` - Failures
- \`load-test-${TIMESTAMP}.html\` - HTML report

## SLA Validation

| Metric | Target | Status |
|--------|--------|--------|
| p95 Latency | < 3000ms | CHECK CSV |
| Error Rate | < 1% | CHECK CSV |
| Concurrent Users | >= 10 | $USERS |
REPORT

    echo "Report saved to: reports/load-test-report.md"
fi
