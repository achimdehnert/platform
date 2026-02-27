#!/usr/bin/env bash
# ============================================================================
# health-monitor.sh — Periodic Service Health Monitoring
# ============================================================================
#
# Checks all platform services for:
#   - HTTP health endpoint reachable
#   - Docker container running
#   - Database container responsive
#   - Response time within threshold
#
# Install as cron:
#   */5 * * * * /opt/deploy/scripts/health-monitor.sh --quiet
#
# Alerting:
#   - First failure: logs to health.log + syslog
#   - Consecutive failures: triggers webhook (if configured)
#   - Recovery: logs recovery event
#
# Usage:
#   health-monitor.sh                 # Interactive with full output
#   health-monitor.sh --quiet         # Cron mode (only log on issues)
#   health-monitor.sh --json          # JSON output
#   health-monitor.sh <service>       # Check single service
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
HEALTH_LOG="${STATE_DIR}/health.log"
HEALTH_STATE_DIR="${STATE_DIR}/.health"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"

# Thresholds
HTTP_TIMEOUT=10             # seconds
SLOW_THRESHOLD_MS=3000      # ms — warn if response slower than this
CONSEC_FAIL_ALERT=3         # alert after N consecutive failures

mkdir -p "$STATE_DIR" "$HEALTH_STATE_DIR"

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

_RESULTS=()
_ALERTS=()
_TOTAL=0
_HEALTHY=0
_UNHEALTHY=0

# ── Consecutive failure tracking ─────────────────────────────────────────

get_fail_count() {
    local slug="$1"
    local file="${HEALTH_STATE_DIR}/${slug}.fails"
    [[ -f "$file" ]] && cat "$file" || echo "0"
}

set_fail_count() {
    local slug="$1" count="$2"
    echo "$count" > "${HEALTH_STATE_DIR}/${slug}.fails"
}

was_healthy() {
    local slug="$1"
    local file="${HEALTH_STATE_DIR}/${slug}.fails"
    [[ ! -f "$file" ]] || [[ "$(cat "$file")" == "0" ]]
}

# ── Check one service ────────────────────────────────────────────────────

check_service_health() {
    local slug="$1"
    _find_service "$slug" || return

    _TOTAL=$((_TOTAL + 1))

    local status="healthy"
    local issues=()
    local response_ms="-"

    # 1. HTTP health check
    if _has_field "$SVC_HEALTH"; then
        local http_start http_end http_code
        http_start=$(date +%s%N)

        http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
            --max-time "$HTTP_TIMEOUT" "$SVC_HEALTH" 2>/dev/null || echo "000")

        http_end=$(date +%s%N)
        response_ms=$(( (http_end - http_start) / 1000000 ))

        if [[ "$http_code" == "200" ]] || [[ "$http_code" == "204" ]]; then
            if [[ "$response_ms" -gt "$SLOW_THRESHOLD_MS" ]]; then
                issues+=("slow: ${response_ms}ms")
                status="degraded"
            fi
        else
            issues+=("http: ${http_code}")
            status="unhealthy"
        fi
    fi

    # 2. Docker container check
    local container_running
    container_running=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "^${SVC_WEB}$" || echo "0")
    if [[ "$container_running" -eq 0 ]]; then
        # Also try with project prefix
        container_running=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "${SVC_WEB}" || echo "0")
    fi

    if [[ "$container_running" -eq 0 ]]; then
        issues+=("container: not running")
        status="unhealthy"
    fi

    # 3. DB container check
    if _has_field "$SVC_DB_CTR"; then
        if ! docker exec "$SVC_DB_CTR" pg_isready -q 2>/dev/null; then
            issues+=("db: not ready")
            # Don't override status to unhealthy if only DB is down
            # (might be shared DB container still starting)
            [[ "$status" == "healthy" ]] && status="degraded"
        fi
    fi

    # ── Record result ────────────────────────────────────────────────

    local prev_fails
    prev_fails=$(get_fail_count "$slug")

    if [[ "$status" == "unhealthy" ]]; then
        _UNHEALTHY=$((_UNHEALTHY + 1))
        local new_fails=$((prev_fails + 1))
        set_fail_count "$slug" "$new_fails"

        local issue_str
        issue_str=$(IFS=', '; echo "${issues[*]}")

        # Log every failure
        echo "[$(TS)] UNHEALTHY $slug: $issue_str (consecutive: $new_fails)" >> "$HEALTH_LOG"

        # Alert after N consecutive failures
        if [[ "$new_fails" -ge "$CONSEC_FAIL_ALERT" ]]; then
            _ALERTS+=("🔴 ${slug} DOWN (${new_fails}x): ${issue_str}")
        fi

        $QUIET || echo "  ❌ ${slug}: ${issue_str} (${response_ms}ms, fails: ${new_fails})"
    elif [[ "$status" == "degraded" ]]; then
        _UNHEALTHY=$((_UNHEALTHY + 1))
        local issue_str
        issue_str=$(IFS=', '; echo "${issues[*]}")
        echo "[$(TS)] DEGRADED $slug: $issue_str" >> "$HEALTH_LOG"
        $QUIET || echo "  ⚠️  ${slug}: ${issue_str} (${response_ms}ms)"
        # Don't increment fail counter for degraded
    else
        _HEALTHY=$((_HEALTHY + 1))

        # Recovery detection
        if [[ "$prev_fails" -gt 0 ]]; then
            echo "[$(TS)] RECOVERED $slug (was down for ${prev_fails} check(s))" >> "$HEALTH_LOG"
            _ALERTS+=("✅ ${slug} RECOVERED (was down for ${prev_fails} check(s))")
            $QUIET || echo "  🔄 ${slug}: RECOVERED (${response_ms}ms)"
        else
            $QUIET || echo "  ✅ ${slug}: healthy (${response_ms}ms)"
        fi

        set_fail_count "$slug" 0
    fi

    _RESULTS+=("${status}|${slug}|${response_ms}|$(IFS=', '; echo "${issues[*]:-none}")")
}

# ── Send alerts ──────────────────────────────────────────────────────────

send_alerts() {
    [[ ${#_ALERTS[@]} -eq 0 ]] && return

    local alert_msg
    alert_msg=$(printf '%s\n' "${_ALERTS[@]}")

    # Syslog
    echo "$alert_msg" | while IFS= read -r line; do
        logger -t health-monitor -p user.warning "$line" 2>/dev/null || true
    done

    # Webhook
    if [[ -n "$ALERT_WEBHOOK_URL" ]]; then
        local payload
        payload=$(printf '{"text": "🏥 Health Monitor Alert\\n%s"}' "$alert_msg")
        curl -sf -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" >/dev/null 2>&1 || true
    fi
}

# ── JSON output ──────────────────────────────────────────────────────────

output_json() {
    echo "{"
    echo "  \"timestamp\": \"$(TS)\","
    echo "  \"total\": $_TOTAL,"
    echo "  \"healthy\": $_HEALTHY,"
    echo "  \"unhealthy\": $_UNHEALTHY,"
    echo "  \"alerts\": ${#_ALERTS[@]},"
    echo "  \"services\": ["
    local first=true
    for r in "${_RESULTS[@]}"; do
        local IFS='|'
        read -r rstatus rslug rms rissues <<< "$r"
        $first && first=false || echo ","
        printf '    {"slug": "%s", "status": "%s", "response_ms": "%s", "issues": "%s"}' \
            "$rslug" "$rstatus" "$rms" "$rissues"
    done
    echo ""
    echo "  ]"
    echo "}"
}

# ── Main ─────────────────────────────────────────────────────────────────

$QUIET || $JSON_OUT || echo "╔══════════════════════════════════════════════════════╗"
$QUIET || $JSON_OUT || echo "║         Platform Health Monitor                      ║"
$QUIET || $JSON_OUT || echo "╚══════════════════════════════════════════════════════╝"
$QUIET || $JSON_OUT || echo ""

if [[ -n "$SINGLE_SERVICE" ]]; then
    check_service_health "$SINGLE_SERVICE"
else
    for entry in "${SERVICES[@]}"; do
        _parse_service "$entry"
        check_service_health "$SVC_SLUG"
    done
fi

send_alerts

if $JSON_OUT; then
    output_json
elif ! $QUIET; then
    echo ""
    echo "── ${_HEALTHY}/${_TOTAL} healthy, ${_UNHEALTHY} issues, ${#_ALERTS[@]} alert(s) ──"
fi

[[ $_UNHEALTHY -gt 0 ]] && exit 1 || exit 0
