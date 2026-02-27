#!/usr/bin/env bash
# ============================================================================
# ssl-check.sh — SSL Certificate Expiry Monitoring
# ============================================================================
#
# Checks all platform domains for SSL certificate expiry.
# Warns at 14 days, alerts at 7 days.
#
# Install as cron job:
#   cp ssl-check.sh /etc/cron.daily/ssl-check
#   chmod +x /etc/cron.daily/ssl-check
#
# Alerting:
#   - Logs to syslog (always)
#   - Logs to deploy.log (always)
#   - Optional webhook (set ALERT_WEBHOOK_URL env var)
#
# Usage:
#   ssl-check.sh                  # Check all domains from services.conf
#   ssl-check.sh --verbose        # Show all results (not just warnings)
#   ssl-check.sh --json           # JSON output (for monitoring systems)
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

STATE_DIR="/opt/deploy/production/.deployed"
LOG_FILE="${STATE_DIR}/deploy.log"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"

mkdir -p "$STATE_DIR"

VERBOSE=false
JSON_OUT=false
for arg in "$@"; do
    case "$arg" in
        --verbose) VERBOSE=true ;;
        --json)    JSON_OUT=true ;;
    esac
done

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

WARN_DAYS=14
CRIT_DAYS=7

# ── Tracking ──────────────────────────────────────────────────────────────

_RESULTS=()
_ALERTS=()

check_domain() {
    local domain="$1"
    local expiry_date days_left status

    # Get certificate expiry via openssl
    expiry_date=$(echo | timeout 10 openssl s_client \
        -servername "$domain" \
        -connect "${domain}:443" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null \
        | cut -d= -f2 || echo "")

    if [[ -z "$expiry_date" ]]; then
        status="ERROR"
        days_left=-1
        _RESULTS+=("ERROR|${domain}|Cannot connect or read certificate|-1")
        _ALERTS+=("SSL ERROR: ${domain} — cannot read certificate")
        return
    fi

    # Calculate days remaining
    local expiry_epoch now_epoch
    expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$expiry_date" +%s 2>/dev/null || echo "0")
    now_epoch=$(date +%s)
    days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

    if [[ "$days_left" -lt 0 ]]; then
        status="EXPIRED"
        _ALERTS+=("SSL EXPIRED: ${domain} — expired ${days_left#-} days ago!")
    elif [[ "$days_left" -lt "$CRIT_DAYS" ]]; then
        status="CRITICAL"
        _ALERTS+=("SSL CRITICAL: ${domain} — expires in ${days_left} days ($(date -d "$expiry_date" +%Y-%m-%d))")
    elif [[ "$days_left" -lt "$WARN_DAYS" ]]; then
        status="WARNING"
        _ALERTS+=("SSL WARNING: ${domain} — expires in ${days_left} days ($(date -d "$expiry_date" +%Y-%m-%d))")
    else
        status="OK"
    fi

    _RESULTS+=("${status}|${domain}|${expiry_date}|${days_left}")

    if $VERBOSE || [[ "$status" != "OK" ]]; then
        case "$status" in
            OK)       $JSON_OUT || echo "  ✅ ${domain} — ${days_left} days ($(date -d "$expiry_date" +%Y-%m-%d))" ;;
            WARNING)  $JSON_OUT || echo "  ⚠️  ${domain} — ${days_left} days ($(date -d "$expiry_date" +%Y-%m-%d))" ;;
            CRITICAL) $JSON_OUT || echo "  🔴 ${domain} — ${days_left} days ($(date -d "$expiry_date" +%Y-%m-%d))" ;;
            EXPIRED)  $JSON_OUT || echo "  ❌ ${domain} — EXPIRED!" ;;
            ERROR)    $JSON_OUT || echo "  ❌ ${domain} — connection error" ;;
        esac
    fi
}

# ── Send alerts ──────────────────────────────────────────────────────────

send_alerts() {
    if [[ ${#_ALERTS[@]} -eq 0 ]]; then
        return
    fi

    local alert_msg
    alert_msg=$(printf '%s\n' "${_ALERTS[@]}")

    # Log to syslog
    echo "$alert_msg" | while IFS= read -r line; do
        logger -t ssl-check -p user.warning "$line" 2>/dev/null || true
    done

    # Log to deploy.log
    for alert in "${_ALERTS[@]}"; do
        echo "[$(TS)] $alert" >> "$LOG_FILE"
    done

    # Webhook (if configured)
    if [[ -n "$ALERT_WEBHOOK_URL" ]]; then
        local payload
        payload=$(printf '{"text": "🔒 SSL Certificate Alert\\n%s"}' "$alert_msg")
        curl -sf -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" >/dev/null 2>&1 || true
    fi
}

# ── JSON output ──────────────────────────────────────────────────────────

output_json() {
    echo "{"
    echo "  \"timestamp\": \"$(TS)\","
    echo "  \"warn_threshold_days\": $WARN_DAYS,"
    echo "  \"crit_threshold_days\": $CRIT_DAYS,"
    echo "  \"alert_count\": ${#_ALERTS[@]},"
    echo "  \"certificates\": ["
    local first=true
    for r in "${_RESULTS[@]}"; do
        local IFS='|'
        read -r status domain expiry days <<< "$r"
        $first && first=false || echo ","
        printf '    {"status": "%s", "domain": "%s", "expiry": "%s", "days_left": %s}' \
            "$status" "$domain" "$expiry" "$days"
    done
    echo ""
    echo "  ]"
    echo "}"
}

# ── Main ─────────────────────────────────────────────────────────────────

$JSON_OUT || echo "╔══════════════════════════════════════════════════════╗"
$JSON_OUT || echo "║         SSL Certificate Expiry Check                 ║"
$JSON_OUT || echo "╚══════════════════════════════════════════════════════╝"
$JSON_OUT || echo ""

# Collect all domains from services.conf
if declare -p SERVICES &>/dev/null 2>&1; then
    DOMAINS=($(_all_domains))
else
    # Fallback: hardcoded domains if services.conf not available
    DOMAINS=(
        bfagent.iil.pet
        drifttales.com
        weltenforger.com
        demo.schutztat.de
        devhub.iil.pet
        prezimo.com
        trading-hub.iil.pet
        wedding-hub.iil.pet
        nl2cad.de
    )
fi

for domain in "${DOMAINS[@]}"; do
    check_domain "$domain"
done

send_alerts

if $JSON_OUT; then
    output_json
else
    echo ""
    local ok_count=0 warn_count=0
    for r in "${_RESULTS[@]}"; do
        [[ "$r" == OK* ]] && ok_count=$((ok_count + 1))
        [[ "$r" != OK* ]] && warn_count=$((warn_count + 1))
    done
    echo "── ${#_RESULTS[@]} domains checked, ${#_ALERTS[@]} alert(s) ──"
fi

# Exit with error if any alerts
[[ ${#_ALERTS[@]} -gt 0 ]] && exit 1 || exit 0
