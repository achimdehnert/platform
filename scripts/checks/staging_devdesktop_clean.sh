#!/bin/bash
# ADR-210 R8 — dev-desktop has no staging-*.conf in nginx and no *_staging_* containers.
set -euo pipefail

DEV_DESKTOP=devuser@88.99.38.75
SSH_OPTS="-o ConnectTimeout=8 -o BatchMode=yes -i ${HOME}/.ssh/id_ed25519"

drift=0

VHOSTS=$(ssh $SSH_OPTS "$DEV_DESKTOP" 'ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -E "^staging[-.]" || true')
if [ -n "$VHOSTS" ]; then
  echo "R8 FAIL: dev-desktop has staging vhosts (must be on staging-platform):"
  echo "$VHOSTS" | sed 's/^/  - /'
  drift=1
fi

NGINX_ACTIVE=$(ssh $SSH_OPTS "$DEV_DESKTOP" 'systemctl is-active nginx 2>/dev/null || echo inactive')
if [ "$NGINX_ACTIVE" = "active" ]; then
  echo "R8 FAIL: nginx is active on dev-desktop (should be inactive — pure dev machine)"
  drift=1
fi

CONTAINERS=$(ssh $SSH_OPTS "$DEV_DESKTOP" 'docker ps --format "{{.Names}}" 2>/dev/null | grep "_staging_" || true')
if [ -n "$CONTAINERS" ]; then
  echo "R8 FAIL: dev-desktop has _staging_ containers:"
  echo "$CONTAINERS" | sed 's/^/  - /'
  drift=1
fi

if [ $drift -eq 0 ]; then
  echo "R8 PASS: dev-desktop is clean (no staging vhosts, no staging containers, nginx inactive)"
fi
exit $drift
