#!/bin/bash
# sync-mcp-config.sh — generiert ~/.codeium/windsurf/mcp_config.json aus Template
# SSoT: platform/templates/mcp_config.*.json (ADR-176)
set -euo pipefail

export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
PLATFORM_DIR="$GITHUB_DIR/platform"
MCP_HUB_DIR="$GITHUB_DIR/mcp-hub"
TARGET="$HOME/.codeium/windsurf/mcp_config.json"
BACKUP="$TARGET.bak.$(date +%Y%m%d-%H%M%S)"

# Environment-Erkennung
if grep -qi microsoft /proc/version 2>/dev/null; then
  ENV_KEY="wsl"
elif [ "$(hostname)" = "dev-desktop" ] || [ "$USER" = "adehnert" ]; then
  ENV_KEY="dev-desktop"
else
  ENV_KEY="wsl"  # Fallback
fi

TEMPLATE="$PLATFORM_DIR/templates/mcp_config.$ENV_KEY.json"

echo "🔧 MCP Config Sync"
echo "   Environment: $ENV_KEY"
echo "   Template:    $TEMPLATE"
echo "   Target:      $TARGET"

if [ ! -f "$TEMPLATE" ]; then
  echo "❌ Template nicht gefunden: $TEMPLATE" >&2
  exit 1
fi

# Validate: alle referenzierten Start-Scripts existieren
echo ""
echo "🔍 Validiere Start-Scripts..."
MISSING=0
while IFS= read -r script; do
  FULL="${script//\$\{GITHUB_DIR\}/$GITHUB_DIR}"
  if [ -n "$FULL" ] && [ ! -f "$FULL" ]; then
    echo "   ⚠️  Fehlt: $FULL"
    MISSING=$((MISSING+1))
  fi
done < <(grep -oP '\$\{GITHUB_DIR\}/[^"]+\.sh' "$TEMPLATE" | sort -u)

if [ $MISSING -gt 0 ]; then
  echo ""
  echo "⚠️  $MISSING Start-Script(s) fehlen in mcp-hub/scripts/"
  echo "    → Server sind im Template aber nicht startbar. Anlegen oder Server im Template deaktivieren."
fi

# Backup
if [ -f "$TARGET" ]; then
  cp "$TARGET" "$BACKUP"
  echo ""
  echo "💾 Backup: $BACKUP"
fi

# Variable-Expansion (envsubst-Style für $GITHUB_DIR)
mkdir -p "$(dirname "$TARGET")"
sed "s|\${GITHUB_DIR}|$GITHUB_DIR|g" "$TEMPLATE" > "$TARGET"

# Syntax-Check
if command -v python3 >/dev/null && ! python3 -c "import json; json.load(open('$TARGET'))" 2>/dev/null; then
  echo "❌ Generierte Config ist kein valides JSON"
  [ -f "$BACKUP" ] && mv "$BACKUP" "$TARGET" && echo "   → Backup wiederhergestellt"
  exit 1
fi

echo "✅ Config geschrieben: $TARGET"
echo ""

# Prefix-Mapping ausgeben (für Abgleich mit Rules)
echo "📋 Prefix-Mapping ($ENV_KEY):"
python3 -c "
import json
cfg = json.load(open('$TARGET'))
servers = [k for k in cfg.get('mcpServers', {}).keys() if not k.startswith('_')]
for i, s in enumerate(servers):
    disabled = cfg['mcpServers'][s].get('disabled', False)
    flag = ' (disabled)' if disabled else ''
    print(f'   mcp{i}_ = {s}{flag}')
"

echo ""
echo "🔄 Windsurf neu laden, damit neue Config aktiv wird."
