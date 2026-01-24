#!/bin/bash
#
# BF Agent Restore Script
# ========================
# Restore database from backup
#
# Usage:
#   ./scripts/restore.sh /path/to/backup/db_YYYYMMDD_HHMMSS.sql.gz [--with-volumes] [--with-pgdata]
#
# WARNING: This will overwrite the current database!

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
# Check Arguments
# =============================================================================

if [ $# -eq 0 ]; then
    error "No backup file specified!"
    echo ""
    echo "Usage: $0 <backup-file> [--with-volumes] [--with-pgdata]"
    echo ""
    echo "Example:"
    echo "  $0 /var/backups/bfagent/daily/db_20241208_030000.sql.gz"
    echo "  $0 /var/backups/bfagent/daily/db_20241208_030000.sql.gz --with-volumes"
    echo "  $0 /var/backups/bfagent/daily/db_20241208_030000.sql.gz --with-volumes --with-pgdata"
    echo ""
    echo "Available backups:"
    find /var/backups/bfagent -name "db_*.sql.gz" -type f -mtime -7 | sort -r | head -10
    exit 1
fi

WITH_VOLUMES=0
WITH_PGDATA=0

POSITIONAL=()
for arg in "$@"; do
    case "$arg" in
        --with-volumes)
            WITH_VOLUMES=1
            ;;
        --with-pgdata)
            WITH_PGDATA=1
            ;;
        *)
            POSITIONAL+=("$arg")
            ;;
    esac
done

if [ ${#POSITIONAL[@]} -lt 1 ]; then
    error "No backup file specified!"
    exit 1
fi

BACKUP_FILE="${POSITIONAL[0]}"



if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

PROJECT_DIR="/opt/bfagent-app"
ENV_FILE="$PROJECT_DIR/.env.prod"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"

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

BACKUP_DIR=$(dirname "$BACKUP_FILE")
BACKUP_BASENAME=$(basename "$BACKUP_FILE")
BACKUP_STEM=${BACKUP_BASENAME%.sql.gz}
BACKUP_TS=${BACKUP_STEM#db_}

MEDIA_BACKUP_FILE="$BACKUP_DIR/media_${BACKUP_TS}.tar.gz"
STATIC_BACKUP_FILE="$BACKUP_DIR/static_${BACKUP_TS}.tar.gz"
PGDATA_BACKUP_FILE="$BACKUP_DIR/postgres_data_${BACKUP_TS}.tar.gz"

# =============================================================================
# Confirmation
# =============================================================================

echo ""
warn "⚠️  WARNING: This will OVERWRITE the current database!"
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo "Created: $(stat -c %y "$BACKUP_FILE" 2>/dev/null || stat -f "%Sm" "$BACKUP_FILE")"
echo ""
read -p "Are you sure you want to restore? (type 'yes' to confirm): " -r
echo ""

if [[ ! $REPLY =~ ^yes$ ]]; then
    log "Restore cancelled"
    exit 0
fi

# =============================================================================
# Stop application (compose)
# =============================================================================

log "Stopping application..."

if [ -f "$COMPOSE_FILE" ]; then
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop bfagent-web mcphub-api caddy 2>/dev/null || true
else
    warn "Compose file not found at $COMPOSE_FILE; continuing"
fi

# =============================================================================
# Pre-Restore Backup
# =============================================================================

log "Creating safety backup of current database..."

SAFETY_BACKUP="/var/backups/bfagent/before_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec bfagent_db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$SAFETY_BACKUP"

log "✅ Safety backup created: $SAFETY_BACKUP"

# =============================================================================
# Restore Database
# =============================================================================

log "Dropping existing database..."
docker exec bfagent_db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"

log "Creating new database..."
docker exec bfagent_db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

log "Restoring from backup..."
if zcat "$BACKUP_FILE" | docker exec -i bfagent_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null; then
    log "✅ Database restored successfully"
else
    error "Restore failed!"

    warn "Rolling back to safety backup..."
    zcat "$SAFETY_BACKUP" | docker exec -i bfagent_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

    error "Restore failed but safety backup restored"
    exit 1
fi

# =============================================================================
# Restore Volumes (optional)
# =============================================================================

restore_volume_from_tar() {
    local volume_name="$1"
    local tar_file="$2"
    local label="$3"

    if [ ! -f "$tar_file" ]; then
        log "ℹ️  ${label} backup not found: $tar_file"
        return 0
    fi

    if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
        warn "${label} volume not found: $volume_name"
        return 0
    fi

    log "Restoring ${label} volume from: $tar_file"
    docker run --rm \
        -v "$volume_name":/data \
        -v "$BACKUP_DIR":/backup:ro \
        alpine:3.20 \
        sh -lc "rm -rf /data/* /data/.[!.]* /data/..?* 2>/dev/null || true; cd /data && tar -xzf /backup/$(basename \"$tar_file\")"
    log "✅ ${label} volume restored"
}

if [ "$WITH_VOLUMES" -eq 1 ]; then
    restore_volume_from_tar "bfagent_media_prod" "$MEDIA_BACKUP_FILE" "Media"
    restore_volume_from_tar "bfagent_static_prod" "$STATIC_BACKUP_FILE" "Static"
fi

if [ "$WITH_PGDATA" -eq 1 ]; then
    log "Stopping postgres before restoring postgres data volume..."
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop postgres 2>/dev/null || true
    fi
    restore_volume_from_tar "bfagent_postgres_data_prod" "$PGDATA_BACKUP_FILE" "Postgres data"
fi

# =============================================================================
# Post-Restore Tasks
# =============================================================================

log "Starting application..."
if [ -f "$COMPOSE_FILE" ]; then
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres redis bfagent-web mcphub-api caddy
    log "✅ Application started via docker compose"
else
    warn "Compose file not found at $COMPOSE_FILE; not starting services"
fi

# =============================================================================
# Success
# =============================================================================

log "🎉 Restore completed successfully!"
log "Safety backup available at: $SAFETY_BACKUP"
log ""
log "Next steps:"
log "  1. Verify application: https://bfagent.iil.pet/login/"
log "  2. Test functionality"
log "  3. Remove safety backup if everything is OK:"
log "     rm $SAFETY_BACKUP"

exit 0
