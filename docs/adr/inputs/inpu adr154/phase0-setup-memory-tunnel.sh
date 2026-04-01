#!/usr/bin/env bash
# =============================================================================
# platform/scripts/phase0-setup-memory-tunnel.sh
# Phase 0: pgvector Memory Store erreichbar machen via autossh-Tunnel
#
# Voraussetzung: autossh installiert (sudo apt install autossh)
# Ziel: Prod pgvector (88.198.191.108:15435) → WSL localhost:15435
# =============================================================================
set -euo pipefail
trap 'echo "ERROR at line $LINENO — exit code $?" >&2; exit 1' ERR

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
PROD_HOST="88.198.191.108"
PROD_USER="root"
REMOTE_PORT="15435"
LOCAL_PORT="15435"
SERVICE_NAME="iil-memory-tunnel"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
ENV_FILE="${HOME}/.config/iil/memory-tunnel.env"
SCRIPT_INSTALL_PATH="${HOME}/.local/bin/iil-memory-tunnel.sh"

# ---------------------------------------------------------------------------
# Schritt 1: autossh prüfen
# ---------------------------------------------------------------------------
echo "[1/5] Prüfe autossh..."
if ! command -v autossh &>/dev/null; then
  echo "  autossh nicht gefunden. Bitte installieren: sudo apt install autossh"
  exit 2
fi
echo "  autossh: $(autossh -V 2>&1 | head -1)"

# ---------------------------------------------------------------------------
# Schritt 2: SSH-Konnektivität testen
# ---------------------------------------------------------------------------
echo "[2/5] Teste SSH-Verbindung zu ${PROD_HOST}..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${PROD_USER}@${PROD_HOST}" exit 2>/dev/null; then
  echo "  FEHLER: SSH-Verbindung zu ${PROD_USER}@${PROD_HOST} fehlgeschlagen."
  echo "  Stelle sicher dass dein SSH-Key hinterlegt ist: ssh-copy-id ${PROD_USER}@${PROD_HOST}"
  exit 3
fi
echo "  SSH-Verbindung OK."

# ---------------------------------------------------------------------------
# Schritt 3: Env-Datei erstellen (Secret wird aus read_secret gelesen)
# ---------------------------------------------------------------------------
echo "[3/5] Erstelle Env-Datei ${ENV_FILE}..."
mkdir -p "$(dirname "${ENV_FILE}")"
# Passwort aus bestehendem Secret-Store lesen (nie hardcoden)
DB_PASSWORD="$(cat "${HOME}/.secrets/orchestrator_mcp_db_password" 2>/dev/null || true)"
if [[ -z "${DB_PASSWORD}" ]]; then
  echo "  WARNUNG: Kein Secret unter ~/.secrets/orchestrator_mcp_db_password gefunden."
  echo "  Bitte manuell setzen: echo 'PASSWORT' > ~/.secrets/orchestrator_mcp_db_password && chmod 600 ~/.secrets/orchestrator_mcp_db_password"
  DB_PASSWORD="REPLACE_WITH_SECRET"
fi

cat > "${ENV_FILE}" <<EOF
# IIL Memory Tunnel Environment
# Generiert von: platform/scripts/phase0-setup-memory-tunnel.sh
# Datum: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
ORCHESTRATOR_MCP_MEMORY_DB_URL=postgresql://orchestrator:${DB_PASSWORD}@localhost:${LOCAL_PORT}/orchestrator_mcp
ORCHESTRATOR_MCP_MEMORY_EMBEDDING_PROVIDER=openai
EOF
chmod 600 "${ENV_FILE}"
echo "  Env-Datei erstellt (chmod 600)."

# ---------------------------------------------------------------------------
# Schritt 4: Tunnel-Script installieren
# ---------------------------------------------------------------------------
echo "[4/5] Installiere Tunnel-Script nach ${SCRIPT_INSTALL_PATH}..."
mkdir -p "$(dirname "${SCRIPT_INSTALL_PATH}")"
cat > "${SCRIPT_INSTALL_PATH}" <<'TUNNEL_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
exec autossh \
  -M 0 \
  -N \
  -o "ServerAliveInterval=30" \
  -o "ServerAliveCountMax=3" \
  -o "ExitOnForwardFailure=yes" \
  -o "StrictHostKeyChecking=accept-new" \
  -L "15435:127.0.0.1:15435" \
  "root@88.198.191.108"
TUNNEL_SCRIPT
chmod +x "${SCRIPT_INSTALL_PATH}"
echo "  Tunnel-Script installiert."

# ---------------------------------------------------------------------------
# Schritt 5: systemd user-service installieren und aktivieren
# ---------------------------------------------------------------------------
echo "[5/5] Installiere systemd user-service ${SERVICE_NAME}..."
mkdir -p "${SYSTEMD_USER_DIR}"
cat > "${SYSTEMD_USER_DIR}/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=IIL pgvector Memory Tunnel (Prod → WSL:${LOCAL_PORT})
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
ExecStart=${SCRIPT_INSTALL_PATH}
Restart=always
RestartSec=10
EnvironmentFile=${ENV_FILE}

# Sicherheit
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}.service"
systemctl --user start "${SERVICE_NAME}.service"

# Status prüfen
sleep 2
if systemctl --user is-active --quiet "${SERVICE_NAME}.service"; then
  echo ""
  echo "✅ Tunnel aktiv."
  echo "   Status: systemctl --user status ${SERVICE_NAME}"
  echo "   Logs:   journalctl --user -u ${SERVICE_NAME} -f"
  echo ""
  echo "Nächster Schritt:"
  echo "  source ${ENV_FILE}"
  echo "  psql \$ORCHESTRATOR_MCP_MEMORY_DB_URL -c 'SELECT version();'"
else
  echo "❌ Service nicht aktiv. Logs:"
  journalctl --user -u "${SERVICE_NAME}" --no-pager -n 20
  exit 4
fi
