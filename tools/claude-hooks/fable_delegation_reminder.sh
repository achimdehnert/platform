#!/usr/bin/env bash
# GATE_HEADER (KONZ-038 D8) — auch in Shell maschinenlesbar gehalten, damit
# tools/gate_drill_check.py Kopf und Registry gegeneinander pruefen kann:
#   "slug": "fable-session-no-delegation"
#   "mode": "advisory"
#   "owner": "achim"
#   "last_drill_pass": "2026-09-03"
#   "evidence": "tools/claude-hooks/tests/test_fable_delegation_reminder.py"
#
# Claude Code SessionStart hook — Fable-Delegationserinnerung (#2750 K3).
#
# Erinnert bei jedem Sessionstart auf claude-fable* an die maschinenlesbare
# Aufgabenklasse->Tier-Tabelle aus policies/session-routing.md (#2750 K2), damit
# die Delegationsregel ohne Zuruf greift statt erst auf Nachfrage: ab Klasse
# "Umsetzung" einen ausfuehrungsreifen Brief schreiben und mit explizitem
# model: delegieren, statt die Fable-Session selbst auf T3-Arbeit zu verbrennen.
#
# Ehrliche Grenze: erkannt wird der settings-Default-Wechsel (wie /model +
# Save), NICHT ein per --model gesetztes Session-Override — dieselbe Grenze
# wie model_change_detector.sh. Vertrag: IMMER Exit 0.
set -uo pipefail

SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
POLICY_FILE="${POLICY_FILE:-$HOME/.claude/policies/session-routing.md}"

model="$(python3 - "$SETTINGS" <<'PYEOF' 2>/dev/null
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("model", ""))
except Exception:
    print("")
PYEOF
)"
[ -n "$model" ] || exit 0

# Suffix wie [1m] abschneiden (gleiche Normalisierung wie model_change_detector.sh)
model="$(printf '%s' "$model" | sed -E 's/\[[^]]*\]$//')"

case "$model" in
  claude-fable*) ;;
  *) exit 0 ;;
esac

[ -f "$POLICY_FILE" ] || exit 0

block="$(python3 - "$POLICY_FILE" <<'PYEOF' 2>/dev/null
import sys

path = sys.argv[1]
try:
    text = open(path, encoding="utf-8").read()
except Exception:
    sys.exit(0)

start_marker = "<!-- routing-table:start -->"
end_marker = "<!-- routing-table:end -->"
si = text.find(start_marker)
ei = text.find(end_marker)
if si == -1 or ei == -1 or ei < si:
    sys.exit(0)

# Absatz: der zusammenhaengende nicht-leere Textblock direkt vor dem Start-Marker.
before_lines = text[:si].splitlines()
i = len(before_lines) - 1
while i >= 0 and before_lines[i].strip() == "":
    i -= 1
absatz_lines = []
while i >= 0 and before_lines[i].strip() != "":
    absatz_lines.append(before_lines[i])
    i -= 1
absatz_lines.reverse()

tabelle = text[si + len(start_marker):ei].strip("\n")

out = []
if absatz_lines:
    out.append("\n".join(absatz_lines))
out.append(tabelle)
print("\n\n".join(out))
PYEOF
)"
[ -n "$block" ] || exit 0

echo "🎯 Fable-Session — Delegationsregel (#2750 K3)"
echo
echo "$block"
echo
echo "Ohne model: erbt der Subagent Fable, Fork erbt immer Fable. Ergebnisprüfung bleibt inline."
exit 0
