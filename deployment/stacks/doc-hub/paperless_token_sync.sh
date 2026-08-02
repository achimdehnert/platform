#!/bin/bash
# Zieht den nach der Rotation gueltigen Paperless-Token vom Prod-Host in ~/.secrets.
#
# Hintergrund: die Rotation am 2026-08-02 schrieb den neuen Wert nur nach
# /opt/dms-hub/.env.prod und loeschte die Uebergabedatei. Die lokale Kopie blieb auf
# dem Stand vom 30.04. stehen und antwortet seither mit "Invalid token".
#
#   bash ~/bin/paperless_token_sync.sh            prueft nur
#   bash ~/bin/paperless_token_sync.sh --scharf   schreibt ~/.secrets/paperless_api_token
#
# Der Wert wird nie ausgegeben — nur Laenge, Pruefsumme und das Ergebnis eines Testabrufs.
set -u
HOST="root@88.198.191.108"
ZIEL="$HOME/.secrets/paperless_api_token"
TMP="$(mktemp)"
trap 'shred -u "$TMP" 2>/dev/null || rm -f "$TMP"' EXIT

ssh -o BatchMode=yes "$HOST" \
  "grep -m1 '^PAPERLESS_API_TOKEN=' /opt/dms-hub/.env.prod | cut -d= -f2- | tr -d '\"'\''[:space:]'" \
  > "$TMP" 2>/dev/null

LAENGE=$(tr -d '\n' < "$TMP" | wc -c)
if [ "$LAENGE" -ne 40 ]; then
  echo "ABBRUCH: aus .env.prod kamen $LAENGE Zeichen statt 40 — nichts geschrieben"
  exit 1
fi

NEU=$(sha256sum < "$TMP" | cut -c1-12)
ALT=$(sha256sum < "$ZIEL" 2>/dev/null | cut -c1-12)
echo "Prod   : 40 Zeichen, Pruefsumme $NEU"
echo "lokal  : Pruefsumme ${ALT:-keine Datei}"
[ "$NEU" = "$ALT" ] && { echo "identisch — nichts zu tun"; exit 0; }

# Testabruf mit dem NEUEN Wert, bevor die lokale Datei angefasst wird
ANTWORT=$(tr -d '\n' < "$TMP" | ssh -o BatchMode=yes "$HOST" \
  "read -r T; docker exec -i iil_dochub_web curl -s -o /dev/null -w '%{http_code}' \
   -H \"Authorization: Token \$T\" http://localhost:8000/api/documents/?page_size=1")
echo "Testabruf mit dem neuen Wert: HTTP $ANTWORT"
[ "$ANTWORT" = "200" ] || { echo "ABBRUCH: kein 200 — nichts geschrieben"; exit 1; }

if [ "${1:-}" != "--scharf" ]; then
  echo "Trockenlauf — mit --scharf wird $ZIEL ersetzt"
  exit 0
fi

[ -f "$ZIEL" ] && cp "$ZIEL" "$ZIEL.alt-$(date +%Y%m%d-%H%M%S)"
install -m 600 "$TMP" "$ZIEL"
echo "geschrieben: $ZIEL (alte Fassung daneben als .alt-*)"
