#!/usr/bin/env bash
# =============================================================================
# subdomain-health-check.sh — iil.pet Platform Subdomain Monitor
# =============================================================================
# Checks all registered subdomains for HTTP 200/3xx responses.
# Alerts via Discord webhook on failure.
#
# Usage:
#   ./subdomain-health-check.sh           # run check, exit 1 if any fail
#   ./subdomain-health-check.sh --quiet   # only print failures
#
# Cron (täglich 06:00):
#   0 6 * * * /opt/scripts/subdomain-health-check.sh >> /var/log/subdomain-health.log 2>&1
#
# Environment variables:
#   DISCORD_WEBHOOK_URL  — optional, send alert on failure
# =============================================================================

set -euo pipefail

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
FAILED=()
CHECKED=0

# ---------------------------------------------------------------------------
# Domain list — add new subdomains here when registering them
# Format: "URL|Service-Name"
# RULE: Every entry here needs BOTH a CF DNS record AND an Nginx server_name!
# ---------------------------------------------------------------------------
DOMAINS=(
  "https://outline.iil.pet|Outline Wiki"
  "https://knowledge.iil.pet|Outline Wiki (Alias)"
  "https://bfagent.iil.pet|BF Agent"
  "https://billing.iil.pet|Billing Hub"
  "https://control-center.iil.pet|Control Center"
  "https://devhub.iil.pet|Dev Hub"
  "https://docs.iil.pet|Docs"
  # "https://governance.iil.pet|Governance"  # NOT DEPLOYED — no container running
  "https://id.iil.pet|Authentik SSO"
  "https://illustration.iil.pet/livez/|Illustration Hub"
  "https://trading-hub.iil.pet|Trading Hub"
  # "https://travel.schutztat.de|Travel Beat"  # No public iil.pet domain, runs via Caddy on 8089 directly
  "https://wedding-hub.iil.pet/accounts/login/|Wedding Hub"
  "https://writing-hub.iil.pet|Writing Hub"
  "https://writing.iil.pet|Writing Hub (Alias)"
  # "https://staging.writing.iil.pet|Writing Hub Staging"  # 400: ALLOWED_HOSTS or missing web container
  "https://dms.iil.pet|DMS Hub"
  # "https://eng.iil.pet|Eng Hub"  # NOT DEPLOYED — no container/nginx config
  "https://hr.iil.pet|HR Hub"
  "https://grafana.iil.pet|Grafana"
  "https://iil.pet|iil.pet Root"
)

# ---------------------------------------------------------------------------
# Check each domain
# ---------------------------------------------------------------------------
[[ "$QUIET" -eq 0 ]] && echo "[$TIMESTAMP] Subdomain Health Check — ${#DOMAINS[@]} domains"

for entry in "${DOMAINS[@]}"; do
  URL="${entry%%|*}"
  NAME="${entry##*|}"
  CHECKED=$((CHECKED + 1))

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 15 \
    --connect-timeout 5 \
    --location \
    "$URL" 2>/dev/null || echo "000")

  if [[ "$HTTP_CODE" -ge 200 && "$HTTP_CODE" -lt 400 ]]; then
    [[ "$QUIET" -eq 0 ]] && echo "  ✅ $HTTP_CODE  $NAME ($URL)"
  else
    echo "  ❌ $HTTP_CODE  $NAME ($URL)"
    FAILED+=("$NAME ($URL) → HTTP $HTTP_CODE")
  fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "[$TIMESTAMP] Result: $((CHECKED - ${#FAILED[@]}))/${CHECKED} OK, ${#FAILED[@]} failed"

if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo ""
  echo "FAILURES:"
  for f in "${FAILED[@]}"; do
    echo "  - $f"
  done

  # Discord alert (optional)
  if [[ -n "${DISCORD_WEBHOOK_URL:-}" ]]; then
    PAYLOAD=$(printf '{"content":"🚨 **Subdomain Health Check FAILED** (%s)\n%s"}' \
      "$TIMESTAMP" \
      "$(printf -- '• %s\n' "${FAILED[@]}")")
    curl -s -X POST "$DISCORD_WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" > /dev/null 2>&1 || true
  fi

  exit 1
fi

exit 0
