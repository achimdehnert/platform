#!/usr/bin/env bash
# =============================================================================
# setup-mcp-servers.sh — MCP Server Setup für Windsurf
# =============================================================================
#
# Installiert alle benötigten Dependencies und konfiguriert MCP-Server.
#
# USAGE:
#   sudo bash scripts/setup-mcp-servers.sh
#
# =============================================================================
set -euo pipefail

# ── Logging ──────────────────────────────────────────────────────────────────
_GREEN='\033[0;32m'; _YELLOW='\033[1;33m'; _RED='\033[0;31m'
_CYAN='\033[0;36m'; _RESET='\033[0m'

log()  { echo -e "${_CYAN}[mcp-setup]${_RESET} $*"; }
ok()   { echo -e "${_GREEN}✓${_RESET} $*"; }
warn() { echo -e "${_YELLOW}⚠${_RESET} $*" >&2; }
err()  { echo -e "${_RED}✗${_RESET} $*" >&2; exit 1; }

# ── Check root ───────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "Dieses Script muss mit sudo ausgeführt werden: sudo bash $0"
fi

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
WINDSURF_CONFIG="$REAL_HOME/.codeium/windsurf/mcp_config.json"
PLATFORM_DIR="$REAL_HOME/CascadeProjects/platform"

log "User: $REAL_USER"
log "Home: $REAL_HOME"
log "Platform: $PLATFORM_DIR"

# ── Step 1: System Dependencies ──────────────────────────────────────────────
log "Installing system dependencies..."
apt update -qq
apt install -y -qq curl python3-pip python3-venv

ok "System dependencies installed"

# ── Step 2: Node.js 20 LTS ───────────────────────────────────────────────────
if command -v node &>/dev/null && [[ "$(node -v)" == v20* ]]; then
    ok "Node.js $(node -v) already installed"
else
    log "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y -qq nodejs
    ok "Node.js $(node -v) installed"
fi

# ── Step 3: Python MCP Framework (via pipx) ─────────────────────────────────
log "Installing pipx..."
apt install -y -qq pipx
sudo -u "$REAL_USER" pipx ensurepath

ok "pipx installed"

# ── Step 4: Platform venv + packages ─────────────────────────────────────────
if [[ -d "$PLATFORM_DIR" ]]; then
    log "Setting up platform venv..."
    cd "$PLATFORM_DIR"
    
    if [[ ! -d ".venv" ]]; then
        sudo -u "$REAL_USER" python3 -m venv .venv
    fi
    
    # Install MCP framework in venv
    sudo -u "$REAL_USER" .venv/bin/pip install --quiet mcp pydantic httpx
    
    # Install local MCP packages
    for pkg in orchestrator_mcp packages/outline-mcp packages/inception-mcp packages/platform-context; do
        if [[ -d "$pkg" ]]; then
            log "Installing $pkg..."
            sudo -u "$REAL_USER" .venv/bin/pip install --quiet -e "$pkg" 2>/dev/null || warn "$pkg install failed (may need dependencies)"
        fi
    done
    
    ok "Platform packages installed"
else
    warn "Platform directory not found: $PLATFORM_DIR"
fi

# ── Step 5: Create MCP Config ────────────────────────────────────────────────
log "Creating MCP config..."

mkdir -p "$(dirname "$WINDSURF_CONFIG")"

cat > "$WINDSURF_CONFIG" << EOF
{
  "mcpServers": {
    "orchestrator": {
      "command": "$PLATFORM_DIR/.venv/bin/python",
      "args": ["-m", "orchestrator_mcp.server"],
      "cwd": "$PLATFORM_DIR",
      "env": {
        "PYTHONPATH": "$PLATFORM_DIR"
      }
    },
    "outline-mcp": {
      "command": "$PLATFORM_DIR/.venv/bin/python",
      "args": ["-m", "outline_mcp.server"],
      "cwd": "$PLATFORM_DIR/packages/outline-mcp",
      "env": {
        "PYTHONPATH": "$PLATFORM_DIR/packages/outline-mcp",
        "OUTLINE_API_URL": "https://outline.iil.pet",
        "OUTLINE_API_TOKEN": ""
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": ""
      }
    },
    "cloudflare-api": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-cloudflare"],
      "env": {
        "CLOUDFLARE_API_TOKEN": ""
      }
    }
  }
}
EOF

chown "$REAL_USER:$REAL_USER" "$WINDSURF_CONFIG"

ok "MCP config created: $WINDSURF_CONFIG"

# ── Step 6: Verify ───────────────────────────────────────────────────────────
log "Verifying installation..."

echo ""
echo "  ✓ Node.js:  $(node -v)"
echo "  ✓ npm:      $(npm -v)"
echo "  ✓ Python:   $(python3 --version)"
echo "  ✓ MCP:      $(sudo -u "$REAL_USER" python3 -c 'import mcp; print(mcp.__version__)' 2>/dev/null || echo 'installed')"
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "  MCP Server Setup Complete!"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "  📝 Config: $WINDSURF_CONFIG"
echo ""
echo "  🔑 API Tokens noch eintragen:"
echo "     - GITHUB_PERSONAL_ACCESS_TOKEN"
echo "     - CLOUDFLARE_API_TOKEN"
echo "     - OUTLINE_API_TOKEN"
echo ""
echo "  🔄 Windsurf neu starten, damit MCP-Server geladen werden!"
echo ""
echo "  📚 Verfügbare MCP-Server:"
echo "     - orchestrator    (Task-Analyse, Agent-Team)"
echo "     - outline-mcp     (Outline Wiki)"
echo "     - github          (GitHub API)"
echo "     - cloudflare-api  (DNS, Tunnels)"
echo ""
