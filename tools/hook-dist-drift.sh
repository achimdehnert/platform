#!/usr/bin/env bash
# tools/hook-dist-drift.sh — Drift zwischen tools/claude-hooks/ und dem aktiven Hook-Pfad
#
# Warum es das gibt (Messung 2026-08-15, platform#1989):
#   Die Welle-1-Scanner liegen DIREKT in ~/.claude/hooks/ und werden von
#   settings.json von dort ausgefuehrt. Eine Verteil-Lane gibt es fuer sie nicht:
#   cc-skill-dist bespielt nur ~/.claude/hooks/managed/, das Makefile kennt kein
#   Ziel. Der Stand kam am 2026-08-10 VON HAND dorthin.
#
#   Am 2026-08-15 wichen daraufhin ALLE DREI Dateien von main ab. Der teuerste
#   Fall war gate_hits.py: die pytest-Sperre aus platform#1986 — der ganze Zweck
#   jenes PRs — war im aktiven Pfad nie angekommen. Das frisch neu gestartete
#   Kalibrierfenster (#1640) waere beim naechsten pytest-Lauf sofort wieder mit
#   Testrauschen gefuellt worden. Der Merge sah gruen aus, die Sperre existierte
#   im Repo, gewirkt haette sie nicht.
#
#   Wie bei 0.7.1 (deploy.sh) und 0.7.3 (/opt/platform) kann sich die Kopie nicht
#   selbst pruefen — der Check muss von aussen kommen. Er haengt in
#   tools/session_start_checks.sh (Phase 0.7.5) und laeuft damit jede Session.
#
# Usage:
#   tools/hook-dist-drift.sh            # nur pruefen, Exit 1 bei Drift
#   tools/hook-dist-drift.sh --sync     # aktive Kopien aus dem Repo nachziehen
#   tools/hook-dist-drift.sh --quiet    # nur die Summary-Zeile (fuer den Runner)
#
# Testbarkeits-Naht: HOOK_SRC_DIR und CLAUDE_HOOKS_DIR ueberschreiben beide
# Verzeichnisse, damit der Drill gegen tmp-Verzeichnisse laufen kann statt gegen
# das echte ~/.claude/hooks/ (siehe tools/tests/test_hook_dist_drift.py).
set -euo pipefail

PLATFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${HOOK_SRC_DIR:-$PLATFORM_DIR/tools/claude-hooks}"
DST_DIR="${CLAUDE_HOOKS_DIR:-$HOME/.claude/hooks}"

DO_SYNC=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --sync)  DO_SYNC=1 ;;
    --quiet) QUIET=1 ;;
    -h|--help) sed -n '1,27p' "$0"; exit 0 ;;
    *) echo "Unbekanntes Argument: $a" >&2; exit 64 ;;
  esac
done

[[ -d "$SRC_DIR" ]] || { echo "FEHLER: $SRC_DIR nicht gefunden" >&2; exit 2; }

if [[ ! -d "$DST_DIR" ]]; then
  echo "RESULT: UNGEPRUEFT — aktiver Hook-Pfad $DST_DIR existiert nicht (nichts verteilt?)"
  exit 0
fi

# Nur die oberste Ebene: tests/ und __pycache__/ gehoeren nie in den aktiven Pfad.
mapfile -t SRC_FILES < <(find "$SRC_DIR" -maxdepth 1 -type f \( -name '*.py' -o -name '*.sh' \) -printf '%f\n' | sort)

DRIFTED=""
SYNCED=0
NICHT_VERTEILT=""

[[ $QUIET -eq 1 ]] || {
  echo "Quelle: ${SRC_DIR/#$HOME/\~}"
  echo "Aktiv : ${DST_DIR/#$HOME/\~}"
  printf '%-40s %s\n' "DATEI" "STATUS"
}

for f in "${SRC_FILES[@]}"; do
  src="$SRC_DIR/$f"
  dst="$DST_DIR/$f"

  # Eine Quelldatei OHNE Gegenstueck ist kein Befund: nicht jeder Hook im Repo
  # gehoert in den aktiven Pfad (manche laufen nur in CI, manche sind Bibliothek).
  # Sie verschwindet aber auch nicht — sie wird gezaehlt und benannt, sonst waere
  # "gebaut, aber nie verteilt" wieder unsichtbar.
  if [[ ! -f "$dst" ]]; then
    NICHT_VERTEILT="$NICHT_VERTEILT $f"
    [[ $QUIET -eq 1 ]] || printf '%-40s %s\n' "$f" "–  nicht verteilt (kein Befund)"
    continue
  fi

  if cmp -s "$src" "$dst"; then
    SYNCED=$((SYNCED + 1))
    [[ $QUIET -eq 1 ]] || printf '%-40s %s\n' "$f" "✅ synchron"
    continue
  fi

  DRIFTED="$DRIFTED $f"
  [[ $QUIET -eq 1 ]] || printf '%-40s %s\n' "$f" "❌ DRIFT — aktive Kopie weicht von der Quelle ab"

  if [[ $DO_SYNC -eq 1 ]]; then
    # Backup behalten: die aktive Kopie ist der einzige Zeuge dessen, was zuletzt
    # wirklich lief — bei einem Fehlverhalten will man sie vergleichen koennen.
    cp -a "$dst" "$dst.bak-$(date +%Y%m%d%H%M%S)"
    cp "$src" "$dst"
    [[ -x "$src" ]] && chmod +x "$dst"
    if cmp -s "$src" "$dst"; then
      [[ $QUIET -eq 1 ]] || echo "   ✅ $f nachgezogen"
      DRIFTED="${DRIFTED/ $f/}"
      SYNCED=$((SYNCED + 1))
    else
      echo "   ❌ $f: nach sync immer noch abweichend" >&2
    fi
  fi
done

DRIFTED="${DRIFTED# }"; NICHT_VERTEILT="${NICHT_VERTEILT# }"
NV_ANZAHL=$(wc -w <<<"$NICHT_VERTEILT")

if [[ -n "$DRIFTED" ]]; then
  echo "RESULT: DRIFT — aktive Kopie(n) weichen von tools/claude-hooks ab: $DRIFTED (beheben: tools/hook-dist-drift.sh --sync)"
  exit 1
else
  echo "RESULT: OK — $SYNCED aktive Kopie(n) synchron · $NV_ANZAHL Quelldatei(en) nicht verteilt (kein Befund)"
fi
