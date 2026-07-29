#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# doc-hub backup — Paperless document_exporter (zip) + pg_dump (ADR-144)
# ═══════════════════════════════════════════════════════════════════════════════
# Install:  cp backup.sh /opt/doc-hub/scripts/paperless-backup.sh && chmod +x
# Cron:     0 3 * * * /opt/doc-hub/scripts/paperless-backup.sh >> /var/log/doc-hub-backup.log 2>&1
#
# WICHTIG: Es darf nur EIN Backup-Lauf existieren. Bis 2026-07-29 lief zusätzlich
# eine ältere Fassung dieses Skripts als /etc/cron.daily/doc-hub-backup und legte
# denselben Bestand ein zweites Mal UNKOMPRIMIERT ab (2,1 GB statt 427 MB je Tag).
# Der dadurch entstandene Platzdruck war 2026-04-18 der Anlass, die Aufbewahrung
# auf EINEN Tag zu senken — Symptombehandlung. Vor dem Ausrollen prüfen:
#   ls /etc/cron.daily/doc-hub-backup   # muss fehlen
#
# Rückspielprobe: deployment/stacks/doc-hub/restore-test.sh (isoliert, gefahrlos)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

BACKUP_BASE="/opt/backups/doc-hub"
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="$BACKUP_BASE/$DATE"
CONTAINER="iil_dochub_web"
DB_CONTAINER="iil_dochub_db"
EXPORT_VOLUME="doc-hub-stack_dochub_export"

# Ein Stand ist ~430 MB (Stand 2026-07-29: 820 Dokumente).
# 30 Stände ≈ 13 GB; die Obergrenze lässt Luft für Wachstum, ohne dass die
# Notbremse greift.
KEEP_DAYS=30
MAX_BACKUP_GB=25
DISK_PCT_MAX=90

echo "$(date) — Paperless backup starting..."

# ── Vorprüfung: Platte ───────────────────────────────────────────────────────
# Bewusst ein FEHLSCHLAG, kein stilles exit 0: ein übersprungener Backup-Lauf,
# der Erfolg meldet, ist ein blinder Melder.
DISK_PCT=$(df / --output=pcent | tail -1 | tr -d ' %')
if (( DISK_PCT > DISK_PCT_MAX )); then
    echo "$(date) — FEHLER: Platte bei ${DISK_PCT}% (>${DISK_PCT_MAX}%), Backup NICHT gelaufen"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# ── 1. Paperless-Export (Originale + Metadaten als Zip) ──────────────────────
# --no-archive/--no-thumbnail: beides ist aus den Originalen regenerierbar.
# Belegt durch die Rückspielprobe vom 2026-07-29: 820 Dokumente, 821 Dateien.
docker exec "$CONTAINER" python3 manage.py document_exporter \
    /usr/src/paperless/export \
    --no-archive --no-thumbnail --zip --no-progress-bar 2>&1 | tail -3

# ── 2. Nur den heutigen Stand herüberkopieren ────────────────────────────────
EXPORT_VOL=$(docker volume inspect "$EXPORT_VOLUME" -f '{{.Mountpoint}}')
cp "$EXPORT_VOL/export-$DATE.zip" "$BACKUP_DIR/" 2>/dev/null || \
    cp "$(ls -1t "$EXPORT_VOL"/export-*.zip 2>/dev/null | head -1)" "$BACKUP_DIR/" 2>/dev/null || true
cp "$EXPORT_VOL/manifest.json" "$BACKUP_DIR/" 2>/dev/null || true
cp "$EXPORT_VOL/metadata.json" "$BACKUP_DIR/" 2>/dev/null || true

# ── 3. PostgreSQL-Dump ───────────────────────────────────────────────────────
docker exec "$DB_CONTAINER" pg_dump -U paperless paperless \
    | gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# ── 4. Export-Volume aufräumen (nur die letzten 3 Zips behalten) ─────────────
cd "$EXPORT_VOL" 2>/dev/null && \
    ls -1t export-*.zip 2>/dev/null | tail -n +4 | xargs -r rm -f || true

# ── 5. Alte Stände rotieren ──────────────────────────────────────────────────
find "$BACKUP_BASE" -maxdepth 1 -type d -name '20*' -mtime +"$KEEP_DAYS" -exec rm -rf {} \;

# ── 6. Notbremse: ältesten Stand entfernen, bis unter der Obergrenze ─────────
# Früher wurde hier auf EINEN Stand zurückgeschnitten — das ist derselbe Sprung
# auf 1 Tag, nur unsichtbar. Jetzt ältester-zuerst, Stand für Stand.
groesse_gb() { echo $(( $(du -sm "$BACKUP_BASE" | cut -f1) / 1024 )); }
while (( $(groesse_gb) > MAX_BACKUP_GB )); do
    STAENDE_JETZT=$(find "$BACKUP_BASE" -maxdepth 1 -type d -name '20*' | wc -l)
    (( STAENDE_JETZT > 1 )) || break   # niemals den letzten Stand löschen
    AELTESTER=$(find "$BACKUP_BASE" -maxdepth 1 -type d -name '20*' | sort | head -1)
    [[ -n "$AELTESTER" ]] || break
    echo "$(date) — Obergrenze ${MAX_BACKUP_GB}GB erreicht, entferne $AELTESTER"
    rm -rf "$AELTESTER"
done

# ── Zusammenfassung ──────────────────────────────────────────────────────────
DB_SIZE=$(du -sh "$BACKUP_DIR/db-$DATE.sql.gz" 2>/dev/null | cut -f1)
TOTAL=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
TOTAL_ALL=$(du -sh "$BACKUP_BASE" 2>/dev/null | cut -f1)
STAENDE=$(find "$BACKUP_BASE" -maxdepth 1 -type d -name '20*' | wc -l)
echo "$(date) — Backup complete: $BACKUP_DIR ($TOTAL, DB: $DB_SIZE)"
echo "$(date) — Bestand: $STAENDE Stände, $TOTAL_ALL gesamt (Ziel: $KEEP_DAYS Tage, max ${MAX_BACKUP_GB}GB)"
