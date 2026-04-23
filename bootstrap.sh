#!/bin/bash
# bootstrap.sh — Platform einmalig einrichten (nach dem Klonen ausführen)
#
# Usage (einmalig auf neuem Computer):
#   git clone https://github.com/achimdehnert/platform
#   bash platform/bootstrap.sh
#
# Oder als One-Liner (ohne vorheriges Klonen):
#   bash <(curl -fsSL https://raw.githubusercontent.com/achimdehnert/platform/main/bootstrap.sh)
set -euo pipefail

# ── Farben ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; exit 1; }

echo ""
echo "┌──────────────────────────────────────────────┐"
echo "│  🚀 IIL Platform Bootstrap                   │"
echo "│  Einmalig auf neuem Computer ausführen        │"
echo "└──────────────────────────────────────────────┘"
echo ""

# ── 1. GITHUB_DIR ermitteln ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# GITHUB_DIR = Elternverzeichnis des platform-Repos (dort wo platform/ liegt)
DETECTED_GITHUB_DIR="$(dirname "$SCRIPT_DIR")"

if [ -n "${GITHUB_DIR:-}" ] && [ "$GITHUB_DIR" != "$DETECTED_GITHUB_DIR" ]; then
  warn "GITHUB_DIR ist bereits gesetzt auf: $GITHUB_DIR"
  warn "Erkannt wurde: $DETECTED_GITHUB_DIR"
  echo -n "  Welchen Pfad verwenden? [detected=$DETECTED_GITHUB_DIR, aktuell=$GITHUB_DIR] (d=detected, k=aktuell): "
  read -r choice
  [ "$choice" = "d" ] && GITHUB_DIR="$DETECTED_GITHUB_DIR"
else
  GITHUB_DIR="$DETECTED_GITHUB_DIR"
fi

echo "   GITHUB_DIR = $GITHUB_DIR"

# ── 2. GITHUB_DIR in ~/.bashrc eintragen ────────────────────────────────────
BASHRC="${HOME}/.bashrc"
if ! grep -q "GITHUB_DIR" "$BASHRC" 2>/dev/null; then
  {
    echo ""
    echo "# Platform: Repo-Basisverzeichnis (Single Source of Truth)"
    echo "export GITHUB_DIR=\"${GITHUB_DIR}\""
  } >> "$BASHRC"
  ok "GITHUB_DIR in $BASHRC eingetragen"
else
  # Update vorhandenen Eintrag falls Pfad unterschiedlich
  CURRENT=$(grep "^export GITHUB_DIR=" "$BASHRC" | grep -oP '(?<=")[^"]+' | head -1)
  if [ "$CURRENT" != "$GITHUB_DIR" ]; then
    sed -i "s|^export GITHUB_DIR=.*|export GITHUB_DIR=\"${GITHUB_DIR}\"|" "$BASHRC"
    ok "GITHUB_DIR in $BASHRC aktualisiert ($CURRENT → $GITHUB_DIR)"
  else
    ok "GITHUB_DIR bereits korrekt in $BASHRC ($GITHUB_DIR)"
  fi
fi
export GITHUB_DIR

# ── 3. platform-Repo prüfen / klonen ────────────────────────────────────────
PLATFORM_DIR="$GITHUB_DIR/platform"
if [ -d "$PLATFORM_DIR/.git" ]; then
  ok "platform bereits vorhanden — pull"
  git -C "$PLATFORM_DIR" pull --rebase --quiet
else
  echo "   Klone platform..."
  git clone https://github.com/achimdehnert/platform "$PLATFORM_DIR" --quiet
  ok "platform geklont nach $PLATFORM_DIR"
fi

# ── 4. Workflows + Rules deployen (Symlinks in alle Repos) ──────────────────
echo ""
echo "   Verteile Workflows + Rules..."
RESULT=$(GITHUB_DIR="$GITHUB_DIR" bash "$PLATFORM_DIR/scripts/sync-workflows.sh" 2>&1)
WF_COUNT=$(echo "$RESULT" | grep -oP '\d+ universal' | grep -oP '\d+' || echo "?")
ok "Workflows deployed (${WF_COUNT} universal + platform-specific)"

# ── 5. project-facts.md für alle lokalen Repos generieren ───────────────────
echo ""
echo "   Generiere project-facts.md..."
FACTS_RESULT=$(GITHUB_DIR="$GITHUB_DIR" python3 "$PLATFORM_DIR/scripts/gen_project_facts.py" 2>&1)
GEN_COUNT=$(echo "$FACTS_RESULT" | grep -oP '\d+ generated' | grep -oP '\d+' || echo "0")
SKIP_COUNT=$(echo "$FACTS_RESULT" | grep -oP '\d+ skipped' | grep -oP '\d+' || echo "?")
ok "project-facts: ${GEN_COUNT} generiert, ${SKIP_COUNT} übersprungen (existieren)"

# ── 6. SSH-Agent prüfen (optional) ─────────────────────────────────────────
if ssh-keygen -F github.com &>/dev/null 2>&1; then
  ok "GitHub SSH-Key vorhanden"
elif [ -f "$HOME/.secrets/github_token" ]; then
  ok "GitHub Token in ~/.secrets/github_token"
else
  warn "Kein GitHub SSH-Key und kein Token in ~/.secrets/github_token"
  echo "   → GitHub-Authentifizierung muss noch eingerichtet werden"
fi

# ── 7. VERSION anzeigen ──────────────────────────────────────────────────────
VERSION=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")

echo ""
echo "┌──────────────────────────────────────────────┐"
echo "│  ✅ Bootstrap abgeschlossen                  │"
echo "│  Platform v${VERSION} (${COMMIT})         │"
echo "│                                              │"
echo "│  Nächste Schritte:                           │"
echo "│  1. source ~/.bashrc    (GITHUB_DIR laden)   │"
echo "│  2. In Windsurf: /session-start ausführen    │"
echo "└──────────────────────────────────────────────┘"
echo ""
