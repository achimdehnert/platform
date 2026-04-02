#!/usr/bin/env bash
# /opt/deploy-core/deploy-status.sh
#
# Deterministisches Status-Polling für MCP — Fix B5
#
# Aufruf:
#   ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-status.sh <repo>")
#
# Ausgabe (JSON):
#   {"repo":"risk-hub","status":"RUNNING","pid":12345,"pid_alive":true,"elapsed_seconds":42,...}
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

# Elapsed-Time aus Log-Datei
ELAPSED="null"
if [[ -f "${LOG_LATEST}" ]]; then
    LOG_TARGET=$(readlink -f "${LOG_LATEST}" 2>/dev/null || echo "${LOG_LATEST}")
    if [[ -f "${LOG_TARGET}" ]]; then
        NOW=$(date +%s)
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

# Log-Tail als JSON-Array
LOG_TAIL_JSON="[]"
if [[ -f "${LOG_LATEST}" ]]; then
    LOG_TARGET=$(readlink -f "${LOG_LATEST}" 2>/dev/null || echo "${LOG_LATEST}")
    if [[ -f "${LOG_TARGET}" ]]; then
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

# Convert bash booleans to Python-safe values
PY_PID_ALIVE="False"
[[ "${PID_ALIVE}" == "true" ]] && PY_PID_ALIVE="True"

PY_PID="None"
[[ "${PID}" != "null" ]] && PY_PID="${PID}"

PY_ELAPSED="None"
[[ "${ELAPSED}" != "null" ]] && PY_ELAPSED="${ELAPSED}"

# JSON-Ausgabe
python3 - << PYEOF
import json
print(json.dumps({
    "repo": "${REPO}",
    "status": "${STATUS}",
    "pid": ${PY_PID},
    "pid_alive": ${PY_PID_ALIVE},
    "elapsed_seconds": ${PY_ELAPSED},
    "log_file": "${LOG_LATEST}",
    "log_tail": ${LOG_TAIL_JSON},
}, indent=2))
PYEOF
