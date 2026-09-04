#!/usr/bin/env bash
# Bootstrap eines GitHub-Actions-Runners (Linux x64) in einer WSL2-Ubuntu-Distro.
# Ziel: writing-hub CI ohne GitHub-hosted Minuten (platform#2392, KONZ-021-Opt-out).
#
# Aufruf (in der WSL, als Nutzer mit sudo):
#   REPO=writing-hub OWNER=achimdehnert LABEL=ci-gpu TOKEN=<registration-token> ./bootstrap_ci_runner_wsl.sh
# Registration-Token (1 h gueltig) auf einer Maschine mit gh:
#   gh api -X POST repos/$OWNER/$REPO/actions/runners/registration-token --jq .token
#
# Idempotent: bereits vorhandene Teile werden uebersprungen. Runner laeuft als `github-ci`
# (REC-5, nicht root), in der docker-Gruppe (Postgres-Service-Container der Jobs).
set -euo pipefail
: "${REPO:?REPO fehlt}" "${OWNER:?OWNER fehlt}" "${TOKEN:?TOKEN fehlt}"
LABEL="${LABEL:-ci-gpu}"
RUNNER_VERSION="${RUNNER_VERSION:-2.328.0}"
DIR="/opt/actions-runner-$REPO"
NAME="${NAME:-$REPO-$LABEL}"

echo "== 1/5 Docker (nativ in WSL, ohne Docker Desktop)"
# Docker Desktop hinterlaesst in der Distro einen Stub `docker`, der nur "not found" ausgibt —
# `command -v docker` ist deshalb KEIN Beweis fuer einen Daemon. Massgeblich ist die systemd-Unit.
if ! systemctl list-unit-files docker.service 2>/dev/null | grep -q '^docker.service'; then
  if [ -x /usr/bin/docker ] && ! dpkg -S /usr/bin/docker >/dev/null 2>&1; then
    sudo mv /usr/bin/docker /usr/bin/docker.desktop-stub   # Stub aus dem Weg, sonst kollidiert das Paket
  fi
  sudo apt-get update -qq
  sudo apt-get install -y -qq ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
sudo systemctl enable --now docker
docker --version

echo "== 2/5 Runner-Nutzer github-ci"
id github-ci >/dev/null 2>&1 || sudo useradd -m -s /bin/bash github-ci
sudo usermod -aG docker github-ci

echo "== 2b/5 Playwright-Systemabhaengigkeiten (einmalig als root, der Runner-Nutzer bekommt kein sudo)"
# writing-hub installiert Chromium im Job per `playwright install chromium` (ohne --with-deps);
# die OS-Libs dafuer liegen nach diesem Schritt bereits auf der Box.
sudo apt-get install -y -qq python3-pip python3-venv >/dev/null
sudo python3 -m pip install -q playwright >/dev/null 2>&1 || true
sudo python3 -m playwright install-deps chromium >/dev/null 2>&1 || echo "WARN: playwright install-deps fehlgeschlagen — Chromium-Libs von Hand nachziehen"

echo "== 3/5 Runner-Paket $RUNNER_VERSION nach $DIR"
if [ ! -x "$DIR/config.sh" ]; then
  sudo mkdir -p "$DIR" && sudo chown github-ci:github-ci "$DIR"
  sudo -u github-ci bash -c "cd '$DIR' && curl -fsSL -o runner.tgz https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz && tar xzf runner.tgz && rm runner.tgz"
  sudo "$DIR/bin/installdependencies.sh" >/dev/null
fi

echo "== 4/5 Registrierung ($OWNER/$REPO, Label $LABEL, Name $NAME)"
if [ ! -f "$DIR/.runner" ]; then
  sudo -u github-ci bash -c "cd '$DIR' && ./config.sh --unattended --url https://github.com/$OWNER/$REPO --token '$TOKEN' --labels '$LABEL' --name '$NAME' --work _work --replace"
fi

echo "== 5/5 systemd-Dienst"
cd "$DIR" && sudo ./svc.sh install github-ci >/dev/null 2>&1 || true
sudo ./svc.sh start
sudo ./svc.sh status | head -5

cat <<EOF

FERTIG. Noch auf der Windows-Seite (einmalig, damit die WSL nach Logout weiterlaeuft):
  1. %USERPROFILE%\\.wslconfig:  [wsl2]  vmIdleTimeout=-1
  2. Aufgabenplanung: Trigger "Beim Start", Aktion: wsl.exe -d Ubuntu -u root -- sleep infinity
     (haelt die VM offen; der Runner-Dienst startet per systemd von selbst)
Pruefen: gh api repos/$OWNER/$REPO/actions/runners --jq '.runners[] | "\(.name) \(.status)"'
EOF
