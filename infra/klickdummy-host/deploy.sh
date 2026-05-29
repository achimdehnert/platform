#!/bin/bash
# Klickdummy-Host One-Shot-Deploy für staging-platform (ADR-216)
# Idempotent: kann mehrfach ausgeführt werden ohne Schaden.
#
# Voraussetzungen (werden geprüft):
#   * Docker + docker-compose v2
#   * Traefik schon laufend mit Network 'traefik_public'
#   * Authentik-Outpost schon laufend (Container-Name: authentik-outpost)
#   * Sudo-Rechte
#
# Aufruf auf staging-platform (NICHT lokal):
#   sudo bash deploy.sh
#
# Was es macht (in dieser Reihenfolge):
#   0. Preflight-Check (Voraussetzungen)
#   1. User klickdummy-sync anlegen (falls noch nicht da)
#   2. Verzeichnisse + Ownership setzen
#   3. SSH-Deploy-Key generieren (falls noch nicht da) — Public-Key ausgeben
#   4. Files an die Stellen kopieren (von /tmp/klickdummy-host-bundle/)
#   5. docker compose up -d (mit traefik-Labels)
#   6. cron-Job einrichten (15-Min-Intervall)
#   7. logrotate-Snippet
#   8. Erster Sync-Test (sofern Deploy-Keys schon zu Repos hinzugefügt)
#
# WICHTIG: Schritte 3 (SSH-Key zu GitHub-Repos hinzufügen),
# Authentik-OAuth-App + Authentik-Gruppe + DNS-Record sind MANUELL
# (siehe DEPLOY-CHECKLIST.md).

set -euo pipefail

# ============================================================================
# Konfiguration (vor Run anpassbar via ENV)
# ============================================================================
SYNC_USER="${SYNC_USER:-klickdummy-sync}"
OPT_DIR="${OPT_DIR:-/opt/klickdummy}"
SRV_DIR="${SRV_DIR:-/srv/klickdummy}"
WORK_DIR="${WORK_DIR:-/var/lib/klickdummy-sync}"
BUNDLE_DIR="${BUNDLE_DIR:-/tmp/klickdummy-host-bundle}"
DEPLOY_KEY="$WORK_DIR/.ssh/klickdummy-deploy_ed25519"

# Cron-Frequenz (Minuten); Default 15 Min (Pre-Pilot)
CRON_INTERVAL="${CRON_INTERVAL:-*/15 * * * *}"

# ============================================================================
# Helper
# ============================================================================
log() { echo -e "\033[36m[$(date -Is)]\033[0m $*"; }
err() { echo -e "\033[31m[$(date -Is)] ✗ $*\033[0m" >&2; }
ok()  { echo -e "\033[32m[$(date -Is)] ✓ $*\033[0m"; }

# ============================================================================
# 0. Preflight
# ============================================================================
preflight() {
  log "Preflight-Check…"

  if [ "$(id -u)" != "0" ]; then
    err "deploy.sh muss als root oder via sudo laufen"
    exit 1
  fi

  if ! command -v docker &>/dev/null; then
    err "docker fehlt — installiere docker + docker-compose v2"
    exit 1
  fi

  if ! docker compose version &>/dev/null; then
    err "docker compose v2 fehlt"
    exit 1
  fi

  if ! docker network inspect traefik_public &>/dev/null; then
    err "Docker-Network 'traefik_public' fehlt — Traefik (ADR-212) muss laufen"
    exit 1
  fi

  if ! docker ps --format '{{.Names}}' | grep -q '^traefik$'; then
    err "traefik-Container läuft nicht — siehe platform/infra/traefik/"
    exit 1
  fi

  if ! docker ps --format '{{.Names}}' | grep -q 'authentik-outpost'; then
    err "authentik-outpost-Container läuft nicht (für SSO)"
    err "  Setup: platform/scripts/authentik-staging-oidc.sh"
    exit 1
  fi

  if [ ! -d "$BUNDLE_DIR" ]; then
    err "Bundle-Dir nicht gefunden: $BUNDLE_DIR"
    err "  Kopiere infra/klickdummy-host/* hierher:"
    err "    scp infra/klickdummy-host/* staging-platform:/tmp/klickdummy-host-bundle/"
    exit 1
  fi

  ok "Preflight bestanden"
}

# ============================================================================
# 1. User klickdummy-sync anlegen
# ============================================================================
setup_user() {
  log "User $SYNC_USER…"
  if id "$SYNC_USER" &>/dev/null; then
    ok "User $SYNC_USER existiert bereits"
  else
    useradd -r -m -d "$WORK_DIR" -s /bin/bash "$SYNC_USER"
    ok "User $SYNC_USER angelegt"
  fi
}

# ============================================================================
# 2. Verzeichnisse + Ownership
# ============================================================================
setup_dirs() {
  log "Verzeichnisse…"
  mkdir -p "$OPT_DIR" "$SRV_DIR" "$WORK_DIR" "$WORK_DIR/.ssh"
  chown -R "$SYNC_USER:$SYNC_USER" "$OPT_DIR" "$SRV_DIR" "$WORK_DIR"
  chmod 700 "$WORK_DIR/.ssh"
  ok "Verzeichnisse $OPT_DIR, $SRV_DIR, $WORK_DIR vorbereitet"
}

# ============================================================================
# 3. SSH-Deploy-Key generieren (idempotent)
# ============================================================================
setup_ssh_key() {
  log "SSH-Deploy-Key…"
  if [ -f "$DEPLOY_KEY" ]; then
    ok "Deploy-Key existiert bereits: $DEPLOY_KEY"
  else
    sudo -u "$SYNC_USER" ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N '' -C "klickdummy-sync@staging-platform"
    ok "Deploy-Key generiert"
  fi

  # ssh-known-hosts für github.com
  sudo -u "$SYNC_USER" bash -c "
    mkdir -p $WORK_DIR/.ssh
    if ! grep -q github.com $WORK_DIR/.ssh/known_hosts 2>/dev/null; then
      ssh-keyscan -t ed25519,rsa github.com >> $WORK_DIR/.ssh/known_hosts 2>/dev/null
    fi
  "

  echo
  echo "════════════════════════════════════════════════════════════════════"
  echo "ACTION REQUIRED — Public-Key zu jedem der 4 Klickdummy-Repos als"
  echo "Deploy-Key (read-only!) hinzufügen:"
  echo
  cat "${DEPLOY_KEY}.pub"
  echo
  echo "Repos:"
  echo "  https://github.com/bahn-sqf/sqf-hub/settings/keys/new"
  echo "  https://github.com/bahn-sqf/pg-hub/settings/keys/new"
  echo "  https://github.com/meiki-lra/meiki-hub/settings/keys/new"
  echo "  https://github.com/ttz-lif/ttz-hub/settings/keys/new"
  echo
  echo "Alternative via gh-CLI (von einem Rechner mit gh-Auth):"
  echo "  for r in bahn-sqf/sqf-hub bahn-sqf/pg-hub meiki-lra/meiki-hub ttz-lif/ttz-hub; do"
  echo "    gh repo deploy-key add ${DEPLOY_KEY}.pub --repo \$r --title 'klickdummy-sync staging-platform' "
  echo "  done"
  echo "════════════════════════════════════════════════════════════════════"
}

# ============================================================================
# 4. Files aus Bundle in $OPT_DIR
# ============================================================================
install_files() {
  log "Files installieren…"
  cp -v "$BUNDLE_DIR"/{docker-compose.yml,nginx.conf,sync.sh,repos.yaml,generate_landing.py} "$OPT_DIR/"
  chown -R "$SYNC_USER:$SYNC_USER" "$OPT_DIR"
  chmod +x "$OPT_DIR/sync.sh" "$OPT_DIR/generate_landing.py"
  ok "Files in $OPT_DIR installiert"
}

# ============================================================================
# 5. Docker Compose starten
# ============================================================================
start_compose() {
  log "Docker Compose…"
  cd "$OPT_DIR"
  docker compose pull
  docker compose up -d
  sleep 3
  if docker ps --format '{{.Names}}' | grep -q '^klickdummy$'; then
    ok "klickdummy-Container läuft"
  else
    err "klickdummy-Container nicht hochgekommen — docker logs klickdummy"
    docker logs klickdummy 2>&1 | tail -20
    exit 1
  fi
}

# ============================================================================
# 6. Cron einrichten
# ============================================================================
setup_cron() {
  log "Cron $CRON_INTERVAL…"
  local cronfile=/etc/cron.d/klickdummy-sync
  cat > "$cronfile" <<EOF
# Klickdummy-Sync (ADR-216) — 15-Min-Intervall
$CRON_INTERVAL $SYNC_USER $OPT_DIR/sync.sh >> /var/log/klickdummy-sync.log 2>&1
EOF
  chmod 644 "$cronfile"
  ok "Cron eingerichtet: $cronfile"
}

# ============================================================================
# 7. logrotate
# ============================================================================
setup_logrotate() {
  log "logrotate…"
  cat > /etc/logrotate.d/klickdummy-sync <<EOF
/var/log/klickdummy-sync.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 640 $SYNC_USER $SYNC_USER
}
EOF
  ok "logrotate konfiguriert"
}

# ============================================================================
# 8. Erster Sync-Test (manuell triggern, prüft Deploy-Keys)
# ============================================================================
first_sync() {
  log "Erster Sync-Test (sofern Deploy-Keys gesetzt)…"
  if sudo -u "$SYNC_USER" "$OPT_DIR/sync.sh"; then
    ok "Sync erfolgreich"
    echo
    echo "Klickdummies in $SRV_DIR:"
    find "$SRV_DIR" -maxdepth 4 -name 'shell.html' -o -name 'chat-simulator.html' 2>/dev/null | head -10
    echo
    echo "Discovery-Endpoint Inhalt: $SRV_DIR/_index.json"
    if [ -f "$SRV_DIR/_index.json" ]; then
      head -20 "$SRV_DIR/_index.json"
    fi
  else
    err "Sync fehlgeschlagen — vermutlich Deploy-Keys noch nicht zu Repos hinzugefügt"
    echo "Wenn Keys hinzugefügt: erneut versuchen mit:"
    echo "  sudo -u $SYNC_USER $OPT_DIR/sync.sh"
  fi
}

# ============================================================================
# Main
# ============================================================================
main() {
  echo "════════════════════════════════════════════════════════════════════"
  echo "  Klickdummy-Host Deploy — ADR-216"
  echo "  Server: $(hostname) — User: $SYNC_USER"
  echo "════════════════════════════════════════════════════════════════════"

  preflight
  setup_user
  setup_dirs
  setup_ssh_key
  install_files
  start_compose
  setup_cron
  setup_logrotate
  first_sync

  echo
  ok "Deploy abgeschlossen."
  echo
  echo "Nächste Schritte (siehe DEPLOY-CHECKLIST.md):"
  echo "  1. Deploy-Key zu 4 Klickdummy-Repos (siehe Output oben)"
  echo "  2. Authentik-OAuth-App via scripts/authentik-staging-oidc.sh"
  echo "  3. Authentik-Gruppe 'klickdummy-viewers' + 5 User"
  echo "  4. DNS-Record für staging-klickdummy.iil.pet (falls kein Wildcard *.iil.pet)"
  echo "  5. Health-Check: curl -s https://staging-klickdummy.iil.pet/healthz"
}

main "$@"
