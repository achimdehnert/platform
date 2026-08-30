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

# Der Baum, in dem DIESE Sitzung gearbeitet hat, bekommt keine Karenz (--sitzungsende).
# Warum das noetig ist: die Karenz von 12 Stunden wurde am 2026-08-20 als Antwort auf
# das rueckfaellige Gate `worktree-midsession-accumulation` eingebaut — und konnte den
# Fall, fuer den sie gedacht war, strukturell nie erreichen. Dieser Hook laeuft bei
# JEDEM Sitzungsende, aber keine Sitzung dauert 12 Stunden; der eigene, gerade gemergte
# Baum war beim Aufraeumen immer zu jung und blieb liegen. Zwei gemessene Rueckfaelle
# danach: chat-hub 2026-08-21 (sechs Baeume), ausschreibungs-hub 2026-08-23 (drei nach
# drei Merges).
#
# Die Karenz bleibt fuer alle anderen Baeume unveraendert — sie schuetzt PARALLEL
# laufende Sitzungen (am 2026-08-23 waren es 14 an einem Tag). Nur die Sitzung, die
# gerade endet, darf ueber ihren eigenen Baum sprechen.
#
# `cwd` kommt aus dem SessionEnd-Event auf stdin. Fehlt es (aelterer Client, leeres
# Event), bleibt EIGEN leer und der Aufruf ist wortgleich der bisherige — kein Fallback
# auf Raten.
EIGEN=""
EVENT="$(cat 2>/dev/null || true)"
if [ -n "$EVENT" ]; then
  CWD="$(printf '%s' "$EVENT" | python3 -c "import json,sys
try: print(json.load(sys.stdin).get('cwd') or '')
except Exception: print('')" 2>/dev/null || true)"
  if [ -n "$CWD" ] && [ -d "$CWD" ]; then
    # Wurzel des Worktrees, nicht das Unterverzeichnis, in dem gerade gearbeitet wurde.
    WURZEL="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"
    [ -n "$WURZEL" ] && EIGEN="$WURZEL"
  fi
fi

for repo in "$GITHUB_DIR"/*/; do
  # nur Haupt-Checkouts (.git als Verzeichnis); Linked-Worktrees haben .git als Datei
  [ -d "$repo/.git" ] || continue
  if [ -n "$EIGEN" ]; then
    ( cd "$repo" && python3 "$REAPER" --apply --sitzungsende "$EIGEN" >/dev/null 2>&1 ) || true
  else
    ( cd "$repo" && python3 "$REAPER" --apply >/dev/null 2>&1 ) || true
  fi
done

exit 0
