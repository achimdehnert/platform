#!/bin/bash
# ============================================================
# CAD-Hub Platform - Load Seed Data
# Run from WSL: ./scripts/load_seed_data.sh
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

export PGPASSWORD=$DB_PASSWORD

echo "Loading seed data into $DB_NAME..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SQL_DIR/005_seed_data.sql"

echo ""
echo "Seed data loaded successfully!"
echo ""
echo "Summary:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT 'Tenants' as entity, COUNT(*) as count FROM core_tenant
UNION ALL
SELECT 'Users', COUNT(*) FROM core_user
UNION ALL
SELECT 'Projects', COUNT(*) FROM cadhub_project
UNION ALL
SELECT 'Models', COUNT(*) FROM cadhub_model
UNION ALL
SELECT 'Rooms', COUNT(*) FROM cadhub_room
UNION ALL
SELECT 'Windows', COUNT(*) FROM cadhub_window
UNION ALL
SELECT 'Doors', COUNT(*) FROM cadhub_door
ORDER BY entity;
"
