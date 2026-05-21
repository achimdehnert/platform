#!/bin/bash
# Klickdummy-Host Klausel-2-Deploy (ADR-216 Patch 2026-05-21)
#
# Übergangs-Variante: nginx-vhost + BasicAuth (statt Traefik+Authentik).
# Nutzt das Bestandsmuster von staging-devhub.iil.pet auf staging-platform.
#
# Voraussetzungen (geprüft):
#   * Docker + docker-compose v2
#   * Host-nginx läuft (mit /etc/nginx/sites-enabled/)
#   * Cloudflared-Service läuft
#   * Sudo-Rechte
#
# Aufruf:
#   sudo bash deploy-klausel2.sh

set -euo pipefail

# Konfiguration
SYNC_USER="${SYNC_USER:-klickdummy-sync}"
OPT_DIR="${OPT_DIR:-/opt/klickdummy}"
SRV_DIR="${SRV_DIR:-/srv/klickdummy}"
WORK_DIR="${WORK_DIR:-/var/lib/klickdummy-sync}"
BUNDLE_DIR="${BUNDLE_DIR:-/tmp/klickdummy-host-bundle}"
DEPLOY_KEY="$WORK_DIR/.ssh/klickdummy-deploy_ed25519"
HTPASSWD_FILE="/etc/nginx/.htpasswd-klickdummy"
HTPASSWD_USER="${HTPASSWD_USER:-klickdummy-viewer}"

CRON_INTERVAL="${CRON_INTERVAL:-*/15 * * * *}"

log() { echo -e "\033[36m[$(date -Is)]\033[0m $*"; }
err() { echo -e "\033[31m[$(date -Is)] ✗ $*\033[0m" >&2; }
ok()  { echo -e "\033[32m[$(date -Is)] ✓ $*\033[0m"; }

# 0. Preflight
preflight() {
  log "Preflight…"
  [ "$(id -u)" = "0" ] || { err "muss als root/sudo laufen"; exit 1; }
  command -v docker &>/dev/null || { err "docker fehlt"; exit 1; }
  docker compose version &>/dev/null || { err "docker compose v2 fehlt"; exit 1; }
  [ -d /etc/nginx/sites-available ] || { err "host-nginx fehlt (/etc/nginx/sites-available)"; exit 1; }
  [ -d "$BUNDLE_DIR" ] || { err "Bundle nicht in $BUNDLE_DIR (scp infra/klickdummy-host/*)"; exit 1; }
  command -v htpasswd &>/dev/null || { log "htpasswd fehlt — apt install apache2-utils"; apt-get install -qq -y apache2-utils; }
  ok "Preflight OK"
}

# 1. User
setup_user() {
  log "User $SYNC_USER…"
  if ! id "$SYNC_USER" &>/dev/null; then
    useradd -r -m -d "$WORK_DIR" -s /bin/bash "$SYNC_USER"
  fi
  ok "User $SYNC_USER"
}

# 2. Dirs
setup_dirs() {
  log "Verzeichnisse…"
  mkdir -p "$OPT_DIR" "$SRV_DIR" "$WORK_DIR" "$WORK_DIR/.ssh"
  chown -R "$SYNC_USER:$SYNC_USER" "$OPT_DIR" "$SRV_DIR" "$WORK_DIR"
  chmod 700 "$WORK_DIR/.ssh"
  ok "Dirs"
}

# 3. SSH-Key
setup_ssh_key() {
  log "SSH-Deploy-Key…"
  if [ ! -f "$DEPLOY_KEY" ]; then
    sudo -u "$SYNC_USER" ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N '' -C "klickdummy-sync@staging-platform" -q
  fi
  sudo -u "$SYNC_USER" bash -c "
    mkdir -p $WORK_DIR/.ssh
    grep -q github.com $WORK_DIR/.ssh/known_hosts 2>/dev/null || \
      ssh-keyscan -t ed25519,rsa github.com >> $WORK_DIR/.ssh/known_hosts 2>/dev/null
  "
  ok "SSH-Key bereit"
}

# 4. Files
install_files() {
  log "Files…"
  cp "$BUNDLE_DIR"/{nginx.conf,sync.sh,repos.yaml,generate_landing.py,docker-compose.klausel2.yml} "$OPT_DIR/"
  ln -sf "$OPT_DIR/docker-compose.klausel2.yml" "$OPT_DIR/docker-compose.yml"
  chown -R "$SYNC_USER:$SYNC_USER" "$OPT_DIR"
  chmod +x "$OPT_DIR/sync.sh" "$OPT_DIR/generate_landing.py"
  ok "Files installiert"
}

# 5. htpasswd erzeugen
setup_htpasswd() {
  log "BasicAuth htpasswd…"
  if [ ! -f "$HTPASSWD_FILE" ]; then
    # Generiere Passwort (16 Zeichen alphanumerisch)
    PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)
    htpasswd -bcB "$HTPASSWD_FILE" "$HTPASSWD_USER" "$PASSWORD"
    chmod 640 "$HTPASSWD_FILE"
    chown root:www-data "$HTPASSWD_FILE" 2>/dev/null || chown root:nginx "$HTPASSWD_FILE" 2>/dev/null || true
    echo
    echo "════════════════════════════════════════════════════════════════════"
    echo " BASIC-AUTH CREDENTIALS — bitte sicher aufbewahren + verteilen"
    echo "   URL:        https://staging-klickdummy.iil.pet/"
    echo "   User:       $HTPASSWD_USER"
    echo "   Password:   $PASSWORD"
    echo "════════════════════════════════════════════════════════════════════"
    echo
  else
    ok "htpasswd existiert bereits"
  fi
}

# 6. nginx-vhost
setup_nginx_vhost() {
  log "Host-nginx-vhost…"
  cp "$BUNDLE_DIR/host-nginx-staging-klickdummy.conf" /etc/nginx/sites-available/staging-klickdummy.iil.pet
  ln -sf /etc/nginx/sites-available/staging-klickdummy.iil.pet /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
  ok "nginx-vhost aktiv"
}

# 7. Docker Compose
start_compose() {
  log "Container…"
  cd "$OPT_DIR"
  docker compose pull
  docker compose up -d
  sleep 3
  docker ps --format '{{.Names}}' | grep -q '^klickdummy$' || {
    err "Container nicht hochgekommen"
    docker logs klickdummy 2>&1 | tail -20
    exit 1
  }
  ok "klickdummy-Container läuft auf 127.0.0.1:8081"
}

# 8. Cron
setup_cron() {
  log "Cron…"
  cat > /etc/cron.d/klickdummy-sync <<EOF
$CRON_INTERVAL $SYNC_USER $OPT_DIR/sync.sh >> /var/log/klickdummy-sync.log 2>&1
EOF
  chmod 644 /etc/cron.d/klickdummy-sync
  ok "Cron"
}

# 9. logrotate
setup_logrotate() {
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
  touch /var/log/klickdummy-sync.log
  chown "$SYNC_USER:$SYNC_USER" /var/log/klickdummy-sync.log
  ok "logrotate"
}

# 10. Public-Key ausgeben für Deploy-Keys
print_deploy_key() {
  echo
  echo "════════════════════════════════════════════════════════════════════"
  echo " DEPLOY-KEY (read-only) für 4 Klickdummy-Repos hinzufügen:"
  echo
  cat "${DEPLOY_KEY}.pub"
  echo
  echo " Via gh-CLI (von Rechner mit gh-Auth):"
  echo "   for r in bahn-sqf/sqf-hub bahn-sqf/pg-hub meiki-lra/meiki-hub ttz-lif/ttz-hub; do"
  echo "     gh repo deploy-key add /tmp/key.pub --repo \$r --title 'klickdummy-sync staging-platform'"
  echo "   done"
  echo "════════════════════════════════════════════════════════════════════"
}

# 11. Cloudflared-Tunnel-Hinweis
cloudflared_hint() {
  echo
  echo "ACTION REQUIRED — Cloudflared-Tunnel-Ingress ergänzen:"
  echo "  In /etc/cloudflared/config.yml (oder Tunnel-Config in CF-Dashboard):"
  echo "    - hostname: staging-klickdummy.iil.pet"
  echo "      service: http://localhost:80"
  echo "  Dann: systemctl restart cloudflared"
  echo
  echo "  Alternativ via cloudflared-CLI:"
  echo "    cloudflared tunnel route dns <tunnel-id> staging-klickdummy.iil.pet"
}

main() {
  echo "════════════════════════════════════════════════════════════════════"
  echo "  Klickdummy-Host Klausel-2-Deploy — ADR-216 Patch"
  echo "  Server: $(hostname) — Hostname: staging-klickdummy.iil.pet"
  echo "════════════════════════════════════════════════════════════════════"

  preflight
  setup_user
  setup_dirs
  setup_ssh_key
  install_files
  setup_htpasswd
  setup_nginx_vhost
  start_compose
  setup_cron
  setup_logrotate
  print_deploy_key
  cloudflared_hint

  echo
  ok "Klausel-2-Deploy abgeschlossen."
  echo
  echo "Test (nach Deploy-Key + Cloudflared):"
  echo "  curl -s https://staging-klickdummy.iil.pet/healthz"
  echo "  curl -s -u $HTPASSWD_USER:<pw> https://staging-klickdummy.iil.pet/api/list"
}

main "$@"
