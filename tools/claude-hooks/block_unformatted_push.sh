#!/usr/bin/env bash
# PreToolUse(Bash) gate — blockt `git push` mit unformatierten Python-Dateien.
#
# GATE_HEADER (KONZ-038 D8) — auch in Shell maschinenlesbar gehalten, damit
# tools/gate_drill_check.py Kopf und Registry gegeneinander pruefen kann:
#   "slug": "lint-failure-no-local-gate"
#   "mode": "blocking"
#   "owner": "achim"
#   "last_drill_pass": "2026-08-28"
#   "evidence": "tools/claude-hooks/tests/test_block_unformatted_push_suite.py"
# Bestand seit ff2981b0, registriert erst 2026-08-12 (platform#1650 Nachmessung).
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

# ── Pfadgetriggerte Zusatzpruefungen (Retro 62f875 §5a, Gate rueckfaellig → ausweiten) ──
# platform#2397 ging mit zwei Fehlern in CI, die dieses Gate nicht sah: `infra/hosts.yaml`
# ohne Host-Block (hosts_audit) und ein Zeitbomben-Test unter tools/tests. Beides laeuft
# lokal in Sekunden. Regel: was im Diff liegt, entscheidet, was vor dem Push laeuft.
# FAIL-OPEN bei Werkzeugfehler (rc>1), DENY nur bei echtem Befund (rc==1).
pf_default="$(git -C "$root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||')"
[ -z "$pf_default" ] && pf_default="main"
if git -C "$root" rev-parse --verify --quiet "origin/${pf_default}" >/dev/null 2>&1; then
  pf_files="$(git -C "$root" diff --name-only "origin/${pf_default}...HEAD" 2>/dev/null)"
else
  pf_files="$(git -C "$root" diff --name-only HEAD~1 2>/dev/null)"
fi
if printf '%s\n' "$pf_files" | grep -qx 'infra/hosts.yaml' && [ -f "$root/infra/scripts/hosts_audit.py" ]; then
  pf_out="$(cd "$root" && timeout 60 python3 infra/scripts/hosts_audit.py 2>&1)"; pf_rc=$?
  if [ "$pf_rc" = "1" ]; then
    pf_line="$(printf '%s' "$pf_out" | grep -m1 -E 'schema|Finding|frisch|stale|Label' | cut -c1-160)"
    reason="⛔ git push geblockt: infra/hosts.yaml im Diff und hosts_audit.py meldet Findings (Gate lint-failure-no-local-gate, Ausweitung Retro 62f875): ${pf_line}. Fix: python3 infra/scripts/hosts_audit.py lokal gruen ziehen, dann erneut pushen."
    reason="${reason//\"/\\\"}"
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
    exit 0
  fi
fi
if printf '%s\n' "$pf_files" | grep -qE '^tools/.*\.py$' && [ -d "$root/tools/tests" ] && python3 -c 'import pytest' >/dev/null 2>&1; then
  (cd "$root" && timeout 180 python3 -m pytest tools/tests -q -x -p no:cacheprovider >/dev/null 2>&1); pf_rc=$?
  if [ "$pf_rc" = "1" ]; then
    reason="⛔ git push geblockt: tools/*.py im Diff und pytest tools/tests ist rot (Gate lint-failure-no-local-gate, Ausweitung Retro 62f875 — Realfall platform#2397 Zeitbomben-Test). Fix: cd ${root} && python3 -m pytest tools/tests -q -x, dann erneut pushen."
    reason="${reason//\"/\\\"}"
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
    exit 0
  fi
fi

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

# ZWEI Pruefungen, nicht eine — der Slug heisst "lint", und bis zum 2026-08-23 lief
# hier ausschliesslich `ruff format`. Das ist Layout (Zeilenumbrueche, Quotes), NICHT
# Lint: ein Import nach einer Zuweisung auf Modulebene (E402) ist fuer `ruff format`
# unsichtbar. Gemessen am 2026-08-23 (Skeptiker-Experiment, Retro a84f71 Befund 5):
# dieselbe Datei -> `ruff format --check` "already formatted", exit 0 · `ruff check`
# meldet 2x E402. Das Gate war verdrahtet, aktiv, gedrillt — und konnte die Sache,
# die sein Name verspricht, seit dem Bau am 2026-08-04 nicht sehen. Realfall: PR
# #2236, CI zweimal rot, obwohl der PreToolUse-Hook lief.
#
# `ruff check` laeuft OHNE --select: massgeblich ist die Repo-Config, damit der Hook
# genau das prueft, woran die CI scheitert — nicht eine eigene, engere Regelmenge.
# Auch hier wird am EXIT-CODE geurteilt, nicht am Ausgabemuster — dieselbe Lehre
# wie beim lint-Zweig unten, nur eine Version spaeter gelernt. Bis 2026-09-03 stand
# hier `grep -c 'Would reformat'`. ruff 0.16 schreibt stattdessen `unformatted: File
# would be reformatted` (Fundstelle als eingerueckter Diff darunter), also zaehlte
# der Grep 0, und der Format-Zweig des Gates konnte NICHTS mehr blocken. Gemessen
# 2026-09-03: 6 der 14 eigenen Selbsttests rot, alle in Richtung "erwartet deny,
# war silent". Der Zaehler ist nur Kosmetik fuer die Meldung; die Entscheidung
# haengt am rc. rc>1 = Werkzeugfehler = FAIL-OPEN (s.u.).
fmt_rc=0
# shellcheck disable=SC2086
(cd "$root" && $RUFF format --check --force-exclude $existing >/dev/null 2>&1) || fmt_rc=$?
bad=0
if [ "$fmt_rc" = "1" ]; then
  # shellcheck disable=SC2086
  bad="$(cd "$root" && $RUFF format --check --force-exclude $existing 2>/dev/null \
        | grep -cE '^(unformatted:|Would reformat:)' || true)"
  [ "${bad:-0}" -eq 0 ] && bad=1
fi
# Geurteilt wird am EXIT-CODE, nicht an einem geratenen Ausgabemuster: `ruff check`
# gibt 0 = sauber, 1 = Verstoesse, >1 = Werkzeugfehler. Das erste Muster hier zaehlte
# Zeilen der Form `datei:zeile:spalte` — ruff 0.15 rueckt die Fundstelle aber als
# ` --> datei:zeile:spalte` ein, und der Zaehler blieb bei 0. Die eigene Positiv-
# kontrolle hat das gefangen; ohne sie waere der Fix fuer Befund 5 wirkungslos
# gewesen und haette trotzdem "gebaut" ausgesehen.
# Werkzeugfehler (rc>1) ist FAIL-OPEN — ein Hook, der bei kaputter Config jeden
# Push blockt, wird abgeschaltet und meldet danach gar nichts mehr.
lint_rc=0
# shellcheck disable=SC2086
(cd "$root" && $RUFF check --force-exclude --quiet $existing >/dev/null 2>&1) || lint_rc=$?
lint=0
if [ "$lint_rc" = "1" ]; then
  # shellcheck disable=SC2086
  lint="$(cd "$root" && $RUFF check --force-exclude --quiet --output-format=concise $existing 2>/dev/null | grep -c ':' || true)"
  [ "${lint:-0}" -eq 0 ] && lint=1
fi
if [ "${lint:-0}" -gt 0 ] && [ "${bad:-0}" -eq 0 ]; then
  reason="⛔ git push geblockt: ${lint} ruff-check-Verstoss/Verstoesse in geänderten .py-Dateien (Gate lint-failure-no-local-gate). Fix: cd ${root} && ${RUFF} check --fix . , Rest von Hand, dann erneut pushen."
  reason="${reason//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
fi
if [ "${bad:-0}" -gt 0 ]; then
  # `${lint:+…}` prueft auf NICHT-LEER, und `lint` ist hier immer gesetzt — bei
  # sauberem Lint eben auf "0". Die Meldung endete deshalb auf "zusaetzlich 0
  # ruff-check-Verstoesse". Unsichtbar geblieben, weil dieser Zweig seit ruff 0.16
  # nie erreicht wurde (platform#2738); mit dem reparierten Gate liest es jeder,
  # der einen unformatierten Push versucht.
  zusatz=""
  [ "${lint:-0}" -gt 0 ] && zusatz=" · zusaetzlich ${lint} ruff-check-Verstoss/Verstoesse"
  reason="⛔ git push geblockt: ${bad} geänderte .py-Datei(en) sind nicht ruff-formatiert (Gate lint-failure-no-local-gate, retro d2522c #9)${zusatz}. Fix: cd ${root} && ${RUFF} format . (bzw. make fmt), dann erneut pushen."
  reason="${reason//\"/\\\"}"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
fi
exit 0
