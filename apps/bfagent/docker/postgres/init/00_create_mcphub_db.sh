#!/usr/bin/env bash
set -euo pipefail

# This script runs on first container init (empty data dir).
# It creates an additional database for MCP Hub.

MCPHUB_DB_NAME="${MCPHUB_POSTGRES_DB:-mcphub_dev}"

if [ -z "${MCPHUB_DB_NAME}" ]; then
  echo "MCPHUB_POSTGRES_DB is empty; skipping."
  exit 0
fi

DB_EXISTS=$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='${MCPHUB_DB_NAME}'")
if [ "$DB_EXISTS" != "1" ]; then
  echo "Creating database: ${MCPHUB_DB_NAME}"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -c "CREATE DATABASE \"${MCPHUB_DB_NAME}\";"
else
  echo "Database already exists: ${MCPHUB_DB_NAME}"
fi
