#!/usr/bin/env bash
# docker-id-name-log.sh — Container-ID → Name-Zuordnung protokollieren.
#
# Motiv (platform#1303): Kernel-OOM-Meldungen benennen ausschliesslich die
# cgroup, also die volle Container-ID:
#
#   oom-kill:constraint=CONSTRAINT_MEMCG,...,oom_memcg=/system.slice/
#   docker-7c29b3a246fec3ab171267b02fd85df628d1ecb37dd5817854e3796bbe2d123a.scope
#
# Sobald der Container weg ist (entfernt, neu erzeugt, Deploy), ist diese ID
# nicht mehr aufloesbar — `docker ps -a` kennt sie nicht mehr, und Docker
# bewahrt keine Historie auf. Der OOM ist damit im Nachhinein anonym.
#
# Genau daran ist die Analyse des trading-hub-Ausfalls vom 2026-07-20
# gescheitert: Ausfallfenster und OOM-Fenster waren belegbar, die Zuordnung
# "welcher Container" nicht. Dieses Skript schliesst die Luecke, indem es
# stuendlich einen Schnappschuss der Zuordnung wegschreibt.
#
# Installation (Host, siehe docs/runbooks/docker-id-name-log.md):
#   /opt/scripts/docker-id-name-log.sh
#   crontab:  7 * * * * /opt/scripts/docker-id-name-log.sh
#
# Read-only gegenueber Docker — ruft ausschliesslich `docker ps` auf.

set -euo pipefail

LOG_DIR="${DOCKER_ID_NAME_LOG_DIR:-/var/log/docker-id-name}"
RETENTION_DAYS="${DOCKER_ID_NAME_RETENTION_DAYS:-30}"

mkdir -p "$LOG_DIR"

STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TARGET="$LOG_DIR/$(date -u +%Y-%m-%d).log"

# Volle (nicht gekuerzte) IDs — der Kernel loggt die volle ID, eine gekuerzte
# waere fuer den Abgleich wertlos. Auch gestoppte Container mitnehmen (-a):
# ein Container kann zwischen zwei Laeufen sterben und trotzdem der Gesuchte sein.
docker ps -a --no-trunc --format '{{.ID}} {{.Names}} {{.State}}' \
  | while read -r line; do
      printf '%s %s\n' "$STAMP" "$line"
    done >> "$TARGET"

# Aufbewahrung begrenzen. -mtime statt Dateiname parsen, damit auch
# manuell abgelegte Dateien erfasst werden.
find "$LOG_DIR" -maxdepth 1 -type f -name '*.log' -mtime "+${RETENTION_DAYS}" -delete
