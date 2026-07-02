#!/bin/bash
# ============================================================
# ADR Review Action - Quick Install
# ============================================================
#
# Dieses Script installiert die ADR Review Action im platform Repo
#
# Voraussetzung: 
#   - GitHub CLI (gh) installiert und eingeloggt
#   - ANTHROPIC_API_KEY bereit
#
# ============================================================

set -e

REPO="achimdehnert/platform"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 ADR Review Action - Installation"
echo "===================================="
echo ""

# Check GitHub CLI
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) nicht gefunden."
    echo "   Installiere: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI nicht eingeloggt."
    echo "   Führe aus: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI gefunden und eingeloggt"
echo ""

# API Key
echo "📝 Schritt 1: ANTHROPIC_API_KEY setzen"
echo "   (Falls bereits gesetzt, einfach Enter drücken)"
read -p "   API Key eingeben (sk-ant-...): " API_KEY

if [ -n "$API_KEY" ]; then
    echo "$API_KEY" | gh secret set ANTHROPIC_API_KEY --repo "$REPO"
    echo "   ✅ Secret gesetzt"
else
    echo "   ⏭️  Übersprungen (bereits vorhanden?)"
fi

echo ""

# Copy workflow
echo "📝 Schritt 2: Workflow-Datei kopieren"

# Get repo root
REPO_ROOT=$(gh repo view "$REPO" --json url -q '.url' | sed 's|https://github.com/||')

echo "   Kopiere nach: $REPO/.github/workflows/adr-review.yml"
echo ""
echo "   ⚠️  Bitte manuell kopieren:"
echo "   cp $SCRIPT_DIR/.github/workflows/adr-review.yml /path/to/platform/.github/workflows/"
echo ""

# Done
echo "===================================="
echo "✅ Setup abgeschlossen!"
echo ""
echo "Nächste Schritte:"
echo "  1. Workflow-Datei ins Repo kopieren (siehe oben)"
echo "  2. git add .github/workflows/adr-review.yml"
echo "  3. git commit -m 'feat: Add ADR review action'"
echo "  4. git push"
echo ""
echo "Test:"
echo "  gh workflow run '📋 ADR Architecture Review (Extended)' -f pr_number=<PR_NUMBER>"
echo ""
