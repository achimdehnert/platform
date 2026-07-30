#!/usr/bin/env bash
# prod-offsite-init.sh — Quell-Seite der Offsite-Sicherung (ADR-289 R1, Phase 5/6)
#
# Installiert restic auf dem Prod-Host, initialisiert das Repository auf dem
# netcup-Ziel (rest-server, append-only) und sichert die Kundendokumente.
#
# Gegenstueck: infra/host-maintenance/netcup-restserver.sh (Ziel-Seite).
# Idempotent. Gibt KEINE Secrets auf stdout aus — nur Pfade.
#
# Voraussetzung: /root/rest-user.pass (Basic-Auth-Kennung, per scp vom Ziel-Host)
#                /etc/restic-netcup-ca.pem (Zertifikat des Ziel-Hosts)

set -euo pipefail

ENV_FILE=/etc/offsite-backup.env
PASS_FILE=/etc/restic-repo.pass
CA_FILE=/etc/restic-netcup-ca.pem
AUTH_FILE=/root/rest-user.pass
REST_HOST="${REST_HOST:-152.53.136.219}"
REST_USER="${REST_USER:-prod-backup}"

log() { printf '\n=== %s\n' "$*"; }

[[ "$(id -u)" -eq 0 ]] || { echo "FEHLER: root noetig." >&2; exit 1; }
[[ -f "$CA_FILE" ]] || { echo "FEHLER: $CA_FILE fehlt." >&2; exit 1; }

log "1. restic"
if command -v restic >/dev/null 2>&1; then
  echo "  ✓ $(restic version 2>/dev/null | head -1)"
else
  apt-get update -qq && apt-get install -y -qq restic
  echo "  → $(restic version 2>/dev/null | head -1)"
fi

log "2. Repository-Passwort"
if [[ -s "$PASS_FILE" ]]; then
  echo "  ✓ vorhanden ($PASS_FILE)"
else
  ( umask 077; openssl rand -base64 32 > "$PASS_FILE" )
  chmod 600 "$PASS_FILE"
  echo "  → erzeugt ($PASS_FILE, 0600)"
fi

log "3. Umgebung"
if [[ -s "$ENV_FILE" ]]; then
  echo "  ✓ vorhanden ($ENV_FILE)"
else
  [[ -s "$AUTH_FILE" ]] || { echo "FEHLER: $AUTH_FILE fehlt (Kennung vom Ziel-Host)." >&2; exit 1; }
  # Die Kennung wird direkt aus der Datei in die env-Datei geschrieben; sie
  # passiert weder stdout noch die Prozessliste.
  ( umask 077
    { printf 'RESTIC_REPOSITORY=rest:https://%s:' "$REST_USER"
      tr -d '\n' < "$AUTH_FILE"
      printf '@%s:8443/\n' "$REST_HOST"
      printf 'RESTIC_PASSWORD_FILE=%s\n' "$PASS_FILE"
      printf 'RESTIC_CACERT=%s\n' "$CA_FILE"
    } > "$ENV_FILE" )
  chmod 600 "$ENV_FILE"
  shred -u "$AUTH_FILE" 2>/dev/null || rm -f "$AUTH_FILE"
  echo "  → geschrieben (0600); Kennungs-Zwischendatei geloescht"
fi

set -a; . "$ENV_FILE"; set +a

# restic gibt bei Fehlern die VOLLSTAENDIGE Repository-URL aus — inklusive der
# Basic-Auth-Kennung. Realfall 2026-07-30: ein Parse-Fehler schrieb die Kennung
# im Klartext ins Terminal, sie musste rotiert werden. Deshalb laeuft jede
# restic-Ausgabe durch diesen Filter. Die Ursache des Parse-Fehlers ist ebenfalls
# behoben: die Kennung wird jetzt hex-kodiert erzeugt (openssl rand -hex), also
# ohne '/' und '+', die in einer URL Sonderbedeutung haben.
redact() { sed -E 's#(://[^:/@]+):[^@]*@#\1:***@#g'; }

log "4. Repository"
if restic snapshots >/dev/null 2>&1; then
  echo "  ✓ existiert und ist lesbar"
else
  restic init 2>&1 | redact
  echo "  → initialisiert"
fi

log "5. Kundendokumente sichern"
# Bewusst NUR Datei-Volumes. Ein laufendes Postgres-Datenverzeichnis per
# Dateikopie zu sichern ergibt einen inkonsistenten Stand — pgdata gehoert
# per pg_dump gesichert, das ist ein eigener Schritt.
VOLROOT="$(docker info --format '{{.DockerRootDir}}')/volumes"
TARGETS=()
for v in risk-hub_risk_hub_minio_data risk-hub_risk_hub_media; do
  d="$VOLROOT/$v/_data"
  if [[ -d "$d" ]]; then TARGETS+=("$d"); else echo "  ⚠ nicht gefunden: $v"; fi
done
[[ ${#TARGETS[@]} -gt 0 ]] || { echo "FEHLER: keine Ziele gefunden." >&2; exit 1; }
echo "  Ziele: ${TARGETS[*]}"
restic backup --tag risk-hub --tag kundendokumente --host prod "${TARGETS[@]}" 2>&1 | redact

log "6. Nachweis"
restic snapshots --compact 2>&1 | redact

cat <<'HINWEIS'

  ⚠ Das Repository-Passwort liegt unter /etc/restic-repo.pass NUR auf diesem Host.
  Geht dieser Host verloren, ist die Sicherung ohne das Passwort unbrauchbar —
  genau der Fall, fuer den sie gemacht ist. Es gehoert an einen dritten Ort.

  Noch offen: pgdata per pg_dump (Schritt 5 sichert bewusst nur Datei-Volumes),
  Cron-Aktivierung von offsite-backup.sh, Feuerübung G3 (Cross-Host-Restore).

HINWEIS
