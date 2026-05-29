#!/bin/bash
# ADR-210 R3 — Staging containers must be named `{repo}_staging_{role}`.
# role ∈ {web, worker, beat, db, redis, minio, celery, celery_beat}
set -euo pipefail

STAGING_HOST=root@178.104.184.168
ALLOWED='_(web|worker|beat|db|redis|minio|celery|celery_beat)$'

NAMES=$(ssh -o ConnectTimeout=8 -o BatchMode=yes "$STAGING_HOST" \
  'docker ps --format "{{.Names}}" 2>/dev/null | grep "_staging_" || true')

if [ -z "$NAMES" ]; then
  echo "R3 SKIP: no staging containers running yet on staging-platform"
  exit 0
fi

drift=0
while IFS= read -r name; do
  if ! echo "$name" | grep -qE "$ALLOWED"; then
    echo "R3 FAIL: container '$name' does not match {repo}_staging_{role}"
    drift=1
  fi
done <<< "$NAMES"

if [ $drift -eq 0 ]; then
  echo "R3 PASS: all staging containers follow naming pattern"
fi
exit $drift
