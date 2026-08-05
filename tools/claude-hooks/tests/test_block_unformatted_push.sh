#!/usr/bin/env bash
# Selbsttest für block_unformatted_push.sh — Lehre aus Retro d2522c-incr #3:
# ALLE Fälle laufen aus FREMDEM CWD (Hook-Prozess-Realität), damit der
# $PWD-Fallback keinen Parsing-Defekt maskieren kann (Schein-Grün-Falle).
# Aufruf: bash ~/.claude/hooks/test_block_unformatted_push.sh  → exit 0 = alle grün
set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/block_unformatted_push.sh"
FIX="$(mktemp -d)"
FOREIGN="$(mktemp -d)"   # fremdes CWD ohne git/ruff
fails=0

setup_repo() { # $1=dir  $2=py-inhalt — 2 Commits, damit HEAD~1 als Diff-Basis existiert
  git -C "$1" init -q
  git -C "$1" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
  echo 'line-length = 120' > "$1/ruff.toml"
  printf '%s\n' "$2" > "$1/bad.py"
  git -C "$1" add -A && git -C "$1" -c user.email=t@t -c user.name=t commit -qm c
}

run_hook() { # $1=command-string ; echo Ausgabe
  (cd "$FOREIGN" && printf '{"tool_input":{"command":"%s"}}' "$1" | bash "$HOOK")
}

check() { # $1=name $2=erwartet(deny|silent) $3=output
  local got="silent"
  printf '%s' "$3" | grep -q '"permissionDecision":"deny"' && got="deny"
  if [ "$got" = "$2" ]; then echo "PASS  $1"; else echo "FAIL  $1 (erwartet $2, war $got)"; fails=$((fails+1)); fi
}

# Repo A: unformatiert
A="$FIX/a"; mkdir -p "$A"; setup_repo "$A" 'x=1
y  =  2'
# Repo B: formatiert
B="$FIX/b"; mkdir -p "$B"; setup_repo "$B" 'x = 1'
( cd "$B" && { command -v ruff >/dev/null && ruff format . || python3 -m ruff format .; } >/dev/null 2>&1
  git add -A && git -c user.email=t@t -c user.name=t commit -qm fmt )
# Dir C: kein ruff-Repo
C="$FIX/c"; mkdir -p "$C"; git -C "$C" init -q
git -C "$C" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
touch "$C/x"; git -C "$C" add -A; git -C "$C" -c user.email=t@t -c user.name=t commit -qm c

# --- Parsing-Zweig (Hauptfälle, fremdes CWD!) ---
check "T1 plain cd&&push (Hauptfall)"        deny   "$(run_hook "cd $A && git push origin main")"
check "T2 mehrfach-cd nimmt letztes"          deny   "$(run_hook "cd /tmp && ls && cd $C && cd $A && git push")"
check "T3 git -C direkt"                      deny   "$(run_hook "git -C $A push origin main")"
check "T7 pushd wird erkannt"                 deny   "$(run_hook "pushd $A && git push")"
# --- Negativ-/Fallback-Zweig ---
check "T4 formatiertes Repo silent"           silent "$(run_hook "cd $B && git push")"
check "T5 kein ruff-Repo silent"              silent "$(run_hook "cd $C && git push")"
check "T6 Variable nicht auflösbar → fail-open" silent "$(run_hook "cd \\\"\$SCRATCH\\\" && git push")"
check "T8 kein push → silent"                 silent "$(run_hook "cd $A && git status")"
# --- Fallback-Zweig POSITIV isoliert (CWD=Repo, kein cd im Kommando) ---
out="$( (cd "$A" && printf '{"tool_input":{"command":"git push origin main"}}' | bash "$HOOK") )"
check "T9 PWD-Fallback greift"                deny   "$out"

# --- T10: Regression zu platform#1754 (A) ---
# Alle Repos oben haben KEIN origin -- sie testen ausschliesslich den Fallback.
# Der Realfall ist ein Branch MIT aufloesbarem origin/<default>, der keine .py
# aendert, waehrend HEAD~1 (der letzte main-Merge) unformatierte .py enthaelt.
# Vor dem Fix feuerte der Fallback hier und blockte einen PR mit 0 .py.
D="$FIX/d"; ORIGIN="$FIX/d-origin"
git init -q --bare -b main "$ORIGIN"
git clone -q "$ORIGIN" "$D" 2>/dev/null
git -C "$D" -c init.defaultBranch=main checkout -q -b main 2>/dev/null || true
echo 'line-length = 120' > "$D/ruff.toml"
printf 'doku\n' > "$D/README.md"
git -C "$D" add -A
git -C "$D" -c user.email=t@t -c user.name=t commit -qm "init"
# Der letzte Commit auf main FUEGT unformatierte .py hinzu -- wie der reale
# main-Merge (#1751). Genau dieser Commit ist HEAD, HEAD~1 liegt davor:
# 'diff HEAD~1 -- *.py' liefert also die .py, 'diff origin/main...HEAD' nicht.
printf 'x=1\ny  =  2\n' > "$D/bad.py"
git -C "$D" add -A
git -C "$D" -c user.email=t@t -c user.name=t commit -qm "merge mit unformatierter py"
git -C "$D" push -q origin main 2>/dev/null
git -C "$D" checkout -q -b feature                # frisch abgezweigt, kein eigener Commit
check "T10 origin aufloesbar + 0 .py -> silent (#1754)" silent "$(run_hook "cd $D && git push origin feature")"

rm -rf "$FIX" "$FOREIGN"
echo "---"
[ "$fails" -eq 0 ] && echo "ALLE TESTS GRÜN" || echo "$fails TEST(S) ROT"
exit "$fails"
