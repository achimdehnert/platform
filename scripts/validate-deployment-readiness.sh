#!/usr/bin/env bash
# =============================================================================
# validate-deployment-readiness.sh — Pre-Flight Check für neue App-Deployments
# ADR-054 M1 Teil A
#
# Usage:
#   ./scripts/validate-deployment-readiness.sh --repo trading-hub --app trading-hub
#   ./scripts/validate-deployment-readiness.sh --repo cad-hub --app cad-hub --pat ghp_xxx
#
# Requires: curl, ssh, actionlint (optional), jq
# =============================================================================
set -euo pipefail

# ── Farben ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

pass()  { echo -e "${GREEN}  ✓${RESET} $*"; }
fail()  { echo -e "${RED}  ✗${RESET} $*"; ERRORS=$((ERRORS+1)); }
warn()  { echo -e "${YELLOW}  ⚠${RESET} $*"; WARNINGS=$((WARNINGS+1)); }
info()  { echo -e "${BLUE}  →${RESET} $*"; }
section(){ echo -e "\n${BOLD}$*${RESET}"; }

ERRORS=0
WARNINGS=0

# ── Argumente ────────────────────────────────────────────────────────────────
REPO=""
APP=""
PAT="${GITHUB_TOKEN:-}"
ORG="achimdehnert"
DEPLOY_SERVER="46.225.113.1"
DEPLOY_USER="deploy"
SSH_KEY="${HETZNER_SSH_KEY_PATH:-$HOME/.ssh/id_rsa}"
DEPLOY_PATH=""
DOCKERFILE="Dockerfile"
COMPOSE_FILE="docker-compose.prod.yml"

while [[ $# -gt 0 ]]; do
  case $1 in
    --repo)    REPO="$2";        shift 2 ;;
    --app)     APP="$2";         shift 2 ;;
    --pat)     PAT="$2";         shift 2 ;;
    --ssh-key) SSH_KEY="$2";     shift 2 ;;
    --deploy-path) DEPLOY_PATH="$2"; shift 2 ;;
    --dockerfile)  DOCKERFILE="$2";  shift 2 ;;
    --compose)     COMPOSE_FILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

[[ -z "$REPO" ]] && { echo "Usage: $0 --repo <repo> --app <app> [--pat <token>]"; exit 1; }
[[ -z "$APP"  ]] && APP="$REPO"
[[ -z "$DEPLOY_PATH" ]] && DEPLOY_PATH="/opt/${APP}"

echo -e "\n${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║  Pre-Flight Validation: ${REPO}${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"

# =============================================================================
# 1. GITHUB CHECKS (benötigt PAT)
# =============================================================================
section "1. GitHub Repository Checks"

if [[ -z "$PAT" ]]; then
  warn "Kein PAT verfügbar (--pat oder \$GITHUB_TOKEN) — GitHub API-Checks übersprungen"
else
  # 1a: allowed_actions
  info "Prüfe allowed_actions für ${ORG}/${REPO}..."
  ALLOWED=$(curl -sf -H "Authorization: Bearer ${PAT}" \
    "https://api.github.com/repos/${ORG}/${REPO}/actions/permissions" \
    | jq -r '.allowed_actions // "unknown"' 2>/dev/null || echo "error")

  if [[ "$ALLOWED" == "local_only" ]]; then
    fail "allowed_actions = local_only → Reusable Workflows aus platform@main werden NICHT ausgeführt"
    info "Fix: GitHub → ${REPO} → Settings → Actions → General → 'Allow all actions'"
  elif [[ "$ALLOWED" == "error" ]]; then
    warn "GitHub API nicht erreichbar oder PAT fehlt Berechtigung"
  else
    pass "allowed_actions = ${ALLOWED}"
  fi

  # 1b: Secrets vorhanden (presence check, nicht Wert)
  info "Prüfe Pflicht-Secrets..."
  REQUIRED_SECRETS=("HETZNER_HOST" "HETZNER_USER" "HETZNER_SSH_KEY" "GHCR_TOKEN")
  SECRETS_JSON=$(curl -sf -H "Authorization: Bearer ${PAT}" \
    "https://api.github.com/repos/${ORG}/${REPO}/actions/secrets" \
    | jq -r '[.secrets[].name]' 2>/dev/null || echo "[]")

  for SECRET in "${REQUIRED_SECRETS[@]}"; do
    EXISTS=$(echo "$SECRETS_JSON" | jq -r --arg s "$SECRET" 'index($s) != null' 2>/dev/null || echo "false")
    if [[ "$EXISTS" == "true" ]]; then
      pass "Secret ${SECRET} vorhanden"
    else
      fail "Secret ${SECRET} FEHLT im Repo"
    fi
  done
fi

# 1c: Workflow-Syntax (actionlint)
section "2. Workflow-Syntax"
if command -v actionlint &>/dev/null; then
  info "Linting .github/workflows/..."
  if actionlint .github/workflows/*.yml 2>&1 | grep -q "error"; then
    fail "actionlint meldet Fehler in Workflow-Dateien"
  else
    pass "Alle Workflow-Dateien syntaktisch valide"
  fi
else
  warn "actionlint nicht installiert — Workflow-Syntax nicht geprüft"
  info "Install: https://github.com/rhysd/actionlint#installation"
fi

# =============================================================================
# 2. DOCKERFILE CHECKS
# =============================================================================
section "3. Dockerfile Checks"

if [[ ! -f "$DOCKERFILE" ]]; then
  fail "Dockerfile nicht gefunden: ${DOCKERFILE}"
else
  pass "Dockerfile gefunden"

  # Cross-Repo COPY
  if grep -qE "^COPY packages/" "$DOCKERFILE" 2>/dev/null; then
    fail "Cross-Repo COPY gefunden: $(grep -E '^COPY packages/' "$DOCKERFILE")"
    info "Fix: platform_context als Package installieren (ADR-054 M4)"
  else
    pass "Keine Cross-Repo COPY-Referenzen"
  fi

  # Absolute lokale Pfade in wheels/
  if grep -qE "COPY.*wheels/" "$DOCKERFILE" 2>/dev/null; then
    warn "wheels/-Pattern gefunden — wird durch platform_context Package ersetzt (ADR-054 M4)"
    grep -E "COPY.*wheels/" "$DOCKERFILE" | while read -r line; do
      info "  $line"
    done
  else
    pass "Kein wheels/-Pattern"
  fi

  # Image-Name in Compose prüfen
  if [[ -f "$COMPOSE_FILE" ]]; then
    IMAGE_IN_COMPOSE=$(grep -oE "ghcr\.io/[^:\"']+" "$COMPOSE_FILE" | head -1 || echo "")
    if [[ -n "$IMAGE_IN_COMPOSE" ]]; then
      pass "Image in Compose: ${IMAGE_IN_COMPOSE}"
    else
      warn "Kein ghcr.io Image-Referenz in ${COMPOSE_FILE} gefunden"
    fi
  fi
fi

# =============================================================================
# 3. PYPROJECT / REQUIREMENTS CHECKS
# =============================================================================
section "4. Dependency Checks"

for DEP_FILE in pyproject.toml requirements.txt requirements-dev.txt; do
  [[ ! -f "$DEP_FILE" ]] && continue
  if grep -qE "file://|/home/|/opt/|/srv/" "$DEP_FILE" 2>/dev/null; then
    fail "Absolute lokale Pfade in ${DEP_FILE}:"
    grep -nE "file://|/home/|/opt/|/srv/" "$DEP_FILE" | while read -r line; do
      info "  $line"
    done
    info "Fix: platform_context als Package installieren (ADR-054 M4)"
  else
    pass "${DEP_FILE}: keine absoluten lokalen Pfade"
  fi
done

# =============================================================================
# 4. SERVER CHECKS (SSH)
# =============================================================================
section "5. Server Checks (${DEPLOY_SERVER})"

SSH_OPTS="-o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes"
[[ -f "$SSH_KEY" ]] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"

if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_SERVER}" "echo OK" &>/dev/null; then
  pass "SSH-Verbindung zu ${DEPLOY_SERVER} erfolgreich"

  # deploy_path existiert
  if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_SERVER}" "test -d '${DEPLOY_PATH}'" 2>/dev/null; then
    pass "Deploy-Pfad ${DEPLOY_PATH} existiert"
  else
    fail "Deploy-Pfad ${DEPLOY_PATH} existiert NICHT"
    info "Fix: sudo mkdir -p ${DEPLOY_PATH} && sudo chown deploy:deploy ${DEPLOY_PATH}"
  fi

  # .env.prod vorhanden und Pflichtfelder
  ENV_FILE="${DEPLOY_PATH}/.env.prod"
  if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_SERVER}" "test -f '${ENV_FILE}'" 2>/dev/null; then
    pass ".env.prod vorhanden"
    REQUIRED_ENV=("POSTGRES_USER" "POSTGRES_PASSWORD" "SECRET_KEY" "ALLOWED_HOSTS")
    for VAR in "${REQUIRED_ENV[@]}"; do
      if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_SERVER}" "grep -q '^${VAR}=' '${ENV_FILE}'" 2>/dev/null; then
        pass "  .env.prod: ${VAR} gesetzt"
      else
        fail "  .env.prod: ${VAR} FEHLT"
      fi
    done
  else
    fail ".env.prod fehlt in ${DEPLOY_PATH}"
    info "Fix: Datei nach ${ENV_FILE} kopieren"
  fi

  # Nginx proxy_pass Check
  info "Prüfe Nginx proxy_pass Konfiguration..."
  NGINX_WRONG=$(ssh $SSH_OPTS "root@88.198.191.108" \
    "grep -rn 'proxy_pass.*127\.0\.0\.1' /etc/nginx/sites-enabled/ 2>/dev/null | grep -i '${APP}' || true" \
    2>/dev/null || echo "")
  if [[ -n "$NGINX_WRONG" ]]; then
    fail "Nginx proxy_pass auf 127.0.0.1 statt 46.225.113.1:"
    info "  $NGINX_WRONG"
    info "Fix: proxy_pass http://46.225.113.1:<port>;"
  else
    pass "Nginx proxy_pass: kein 127.0.0.1-Problem gefunden"
  fi

else
  warn "SSH-Verbindung zu ${DEPLOY_SERVER} nicht möglich — Server-Checks übersprungen"
  info "Prüfe SSH-Key: ${SSH_KEY}"
fi

# =============================================================================
# ZUSAMMENFASSUNG
# =============================================================================
echo -e "\n${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║  Ergebnis                                            ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo -e "  Fehler:   ${RED}${ERRORS}${RESET}"
echo -e "  Warnungen: ${YELLOW}${WARNINGS}${RESET}"

if [[ $ERRORS -eq 0 ]]; then
  echo -e "\n${GREEN}${BOLD}✅ Deployment-Readiness: OK — bereit für ersten Workflow-Run${RESET}\n"
  exit 0
else
  echo -e "\n${RED}${BOLD}❌ Deployment-Readiness: NICHT OK — ${ERRORS} Problem(e) beheben${RESET}\n"
  exit 1
fi
