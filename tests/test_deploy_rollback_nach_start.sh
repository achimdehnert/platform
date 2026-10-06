#!/usr/bin/env bash
# tests/test_deploy_rollback_nach_start.sh — Vertragstest: jeder Abbruch NACH dem
# Hochfahren des neuen Stacks (Health-Check, Fehlerzustand, Crashloop-Gate) muss
# in scripts/deploy.sh das Rollback auslösen (platform#3804, Kriterium 6).
#
# Realfall im lokalen Rollback-Drill 2026-10-06: ein Abbild, das nie auf /healthz/
# antwortete, blieb nach „❌ Health-Check fehlgeschlagen" einfach stehen, `.env`
# trug seinen Tag, kein Rollback. Ursache: `trap rollback ERR` feuert bei einem
# nackten `exit N` nicht — nur bei einem Kommando, das mit N scheitert. Alle drei
# Nach-Start-Abbrüche waren nackte `exit`. Am Deploy-Log war das nicht zu sehen:
# rot war er so oder so; kaputt war wieder der Notausgang.
#
# Geprüfte Zusagen:
#   1. Zwischen dem Hochfahren (`up -d --force-recreate --remove-orphans`) und
#      `trap - ERR` steht kein nacktes `exit N` mehr — nur `fehlschlag N`.
#   2. `fehlschlag N` feuert unter `set -euo pipefail` den ERR-Trap mit $?=N,
#      auch als letztes Glied einer `&&`-Liste (so steht es im Health-Loop).
#   3. Ein nacktes `exit N` an derselben Stelle feuert den Trap NICHT — der Test
#      prüft damit seine eigene Prämisse, nicht nur das Skript.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/scripts/deploy.sh"

FAILED=0
pruefe() { # pruefe <name> <erwartet> <tatsaechlich>
  if [[ "$2" == "$3" ]]; then
    echo "  ok    $1"
  else
    echo "  FAIL  $1 — erwartet '$2', bekam '$3'" >&2
    FAILED=1
  fi
}

# ── Zusage 1: kein nacktes exit im Nach-Start-Fenster ────────────────────────
echo "Zusage 1: Nach-Start-Fenster ohne nacktes exit"
START_ZEILE=$(grep -nE '^docker compose .* up -d --force-recreate --remove-orphans' "$SRC" | head -1 | cut -d: -f1)
ENDE_ZEILE=$(grep -nE '^trap - ERR' "$SRC" | head -1 | cut -d: -f1)
if [[ -z "$START_ZEILE" || -z "$ENDE_ZEILE" || "$START_ZEILE" -ge "$ENDE_ZEILE" ]]; then
  echo "FAIL: Nach-Start-Fenster nicht aus $SRC extrahierbar — Marker geändert?" >&2
  exit 1
fi
FENSTER=$(sed -n "${START_ZEILE},${ENDE_ZEILE}p" "$SRC" | sed -E 's/#.*$//')
pruefe "kein nacktes 'exit N' im Fenster" "0" "$(grep -cE '(^|[;{[:space:]])exit[[:space:]]+[0-9]+' <<<"$FENSTER")"
pruefe "drei Abbrüche über fehlschlag" "3" "$(grep -cE '(^|[;{[:space:]])fehlschlag[[:space:]]+[0-9]+' <<<"$FENSTER")"
pruefe "fehlschlag ist vor dem Fenster definiert" "1" \
  "$(sed -n "1,${START_ZEILE}p" "$SRC" | grep -cE '^fehlschlag\(\) \{ return "\$1"; \}')"

# ── Zusage 2/3: Trap-Mechanik unter denselben Shell-Optionen wie deploy.sh ──
echo "Zusage 2/3: ERR-Trap-Mechanik"
trap_lauf() { # trap_lauf <abbruch-kommando> → "TRAP:<ec>" oder "KEIN-TRAP", gefolgt vom Exit-Code
  bash -c '
    set -euo pipefail
    fehlschlag() { return "$1"; }
    rollback() { local ec=$?; echo "TRAP:$ec"; exit "$ec"; }
    trap rollback ERR
    for i in 1; do
      [[ $i -eq 1 ]] && { echo "fehl" >/dev/null; '"$1"'; }
    done
    echo "KEIN-TRAP"
  ' 2>/dev/null
  echo "rc=$?"
}
pruefe "fehlschlag 4 feuert Trap mit ec=4" "TRAP:4 rc=4" "$(trap_lauf 'fehlschlag 4' | tr '\n' ' ' | sed 's/ $//')"
pruefe "fehlschlag 6 feuert Trap mit ec=6" "TRAP:6 rc=6" "$(trap_lauf 'fehlschlag 6' | tr '\n' ' ' | sed 's/ $//')"
pruefe "nacktes exit 4 feuert KEINEN Trap (Prämisse)" "rc=4" "$(trap_lauf 'exit 4' | tr '\n' ' ' | sed 's/ $//')"

if [[ $FAILED -ne 0 ]]; then
  echo "FEHLGESCHLAGEN" >&2
  exit 1
fi
echo "ALLE ZUSAGEN GEHALTEN"
