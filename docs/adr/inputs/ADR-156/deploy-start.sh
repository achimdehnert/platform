#!/usr/bin/env bash
# /opt/deploy-core/deploy-start.sh
#
# MCP-facing Wrapper für deploy.sh — Fix B4 (nohup PID-Verlust)
#
# PROBLEM im ADR-v2:
#   "nohup bash deploy.sh repo &"  →  $! geht in SSH-Session verloren
#   MCP sieht nur "exit 0" des SSH-Befehls — nicht ob Deploy läuft
#
# LÖSUNG:
#   deploy-start.sh startet deploy.sh im Background und schreibt PID auf Server.
#   MCP pollt /var/run/deploy/<repo>.status — deterministisch, kein Glob.
#
# Aufruf durch MCP:
#   ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-start.sh <repo>", timeout=10)
#
# Antwort (stdout, <2s):
#   JSON mit PID, Status-File-Pfad, Log-Pfad, geschätzter Dauer
#
# MCP pollt danach:
#   ssh_manage(action="file_read", path="/var/run/deploy/<repo>.status")
#   ssh_manage(action="file_read", path="/var/log/deploy/<repo>-latest.log")
#
set -euo pipefail

REPO="${1:?Usage: deploy-start.sh <repo> [compose-file]}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"

DEPLOY_SCRIPT="/opt/deploy-core/deploy.sh"
STATE_DIR="/var/run/deploy"
LOG_DIR="/var/log/deploy"
PID_FILE="${STATE_DIR}/${REPO}.pid"
STATUS_FILE="${STATE_DIR}/${REPO}.status"
LOG_LATEST="${LOG_DIR}/${REPO}-latest.log"
LOCK_FILE="${STATE_DIR}/${REPO}.lock"

mkdir -p "${STATE_DIR}" "${LOG_DIR}"

# Prüfe ob Deploy bereits läuft (schnelle Vorprüfung — atomare Prüfung via flock im Haupt-Script)
if [[ -f "${PID_FILE}" ]]; then
    existing_pid=$(cat "${PID_FILE}" 2>/dev/null || echo "")
    if [[ -n "${existing_pid}" ]] && kill -0 "${existing_pid}" 2>/dev/null; then
        # Prozess läuft noch
        printf '{"status":"already_running","pid":%s,"status_file":"%s","log_file":"%s","message":"Deploy für %s läuft bereits (PID %s). Warte auf Abschluss."}\n' \
            "${existing_pid}" "${STATUS_FILE}" "${LOG_LATEST}" "${REPO}" "${existing_pid}"
        exit 4
    fi
fi

# Prüfe ob Script existiert
if [[ ! -x "${DEPLOY_SCRIPT}" ]]; then
    printf '{"status":"error","message":"Deploy-Script nicht gefunden oder nicht ausführbar: %s"}\n' "${DEPLOY_SCRIPT}"
    exit 1
fi

# Status auf STARTING setzen (vor nohup — damit Polling sofort sinnvoll ist)
echo "STARTING" > "${STATUS_FILE}"

# Deploy im Background starten — disown löst vom Shell-Job ab
# PID wird durch deploy.sh selbst in PID_FILE geschrieben
nohup bash "${DEPLOY_SCRIPT}" "${REPO}" "${COMPOSE_FILE}" \
    >> "${LOG_LATEST}" 2>&1 &

BACKGROUND_PID=$!
disown "${BACKGROUND_PID}"

# Kurz warten bis deploy.sh seine eigene PID geschrieben hat (max 1s)
for i in 1 2 3 4 5; do
    sleep 0.2
    if [[ -f "${PID_FILE}" ]]; then
        break
    fi
done

# Antwort für MCP — alles was MCP für Polling braucht
printf '{"status":"started","background_pid":%d,"status_file":"%s","log_file":"%s","repo":"%s","poll_interval_seconds":10,"message":"Deploy gestartet. Polle status_file für Fortschritt."}\n' \
    "${BACKGROUND_PID}" \
    "${STATUS_FILE}" \
    "${LOG_LATEST}" \
    "${REPO}"

exit 0
