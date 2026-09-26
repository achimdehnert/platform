#!/usr/bin/env bash
# secret_lesen.sh — der EINE Weg, aus einem Shell-Skript an einen Secret-Wert
# zu kommen.
#
# WOZU
#   Am 2026-09-13 wurde eine Datei aus ~/.secrets per ``. datei`` gesourced.
#   Sie lag in ``bare``-Form vor (ganze Datei = nackter Wert), also war die
#   erste Zeile fuer die Shell kein ``NAME=WERT``, sondern ein KOMMANDO: sie
#   versuchte den Token auszufuehren und schrieb ihn dabei in ihre eigene
#   Fehlermeldung — ein Leck ohne Ausgabe-Befehl, ohne Absicht.
#
#   Die Antwort darauf ist, alle Dateien auf ``NAME=WERT`` umzustellen
#   (Stufe 3, platform#3129). Damit das keinen Leser bricht, muss VORHER jeder
#   Leser beide Formen verstehen. Dieses Skript ist der tolerante Leser fuer
#   die Shell-Seite; die Python-Seite ist ``infra/lib/secrets.py``. Beide
#   benutzen dieselbe Implementierung — dieses Skript ruft sie nur auf, damit
#   die Regel nicht an zwei Stellen auseinanderlaufen kann.
#
# BENUTZUNG
#   WERT=$(tools/secret_lesen.sh cloudflare_write_token)   # Name -> ~/.secrets/
#   WERT=$(tools/secret_lesen.sh /pfad/zur/datei)          # oder ganzer Pfad
#   WERT=$(tools/secret_lesen.sh datei ORCHESTRATOR_MCP_API_KEY)  # Auswahl
#
#   Die Ausgabe auf stdout ist die EINZIGE erlaubte Stelle, an der ein Wert
#   sichtbar wird — und sie existiert nur fuer ``$(...)``. Nie in eine Datei
#   umleiten, nie ohne Not aufrufen. Weiterhin verboten: rohe Lesebefehle auf
#   ~/.secrets und jedes ``source``/``.`` einer Secret-Datei.
#
# EXIT-CODES
#   0  Wert steht auf stdout
#   2  Datei fehlt oder ist nicht lesbar
#   3  mehrere Variablen in der Datei, ohne dass ein NAME angegeben wurde
set -euo pipefail

WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  echo "Aufruf: secret_lesen.sh <datei-oder-name> [NAME]" >&2
  exit 2
fi

ZIEL="$1"
case "$ZIEL" in
  */*) : ;;                       # ganzer Pfad, so lassen
  *) ZIEL="$HOME/.secrets/$ZIEL" ;;
esac

exec python3 -c '
import pathlib
import sys

wurzel, ziel = sys.argv[1], sys.argv[2]
name = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
sys.path.insert(0, wurzel)
from infra.lib.secrets import secret_wert  # noqa: E402

pfad = pathlib.Path(ziel)
if not pfad.is_file():
    sys.stderr.write(f"fehlt: {pfad}\n")
    raise SystemExit(2)
try:
    wert = secret_wert(pfad, name=name)
except OSError as fehler:
    sys.stderr.write(f"nicht lesbar: {pfad} ({fehler.__class__.__name__})\n")
    raise SystemExit(2) from None
except ValueError as fehler:
    sys.stderr.write(f"{fehler}\n")
    raise SystemExit(3) from None
print(wert)
' "$WURZEL" "$ZIEL" "${2:-}"
