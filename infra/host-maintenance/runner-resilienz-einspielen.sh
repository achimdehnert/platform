#!/usr/bin/env bash
# Spielt runner-resilienz.conf fuer alle Actions-Runner-Units dieses Hosts ein.
# Idempotent; als root auf dem Runner-Host ausfuehren:
#   sudo bash infra/host-maintenance/runner-resilienz-einspielen.sh [--pruefen]
# --pruefen: aendert nichts, Exit 1, wenn eine Unit das Drop-in nicht wirksam hat.
set -euo pipefail

QUELLE="$(dirname "$(readlink -f "$0")")/runner-resilienz.conf"
PRUEFEN=0
[ "${1:-}" = "--pruefen" ] && PRUEFEN=1

mapfile -t UNITS < <(systemctl list-unit-files --no-legend 'actions.runner.*.service' | awk '{print $1}')
if [ "${#UNITS[@]}" -eq 0 ]; then
  echo "Keine actions.runner.*-Units auf $(hostname) — nichts zu tun."
  exit 0
fi

fehlt=0
for u in "${UNITS[@]}"; do
  policy=$(systemctl show "$u" -p OOMPolicy --value)
  restart=$(systemctl show "$u" -p Restart --value)
  if [ "$policy" = continue ] && [ "$restart" = on-failure ]; then
    echo "OK     $u"
    continue
  fi
  if [ "$PRUEFEN" -eq 1 ]; then
    echo "FEHLT  $u (OOMPolicy=$policy Restart=$restart)"
    fehlt=1
    continue
  fi
  install -D -m 0644 "$QUELLE" "/etc/systemd/system/$u.d/10-resilienz.conf"
  echo "SETZE  $u"
done

if [ "$PRUEFEN" -eq 0 ]; then
  systemctl daemon-reload
  # Nur aktivierte Units starten: eine bewusst stillgelegte (disabled) bleibt aus.
  for u in "${UNITS[@]}"; do
    systemctl is-enabled --quiet "$u" || continue
    systemctl is-active --quiet "$u" || { systemctl start "$u"; echo "START  $u"; }
  done
fi
exit "$fehlt"
