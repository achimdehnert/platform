#!/usr/bin/env bash
# =============================================================================
# validate-deployment-readiness.sh — Pre-Flight Check für neue App-Deployments
# ADR-056 §2.1 (updated from ADR-054 M1)
#
# Usage:
#   ./scripts/validate-deployment-readiness.sh --repo trading-hub --app trading-hub
#   ./scripts/validate-deployment-readiness.sh --repo cad-hub --app cad-hub --pat ghp_xxx
#
# Requires: curl, ssh, jq
# Optional: actionlint, sops
# =============================================================================
set -euo pipefail

# ── Farben ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

pass()   { echo -e "${GREEN}  ✓${RESET} $*"; }
fail()   { echo -e "${RED}  ✗${RESET} $*"; ERRORS=$((ERRORS+1)); }
warn()   { echo -e "${YELLOW}  ⚠${RESET} $*"; WARNINGS=$((WARNINGS+1)); }
info()   { echo -e "${BLUE}  →${RESET} $*"; }
section(){ echo -e "\n${BOLD}$*${RESET}"; }

ERRORS=0
WARNINGS=0

# ── Argumente ────────────────────────────────────────────────────────────────
REPO=""
APP=""
PAT="${GITHUB_TOKEN:-}"
ORG="achimdehnert"
DEPLOY_HOST="${DEPLOY_HOST:-88.198.191.108}"
DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY:-}"
SSH_KEY_PATH="${HETZNER_SSH_KEY_PATH:-$HOME/.ssh/id_rsa}"
DEPLOY_PATH=""
DOCKERFILE="Dockerfile"
COMPOSE_FILE="docker-compose.prod.yml"

while [[ $# -gt 0 ]]; do
  case $1 in
    --repo)        REPO="$2";        shift 2 ;;
    --app)         APP="$2";         shift 2 ;;
    --pat)         PAT="$2";         shift 2 ;;
    --ssh-key)     SSH_KEY_PATH="$2"; shift 2 ;;
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
# 1. GITHUB CHECKS (Fehlerklasse A)
# =============================================================================
section "1. GitHub Repository Checks (Fehlerklasse A)"

if [[ -z "$PAT" ]]; then
  warn "Kein PAT verfügbar (--pat oder \$GITHUB_TOKEN) — GitHub API-Checks übersprungen"
else
  # 1a: allowed_actions
  info "Prüfe allowed_actions für ${ORG}/${REPO}..."
  ALLOWED=$(curl -sf -H "Authorization: Bearer ${PAT}" \
    "https://api.github.com/repos/${ORG}/${REPO}/actions/permissions" \
    | jq -r '.allowed_actions // "unknown"' 2>/dev/null || echo "error")

  if [[ "$ALLOWED" == "local_only" ]]; then
    fail "allowed_actions = local_only → externe Actions (actions/checkout@v4 etc.) werden NICHT ausgeführt"
    info "Fix: GitHub → ${REPO} → Settings → Actions → General → 'Allow all actions and reusable workflows'"
  elif [[ "$ALLOWED" == "error" ]]; then
    warn "GitHub API nicht erreichbar oder PAT fehlt Berechtigung"
  else
    pass "allowed_actions = ${ALLOWED}"
  fi

  # 1b: Pflicht-Secrets (ADR-056 §2.1 + ADR-021 §2.6)
  info "Prüfe Pflicht-Secrets (DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY)..."
  REQUIRED_SECRETS=("DEPLOY_HOST" "DEPLOY_USER" "DEPLOY_SSH_KEY")
  SECRETS_JSON=$(curl -sf -H "Authorization: Bearer ${PAT}" \
    "https://api.github.com/repos/${ORG}/${REPO}/actions/secrets" \
    | jq -r '[.secrets[].name]' 2>/dev/null || echo "[]")

  for SECRET in "${REQUIRED_SECRETS[@]}"; do
    EXISTS=$(echo "$SECRETS_JSON" | jq -r --arg s "$SECRET" 'index($s) != null' 2>/dev/null || echo "false")
    if [[ "$EXISTS" == "true" ]]; then
      pass "Secret ${SECRET} vorhanden"
    else
      fail "Secret ${SECRET} FEHLT im Repo (ADR-021 §2.6)"
    fi
  done
fi

# 1c: Workflow-Syntax (actionlint)
section "2. Workflow-Syntax (Fehlerklasse C)"
if command -v actionlint &>/dev/null; then
  info "Linting .github/workflows/..."
  if actionlint .github/workflows/*.yml 2>&1 | grep -q "error"; then
    fail "actionlint meldet Fehler in Workflow-Dateien"
  else
    pass "Alle Workflow-Dateien syntaktisch valide"
  fi
  # inputs.* bei push-Trigger (class C anti-pattern)
  if grep -rn 'inputs\.' .github/workflows/*.yml 2>/dev/null | grep -q 'push'; then
    warn "Mögliches inputs.* bei push-Trigger gefunden — prüfe manuell (ADR-056 §2.4 Klasse C)"
  fi
else
  warn "actionlint nicht installiert — Workflow-Syntax nicht geprüft"
  info "Install: https://github.com/rhysd/actionlint#installation"
fi

# =============================================================================
# 2. DOCKERFILE CHECKS (Fehlerklasse B)
# =============================================================================
section "3. Dockerfile Checks (Fehlerklasse B)"

if [[ ! -f "$DOCKERFILE" ]]; then
  fail "Dockerfile nicht gefunden: ${DOCKERFILE}"
else
  pass "Dockerfile gefunden: ${DOCKERFILE}"

  # Cross-Repo COPY
  if grep -qE "^COPY packages/" "$DOCKERFILE" 2>/dev/null; then
    fail "Cross-Repo COPY gefunden: $(grep -E '^COPY packages/' "$DOCKERFILE")"
    info "Fix: platform_context als GHCR-Package installieren (ADR-056 §2.3)"
  else
    pass "Keine Cross-Repo COPY-Referenzen"
  fi

  # wheels/ Pattern
  if grep -qE "COPY.*wheels/" "$DOCKERFILE" 2>/dev/null; then
    warn "wheels/-Pattern gefunden — durch platform_context GHCR-Package ersetzen (ADR-056 §2.3)"
    grep -E "COPY.*wheels/" "$DOCKERFILE" | while read -r line; do info "  $line"; done
  else
    pass "Kein wheels/-Pattern"
  fi

  # SHA-Tag in Compose prüfen
  if [[ -f "$COMPOSE_FILE" ]]; then
    IMAGE_IN_COMPOSE=$(grep -oE "ghcr\.io/[^:\"']+" "$COMPOSE_FILE" | head -1 || echo "")
    if [[ -n "$IMAGE_IN_COMPOSE" ]]; then
      pass "Image in Compose: ${IMAGE_IN_COMPOSE}"
    else
      warn "Kein ghcr.io Image in ${COMPOSE_FILE} — prüfe Image-Pfad"
    fi
  fi
fi

# =============================================================================
# 3. DEPENDENCY CHECKS (Fehlerklasse B)
# =============================================================================
section "4. Dependency Checks (Fehlerklasse B)"

for DEP_FILE in pyproject.toml requirements.txt requirements-dev.txt; do
  [[ ! -f "$DEP_FILE" ]] && continue
  if grep -qE "file://|/home/|/opt/|/srv/" "$DEP_FILE" 2>/dev/null; then
    fail "Absolute lokale Pfade in ${DEP_FILE}:"
    grep -nE "file://|/home/|/opt/|/srv/" "$DEP_FILE" | while read -r line; do info "  $line"; done
    info "Fix: platform_context als GHCR-Package (ADR-056 §2.3)"
  else
    pass "${DEP_FILE}: keine absoluten lokalen Pfade"
  fi
done

# platform_context importierbar?
if command -v python3 &>/dev/null; then
  if python3 -c "import platform_context" &>/dev/null; then
    pass "platform_context importierbar"
  else
    warn "platform_context nicht importierbar — im CI via GHCR-Package installieren (ADR-056 §2.3)"
  fi
fi

# =============================================================================
# 4. SERVER CHECKS via SSH (Fehlerklasse D)
# =============================================================================
section "5. Server Checks (${DEPLOY_HOST}) — Fehlerklasse D"

# SSH known_hosts via ssh-keyscan (kein StrictHostKeyChecking=no — ADR-056 §2.2)
KNOWN_HOSTS_FILE=$(mktemp)
if ssh-keyscan -H "${DEPLOY_HOST}" >> "$KNOWN_HOSTS_FILE" 2>/dev/null; then
  pass "ssh-keyscan für ${DEPLOY_HOST} erfolgreich"
else
  warn "ssh-keyscan fehlgeschlagen — Server-Checks übersprungen"
  rm -f "$KNOWN_HOSTS_FILE"
  KNOWN_HOSTS_FILE=""
fi

SSH_OPTS="-o ConnectTimeout=5 -o UserKnownHostsFile=${KNOWN_HOSTS_FILE} -o BatchMode=yes"
# SSH-Key: aus Argument, Env-Variable oder Standard-Pfad
if [[ -n "$DEPLOY_SSH_KEY" ]]; then
  TMPKEY=$(mktemp)
  echo "$DEPLOY_SSH_KEY" > "$TMPKEY"
  chmod 600 "$TMPKEY"
  SSH_OPTS="$SSH_OPTS -i $TMPKEY"
elif [[ -f "$SSH_KEY_PATH" ]]; then
  SSH_OPTS="$SSH_OPTS -i $SSH_KEY_PATH"
fi

if [[ -n "$KNOWN_HOSTS_FILE" ]] && ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" "echo OK" &>/dev/null; then
  pass "SSH-Verbindung zu ${DEPLOY_HOST} erfolgreich"

  # deploy_path
  if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" "test -d '${DEPLOY_PATH}'" 2>/dev/null; then
    pass "Deploy-Pfad ${DEPLOY_PATH} existiert"
  else
    fail "Deploy-Pfad ${DEPLOY_PATH} existiert NICHT"
    info "Fix: mkdir -p ${DEPLOY_PATH}"
  fi

  # .env.prod
  ENV_FILE="${DEPLOY_PATH}/.env.prod"
  if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" "test -f '${ENV_FILE}'" 2>/dev/null; then
    pass ".env.prod vorhanden"

    # SOPS-Check (ADR-056 §2.1 SOPS note)
    IS_SOPS=$(ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" \
      "head -1 '${ENV_FILE}' | grep -c 'sops' || true" 2>/dev/null || echo "0")
    if [[ "$IS_SOPS" -gt 0 ]]; then
      warn ".env.prod ist SOPS-verschlüsselt — Pflichtfeld-Check via 'sops -d' erforderlich"
      info "Manuell prüfen: sops -d ${ENV_FILE} | grep REQUIRED_KEY"
    else
      REQUIRED_ENV=("POSTGRES_USER" "POSTGRES_PASSWORD" "SECRET_KEY" "ALLOWED_HOSTS")
      for VAR in "${REQUIRED_ENV[@]}"; do
        if ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" "grep -q '^${VAR}=' '${ENV_FILE}'" 2>/dev/null; then
          pass "  .env.prod: ${VAR} gesetzt"
        else
          fail "  .env.prod: ${VAR} FEHLT"
        fi
      done
    fi
  else
    fail ".env.prod fehlt in ${DEPLOY_PATH}"
    info "Fix: Datei nach ${ENV_FILE} kopieren"
  fi

  # Nginx proxy_pass Check
  info "Prüfe Nginx-Konfiguration für ${APP}..."
  NGINX_WRONG=$(ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" \
    "grep -rn 'proxy_pass.*127\.0\.0\.1' /etc/nginx/sites-enabled/ 2>/dev/null | grep -i '${APP}' || true" \
    2>/dev/null || echo "")
  if [[ -n "$NGINX_WRONG" ]]; then
    fail "Nginx proxy_pass auf 127.0.0.1 (Infrastructure Drift):"
    info "  $NGINX_WRONG"
    info "Fix: proxy_pass http://localhost:<port>; oder direkt auf Container-Port"
  else
    pass "Nginx proxy_pass: kein 127.0.0.1-Problem für ${APP}"
  fi

  # Nginx config vorhanden?
  NGINX_CONF=$(ssh $SSH_OPTS "${DEPLOY_USER}@${DEPLOY_HOST}" \
    "ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -i '${APP}' || true" 2>/dev/null || echo "")
  if [[ -n "$NGINX_CONF" ]]; then
    pass "Nginx-Config gefunden: ${NGINX_CONF}"
  else
    warn "Keine Nginx-Config für '${APP}' in /etc/nginx/sites-enabled/ — ggf. anderen Namen prüfen"
  fi

else
  warn "SSH-Verbindung zu ${DEPLOY_HOST} nicht möglich — Server-Checks übersprungen"
fi

# Cleanup
[[ -n "${KNOWN_HOSTS_FILE:-}" ]] && rm -f "$KNOWN_HOSTS_FILE"
[[ -n "${TMPKEY:-}" ]] && rm -f "$TMPKEY"

# =============================================================================
# ZUSAMMENFASSUNG
# =============================================================================
echo -e "\n${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║  Ergebnis                                            ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo -e "  Fehler:    ${RED}${ERRORS}${RESET}"
echo -e "  Warnungen: ${YELLOW}${WARNINGS}${RESET}"

if [[ $ERRORS -eq 0 ]]; then
  echo -e "\n${GREEN}${BOLD}✅ Deployment-Readiness: OK — bereit für ersten Workflow-Run${RESET}\n"
  exit 0
else
  echo -e "\n${RED}${BOLD}❌ Deployment-Readiness: NICHT OK — ${ERRORS} Problem(e) beheben${RESET}\n"
  exit 1
fi
