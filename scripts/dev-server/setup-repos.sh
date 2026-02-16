#!/usr/bin/env bash
# setup-repos.sh — Run as deploy user on DEV server
# See ADR-042 for context.
set -euo pipefail

echo "=== ADR-042: Setting up repositories ==="

mkdir -p ~/projects && cd ~/projects

# ── Clone all platform repos ─────────────────────────────────────
repos=(
    "achimdehnert/bfagent"
    "achimdehnert/travel-beat"
    "achimdehnert/mcp-hub"
    "achimdehnert/risk-hub"
    "achimdehnert/weltenhub"
    "achimdehnert/pptx-hub"
    "achimdehnert/trading-hub"
    "achimdehnert/platform"
)

for repo in "${repos[@]}"; do
    name=$(basename "$repo")
    if [ ! -d "$name" ]; then
        echo "Cloning $repo..."
        git clone "git@github.com:${repo}.git"
    else
        echo "Skipping $name (already exists)"
    fi
done

# ── Set up Python virtual environments (idempotent) ──────────────
for name in bfagent travel-beat mcp-hub risk-hub weltenhub pptx-hub trading-hub; do
    if [ -d "$name" ]; then
        cd "$name"
        EXPECTED_PY="$(python3.12 --version 2>/dev/null)"
        CURRENT_PY="$(.venv/bin/python --version 2>/dev/null || echo 'none')"
        if [ "$EXPECTED_PY" != "$CURRENT_PY" ]; then
            echo "Creating venv for $name (${EXPECTED_PY})..."
            python3.12 -m venv .venv --clear
        else
            echo "Venv for $name OK (${CURRENT_PY}), skipping create."
        fi
        source .venv/bin/activate
        pip install --quiet --upgrade pip
        [ -f requirements.txt ] && pip install --quiet -r requirements.txt
        [ -f requirements-dev.txt ] && pip install --quiet -r requirements-dev.txt
        deactivate
        cd ..
    fi
done

echo ""
echo "✅ All repos cloned and venvs created."
