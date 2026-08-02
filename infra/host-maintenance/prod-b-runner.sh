#!/usr/bin/env bash
# Registriert einen per-Repo GitHub-Actions-Runner auf prod-b (89.167.43.30)
# nach dem prod-Muster (systemd, ein Runner je Repo), aber mit EINDEUTIGEM
# Label `prod-b-server` (ADR-257: nie plain self-hosted, nie prod-server).
#
# Aufruf (lokal, braucht gh mit Admin auf dem Ziel-Repo):
#   bash prod-b-runner.sh achimdehnert/coach-hub
#
# Gate autonomous-no-human-review (Welle #1695 Phase 0): nach der Registrierung
# PFLICHT ein Beweis-Lauf in CI — Dummy-Job mit `runs-on: [self-hosted, prod-b-server]`
# muss auf DIESEM Runner grün laufen, bevor der erste echte Deploy dorthin zeigt.
set -euo pipefail
REPO="${1:?Aufruf: prod-b-runner.sh <org>/<repo>}"
HOST=root@89.167.43.30
NAME="$(echo "$REPO" | tr '/' '-')"
LABEL=prod-b-server

echo "== Registration-Token für $REPO holen (kurzlebig, nur in Env) =="
TOKEN=$(gh api -X POST "repos/$REPO/actions/runners/registration-token" -q .token)

echo "== Runner-Version ermitteln =="
VER=$(curl -sf https://api.github.com/repos/actions/runner/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')

echo "== Auf prod-b installieren: /opt/actions-runner/$NAME (Runner v$VER) =="
ssh "$HOST" "bash -s" <<EOF
set -euo pipefail
D=/opt/actions-runner/$NAME
if [ -d "\$D/.runner" ] || [ -f "\$D/.runner" ]; then echo "bereits konfiguriert: \$D"; exit 0; fi
mkdir -p "\$D" && cd "\$D"
[ -f run.sh ] || { curl -sfLo r.tgz "https://github.com/actions/runner/releases/download/v$VER/actions-runner-linux-x64-$VER.tar.gz"; tar xzf r.tgz && rm r.tgz; }
export RUNNER_ALLOW_RUNASROOT=1
./config.sh --unattended --url "https://github.com/$REPO" --token "$TOKEN" \
  --name "$NAME.$LABEL" --labels "$LABEL" --replace
./svc.sh install root && ./svc.sh start
EOF

echo "== Verifikation: Runner online? =="
gh api "repos/$REPO/actions/runners" \
  -q '.runners[] | select(.labels[].name=="'"$LABEL"'") | .name + " -> " + .status'
echo "FERTIG. Nächster Pflicht-Schritt (Gate): Dummy-Job auf [self-hosted, $LABEL] grün laufen lassen."
