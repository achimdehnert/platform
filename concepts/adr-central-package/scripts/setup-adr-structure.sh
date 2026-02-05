#!/bin/bash
# scripts/setup-adr-structure.sh
#
# Erstellt die zentralisierte ADR-Ordnerstruktur.
#
# Usage:
#   ./scripts/setup-adr-structure.sh

set -euo pipefail

ADR_ROOT="docs/adr"

echo "🏗️ Setting up centralized ADR structure..."

# Create main directories
SCOPES="drafts core bfagent travel-beat mcp-hub risk-hub cad-hub pptx-hub shared"

for scope in $SCOPES; do
    mkdir -p "$ADR_ROOT/$scope"
    echo "  ✓ Created $ADR_ROOT/$scope/"
done

# Create archive directories
for scope in core bfagent travel-beat mcp-hub risk-hub cad-hub pptx-hub shared; do
    mkdir -p "$ADR_ROOT/_archive/$scope"
done
echo "  ✓ Created $ADR_ROOT/_archive/ structure"

# Add .gitkeep to empty directories
find "$ADR_ROOT" -type d -empty -exec touch {}/.gitkeep \;
echo "  ✓ Added .gitkeep files"

# Copy templates if they exist in package but not in target
if [ ! -f "$ADR_ROOT/TEMPLATE.md" ]; then
    if [ -f "$(dirname "$0")/../docs/adr/TEMPLATE.md" ]; then
        cp "$(dirname "$0")/../docs/adr/TEMPLATE.md" "$ADR_ROOT/"
        echo "  ✓ Copied TEMPLATE.md"
    fi
fi

if [ ! -f "$ADR_ROOT/TRIAGE.md" ]; then
    if [ -f "$(dirname "$0")/../docs/adr/TRIAGE.md" ]; then
        cp "$(dirname "$0")/../docs/adr/TRIAGE.md" "$ADR_ROOT/"
        echo "  ✓ Copied TRIAGE.md"
    fi
fi

echo ""
echo "✅ ADR structure created!"
echo ""
echo "Directory layout:"
echo "  $ADR_ROOT/"
echo "  ├── drafts/       # New ADRs (work in progress)"
echo "  ├── core/         # Platform infrastructure (001-019)"
echo "  ├── bfagent/      # BF Agent app (020-029)"
echo "  ├── travel-beat/  # Travel-Beat app (030-039)"
echo "  ├── mcp-hub/      # MCP Hub (040-049)"
echo "  ├── risk-hub/     # Risk Hub (050-059)"
echo "  ├── cad-hub/      # CAD Hub (060-069)"
echo "  ├── pptx-hub/     # PPTX Hub (070-079)"
echo "  ├── shared/       # Cross-app (080-099)"
echo "  ├── _archive/     # Superseded/Deprecated"
echo "  ├── TEMPLATE.md   # ADR template"
echo "  └── TRIAGE.md     # Scope selection guide"
echo ""
echo "Next steps:"
echo "  1. Move existing ADRs to appropriate scope directories"
echo "  2. Run: python3 scripts/generate-adr-index.py"
echo "  3. Commit: git add docs/adr && git commit -m 'chore: Setup centralized ADR structure'"
