#!/usr/bin/env bash
# PreToolUse(Bash) gate — blockt `git push` mit unformatierten Python-Dateien.
#
# Hintergrund: recurring_finding `lint-failure-no-local-gate` (retro_kpis ≥2,
# zuletzt Retro d2522c #9: iil-adrfw#59 ging mit ruff-format-Fehler in CI,
# 19-Min-Rework-Loop; Repo-CLAUDE.md verlangte "make fmt before committing").
# Memory-/Instruktions-Schicht hielt nicht -> hartes Gate (Muster:
# block_stale_branch_commit.sh).
#
# Verhalten:
#   - feuert nur auf Bash-Kommandos, die "git push" enthalten
#   - nur in Repos mit ruff-Config (ruff.toml / .ruff.toml / [tool.ruff] in pyproject)
#   - prueft NUR die gegen origin/<default> geaenderten *.py (schnell, kein Repo-Scan)
#   - FAIL-OPEN: kein ruff / kein git / kein Upstream-Vergleich moeglich -> exit 0
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
printf '%s' "$input" | grep -qE 'git (-C [^ ]+ )?push' || exit 0

# Ziel-Verzeichnis best effort (Retro d2522c-incr #3: alter Boundary-Regex
# matchte das JSON-quote-adjazente erste `cd` NIE -> Hauptfall lief in den
# $PWD-Fallback; Schein-Gruen im Selbsttest, weil Test-CWD=Zielrepo war):
#   1. `git -C <dir> ... push` hat Vorrang
#   2. sonst LETZTES `cd`/`pushd`-Ziel VOR dem push (mehrfach-cd korrekt)
#   3. sonst $PWD (dokumentierter Fallback; $VAR-Pfade -> rev-parse-Fail -> fail-open)
dir="$(printf '%s' "$input" | grep -oE 'git -C [^ ]+ [^"]*push' | head -1 | awk '{print $3}')"
if [ -z "$dir" ]; then
  pre="${input%%git push*}"
  dir="$(printf '%s' "$pre" | grep -oE "(cd|pushd)[[:space:]]+[^;&|)\"']+" | tail -1 | sed -E 's/^(cd|pushd)[[:space:]]+//; s/[[:space:]]+$//')"
fi
dir="${dir%\"}"; dir="${dir#\"}"
[ -z "$dir" ] && dir="$PWD"
dir="${dir/#\~/$HOME}"

root="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || exit 0

# Nur Python-Repos mit ruff-Config gaten
has_ruff_cfg=""
[ -f "$root/ruff.toml" ] || [ -f "$root/.ruff.toml" ] && has_ruff_cfg=1
if [ -z "$has_ruff_cfg" ] && [ -f "$root/pyproject.toml" ]; then
  grep -q '^\[tool\.ruff' "$root/pyproject.toml" 2>/dev/null && has_ruff_cfg=1
fi
[ -z "$has_ruff_cfg" ] && exit 0

# ruff finden (fail-open)
RUFF=""
if command -v ruff >/dev/null 2>&1; then RUFF="ruff";
elif python3 -c "import ruff" >/dev/null 2>&1; then RUFF="python3 -m ruff"; fi
[ -z "$RUFF" ] && exit 0

# Geaenderte .py gegen origin/<default> (Fallback: letzter Commit); fail-open
default="$(git -C "$root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||')"
# Retro d2522c-incr #9: statt "main" raten erst gh fragen (deterministisch, fail-open)
if [ -z "$default" ]; then
  default="$(cd "$root" && gh repo view --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null)"
fi
[ -z "$default" ] && default="main"
# platform#1754 (A): Der Fallback haengt an der AUFLOESBARKEIT der Referenz, nicht
# an der Leere des Ergebnisses. Vorher feuerte er genau dann, wenn der richtige
# Vergleich "keine .py geaendert" ergab -- dann pruefte das Gate HEAD~1, bei frisch
# abgezweigten Branches also den letzten main-Merge, und blockte PRs mit 0 .py.
if git -C "$root" rev-parse --verify --quiet "origin/${default}" >/dev/null 2>&1; then
  files="$(git -C "$root" diff --name-only "origin/${default}...HEAD" -- '*.py' 2>/dev/null)"
else
  files="$(git -C "$root" diff --name-only HEAD~1 -- '*.py' 2>/dev/null)"
fi
[ -z "$files" ] && exit 0

# Nur existierende Dateien pruefen
existing=""
while IFS= read -r f; do
  [ -f "$root/$f" ] && existing="$existing $root/$f"
done <<< "$files"
[ -z "${existing// /}" ] && exit 0

# shellcheck disable=SC2086
bad="$(cd "$root" && $RUFF format --check --force-exclude $existing 2>/dev/null | grep -c 'Would reformat' || true)"
if [ "${bad:-0}" -gt 0 ]; then
  reason="⛔ git push geblockt: ${bad} geänderte .py-Datei(en) sind nicht ruff-formatiert (Gate lint-failure-no-local-gate, retro d2522c #9). Fix: cd ${root} && ${RUFF} format . (bzw. make fmt), dann erneut pushen."
  reason="${reason//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
fi
exit 0
