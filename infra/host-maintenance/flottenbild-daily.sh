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
# ── Backup-Deckung, taeglich statt nur bei Sitzungsstart (platform#2529) ────
# Der CI-Melder backup-deckung.yml sieht nur prod: sein Runner hat keinen
# ssh-Zugang zu prod-b (Owner-Entscheid "Weg B" 2026-08-25, #2284 K5 — kein
# Runner-Key zwischen Prod-Hosts). Gemessen wurde prod-b deshalb ausschliesslich
# in Phase 0.7.17 beim Sitzungsstart. Das ist ~6x am Tag genug — und genau null
# mal, sobald niemand arbeitet. Ausgerechnet prod-b hing am 2026-08-31 mit einem
# sechs Tage alten Backup-Skript zurueck.
# Diese Maschine erreicht beide Hosts und hat mit dem Timer bereits einen
# Zeitplan. Ein zweiter Timer waere ein zweiter Melder, der ausfallen kann.
DECKUNG_LOG="$OUT/backup-deckung-$STAMP.txt"
DECKUNG=$(timeout 300 python3 "$PLATFORM/tools/backup_deckung.py" --kurz 2>&1)
drc=$?
printf '%s\n' "$DECKUNG" > "$DECKUNG_LOG"
ln -sfn "backup-deckung-$STAMP.txt" "$OUT/backup-deckung-latest.txt"
find "$OUT" -name 'backup-deckung-*.txt' -mtime +30 -delete
echo "backup-deckung: rc=$drc — $DECKUNG"

# Bei Befund melden. Der einzige belegte Alarmweg ist github-issue-owner
# (infra/alarmwege.yaml) — Discord existiert nicht, Mail hat keinen MTA.
# Idempotent ueber den Titel: ein offenes Issue wird nicht verdoppelt, sonst
# entstuende taeglich eines und der Kanal waere binnen einer Woche taub.
if [ "$drc" -ne 0 ] && command -v gh >/dev/null 2>&1; then
  TITEL="[backup-deckung] Taeglicher Lauf meldet einen Befund"
  OFFEN=$(gh issue list --repo achimdehnert/platform --state open \
            --search "$TITEL in:title" --json number --jq 'length' 2>/dev/null || echo 1)
  if [ "$OFFEN" = "0" ]; then
    gh issue create --repo achimdehnert/platform \
      --title "$TITEL" \
      --assignee achimdehnert \
      --body "Der taegliche Deckungslauf auf der Dev-Maschine endete mit rc=$drc.

\`\`\`
$DECKUNG
\`\`\`

Vollbild: \`python3 platform/tools/backup_deckung.py\` · Rohdaten: \`$DECKUNG_LOG\`

Dieser Melder existiert, weil der CI-Melder prod-b nicht sieht (Weg B, #2284 K5)
und Phase 0.7.17 nur laeuft, wenn jemand eine Sitzung startet (#2529)." \
      >/dev/null 2>&1 && echo "backup-deckung: Issue angelegt"
  else
    echo "backup-deckung: Befund steht bereits als offenes Issue"
  fi
fi

# ── Speicher-Vorlauf, taeglich (platform#2529) ──────────────────────────────
# Die einzige der fuenf sitzungsabhaengigen Weltzustands-Phasen, bei der ein
# verpasster Lauf den Schaden ERZEUGT statt ihn nur spaeter zu melden: eine volle
# Platte stoppt Dienste. Die vier anderen (erreichbarkeit, origin-tls,
# prod-wirkung, umgebung) melden einen Zustand, der bei der naechsten Sitzung noch
# da ist — sie bleiben bewusst ohne Zeitplan.
# Zweiter Grund: speicher_melder.py leitet seine Rate aus einem TAGESJOURNAL ab.
# Ohne taeglichen Lauf gibt es keine Tagespunkte, und ohne Tagespunkte keine
# Vorlaufzeit — der Melder haengt nicht nur am Sitzungsstart, er wird durch ihn
# auch ungenau.
SPEICHER=$(timeout 180 python3 "$PLATFORM/tools/speicher_melder.py" --kurz 2>&1)
src=$?
echo "speicher: rc=$src — $SPEICHER"

if [ "$src" -ne 0 ] && command -v gh >/dev/null 2>&1; then
  STITEL="[speicher] Taeglicher Lauf meldet knappen Vorlauf"
  SOFFEN=$(gh issue list --repo achimdehnert/platform --state open \
             --search "$STITEL in:title" --json number --jq 'length' 2>/dev/null || echo 1)
  if [ "$SOFFEN" = "0" ]; then
    gh issue create --repo achimdehnert/platform \
      --title "$STITEL" \
      --assignee achimdehnert \
      --body "Der taegliche Speicher-Lauf auf der Dev-Maschine endete mit rc=$src.

\`\`\`
$SPEICHER
\`\`\`

Vollbild: \`python3 platform/tools/speicher_melder.py\`

Dieser Melder laeuft taeglich, weil eine volle Platte nach Kalender passiert und
nicht nach Arbeitsrhythmus — und weil die Rate aus Tagespunkten stammt, die ohne
taeglichen Lauf gar nicht entstehen (#2529)." \
      >/dev/null 2>&1 && echo "speicher: Issue angelegt"
  else
    echo "speicher: Befund steht bereits als offenes Issue"
  fi
fi

echo "flottenbild-daily: rc=$rc -> $OUT/latest.html"
exit $rc
