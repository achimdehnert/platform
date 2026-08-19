#!/usr/bin/env bash
# Einen GitHub-Actions-Runner von einem Host auf einen anderen umziehen.
#
#     bash runner-umziehen.sh <repo> <ziel-host-ssh> [<quell-host-ssh>]
#     bash runner-umziehen.sh pptx-hub root@89.167.43.30 root@88.198.191.108
#
# WARUM ES DAS GIBT
#
# Beim Long-Tail-Umzug am 2026-08-04 (ADR-292) wanderten neun Hubs von prod-a
# nach prod-b -- die Runner blieben stehen. In hosts.yaml steht dazu bis heute
# `hosts_runners: []  # TODO: Runner je umgezogenem Repo registrieren`.
#
# Die Folge ist unsichtbar und teuer: `_deploy-unified.yml` deployt auf einem
# self-hosted Runner DIREKT auf dessen Host. Steht der Runner noch auf dem alten
# Host, liefert jeder Merge dorthin -- und die Live-Seite auf dem neuen Host
# behaelt ihren alten Stand. Gemessen am 2026-08-18 bei pptx-hub: prod-a hatte
# Commit 7ed1566 (17.08.), prod-b bediente prezimo.de mit 0c49ae4 (03.08.) --
# sechs Commits Rueckstand, ohne dass irgendetwas rot wurde.
#
# WAS DAS SKRIPT TUT
#
#   1. Registrierungs-Token holen (gh, lokal authentifiziert)
#   2. Runner auf dem ZIEL-Host anlegen, als Dienst starten
#   3. Runner auf dem QUELL-Host stoppen und abmelden (optional, aber empfohlen:
#      solange beide mit Label 'self-hosted' online sind, entscheidet der Zufall)
#
# Danach: einmal deployen und pruefen, dass der neue Host wirklich liefert.
set -euo pipefail

REPO="${1:?Verwendung: runner-umziehen.sh <repo> <ziel-ssh> [<quell-ssh>]}"
ZIEL="${2:?Ziel-Host fehlt, z.B. root@89.167.43.30}"
QUELL="${3:-}"
OWNER="${OWNER:-achimdehnert}"
VERZ="/opt/actions-runner-$REPO"
NAME="$(echo "$ZIEL" | sed 's/.*@//;s/\./-/g')-$REPO"

echo "== Runner fuer $OWNER/$REPO nach $ZIEL =="

vorhandene=$(gh api "repos/$OWNER/$REPO/actions/runners" \
  --jq '.runners[]|"\(.name) [\(.status)]"' 2>/dev/null || true)
echo "Bisher registriert:"; echo "${vorhandene:-  (keine)}" | sed 's/^/  /'

echo "== Token holen (kurzlebig, 1 Stunde) =="
TOKEN=$(gh api -X POST "repos/$OWNER/$REPO/actions/runners/registration-token" --jq .token)
[ -n "$TOKEN" ] || { echo "FEHLER: kein Token erhalten." >&2; exit 1; }

echo "== Runner auf $ZIEL anlegen =="
ssh -o BatchMode=yes "$ZIEL" "
set -euo pipefail
if [ -f '$VERZ/.runner' ]; then echo 'Runner existiert schon -- nichts getan.'; exit 0; fi
mkdir -p '$VERZ' && cd '$VERZ'
if [ ! -f config.sh ]; then
  V=\$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | grep -oP '\"tag_name\": \"v\\K[^\"]+')
  curl -fsSL -o runner.tar.gz \"https://github.com/actions/runner/releases/download/v\${V}/actions-runner-linux-x64-\${V}.tar.gz\"
  tar xzf runner.tar.gz && rm -f runner.tar.gz
fi
# Der Runner laeuft nicht als root -- das lehnt config.sh ab. Wie bei den
# bestehenden Runnern auf diesen Hosts uebernimmt ein eigener Dienstbenutzer.
id runner >/dev/null 2>&1 || useradd -r -m -d /home/runner -s /bin/bash runner
chown -R runner:runner '$VERZ'
sudo -u runner ./config.sh --unattended --replace \
  --url 'https://github.com/$OWNER/$REPO' --token '$TOKEN' \
  --name '$NAME' --labels 'self-hosted,Linux,X64,$NAME' --work _work
./svc.sh install runner
./svc.sh start
./svc.sh status | head -5
"

if [ -n "$QUELL" ]; then
  echo "== Alten Runner auf $QUELL abmelden =="
  ALT_TOKEN=$(gh api -X POST "repos/$OWNER/$REPO/actions/runners/remove-token" --jq .token)
  ssh -o BatchMode=yes "$QUELL" "
  set -euo pipefail
  D='$VERZ'
  [ -d \"\$D\" ] || { echo 'Kein Runner-Verzeichnis auf dem Quell-Host -- nichts zu tun.'; exit 0; }
  cd \"\$D\"
  ./svc.sh stop || true
  ./svc.sh uninstall || true
  sudo -u runner ./config.sh remove --token '$ALT_TOKEN' || ./config.sh remove --token '$ALT_TOKEN' || true
  echo 'Alter Runner abgemeldet.'
  "
fi

echo "== Stand danach =="
gh api "repos/$OWNER/$REPO/actions/runners" \
  --jq '.runners[]|"  \(.name) [\(.status)] labels=\([.labels[].name]|join(","))"'

cat <<HINWEIS

Naechster Schritt -- NICHT vergessen, sonst bleibt der Rueckstand bestehen:

  gh workflow run deploy.yml --repo $OWNER/$REPO

Danach pruefen, dass wirklich der neue Host geliefert hat:

  ssh $ZIEL "cat /opt/$REPO/.deploy-manifest.json"

Der 'commit' dort muss der neue sein.
HINWEIS
