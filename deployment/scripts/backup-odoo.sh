#!/usr/bin/env bash
# =============================================================================
# backup-odoo.sh — DB dump + Filestore backup for Odoo
# =============================================================================
# Usage: backup-odoo.sh <APP_NAME> <DEPLOY_DIR>
# =============================================================================
set -euo pipefail

APP_NAME="${1:-}"
DEPLOY_DIR="${2:-}"

if [[ -z "$APP_NAME" || -z "$DEPLOY_DIR" ]]; then
    echo "Usage: backup-odoo.sh <APP_NAME> <DEPLOY_DIR>"
    exit 1
fi

cd "$DEPLOY_DIR"

ENV_FILE=".env.prod"
COMPOSE_FILE="docker-compose.prod.yml"

compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

BACKUP_DIR="${DEPLOY_DIR}/backups"
mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"

# -- Identify DB container ---------------------------------------------------
DB_CONTAINER=$(compose ps --format '{{.Names}}' 2>/dev/null \
    | grep -E '(postgres|_db)' | head -1 || true)
if [[ -z "$DB_CONTAINER" ]]; then
    echo "ERROR: No DB container found."
    exit 1
fi

# -- Read credentials from env -----------------------------------------------
POSTGRES_DB=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d= -f2-)
POSTGRES_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2-)

# -- DB backup (custom format, compressed) -----------------------------------
DB_OUT="${BACKUP_DIR}/db_${TS}.dump"
echo "Creating DB backup: ${DB_OUT}"
docker exec "$DB_CONTAINER" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$DB_OUT"

# -- Filestore backup (odoo_data volume) -------------------------------------
VOL_NAME="${APP_NAME}_odoo_data"
FS_OUT="${BACKUP_DIR}/odoo_data_${TS}.tgz"
echo "Creating filestore backup: ${FS_OUT}"
docker run --rm \
    -v "${VOL_NAME}:/data:ro" \
    -v "${BACKUP_DIR}:/backup" \
    alpine:3 sh -c "cd /data && tar czf /backup/odoo_data_${TS}.tgz ."

# -- Cleanup old backups (keep last 10) --------------------------------------
ls -1t "${BACKUP_DIR}"/db_*.dump 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
ls -1t "${BACKUP_DIR}"/odoo_data_*.tgz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

# -- Summary -----------------------------------------------------------------
echo "Backup done:"
ls -lh "$DB_OUT" "$FS_OUT"
