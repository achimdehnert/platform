#!/usr/bin/env bash
# prod-offsite-daily.sh — taeglicher Offsite-Lauf (ADR-289 R1, ADR-241 §Rollout)
#
# Sichert nach netcup (rest-server, append-only):
#   1. ALLE laufenden Postgres-Instanzen per pg_dumpall (konsistent, im Gegensatz
#      zur Dateikopie eines laufenden Datenverzeichnisses)
#   2. Datei-Volumes mit Nutzdaten (MinIO, Media)
#
# Die DB-Liste wird zur Laufzeit ERMITTELT, nicht gepflegt — eine feste Liste
# driftet, sobald ein Hub dazukommt oder wegfaellt.
#
# Aufruf ohne Argumente. Fuer Cron gedacht, aber auch von Hand sicher.
# Gibt KEINE Secrets aus (redact-Filter auf allen restic-Aufrufen).

set -uo pipefail

ENV_FILE=/etc/offsite-backup.env
LOG_TAG=offsite-backup

[[ -r "$ENV_FILE" ]] || { echo "FEHLER: $ENV_FILE fehlt — erst prod-offsite-init.sh." >&2; exit 1; }
set -a; . "$ENV_FILE"; set +a

redact() { sed -E 's#(://[^:/@]+):[^@]*@#\1:***@#g'; }
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

rc_total=0

# ─────────────────────────────────────────────────────────────────────────────
log "Postgres-Instanzen sichern (pg_dumpall)"
mapfile -t PGC < <(docker ps --format '{{.Names}}\t{{.Image}}' \
                   | grep -iE 'postgres|pgvector' | cut -f1 | sort)

if [[ ${#PGC[@]} -eq 0 ]]; then
  log "  WARNUNG: keine Postgres-Container gefunden"
  rc_total=1
fi

for c in "${PGC[@]}"; do
  # Superuser ermitteln: die Images setzen POSTGRES_USER, Default ist 'postgres'.
  u=$(docker exec "$c" sh -c 'printf "%s" "${POSTGRES_USER:-postgres}"' 2>/dev/null || echo postgres)
  if docker exec "$c" pg_dumpall -U "$u" 2>/dev/null \
     | restic backup --stdin --stdin-filename "${c}.sql" \
         --tag pgdump --tag "$c" --host prod 2>&1 | redact; then
    log "  ✓ $c (als $u)"
  else
    log "  ✗ $c — Dump oder Upload fehlgeschlagen"
    rc_total=1
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
log "Datei-Volumes mit Nutzdaten sichern"
VOLROOT="$(docker info --format '{{.DockerRootDir}}')/volumes"
TARGETS=()
# Nur Volumes mit echtem Nutzdaten-Charakter. Bewusst KEINE pgdata-Volumes —
# die kommen oben konsistent per pg_dumpall.
while read -r v; do
  d="$VOLROOT/$v/_data"
  [[ -d "$d" ]] && TARGETS+=("$d")
done < <(docker volume ls --format '{{.Name}}' | grep -iE 'minio|media|upload|documents' | sort)

if [[ ${#TARGETS[@]} -gt 0 ]]; then
  if restic backup --tag volumes --host prod "${TARGETS[@]}" 2>&1 | redact; then
    log "  ✓ ${#TARGETS[@]} Volume(s)"
  else
    log "  ✗ Volume-Sicherung fehlgeschlagen"; rc_total=1
  fi
else
  log "  (keine passenden Volumes)"
fi

# ─────────────────────────────────────────────────────────────────────────────
log "Aufraeumen (Retention)"
# Append-only am Server: 'forget --prune' scheitert dort bewusst. Wir markieren
# nur; das tatsaechliche Prune laeuft mit einem GETRENNTEN Zugang auf dem
# Ziel-Host (ADR-289 §4.2) — ein kompromittierter Quell-Host darf nicht loeschen.
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 2>&1 | redact || \
  log "  (forget nicht moeglich — erwartet bei append-only; Prune laeuft am Ziel)"

# ─────────────────────────────────────────────────────────────────────────────
log "Ergebnis"
restic snapshots --compact 2>&1 | redact | tail -15
if [[ $rc_total -ne 0 ]]; then
  log "MIT FEHLERN beendet — der Backup-Meter meldet das als Verletzung."
fi
exit $rc_total
