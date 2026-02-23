#!/usr/bin/env bash
# create-secrets.sh — ADR-045 Phase 2
# Erstellt secrets.enc.env für ein Repo aus dem bestehenden .env.prod auf dem Server.
#
# Voraussetzungen:
#   - age private key in ~/.config/sops/age/keys.txt
#   - sops installiert (sops --version)
#   - SSH-Zugang zum Server
#
# Nutzung:
#   ./scripts/create-secrets.sh bfagent /opt/bfagent-app
#   ./scripts/create-secrets.sh dev-hub /opt/dev-hub
#   ./scripts/create-secrets.sh travel-beat /opt/travel-beat

set -euo pipefail

REPO="${1:?Usage: create-secrets.sh <repo-name> <server-deploy-path>}"
SERVER_PATH="${2:?Usage: create-secrets.sh <repo-name> <server-deploy-path>}"
SERVER="${DEPLOY_SERVER:-deploy@46.225.113.1}"
SOPS_YAML="${BASH_SOURCE%/*}/../.sops.yaml"

# Ziel-Verzeichnis = Repo-Root
REPO_DIR="$(cd "${BASH_SOURCE%/*}/.." && pwd)/../${REPO}"
if [ ! -d "$REPO_DIR" ]; then
  echo "ERROR: Repo-Verzeichnis nicht gefunden: $REPO_DIR" >&2
  exit 1
fi

echo "=== ADR-045: secrets.enc.env für ${REPO} erstellen ==="
echo "Server:     ${SERVER}:${SERVER_PATH}/.env.prod"
echo "Ziel:       ${REPO_DIR}/secrets.enc.env"
echo ""

# Prüfe Voraussetzungen
if ! command -v sops &>/dev/null; then
  echo "ERROR: sops nicht installiert. Installieren mit:" >&2
  echo "  curl -sLo /usr/local/bin/sops https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64 && chmod +x /usr/local/bin/sops" >&2
  exit 1
fi

if [ ! -f "${HOME}/.config/sops/age/keys.txt" ]; then
  echo "ERROR: age private key nicht gefunden: ~/.config/sops/age/keys.txt" >&2
  echo "  Generieren mit: age-keygen -o ~/.config/sops/age/keys.txt" >&2
  echo "  ODER: Bestehenden Key aus sicherem Speicher kopieren" >&2
  exit 1
fi

# .env.prod vom Server holen (temporär, nie auf Disk schreiben wenn möglich)
echo "Hole .env.prod vom Server..."
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

ssh "${SERVER}" "cat ${SERVER_PATH}/.env.prod" > "$TMPFILE"
LINE_COUNT=$(wc -l < "$TMPFILE")
echo "  ${LINE_COUNT} Zeilen gelesen."

# Zeige welche Keys verschlüsselt werden (ohne Werte)
echo ""
echo "Keys die verschlüsselt werden:"
grep -v '^#' "$TMPFILE" | grep '=' | cut -d'=' -f1 | sed 's/^/  - /'
echo ""

read -rp "Fortfahren? (j/N) " confirm
if [[ "$confirm" != "j" && "$confirm" != "J" ]]; then
  echo "Abgebrochen."
  exit 0
fi

# Mit SOPS verschlüsseln (liest .sops.yaml automatisch)
echo "Verschlüssele mit SOPS..."
SOPS_AGE_KEY_FILE="${HOME}/.config/sops/age/keys.txt" \
  sops --config "$SOPS_YAML" \
       --encrypt \
       --input-type dotenv \
       --output-type dotenv \
       "$TMPFILE" > "${REPO_DIR}/secrets.enc.env"

echo "✅ ${REPO_DIR}/secrets.enc.env erstellt."
echo ""
echo "Nächste Schritte:"
echo "  1. Prüfen: sops -d ${REPO_DIR}/secrets.enc.env | head -5"
echo "  2. Committen: cd ${REPO_DIR} && git add secrets.enc.env && git commit -m 'feat: SOPS-encrypted secrets (ADR-045)'"
echo "  3. SOPS_AGE_KEY in GitHub Secrets setzen (Inhalt von ~/.config/sops/age/keys.txt)"
echo "  4. .env.prod vom Server entfernen (nach erstem erfolgreichen CI-Deploy mit SOPS)"
