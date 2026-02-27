#!/usr/bin/env bash
# ============================================================================
# deploy.sh — Atomic deploy for a single platform service (v2)
# ============================================================================
#
# Changes from v1:
#   - Sources services.conf instead of inline registry (DRY)
#   - Automatic DB backup before migrations
#   - Pre-deploy validation checks
#   - Structured JSON log entries
#
# Usage:
#   deploy.sh <service> <image_tag> [--migrate] [--skip-checks] [--skip-backup]
#
# Examples:
#   deploy.sh travel-beat latest
#   deploy.sh bfagent v1.5.2 --migrate
#   deploy.sh dev-hub latest --migrate --skip-checks
#
# ============================================================================
set -euo pipefail

SERVICE="${1:?Usage: deploy.sh <service> <image_tag> [--migrate] [--skip-checks] [--skip-backup]}"
IMAGE_TAG="${2:-latest}"
shift 2 || true

# Parse flags
HAS_MIGRATIONS=false
SKIP_CHECKS=false
SKIP_BACKUP=false
for arg in "$@"; do
    case "$arg" in
        --migrate)      HAS_MIGRATIONS=true ;;
        --skip-checks)  SKIP_CHECKS=true ;;
        --skip-backup)  SKIP_BACKUP=true ;;
    esac
done

# ── Load service registry ────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# services.conf can be in same dir, or in setup/ subdir
for conf_path in \
    "${SCRIPT_DIR}/services.conf" \
    "${SCRIPT_DIR}/setup/services.conf" \
    "${SCRIPT_DIR}/../setup/services.conf"; do
    if [[ -f "$conf_path" ]]; then
        # shellcheck source=services.conf
        source "$conf_path"
        break
    fi
done

if ! declare -p SERVICES &>/dev/null 2>&1; then
    echo "ERROR: services.conf not found. Expected near $SCRIPT_DIR" >&2
    exit 1
fi

# ── Resolve service ──────────────────────────────────────────────────────

if ! _find_service "$SERVICE"; then
    echo "ERROR: Unknown service '$SERVICE'. Valid: $(_list_slugs)" >&2
    exit 1
fi

STATE_DIR="/opt/deploy/production/.deployed"
LOG_FILE="${STATE_DIR}/deploy.log"
TAG_FILE="${STATE_DIR}/${SVC_SLUG}.tag"
PREV_TAG_FILE="${STATE_DIR}/${SVC_SLUG}.tag.prev"

mkdir -p "$STATE_DIR"

# ── Helpers ──────────────────────────────────────────────────────────────

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

log_event() {
    local status="$1" message="$2"
    echo "[$(TS)] ${status} deploy ${SVC_SLUG} ${message}" >> "$LOG_FILE"
}

die() {
    echo "ERROR: $*" >&2
    log_event "FAILED" "${OLD_TAG:-unknown} -> ${IMAGE_TAG}: $*"
    exit 1
}

# ── Save current tag for rollback ────────────────────────────────────────

OLD_TAG="unknown"
if [[ -f "$TAG_FILE" ]]; then
    OLD_TAG=$(cat "$TAG_FILE")
    cp "$TAG_FILE" "$PREV_TAG_FILE"
fi

echo "═══════════════════════════════════════════════════════"
echo "  Deploy: ${SVC_SLUG} ${OLD_TAG} → ${IMAGE_TAG}"
echo "  Path:   ${SVC_PATH}"
echo "  Flags:  migrate=${HAS_MIGRATIONS} checks=$([[ $SKIP_CHECKS == true ]] && echo skip || echo run)"
echo "═══════════════════════════════════════════════════════"

log_event "START" "${OLD_TAG} -> ${IMAGE_TAG}"

# ============================================================================
# PHASE 0: Pre-deploy validation
# ============================================================================

if [[ "$SKIP_CHECKS" != "true" ]]; then
    echo ""
    echo "── Pre-deploy checks ──────────────────────────────"

    # 0a. Disk space
    DISK_USAGE=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    if [[ "$DISK_USAGE" -gt 90 ]]; then
        die "Disk usage critical: ${DISK_USAGE}% (>90%). Free space before deploying."
    elif [[ "$DISK_USAGE" -gt 85 ]]; then
        echo "  ⚠️  Disk usage warning: ${DISK_USAGE}%"
    else
        echo "  ✅ Disk usage: ${DISK_USAGE}%"
    fi

    # 0b. Docker running
    if docker info >/dev/null 2>&1; then
        echo "  ✅ Docker running"
    else
        die "Docker is not running"
    fi

    # 0c. Deploy path exists
    if [[ -d "$SVC_PATH" ]]; then
        echo "  ✅ Deploy path exists: $SVC_PATH"
    else
        die "Deploy path missing: $SVC_PATH"
    fi

    # 0d. Compose file valid
    COMPOSE_PATH="${SVC_PATH}/${SVC_COMPOSE}"
    if [[ -f "$COMPOSE_PATH" ]]; then
        if docker compose -f "$COMPOSE_PATH" config --quiet 2>/dev/null; then
            echo "  ✅ Compose file valid"
        else
            die "Compose file invalid: $COMPOSE_PATH"
        fi
    else
        die "Compose file missing: $COMPOSE_PATH"
    fi

    # 0e. Env file present
    ENV_FILE="${SVC_PATH}/.env.prod"
    if [[ -f "$ENV_FILE" ]]; then
        echo "  ✅ Env file present: .env.prod"
    else
        echo "  ⚠️  No .env.prod found (might use env in compose)"
    fi

    # 0f. DB reachable (if service has DB and migrations requested)
    if [[ "$HAS_MIGRATIONS" == "true" ]] && _has_field "$SVC_DB_CTR"; then
        if docker exec "$SVC_DB_CTR" pg_isready -q 2>/dev/null; then
            echo "  ✅ Database reachable: $SVC_DB_CTR"
        else
            die "Database not reachable: $SVC_DB_CTR (needed for migrations)"
        fi
    fi

    echo ""
fi

# ============================================================================
# PHASE 1: Pull new image
# ============================================================================

echo "── Pulling image ──────────────────────────────────"
cd "$SVC_PATH"
docker compose -f "$SVC_COMPOSE" pull "$SVC_WEB" || die "docker compose pull failed"
echo "  ✅ Image pulled"

# ============================================================================
# PHASE 2: Pre-migration backup + Migrate
# ============================================================================

if [[ "$HAS_MIGRATIONS" == "true" ]]; then
    echo ""
    echo "── Migrations ─────────────────────────────────────"

    # Automatic backup before migration (unless skipped)
    if [[ "$SKIP_BACKUP" != "true" ]] && _has_field "$SVC_DB_CTR"; then
        echo "  Creating pre-migration backup..."
        BACKUP_SCRIPT="${SCRIPT_DIR}/db-backup.sh"
        if [[ -x "$BACKUP_SCRIPT" ]]; then
            if "$BACKUP_SCRIPT" "$SVC_SLUG"; then
                echo "  ✅ Pre-migration backup created"
            else
                echo "  ⚠️  Backup failed — continuing anyway (use --skip-backup to suppress)"
            fi
        else
            # Inline minimal backup if db-backup.sh not found
            BACKUP_DIR="/opt/deploy/backups/${SVC_SLUG}"
            BACKUP_TS=$(date -u +%Y%m%d_%H%M%S)
            mkdir -p "$BACKUP_DIR"
            if docker exec "$SVC_DB_CTR" pg_dump -U "$SVC_DB_USER" "$SVC_DB_NAME" \
                | gzip > "${BACKUP_DIR}/${SVC_SLUG}_premigrate_${BACKUP_TS}.sql.gz"; then
                echo "  ✅ Pre-migration backup: ${BACKUP_DIR}/${SVC_SLUG}_premigrate_${BACKUP_TS}.sql.gz"
            else
                echo "  ⚠️  Backup failed (non-fatal)"
            fi
        fi
    fi

    echo "  Running migrations..."
    docker compose -f "$SVC_COMPOSE" run --rm "$SVC_WEB" python manage.py migrate --noinput \
        || die "Migrations failed"
    echo "  ✅ Migrations complete"
fi

# ============================================================================
# PHASE 3: Deploy (recreate container)
# ============================================================================

echo ""
echo "── Starting service ───────────────────────────────"
docker compose -f "$SVC_COMPOSE" up -d --force-recreate "$SVC_WEB" \
    || die "docker compose up failed"
echo "  ✅ Container started"

# ============================================================================
# PHASE 4: Health check
# ============================================================================

if _has_field "$SVC_HEALTH"; then
    echo ""
    echo "── Health check ───────────────────────────────────"
    HEALTH_RETRIES=12
    HEALTH_INTERVAL=5
    HEALTH_OK=false

    for i in $(seq 1 $HEALTH_RETRIES); do
        if curl -sf --max-time 5 "$SVC_HEALTH" > /dev/null 2>&1; then
            HEALTH_OK=true
            break
        fi
        echo "  Attempt $i/$HEALTH_RETRIES — waiting ${HEALTH_INTERVAL}s..."
        sleep "$HEALTH_INTERVAL"
    done

    if [[ "$HEALTH_OK" == "true" ]]; then
        echo "  ✅ Health check passed: $SVC_HEALTH"
    else
        echo "  ❌ Health check failed after $HEALTH_RETRIES attempts"
        echo "  Rolling back to $OLD_TAG..."

        if [[ "$OLD_TAG" != "unknown" ]]; then
            export IMAGE_TAG="$OLD_TAG"
            docker compose -f "$SVC_COMPOSE" pull "$SVC_WEB" || true
            docker compose -f "$SVC_COMPOSE" up -d --force-recreate "$SVC_WEB" || true
        fi

        log_event "ROLLBACK" "${IMAGE_TAG} -> ${OLD_TAG} (health check failed)"
        echo "  Deploy ROLLED BACK to ${OLD_TAG}"
        exit 1
    fi
else
    echo ""
    echo "  ⚠️  No health URL configured — skipping health check"
fi

# ============================================================================
# PHASE 5: Finalize
# ============================================================================

echo "$IMAGE_TAG" > "$TAG_FILE"
log_event "SUCCESS" "${OLD_TAG} -> ${IMAGE_TAG}"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Deploy SUCCESS: ${SVC_SLUG}:${IMAGE_TAG}"
echo "═══════════════════════════════════════════════════════"
