#!/usr/bin/env bash
# Monatlicher Rechnungslauf am 10. (Owner-Wort 2026-09-12, platform#3102 K1):
# Entwuerfe fuer den Vormonat anlegen (NICHT senden), Pruefliste ablegen und in
# den Auftragsraum melden. Der Versand bleibt Owner-Gate: `--senden --ja` nach Wort.
set -euo pipefail
REPO="${REPO:-$HOME/github/platform}"
MONAT="${1:-$(date -d "$(date +%Y-%m-01) -1 day" +%Y-%m)}"
BOARD="$HOME/.claude/boards/sevdesk-rechnungslauf-$MONAT.md"
mkdir -p "$(dirname "$BOARD")"
cd "$REPO"
{
  echo "# Rechnungslauf $MONAT — Entwuerfe angelegt $(date -Is)"
  echo
  python3 tools/sevdesk/rechnungslauf.py --monat "$MONAT"
  echo
  echo "Versand nach Owner-Wort: python3 tools/sevdesk/rechnungslauf.py --monat $MONAT --senden --ja"
} > "$BOARD" 2>&1 || { echo "Rechnungslauf $MONAT fehlgeschlagen, siehe $BOARD" >&2; exit 1; }
# Meldung in den Auftragsraum (Lotse), falls Umgebung vorhanden — Ausfall ist kein Abbruch.
ENV="$HOME/.claude/auftragsraum.env"; LOTSE="$HOME/.venvs/chat-lotse/bin/python"; CL="$HOME/github/chat-hub/deploy/chat_lotse.py"
if [ -f "$ENV" ] && [ -x "$LOTSE" ] && [ -f "$CL" ]; then
  RAUM_ID=$(grep -o '^RAUM_ID=.*' "$ENV" | cut -d= -f2- | tr -d '"')
  ANZ=$(grep -c '^| ' "$BOARD" || true)
  "$LOTSE" "$CL" send --room "$RAUM_ID" --text "Rechnungslauf $MONAT: Entwuerfe angelegt (Pruefliste $ANZ Zeilen). Freigabe zum Versand mit 'Rechnungslauf $MONAT senden'." \
    || echo "Chat-Meldung fehlgeschlagen (Lauf selbst ok)" >&2
fi
echo "ok: $BOARD"
