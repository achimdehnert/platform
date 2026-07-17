#!/bin/bash
# ADR-210 R2, REVIDIERT 2026-07-17 (KONZ-platform-015, #1227) — staging containers
# run on staging-platform by default, OR on a registry-declared alternate host
# (`staging.host` in registry/canonical.yaml). Never on prod, never on an
# undeclared host. Original rule ("staging-platform only, no exceptions") was
# falsified by live evidence: risk-hub/tax-hub run staging on dev-desktop, and
# have for some time, without incident — a blanket ban would have permanently
# red-flagged accepted architecture instead of catching real drift.
set -euo pipefail

PROD_HOST=root@88.198.191.108
DEV_DESKTOP=devuser@88.99.38.75
SSH_OPTS="-o ConnectTimeout=8 -o BatchMode=yes"
DEV_KEY="-i ${HOME}/.ssh/id_ed25519"
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

drift=0

# Prod is never an allowed staging host — no registry override changes this.
FOUND_PROD=$(ssh $SSH_OPTS "$PROD_HOST" 'docker ps --format "{{.Names}}" 2>/dev/null | grep "_staging_" || true')
if [ -n "$FOUND_PROD" ]; then
  echo "R2 FAIL: \`*_staging_*\` containers on prod (never allowed):"
  echo "$FOUND_PROD" | sed 's/^/  - /'
  drift=1
fi

FOUND_DEVDESKTOP=$(ssh $SSH_OPTS $DEV_KEY "$DEV_DESKTOP" 'docker ps --format "{{.Names}}" 2>/dev/null | grep "_staging_" || true')
if [ -n "$FOUND_DEVDESKTOP" ]; then
  UNDECLARED=$(cd "$SCRIPT_DIR" && python3 -c "
import sys
sys.path.insert(0, 'tools')
import registry_api as reg

names = '''$FOUND_DEVDESKTOP'''.strip().splitlines()
canon = reg.load_canonical()
undeclared = []
for name in names:
    # tax_hub_staging_web -> repo 'tax-hub' (strip trailing _staging_<role>)
    if '_staging_' not in name:
        continue
    repo_part = name.split('_staging_')[0]
    repo = repo_part.replace('_', '-')
    e = canon.get('repos', {}).get(repo)
    staging = (e.get('rich') or {}).get('staging') if e else None
    host = (staging or {}).get('host', 'staging-platform')
    if host != 'dev-desktop':
        undeclared.append(f'{name} (repo={repo}, declared host={host})')
for u in undeclared:
    print(u)
" 2>&1)
  if [ -n "$UNDECLARED" ]; then
    echo "R2 FAIL: \`*_staging_*\` containers on dev-desktop without registry \`staging.host: dev-desktop\`:"
    echo "$UNDECLARED" | sed 's/^/  - /'
    drift=1
  fi
fi

if [ $drift -eq 0 ]; then
  echo "R2 PASS: no staging containers on prod; dev-desktop containers all registry-declared"
fi
exit $drift
