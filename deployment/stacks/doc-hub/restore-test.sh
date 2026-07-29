#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# doc-hub Rückspielprobe — isoliert, ohne die Produktiv-Instanz zu berühren
# ═══════════════════════════════════════════════════════════════════════════════
# Spielt das jüngste Backup in eine WEGWERF-Instanz zurück (eigene Container,
# eigene Volumes, eigenes Netz) und prüft, ob die Dokumente wirklich ankommen.
# Räumt am Ende alles ab. Fasst iil_dochub_* NIE an.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

BACKUP_BASE="/opt/backups/doc-hub"
WORK="/opt/restore-test"
NET="restoretest_net"
PGC="restoretest_db"
RDC="restoretest_redis"
PGPASS="restore-test-only-throwaway"
IMAGE="ghcr.io/paperless-ngx/paperless-ngx:2.14"
MIN_FREE_GB=15

cleanup() {
    echo "--- Aufräumen ---"
    docker rm -f "$PGC" "$RDC" >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
    rm -rf "$WORK"
    echo "    Wegwerf-Instanz entfernt."
}
trap cleanup EXIT

# ── 0. Vorbedingungen ────────────────────────────────────────────────────────
FREE_GB=$(df --output=avail -BG / | tail -1 | tr -d ' G')
if (( FREE_GB < MIN_FREE_GB )); then
    echo "ABBRUCH: nur ${FREE_GB}G frei, brauche ${MIN_FREE_GB}G"; exit 2
fi

STAND=$(ls -1d "$BACKUP_BASE"/20* 2>/dev/null | sort | tail -1)
ZIP=$(ls -1t "$STAND"/export-*.zip 2>/dev/null | head -1)
DUMP=$(ls -1t "$STAND"/db-*.sql.gz 2>/dev/null | head -1)
[[ -f "$ZIP"  ]] || { echo "ABBRUCH: keine export-*.zip in $STAND"; exit 2; }
[[ -f "$DUMP" ]] || { echo "ABBRUCH: kein db-*.sql.gz in $STAND"; exit 2; }

echo "=== Rückspielprobe doc-hub ==="
echo "  Stand:   $STAND"
echo "  Export:  $(basename "$ZIP") ($(du -h "$ZIP" | cut -f1))"
echo "  DB-Dump: $(basename "$DUMP") ($(du -h "$DUMP" | cut -f1))"
echo "  frei:    ${FREE_GB}G"
echo

# ── 1. Soll-Werte aus der PRODUKTIV-DB (nur lesend) ──────────────────────────
SOLL_AKTIV=$(docker exec iil_dochub_db psql -U paperless -d paperless -tAc \
    "select count(*) from documents_document where deleted_at is null;")
SOLL_ALLE=$(docker exec iil_dochub_db psql -U paperless -d paperless -tAc \
    "select count(*) from documents_document;")
echo "SOLL (Produktiv): $SOLL_AKTIV aktiv, $SOLL_ALLE inkl. Papierkorb"

# ── 2. Wegwerf-Postgres ──────────────────────────────────────────────────────
mkdir -p "$WORK"
docker network create "$NET" >/dev/null
docker run -d --name "$PGC" --network "$NET" \
    -e POSTGRES_DB=paperless -e POSTGRES_USER=paperless \
    -e POSTGRES_PASSWORD="$PGPASS" \
    postgres:16-alpine >/dev/null
docker run -d --name "$RDC" --network "$NET" redis:7-alpine >/dev/null
echo "--- warte auf Wegwerf-Postgres ---"
for i in $(seq 1 30); do
    docker exec "$PGC" pg_isready -U paperless >/dev/null 2>&1 && break
    sleep 2
done
docker exec "$PGC" pg_isready -U paperless >/dev/null || { echo "ABBRUCH: DB nicht bereit"; exit 3; }

# ── 3. Weg A: DB-Dump zurückspielen ──────────────────────────────────────────
echo "--- Weg A: pg_dump zurückspielen ---"
set +e
gunzip -c "$DUMP" | docker exec -i "$PGC" psql -U paperless -d paperless \
    -v ON_ERROR_STOP=0 > "$WORK/restore_a.log" 2>&1
set -e
# grep -c liefert Exit 1 bei 0 Treffern — mit pipefail bricht das den Lauf ab
FEHLERZEILEN=$(grep -ci "^ERROR\|^FEHLER" "$WORK/restore_a.log" 2>/dev/null) || FEHLERZEILEN=0
echo "    psql meldete $FEHLERZEILEN Fehlerzeile(n)"
if (( FEHLERZEILEN > 0 )); then
    grep -i "^ERROR\|^FEHLER" "$WORK/restore_a.log" | sort -u | head -5 | sed "s/^/    | /"
fi
IST_A_AKTIV=$(docker exec "$PGC" psql -U paperless -d paperless -tAc \
    "select count(*) from documents_document where deleted_at is null;" 2>/dev/null || echo "FEHLER")
IST_A_ALLE=$(docker exec "$PGC" psql -U paperless -d paperless -tAc \
    "select count(*) from documents_document;" 2>/dev/null || echo "FEHLER")
echo "    IST: $IST_A_AKTIV aktiv, $IST_A_ALLE inkl. Papierkorb"

# ── 4. Weg B: Export-Zip über document_importer ──────────────────────────────
echo "--- Weg B: document_importer aus dem Export-Zip ---"
mkdir -p "$WORK/export"
# unzip ist auf dem Host nicht installiert — python3 kann es auch
python3 -c "
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    z.extractall(sys.argv[2])
" "$ZIP" "$WORK/export"
DATEIEN=$(find "$WORK/export" -type f ! -name "*.json" | wc -l)
echo "    entpackt: $DATEIEN Dateien + $(ls "$WORK/export"/*.json 2>/dev/null | wc -l) Manifest(e)"

# Importer braucht eine LEERE DB — zweiter Wegwerf-Postgres wäre teuer,
# also dieselbe Instanz zurücksetzen:
docker exec "$PGC" psql -U paperless -d postgres -q \
    -c "drop database paperless;" -c "create database paperless owner paperless;" >/dev/null 2>&1

set +e
docker run --rm --network "$NET" \
    -e PAPERLESS_DBHOST="$PGC" -e PAPERLESS_DBNAME=paperless \
    -e PAPERLESS_DBUSER=paperless -e PAPERLESS_DBPASS="$PGPASS" \
    -e PAPERLESS_SECRET_KEY=restore-test-only \
    -e PAPERLESS_REDIS="redis://$RDC:6379" \
    -e PAPERLESS_TIME_ZONE=Europe/Berlin \
    -v "$WORK/export":/usr/src/paperless/export:ro \
    -v "$WORK/media":/usr/src/paperless/media \
    -v "$WORK/data":/usr/src/paperless/data \
    "$IMAGE" \
    document_importer --no-progress-bar /usr/src/paperless/export > "$WORK/import.log" 2>&1
IMPORT_RC=$?
set -e
echo "    Importer exit=$IMPORT_RC"
tail -5 "$WORK/import.log" | sed "s/^/    | /"

IST_B=$(docker exec "$PGC" psql -U paperless -d paperless -tAc \
    "select count(*) from documents_document;" 2>/dev/null || echo "FEHLER")
DATEIEN_DA=$(find "$WORK/media" -type f 2>/dev/null | wc -l) || DATEIEN_DA=0
echo "    IST: $IST_B Dokumente in der DB, $DATEIEN_DA Dateien unter media/"

# ── 5. Urteil ────────────────────────────────────────────────────────────────
echo
echo "=== ERGEBNIS ==="
printf "  %-34s %s\n" "Soll aktiv (Produktiv):"        "$SOLL_AKTIV"
printf "  %-34s %s\n" "Soll inkl. Papierkorb:"         "$SOLL_ALLE"
printf "  %-34s %s\n" "Weg A (DB-Dump) aktiv:"         "$IST_A_AKTIV"
printf "  %-34s %s\n" "Weg B (Importer) Dokumente:"    "$IST_B"
printf "  %-34s %s\n" "Weg B Dateien unter media/:"    "$DATEIEN_DA"

FEHLER=0
[[ "$IST_A_ALLE" == "$SOLL_ALLE" ]] || { echo "  ✗ Weg A: Zeilenzahl weicht ab"; FEHLER=1; }
[[ "$IMPORT_RC" == "0" ]]           || { echo "  ✗ Weg B: Importer scheiterte"; FEHLER=1; }
(( DATEIEN_DA > 0 ))                || { echo "  ✗ Weg B: keine Dateien angekommen"; FEHLER=1; }

if (( FEHLER == 0 )); then
    echo "  ✓ Rückspielprobe bestanden — beide Wege tragen."
else
    echo "  ✗ Rückspielprobe NICHT bestanden — siehe oben."
fi
exit $FEHLER
