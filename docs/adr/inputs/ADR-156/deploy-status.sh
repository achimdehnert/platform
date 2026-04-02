#!/usr/bin/env bash
# /opt/deploy-core/deploy-status.sh
#
# Deterministisches Status-Polling für MCP — Fix B5 (Glob-Ambiguität)
#
# Aufruf durch MCP (statt Glob-file_read):
#   ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-status.sh <repo>")
#
# Ausgabe (JSON):
#   {
#     "repo": "risk-hub",
#     "status": "RUNNING|SUCCESS|FAILED|UNKNOWN",
#     "pid": 12345,
#     "pid_alive": true,
#     "elapsed_seconds": 42,
#     "log_tail": ["letzte 10 Log-Zeilen ..."],
#     "log_file": "/var/log/deploy/risk-hub-latest.log"
#   }
#
set -euo pipefail

REPO="${1:?Usage: deploy-status.sh <repo>}"

STATE_DIR="/var/run/deploy"
LOG_DIR="/var/log/deploy"
PID_FILE="${STATE_DIR}/${REPO}.pid"
STATUS_FILE="${STATE_DIR}/${REPO}.status"
LOG_LATEST="${LOG_DIR}/${REPO}-latest.log"

# Status lesen
STATUS="UNKNOWN"
if [[ -f "${STATUS_FILE}" ]]; then
    STATUS=$(cat "${STATUS_FILE}" | tr -d '[:space:]')
fi

# PID und Liveness
PID="null"
PID_ALIVE="false"
if [[ -f "${PID_FILE}" ]]; then
    PID=$(cat "${PID_FILE}" | tr -d '[:space:]')
    if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
        PID_ALIVE="true"
    fi
fi

# Elapsed-Time aus Log-Datei (Mtime)
ELAPSED="null"
if [[ -f "${LOG_LATEST}" ]]; then
    # Sekunden seit letzter Modifikation des Log-Symlinks-Targets
    LOG_TARGET=$(readlink -f "${LOG_LATEST}" 2>/dev/null || echo "${LOG_LATEST}")
    if [[ -f "${LOG_TARGET}" ]]; then
        MTIME=$(stat -c %Y "${LOG_TARGET}" 2>/dev/null || echo 0)
        NOW=$(date +%s)
        ELAPSED=$((NOW - MTIME))
        # Elapsed = Zeit seit LETZTER Log-Änderung, nicht Deploy-Start
        # Für Deploy-Start: erste Zeile des Logs parsen
        START_LINE=$(head -1 "${LOG_TARGET}" 2>/dev/null || echo "")
        if [[ "${START_LINE}" =~ gestartet:\ ([0-9T:+-]+) ]]; then
            START_TS="${BASH_REMATCH[1]}"
            START_EPOCH=$(date -d "${START_TS}" +%s 2>/dev/null || echo 0)
            if [[ "${START_EPOCH}" -gt 0 ]]; then
                ELAPSED=$((NOW - START_EPOCH))
            fi
        fi
    fi
fi

# Log-Tail (letzte 15 Zeilen) als JSON-Array
LOG_TAIL_JSON="[]"
if [[ -f "${LOG_LATEST}" ]]; then
    LOG_TARGET=$(readlink -f "${LOG_LATEST}" 2>/dev/null || echo "${LOG_LATEST}")
    if [[ -f "${LOG_TARGET}" ]]; then
        # JSON-sichere Ausgabe: Escaping von " und \
        LOG_TAIL_JSON=$(
            tail -15 "${LOG_TARGET}" 2>/dev/null \
            | python3 -c "
import sys, json
lines = sys.stdin.read().splitlines()
print(json.dumps(lines))
" 2>/dev/null || echo '["(Log-Lese-Fehler)"]'
        )
    fi
fi

# JSON-Ausgabe
python3 - << PYEOF
import json
print(json.dumps({
    "repo": "${REPO}",
    "status": "${STATUS}",
    "pid": ${PID} if "${PID}" != "null" else None,
    "pid_alive": ${PID_ALIVE},
    "elapsed_seconds": ${ELAPSED} if "${ELAPSED}" != "null" else None,
    "log_file": "${LOG_LATEST}",
    "log_tail": ${LOG_TAIL_JSON},
}, indent=2))
PYEOF
