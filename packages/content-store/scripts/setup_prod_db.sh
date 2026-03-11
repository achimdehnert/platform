#!/usr/bin/env bash
# content_store — Production Database Setup (ADR-130)
# Run on: 88.198.191.108 (hetzner-prod)
# Usage: bash setup_prod_db.sh
set -euo pipefail

DB_NAME="${CONTENT_STORE_DB_NAME:-content_store}"
DB_USER="${CONTENT_STORE_DB_USER:-content_store}"
DB_PASS="${CONTENT_STORE_DB_PASSWORD:?CONTENT_STORE_DB_PASSWORD must be set}"

echo "=== content_store DB Setup (ADR-130) ==="

# Create role + database (idempotent)
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
    RAISE NOTICE 'Role ${DB_USER} created';
  ELSE
    RAISE NOTICE 'Role ${DB_USER} already exists';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}');

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

# Verify
sudo -u postgres psql -c "SELECT datname FROM pg_database WHERE datname = '${DB_NAME}';"
echo "=== Done. Next: manage.py migrate --database=content_store ==="
