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

# Erkennung ueber das VERHALTEN, nicht ueber den Namen des Images.
#
# Bis 2026-08-17 filterte hier `docker ps --format '{{.Names}}\t{{.Image}}'`
# auf 'postgres|pgvector'. Die Image-SPALTE von `docker ps` zeigt aber eine
# nackte Image-ID, sobald die urspruengliche Referenz lokal nicht mehr getaggt
# ist (etwa nach einem `docker pull`, der den alten Stand verwaist). Genau das
# passierte: `risk_hub_db` lief unveraendert weiter und erschien als
# `57c72fd2a128` — der Filter griff nicht mehr, und die Datenbank fiel
# lautlos aus dem Backup. Vier Instanzen waren betroffen (risk_hub_db,
# travel_beat_db, wedding_hub_db, iil_dochub_db), risk-hub davon vier Tage
# lang; `docker inspect .Config.Image` sagte die ganze Zeit `postgres:16-alpine`.
#
# `pg_isready` fragt die Sache selbst: antwortet der Container als
# Postgres-Server? Das ist unabhaengig davon, wie sein Image gerade heisst,
# und schliesst zugleich App-Container aus, die nur den Client mitbringen
# (dort findet pg_isready keinen Server auf localhost).
#
# Zweite Bedingung: ein compose-Projekt-Label. Auf diesem Host laufen zeitweise
# Postgres-SERVICE-Container von CI-Jobs (Namen wie
# `81423c76…_postgres16alpine_71ca5d`). Die sind echte Postgres-Server, aber
# Wegwerfware — sie zu sichern ist sinnlos, und ihr Kommen und Gehen wuerde den
# Rueckgang-Waechter unten bei jedem zweiten Lauf fehlalarmieren. Gemessen am
# 2026-08-17: 21 antwortende Server, davon 20 mit Projekt-Label (die echten
# Stacks) und 1 ohne (ein CI-Job). Der alte Image-Filter sicherte solche
# CI-Container mit — und dafuer vier echte Datenbanken nicht.
PGC=()
while read -r c; do
  [[ -n "$c" ]] || continue
  timeout 10 docker exec "$c" pg_isready -q >/dev/null 2>&1 || continue
  projekt=$(docker inspect "$c" \
            --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null)
  [[ -n "$projekt" ]] || { log "  · $c uebersprungen (kein compose-Projekt — CI-Wegwerfcontainer)"; continue; }
  PGC+=("$c")
done < <(docker ps --format '{{.Names}}' | sort)

if [[ ${#PGC[@]} -eq 0 ]]; then
  log "  WARNUNG: keine Postgres-Container gefunden"
  rc_total=1
fi

# Rueckgang-Waechter: der eigentliche Grund, warum das vier Tage unbemerkt
# blieb. Ein Lauf, der WENIGER Datenbanken sichert als der letzte, sieht in
# Log und Exit-Code exakt aus wie ein erfolgreicher — die fehlende Zeile faellt
# niemandem auf. Ein Rueckgang ist ab jetzt ein roter Lauf; ein Zuwachs (neuer
# Hub) laeuft still durch. Faellt eine Instanz absichtlich weg, wird der Stand
# einmal quittiert: Datei loeschen, der naechste Lauf schreibt sie neu.
ZAEHLER_DATEI=/var/lib/offsite-backup/pg-instanzen.zahl
mkdir -p "$(dirname "$ZAEHLER_DATEI")" 2>/dev/null || true
vorher=$(cat "$ZAEHLER_DATEI" 2>/dev/null || echo 0)
if [[ "$vorher" =~ ^[0-9]+$ ]] && (( ${#PGC[@]} < vorher )); then
  log "  FEHLER: nur ${#PGC[@]} Postgres-Instanz(en) gefunden, letzter Lauf hatte $vorher."
  log "          Gesichert wird trotzdem, was da ist — aber hier fehlt etwas."
  log "          Gefunden: ${PGC[*]}"
  rc_total=1
fi
printf '%s' "${#PGC[@]}" > "$ZAEHLER_DATEI" 2>/dev/null || true
log "  ${#PGC[@]} Postgres-Instanz(en) erkannt (Vorlauf: $vorher)"

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
