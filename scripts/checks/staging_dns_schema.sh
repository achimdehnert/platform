#!/bin/bash
# ADR-210 R1 — Staging DNS schema is exactly `staging-{repo}.iil.pet`.
# Fails if any *-staging.iil.pet record exists in CF zone iil.pet.
set -euo pipefail

TOKEN=${CLOUDFLARE_WRITE_TOKEN:-$(cat ~/.secrets/cloudflare_write_token 2>/dev/null || true)}
[ -n "$TOKEN" ] || { echo "R1 SKIP: no cloudflare token"; exit 0; }

ZONE_ID=$(curl -fsS -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones?name=iil.pet" \
  | python3 -c "import json,sys;r=json.load(sys.stdin)['result'];print(r[0]['id'] if r else '')")
[ -n "$ZONE_ID" ] || { echo "R1 ERROR: zone iil.pet not found"; exit 2; }

VIOLATIONS=$(curl -fsS -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?per_page=300" \
  | python3 -c "
import json,sys
data=json.load(sys.stdin)
viol=[r['name'] for r in data.get('result',[]) if '-staging.iil.pet' in r['name']]
print('\n'.join(viol))")

if [ -n "$VIOLATIONS" ]; then
  echo "R1 FAIL: found \`*-staging.iil.pet\` records (must be \`staging-*.iil.pet\`):"
  echo "$VIOLATIONS" | sed 's/^/  - /'
  exit 1
fi
echo "R1 PASS: no *-staging.iil.pet drift records"
