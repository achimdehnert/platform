#!/usr/bin/env bash
# Taegliche, sichere Docker-Praevention fuer dev-desktop (platform#2895 Item 98,
# /infra-cleanup Trockenlauf 2026-09-07: Images 84 GB, davon 74 GB freigebbar;
# Build-Cache 8,3 GB; 8 dangling Images).
#
# NUR zwei Operationen, beide ohne Risiko fuer laufende oder bewusst gestoppte
# Dienste:
#   - docker image prune -f            (NUR dangling Images, kein -a)
#   - docker builder prune -f --keep-storage 10GB
#
# NIE hier: `container prune` (21 gestoppte Container, davon 17 bewusst mit
# restart=no — die duerfen NICHT verschwinden), NIE `volume prune`, NIE
# `image prune -a` ohne Altersfilter (wuerde auch benutzte-aber-nicht-laufende
# Images fuer die 17 gestoppten Container ziehen). Aggressiveres Reclaim bleibt
# Owner-gefuehrt ueber die /infra-cleanup Skill.
set -euo pipefail

log() { echo "[docker-prune] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }

log "start — df vorher:"
df -h / | tail -1

docker image prune -f >/dev/null && log "dangling image prune ok"
docker builder prune -f --keep-storage 10GB >/dev/null && log "builder prune ok (keep 10GB)"

log "ende — df nachher:"
df -h / | tail -1
