#!/usr/bin/env bash
# Einstieg im Sandbox-Container (platform#3685): erst Selbstpruefung, dann Waechter.
# Faellt die Selbstpruefung durch, startet kein Agent.
set -euo pipefail

AUSGANG="${SANDBOX_ARBEIT:-/arbeit}/ausgang"
mkdir -p "$AUSGANG"
if ! python3 /sandbox/selbstpruefung.py; then
  printf '{\n  "status": "abgebrochen: Selbstpruefung"\n}\n' >"$AUSGANG/status.json"
  exit 1
fi
[ "${1:-}" = "--nur-pruefen" ] && exit 0

git config --global user.name "iil-sandbox-agent"
git config --global user.email "sandbox@iil.invalid"
if [ -n "${GH_TOKEN:-}" ]; then
  gh auth setup-git
fi
exec python3 /sandbox/waechter.py "$@"
