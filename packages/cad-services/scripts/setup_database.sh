#!/bin/bash
# ============================================================
# CAD-Hub Platform - Database Setup Script
# Run from WSL: ./scripts/setup_database.sh
# ============================================================

set -e

# Configuration
DB_NAME="${DB_NAME:-cadhub}"
DB_USER="${DB_USER:-bfagent}"
DB_PASSWORD="${DB_PASSWORD:-bfagent_dev_2024}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="$SCRIPT_DIR/../sql"

echo "=============================================="
echo "CAD-Hub Platform - Database Setup"
echo "=============================================="
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "=============================================="

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql not found. Please install PostgreSQL client."
    exit 1
fi

# Create database if not exists
echo ""
echo "[1/6] Creating database (if not exists)..."
psql -h $DB_HOST -p $DB_PORT -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER"

# Grant privileges
echo "[2/6] Granting privileges..."
psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER"

# Set connection string
export PGPASSWORD=$DB_PASSWORD

# Run migrations in order
echo ""
echo "[3/6] Running core schema migration..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SQL_DIR/001_core_schema.sql"

echo ""
echo "[4/6] Running CAD-Hub schema migration..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SQL_DIR/002_cadhub_schema.sql"

echo ""
echo "[5/6] Running infrastructure schema migration..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SQL_DIR/003_infra_schema.sql"

echo ""
echo "[6/6] Applying RLS policies..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SQL_DIR/004_rls_policies.sql"

echo ""
echo "=============================================="
echo "Database setup complete!"
echo "=============================================="
echo ""
echo "To load seed data, run:"
echo "  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $SQL_DIR/005_seed_data.sql"
echo ""
echo "Connection string:"
echo "  postgresql://$DB_USER:****@$DB_HOST:$DB_PORT/$DB_NAME"
