#!/usr/bin/env bash
# =============================================================================
# mcp-wrapper.sh — Startet MCP-Server mit Secrets aus ~/.secrets/
# =============================================================================
# Wird von Windsurf mcp_config.json als command verwendet.
# Lädt Secrets aus Dateien und exportiert sie als Env-Vars.
#
# USAGE in mcp_config.json:
#   "command": "/path/to/mcp-wrapper.sh",
#   "args": ["github"]  oder ["orchestrator"] etc.
# =============================================================================
set -euo pipefail

SECRETS_DIR="$HOME/.secrets"
SERVER="${1:-}"

# ── Load secret from file ────────────────────────────────────────────────────
load_secret() {
    local file="$SECRETS_DIR/$1"
    if [[ -f "$file" ]]; then
        cat "$file" | tr -d '\n'
    fi
}

# ── Export secrets based on server ───────────────────────────────────────────
case "$SERVER" in
    github)
        export GITHUB_PERSONAL_ACCESS_TOKEN="$(load_secret github_token)"
        exec npx -y @modelcontextprotocol/server-github
        ;;
    cloudflare|cloudflare-api)
        export CLOUDFLARE_API_TOKEN="$(load_secret cloudflare_api_token)"
        exec npx -y @anthropic/mcp-cloudflare
        ;;
    outline|outline-mcp)
        export OUTLINE_MCP_OUTLINE_API_TOKEN="$(load_secret outline_api_token)"
        export OUTLINE_MCP_OUTLINE_URL="${OUTLINE_API_URL:-https://outline.iil.pet}"
        cd "$HOME/CascadeProjects/platform/packages/outline-mcp"
        exec "$HOME/CascadeProjects/platform/.venv/bin/python" -m outline_mcp
        ;;
    orchestrator)
        cd "$HOME/CascadeProjects/platform"
        export PYTHONPATH="$HOME/CascadeProjects/platform"
        exec "$HOME/CascadeProjects/platform/.venv/bin/python" -m orchestrator_mcp.server
        ;;
    *)
        echo "Unknown server: $SERVER" >&2
        echo "Available: github, cloudflare, outline, orchestrator" >&2
        exit 1
        ;;
esac
