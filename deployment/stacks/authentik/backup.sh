#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# authentik backup — pg_dump for identity database (ADR-142)
# ═══════════════════════════════════════════════════════════════════════════════
# Install: cp backup.sh /etc/cron.daily/authentik-backup && chmod +x /etc/cron.daily/authentik-backup
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

BACKUP_BASE="/opt/backups/authentik"
BACKUP_DIR="${BACKUP_BASE}/$(date +%Y-%m-%d)"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}"

# 1. PostgreSQL Dump (alle User-Identitäten der Platform)
docker exec iil_authentik_db pg_dump \
  -U authentik authentik \
  --no-owner --no-acl \
  | gzip > "${BACKUP_DIR}/authentik_db.sql.gz"

# 2. Media (Custom Branding, Logos)
docker cp \
  iil_authentik_server:/media/. \
  "${BACKUP_DIR}/media/" 2>/dev/null || true

# 3. Rotation
find "${BACKUP_BASE}/" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} +

echo "[$(date -Is)] authentik backup completed: ${BACKUP_DIR}"
