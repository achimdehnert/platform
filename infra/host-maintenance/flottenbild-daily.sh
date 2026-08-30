#!/usr/bin/env bash
# flottenbild-daily.sh — rendert das Flottenbild einmal am Tag auf der Dev-Maschine
# (KONZ-054, Punkt 189 — Owner-Go 2026-08-30).
#
# Warum hier und nicht in GitHub Actions: der Runner auf prod hat keinen ssh-Zugang
# zu den anderen Knoten (platform#2284), die Dev-Maschine hat ihn. Ausgabe liegt
# unter ~/.claude/flottenbild/ — latest.json ist die Eingabe fuer die Session-Start-
# Phase 0.7.22, latest.html die Leseflaeche (Ablageort dev-hub: Owner-Entscheidung).
set -uo pipefail
PLATFORM="${GITHUB_DIR:-$HOME/github}/platform"
OUT="$HOME/.claude/flottenbild"
mkdir -p "$OUT"
STAMP=$(date -u +%Y-%m-%d)
python3 "$PLATFORM/tools/flottenbild.py" --out "$OUT/flottenbild-$STAMP.html" --json "$OUT/flottenbild-$STAMP.json"
rc=$?
ln -sfn "flottenbild-$STAMP.html" "$OUT/latest.html"
ln -sfn "flottenbild-$STAMP.json" "$OUT/latest.json"
# 30 Tage behalten — das ist die Historie, die K3 (Vorhersage) braucht und die es
# vor dem 2026-08-30 nirgends gab.
find "$OUT" -name 'flottenbild-*.json' -mtime +30 -delete
find "$OUT" -name 'flottenbild-*.html' -mtime +30 -delete
echo "flottenbild-daily: rc=$rc -> $OUT/latest.html"
exit $rc
