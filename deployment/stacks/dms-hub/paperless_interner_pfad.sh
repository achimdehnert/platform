#!/bin/bash
# Stellt dms-hub auf den internen Weg zu Paperless um. Laeuft AUF DEM PROD-HOST.
#
#   bash /root/paperless_interner_pfad.sh            Trockenlauf
#   bash /root/paperless_interner_pfad.sh --scharf   stellt um
#
# Warum: PAPERLESS_URL zeigte auf die oeffentliche Adresse. Seit dort Cloudflare
# Access davorsteht, bekommt dms-hub eine Weiterleitung auf die Anmeldeseite statt
# JSON — fetch_paperless_documents() faengt das ab und gibt None zurueck, lautlos.
# Der Spiegel stand deshalb seit dem 2026-07-19 still.
#
# Der interne Weg im Docker-Netz umgeht Cloudflare ganz, scheitert aber an Djangos
# ALLOWED_HOSTS (400), solange der Host-Kopf fehlt. Beides wird hier gesetzt.
set -u

ENVDATEI="/opt/dms-hub/.env.prod"
ZIEL_URL="http://iil_dochub_web:8000"
ZIEL_HOST="docs.iil.pet"
SCHARF=""
[ "${1:-}" = "--scharf" ] && SCHARF=1

pruefe() {
  echo "FEHLER: $1"
  exit 1
}

echo "== 1. Vorbedingungen"
for c in dms_hub_web iil_dochub_web; do
  docker ps --format '{{.Names}}' | grep -qx "$c" || pruefe "Container $c laeuft nicht"
done
[ -f "$ENVDATEI" ] || pruefe "$ENVDATEI gibt es nicht"
echo "   beide Container laufen, $ENVDATEI vorhanden"

echo "== 2. Traegt der laufende Code die neue Variable?"
TREFFER=$(docker exec dms_hub_web grep -c 'PAPERLESS_HOST_HEADER' /app/src/apps/scanner/services.py 2>/dev/null || echo 0)
[ "$TREFFER" -ge 1 ] || pruefe "der laufende Container kennt PAPERLESS_HOST_HEADER nicht — erst deployen"
echo "   ja, $TREFFER Fundstellen in services.py"

echo "== 3. Erreichbarkeit des internen Pfades"
CODE=$(docker exec -i dms_hub_web python3 - <<'PY' 2>/dev/null
import urllib.request
r = urllib.request.Request("http://iil_dochub_web:8000/api/", headers={"Host": "docs.iil.pet"})
try:
    print(urllib.request.urlopen(r, timeout=8).status)
except urllib.error.HTTPError as e:
    print(e.code)
except Exception as e:
    print("FEHLER", type(e).__name__)
PY
)
echo "   ${ZIEL_URL}/api/ mit Host ${ZIEL_HOST} -> ${CODE:-keine Antwort}"
# 401/403 sind gute Nachrichten: Django antwortet, nur die Anmeldung fehlt an dieser Stelle.
case "$CODE" in
  200|401|403) ;;
  *) pruefe "interner Pfad antwortet mit '${CODE:-nichts}' — Abbruch, .env unveraendert" ;;
esac

echo "== 4. Ausgangslage des Spiegels"
VORHER=$(docker exec dms_hub_web python manage.py shell -c \
  "from apps.scanner.models import ScanDocument; print(ScanDocument.objects.count())" 2>/dev/null | tail -1)
echo "   ScanDocument vorher: ${VORHER:-unbekannt}"

if [ -z "$SCHARF" ]; then
  echo "== TROCKENLAUF ENDE — nichts geaendert"
  echo "   wuerde setzen: PAPERLESS_URL=${ZIEL_URL}"
  echo "   wuerde setzen: PAPERLESS_HOST_HEADER=${ZIEL_HOST}"
  exit 0
fi

echo "== 5. Sicherung"
SICHER="${ENVDATEI}.bak-$(date +%F-%H%M%S)"
cp "$ENVDATEI" "$SICHER"
echo "   $SICHER"

echo "== 6. Umstellen"
setze() {
  local schluessel="$1" wert="$2"
  if grep -q "^${schluessel}=" "$ENVDATEI"; then
    sed -i "s|^${schluessel}=.*|${schluessel}=${wert}|" "$ENVDATEI"
  else
    printf '%s=%s\n' "$schluessel" "$wert" >> "$ENVDATEI"
  fi
  echo "   ${schluessel}=${wert}"
}
setze PAPERLESS_URL "$ZIEL_URL"
setze PAPERLESS_HOST_HEADER "$ZIEL_HOST"

echo "== 7. Container neu erzeugen"
# `docker restart` reicht NICHT: env_file wird nur beim ERZEUGEN des Containers
# ausgewertet. Ein Neustart laeuft mit den alten Werten weiter — genau daran
# scheiterte der erste Anlauf am 2026-08-02. Deshalb `up -d --force-recreate`.
COMPOSE_KETTE=$(docker inspect dms_hub_web --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}')
PROJEKT=$(docker inspect dms_hub_web --format '{{index .Config.Labels "com.docker.compose.project"}}')
[ -n "$COMPOSE_KETTE" ] || pruefe "compose-Dateien nicht ermittelbar"
DATEI_ARGS=""
IFS=',' read -ra TEILE <<< "$COMPOSE_KETTE"
for t in "${TEILE[@]}"; do DATEI_ARGS="$DATEI_ARGS -f $t"; done
echo "   Projekt $PROJEKT, Dateien:$DATEI_ARGS"
# shellcheck disable=SC2086
docker compose -p "$PROJEKT" $DATEI_ARGS up -d --force-recreate dms-hub-web dms-hub-worker dms-hub-beat > /dev/null 2>&1 \
  || pruefe "compose up fehlgeschlagen — Ruecknahme: cp $SICHER $ENVDATEI"
sleep 15
echo "   neu erzeugt"

echo "   gelesene Werte im Container:"
docker exec -i dms_hub_web python3 - <<'PY' 2>/dev/null
from decouple import config
print("     PAPERLESS_URL         =", config("PAPERLESS_URL", default="(nicht gesetzt)"))
print("     PAPERLESS_HOST_HEADER =", repr(config("PAPERLESS_HOST_HEADER", default="")))
PY

echo "== 8. Beweis: holt der Abgleich jetzt Daten?"
docker exec dms_hub_web python manage.py shell -c "
from apps.scanner.services import fetch_paperless_documents
d = fetch_paperless_documents()
print('Antwort:', 'FEHLGESCHLAGEN (None)' if d is None else '%d Dokumente' % (d.get('count', -1) if isinstance(d, dict) else len(d)))
" 2>/dev/null | tail -1

echo
echo "== FERTIG. Ruecknahme (restart reicht NICHT, die Container muessen neu erzeugt werden):"
echo "   cp $SICHER $ENVDATEI"
echo "   docker compose -p $PROJEKT$DATEI_ARGS up -d --force-recreate dms-hub-web dms-hub-worker dms-hub-beat"
