#!/bin/bash
# Rotiert den Paperless-API-Token des Dienst-Benutzers und zieht ihn in dms-hub nach.
# Der Tokenwert erscheint zu keinem Zeitpunkt auf stdout.
#
#   ./rotate_paperless_token.sh --trocken   # prueft alles, aendert nichts
#   ./rotate_paperless_token.sh             # rotiert scharf
set -euo pipefail

BENUTZER="admin"
ENVDATEI="/opt/dms-hub/.env.prod"
TOKDATEI="/root/.newtok"
API="http://127.0.0.1:8102/api/documents/?page_size=1"
TROCKEN=""
[ "${1:-}" = "--trocken" ] && TROCKEN="--trocken"

pruefe() {  # $1 = Token, gibt HTTP-Code aus
  curl -s -o /dev/null -w "%{http_code}" \
       -H "Authorization: Token $1" -H "Host: docs.iil.pet" "$API"
}

echo "== 1. Vorbedingungen"
[ -f "$ENVDATEI" ] || { echo "FEHLER: $ENVDATEI fehlt"; exit 1; }
docker ps --format "{{.Names}}" | grep -qx iil_dochub_web || { echo "FEHLER: iil_dochub_web laeuft nicht"; exit 1; }
ALT=$(grep -m1 "^PAPERLESS_API_TOKEN=" "$ENVDATEI" | cut -d= -f2- | tr -d "\"'")
[ ${#ALT} -eq 40 ] || { echo "FEHLER: alter Token hat ${#ALT} statt 40 Zeichen"; exit 1; }
echo "   alter Token vorhanden (40 Zeichen), Antwort der API: $(pruefe "$ALT")"

echo "== 2. Sicherung"
SICHER="${ENVDATEI}.bak-$(date +%F-%H%M%S)"
cp "$ENVDATEI" "$SICHER"
echo "   $SICHER"

if [ -n "$TROCKEN" ]; then
  echo "== 3. Trockenlauf im Container"
  docker exec iil_dochub_web python3 /usr/src/paperless/scripts/rotate_token.py "$BENUTZER" --trocken
  echo "== TROCKENLAUF ENDE — nichts wurde geaendert"
  exit 0
fi

echo "== 3. Neuen Token erzeugen"
docker exec iil_dochub_web python3 /usr/src/paperless/scripts/rotate_token.py "$BENUTZER" > "$TOKDATEI"
chmod 600 "$TOKDATEI"
[ "$(wc -c < "$TOKDATEI")" -eq 40 ] || { echo "FEHLER: neuer Token hat $(wc -c < "$TOKDATEI") statt 40 Zeichen — Abbruch, .env unveraendert"; exit 1; }
echo "   erzeugt (40 Zeichen)"

echo "== 4. Gegenprobe VOR der Uebernahme"
echo "   alter Token: $(pruefe "$ALT")   (erwartet 401)"
echo "   neuer Token: $(pruefe "$(cat "$TOKDATEI")")   (erwartet 200)"

echo "== 5. In die Konfiguration uebernehmen"
python3 - "$ENVDATEI" "$TOKDATEI" <<"PYIN"
import io, sys
env, tok = sys.argv[1], sys.argv[2]
wert = io.open(tok).read().strip()
zeilen = io.open(env, encoding="utf-8").read().splitlines(True)
raus = []
getroffen = 0
for z in zeilen:
    if z.startswith("PAPERLESS_API_TOKEN="):
        raus.append("PAPERLESS_API_TOKEN=" + wert + "\n"); getroffen += 1
    else:
        raus.append(z)
assert getroffen == 1, "erwartete genau 1 Token-Zeile, fand %d" % getroffen
io.open(env, "w", encoding="utf-8").write("".join(raus))
print("   Token-Zeile ersetzt")
PYIN
shred -u "$TOKDATEI"
echo "   Zwischendatei geloescht"

echo "== 6. Dienste neu starten"
docker restart dms_hub_web dms_hub_worker dms_hub_beat > /dev/null
echo "   neugestartet"

echo "== 7. Abschlusspruefung"
NEU=$(grep -m1 "^PAPERLESS_API_TOKEN=" "$ENVDATEI" | cut -d= -f2- | tr -d "\"'")
echo "   alter Token: $(pruefe "$ALT")   (muss 401 sein)"
echo "   neuer Token: $(pruefe "$NEU")   (muss 200 sein)"
echo "== FERTIG. Ruecknahme bei Bedarf: cp $SICHER $ENVDATEI && docker restart dms_hub_web dms_hub_worker dms_hub_beat"
