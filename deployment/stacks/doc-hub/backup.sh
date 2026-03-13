#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# doc-hub backup — pg_dump + Paperless document_exporter (ADR-144)
# ═══════════════════════════════════════════════════════════════════════════════
# Install: cp backup.sh /etc/cron.daily/doc-hub-backup && chmod +x /etc/cron.daily/doc-hub-backup
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

DEPLOY_DIR="/opt/doc-hub"
BACKUP_BASE="/opt/backups/doc-hub"
BACKUP_DIR="${BACKUP_BASE}/$(date +%Y-%m-%d)"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

# 1. PostgreSQL Dump
docker exec iil_dochub_db pg_dump \
  -U paperless paperless \
  --no-owner --no-acl \
  | gzip > "${BACKUP_DIR}/paperless_db.sql.gz"

# 2. Paperless Export (Dokumente + Metadaten als JSON-Manifest)
docker exec iil_dochub_web \
  python manage.py document_exporter \
  --no-progress-bar \
  /usr/src/paperless/export

docker cp \
  iil_dochub_web:/usr/src/paperless/export/. \
  "${BACKUP_DIR}/paperless_export/"

# 3. Rotation — ältere Backups löschen
find "${BACKUP_BASE}/" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} +

echo "[$(date -Is)] doc-hub backup completed: ${BACKUP_DIR}"
