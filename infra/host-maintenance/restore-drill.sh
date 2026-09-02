#!/usr/bin/env bash
# restore-drill.sh — ADR-241 §5 Restore-Feuerübung, ein Kommando (#2284 K4).
#
# Läuft AUF dem Prod-Host, wird aber nicht dort abgelegt: `make restore-drill`
# pipet diese Datei per `ssh … bash -s` hinüber. Damit gibt es keine Host-Kopie,
# die vom IaC-Stand abweichen könnte (🌀 host_fix_must_mirror_to_iac).
#
# Ablauf: jüngsten pg_dumpall-Snapshot des Containers aus dem Offsite-Repo
# holen → Wegwerf-Postgres mit demselben Image starten → Dump einspielen →
# Zeilen einer benannten Tabelle gegen die laufende Prod-Instanz zählen →
# Protokoll (Markdown) auf STDOUT → alles wieder abräumen (trap, auch bei Fehler).
#
# Alles außer dem Protokoll geht nach stderr; stdout ist die Datei, die der
# Aufrufer unter docs/runbooks/restore-drills/ ablegt und die backup_meter.py
# als Nachweis (< 100 Tage) liest.
#
# Aufruf: bash -s -- <container> <datenbank> <tabelle>
set -uo pipefail
APP_CTR="${1:-risk_hub_db}"
DB="${2:-risk_hub}"
TABLE="${3:-dsb_technical_measure}"
ENV_FILE=/etc/offsite-backup.env
BASE=/mnt/HC_Volume_105908261/restore-drill   # 344-GB-Volume, nicht die Root-Platte
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DIR="$BASE/$STAMP"
NAME="restore-drill-$STAMP"
RTO_SOLL_H=4

err() { printf '%s\n' "$*" >&2; }
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$DIR"
}
trap cleanup EXIT

[[ -f "$ENV_FILE" ]] || { err "kein $ENV_FILE"; exit 2; }
IMAGE=$(docker inspect "$APP_CTR" --format '{{.Config.Image}}') || { err "Container $APP_CTR unbekannt"; exit 2; }
PGUSER=$(docker inspect "$APP_CTR" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_USER=//p')
[[ -n "$PGUSER" ]] || { err "POSTGRES_USER nicht am Container"; exit 2; }

T0=$(date +%s)
set -a; . "$ENV_FILE"; set +a
SNAP_JSON=$(restic snapshots --json --tag "$APP_CTR" --latest 1 2>/dev/null)
SNAP_ID=$(python3 -c 'import json,sys; s=json.load(sys.stdin); print(s[-1]["short_id"] if s else "")' <<<"$SNAP_JSON")
SNAP_TIME=$(python3 -c 'import json,sys; s=json.load(sys.stdin); print(s[-1]["time"][:19] if s else "")' <<<"$SNAP_JSON")
[[ -n "$SNAP_ID" ]] || { err "kein Snapshot mit Tag $APP_CTR"; exit 2; }

mkdir -p "$DIR/dump" "$DIR/pgdata"
restic restore "$SNAP_ID" --target "$DIR/dump" </dev/null >/dev/null 2>&1 || { err "restic restore fehlgeschlagen"; exit 2; }
DUMP=$(find "$DIR/dump" -name "${APP_CTR}.sql" | head -1)
[[ -s "$DUMP" ]] || { err "Dump ${APP_CTR}.sql nicht im Snapshot"; exit 2; }
DUMP_MB=$(du -m "$DUMP" | cut -f1)

# Passwort nur für diesen Wegwerf-Container, nie ausgegeben.
PW=$(tr -dc 'A-Za-z0-9' </dev/urandom | dd bs=24 count=1 2>/dev/null)
docker run -d --name "$NAME" \
  -e POSTGRES_PASSWORD="$PW" -e POSTGRES_USER="$PGUSER" \
  -v "$DIR/pgdata:/var/lib/postgresql/data" -v "$DIR/dump:/restore:ro" \
  "$IMAGE" </dev/null >/dev/null 2>&1 || { err "docker run fehlgeschlagen"; exit 2; }
for _ in $(seq 1 90); do
  docker exec "$NAME" pg_isready -q -U "$PGUSER" >/dev/null 2>&1 && break
  sleep 1
done
docker exec "$NAME" pg_isready -q -U "$PGUSER" >/dev/null 2>&1 || { err "Wegwerf-Postgres wurde nicht bereit"; exit 2; }

T_LOAD0=$(date +%s)
# pg_dumpall enthält CREATE ROLE/CREATE DATABASE; Rolle und DB existieren durch
# das Image-Init bereits → diese zwei "already exists" sind erwartet, alles
# andere zählt.
# KEIN `docker exec -i`: das Skript kommt per `bash -s` ueber stdin herein, und
# ein Kindprozess, der stdin liest, frisst den Rest des Skripts (Erstlauf
# 2026-08-25: exit 0, leeres Protokoll, 29 s — psql hatte die Zeilen 60-95).
docker exec "$NAME" psql -q -U "$PGUSER" -d postgres -v ON_ERROR_STOP=0 \
  -f "/restore/${DUMP#"$DIR/dump/"}" </dev/null >/dev/null 2>"$DIR/psql.err" || true
ERR_ALL=$(grep -c "ERROR" "$DIR/psql.err" || true)
ERR_UNERWARTET=$(grep "ERROR" "$DIR/psql.err" | grep -vc "already exists" || true)
T_LOAD1=$(date +%s)

RESTORED=$(docker exec "$NAME" psql -U "$PGUSER" -d "$DB" -Atc "select count(*) from $TABLE" 2>/dev/null || echo "FEHLER")
LIVE=$(docker exec "$APP_CTR" psql -U "$PGUSER" -d "$DB" -Atc "select count(*) from $TABLE" 2>/dev/null || echo "FEHLER")
TABELLEN=$(docker exec "$NAME" psql -U "$PGUSER" -d "$DB" -Atc "select count(*) from pg_stat_user_tables" 2>/dev/null || echo "?")
T1=$(date +%s)
DAUER=$((T1 - T0)); LADEN=$((T_LOAD1 - T_LOAD0))
SNAP_ALTER_H=$(( (T0 - $(date -d "${SNAP_TIME}Z" +%s)) / 3600 ))

URTEIL="✅ bestanden"
[[ "$RESTORED" == "$LIVE" ]] || URTEIL="⚠️ Zeilenzahl weicht ab (Snapshot ist ${SNAP_ALTER_H} h alt — Abweichung erklärbar, wenn seither geschrieben wurde; sonst Befund)"
[[ "$RESTORED" =~ ^[0-9]+$ ]] || URTEIL="❌ Restore unbrauchbar — Tabelle nicht lesbar"
[[ "$ERR_UNERWARTET" -eq 0 ]] || URTEIL="$URTEIL · ⚠️ ${ERR_UNERWARTET} unerwartete psql-Fehler"

cat <<PROTOKOLL
# Restore-Feuerübung ${STAMP:0:4}-${STAMP:4:2}-${STAMP:6:2} — ${APP_CTR} (${DB})

> ADR-241 §5 / #2284 K4 · erzeugt von \`infra/host-maintenance/restore-drill.sh\` via \`make restore-drill\`
> Ausführung: Kapitäns-Kanal (Claude Code), Host \`prod\`, ohne Rückstände (Wegwerf-Container + Verzeichnis per trap entfernt)

| Feld | Wert |
|---|---|
| Quell-Snapshot | \`${SNAP_ID}\` · Tag \`${APP_CTR}\` · ${SNAP_TIME}Z (${SNAP_ALTER_H} h alt) |
| Dump | \`${APP_CTR}.sql\` (pg_dumpall), ${DUMP_MB} MB |
| Restore-Ziel | Wegwerf-Container \`${NAME}\`, Image \`${IMAGE}\`, Datenverzeichnis unter \`${BASE}\` |
| Smoke-Query | \`select count(*) from ${TABLE}\` |
| Ergebnis restauriert | **${RESTORED}** |
| Ergebnis Prod (live) | **${LIVE}** |
| Tabellen in \`${DB}\` nach Restore | ${TABELLEN} |
| psql-Fehler | ${ERR_ALL} gesamt, davon ${ERR_UNERWARTET} unerwartet (erwartet: Rolle/DB \`already exists\`) |
| RTO-Ist | **${DAUER} s** gesamt, davon ${LADEN} s Einspielen · Soll ${RTO_SOLL_H} h |
| Urteil | ${URTEIL} |

## Wiederholen

\`\`\`
make restore-drill                       # Vorgabe: risk_hub_db / risk_hub / ${TABLE}
make restore-drill APP=<container> DB=<db> TABLE=<tabelle>
\`\`\`

Quartalsweise (ADR-241). \`backup_meter.py --enforce-drill\` meldet ab 100 Tagen ohne neues Protokoll eine Verletzung.
PROTOKOLL
