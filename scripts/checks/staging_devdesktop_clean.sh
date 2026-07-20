#!/bin/bash
# ADR-210 R8, REVIDIERT 2026-07-17 (KONZ-platform-015, #1227) — dev-desktop MAY
# host staging vhosts/containers for repos that declare `staging.host:
# dev-desktop` in registry/canonical.yaml. Original rule ("dev-desktop must be
# completely staging-free, nginx must be inactive") was falsified by live
# evidence: 22 staging vhosts + risk-hub/tax-hub containers have run there,
# nginx active, without incident — the check now enforces "every vhost/
# container on dev-desktop is registry-declared", not "dev-desktop is empty".
set -euo pipefail

DEV_DESKTOP=devuser@88.99.38.75
SSH_OPTS="-o ConnectTimeout=8 -o BatchMode=yes -i ${HOME}/.ssh/id_ed25519"
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

drift=0

VHOSTS=$(ssh $SSH_OPTS "$DEV_DESKTOP" 'ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -E "^staging[-.]" || true')
if [ -n "$VHOSTS" ]; then
  UNDECLARED_VHOSTS=$(cd "$SCRIPT_DIR" && python3 -c "
import sys
sys.path.insert(0, 'tools')
import registry_api as reg

vhosts = '''$VHOSTS'''.strip().splitlines()
canon = reg.load_canonical()
declared_dev_desktop_hosts = set()
for name, e in canon.get('repos', {}).items():
    staging = (e.get('rich') or {}).get('staging') or {}
    if staging.get('host') == 'dev-desktop':
        declared_dev_desktop_hosts.update(staging.get('hostnames', []))
        declared_dev_desktop_hosts.add(f'staging-{name}.iil.pet')

for v in vhosts:
    vhost_name = v.strip()
    base = vhost_name.split('.conf')[0]
    if base and any(base == h or base.startswith(h + '.') for h in declared_dev_desktop_hosts):
        continue
    print(vhost_name)
" 2>&1)
  if [ -n "$UNDECLARED_VHOSTS" ]; then
    echo "R8 FAIL: dev-desktop nginx vhosts without registry \`staging.host: dev-desktop\`:"
    echo "$UNDECLARED_VHOSTS" | sed 's/^/  - /'
    drift=1
  fi
fi

CONTAINERS=$(ssh $SSH_OPTS "$DEV_DESKTOP" 'docker ps --format "{{.Names}}" 2>/dev/null | grep "_staging_" || true')
if [ -n "$CONTAINERS" ]; then
  UNDECLARED_CONTAINERS=$(cd "$SCRIPT_DIR" && python3 -c "
import sys
sys.path.insert(0, 'tools')
import registry_api as reg

names = '''$CONTAINERS'''.strip().splitlines()
canon = reg.load_canonical()
undeclared = []
for name in names:
    if '_staging_' not in name:
        continue
    repo = name.split('_staging_')[0].replace('_', '-')
    e = canon.get('repos', {}).get(repo)
    staging = (e.get('rich') or {}).get('staging') if e else None
    host = (staging or {}).get('host', 'staging-platform')
    if host != 'dev-desktop':
        undeclared.append(f'{name} (repo={repo}, declared host={host})')
for u in undeclared:
    print(u)
" 2>&1)
  if [ -n "$UNDECLARED_CONTAINERS" ]; then
    echo "R8 FAIL: dev-desktop _staging_ containers without registry \`staging.host: dev-desktop\`:"
    echo "$UNDECLARED_CONTAINERS" | sed 's/^/  - /'
    drift=1
  fi
fi

if [ $drift -eq 0 ]; then
  echo "R8 PASS: all dev-desktop staging vhosts/containers are registry-declared"
fi
exit $drift
