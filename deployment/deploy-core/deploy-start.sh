#!/usr/bin/env bash
# /opt/deploy-core/deploy-start.sh
#
# MCP-facing Wrapper für deploy.sh — Fix B4 (nohup PID-Verlust)
#
# Aufruf durch MCP:
#   ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-start.sh <repo>", timeout=10)
#
# Antwort (stdout, <2s):
#   JSON mit PID, Status-File-Pfad, Log-Pfad
#
set -euo pipefail

REPO="${1:?Usage: deploy-start.sh <repo> [compose-file] [health-port]}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"
HEALTH_PORT="${3:-8000}"

DEPLOY_SCRIPT="/opt/deploy-core/deploy.sh"
STATE_DIR="/var/run/deploy"
LOG_DIR="/var/log/deploy"
PID_FILE="${STATE_DIR}/${REPO}.pid"
STATUS_FILE="${STATE_DIR}/${REPO}.status"
LOG_LATEST="${LOG_DIR}/${REPO}-latest.log"

mkdir -p "${STATE_DIR}" "${LOG_DIR}"

# Prüfe ob Deploy bereits läuft
if [[ -f "${PID_FILE}" ]]; then
    existing_pid=$(cat "${PID_FILE}" 2>/dev/null || echo "")
    if [[ -n "${existing_pid}" ]] && kill -0 "${existing_pid}" 2>/dev/null; then
        printf '{"status":"already_running","pid":%s,"status_file":"%s","log_file":"%s","message":"Deploy für %s läuft bereits (PID %s)."}\n' \
            "${existing_pid}" "${STATUS_FILE}" "${LOG_LATEST}" "${REPO}" "${existing_pid}"
        exit 4
    fi
fi

# Prüfe ob Script existiert
if [[ ! -x "${DEPLOY_SCRIPT}" ]]; then
    printf '{"status":"error","message":"Deploy-Script nicht gefunden oder nicht ausführbar: %s"}\n' "${DEPLOY_SCRIPT}"
    exit 1
fi

# Status auf STARTING setzen
echo "STARTING" > "${STATUS_FILE}"

# Deploy im Background starten
nohup bash "${DEPLOY_SCRIPT}" "${REPO}" "${COMPOSE_FILE}" "${HEALTH_PORT}" \
    >> "${LOG_LATEST}" 2>&1 &

BACKGROUND_PID=$!
disown "${BACKGROUND_PID}"

# Kurz warten bis deploy.sh seine PID geschrieben hat
for i in 1 2 3 4 5; do
    sleep 0.2
    if [[ -f "${PID_FILE}" ]]; then
        break
    fi
done

# JSON-Antwort für MCP
printf '{"status":"started","background_pid":%d,"status_file":"%s","log_file":"%s","repo":"%s","health_port":%s,"poll_interval_seconds":10}\n' \
    "${BACKGROUND_PID}" \
    "${STATUS_FILE}" \
    "${LOG_LATEST}" \
    "${REPO}" \
    "${HEALTH_PORT}"

exit 0
