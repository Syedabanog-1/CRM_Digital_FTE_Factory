#!/usr/bin/env bash
# Run all unit tests (no Docker required)
# Usage: ./scripts/run-unit-tests.sh

set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Running all unit tests..."
python -m pytest tests/ production/tests/test_agent.py production/tests/test_channels.py \
    production/tests/test_transition.py -v
