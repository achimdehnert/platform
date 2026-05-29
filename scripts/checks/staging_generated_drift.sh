#!/bin/bash
# ADR-210 R7 — Generated staging artifacts must be byte-identical to renderer output.
# Iterates all repos with `staging:` block in registry, runs render_staging.py --verify.
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")/.."
REG="$SCRIPT_DIR/../registry/repos.yaml"

REPOS=$(python3 <<PY
import yaml
with open("$REG") as f:
    data = yaml.safe_load(f)
for d in data.get('domains', []):
    for s in d.get('systems', []):
        if 'staging' in s:
            print(s['name'])
PY
)

drift=0
for repo in $REPOS; do
  if ! python3 "$SCRIPT_DIR/render_staging.py" "$repo" --verify; then
    drift=1
  fi
done

if [ $drift -eq 0 ]; then
  echo "R7 PASS: no generated-artifact drift"
fi
exit $drift
