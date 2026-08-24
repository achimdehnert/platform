#!/usr/bin/env bash
# Klaert, welche Orgs wirklich zur Enterprise `iilgmbh` gehoeren (ADR-297, offener Punkt 3).
#
# WARUM ES DIESEN CHECK BRAUCHT: `gh api orgs/<org> --jq .plan.name` liefert fuer ALLE
# vier Orgs byte-identisch "enterprise" — auch fuer ttz-lif und meiki-lra, die laut
# ADR-236 ausserhalb der Enterprise laufen. Das Feld unterscheidet nichts.
#
# WARUM DIE ANMELDUNG NICHT HIER DRIN STEHT: die erste Fassung rief `gh auth refresh`
# selbst auf. Das nutzt den Device-Flow — Code anzeigen, auf den Browser warten — und
# lief im Aufruf ueber die Agenten-Shell in ein 120-Sekunden-Timeout
# ("context deadline exceeded", 2026-08-24). Ein Skript, das auf eine Browser-Eingabe
# wartet, gehoert nicht in einen Kontext, der nach zwei Minuten abbricht. Es prueft
# jetzt nur noch und sagt, was zu tun ist.
set -euo pipefail

if ! gh auth status 2>&1 | grep -q "admin:enterprise"; then
  cat <<'HINWEIS'
⛔ Der Scope `admin:enterprise` fehlt — ohne ihn ist die Frage nicht beantwortbar.

Diesen einen Befehl in einem NORMALEN Terminal ausfuehren (nicht ueber die
Agenten-Shell — der Device-Flow wartet auf den Browser und wird dort abgebrochen):

    gh auth refresh -h github.com -s admin:enterprise -s admin:org

Danach dieses Skript erneut starten. Es laeuft dann ohne Rueckfrage durch.
HINWEIS
  exit 2
fi

echo "Orgs der Enterprise 'iilgmbh':"
gh api enterprises/iilgmbh/organizations --jq '.[].login' 2>/dev/null \
  || gh api graphql -f query='{ enterprise(slug:"iilgmbh"){ organizations(first:50){ nodes { login } } } }' \
       --jq '.data.enterprise.organizations.nodes[].login'

echo
echo "Sitzverbrauch:"
gh api enterprises/iilgmbh/consumed-licenses --jq '{total_seats_purchased, total_seats_consumed}'

echo
echo "Zum Vergleich — was ADR-236 (Stand 2026-06-03) behauptet:"
echo "  Enterprise 'iilgmbh' enthaelt NUR 'bahn-sqf'."
echo "Weicht die Liste oben davon ab, ist ADR-236 an dieser Stelle ueberholt."
echo
echo "Ergebnis in ADR-297 unter 'Offene Punkte' eintragen."
