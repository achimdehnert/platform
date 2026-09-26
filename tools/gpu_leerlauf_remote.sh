#!/usr/bin/env bash
# gpu_leerlauf_remote.sh — laeuft AUF einem GPU-Knoten, gibt JSON-Zeilen aus.
#
# Je Prozess mit Grafikspeicher: welche systemd-Unit haelt ihn, wieviel, und
# wann hat sie zuletzt eine echte Anfrage gesehen? Die Zuordnung laeuft ueber
# /proc/<pid>/cgroup — der MainPID der Unit reicht NICHT, weil die Engine oft
# ein Kindprozess ist (vLLM: Unit-MainPID 2411, Speicher haelt 3588).
#
# Ausgabe je Zeile: {"pid":N,"mib":N,"unit":"...","cmd":"...","letzte_anfrage":"..."}
# Verteilt von tools/gpu_leerlauf.py; nicht von Hand auf den Knoten legen.
set -uo pipefail

nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv,noheader 2>/dev/null |
while IFS=, read -r pid mib cmd; do
  pid="${pid// /}"
  mib="$(echo "$mib" | tr -dc '0-9')"
  cmd="$(echo "$cmd" | sed 's/^ *//')"
  unit="$(sed -n 's/.*\/\([a-zA-Z0-9_.@-]*\.service\).*/\1/p' "/proc/$pid/cgroup" 2>/dev/null | head -1)"
  [ -z "$unit" ] && unit="(keine Unit)"
  letzte=""
  if [ "$unit" != "(keine Unit)" ]; then
    # Echte Anfragen — und NUR die. Zwei Fallen, beide am 2026-09-21 real
    # aufgetreten und hier gegengeprueft:
    #   1. Beim Start listet vLLM seine Routen ("Route: /infer...") auf.
    #   2. Beim Herunterfahren schreibt es "[shutdown] EngineCore: request
    #      processing complete" — ein loses 'processing ' im Muster machte
    #      daraus eine frische Anfrage, und der Melder war blind fuer genau
    #      den Dienst, fuer den er gebaut wurde.
    # whisper meldet echte Arbeit als "processing '<datei>'" — mit Anfuehrungs-
    # zeichen, daran unterscheiden sich die Faelle.
    letzte="$(journalctl --user -u "$unit" --no-pager -o short-iso 2>/dev/null |
      grep -aE "(POST|GET|PUT) /|Received request|Added request|processing '" |
      grep -avE 'Route: |Waiting for application|startup complete|\[shutdown\]' |
      tail -1 | awk '{print $1}')"
  fi
  printf '{"pid":%s,"mib":%s,"unit":"%s","cmd":"%s","letzte_anfrage":"%s"}\n' \
    "${pid:-0}" "${mib:-0}" "$unit" "${cmd//\"/}" "$letzte"
done
