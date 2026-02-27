#!/usr/bin/env bash
# ============================================================================
# db-backup.sh — PostgreSQL backup for platform services (v2)
# ============================================================================
#
# Changes from v1:
#   - Sources services.conf instead of inline DB maps
#   - Supports --all flag to backup all services
#   - Validates backup integrity (non-empty + gzip valid)
#
# Usage:
#   db-backup.sh <service>           # Single service backup
#   db-backup.sh --all               # Backup all services with DBs
#
# Backups: /opt/deploy/backups/<service>/<service>_YYYYMMDD_HHMMSS.sql.gz
# Retention: 7 days (configurable via RETENTION_DAYS)
# ============================================================================
set -euo pipefail

# ── Load service registry ────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for conf_path in \
    "${SCRIPT_DIR}/services.conf" \
    "${SCRIPT_DIR}/setup/services.conf" \
    "${SCRIPT_DIR}/../setup/services.conf"; do
    [[ -f "$conf_path" ]] && { source "$conf_path"; break; }
done

if ! declare -p SERVICES &>/dev/null 2>&1; then
    echo "ERROR: services.conf not found." >&2
    exit 1
fi

BACKUP_BASE="/opt/deploy/backups"
STATE_DIR="/opt/deploy/production/.deployed"
LOG_FILE="${STATE_DIR}/deploy.log"
RETENTION_DAYS=7

mkdir -p "$STATE_DIR"

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ── Backup one service ───────────────────────────────────────────────────

backup_service() {
    local slug="$1"

    if ! _find_service "$slug"; then
        echo "ERROR: Unknown service '$slug'." >&2
        return 1
    fi

    if ! _has_field "$SVC_DB_CTR"; then
        echo "  SKIP $slug — no database configured"
        return 0
    fi

    local backup_dir="${BACKUP_BASE}/${slug}"
    local timestamp
    timestamp=$(date -u +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/${slug}_${timestamp}.sql.gz"

    mkdir -p "$backup_dir"

    # Check DB container running
    if ! docker inspect "$SVC_DB_CTR" >/dev/null 2>&1; then
        echo "  ❌ $slug — DB container not running: $SVC_DB_CTR"
        echo "[$(TS)] FAILED backup $slug container_not_running" >> "$LOG_FILE"
        return 1
    fi

    # Check DB reachable
    if ! docker exec "$SVC_DB_CTR" pg_isready -q 2>/dev/null; then
        echo "  ❌ $slug — DB not ready: $SVC_DB_CTR"
        echo "[$(TS)] FAILED backup $slug db_not_ready" >> "$LOG_FILE"
        return 1
    fi

    # Create backup
    echo -n "  Backing up $slug ($SVC_DB_NAME)... "
    if docker exec "$SVC_DB_CTR" pg_dump -U "$SVC_DB_USER" "$SVC_DB_NAME" \
        | gzip > "$backup_file" 2>/dev/null; then

        # Validate: non-empty and valid gzip
        if [[ ! -s "$backup_file" ]]; then
            echo "❌ empty file"
            rm -f "$backup_file"
            echo "[$(TS)] FAILED backup $slug empty_file" >> "$LOG_FILE"
            return 1
        fi

        if ! gzip -t "$backup_file" 2>/dev/null; then
            echo "❌ corrupt gzip"
            rm -f "$backup_file"
            echo "[$(TS)] FAILED backup $slug corrupt_gzip" >> "$LOG_FILE"
            return 1
        fi

        local size
        size=$(du -sh "$backup_file" | cut -f1)
        echo "✅ ${size} → $(basename "$backup_file")"
        echo "[$(TS)] SUCCESS backup $slug size=${size}" >> "$LOG_FILE"
    else
        echo "❌ pg_dump failed"
        rm -f "$backup_file"
        echo "[$(TS)] FAILED backup $slug pg_dump_error" >> "$LOG_FILE"
        return 1
    fi

    # Retention cleanup
    local deleted
    deleted=$(find "$backup_dir" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
    if [[ "$deleted" -gt 0 ]]; then
        echo "    Cleaned $deleted backup(s) older than ${RETENTION_DAYS} days"
    fi

    return 0
}

# ── Main ─────────────────────────────────────────────────────────────────

BACKUP_ALL=false
TARGET="${1:?Usage: db-backup.sh <service> | --all}"

if [[ "$TARGET" == "--all" ]]; then
    BACKUP_ALL=true
fi

echo "═══════════════════════════════════════════════════════"
echo "  Database Backup — $(date -u +%Y-%m-%d\ %H:%M:%S\ UTC)"
echo "═══════════════════════════════════════════════════════"
echo ""

TOTAL=0
PASS=0
FAIL=0

if $BACKUP_ALL; then
    for entry in "${SERVICES[@]}"; do
        _parse_service "$entry"
        if _has_field "$SVC_DB_CTR"; then
            TOTAL=$((TOTAL + 1))
            if backup_service "$SVC_SLUG"; then
                PASS=$((PASS + 1))
            else
                FAIL=$((FAIL + 1))
            fi
        fi
    done
else
    TOTAL=1
    if backup_service "$TARGET"; then
        PASS=1
    else
        FAIL=1
    fi
fi

echo ""
echo "─── Summary: ${PASS}/${TOTAL} succeeded, ${FAIL} failed ───"
[[ "$FAIL" -gt 0 ]] && exit 1 || exit 0
