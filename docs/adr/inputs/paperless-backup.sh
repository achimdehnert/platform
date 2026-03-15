#!/bin/bash
# Paperless-ngx daily backup script
# Runs: document_exporter + DB dump + rotation (keep 7 days)

set -euo pipefail

BACKUP_BASE="/opt/doc-hub/backups"
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="$BACKUP_BASE/$DATE"
CONTAINER="iil_dochub_web"
DB_CONTAINER="iil_dochub_db"
KEEP_DAYS=7

echo "$(date) — Paperless backup starting..."

# Create backup dir
mkdir -p "$BACKUP_DIR"

# 1. Paperless document exporter (metadata + manifests)
docker exec "$CONTAINER" python3 manage.py document_exporter \
    /usr/src/paperless/export \
    --no-archive --no-thumbnail --zip 2>&1 | tail -3

# Copy export from volume to backup dir
EXPORT_VOL=$(docker volume inspect doc-hub-stack_dochub_export -f '{{.Mountpoint}}')
cp -r "$EXPORT_VOL"/* "$BACKUP_DIR/" 2>/dev/null || true

# 2. PostgreSQL dump
docker exec "$DB_CONTAINER" pg_dump -U paperless paperless \
    | gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# 3. Rotate old backups
find "$BACKUP_BASE" -maxdepth 1 -type d -mtime +$KEEP_DAYS -exec rm -rf {} \;

# Summary
DB_SIZE=$(du -sh "$BACKUP_DIR/db-$DATE.sql.gz" | cut -f1)
TOTAL=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "$(date) — Backup complete: $BACKUP_DIR ($TOTAL, DB: $DB_SIZE)"
echo "$(date) — Keeping last $KEEP_DAYS days"
