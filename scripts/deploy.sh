#!/usr/bin/env bash
# /opt/scripts/deploy.sh — iil-Platform Unified Deploy Script (ADR-120, ADR-166)
# Auf PROD (88.198.191.108) und DEV/Staging (88.99.38.75) installieren
#
# Usage: deploy.sh <APP_NAME> <APP_PATH> <IMAGE_TAG> <ENVIRONMENT> [HEALTH_CHECK_URL]
# Example: deploy.sh risk-hub /opt/risk-hub v1.4.2 production https://schutztat.de/livez/
set -euo pipefail

APP_NAME="${1:?'APP_NAME fehlt'}"
APP_PATH="${2:?'APP_PATH fehlt'}"
IMAGE_TAG="${3:?'IMAGE_TAG fehlt'}"
ENVIRONMENT="${4:?'ENVIRONMENT fehlt (staging|production)'}"
HEALTH_CHECK_URL="${5:-}"

# ADR-160: log to file only if writable — never break deploy for logging
LOG_DIR="/var/log/iil-deploys"
mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG_FILE="$LOG_DIR/${APP_NAME}_$(date +%Y%m%d_%H%M%S)_$$.log"
if touch "$LOG_FILE" 2>/dev/null; then
  exec > >(tee -a "$LOG_FILE" 2>/dev/null || cat) 2>&1
fi

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

# Compose-File nach Umgebung wählen (ADR-022)
# Production: docker-compose.prod.yml
# Staging:    docker-compose.staging.yml
# Fallback:   docker-compose.yml
COMPOSE_FILE="docker-compose.yml"
if [[ "$ENVIRONMENT" == "production" && -f "$APP_PATH/docker-compose.prod.yml" ]]; then
  COMPOSE_FILE="docker-compose.prod.yml"
elif [[ "$ENVIRONMENT" == "staging" && -f "$APP_PATH/docker-compose.staging.yml" ]]; then
  COMPOSE_FILE="docker-compose.staging.yml"
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

echo "═══════════════════════════════════════════════════"
echo "iil-Platform Deploy — ADR-120"
echo "App:  $APP_NAME"
echo "Env:  $ENVIRONMENT"
echo "Tag:  $IMAGE_TAG"
[[ -n "$PREVIOUS_TAG" ]] && echo "Prev: $PREVIOUS_TAG"
echo "═══════════════════════════════════════════════════"

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

# Staging: vor dem Hochfahren den Altstack sauber abräumen.
# `up -d --remove-orphans` entfernt nur Orphans DESSELBEN Compose-Projekts;
# ein Altcontainer aus einem früheren Run (anderes Projekt/Netz) bleibt
# bestehen und blockiert dauerhaft Host-Ports (real passiert:
# risk_hub_staging_minio hielt 127.0.0.1:9002 → Deploy + Rollback failten).
# Nur staging, damit Prod (self-hosted, kein Stale-Stack-Problem) keinen
# zusätzlichen Downtime durch ein down→up bekommt.
if [[ "$ENVIRONMENT" == "staging" ]]; then
  echo "Staging: räume Altstack ab (down --remove-orphans)"
  docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>&1 || true
fi

docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans

# Health-Check
# Staging: derive local URL from the WEB service's host-port mapping.
# We must NOT just take the first 127.0.0.1:PORT line in the compose
# file — that frequently belongs to MinIO/Redis/etc. Try (in order):
#   1. docker compose port lookup on every service whose name ends in -web
#   2. awk-parse the compose block under a `*-web:` service key
#   3. legacy fallback: first 127.0.0.1 host port (preserves old behaviour)
if [[ "$ENVIRONMENT" == "staging" ]]; then
  LOCAL_PORT=""

  for svc in $(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null | grep -E '(^|-)web$' || true); do
    LOCAL_PORT=$(docker compose -f "$COMPOSE_FILE" port "$svc" 8000 2>/dev/null | awk -F: '{print $NF}' | head -1 || true)
    [[ -n "$LOCAL_PORT" ]] && break
  done

  if [[ -z "$LOCAL_PORT" ]]; then
    LOCAL_PORT=$(awk '
      /^  [a-zA-Z0-9_-]+-web:[[:space:]]*$/ { in_web=1; next }
      /^  [a-zA-Z0-9_-]+:[[:space:]]*$/     { in_web=0 }
      in_web && match($0, /127\.0\.0\.1:[0-9]+/) {
        s = substr($0, RSTART, RLENGTH)
        sub(/.*:/, "", s)
        print s; exit
      }
    ' "$APP_PATH/$COMPOSE_FILE" || true)
  fi

  if [[ -z "$LOCAL_PORT" ]]; then
    LOCAL_PORT=$(grep -oP '127\.0\.0\.1:\K\d+' "$APP_PATH/$COMPOSE_FILE" | head -1 || true)
  fi

  if [[ -n "$LOCAL_PORT" ]]; then
    HEALTH_CHECK_URL="http://127.0.0.1:${LOCAL_PORT}/livez/"
    echo "Staging: using local health check $HEALTH_CHECK_URL"
  fi
fi

# Retry-Budget konfigurierbar (Default 30 × 5s ≈ 150s Sleep + curl). Vorher fix 12 (60s) —
# zu kurz für langsame Cold-Starts (z.B. dev-hub: 16 Django-Apps gunicorn-Boot >60s) →
# falsch-roter Deploy trotz gesundem Prod (ADR-231 Welle 0). Loop bricht beim ersten 200 →
# schnelle Apps verlieren nichts; nur echt-langsame/kaputte Deploys nutzen das Budget aus.
# Per-Deploy übersteuerbar via env HEALTH_CHECK_RETRIES.
HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-30}"
if [[ -n "$HEALTH_CHECK_URL" ]]; then
  echo "Health-Check: $HEALTH_CHECK_URL (max $HEALTH_CHECK_RETRIES Versuche)"
  for i in $(seq 1 "$HEALTH_CHECK_RETRIES"); do
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_CHECK_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
      echo "✅ Health-Check OK (Versuch $i/$HEALTH_CHECK_RETRIES)"
      break
    fi
    echo "⏳ Versuch $i/$HEALTH_CHECK_RETRIES — HTTP $HTTP_CODE"
    sleep 5
    [[ $i -eq "$HEALTH_CHECK_RETRIES" ]] && { echo "❌ Health-Check fehlgeschlagen nach $((HEALTH_CHECK_RETRIES * 5))s"; exit 4; }
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
echo "═══════════════════════════════════════════════════"
echo "✅ Deploy erfolgreich: $APP_NAME:$IMAGE_TAG ($ENVIRONMENT)"
echo "═══════════════════════════════════════════════════"
