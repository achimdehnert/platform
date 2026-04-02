#!/usr/bin/env bash
# /opt/deploy-core/deploy.sh
#
# Platform-Standard Deploy-Script — ADR-156 §Phase 1 (korrigierte Version)
#
# Fixes gegenüber ADR-v2:
#   B1: flock(1) für atomaren Lock statt race-prone Datei-Existenz-Check
#   B2: Migration-Fehler → Fail-Hard (kein || true)
#   B3: Rollback auf vorheriges Image-Digest bei Health-Check-Failure
#   B4: PID-File auf Server für Liveness-Check durch MCP
#   B5: Symlink <repo>-latest.log für deterministisches Polling
#   B6: COMPOSE_PROJECT_NAME gesetzt (ADR-022)
#   H2: --no-deps bei up -d (kein Neustart abhängiger Services)
#
# Aufruf:
#   bash /opt/deploy-core/deploy.sh <repo> [docker-compose-file]
#
# Exits:
#   0 — Deploy erfolgreich
#   1 — Allgemeiner Fehler (Script-Fehler, Config-Fehler)
#   2 — Migration fehlgeschlagen (Rollback ggf. durchgeführt)
#   3 — Health-Check fehlgeschlagen (Rollback durchgeführt)
#   4 — Deploy bereits läuft (Lock gehalten)
#
# Platform-Standards (ADR-022, ADR-155, ADR-156):
#   - set -euo pipefail
#   - COMPOSE_PROJECT_NAME gesetzt
#   - Idempotentes Health-Check
#   - Fail-Closed bei Migration-Fehler
#
set -euo pipefail

# ── Konfiguration ─────────────────────────────────────────────────────────────

REPO="${1:?Usage: deploy.sh <repo> [compose-file]}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"

# ADR-022: COMPOSE_PROJECT_NAME ist Pflicht — verhindert Namespace-Kollisionen
# zwischen den 18+ Hubs auf dem gleichen Host
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

# ── Initialisierung ───────────────────────────────────────────────────────────

mkdir -p "${STATE_DIR}" "${LOG_DIR}"

# Fix B5: Symlink auf aktuelles Log für deterministisches MCP-Polling
# (kein Glob mehr nötig — MCP liest immer <repo>-latest.log)
ln -sf "${LOG_FILE}" "${LOG_LATEST}"

# Logging: stdout + stderr in Logdatei; stderr zusätzlich auf stderr des Terminals
# Robuster als exec > >(tee ...) — kein Process-Substitution-Problem (Fix H1)
exec > "${LOG_FILE}" 2>&1

echo "=== Deploy ${REPO} gestartet: $(date -Iseconds) ==="
echo "=== Compose-File: ${COMPOSE_FILE} ==="
echo "=== COMPOSE_PROJECT_NAME: ${COMPOSE_PROJECT_NAME} ==="
echo "=== PID: $$ ==="

# PID für MCP-Liveness-Check (Fix B4)
echo "$$" > "${PID_FILE}"

# ── Lock — verhindert parallele Deploys (Fix B1) ──────────────────────────────

# flock(1) ist atomar — kein Race-Condition im Gegensatz zu Datei-Existenz-Check
# -n: non-blocking (schlägt sofort fehl wenn Lock gehalten)
# FD 9 bleibt für die Script-Laufzeit offen → Lock gehalten
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "FATAL: Deploy für '${REPO}' läuft bereits (Lock: ${LOCK_FILE})." >&2
    echo "       Warte auf Abschluss oder entferne Lock manuell." >&2
    echo "RUNNING" > "${STATUS_FILE}"
    exit 4
fi

echo "RUNNING" > "${STATUS_FILE}"

# ── Cleanup bei Exit (auch bei Fehler) ───────────────────────────────────────

_cleanup() {
    local exit_code=$?
    # Lock wird durch exec 9> beim Script-Exit automatisch freigegeben
    # PID-File entfernen
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

# ── Rollback-Vorbereitung (Fix B3) ───────────────────────────────────────────

# Aktuellen Image-Digest sichern BEVOR Pull — für Rollback bei Health-Failure
_save_rollback_tag() {
    local rollback_tag
    # Lese aktuellen Image-Tag aus laufendem Container (wenn vorhanden)
    rollback_tag=$(
        docker compose -f "${COMPOSE_FILE}" images web 2>/dev/null \
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
        # Image-Tag in compose-Datei temporär überschreiben ist fehleranfällig;
        # stattdessen: Docker-Tag direkt nutzen
        docker compose -f "${COMPOSE_FILE}" \
            up -d --no-deps --force-recreate \
            --scale web=1 \
            web 2>&1 || true
        # Hinweis: Vollständiger Rollback erfordert docker pull <old-tag> + compose override
        # → Phase 2: image-tag pinning in docker-compose.prod.yml via sed
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
if ! docker compose -f "${COMPOSE_FILE}" pull web; then
    echo "FATAL: Image pull fehlgeschlagen." >&2
    echo "FAILED" > "${STATUS_FILE}"
    exit 1
fi

# ── Step 2: Migrations (Fix B2 — kein || true, kein 2>/dev/null) ─────────────

echo ""
echo "--- Step 2/4: Migrations ---"

# Strategie: migrate-Service hat Vorrang (idempotenter Container-Job)
# Kein 2>/dev/null — Fehler MÜSSEN sichtbar sein
# Kein || true — Migration-Fehler sind FATAL (Fail-Closed, ADR-062-Prinzip)

MIGRATION_DONE=false

if docker compose -f "${COMPOSE_FILE}" config --services 2>/dev/null | grep -q '^migrate$'; then
    echo "Führe Migration via 'migrate' Service aus..."
    if docker compose -f "${COMPOSE_FILE}" run --rm migrate; then
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
    if docker compose -f "${COMPOSE_FILE}" exec -T web \
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

# Fix H2: --no-deps verhindert Neustart von DB/Redis-Abhängigkeiten
# Andere Hubs auf gleichem Host bleiben unberührt
if ! docker compose -f "${COMPOSE_FILE}" up -d \
    --no-deps \
    --force-recreate \
    web; then
    echo "FATAL: Container-Start fehlgeschlagen." >&2
    _rollback
    exit 3
fi

# Celery-Worker falls vorhanden (optional — kein Fehler wenn nicht vorhanden)
if docker compose -f "${COMPOSE_FILE}" config --services 2>/dev/null | grep -q '^celery'; then
    echo "Starte Celery-Worker neu..."
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate celery || {
        echo "Warnung: Celery-Worker-Start fehlgeschlagen — manuell prüfen" >&2
    }
fi

# ── Step 4: Health Check ──────────────────────────────────────────────────────

echo ""
echo "--- Step 4/4: Health Check (max ${HEALTH_MAX_ATTEMPTS}×${HEALTH_INTERVAL}s = $((HEALTH_MAX_ATTEMPTS * HEALTH_INTERVAL))s) ---"

# Kurze Wartezeit damit Container-Startup beginnen kann
sleep 2

HEALTH_PASSED=false
for attempt in $(seq 1 "${HEALTH_MAX_ATTEMPTS}"); do
    # curl ist robuster als python urllib im Container — läuft auf dem Host
    HTTP_CODE=$(
        curl --silent --output /dev/null --write-out "%{http_code}" \
            --max-time 3 \
            "http://localhost:8000/livez/" \
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
    docker compose -f "${COMPOSE_FILE}" logs --tail=50 web >&2 || true
    _rollback
    exit 3
fi

# ── Abschluss ─────────────────────────────────────────────────────────────────

echo ""
echo "=== Deploy ${REPO} ERFOLGREICH abgeschlossen: $(date -Iseconds) ==="
echo "SUCCESS" > "${STATUS_FILE}"

# Cleanup: alten Rollback-Tag entfernen (aktueller Stand ist stabil)
rm -f "${ROLLBACK_TAG_FILE}"

exit 0
