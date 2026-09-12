#!/usr/bin/env bash
# Non-Prod-Runner (Label ci-nonprod) fuer EIN Repo auf dev-desktop registrieren — genau nach
# platform/infra/host-maintenance/runner-nonprod-runbook.md §3 (ADR-257).
#
# Warum als Datei: die Schritte brauchen sudo (Nutzer github-ci, Dienst-Installation);
# die Kapitaens-Session hat auf dev-desktop kein sudo ohne Passwort. Der Owner fuehrt
# das Skript in seiner eigenen Shell aus:
#
#     bash infra/host-maintenance/runner-nonprod-registrieren.sh <repo>
#     (Vorlage: /opt/actions-runner-travel-beat; am 2026-09-10 fuer mcp-hub vom Owner ausgefuehrt)
#
# Voraussetzungen (geprueft 2026-09-10): /opt/actions-runner-travel-beat existiert als
# Vorlage (Nutzer github-ci, Runner 2.336.0), 335 GB frei, gh ist als devuser angemeldet
# und darf Runner der Repos lesen. Nichts hier ist Prod: dev-desktop traegt laut
# hosts.yaml den Runner staging-ci mit demselben Label.
set -euo pipefail

REPO="${1:-mcp-hub}"
OWNER="achimdehnert"
ZIEL="/opt/actions-runner-$REPO"
VORLAGE="/opt/actions-runner-travel-beat"
NAME="$REPO-staging-ci"

if [ -d "$ZIEL" ]; then
  echo "❌ $ZIEL existiert schon — nichts getan (Runbook §7 statt Neuanlage)."; exit 1
fi

# 1) Registrierungs-Token (1 h gueltig) als angemeldeter gh-Nutzer holen — wird nicht ausgegeben
TOKEN="$(gh api -X POST "/repos/$OWNER/$REPO/actions/runners/registration-token" --jq .token)"
[ -n "$TOKEN" ] || { echo "❌ kein Registrierungs-Token (gh-Rechte auf $OWNER/$REPO?)"; exit 1; }

# 2) Runner-Verzeichnis aus der Vorlage (Binaries), Rechte github-ci, KEIN root-Lauf (REC-5)
VERSION_DIR="$(readlink -f "$VORLAGE/bin")"
sudo install -d -o github-ci -g github-ci -m 755 "$ZIEL"
sudo -u github-ci cp -r "$VERSION_DIR" "$ZIEL/bin"
sudo -u github-ci cp -r "$VORLAGE/externals" "$ZIEL/externals" 2>/dev/null || sudo -u github-ci cp -r "$(readlink -f "$VORLAGE/externals")" "$ZIEL/externals"
for f in config.sh run.sh env.sh svc.sh run-helper.sh.template safe_sleep.sh; do
  [ -f "$VORLAGE/$f" ] && sudo -u github-ci cp "$VORLAGE/$f" "$ZIEL/$f"
done

# 3) Registrieren (Runbook §3): Label ci-nonprod, kein prod-Label, Name <repo>-staging-ci
cd "$ZIEL"
sudo -u github-ci bash -c "./config.sh --unattended --url https://github.com/$OWNER/$REPO \
  --token '$TOKEN' --labels ci-nonprod --name '$NAME' --work _work --replace"

# 4) Dienst als github-ci installieren und starten (NICHT root)
sudo ./svc.sh install github-ci
sudo ./svc.sh start

# 5) Beleg: Runner online in GitHub, Dienst aktiv
sleep 5
gh api "/repos/$OWNER/$REPO/actions/runners" --jq ".runners[]|select(.name==\"$NAME\")|.name+\" \"+.status+\" [\"+([.labels[].name]|join(\",\"))+\"]\""
systemctl is-active "actions.runner.$OWNER-$REPO.$NAME.service" || true
echo "→ danach in platform/infra/hosts.yaml: hosts_runners von dev-desktop um '$NAME' ergaenzen (Deklaration folgt der Registrierung, Runbook §2)."
