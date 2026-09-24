#!/usr/bin/env bash
# Befund-Journal-Sicherung (KONZ-platform-054 §12.7 "Ablageort", Owner-Go 2026-09-24).
#
# Das Journal (~/.claude/befund-journal.json) traegt offene Befunde, Urteile und
# seit #3527 den Heilungsverlauf, aus dem die Wiederkehr-Abstaende berechnet
# werden. Es lag nur auf dem Sitzungs-Host: faellt der aus, sind Praezision je
# Melder und Wiederkehr-Historie weg — genau die Zeitreihen, die KONZ-054 am
# Kill-Gate 2026-10-15 messen will.
#
# Ablageort nach demselben Muster wie der Mail-State (KONZ-platform-040 MVC-4,
# Owner-Entscheid 2026-08-06): eigener Dev-Server, NICHT dieses Repo — platform
# ist oeffentlich und die Notizen tragen Laufausschnitte (KONZ-054 §6.3).
# Verzeichnis 700, Archive 600, Transport per SSH.
set -euo pipefail

ZIEL_HOST="${BEFUND_SICHERUNG_ZIEL:-root@88.99.38.75}"
ZIEL_DIR="/opt/backups/befund-journal"
BEHALTEN=30
QUELLE="$HOME/.claude/befund-journal.json"

[ -s "$QUELLE" ] || { echo "FEHLER: $QUELLE fehlt oder leer" >&2; exit 1; }
# Kaputtes JSON nicht sichern: ein Archiv, das beim Restore nicht laedt, ist
# schlechter als keins, weil es Sicherheit vortaeuscht.
python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$QUELLE" \
  || { echo "FEHLER: $QUELLE ist kein gueltiges JSON" >&2; exit 1; }

stempel=$(date +%Y%m%d-%H%M%S)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
archiv="$tmp/befund-journal-$stempel.json.gz"
gzip -c "$QUELLE" >"$archiv"

ssh -o ConnectTimeout=10 "$ZIEL_HOST" "mkdir -p '$ZIEL_DIR' && chmod 700 '$ZIEL_DIR'"
scp -q "$archiv" "$ZIEL_HOST:$ZIEL_DIR/"
ssh "$ZIEL_HOST" "chmod 600 '$ZIEL_DIR'/befund-journal-*.json.gz; ls -1 '$ZIEL_DIR' | sort | head -n -$BEHALTEN | while read -r alt; do rm -f '$ZIEL_DIR/'\"\$alt\"; done"

# Verifikation gehoert zur Sicherung: Archiv auf dem ZIEL entpacken und als JSON laden.
befunde=$(ssh "$ZIEL_HOST" "gzip -dc '$ZIEL_DIR/befund-journal-$stempel.json.gz' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get(\"befunde\", {})))'")
echo "OK: befund-journal-$stempel.json.gz auf $ZIEL_HOST:$ZIEL_DIR ($befunde Befunde, Retention $BEHALTEN)"
