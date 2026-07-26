#!/usr/bin/env bash
# Claude Code SessionStart hook — Rueckstand des lokalen Klons melden.
#
# Warum es das gibt (Session 2026-07-26, platform): der Assistent las eine
# Workflow-Datei aus einem veralteten `main`, meldete einen Defekt als neuen
# Befund und schrieb ihn in ein Issue — behoben war er seit 30 Minuten durch
# einen bereits gemergten PR. Dafuer gab es zu dem Zeitpunkt ZWEI Memories
# ("Stale Klon nie Ground Truth", "aus dem Ref lesen"), beide im Kontext.
#
# Eine dritte Formulierung derselben Regel haette nichts geaendert (Lehre
# "Kanon-Entscheidung braucht Gate"). Dieser Hook stellt die Tatsache stattdessen
# an den Anfang der Session, wo sie nicht zu uebersehen ist.
#
# Vertrag: IMMER Exit 0 - ein Hinweis darf keine Session blockieren. Kein
# `git pull`, kein Schreibzugriff: nur `fetch` und zaehlen.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Nur der Haupt-Branch ist interessant; auf einem Session-Branch ist ein
# Rueckstand gegenueber main normal und kein Befund.
branch="$(git branch --show-current 2>/dev/null)"
[ -n "$branch" ] || exit 0

timeout 15 git fetch --quiet origin 2>/dev/null || exit 0

upstream="origin/${branch}"
git rev-parse --verify --quiet "$upstream" >/dev/null 2>&1 || upstream="origin/main"
git rev-parse --verify --quiet "$upstream" >/dev/null 2>&1 || exit 0

behind="$(git rev-list --count "HEAD..$upstream" 2>/dev/null || echo 0)"
[ "$behind" -gt 0 ] 2>/dev/null || exit 0

newest="$(git log -1 --format='%h %s' "$upstream" 2>/dev/null | cut -c1-72)"

echo "⚠ STALE KLON: $behind Commit(s) hinter $upstream."
echo "   Neuester dort: $newest"
echo "   Vor jeder Aussage ueber Repo-Inhalte aus dem Ref lesen"
echo "   (git show $upstream:<pfad>), nicht aus dem Arbeitsbaum."
exit 0
