#!/bin/bash
#
# BF Agent Backup Script
# ======================
# Automated daily backups for production server
#
# Usage:
#   ./scripts/backup.sh
#
# Cron (daily at 3 AM):
#   0 3 * * * /opt/bfagent-app/scripts/backup.sh >> /var/log/bfagent/backup.log 2>&1

set -e

# =============================================================================
# Configuration
# =============================================================================

BACKUP_DIR="/var/backups/bfagent"
PROJECT_DIR="/opt/bfagent-app"
ENV_FILE="$PROJECT_DIR/.env.prod"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7
KEEP_WEEKS=4
KEEP_MONTHS=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

log "Starting BF Agent backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"/{daily,weekly,monthly}

# Check if Docker is running
if ! docker ps &> /dev/null; then
    error "Docker is not running!"
    exit 1
fi

# Check if database container is running
if ! docker ps | grep -q bfagent_db; then
    error "Database container is not running!"
    exit 1
fi

# Load DB settings from env file if present
POSTGRES_DB="bfagent_prod"
POSTGRES_USER="bfagent"
if [ -f "$ENV_FILE" ]; then
    POSTGRES_DB=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f2- | tr -d '"' || true)
    POSTGRES_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f2- | tr -d '"' || true)
fi

if [ -z "$POSTGRES_DB" ] || [ -z "$POSTGRES_USER" ]; then
    error "POSTGRES_DB/POSTGRES_USER not set (checked $ENV_FILE)"
    exit 1
fi

# =============================================================================
# Database Backup
# =============================================================================

log "Backing up database..."

DB_BACKUP_FILE="$BACKUP_DIR/daily/db_$DATE.sql.gz"

if docker exec bfagent_db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$DB_BACKUP_FILE"; then
    DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
    log "✅ Database backup complete: $DB_SIZE"
else
    error "Database backup failed!"
    exit 1
fi

# =============================================================================
# Media Files Backup
# =============================================================================

log "Backing up media files..."

MEDIA_BACKUP_FILE="$BACKUP_DIR/daily/media_$DATE.tar.gz"

if docker volume inspect bfagent_media_prod >/dev/null 2>&1; then
    if docker run --rm \
        -v bfagent_media_prod:/data:ro \
        -v "$BACKUP_DIR/daily":/backup \
        alpine:3.20 \
        sh -lc "cd /data && tar -czf /backup/$(basename "$MEDIA_BACKUP_FILE") ."; then
        MEDIA_SIZE=$(du -h "$MEDIA_BACKUP_FILE" | cut -f1)
        log "✅ Media backup complete: $MEDIA_SIZE"
    else
        warn "Media backup had warnings (check permissions)"
    fi
else
    log "ℹ️  Media volume not found: bfagent_media_prod"
fi

STATIC_BACKUP_FILE="$BACKUP_DIR/daily/static_$DATE.tar.gz"

if docker volume inspect bfagent_static_prod >/dev/null 2>&1; then
    if docker run --rm \
        -v bfagent_static_prod:/data:ro \
        -v "$BACKUP_DIR/daily":/backup \
        alpine:3.20 \
        sh -lc "cd /data && tar -czf /backup/$(basename "$STATIC_BACKUP_FILE") ."; then
        STATIC_SIZE=$(du -h "$STATIC_BACKUP_FILE" | cut -f1)
        log "✅ Static backup complete: $STATIC_SIZE"
    else
        warn "Static backup had warnings (check permissions)"
    fi
else
    log "ℹ️  Static volume not found: bfagent_static_prod"
fi

PGDATA_BACKUP_FILE="$BACKUP_DIR/daily/postgres_data_$DATE.tar.gz"

if docker volume inspect bfagent_postgres_data_prod >/dev/null 2>&1; then
    if docker run --rm \
        -v bfagent_postgres_data_prod:/data:ro \
        -v "$BACKUP_DIR/daily":/backup \
        alpine:3.20 \
        sh -lc "cd /data && tar -czf /backup/$(basename "$PGDATA_BACKUP_FILE") ."; then
        PGDATA_SIZE=$(du -h "$PGDATA_BACKUP_FILE" | cut -f1)
        log "✅ Postgres volume backup complete: $PGDATA_SIZE"
    else
        warn "Postgres volume backup had warnings (check permissions)"
    fi
else
    log "ℹ️  Postgres volume not found: bfagent_postgres_data_prod"
fi

# =============================================================================
# Configuration Backup
# =============================================================================

log "Backing up configuration..."

CONFIG_BACKUP_FILE="$BACKUP_DIR/daily/config_$DATE.tar.gz"

tar -czf "$CONFIG_BACKUP_FILE" \
    -C "$PROJECT_DIR" \
    .env.prod \
    docker-compose.prod.yml \
    Caddyfile \
    2>/dev/null || warn "Some config files missing"

log "✅ Configuration backup complete"

# =============================================================================
# Weekly Backup (Sunday)
# =============================================================================

if [ "$(date +%u)" -eq 7 ]; then
    log "Creating weekly backup..."

    cp "$DB_BACKUP_FILE" "$BACKUP_DIR/weekly/db_week_$(date +%Y_W%W).sql.gz"

    if [ -f "$MEDIA_BACKUP_FILE" ]; then
        cp "$MEDIA_BACKUP_FILE" "$BACKUP_DIR/weekly/media_week_$(date +%Y_W%W).tar.gz"
    fi

    log "✅ Weekly backup created"
fi

# =============================================================================
# Monthly Backup (1st of month)
# =============================================================================

if [ "$(date +%d)" -eq 1 ]; then
    log "Creating monthly backup..."

    cp "$DB_BACKUP_FILE" "$BACKUP_DIR/monthly/db_month_$(date +%Y_%m).sql.gz"

    if [ -f "$MEDIA_BACKUP_FILE" ]; then
        cp "$MEDIA_BACKUP_FILE" "$BACKUP_DIR/monthly/media_month_$(date +%Y_%m).tar.gz"
    fi

    log "✅ Monthly backup created"
fi

# =============================================================================
# Cleanup Old Backups
# =============================================================================

log "Cleaning up old backups..."

# Daily backups (keep 7 days)
find "$BACKUP_DIR/daily" -type f -mtime +$KEEP_DAYS -delete 2>/dev/null || true

# Weekly backups (keep 4 weeks)
find "$BACKUP_DIR/weekly" -type f -mtime +$((KEEP_WEEKS * 7)) -delete 2>/dev/null || true

# Monthly backups (keep 3 months)
find "$BACKUP_DIR/monthly" -type f -mtime +$((KEEP_MONTHS * 30)) -delete 2>/dev/null || true

log "✅ Cleanup complete"

# =============================================================================
# Backup Statistics
# =============================================================================

log "Backup statistics:"
echo "  Daily backups:   $(ls -1 $BACKUP_DIR/daily/*.sql.gz 2>/dev/null | wc -l) files"
echo "  Weekly backups:  $(ls -1 $BACKUP_DIR/weekly/*.sql.gz 2>/dev/null | wc -l) files"
echo "  Monthly backups: $(ls -1 $BACKUP_DIR/monthly/*.sql.gz 2>/dev/null | wc -l) files"
echo "  Total size:      $(du -sh $BACKUP_DIR | cut -f1)"

# =============================================================================
# Optional: Upload to S3 or Offsite Storage
# =============================================================================

# Uncomment if you want to upload to S3
# if command -v aws &> /dev/null; then
#     log "Uploading to S3..."
#     aws s3 sync "$BACKUP_DIR" s3://your-bucket/bfagent-backups/ \
#         --exclude "*" \
#         --include "daily/*" \
#         --include "weekly/*" \
#         --include "monthly/*"
#     log "✅ S3 upload complete"
# fi

# =============================================================================
# Verify Latest Backup
# =============================================================================

if [ -f "$DB_BACKUP_FILE" ]; then
    # Check if backup is not empty
    if [ $(stat -f%z "$DB_BACKUP_FILE" 2>/dev/null || stat -c%s "$DB_BACKUP_FILE" 2>/dev/null) -gt 1000 ]; then
        log "✅ Backup verification passed"
    else
        error "Backup file too small - might be corrupted!"
        exit 1
    fi
else
    error "Backup file not found!"
    exit 1
fi

# =============================================================================
# Success
# =============================================================================

log "🎉 Backup completed successfully!"
log "Latest backup: $DB_BACKUP_FILE"

exit 0
