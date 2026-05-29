#!/bin/bash
# ADR-210 R2 — All `*_staging_*` containers run only on staging-platform.
# Fails if such containers exist on prod or dev-desktop.
set -euo pipefail

PROD_HOST=root@88.198.191.108
DEV_DESKTOP=devuser@88.99.38.75
SSH_OPTS="-o ConnectTimeout=8 -o BatchMode=yes"
DEV_KEY="-i ${HOME}/.ssh/id_ed25519"

drift=0

check_host() {
  local label="$1"; shift
  local found
  found=$(ssh $SSH_OPTS "$@" 'docker ps --format "{{.Names}}" 2>/dev/null | grep "_staging_" || true')
  if [ -n "$found" ]; then
    echo "R2 FAIL: \`*_staging_*\` containers on $label (must only run on staging-platform):"
    echo "$found" | sed 's/^/  - /'
    drift=1
  fi
}

check_host "prod" "$PROD_HOST"
check_host "dev-desktop" $DEV_KEY "$DEV_DESKTOP"

if [ $drift -eq 0 ]; then
  echo "R2 PASS: no staging containers outside staging-platform"
fi
exit $drift
