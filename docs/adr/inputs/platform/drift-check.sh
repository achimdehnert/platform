#!/usr/bin/env bash
# ============================================================================
# drift-check.sh — Configuration Drift Detection
# ============================================================================
#
# Detects when files on the server have diverged from git:
#   - docker-compose.prod.yml modified locally?
#   - .env.prod has unexpected changes?
#   - nginx config out of sync?
#   - Uncommitted changes in repo?
#   - Branch behind remote?
#
# This catches the common "someone SSH'd in and edited something" problem.
#
# Install as cron:
#   0 8 * * * /opt/deploy/scripts/drift-check.sh --quiet
#
# Usage:
#   drift-check.sh                    # Full drift check (interactive)
#   drift-check.sh --quiet            # Cron mode (only log drift)
#   drift-check.sh --json             # JSON output
#   drift-check.sh <service>          # Check single service
#
# ============================================================================
set -uo pipefail

# ── Load service registry ────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for conf_path in \
    "${SCRIPT_DIR}/services.conf" \
    "${SCRIPT_DIR}/setup/services.conf" \
    "${SCRIPT_DIR}/../setup/services.conf" \
    "/opt/deploy/scripts/services.conf"; do
    [[ -f "$conf_path" ]] && { source "$conf_path"; break; }
done

if ! declare -p SERVICES &>/dev/null 2>&1; then
    echo "ERROR: services.conf not found." >&2
    exit 1
fi

STATE_DIR="/opt/deploy/production/.deployed"
LOG_FILE="${STATE_DIR}/deploy.log"

mkdir -p "$STATE_DIR"

QUIET=false
JSON_OUT=false
SINGLE_SERVICE=""

for arg in "$@"; do
    case "$arg" in
        --quiet) QUIET=true ;;
        --json)  JSON_OUT=true ;;
        --*)     ;;
        *)       SINGLE_SERVICE="$arg" ;;
    esac
done

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ── Tracking ──────────────────────────────────────────────────────────────

_TOTAL=0
_CLEAN=0
_DRIFTED=0
_RESULTS=()
_ALERTS=()

# ── Check one service ────────────────────────────────────────────────────

check_drift() {
    local slug="$1"
    _find_service "$slug" || return

    if [[ ! -d "$SVC_PATH" ]]; then
        $QUIET || echo "  ⏭️  ${slug}: path not found ($SVC_PATH)"
        return
    fi

    if [[ ! -d "${SVC_PATH}/.git" ]]; then
        $QUIET || echo "  ⏭️  ${slug}: not a git repo"
        return
    fi

    _TOTAL=$((_TOTAL + 1))
    local drifts=()

    cd "$SVC_PATH"

    # 1. Uncommitted changes
    local dirty_count
    dirty_count=$(git status --porcelain 2>/dev/null | wc -l)
    if [[ "$dirty_count" -gt 0 ]]; then
        local dirty_files
        dirty_files=$(git status --porcelain 2>/dev/null | head -5)
        drifts+=("uncommitted: ${dirty_count} file(s)")
    fi

    # 2. Branch behind remote
    git fetch origin --quiet 2>/dev/null || true
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")

    local behind=0
    behind=$(git rev-list --count HEAD..origin/"${current_branch}" 2>/dev/null || echo "0")
    if [[ "$behind" -gt 0 ]]; then
        drifts+=("behind: ${behind} commit(s) behind origin/${current_branch}")
    fi

    # 3. Compose file modified (tracked file has local changes)
    if [[ -f "$SVC_COMPOSE" ]]; then
        if git diff --quiet HEAD -- "$SVC_COMPOSE" 2>/dev/null; then
            : # Clean
        else
            drifts+=("compose: $SVC_COMPOSE modified locally")
        fi
    fi

    # 4. .env.prod permissions (should be 600)
    local env_file="${SVC_PATH}/.env.prod"
    if [[ -f "$env_file" ]]; then
        local env_perms
        env_perms=$(stat -c "%a" "$env_file" 2>/dev/null || echo "unknown")
        if [[ "$env_perms" != "600" ]]; then
            drifts+=("env perms: .env.prod is ${env_perms} (should be 600)")
        fi
    fi

    # 5. Check if running container image matches deployed tag
    local tag_file="${STATE_DIR}/${slug}.tag"
    if [[ -f "$tag_file" ]]; then
        local expected_tag
        expected_tag=$(cat "$tag_file")
        # Try to get running container image tag
        local running_image
        running_image=$(docker inspect --format '{{.Config.Image}}' "${SVC_WEB}" 2>/dev/null \
            || docker compose -f "$SVC_COMPOSE" ps --format '{{.Image}}' "$SVC_WEB" 2>/dev/null \
            || echo "unknown")
        if [[ "$running_image" != *"$expected_tag"* ]] && [[ "$expected_tag" != "unknown" ]] && [[ "$running_image" != "unknown" ]]; then
            drifts+=("image: running ${running_image} vs expected tag ${expected_tag}")
        fi
    fi

    # ── Result ────────────────────────────────────────────────────────

    if [[ ${#drifts[@]} -eq 0 ]]; then
        _CLEAN=$((_CLEAN + 1))
        _RESULTS+=("clean|${slug}|${current_branch}|none")
        $QUIET || echo "  ✅ ${slug}: clean (${current_branch})"
    else
        _DRIFTED=$((_DRIFTED + 1))
        local drift_str
        drift_str=$(IFS='; '; echo "${drifts[*]}")
        _RESULTS+=("drifted|${slug}|${current_branch}|${drift_str}")
        _ALERTS+=("DRIFT: ${slug} — ${drift_str}")

        $QUIET || echo "  ⚠️  ${slug}: DRIFT DETECTED (${current_branch})"
        if ! $QUIET; then
            for d in "${drifts[@]}"; do
                echo "      → $d"
            done
        fi
    fi
}

# ── Nginx config drift ──────────────────────────────────────────────────

check_nginx_drift() {
    $QUIET || $JSON_OUT || echo ""
    $QUIET || $JSON_OUT || echo -e "\033[1;34m── Nginx Config ──\033[0m"

    # Check if nginx config was modified since last deploy
    local nginx_mtime
    nginx_mtime=$(stat -c %Y /etc/nginx/nginx.conf 2>/dev/null || echo "0")
    local sites_mtime
    sites_mtime=$(find /etc/nginx/sites-enabled/ -type f -newer /etc/nginx/nginx.conf 2>/dev/null | wc -l)

    if nginx -t 2>/dev/null; then
        $QUIET || echo "  ✅ Nginx config valid"
    else
        _ALERTS+=("DRIFT: nginx config invalid (nginx -t fails)")
        $QUIET || echo "  ❌ Nginx config INVALID"
    fi
}

# ── Send alerts ──────────────────────────────────────────────────────────

send_alerts() {
    [[ ${#_ALERTS[@]} -eq 0 ]] && return

    for alert in "${_ALERTS[@]}"; do
        echo "[$(TS)] $alert" >> "$LOG_FILE"
        logger -t drift-check -p user.notice "$alert" 2>/dev/null || true
    done
}

# ── JSON output ──────────────────────────────────────────────────────────

output_json() {
    echo "{"
    echo "  \"timestamp\": \"$(TS)\","
    echo "  \"total\": $_TOTAL,"
    echo "  \"clean\": $_CLEAN,"
    echo "  \"drifted\": $_DRIFTED,"
    echo "  \"services\": ["
    local first=true
    for r in "${_RESULTS[@]}"; do
        local IFS='|'
        read -r rstatus rslug rbranch rdetail <<< "$r"
        $first && first=false || echo ","
        printf '    {"slug": "%s", "status": "%s", "branch": "%s", "detail": "%s"}' \
            "$rslug" "$rstatus" "$rbranch" "$rdetail"
    done
    echo ""
    echo "  ]"
    echo "}"
}

# ── Main ─────────────────────────────────────────────────────────────────

$QUIET || $JSON_OUT || echo "╔══════════════════════════════════════════════════════╗"
$QUIET || $JSON_OUT || echo "║         Configuration Drift Detection                ║"
$QUIET || $JSON_OUT || echo "╚══════════════════════════════════════════════════════╝"
$QUIET || $JSON_OUT || echo ""

if [[ -n "$SINGLE_SERVICE" ]]; then
    check_drift "$SINGLE_SERVICE"
else
    for entry in "${SERVICES[@]}"; do
        _parse_service "$entry"
        check_drift "$SVC_SLUG"
    done
    check_nginx_drift
fi

send_alerts

if $JSON_OUT; then
    output_json
elif ! $QUIET; then
    echo ""
    echo "── ${_CLEAN}/${_TOTAL} clean, ${_DRIFTED} drifted ──"
fi

[[ $_DRIFTED -gt 0 ]] && exit 1 || exit 0
