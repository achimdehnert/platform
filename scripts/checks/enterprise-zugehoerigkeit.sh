#!/usr/bin/env bash
# Klaert, welche Orgs wirklich zur Enterprise `iilgmbh` gehoeren (ADR-297, offener Punkt 3).
#
# WARUM EIN EIGENES SKRIPT: `gh api orgs/<org> --jq .plan.name` liefert fuer ALLE vier
# Orgs byte-identisch "enterprise" — auch fuer ttz-lif und meiki-lra, die laut ADR-236
# ausserhalb der Enterprise laufen. Das Feld unterscheidet nichts. Der Nachweis braucht
# den Scope `admin:enterprise`, und der verlangt eine interaktive Anmeldung.
set -euo pipefail

echo "1/3 Scope nachfordern (oeffnet den Browser)…"
gh auth refresh -h github.com -s admin:enterprise -s admin:org

echo
echo "2/3 Orgs der Enterprise 'iilgmbh':"
gh api enterprises/iilgmbh/organizations --jq '.[].login' 2>/dev/null \
  || gh api graphql -f query='{ enterprise(slug:"iilgmbh"){ organizations(first:50){ nodes { login } } } }' \
       --jq '.data.enterprise.organizations.nodes[].login'

echo
echo "3/3 Sitzverbrauch:"
gh api enterprises/iilgmbh/consumed-licenses --jq '{total_seats_purchased, total_seats_consumed}'

echo
echo "Ergebnis in ADR-297 unter 'Offene Punkte' eintragen."
