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

# Einstufung (Runbook §0). Drei Dimensionen, absteigend nach Gewicht:
#   Familie/Hauptversion  -> MAJOR   (opus-5 -> fable-5, fable-5-1 -> fable-6)
#   Datums-Snapshot       -> MAJOR   (haiku-4-5-20251001 -> haiku-4-5-20260315)
#   Punkt-Release         -> MINOR   (fable-5 -> fable-5-1)
#   [..]-Variante         -> SUFFIX  (fable-5-1 -> fable-5-1[1m])
# Unparsbares faellt immer auf MAJOR (fail-loud).
#
# WARUM das Datum eine eigene Dimension ist (Retro c36878, #2655): die
# Vorgaengerfassung schnitt mit `^claude-([a-z]+)-([0-9]+).*$` nach der ERSTEN
# Ziffernfolge ab und verwarf alles danach. `claude-haiku-4-5-20251001` und
# `claude-haiku-4-9-20260315` ergaben beide `haiku-4` und damit MINOR — obwohl
# zwei verschiedene Snapshots zwei verschiedene Gewichtsmatrizen sind. MINOR
# heisst im Runbook: Vollmachten bleiben aktiv, keine Re-Qualifikation. Das ist
# genau die Fehlerrichtung, die "im Zweifel MAJOR" verhindern soll, und sie traf
# nur BEKANNTE Formen: Provider-Praefixe und Schreibfehler fielen korrekt auf
# MAJOR, weil ihr Match leer blieb. Charta Art. 2.5: "Vertrauen ist nicht
# uebertragbar zwischen Gewichtsmatrizen."
norm_id() { printf '%s' "$1" | sed -E 's/\[[^]]*\]$//'; }
# Familie + ERSTE Versionsstelle. Leer bei unbekannter Form -> Aufrufer wertet MAJOR.
fam_major() { printf '%s' "$1" | sed -nE 's/^claude-([a-z]+)-([0-9]+)([^0-9].*)?$/\1-\2/p'; }
# Datums-Snapshot: ein Segment mit 6+ Ziffern. Leer, wenn die ID keins traegt.
datum_teil() { printf '%s' "$1" | sed -nE 's/^.*-([0-9]{6,})$/\1/p'; }
# Alles nach der Familie: die vollstaendige Versionskette inkl. Datum. Damit
# faellt keine Stelle mehr still unter den Tisch.
version_kette() { printf '%s' "$1" | sed -nE 's/^claude-[a-z]+-(.*)$/\1/p'; }
LOG="$STATE_DIR/model-changes.log"

if [ "$current" != "$previous" ]; then
  printf '%s' "$current" > "$STATE" 2>/dev/null
  p="$(norm_id "$previous")"; c="$(norm_id "$current")"
  if [ "$p" = "$c" ]; then
    klasse="SUFFIX"
  elif [ -z "$(fam_major "$p")" ] || [ "$(fam_major "$p")" != "$(fam_major "$c")" ]; then
    # unbekannte Form ODER Familie/Hauptversion wechselt
    klasse="MAJOR"
  elif [ "$(datum_teil "$p")" != "$(datum_teil "$c")" ]; then
    # gleiche Familie+Hauptversion, aber anderer Snapshot = anderes Gewicht
    klasse="MAJOR"
  elif [ "$(version_kette "$p")" != "$(version_kette "$c")" ]; then
    klasse="MINOR"
  else
    # normalisiert verschieden, aber in jeder Dimension gleich: nur Variante
    klasse="SUFFIX"
  fi
  # Durable Spur (vorher: nur eine Session-Start-Zeile, die niemand nachlesen konnte).
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$previous" "$current" "$klasse" >> "$LOG" 2>/dev/null
  case "$klasse" in
    SUFFIX) ;;
    MINOR)
      echo "🔁 MODELLWECHSEL erkannt (MINOR): ${previous} → ${current}"
      echo "   Pflicht (KONZ-038 §5.6 Minor): Smoke-Kalibrierung (Runbook §1);"
      echo "   Vollmachten bleiben active, assessed_with im naechsten Ritual nachziehen."
      echo "   Runbook: platform docs/governance/model-rebaseline-runbook.md"
      ;;
    MAJOR)
      echo "🔁 MODELLWECHSEL erkannt (MAJOR): ${previous} → ${current}"
      echo "   Pflicht (KONZ-038 §5.6): Smoke-Kalibrierung fahren + Typ-A-Labels mit"
      echo "   Exposure im letzten Fenster re-assessen (assessed_with veraltet)."
      echo "   Vollmachten (registry/lotse-authorizations.yaml, Art. 2.5): Re-Qualifikation"
      echo "   nach Runbook §3a — bis dahin gelten sie als suspendiert."
      echo "   Runbook: platform docs/governance/model-rebaseline-runbook.md"
      ;;
  esac
fi
exit 0
