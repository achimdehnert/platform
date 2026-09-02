#!/usr/bin/env bash
# Was bedeutet die Antwort der Gegenprobe? — eine Entscheidung, absichtlich in
# einer eigenen Datei, damit sie ohne Cloudflare-Konto und ohne systemd testbar
# ist (tools/tests/test_cf_gegenprobe.py).
#
# Warum es diese Trennung gibt (platform#2700, Retro-Befund 2026-09-02):
# `veroeffentlichen.sh` wertete bis dahin JEDES "nicht 200" als Erfolg. Es suchte
# die Access-Abweisung — und ein 502 durch einen kaputten Ursprung sieht genauso
# "nicht 200" aus. Ein falsch gesetzter ORIGIN blieb dadurch still, bis sich
# jemand anmeldete und ins Leere griff.
#
# Gemessen am 2026-09-02: mail.iil.pet, docs.iil.pet, kd.iil.pet und gpu.iil.pet
# antworten unangemeldet ausnahmslos mit 302 und zeigen dabei auf
# `cloudflareaccess.com`. Die Abweisung hat also eine erkennbare Signatur.
#
# URSPRUNG_DARF_SCHLAFEN=1 fuer Dienste auf Geraeten mit `betrieb: auf_zuruf`
# (hosts.yaml): dort ist ein 502 der erwartete Normalfall, kein Fehler.

#: 0 = erwartet (Access weist ab)  ·  1 = Access greift nicht  ·
#: 2 = Ursprung antwortet nicht    ·  3 = unerwartete Antwort
beurteile_gegenprobe() {
  case "$1" in
    301|302)
      return 0 ;;
    200)
      return 1 ;;
    502|503|504)
      if [ "${URSPRUNG_DARF_SCHLAFEN:-0}" = "1" ]; then
        return 0
      fi
      return 2 ;;
    *)
      return 3 ;;
  esac
}
