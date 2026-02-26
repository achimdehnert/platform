#!/usr/bin/env bash
# Run bfagent-llm tests with Docker PostgreSQL.
# Usage: bash scripts/test.sh [pytest args...]
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Starting test PostgreSQL ==="
docker compose -f docker-compose.test.yml up -d --wait

echo "=== Running tests ==="
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5433
export TEST_DB_USER=test
export TEST_DB_PASSWORD=test
export TEST_DB_NAME=test_bfagent_llm

pytest tests/ "$@"
RESULT=$?

echo "=== Stopping test PostgreSQL ==="
docker compose -f docker-compose.test.yml down

exit $RESULT
