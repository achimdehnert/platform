#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# outline backup — pg_dump for Knowledge-Hub (ADR-143)
# ═══════════════════════════════════════════════════════════════════════════════
# Install: cp backup.sh /etc/cron.daily/outline-backup && chmod +x /etc/cron.daily/outline-backup
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

BACKUP_BASE="/opt/backups/outline"
BACKUP_DIR="${BACKUP_BASE}/$(date +%Y-%m-%d)"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}"

# 1. PostgreSQL Dump (alle Wiki-Dokumente)
docker exec iil_knowledge_outline_db pg_dump \
  -U outline outline \
  --no-owner --no-acl \
  | gzip > "${BACKUP_DIR}/outline_db.sql.gz"

# 2. File-Storage (Uploads, Attachments)
docker cp \
  iil_knowledge_outline:/var/lib/outline/data/. \
  "${BACKUP_DIR}/outline_data/" 2>/dev/null || true

# 3. Rotation
find "${BACKUP_BASE}/" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} +

echo "[$(date -Is)] outline backup completed: ${BACKUP_DIR}"
