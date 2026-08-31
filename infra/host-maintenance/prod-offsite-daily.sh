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

# Unter welchem Host-Namen die Snapshots im Repository stehen.
#
# Frueher stand hier fest `--host prod`. Das reichte, solange nur ein Host
# sicherte. Seit dem ADR-292-Umzug tragen `prod` und `prod-b` teils
# GLEICHNAMIGE Container (cad_hub_db, coach_hub_db, dms_hub_db, pptx_hub_db,
# trading_hub_db) — mit festem `--host prod` waeren deren Snapshots im selben
# Repository nicht mehr auseinanderzuhalten. Genau daran haette sich sonst die
# Frage "welche der beiden Datenbanken liegt hier eigentlich?" nicht mehr
# beantworten lassen (platform#2058).
#
# Voreinstellung bleibt bewusst `prod` — NICHT `hostname`. Der Hostname luegt
# hier (die Box heisst bis heute `ubuntu-8gb-nbg1-1`, siehe infra/hosts.yaml),
# und ein Wechsel des Host-Namens haette die 297 bestehenden Snapshots still in
# einen anderen Namensraum verschoben. Jeder WEITERE Host setzt `OFFSITE_HOST`
# in seiner /etc/offsite-backup.env; vergisst er es, sichert er unter `prod`
# und der Fehler faellt beim ersten Blick in `restic snapshots` auf, statt
# unbemerkt zu bleiben.
RESTIC_HOST="${OFFSITE_HOST:-prod}"

redact() { sed -E 's#(://[^:/@]+):[^@]*@#\1:***@#g'; }
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

rc_total=0

# ─────────────────────────────────────────────────────────────────────────────
log "Sicherung laeuft unter Host-Name: $RESTIC_HOST"
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
# Bis 2026-08-31 stand hier eine blosse ZAHL. Das reichte, um "etwas ist weg" zu
# sehen, aber nicht, um "was" zu sagen — und damit nicht, um einen gewollten
# Abgang von einem Ausfall zu trennen. Am 2026-08-31 meldete der Waechter
# "nur 13 statt 15" nach den Stilllegungen vom Vortag (#2480): sachlich richtig,
# praktisch ein Fehlalarm. Schlimmer ist die Kehrseite: im Fenster nach einer
# Stilllegung sieht ein ECHTER Ausfall genauso aus und wird als bekannt abgetan.
# Seitdem wird die Namensliste gefuehrt und die Differenz benannt.
LISTE_DATEI=/var/lib/offsite-backup/pg-instanzen.liste
ERWARTET_WEG=/var/lib/offsite-backup/pg-instanzen.erwartet-weg
mkdir -p /var/lib/offsite-backup 2>/dev/null || true

# Migration vom Zahl- auf das Listenformat: beim ersten Lauf danach gibt es noch
# keine Liste. Dann schweigt der Vergleich fuer genau diesen einen Lauf, statt
# einen Rueckgang zu behaupten, den niemand nachpruefen kann.
VORHER=()
[[ -r "$LISTE_DATEI" ]] && mapfile -t VORHER < "$LISTE_DATEI"

FEHLEND=()
for v in ${VORHER[@]+"${VORHER[@]}"}; do
  [[ -n "$v" ]] || continue
  drin=0
  for c in ${PGC[@]+"${PGC[@]}"}; do [[ "$c" == "$v" ]] && { drin=1; break; }; done
  (( drin )) || FEHLEND+=("$v")
done

# Quittierte Abgaenge: eine Zeile je Container-Name, '#' leitet einen Kommentar
# ein. Ein Eintrag hier heisst "weg und gewollt" — er unterdrueckt genau diesen
# einen Namen und keinen zweiten.
UNERWARTET=()
for f in ${FEHLEND[@]+"${FEHLEND[@]}"}; do
  if [[ -r "$ERWARTET_WEG" ]] \
     && grep -vE '^[[:space:]]*(#|$)' "$ERWARTET_WEG" | grep -qxF "$f"; then
    log "  · $f fehlt — als bewusster Abgang quittiert ($ERWARTET_WEG)"
  else
    UNERWARTET+=("$f")
  fi
done

if (( ${#UNERWARTET[@]} )); then
  log "  FEHLER: ${#UNERWARTET[@]} Instanz(en) aus dem letzten Lauf fehlen: ${UNERWARTET[*]}"
  log "          Gesichert wird trotzdem, was da ist — aber hier fehlt etwas."
  log "          War der Abgang gewollt? Dann den Namen in $ERWARTET_WEG eintragen."
  rc_total=1
fi

# Nur fortschreiben, wenn wirklich etwas gefunden wurde. Sonst wuerde ein Lauf,
# bei dem der Docker-Daemon klemmt, die leere Menge zum neuen Vorlauf machen und
# den Waechter fuer alle folgenden Laeufe entwaffnen.
if (( ${#PGC[@]} )); then
  printf '%s\n' "${PGC[@]}" > "$LISTE_DATEI" 2>/dev/null || true
else
  log "  (Vorlauf-Liste NICHT ueberschrieben — 0 Instanzen waeren sonst das neue Soll)"
fi
log "  ${#PGC[@]} Postgres-Instanz(en) erkannt (Vorlauf: ${#VORHER[@]})"

for c in "${PGC[@]}"; do
  # Dump-Rolle bestimmen. Frueher wurde blind POSTGRES_USER genommen — in fast
  # allen Images IST das der Superuser, aber eben nicht in allen: pptx_hub_db
  # setzt POSTGRES_USER=pptx_hub_app, eine App-Rolle OHNE Attribute, waehrend
  # der Superuser daneben `pptx_hub` heisst. pg_dumpall liest als Erstes die
  # Rollen aus pg_authid, scheiterte dort an fehlenden Rechten und lieferte
  # 229 Byte statt 145 KB (platform#2057).
  #
  # Deshalb: POSTGRES_USER bleibt die erste Wahl, aber nur wenn es wirklich ein
  # Superuser ist; sonst wird eine login-faehige Superuser-Rolle gesucht.
  # `pg_roles` ist eine fuer jeden lesbare Sicht (anders als pg_authid), die
  # Abfrage gelingt also auch mit der App-Rolle. Gemessen 2026-08-18 ueber alle
  # 21 Instanzen: 20 liefern exakt POSTGRES_USER zurueck (nichts aendert sich),
  # nur pptx_hub_db weicht ab.
  u=$(docker exec "$c" sh -c 'printf "%s" "${POSTGRES_USER:-postgres}"' 2>/dev/null || echo postgres)
  su=$(docker exec "$c" psql -U "$u" -d postgres -tAc \
        "SELECT rolname FROM pg_roles WHERE rolsuper AND rolcanlogin
         ORDER BY (rolname = current_user) DESC, rolname LIMIT 1" 2>/dev/null \
       | tr -d '[:space:]')
  if [[ -n "$su" && "$su" != "$u" ]]; then
    log "  · $c: POSTGRES_USER=$u ist kein Superuser — nutze $su"
    u="$su"
  fi

  # Vorbedingung pruefen, BEVOR etwas hochgeladen wird. Der eigentliche Schaden
  # in #2057 war nicht der Fehlschlag, sondern dass `restic backup --stdin` den
  # abgebrochenen 229-Byte-Strom klaglos als Snapshot speicherte: die Frage
  # "gibt es einen Snapshot fuer pptx_hub_db?" wurde mit JA beantwortet, obwohl
  # die Datenbank nicht gesichert war. Ein Groessen-Check nach dem Upload waere
  # zu spaet, und den Dump erst in eine Datei zu schreiben scheidet aus
  # (devhub_db allein sind 14,6 GB). pg_authid ist genau das, woran pg_dumpall
  # als Erstes scheitert — die Abfrage kostet nichts und faengt die Klasse ab.
  if ! docker exec "$c" psql -U "$u" -d postgres -tAc \
         "SELECT 1 FROM pg_authid LIMIT 1" >/dev/null 2>&1; then
    log "  ✗ $c — $u darf pg_authid nicht lesen; pg_dumpall wuerde leer abbrechen."
    log "        NICHT hochgeladen (ein Leer-Snapshot taeuscht Abdeckung vor)."
    rc_total=1
    continue
  fi

  if docker exec "$c" pg_dumpall -U "$u" 2>/dev/null \
     | restic backup --stdin --stdin-filename "${c}.sql" \
         --tag pgdump --tag "$c" --host "$RESTIC_HOST" 2>&1 | redact; then
    log "  ✓ $c (als $u)"
  else
    log "  ✗ $c — Dump oder Upload fehlgeschlagen"
    rc_total=1
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
log "Datei-Volumes sichern — Standard: ALLES Benannte, Verzicht explizit (platform#2284, 2026-08-25)"
# Bis 2026-08-25 sicherte dieser Block nur Volumes, deren Name auf
# minio|media|upload|documents passte. Alles andere war unsichtbar — 46 Volumes
# mit 7,2 GB, darunter drei doc-hub-Volumes in Nutzung (platform#2284 K1).
# Jetzt ist das Vorzeichen gedreht: gesichert wird jedes benannte Volume, AUSSER
#   (a) pgdata der oben gedumpten Postgres-Container (konsistent per pg_dumpall),
#   (b) was governance/backup/volume-verzicht.yaml MIT Grund verzichtet
#       (Regeln = Klassen ohne Nutzdatenanspruch, exakt = Einzelfaelle).
# Fehlt die Verzichtsliste, wird ALLES Benannte gesichert und das laut gesagt —
# die Fehlerrichtung ist "zu viel Backup", nie "zu wenig".
VOLROOT="$(docker info --format '{{.DockerRootDir}}')/volumes"
VERZICHT_YAML="${VERZICHT_YAML:-/opt/platform/governance/backup/volume-verzicht.yaml}"
TARGETS=(); N_VERZICHT=0; N_PGDATA=0
# pgdata-Volumes der gedumpten Container
PG_VOLS=""
for c in "${PGC[@]}"; do
  PG_VOLS+="$(docker inspect "$c" --format '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}{{"\n"}}{{end}}{{end}}' 2>/dev/null)"$'\n'
done
# Volume-Liste in eine Datei — NICHT in eine Pipe: `python3 -` liest das
# Programm von stdin, und ein Heredoc dort verdraengt die Pipe. Der Erstlauf
# nach platform#2306 entschied so "0 sichern · 0 verzichtet" auf beiden Hosts
# (2026-08-25 15:00) — die Liste war weg, bevor Python sie sah.
VOL_LISTE=$(mktemp)
docker volume ls --format '{{.Name}}\t{{.Labels}}' > "$VOL_LISTE"
if [[ -f "$VERZICHT_YAML" ]]; then
  # Entscheidung je Volume in Python (Regex + YAML), eine Zeile "NAME<TAB>sichern|verzicht"
  ENTSCHEID=$(python3 - "$VERZICHT_YAML" "$RESTIC_HOST" "$VOL_LISTE" <<'PY'
import re, sys, yaml
pfad, host, liste = sys.argv[1], sys.argv[2], sys.argv[3]
d = yaml.safe_load(open(pfad, encoding="utf-8")) or {}
exakt = {(str(e.get("host")), str(e.get("volume"))) for e in d.get("verzicht") or [] if isinstance(e, dict) and e.get("grund")}
regeln = [re.compile(str(r["muster"]), re.I) for r in d.get("regeln") or [] if isinstance(r, dict) and r.get("muster") and r.get("grund")]
for zeile in open(liste, encoding="utf-8"):
    name, _, labels = zeile.rstrip("\n").partition("\t")
    if not name or "com.docker.volume.anonymous" in labels:
        continue
    if (host, name) in exakt or any(r.search(name) for r in regeln):
        print(f"{name}\tverzicht")
    else:
        print(f"{name}\tsichern")
PY
)
else
  log "  WARNUNG: Verzichtsliste $VERZICHT_YAML fehlt — sichere ALLES Benannte (Fehlerrichtung: zu viel, nie zu wenig)"
  ENTSCHEID=$(awk -F'\t' '$2 !~ /com.docker.volume.anonymous/ {print $1"\tsichern"}' "$VOL_LISTE")
fi
rm -f "$VOL_LISTE"
# Ein leerer Entscheid ist ein Werkzeugfehler, keine Lage: 175 Volumes auf prod
# verschwinden nicht ueber Nacht. Laut sagen, nicht still "0 sichern".
[[ -n "$ENTSCHEID" ]] || { log "  FEHLER: Volume-Entscheidung leer — Volume-Sicherung NICHT gelaufen (Werkzeugfehler)"; rc_total=1; }
while IFS=$'\t' read -r v was; do
  [[ -n "$v" ]] || continue
  if grep -qxF "$v" <<<"$PG_VOLS"; then N_PGDATA=$((N_PGDATA+1)); continue; fi
  if [[ "$was" == "verzicht" ]]; then N_VERZICHT=$((N_VERZICHT+1)); continue; fi
  d="$VOLROOT/$v/_data"
  [[ -d "$d" ]] && TARGETS+=("$d")
done <<<"$ENTSCHEID"
log "  Entscheidung: ${#TARGETS[@]} sichern · $N_VERZICHT verzichtet (Regel/Liste) · $N_PGDATA pgdata (per Dump gedeckt)"

if [[ ${#TARGETS[@]} -gt 0 ]]; then
  if restic backup --tag volumes --host "$RESTIC_HOST" "${TARGETS[@]}" 2>&1 | redact; then
    log "  ✓ ${#TARGETS[@]} Volume(s)"
  else
    log "  ✗ Volume-Sicherung fehlgeschlagen"; rc_total=1
  fi
else
  log "  (keine passenden Volumes)"
fi

# ─────────────────────────────────────────────────────────────────────────────
log "Konfiguration sichern — was ein Host von Null braucht (KONZ-054 §12, 2026-08-30)"
# Gemessen 2026-08-30: 689 Snapshots im Repo, 0 Pfade unter /etc, 0 unter /opt.
# Datenbanken und Volumes waren gesichert — nginx-vhosts, Tunnel-Credential,
# Compose-Dateien und .env je App nicht. Ein Wiederanlauf haette an der ersten
# Datei gescheitert, die kein Backup kannte. Das Repo ist verschluesselt; die
# .env-Dateien gehoeren deshalb hinein, nicht heraus — ohne sie startet kein Stack.
CONF=()
for p in /etc/nginx /etc/cloudflared /root/.cloudflared /etc/cron.d /etc/systemd/system \
         /etc/fstab /etc/offsite-backup.env /usr/local/bin /etc/ufw/user.rules; do
  [[ -e "$p" ]] && CONF+=("$p")
done
for d in /opt/*/; do
  for f in docker-compose.yml docker-compose.prod.yml docker-compose.override.yml \
           .env .env.prod .env.production secrets.enc.env Caddyfile; do
    [[ -f "$d$f" ]] && CONF+=("$d$f")
  done
done
if [[ ${#CONF[@]} -gt 0 ]]; then
  if restic backup --tag config --host "$RESTIC_HOST" "${CONF[@]}" 2>&1 | redact; then
    log "  ✓ ${#CONF[@]} Konfigurationspfade (Tag config)"
  else
    log "  ✗ Konfigurations-Sicherung fehlgeschlagen"; rc_total=1
  fi
else
  log "  ✗ keine Konfigurationspfade gefunden — das ist ein Befund, kein Leerlauf"; rc_total=1
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
