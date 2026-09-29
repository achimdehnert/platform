#!/usr/bin/env bash
# Richtet systemd-oomd fuer user.slice ein (platform#3616). Idempotent; als root
# auf dem Dev-/Session-Host ausfuehren:
#   sudo bash infra/host-maintenance/oomd-einspielen.sh [--pruefen]
# --pruefen: aendert nichts, Exit 1, wenn oomd nicht laeuft oder user.slice nicht
# mit 60 % ueberwacht wird.
set -euo pipefail

QUELLE="$(dirname "$(readlink -f "$0")")/oomd-user-slice.conf"
ZIEL=/etc/systemd/system/user.slice.d/10-oomd.conf
PRUEFEN=0
[ "${1:-}" = "--pruefen" ] && PRUEFEN=1

pruefe() {
  local fehlt=0
  if systemctl is-active --quiet systemd-oomd; then
    echo "OK     systemd-oomd aktiv"
  else
    echo "FEHLT  systemd-oomd nicht aktiv"
    fehlt=1
  fi
  if cmp -s "$QUELLE" "$ZIEL"; then
    echo "OK     $ZIEL"
  else
    echo "FEHLT  $ZIEL weicht vom Repo ab oder fehlt"
    fehlt=1
  fi
  # Wirksam ist erst, was oomd selbst ueberwacht — nicht, was in der Datei steht.
  if timeout 40 oomctl 2>/dev/null | grep -A2 -E '^\s*Path: /user\.slice$' | grep -q 'Memory Pressure Limit: 60\.00%'; then
    echo "OK     oomd ueberwacht /user.slice mit 60 %"
  else
    echo "FEHLT  oomd ueberwacht /user.slice nicht mit 60 %"
    fehlt=1
  fi
  return "$fehlt"
}

if [ "$PRUEFEN" -eq 1 ]; then
  pruefe
  exit $?
fi

if ! dpkg-query -W -f='${Status}' systemd-oomd 2>/dev/null | grep -q 'install ok installed'; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q systemd-oomd
  # Das Paket bringt eine D-Bus-Policy mit; ohne Reload laeuft oomctl in einen
  # Aktivierungs-Timeout (Realfall 2026-09-29), obwohl oomd laeuft.
  systemctl reload dbus
  systemctl restart systemd-oomd
fi
install -D -m 0644 "$QUELLE" "$ZIEL"
systemctl daemon-reload
systemctl enable --now systemd-oomd
pruefe
