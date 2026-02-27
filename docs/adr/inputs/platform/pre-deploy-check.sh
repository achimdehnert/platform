#!/usr/bin/env bash
# ============================================================================
# pre-deploy-check.sh — Validate server readiness before deploy
# ============================================================================
#
# Runs all pre-deployment checks and returns pass/fail.
# Can be called standalone or sourced by deploy.sh.
#
# Usage:
#   pre-deploy-check.sh <service>    # Check specific service
#   pre-deploy-check.sh --all        # Check entire server
#   pre-deploy-check.sh --json       # Output as JSON
#
# Exit codes:
#   0 = all checks passed
#   1 = critical check failed (do NOT deploy)
#   2 = warnings only (deploy at your risk)
#
# ============================================================================
set -uo pipefail

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

CHECK_ALL=false
JSON_OUT=false
TARGET="${1:---all}"

for arg in "$@"; do
    case "$arg" in
        --all)  CHECK_ALL=true ;;
        --json) JSON_OUT=true ;;
    esac
done

if [[ "$TARGET" != "--all" ]] && [[ "$TARGET" != "--json" ]]; then
    if ! _find_service "$TARGET"; then
        echo "ERROR: Unknown service '$TARGET'. Valid: $(_list_slugs)" >&2
        exit 1
    fi
fi

# ── Tracking ──────────────────────────────────────────────────────────────

_PASS=0
_FAIL=0
_WARN=0
_RESULTS=()

pass() { _PASS=$((_PASS + 1)); _RESULTS+=("PASS|$1"); $JSON_OUT || echo "  ✅ $1"; }
fail() { _FAIL=$((_FAIL + 1)); _RESULTS+=("FAIL|$1"); $JSON_OUT || echo "  ❌ $1"; }
warn() { _WARN=$((_WARN + 1)); _RESULTS+=("WARN|$1"); $JSON_OUT || echo "  ⚠️  $1"; }

section() { $JSON_OUT || echo -e "\n\033[1;34m── $1 ──\033[0m"; }

# ============================================================================
# Global checks (always run)
# ============================================================================

check_system() {
    section "System"

    # Disk usage /
    local usage
    usage=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    if [[ "$usage" -gt 90 ]]; then
        fail "Disk / critical: ${usage}% used (>90%)"
    elif [[ "$usage" -gt 85 ]]; then
        warn "Disk / high: ${usage}% used (>85%)"
    else
        pass "Disk / OK: ${usage}% used"
    fi

    # Disk usage /var/lib/docker
    if df -h /var/lib/docker >/dev/null 2>&1; then
        local docker_usage
        docker_usage=$(df /var/lib/docker | awk 'NR==2{print $5}' | tr -d '%')
        if [[ "$docker_usage" -gt 90 ]]; then
            fail "Disk /var/lib/docker critical: ${docker_usage}% (run: docker system prune)"
        elif [[ "$docker_usage" -gt 80 ]]; then
            warn "Disk /var/lib/docker high: ${docker_usage}%"
        else
            pass "Disk /var/lib/docker OK: ${docker_usage}%"
        fi
    fi

    # Docker daemon
    if docker info >/dev/null 2>&1; then
        pass "Docker daemon running"
    else
        fail "Docker daemon NOT running"
    fi

    # System memory
    local mem_pct
    mem_pct=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ "$mem_pct" -gt 95 ]]; then
        fail "Memory critical: ${mem_pct}% used"
    elif [[ "$mem_pct" -gt 85 ]]; then
        warn "Memory high: ${mem_pct}% used"
    else
        pass "Memory OK: ${mem_pct}% used"
    fi

    # Load average vs CPU count
    local load_1m cpus
    load_1m=$(awk '{print $1}' /proc/loadavg)
    cpus=$(nproc)
    local load_int=${load_1m%%.*}
    if [[ "$load_int" -gt $((cpus * 2)) ]]; then
        warn "Load high: ${load_1m} (${cpus} CPUs)"
    else
        pass "Load OK: ${load_1m} (${cpus} CPUs)"
    fi

    # Nginx running
    if systemctl is-active nginx >/dev/null 2>&1; then
        pass "Nginx running"
        # Config valid
        if nginx -t 2>/dev/null; then
            pass "Nginx config valid"
        else
            warn "Nginx config has warnings"
        fi
    else
        warn "Nginx not running"
    fi

    # Dangling images (cleanup indicator)
    local dangling
    dangling=$(docker images -f "dangling=true" -q | wc -l)
    if [[ "$dangling" -gt 20 ]]; then
        warn "Docker: $dangling dangling images (run: docker image prune)"
    elif [[ "$dangling" -gt 0 ]]; then
        pass "Docker: $dangling dangling images"
    fi
}

# ============================================================================
# Per-service checks
# ============================================================================

check_service() {
    local slug="$1"
    _find_service "$slug" || return

    section "Service: $SVC_SLUG"

    # Deploy path
    if [[ -d "$SVC_PATH" ]]; then
        pass "Deploy path: $SVC_PATH"
    else
        fail "Deploy path missing: $SVC_PATH"
        return
    fi

    # Compose file
    local compose="${SVC_PATH}/${SVC_COMPOSE}"
    if [[ -f "$compose" ]]; then
        if docker compose -f "$compose" config --quiet 2>/dev/null; then
            pass "Compose file valid: $SVC_COMPOSE"
        else
            fail "Compose file INVALID: $SVC_COMPOSE"
        fi
    else
        fail "Compose file missing: $compose"
    fi

    # Env file
    local env_file="${SVC_PATH}/.env.prod"
    if [[ -f "$env_file" ]]; then
        # Check basic required vars
        local missing_vars=()
        for key in SECRET_KEY DATABASE_URL; do
            if ! grep -q "^${key}=" "$env_file" 2>/dev/null; then
                missing_vars+=("$key")
            fi
        done
        if [[ ${#missing_vars[@]} -gt 0 ]]; then
            warn "Env vars missing from .env.prod: ${missing_vars[*]}"
        else
            pass "Env file OK: .env.prod"
        fi
    else
        warn "No .env.prod found"
    fi

    # Container running
    local web_status
    web_status=$(docker compose -f "$compose" ps --format json "$SVC_WEB" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('State','unknown'))" 2>/dev/null || echo "unknown")
    if [[ "$web_status" == "running" ]]; then
        pass "Container running: $SVC_WEB"
    else
        warn "Container not running: $SVC_WEB (state=$web_status)"
    fi

    # DB reachable
    if _has_field "$SVC_DB_CTR"; then
        if docker exec "$SVC_DB_CTR" pg_isready -q 2>/dev/null; then
            pass "Database reachable: $SVC_DB_CTR"
        else
            warn "Database not reachable: $SVC_DB_CTR"
        fi
    fi

    # Health URL
    if _has_field "$SVC_HEALTH"; then
        if curl -sf --max-time 5 "$SVC_HEALTH" >/dev/null 2>&1; then
            pass "Health OK: $SVC_HEALTH"
        else
            warn "Health FAIL: $SVC_HEALTH"
        fi
    fi

    # Git status (drift detection)
    if [[ -d "${SVC_PATH}/.git" ]]; then
        local git_status
        git_status=$(cd "$SVC_PATH" && git status --porcelain 2>/dev/null | wc -l)
        if [[ "$git_status" -eq 0 ]]; then
            pass "Git clean: no uncommitted changes"
        else
            warn "Git dirty: $git_status uncommitted file(s) in $SVC_PATH"
        fi
    fi
}

# ============================================================================
# Output
# ============================================================================

output_json() {
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"passed\": $_PASS,"
    echo "  \"failed\": $_FAIL,"
    echo "  \"warnings\": $_WARN,"
    echo "  \"deploy_safe\": $([ $_FAIL -eq 0 ] && echo "true" || echo "false"),"
    echo "  \"checks\": ["
    local first=true
    for result in "${_RESULTS[@]}"; do
        local status="${result%%|*}" msg="${result#*|}"
        $first && first=false || echo ","
        printf '    {"status": "%s", "message": "%s"}' "$status" "$msg"
    done
    echo ""
    echo "  ]"
    echo "}"
}

# ============================================================================
# Main
# ============================================================================

$JSON_OUT || echo "╔══════════════════════════════════════════════════════╗"
$JSON_OUT || echo "║         Pre-Deploy Validation Check                  ║"
$JSON_OUT || echo "╚══════════════════════════════════════════════════════╝"

check_system

if $CHECK_ALL || [[ "$TARGET" == "--all" ]] || [[ "$TARGET" == "--json" ]]; then
    for entry in "${SERVICES[@]}"; do
        _parse_service "$entry"
        check_service "$SVC_SLUG"
    done
else
    check_service "$TARGET"
fi

if $JSON_OUT; then
    output_json
else
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  ✅ Passed: $_PASS    ❌ Failed: $_FAIL    ⚠️  Warnings: $_WARN"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    if [[ $_FAIL -gt 0 ]]; then
        echo "  ⛔ DEPLOY BLOCKED — $_FAIL critical issue(s)"
    elif [[ $_WARN -gt 0 ]]; then
        echo "  ⚠️  Deploy OK with warnings"
    else
        echo "  🎉 All clear — safe to deploy"
    fi
    echo ""
fi

if [[ $_FAIL -gt 0 ]]; then
    exit 1
elif [[ $_WARN -gt 0 ]]; then
    exit 2
else
    exit 0
fi
