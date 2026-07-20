#!/bin/bash
# ADR-210 R6 — Authentik staging providers must redirect to staging-{repo}.iil.pet
# (or to a hostname listed in registry staging.hostnames for that repo).
set -euo pipefail

PROD_HOST=root@88.198.191.108
REG="$(dirname "$0")/../../registry/repos.yaml"

# Get OIDC providers + redirects from authentik
RAW=$(ssh -o ConnectTimeout=20 -o BatchMode=yes "$PROD_HOST" \
  'docker exec iil_authentik_server ak shell -c "
from authentik.providers.oauth2.models import OAuth2Provider
import json
out=[]
for p in OAuth2Provider.objects.all():
    uris=[r.url for r in p.redirect_uris]
    out.append({\"name\": p.name, \"client_id\": p.client_id, \"redirects\": uris})
print(\"@@@\"+json.dumps(out)+\"@@@\")" 2>/dev/null')

DATA=$(echo "$RAW" | python3 -c "import sys,re; m=re.search(r'@@@(.*?)@@@', sys.stdin.read(), re.S); print(m.group(1) if m else '[]')")

# DATA/REG via Env statt String-Interpolation ins Heredoc (Bug: JSON-Escapes wie
# \/ sind keine gueltigen Python-String-Escapes -> "Invalid \escape" bei jedem
# echten Redirect-URI-Fund; deshalb lief dieses Skript nie durch).
DATA="$DATA" REG="$REG" python3 <<'PY'
import yaml, json, os, sys
data = json.loads(os.environ["DATA"])
with open(os.environ["REG"]) as f:
    reg = yaml.safe_load(f)

# Build allowed hostnames per repo
allowed = {}
for d in reg.get('domains', []):
    for s in d.get('systems', []):
        if 'staging' in s:
            allowed[s['name']] = set(s['staging'].get('hostnames', []) + [f"staging-{s['name']}.iil.pet"])

drift = []
unchecked_staging = []
for p in data:
    name = p['name']
    if 'staging' not in name.lower():
        continue
    # extract repo name: "{repo}-staging OIDC Provider" or "{repo} ... staging ..."
    base = name.split(' OIDC')[0].replace(' ', '-').lower()
    repo = base.removesuffix('-staging')
    if repo not in allowed:
        unchecked_staging.append(f"{name} (repo '{repo}' not in registry yet)")
        continue
    valid_hosts = allowed[repo]
    for r in p['redirects']:
        host = r.split('://')[1].split('/')[0] if '://' in r else r
        if host not in valid_hosts:
            drift.append(f"{name}: redirect {r} (host '{host}' not in registry)")

if drift:
    print("R6 FAIL: OIDC redirect schema drift:")
    for d in drift:
        print(f"  - {d}")
    sys.exit(1)
if unchecked_staging:
    print("R6 INFO: staging providers without registry entry yet:")
    for u in unchecked_staging:
        print(f"  - {u}")
print(f"R6 PASS: all registered staging OIDC providers redirect to allowed hostnames")
PY
