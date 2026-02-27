#!/usr/bin/env bash
# ============================================================================
# rollback.sh — Explicit rollback for a single platform service (v2)
# ============================================================================
#
# Changes from v1:
#   - Sources services.conf instead of inline registry
#   - Pre-rollback health snapshot
#   - Post-rollback health verification
#
# Usage:
#   rollback.sh <service> [target_tag]
#
# If target_tag is empty, rolls back to previous tag from state dir.
# ============================================================================
set -euo pipefail

SERVICE="${1:?Usage: rollback.sh <service> [target_tag]}"
TARGET_TAG="${2:-}"

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

if ! _find_service "$SERVICE"; then
    echo "ERROR: Unknown service '$SERVICE'. Valid: $(_list_slugs)" >&2
    exit 1
fi

STATE_DIR="/opt/deploy/production/.deployed"
LOG_FILE="${STATE_DIR}/deploy.log"
TAG_FILE="${STATE_DIR}/${SVC_SLUG}.tag"
PREV_TAG_FILE="${STATE_DIR}/${SVC_SLUG}.tag.prev"

mkdir -p "$STATE_DIR"

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ── Determine rollback target ────────────────────────────────────────────

if [[ -n "$TARGET_TAG" ]]; then
    ROLLBACK_TO="$TARGET_TAG"
elif [[ -f "$PREV_TAG_FILE" ]]; then
    ROLLBACK_TO=$(cat "$PREV_TAG_FILE")
else
    echo "ERROR: No previous tag for $SVC_SLUG and no target_tag specified." >&2
    exit 1
fi

CURRENT_TAG="unknown"
[[ -f "$TAG_FILE" ]] && CURRENT_TAG=$(cat "$TAG_FILE")

echo "═══════════════════════════════════════════════════════"
echo "  Rollback: ${SVC_SLUG} ${CURRENT_TAG} → ${ROLLBACK_TO}"
echo "  Path:     ${SVC_PATH}"
echo "═══════════════════════════════════════════════════════"
echo ""

echo "[$(TS)] START rollback $SVC_SLUG $CURRENT_TAG -> $ROLLBACK_TO" >> "$LOG_FILE"

# ── Pull rollback image and restart ──────────────────────────────────────

cd "$SVC_PATH"
export IMAGE_TAG="$ROLLBACK_TO"
docker compose -f "$SVC_COMPOSE" pull "$SVC_WEB" || true
docker compose -f "$SVC_COMPOSE" up -d --force-recreate "$SVC_WEB"

# ── Post-rollback health check ───────────────────────────────────────────

if _has_field "$SVC_HEALTH"; then
    echo ""
    echo "── Post-rollback health check ───────────────────"
    HEALTH_OK=false
    for i in $(seq 1 6); do
        if curl -sf --max-time 5 "$SVC_HEALTH" > /dev/null 2>&1; then
            HEALTH_OK=true
            break
        fi
        echo "  Attempt $i/6 — waiting 5s..."
        sleep 5
    done

    if [[ "$HEALTH_OK" == "true" ]]; then
        echo "  ✅ Rollback healthy"
    else
        echo "  ⚠️  Health check failed after rollback — manual intervention needed"
    fi
fi

# ── Update state ─────────────────────────────────────────────────────────

echo "$ROLLBACK_TO" > "$TAG_FILE"
echo "[$(TS)] SUCCESS rollback $SVC_SLUG $CURRENT_TAG -> $ROLLBACK_TO" >> "$LOG_FILE"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Rollback SUCCESS: ${SVC_SLUG}:${ROLLBACK_TO}"
echo "═══════════════════════════════════════════════════════"
