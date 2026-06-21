#!/bin/bash
# offsite-backup.sh — ADR-241 §2: einheitlicher Offsite-Transport via restic.
#
# Schiebt die lokal erzeugten Backups (pro App von deren backup.sh nach
# /opt/backups/<app>/ gelegt) nächtlich verschlüsselt + dedupliziert auf die
# Hetzner Storage Box. Erzeugung bleibt dezentral (App-Skripte); dieser Wrapper
# ist nur der Transport + die Retention.
#
# ── Secrets (NIE hardcoden, NIE echoen; ADR-045 / ~/.secrets) ───────────────
#   RESTIC_REPOSITORY       z. B. sftp:u123456@u123456.your-storagebox.de:/restic
#   RESTIC_PASSWORD_FILE    Pfad zur Key-Datei (Key-Escrow ≥2 Orte: Host + ~/.secrets)
#   Quelle der Variablen: /etc/offsite-backup.env (root:root 600), das aus
#   ~/.secrets/ befüllt wird — dieser Pfad ist die EINZIGE Stelle, an der die
#   Storage-Box-Credentials liegen; bewusst NICHT der Hetzner-Cloud-Token
#   (Blast-Radius-Trennung).
#
# ── Key-Escrow (Pflicht, ADR-241 §2) ────────────────────────────────────────
#   Der restic-Repo-Schlüssel MUSS an ≥2 Orten existieren: auf dem Prod-Host
#   (für den nächtlichen Push) UND in ~/.secrets (SOPS-kompatibel). Läge er nur
#   auf dem Host, machte Host-Verlust die Offsite-Backups unlesbar — genau das
#   Risiko, das dieses ADR adressiert. Restore beginnt mit "Key beschaffen".
#
# ── Installation (by construction; ADR-241 §3) ──────────────────────────────
#   cp deployment/scripts/offsite-backup.sh /etc/cron.daily/zz-offsite-backup
#   chmod +x /etc/cron.daily/zz-offsite-backup
#   (zz- = läuft NACH den App-Backups in cron.daily, alphabetisch zuletzt)
#
# Retention: 7 daily / 4 weekly / 6 monthly (restic forget policy).
set -euo pipefail

ENV_FILE="${OFFSITE_ENV_FILE:-/etc/offsite-backup.env}"
SOURCE_ROOT="${OFFSITE_SOURCE_ROOT:-/opt/backups}"
LOG_TAG="offsite-backup"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ${LOG_TAG}: $*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

command -v restic >/dev/null 2>&1 || fail "restic nicht installiert (apt-get install restic)"

# Secrets aus der Env-Datei laden (nie ins Repo, nie nach stdout)
[ -f "$ENV_FILE" ] || fail "Secrets-Datei $ENV_FILE fehlt — aus ~/.secrets befüllen (ADR-045)"
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY nicht gesetzt}"
: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE nicht gesetzt}"
[ -r "$RESTIC_PASSWORD_FILE" ] || fail "RESTIC_PASSWORD_FILE nicht lesbar (Key-Escrow prüfen)"

# Repo initialisieren, falls noch nicht vorhanden (idempotent)
if ! restic cat config >/dev/null 2>&1; then
  log "restic-Repo nicht initialisiert — init"
  restic init
fi

# Jede App unter SOURCE_ROOT als eigener, getaggter Snapshot (Tag = App-Name).
# Der Meter (tools/backup_meter.py) prüft je Soll-App den jüngsten Snapshot mit
# diesem Tag — der Tag ist also der Vertrag zwischen Wrapper und Meter.
shopt -s nullglob
rc=0
for dir in "$SOURCE_ROOT"/*/; do
  app="$(basename "$dir")"
  if [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
    log "WARN: $dir leer — übersprungen (App-backup.sh lief nicht?)"
    continue
  fi
  log "backup $app …"
  if restic backup --tag "$app" --host "$(hostname -s)" "$dir"; then
    log "OK: $app"
  else
    log "FAIL: $app (restic backup rc=$?)"
    rc=1
  fi
done

# Retention einmal global anwenden (forget + prune)
log "forget/prune (7d/4w/6m) …"
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune || rc=1

log "fertig (rc=$rc)"
exit $rc
