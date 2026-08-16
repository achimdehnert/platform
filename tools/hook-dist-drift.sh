#!/usr/bin/env bash
# tools/hook-dist-drift.sh — Drift zwischen tools/claude-hooks/ und dem aktiven Hook-Pfad
#
# GATE_HEADER (KONZ-038 D8) — auch in Shell maschinenlesbar gehalten, damit
# tools/gate_drill_check.py Kopf und Registry gegeneinander pruefen kann:
#   "slug": "hand-distributed-copy-not-redistributed"
#   "mode": "advisory"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-16"
#   "evidence": "tools/tests/test_hook_dist_drift.py"
#
# Warum es das gibt (Messung 2026-08-15, platform#1989):
#   Die Welle-1-Scanner liegen DIREKT in ~/.claude/hooks/ und werden von
#   settings.json von dort ausgefuehrt. Der Stand kam am 2026-08-10 VON HAND
#   dorthin — eine Verteil-Lane gab es fuer sie nicht: die `hooks`-Lane von
#   cc-skill-dist liest `tools/hooks/` und matcht nur `.sh`.
#
#   Seit demselben Tag gibt es die Lane `claude-hooks` (merge-Modus, siehe
#   generate.py). Dieser Melder bleibt trotzdem noetig und ist NICHT redundant:
#   er prueft den Ist-Zustand des aktiven Pfads, unabhaengig davon, ob und wann
#   jemand die Lane laufen liess. Genau diese Unabhaengigkeit ist der Punkt —
#   eine Lane, auf deren Ausfuehrung man sich verlaesst, ist wieder Disziplin.
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

# Ueberschreibbar wie HOOK_SRC_DIR/CLAUDE_HOOKS_DIR — sonst laesst sich der
# Basis-Hinweis unten nicht gegen ein Repo mit bekanntem Abstand pruefen.
PLATFORM_DIR="${PLATFORM_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SRC_DIR="${HOOK_SRC_DIR:-$PLATFORM_DIR/tools/claude-hooks}"
DST_DIR="${CLAUDE_HOOKS_DIR:-$HOME/.claude/hooks}"

DO_SYNC=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --sync)  DO_SYNC=1 ;;
    --quiet) QUIET=1 ;;
    -h|--help) sed -n '1,34p' "$0"; exit 0 ;;
    *) echo "Unbekanntes Argument: $a" >&2; exit 64 ;;
  esac
done

_ohne_footer() {
  # Generierten MANAGED-BY-Footer ausblenden — samt der Leerzeile davor, die der
  # Generator mitschreibt. Ohne das Entfernen der Leerzeile bliebe ein Unterschied
  # stehen und der Melder waere nach der ersten Verteilung dauerhaft rot.
  grep -v 'MANAGED-BY' "$1" | sed -e :a -e '/^[[:space:]]*$/{$d;N;ba' -e '}'
}

[[ -d "$SRC_DIR" ]] || { echo "FEHLER: $SRC_DIR nicht gefunden" >&2; exit 2; }

# Vergleichsbasis benennen — und melden, wenn sie selbst veraltet ist.
#
# Gemessen 2026-08-16 (platform#2004): derselbe unveraenderte Hook (md5 597225…)
# bekam von diesem Skript zwei Urteile — `RESULT: OK` bei HEAD 1612cd94, `RESULT:
# DRIFT` bei HEAD 2037dc5c. Verglichen wird gegen den ARBEITSBAUM, nicht gegen
# origin/main. Zu Sitzungsbeginn stimmt das (Phase 0.2 zieht vorher), aber jeder
# Merge WAEHREND einer Sitzung macht den Melder still gruen — genau in dem Moment,
# in dem eine frisch gemergte Aenderung noch nicht im aktiven Pfad liegt. Das ist
# der Fall, fuer den es diesen Melder ueberhaupt gibt (#1989).
#
# Bewusst KEIN automatischer Vergleich gegen origin/main: waehrend der Arbeit an
# einem Hook weicht der eigene Worktree zu Recht ab, das waere Dauerrot. Der Melder
# sagt stattdessen, WOGEGEN er geurteilt hat — ein Urteil ohne genannte Basis ist
# der eigentliche Defekt.
BASIS_HINWEIS=""
if git -C "$PLATFORM_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  BASIS_SHA=$(git -C "$PLATFORM_DIR" log -1 --format=%h -- tools/claude-hooks 2>/dev/null || echo "?")
  HINTEN=$(git -C "$PLATFORM_DIR" rev-list --count HEAD..origin/main -- tools/claude-hooks 2>/dev/null || echo 0)
  if [[ "${HINTEN:-0}" -gt 0 ]]; then
    BASIS_HINWEIS=" · ⚠ Basis ${BASIS_SHA} ist ${HINTEN} Commit(s) hinter origin/main — das Urteil gilt NUR fuer diese Basis (git pull, dann erneut pruefen)"
  else
    BASIS_HINWEIS=" · Basis ${BASIS_SHA}"
  fi
fi

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

  # Die MANAGED-BY-Zeile beim Vergleich ausblenden: seit platform#1989 kann die
  # aktive Kopie aus der `claude-hooks`-Lane von cc-skill-dist stammen, und die
  # haengt jeder verteilten Datei einen Footer mit `source_commit` an. Ohne diese
  # Ausblendung meldete dieser Melder nach der ERSTEN Verteilung alle Dateien
  # dauerhaft als Drift — zwei Mechanismen, die sich gegenseitig widerlegen, und
  # ein dauerhaft roter Melder meldet nichts mehr (#1508).
  # Der Footer ist generiert und traegt keine Semantik; alles andere zaehlt.
  if diff -q <(_ohne_footer "$src") <(_ohne_footer "$dst") >/dev/null 2>&1; then
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
  echo "RESULT: DRIFT — aktive Kopie(n) weichen von tools/claude-hooks ab: $DRIFTED (beheben: tools/hook-dist-drift.sh --sync)${BASIS_HINWEIS}"
  exit 1
else
  echo "RESULT: OK — $SYNCED aktive Kopie(n) synchron · $NV_ANZAHL Quelldatei(en) nicht verteilt (kein Befund)${BASIS_HINWEIS}"
fi
