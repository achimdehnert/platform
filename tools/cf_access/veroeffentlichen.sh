#!/usr/bin/env bash
# Einen Loopback-Dienst hinter Cloudflare Access veröffentlichen.
#
#   HOST=mail.iil.pet PORT=8787 UNIT=cloudflared-mail-links.service \
#     tools/cf_access/veroeffentlichen.sh
#
# Reihenfolge — und Schritt 3 ist die Lehre aus dem Erstlauf am 2026-07-30:
#   1. Access-Anwendung + Richtlinie
#   2. Tunnel + DNS (Tunnel läuft noch NICHT — es gibt keinen Ursprung)
#   3. Warten, bis Access nachweislich abweist
#   4. Tunnel starten und gegenprüfen; bei 200 sofort wieder stoppen
#
# Beim Erstlauf war die Access-Anwendung angelegt, der Tunnel aber schon gestartet:
# der Host antwortete rund 20 Sekunden lang mit HTTP 200 OHNE Anmeldung. Access
# angelegt ist nicht Access durchgesetzt.
#
# Volltext: docs/runbooks/loopback-dienst-hinter-cloudflare-access.md
set -euo pipefail

: "${HOST:?HOST fehlt (z.B. mail.iil.pet)}"
: "${PORT:?PORT fehlt (Loopback-Port des Dienstes)}"
: "${UNIT:?UNIT fehlt (systemd --user Unit des Tunnels)}"
HIER="$(cd "$(dirname "$0")" && pwd)"

status() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$HOST/" || echo 000; }

echo "── 1/4 Cloudflare Access ─────────────────────────────"
python3 "$HIER/access_anlegen.py"

echo "── 2/4 Tunnel + DNS ─────────────────────────────────"
python3 "$HIER/tunnel_anlegen.py"

echo "── 3/4 Warten auf die Durchsetzung (VOR dem Tunnel) ──"
durchgesetzt=nein
for i in $(seq 20); do
  code="$(status)"
  echo "  Probe $i: HTTP $code"
  case "$code" in
    301|302) echo "  Access weist ab — Durchsetzung ist aktiv."; durchgesetzt=ja; break ;;
    200)     echo "  ⛔ 200 OHNE laufenden Tunnel — hier antwortet etwas anderes. Abbruch."; exit 1 ;;
    *)       sleep 6 ;;
  esac
done
if [ "$durchgesetzt" != ja ]; then
  echo "  ⛔ Nach 20 Proben keine Abweisung gesehen — Tunnel wird NICHT gestartet."
  echo "     Anwendung und Richtlinie im Zero-Trust-Dashboard prüfen."
  exit 1
fi

echo "── 4/4 Tunnel starten und gegenprüfen ───────────────"
systemctl --user enable --now "$UNIT"
sleep 8
systemctl --user is-active "$UNIT"
for i in 1 2 3; do
  sleep 3
  code="$(status)"
  echo "  Gegenprobe $i: HTTP $code"
  if [ "$code" = "200" ]; then
    echo "  ⛔ 200 mit laufendem Tunnel — Access greift NICHT. Tunnel wird gestoppt."
    systemctl --user stop "$UNIT"
    exit 1
  fi
done
echo "Fertig: https://$HOST/ — Anmeldung über den Zero-Trust-Anbieter, Sitzung 24 h."
