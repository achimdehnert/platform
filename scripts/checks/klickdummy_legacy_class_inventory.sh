#!/usr/bin/env bash
# platform/scripts/checks/klickdummy_legacy_class_inventory.sh
# S11 Cross-Repo-Inventur per platform:ADR-211 Rev 12 §Migration.
# Bootstrap-Bash (Fallback); kanonische Implementation: iil_klickdummy.inventory
#
# Exit 0 wenn 0 echte Treffer ⇒ Strict-Mode (LEGACY={}) aktivierbar.
# Exit 1 sonst (+ Liste Repos+Pfade auf stdout).
set -euo pipefail

REPOS_BASE="${REPOS_BASE:-$HOME/github}"
REPOS="${REPOS:-meiki-hub writing-hub risk-hub pptx-hub dev-hub ttz-hub}"
PATTERNS='mock-prototyp|demo-render'

# Beabsichtigte Referenzen ignorieren (LEGACY-Maps, History-Kommentare)
INTENTIONAL_GREP='-v LEGACY|"mock-prototyp":\s*"mock"|"demo-render":\s*"spec-demo"|#\s*vorher\s+(mock-prototyp|demo-render)|\(vorher\s+(mock-prototyp|demo-render)'

FOUND=0
for repo in $REPOS; do
  d="$REPOS_BASE/$repo"
  [[ -d "$d" ]] || { echo "=== $repo: NOT PRESENT (skip) ==="; continue; }
  matches=$(grep -rEn --include='*.yaml' --include='*.yml' --include='*.json' \
            --include='*.md' --include='*.html' --include='*.py' "$PATTERNS" "$d" 2>/dev/null | \
            grep -v 'node_modules\|\.venv\|__pycache__\|/build/\|/dist/\|feedback-log\|_archiv' | \
            grep -Ev 'LEGACY|"mock-prototyp": "mock"|"demo-render": "spec-demo"|# vorher|\(vorher ' || true)
  if [[ -n "$matches" ]]; then
    echo "=== $repo ($(echo "$matches" | wc -l) Treffer) ==="
    echo "$matches" | head -10
    FOUND=1
  else
    echo "=== $repo: ✓ clean ==="
  fi
done

if [[ $FOUND -eq 0 ]]; then
  echo ""
  echo "S11 → 0 echte Drift-Treffer cross-repo. Strict-Mode kann aktiviert werden."
fi
exit $FOUND
