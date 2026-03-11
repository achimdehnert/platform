#!/usr/bin/env bash
# /opt/scripts/deploy.sh — iil-Platform Unified Deploy Script (ADR-120)
# Auf PROD (88.198.191.108) und DEV/Staging (46.225.113.1) installieren
#
# Usage: deploy.sh <APP_NAME> <APP_PATH> <IMAGE_TAG> <ENVIRONMENT> [HEALTH_CHECK_URL]
# Example: deploy.sh risk-hub /opt/risk-hub v1.4.2 production https://schutztat.de/healthz/
set -euo pipefail

APP_NAME="${1:?'APP_NAME fehlt'}"
APP_PATH="${2:?'APP_PATH fehlt'}"
IMAGE_TAG="${3:?'IMAGE_TAG fehlt'}"
ENVIRONMENT="${4:?'ENVIRONMENT fehlt (staging|production)'}"
HEALTH_CHECK_URL="${5:-}"

LOG_DIR="/var/log/iil-deploys"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${APP_NAME}_$(date +%Y%m%d_%H%M%S)_$$.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Validierung
[[ "$ENVIRONMENT" =~ ^(staging|production)$ ]] || { echo "FEHLER: ENVIRONMENT ungültig: $ENVIRONMENT" >&2; exit 1; }
[[ -d "$APP_PATH" ]] || { echo "FEHLER: $APP_PATH existiert nicht" >&2; exit 2; }
[[ -f "$APP_PATH/docker-compose.yml" || -f "$APP_PATH/docker-compose.prod.yml" ]] || {
  echo "FEHLER: Kein Compose-File in $APP_PATH" >&2; exit 3;
}

# Vorherigen Tag für Rollback speichern
PREVIOUS_TAG=""
if [[ -f "$APP_PATH/.env" ]]; then
  PREVIOUS_TAG=$(grep "^IMAGE_TAG=" "$APP_PATH/.env" | cut -d= -f2 || true)
fi

# Compose-File nach Umgebung wählen (ADR-022: docker-compose.prod.yml für Production)
COMPOSE_FILE="docker-compose.yml"
if [[ "$ENVIRONMENT" == "production" && -f "$APP_PATH/docker-compose.prod.yml" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
fi

# Staging: eigenes Compose-Projekt um DEV-Container nicht zu überschreiben
if [[ "$ENVIRONMENT" == "staging" ]]; then
  export COMPOSE_PROJECT_NAME="staging-${APP_NAME}"
fi

# Rollback-Funktion
rollback() {
  local ec=$?
  if [[ -n "$PREVIOUS_TAG" && "$PREVIOUS_TAG" != "$IMAGE_TAG" ]]; then
    echo "❌ Deploy fehlgeschlagen (exit $ec) — Rollback auf $PREVIOUS_TAG"
    cd "$APP_PATH"
    export IMAGE_TAG="$PREVIOUS_TAG"
    docker compose -f "$COMPOSE_FILE" up -d --force-recreate 2>&1 || {
      echo "KRITISCH: Rollback fehlgeschlagen! Manuell: IMAGE_TAG=$PREVIOUS_TAG docker compose -f $COMPOSE_FILE up -d" >&2
      exit 10
    }
    echo "⚠️  Rollback auf $PREVIOUS_TAG erfolgreich"
  fi
  exit "$ec"
}
trap rollback ERR

echo "═══════════════════════════════════════════════"
echo "iil-Platform Deploy — ADR-120"
echo "App:  $APP_NAME"
echo "Env:  $ENVIRONMENT"
echo "Tag:  $IMAGE_TAG"
[[ -n "$PREVIOUS_TAG" ]] && echo "Prev: $PREVIOUS_TAG"
echo "═══════════════════════════════════════════════"

# IMAGE_TAG in .env schreiben
if [[ -f "$APP_PATH/.env" ]] && grep -q "^IMAGE_TAG=" "$APP_PATH/.env"; then
  sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${IMAGE_TAG}|" "$APP_PATH/.env"
else
  echo "IMAGE_TAG=${IMAGE_TAG}" >> "$APP_PATH/.env"
fi

# GHCR Login (Token aus /opt/scripts/.ghcr_token falls vorhanden)
if [[ -f "/opt/scripts/.ghcr_token" ]]; then
  docker login ghcr.io -u achimdehnert --password-stdin < /opt/scripts/.ghcr_token
fi

# Deploy
cd "$APP_PATH"
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans

# Health-Check (nur HTTP 200 — ADR-022: /healthz/ Pflicht)
if [[ -n "$HEALTH_CHECK_URL" ]]; then
  echo "Health-Check: $HEALTH_CHECK_URL"
  for i in $(seq 1 12); do
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
      echo "✅ Health-Check OK (Versuch $i)"
      break
    fi
    echo "⏳ Versuch $i/12 — HTTP $HTTP_CODE"
    sleep 5
    [[ $i -eq 12 ]] && { echo "❌ Health-Check fehlgeschlagen nach 60s"; exit 4; }
  done
else
  sleep 5
  docker compose -f "$COMPOSE_FILE" ps | grep -qi "unhealthy\|exit\|error" && {
    echo "❌ Container in Fehlerzustand"
    exit 5
  }
  echo "✅ Container läuft"
fi

# Cleanup: nur dangling (ungetaggte) Images — nicht zu aggressiv
docker image prune -f 2>/dev/null || true

trap - ERR
echo "═══════════════════════════════════════════════"
echo "✅ Deploy erfolgreich: $APP_NAME:$IMAGE_TAG ($ENVIRONMENT)"
echo "═══════════════════════════════════════════════"
