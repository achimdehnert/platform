#!/usr/bin/env bash
# Bash-Bootstrap-Fallback. Kanonisch: `klickdummy-inventory` (iil-klickdummy pip-Paket).
set -euo pipefail
REPOS_BASE="${REPOS_BASE:-$HOME/github}"
REPOS="${REPOS:-meiki-hub writing-hub risk-hub pptx-hub dev-hub ttz-hub}"
FOUND=0
for repo in $REPOS; do
  d="$REPOS_BASE/$repo"
  [[ -d "$d" ]] || { echo "=== $repo: NOT PRESENT ==="; continue; }
  matches=$(grep -rEn --include='*.yaml' --include='*.yml' --include='*.json' \
            --include='*.md' --include='*.html' --include='*.py' 'mock-prototyp|demo-render' "$d" 2>/dev/null | \
            grep -v 'node_modules\|\.venv\|__pycache__\|/build/\|/dist/\|feedback-log\|_archiv' | \
            grep -Ev 'LEGACY|"mock-prototyp": "mock"|"demo-render": "spec-demo"|# vorher|\(vorher ' || true)
  if [[ -n "$matches" ]]; then echo "=== $repo ==="; echo "$matches" | head -10; FOUND=1
  else echo "=== $repo: ✓ clean ==="; fi
done
[[ $FOUND -eq 0 ]] && echo -e "\nS11 → 0 echte Drift-Treffer cross-repo."
exit $FOUND
