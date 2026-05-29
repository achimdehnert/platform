#!/bin/bash
# ADR-210 R4 — staging.port ∈ [19000..19999], unique across all repos.
# Dedicated range eliminates collision with prod-port-space and ad-hoc ports.
set -euo pipefail

REG="$(dirname "$0")/../../registry/repos.yaml"

python3 <<PY
import yaml, sys
with open("$REG") as f:
    data = yaml.safe_load(f)

MIN, MAX = 19000, 19999
ports = {}        # port -> repo
violations = []
checked = 0

for d in data.get('domains', []):
    for s in d.get('systems', []):
        if 'staging' not in s:
            continue
        checked += 1
        repo = s['name']
        port = s.get('staging', {}).get('port')
        if port is None:
            violations.append(f"{repo}: missing staging.port")
            continue
        if not (MIN <= port <= MAX):
            violations.append(f"{repo}: port={port} not in [{MIN}..{MAX}]")
            continue
        if port in ports:
            violations.append(f"{repo}: port={port} collides with {ports[port]}")
            continue
        ports[port] = repo

if violations:
    print("R4 FAIL: staging port-range violations:")
    for v in violations:
        print(f"  - {v}")
    sys.exit(1)

print(f"R4 PASS: {checked} staging entries; all ports in [{MIN}..{MAX}], no collisions")
PY
