#!/usr/bin/env bash
# tools/hostzugang.sh — Bash-Gegenstueck zu tools/hostzugang.py (platform#2783).
#
# Baut die (ggf. per ssh_via gehoppte) ssh-Argv-Liste aus einem hosts.yaml-
# Eintrag — dieselbe Konstruktion, die vorher in tools/deploy-script-drift.sh
# eigenstaendig stand (dritte Kopie neben flottenbild.py und
# host_datei_drift.py, siehe hostzugang.py-Kopfkommentar).
#
# Usage (source it, ruft sich nicht selbst auf):
#   source "$(dirname "$0")/hostzugang.sh"
#   hostzugang_ssh_kommando "$ssh_target" "$ssh_via" "$kommando" -o Foo=bar ...
#   "${HOSTZUGANG_CMD[@]}" <<< "$PAYLOAD"
#
# `kommando` ist das Wort/die Worte, die am Ziel ausgefuehrt werden (z.B.
# "$shell -- $REMOTE_PATH"). Bleibt im Direkt-Zweig UNQUOTED beim Anhaengen,
# damit es wie im Original per word-splitting in mehrere argv-Woerter
# zerfaellt (setzt voraus, dass darin enthaltene Pfade keine Leerzeichen
# haben — wie bisher). Im Hop-Zweig wandert es GEQUOTET als ein Wort in den
# inneren ssh-Aufruf.

# Optionen des inneren, gehoppten ssh-Aufrufs — in allen drei Originalen
# (flottenbild.py, host_datei_drift.py, deploy-script-drift.sh) bereits
# identisch, deshalb hier fest statt als Parameter.
HOSTZUGANG_VIA_OPTS=(-o BatchMode=yes -o ConnectTimeout=8)

hostzugang_ssh_kommando() {
  local ssh_target="$1" ssh_via="$2" kommando="$3"
  shift 3
  local -a opts=("$@")
  if [[ -n "$ssh_via" ]]; then
    local inner="ssh ${HOSTZUGANG_VIA_OPTS[*]} $ssh_target \"$kommando\""
    HOSTZUGANG_CMD=(ssh "${opts[@]}" "$ssh_via" "$inner")
  else
    # shellcheck disable=SC2206 # bewusst unquoted: word-splitting wie im Original
    HOSTZUGANG_CMD=(ssh "${opts[@]}" "$ssh_target" $kommando)
  fi
}
