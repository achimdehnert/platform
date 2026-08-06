#!/usr/bin/env bash
# GATE_HEADER (KONZ-038 D8) — auch in Shell maschinenlesbar gehalten, damit
# tools/gate_drill_check.py Kopf und Registry gegeneinander pruefen kann:
#   "slug": "model-change-detection"
#   "mode": "advisory"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-06"
#   "evidence": "tools/claude-hooks/tests/test_model_change_detector.py"
#
# Claude Code SessionStart hook — Modellwechsel-Detektor (KONZ-038 D7, §5.6).
#
# Event-Trigger statt Kalender-Raten (EXT2-M28-6): vergleicht die konfigurierte
# Modell-ID (settings.json "model") gegen den letzten bekannten Stand und meldet
# einen Wechsel an den Session-Anfang — dort haengt die Pflicht dran:
# Smoke-Kalibrierung + Re-Assessment der Typ-A-Labels mit Exposure im letzten
# Fenster (Runbook: docs/governance/model-rebaseline-runbook.md).
#
# Ehrliche Grenze: erkannt wird der settings-Default-Wechsel (wie /model + Save),
# NICHT ein per --model gesetztes Session-Override. Vertrag: IMMER Exit 0.
set -uo pipefail

SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
STATE_DIR="${MODEL_STATE_DIR:-$HOME/.claude/hooks/state}"
STATE="$STATE_DIR/model-id"

current="$(python3 - "$SETTINGS" <<'PYEOF' 2>/dev/null
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("model", ""))
except Exception:
    print("")
PYEOF
)"
[ -n "$current" ] || exit 0

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
previous="$(cat "$STATE" 2>/dev/null || echo "")"

if [ -z "$previous" ]; then
  printf '%s' "$current" > "$STATE" 2>/dev/null
  exit 0
fi

if [ "$current" != "$previous" ]; then
  printf '%s' "$current" > "$STATE" 2>/dev/null
  echo "🔁 MODELLWECHSEL erkannt: ${previous} → ${current}"
  echo "   Pflicht (KONZ-038 §5.6): Smoke-Kalibrierung fahren + Typ-A-Labels mit"
  echo "   Exposure im letzten Fenster re-assessen (assessed_with veraltet)."
  echo "   Runbook: platform docs/governance/model-rebaseline-runbook.md"
fi
exit 0
