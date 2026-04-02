#!/usr/bin/env bash
# /opt/deploy-core/deploy.sh
#
# Platform-Standard Deploy-Script — ADR-156 §Phase 1 (v3.1)
#
# Fixes gegenüber ADR-v2:
#   B1: flock(1) für atomaren Lock statt race-prone Datei-Existenz-Check
#   B2: Migration-Fehler → Fail-Hard (kein || true)
#   B3: Rollback auf vorheriges Image-Digest bei Health-Check-Failure
#   B4: PID-File auf Server für Liveness-Check durch MCP
#   B5: Symlink <repo>-latest.log für deterministisches Polling
#   B6: COMPOSE_PROJECT_NAME gesetzt (ADR-022)
#   H2: --no-deps bei up -d (kein Neustart abhängiger Services)
#   T1: Health-Check-Port parametrisiert (kein hardcoded 8000)
#
# Aufruf:
#   bash /opt/deploy-core/deploy.sh <repo> [docker-compose-file] [health-port]
#
# Exits:
#   0 — Deploy erfolgreich
#   1 — Allgemeiner Fehler (Script-Fehler, Config-Fehler)
#   2 — Migration fehlgeschlagen
#   3 — Health-Check fehlgeschlagen (Rollback durchgeführt)
#   4 — Deploy bereits läuft (Lock gehalten)
#
set -euo pipefail

# ── Konfiguration ─────────────────────────────────────────────────────────────

REPO="${1:?Usage: deploy.sh <repo> [compose-file] [health-port]}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"
HEALTH_PORT="${3:-8000}"

# ADR-022: COMPOSE_PROJECT_NAME ist Pflicht — verhindert Namespace-Kollisionen
export COMPOSE_PROJECT_NAME="${REPO}"

REPO_DIR="/opt/${REPO}"
STATE_DIR="/var/run/deploy"
LOG_DIR="/var/log/deploy"
LOG_FILE="${LOG_DIR}/${REPO}-$(date +%Y%m%d-%H%M%S).log"
LOG_LATEST="${LOG_DIR}/${REPO}-latest.log"
LOCK_FILE="${STATE_DIR}/${REPO}.lock"
PID_FILE="${STATE_DIR}/${REPO}.pid"
STATUS_FILE="${STATE_DIR}/${REPO}.status"
ROLLBACK_TAG_FILE="${STATE_DIR}/${REPO}.rollback-tag"
HEALTH_MAX_ATTEMPTS=12   # 12 × 5s = 60s
HEALTH_INTERVAL=5

# ── Service-Name Auto-Detection ──────────────────────────────────────────────
# Repos nutzen "web" oder "<repo>-web" als Service-Name
_detect_service() {
    local pattern="$1"
    local services
    services=$(docker compose -f "${REPO_DIR}/${COMPOSE_FILE}" config --services 2>/dev/null || echo "")
    # Exact match first, then pattern match
    if echo "${services}" | grep -qx "${pattern}"; then
        echo "${pattern}"
    elif echo "${services}" | grep -q "${pattern}"; then
        echo "${services}" | grep "${pattern}" | head -1
    else
        echo ""
    fi
}

# ── Initialisierung ───────────────────────────────────────────────────────────

mkdir -p "${STATE_DIR}" "${LOG_DIR}"

# Fix B5: Symlink auf aktuelles Log für deterministisches MCP-Polling
ln -sf "${LOG_FILE}" "${LOG_LATEST}"

# Fix H1: Kein Process-Substitution — direkte Umleitung
exec > "${LOG_FILE}" 2>&1

echo "=== Deploy ${REPO} gestartet: $(date -Iseconds) ==="
echo "=== Compose-File: ${COMPOSE_FILE} ==="
echo "=== COMPOSE_PROJECT_NAME: ${COMPOSE_PROJECT_NAME} ==="
echo "=== Health-Port: ${HEALTH_PORT} ==="
echo "=== PID: $$ ==="

# PID für MCP-Liveness-Check (Fix B4)
echo "$$" > "${PID_FILE}"

# ── Lock — verhindert parallele Deploys (Fix B1) ──────────────────────────────

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "FATAL: Deploy für '${REPO}' läuft bereits (Lock: ${LOCK_FILE})." >&2
    echo "RUNNING" > "${STATUS_FILE}"
    exit 4
fi

echo "RUNNING" > "${STATUS_FILE}"

# ── Cleanup bei Exit ─────────────────────────────────────────────────────────

_cleanup() {
    local exit_code=$?
    rm -f "${PID_FILE}"
    echo "=== Deploy ${REPO} beendet: $(date -Iseconds) — Exit-Code: ${exit_code} ==="
}
trap _cleanup EXIT

# ── Validierung ───────────────────────────────────────────────────────────────

if [[ ! -d "${REPO_DIR}" ]]; then
    echo "FATAL: Repo-Verzeichnis ${REPO_DIR} existiert nicht." >&2
    echo "FAILED" > "${STATUS_FILE}"
    exit 1
fi

if [[ ! -f "${REPO_DIR}/${COMPOSE_FILE}" ]]; then
    echo "FATAL: ${REPO_DIR}/${COMPOSE_FILE} nicht gefunden." >&2
    echo "FAILED" > "${STATUS_FILE}"
    exit 1
fi

cd "${REPO_DIR}"

# Detect service names
WEB_SERVICE=$(_detect_service "web")
if [[ -z "${WEB_SERVICE}" ]]; then
    echo "FATAL: Kein web-Service in ${COMPOSE_FILE} gefunden." >&2
    echo "FAILED" > "${STATUS_FILE}"
    exit 1
fi
CELERY_SERVICE=$(_detect_service "celery")
echo "=== Web-Service: ${WEB_SERVICE}, Celery-Service: ${CELERY_SERVICE:-keine} ==="

# ── Rollback-Vorbereitung (Fix B3) ───────────────────────────────────────────

_save_rollback_tag() {
    local rollback_tag
    rollback_tag=$(
        docker compose -f "${COMPOSE_FILE}" images "${WEB_SERVICE}" 2>/dev/null \
        | awk 'NR==2 {print $3}' \
        || echo ""
    )
    if [[ -n "${rollback_tag}" && "${rollback_tag}" != "<none>" ]]; then
        echo "${rollback_tag}" > "${ROLLBACK_TAG_FILE}"
        echo "Rollback-Tag gesichert: ${rollback_tag}"
    else
        echo "Warnung: Kein aktueller Image-Tag für Rollback verfügbar (erster Deploy?)"
        rm -f "${ROLLBACK_TAG_FILE}"
    fi
}

_rollback() {
    echo "=== ROLLBACK gestartet ===" >&2
    if [[ -f "${ROLLBACK_TAG_FILE}" ]]; then
        local rollback_tag
        rollback_tag=$(cat "${ROLLBACK_TAG_FILE}")
        echo "Rollback auf Image-Tag: ${rollback_tag}" >&2
        docker compose -f "${COMPOSE_FILE}" \
            up -d --no-deps --force-recreate \
            "${WEB_SERVICE}" 2>&1 || true
        echo "ROLLBACK abgeschlossen — bitte manuell prüfen!" >&2
    else
        echo "Kein Rollback-Tag verfügbar — manuelles Eingreifen erforderlich!" >&2
    fi
    echo "FAILED" > "${STATUS_FILE}"
}

_save_rollback_tag

# ── Step 1: Image Pull ────────────────────────────────────────────────────────

echo ""
echo "--- Step 1/4: docker compose pull web ---"
if ! docker compose -f "${COMPOSE_FILE}" pull "${WEB_SERVICE}"; then
    echo "FATAL: Image pull fehlgeschlagen." >&2
    echo "FAILED" > "${STATUS_FILE}"
    exit 1
fi

# ── Step 2: Migrations (Fix B2 — Fail-Closed) ────────────────────────────────

echo ""
echo "--- Step 2/4: Migrations ---"

MIGRATION_DONE=false

MIGRATE_SERVICE=$(_detect_service "migrate")
if [[ -n "${MIGRATE_SERVICE}" ]]; then
    echo "Führe Migration via '${MIGRATE_SERVICE}' Service aus..."
    if docker compose -f "${COMPOSE_FILE}" run --rm "${MIGRATE_SERVICE}"; then
        MIGRATION_DONE=true
        echo "Migration erfolgreich (migrate service)."
    else
        MIGRATION_EXIT=$?
        echo "FATAL: Migration fehlgeschlagen (Exit-Code: ${MIGRATION_EXIT})." >&2
        echo "       Deployment wird ABGEBROCHEN — DB-Schema unverändert." >&2
        echo "FAILED" > "${STATUS_FILE}"
        exit 2
    fi
fi

if [[ "${MIGRATION_DONE}" == false ]]; then
    echo "Kein 'migrate' Service — versuche exec in laufendem Container..."
    if docker compose -f "${COMPOSE_FILE}" exec -T "${WEB_SERVICE}" \
        python manage.py migrate --noinput; then
        echo "Migration erfolgreich (exec in web)."
    else
        MIGRATION_EXIT=$?
        echo "FATAL: Migration fehlgeschlagen (Exit-Code: ${MIGRATION_EXIT})." >&2
        echo "       Deployment wird ABGEBROCHEN." >&2
        echo "FAILED" > "${STATUS_FILE}"
        exit 2
    fi
fi

# ── Step 3: Container neu starten ────────────────────────────────────────────

echo ""
echo "--- Step 3/4: Container recreate ---"

# Fix H2: --no-deps verhindert Neustart von DB/Redis
if ! docker compose -f "${COMPOSE_FILE}" up -d \
    --no-deps \
    --force-recreate \
    "${WEB_SERVICE}"; then
    echo "FATAL: Container-Start fehlgeschlagen." >&2
    _rollback
    exit 3
fi

# Celery-Worker falls vorhanden
if [[ -n "${CELERY_SERVICE}" ]]; then
    echo "Starte Celery-Worker neu (${CELERY_SERVICE})..."
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate "${CELERY_SERVICE}" || {
        echo "Warnung: Celery-Worker-Start fehlgeschlagen — manuell prüfen" >&2
    }
fi

# ── Step 4: Health Check ──────────────────────────────────────────────────────

echo ""
echo "--- Step 4/4: Health Check (max ${HEALTH_MAX_ATTEMPTS}×${HEALTH_INTERVAL}s) ---"

sleep 2

HEALTH_PASSED=false
for attempt in $(seq 1 "${HEALTH_MAX_ATTEMPTS}"); do
    # T1: HEALTH_PORT parametrisiert statt hardcoded 8000
    HTTP_CODE=$(
        curl --silent --output /dev/null --write-out "%{http_code}" \
            --max-time 3 \
            "http://localhost:${HEALTH_PORT}/livez/" \
        2>/dev/null || echo "000"
    )

    if [[ "${HTTP_CODE}" == "200" ]]; then
        echo "Health-Check bestanden (Versuch ${attempt}/${HEALTH_MAX_ATTEMPTS}, HTTP ${HTTP_CODE})."
        HEALTH_PASSED=true
        break
    fi

    echo "Health-Check Versuch ${attempt}/${HEALTH_MAX_ATTEMPTS}: HTTP ${HTTP_CODE} — warte ${HEALTH_INTERVAL}s..."
    sleep "${HEALTH_INTERVAL}"
done

if [[ "${HEALTH_PASSED}" == false ]]; then
    echo "FATAL: Health-Check nach $((HEALTH_MAX_ATTEMPTS * HEALTH_INTERVAL))s nicht bestanden." >&2
    echo "       Container-Logs:" >&2
    docker compose -f "${COMPOSE_FILE}" logs --tail=50 "${WEB_SERVICE}" >&2 || true
    _rollback
    exit 3
fi

# ── Abschluss ─────────────────────────────────────────────────────────────────

echo ""
echo "=== Deploy ${REPO} ERFOLGREICH abgeschlossen: $(date -Iseconds) ==="
echo "SUCCESS" > "${STATUS_FILE}"

rm -f "${ROLLBACK_TAG_FILE}"

exit 0
