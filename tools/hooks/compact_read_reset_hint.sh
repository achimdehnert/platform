#!/usr/bin/env bash
# GATE_HEADER (KONZ-038 D8) — auch in Shell maschinenlesbar gehalten, damit
# tools/gate_drill_check.py Kopf und Registry gegeneinander pruefen kann:
#   "slug": "edit-in-worktree-without-read"
#   "mode": "advisory"
#   "owner": "achim"
#   "last_drill_pass": "2026-10-13"
#   "evidence": "tools/tests/test_edit_ohne_read_hinweis.py"
#
# Claude Code SessionStart hook (matcher `compact`) — Read-Zustand nach der
# Kontextverdichtung ansagen.
#
# Warum es das gibt (Retro 2026-10-13 robo-lab 4ce56a, platform#3906): 18 von 31
# Fehlerlaeufen einer Sitzung waren Edits auf Dateien, die der Harness als
# ungelesen fuehrte — "File has not been read yet". Zwei Ausloeser: ein frischer
# Worktree (neuer Pfad, den Hinweis dafuer gibt `repo-session.sh start`) und die
# Kontextverdichtung, nach der jede vorher gelesene Datei wieder als ungelesen
# gilt. Der Harness blockt den Edit selbst; dieses Gate verhindert nur die
# Salve, die danach Lauf fuer Lauf scheitert. Seit 8 Retros notiert, ohne Gate.
#
# Vertrag: IMMER Exit 0, nur bei `"source": "compact"` eine Ausgabe. Ein
# Hinweis, der bei jedem Start redet, wird ueberlesen.
set -uo pipefail

eingabe="$(cat 2>/dev/null || true)"
quelle="$(printf '%s' "$eingabe" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("source", ""))
except Exception:
    print("")
' 2>/dev/null || true)"

[ "$quelle" = "compact" ] || exit 0

cat <<'HINWEIS'
⚠ READ-ZUSTAND ZURUECKGESETZT (Gate edit-in-worktree-without-read): Nach der
  Verdichtung gilt jede vorher gelesene Datei als ungelesen. Vor der ersten
  Edit-Salve alle Zieldateien in EINEM Read-Batch lesen; cat/sed in der Shell
  zaehlen dafuer nicht.
HINWEIS
exit 0
