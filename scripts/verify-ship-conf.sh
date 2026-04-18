#!/usr/bin/env bash
# verify-ship-conf.sh — Verify .ship.conf consistency across all repos (ADR-120)
# Usage: bash scripts/verify-ship-conf.sh [--fix]
#
# Checks:
# 1. Every deployable repo has .ship.conf
# 2. Every .ship.conf has all required fields
# 3. HEALTH_URL ends with /healthz/ (ADR-022)
# 4. IMAGE uses nested pattern (repo/repo-web, no :latest)
# 5. ship.sh is thin-wrapper (delegates to platform)
# 6. .ship.conf HEALTH_URL matches repos.json health_url (KG consistency)
set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
REPOS_JSON="$GITHUB_DIR/mcp-hub/platform_context_mcp/graph/repos.json"
REQUIRED_FIELDS="APP_NAME IMAGE DOCKERFILE WEB_SERVICE SERVER COMPOSE_PATH COMPOSE_FILE HEALTH_URL MIGRATE_CMD"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
errors=0; warnings=0; ok=0

echo "═══ .ship.conf Verification (ADR-120) ═══"
echo "GitHub dir: $GITHUB_DIR"
echo ""

for repo_dir in "$GITHUB_DIR"/*/; do
  repo=$(basename "$repo_dir")
  conf="$repo_dir/.ship.conf"
  compose="$repo_dir/docker-compose.prod.yml"
  ship="$repo_dir/scripts/ship.sh"

  # Skip non-deployable repos (no compose file)
  [ ! -f "$compose" ] && continue

  echo -n "[$repo] "

  # Check 1: .ship.conf exists
  if [ ! -f "$conf" ]; then
    echo -e "${RED}MISSING .ship.conf${NC}"
    errors=$((errors + 1))
    continue
  fi

  # Source the conf
  source "$conf" 2>/dev/null

  # Check 2: Required fields
  missing=""
  for field in $REQUIRED_FIELDS; do
    val=$(grep "^${field}=" "$conf" | cut -d= -f2 | tr -d '"')
    [ -z "$val" ] && missing="$missing $field"
  done
  if [ -n "$missing" ]; then
    echo -e "${RED}MISSING FIELDS:$missing${NC}"
    errors=$((errors + 1))
    continue
  fi

  # Check 3: HEALTH_URL ends with /healthz/
  health=$(grep "^HEALTH_URL=" "$conf" | cut -d= -f2 | tr -d '"')
  if [[ "$health" != *"/healthz/" ]]; then
    echo -e "${YELLOW}HEALTH=$health (should end with /healthz/)${NC}"
    warnings=$((warnings + 1))
  fi

  # Check 4: IMAGE pattern (nested, no :latest)
  image=$(grep "^IMAGE=" "$conf" | cut -d= -f2 | tr -d '"')
  if [[ "$image" == *":latest"* ]]; then
    echo -e "${RED}IMAGE has :latest — forbidden in PROD (ADR-120)${NC}"
    errors=$((errors + 1))
  fi
  if [[ ! "$image" =~ /[a-z0-9_-]+-web$ ]]; then
    echo -e "${YELLOW}IMAGE=$image (expected nested pattern: repo/repo-web)${NC}"
    warnings=$((warnings + 1))
  fi

  # Check 5: ship.sh is thin-wrapper
  if [ -f "$ship" ]; then
    if ! grep -q "platform/scripts/ship.sh" "$ship" 2>/dev/null; then
      echo -e "${YELLOW}ship.sh is standalone (should delegate to platform)${NC}"
      warnings=$((warnings + 1))
    fi
  fi

  # Check 6: KG consistency (if repos.json exists)
  if [ -f "$REPOS_JSON" ]; then
    kg_health=$(python3 -c "
import json
with open('$REPOS_JSON') as f:
  r = json.load(f)
print(r.get('$repo', {}).get('health_url', ''))
" 2>/dev/null)
    if [ -n "$kg_health" ] && [ "$kg_health" != "$health" ]; then
      echo -e "${YELLOW}KG DRIFT: .ship.conf=$health vs repos.json=$kg_health${NC}"
      warnings=$((warnings + 1))
    fi
  fi

  echo -e "${GREEN}OK${NC}"
  ok=$((ok + 1))
done

echo ""
echo "═══ Results: ${ok} OK, ${warnings} warnings, ${errors} errors ═══"
[ $errors -gt 0 ] && exit 1
exit 0
