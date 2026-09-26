#!/usr/bin/env bash
# Strang-Cache des todo-boards nachziehen (platform#3175).
#
# Jede Ergaenzung am Verlauf eines Vorgangs aendert den Cache-Schluessel; bis zum
# naechsten Vorwaermen zeigt die Seite dann den Ein-Strang-Rueckfall. Dieses
# Skript laeuft per Timer (infra/host-maintenance/todo-straenge.timer) und ruft
# das Modell nur fuer Vorgaenge ohne Cache-Treffer — ohne Aenderung: 0 Aufrufe.
#
# Schluessel nur ueber den toleranten Leser, nie per source, nie ausgegeben.
set -euo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="$(cd "$HIER/../.." && pwd)"
GROQ_API_KEY="$("$PLATFORM/tools/secret_lesen.sh" groq_api_key)"
export GROQ_API_KEY
exec /usr/bin/python3 "$PLATFORM/tools/todo_board/straenge.py" --vorwaermen
