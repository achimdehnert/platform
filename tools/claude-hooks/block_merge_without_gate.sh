#!/usr/bin/env bash
# PreToolUse(Bash) gate — blockt Merge und Publish, wenn gar kein CI gelaufen ist.
#
# GATE_HEADER (KONZ-038 D8):
#   "slug": "no-checks-reported-read-as-green"
#   "mode": "blocking"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-25"
#   "evidence": "tools/claude-hooks/tests/test_block_merge_without_gate.sh"
#
# Hintergrund: Retro 3106ae Befund #1. `gh pr checks 51` meldete
# "no checks reported"; das wurde als gruenes Licht gelesen, der PR gemergt und
# `iil-aifw==0.13.0` nach PyPI veroeffentlicht. Erst die Retro fand, dass das CI
# jenes Repos seit sechs Tagen VOR jedem Job scheiterte (Workflow-Referenz mit
# einem Pfadteil zu viel, aifw#53). Eine leere Pruefliste sieht aus wie Ruhe und
# heisst "hier prueft nichts".
#
# Warum ein eigener Slug und nicht der `claim-before-cheapest-check`-Scanner:
# jener liest die SPRACHE einer Behauptung. Hier ist nichts behauptet worden —
# es wurde gehandelt. Die Familie ist fuer einen Textscanner unsichtbar
# (Owner-Entscheid 2026-08-25 "ausweiten", umgesetzt als eigenes Gate).
#
# Verhalten:
#   - feuert auf `gh pr merge` und auf `publish-package.sh`
#   - `--admin` passiert: das ist der ausdrueckliche, benannte Bypass eines Menschen
#   - blockt, wenn der letzte Lauf auf dem Default-Branch `failure` ist
#   - blockt, wenn es GAR KEINEN Lauf gibt — das ist der eigentliche Fall
#   - FAIL-OPEN: kein gh, kein Netz, Repo nicht bestimmbar -> exit 0
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
cmd="$(printf '%s' "$input" | tr '\n' ' ')"

printf '%s' "$cmd" | grep -qE 'gh pr merge|publish-package\.sh' || exit 0
# Der benannte Bypass eines Menschen ist kein Fall fuer dieses Gate.
printf '%s' "$cmd" | grep -q -- '--admin' && exit 0
command -v gh >/dev/null 2>&1 || exit 0

# Repo bestimmen: explizites --repo hat Vorrang, sonst das Verzeichnis.
repo="$(printf '%s' "$cmd" | grep -oE '\-\-repo [A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' | head -1 | awk '{print $2}')"
if [ -z "$repo" ]; then
  dir="$(printf '%s' "$cmd" | grep -oE "(cd|pushd)[[:space:]]+[^;&|)\"']+" | tail -1 | sed -E 's/^(cd|pushd)[[:space:]]+//; s/[[:space:]]+$//')"
  dir="${dir:-$PWD}"; dir="${dir%\"}"; dir="${dir#\"}"
  [ -d "$dir" ] || exit 0
  repo="$(cd "$dir" 2>/dev/null && gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
fi
[ -n "$repo" ] || exit 0

zweig="$(gh repo view "$repo" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || true)"
[ -n "$zweig" ] || exit 0

laeufe="$(gh run list --repo "$repo" --branch "$zweig" --limit 5 --json conclusion,status --jq '[.[]|select(.status=="completed")|.conclusion] | join(",")' 2>/dev/null)" || exit 0

melde() {
  reason="${1//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
}

if [ -z "$laeufe" ]; then
  melde "⛔ Merge/Publish geblockt: ${repo} hat auf ${zweig} KEINEN abgeschlossenen CI-Lauf (Gate no-checks-reported-read-as-green). Eine leere Pruefliste heisst 'hier prueft nichts', nicht 'nichts zu beanstanden' — Realfall aifw#53: sechs Tage tote Workflow-Referenz, in dem Fenster ging 0.13.0 nach PyPI. Pruefen: gh run list --repo ${repo} --branch ${zweig} --limit 3"
fi

erster="${laeufe%%,*}"
if [ "$erster" = "failure" ]; then
  melde "⛔ Merge/Publish geblockt: der letzte abgeschlossene CI-Lauf auf ${repo}@${zweig} ist FAILURE (Gate no-checks-reported-read-as-green). Erst die Ursache ansehen — vorbestehend ist eine Feststellung, keine Freigabe: gh run list --repo ${repo} --branch ${zweig} --limit 3"
fi

exit 0
