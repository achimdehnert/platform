#!/usr/bin/env bash
# Kanonische Quelle (ADR-258, Stufe A) — via cc-skill-dist `hooks`-Lane nach
# ~/.claude/hooks/managed/reap_worktrees.sh verteilt (managed/-Subdir, weil generate das
# Verzeichnis atomar swappt und ~/.claude/hooks/ auch hand-gepflegte Hooks enthält).
# STABILER PFAD: der settings.json-SessionEnd-Eintrag verweist dauerhaft auf diesen Pfad
# (REC-4); Versionierung passiert im Inhalt.
#
# SessionEnd-Hook: reapt gemergte Session-Worktrees (Gate worktree-orphan-accumulation).
# worktree-reaper.py ist self-protecting — behält offene-PR/Lease/DIRTY-Worktrees, schreibt
# Restore-Manifest je Repo. Namensraum-Garantie (REC-19): bearbeitet ausschliesslich die
# Worktrees unter den Repos in $GITHUB_DIR; fremde Pfade ausserhalb bleiben unberuehrt.
# Darf den Session-Abschluss nie blockieren -> laeuft still und beendet immer mit 0 (REC-7).
set -uo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
REAPER="$GITHUB_DIR/platform/tools/worktree-reaper.py"
[ -f "$REAPER" ] || exit 0

for repo in "$GITHUB_DIR"/*/; do
  # nur Haupt-Checkouts (.git als Verzeichnis); Linked-Worktrees haben .git als Datei
  [ -d "$repo/.git" ] || continue
  ( cd "$repo" && python3 "$REAPER" --apply >/dev/null 2>&1 ) || true
done

exit 0
