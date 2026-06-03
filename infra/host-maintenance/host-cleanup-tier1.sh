#!/usr/bin/env bash
# Unattended SAFE host disk cleanup — mirrors /infra-cleanup Tier 1 + conservative
# image GC. Designed for the systemd timer (no human present), so it does ONLY
# operations that cannot lose service data or interrupt a running CI job:
#   - prune stopped containers, dangling images, build cache
#   - prune UNUSED images older than 30 days (>720h) — never recent ones
#   - clear runner _work/_temp ONLY when no runner job is active
# It NEVER touches: named volumes, _tool/_actions caches, in-flight job _work,
# or images younger than 30 days. Aggressive reclaim (image prune -a no-filter,
# full _work) stays human-driven via the /infra-cleanup skill.
set -euo pipefail

log() { echo "[infra-cleanup] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }

log "start — df:"; df -h / | tail -1

docker container prune -f       >/dev/null && log "container prune ok"
docker image prune -f           >/dev/null && log "dangling image prune ok"
docker builder prune -f         >/dev/null && log "builder prune ok"
docker image prune -a -f --filter "until=720h" >/dev/null && log "image prune (>30d unused) ok"

# Runner _work/_temp only when idle (racy check is acceptable for _temp only —
# transient per-job scratch; never the checkouts/_tool here).
if ! pgrep -f Runner.Worker >/dev/null 2>&1; then
  find /opt/actions-runner-*/_work -mindepth 2 -maxdepth 2 -name _temp -type d \
    -exec rm -rf {} + 2>/dev/null || true
  log "runner _temp cleared (idle)"
else
  log "runner busy — skipped _work"
fi

log "done — df:"; df -h / | tail -1
