#!/usr/bin/env bash
# smoke-test.sh — ADR-057 §2.11 post-deployment smoke tests
# Usage: ./scripts/smoke-test.sh <base-url> [login-path]
#
# login-path defaults:
#   /accounts/login/  — allauth (weltenhub, travel-beat, risk-hub)
#   /login/           — Django built-in (bfagent)
#
# Examples:
#   ./scripts/smoke-test.sh https://weltenforger.com
#   ./scripts/smoke-test.sh https://bfagent.iil.pet /login/
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
pass() { echo -e "${GREEN}  ✓${RESET} $*"; }
fail() { echo -e "${RED}  ✗${RESET} $*"; exit 1; }

BASE_URL="${1:?Usage: smoke-test.sh <base-url> [login-path]}"
LOGIN_PATH="${2:-/accounts/login/}"

echo -e "\n${BOLD}=== Smoke Tests: ${BASE_URL} ===${RESET}"

# 1. Liveness check
curl --fail --silent --max-time 10 -o /dev/null "${BASE_URL}/livez/" \
  && pass "/livez/" \
  || fail "/livez/ returned non-200"

# 2. Homepage
curl --fail --silent --max-time 10 -o /dev/null "${BASE_URL}/" \
  && pass "/" \
  || fail "/ returned non-200"

# 3. Login page with CSRF token
BODY=$(curl --fail --silent --max-time 10 "${BASE_URL}${LOGIN_PATH}" || echo "")
echo "${BODY}" | grep -q "csrfmiddlewaretoken" \
  && pass "${LOGIN_PATH} (CSRF token present)" \
  || fail "${LOGIN_PATH} missing csrfmiddlewaretoken"

echo -e "\n${GREEN}${BOLD}=== All smoke tests passed ===${RESET}\n"
