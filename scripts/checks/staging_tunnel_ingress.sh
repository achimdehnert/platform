#!/bin/bash
# ADR-210 R5 — bf-staging tunnel ingress is catch-all `https://localhost:443`.
set -euo pipefail

STAGING_HOST=root@178.104.184.168
CFG=$(ssh -o ConnectTimeout=8 -o BatchMode=yes "$STAGING_HOST" 'cat /etc/cloudflared/config.yml 2>/dev/null')

if [ -z "$CFG" ]; then
  echo "R5 FAIL: cloudflared config not readable on staging-platform"
  exit 1
fi

# Last ingress rule must be catch-all https://localhost:443 (no hostname-restricted rules in front)
LAST=$(echo "$CFG" | python3 -c "
import sys, yaml
d = yaml.safe_load(sys.stdin)
ing = d.get('ingress', [])
if not ing:
    print('FAIL:no_ingress'); sys.exit()
last = ing[-1]
if 'hostname' in last:
    print('FAIL:catch_all_missing'); sys.exit()
if last.get('service') != 'https://localhost:443':
    print(f'FAIL:wrong_service:{last.get(\"service\")}'); sys.exit()
# Reject hostname-specific overrides (this strategy uses single catch-all)
if any('hostname' in r for r in ing[:-1]):
    print('WARN:hostname_specific_rules_present'); sys.exit()
print('OK')
")

if [[ "$LAST" == OK* ]]; then
  echo "R5 PASS: bf-staging tunnel = catch-all https://localhost:443"
  exit 0
elif [[ "$LAST" == WARN* ]]; then
  echo "R5 WARN: $LAST"
  exit 0
else
  echo "R5 FAIL: $LAST"
  exit 1
fi
