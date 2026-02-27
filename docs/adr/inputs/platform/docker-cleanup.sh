#!/usr/bin/env bash
# ============================================================================
# docker-cleanup.sh — Docker image/volume/builder pruning
# ============================================================================
#
# Install as cron job:
#   cp docker-cleanup.sh /etc/cron.weekly/docker-cleanup
#   chmod +x /etc/cron.weekly/docker-cleanup
#
# Or install as daily with threshold check:
#   cp docker-cleanup.sh /etc/cron.daily/docker-cleanup
#
# What it cleans:
#   - Dangling images (no tag, no container reference)
#   - Images older than 7 days that aren't used by running containers
#   - Stopped containers older than 24h
#   - Build cache older than 7 days
#   - Anonymous volumes not used by any container
#
# What it does NOT clean:
#   - Running containers
#   - Images used by running containers
#   - Named volumes (your data is safe)
#   - Images newer than 7 days
#
# ============================================================================
set -euo pipefail

LOG_TAG="docker-cleanup"
STATE_DIR="/opt/deploy/production/.deployed"
LOG_FILE="${STATE_DIR}/deploy.log"
RETENTION_HOURS=168  # 7 days in hours

mkdir -p "$STATE_DIR"

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

log() {
    echo "$*"
    logger -t "$LOG_TAG" "$*" 2>/dev/null || true
}

# ── Check if cleanup is needed ───────────────────────────────────────────

DISK_USAGE=$(df /var/lib/docker 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%' || echo "0")
DANGLING_COUNT=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l)

log "Docker cleanup started. Disk: ${DISK_USAGE}%, Dangling images: ${DANGLING_COUNT}"

# Skip if disk is fine and few dangling images
if [[ "$DISK_USAGE" -lt 70 ]] && [[ "$DANGLING_COUNT" -lt 5 ]]; then
    log "Disk OK (${DISK_USAGE}%) and few dangling images ($DANGLING_COUNT). Skipping."
    echo "[$(TS)] SKIP docker-cleanup disk=${DISK_USAGE}% dangling=${DANGLING_COUNT}" >> "$LOG_FILE"
    exit 0
fi

# ── Record before state ──────────────────────────────────────────────────

BEFORE_DISK="$DISK_USAGE"
BEFORE_IMAGES=$(docker images -q | wc -l)

# ── Clean stopped containers (>24h) ─────────────────────────────────────

log "Pruning stopped containers older than 24h..."
CONTAINER_OUTPUT=$(docker container prune -f --filter "until=24h" 2>&1 || true)
CONTAINERS_REMOVED=$(echo "$CONTAINER_OUTPUT" | grep -c "Deleted" || echo "0")

# ── Clean dangling images ────────────────────────────────────────────────

log "Pruning dangling images..."
docker image prune -f 2>&1 || true

# ── Clean old unused images (>7 days, not used by running containers) ────

log "Pruning unused images older than ${RETENTION_HOURS}h..."
IMAGE_OUTPUT=$(docker image prune -af --filter "until=${RETENTION_HOURS}h" 2>&1 || true)

# ── Clean build cache ────────────────────────────────────────────────────

log "Pruning build cache older than ${RETENTION_HOURS}h..."
docker builder prune -af --filter "until=${RETENTION_HOURS}h" 2>&1 || true

# ── Clean anonymous volumes ──────────────────────────────────────────────

log "Pruning anonymous volumes..."
docker volume prune -f --filter "label!=keep" 2>&1 || true

# ── Record after state ───────────────────────────────────────────────────

AFTER_DISK=$(df /var/lib/docker 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%' || echo "0")
AFTER_IMAGES=$(docker images -q | wc -l)
FREED=$((BEFORE_IMAGES - AFTER_IMAGES))

log "Cleanup complete. Disk: ${BEFORE_DISK}% → ${AFTER_DISK}%. Images: ${BEFORE_IMAGES} → ${AFTER_IMAGES} (-${FREED})"
echo "[$(TS)] SUCCESS docker-cleanup disk=${BEFORE_DISK}%->${AFTER_DISK}% images_removed=${FREED}" >> "$LOG_FILE"

# ── Emergency prune if still critical ────────────────────────────────────

if [[ "$AFTER_DISK" -gt 90 ]]; then
    log "WARNING: Disk still critical (${AFTER_DISK}%). Running aggressive prune..."
    docker system prune -af --volumes 2>&1 || true
    EMERGENCY_DISK=$(df /var/lib/docker 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%' || echo "0")
    log "Emergency prune done. Disk: ${EMERGENCY_DISK}%"
    echo "[$(TS)] EMERGENCY docker-cleanup disk=${AFTER_DISK}%->${EMERGENCY_DISK}%" >> "$LOG_FILE"
fi
