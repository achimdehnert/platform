#!/usr/bin/env bash
# ADR-266 / #2075 K2 — Cold-Start-Baseline (deterministisch, ohne LLM).
# Je Paket: frischer Shallow-Clone -> Einstiegskommando erkennen -> Setup -> Tests.
#
#   tools/pypi_coldstart_baseline.sh <org/repo> [<org/repo> ...]
#   COLDSTART_BASE=<dir>  Arbeits-/Ausgabeverzeichnis (default: mktemp -d)
#
# Ausgabe: eine TSV-Zeile je Paket (slug, entry, setup, tests, dauer) nach
# $COLDSTART_BASE/results.tsv; volle Logs je Paket daneben. Bestanden =
# entry!=none && setup=ok && tests=ok. Braucht gh (auth) fuer private Repos.
set -u
BASE="${COLDSTART_BASE:-$(mktemp -d)}"
OUT="$BASE/results.tsv"
mkdir -p "$BASE"
PYBIN=python3

run_pkg() {
  local slug="$1"            # org/repo
  local name="${slug#*/}"
  local dir="$BASE/$name"
  local log="$BASE/$name.log"
  rm -rf "$dir"
  local t0=$SECONDS
  if ! gh repo clone "$slug" "$dir" -- --depth 1 -q >>"$log" 2>&1; then
    echo -e "$slug\tclone_fail\t-\t-\t$((SECONDS-t0))s" >> "$OUT"; return
  fi
  cd "$dir" || return
  # Einstiegskommando erkennen
  local entry="none"
  if [ -f Makefile ]; then
    grep -qE '^setup:' Makefile && grep -qE '^test:' Makefile && entry="make setup+test"
    [ "$entry" = "none" ] && grep -qE '^test:' Makefile && entry="make test"
  fi
  [ "$entry" = "none" ] && [ -f pyproject.toml ] && entry="pip+pytest"
  # Setup + Tests in eigenem venv
  local setup=fail tests=fail
  $PYBIN -m venv "$dir/.cs-venv" >>"$log" 2>&1
  # shellcheck disable=SC1091
  source "$dir/.cs-venv/bin/activate"
  case "$entry" in
    "make setup+test")
      if timeout 240 make setup >>"$log" 2>&1; then setup=ok
        if timeout 240 make test >>"$log" 2>&1; then tests=ok; fi
      fi ;;
    "make test")
      if timeout 240 pip install -q -e ".[dev]" >>"$log" 2>&1 || timeout 240 pip install -q -e . pytest >>"$log" 2>&1; then setup=ok
        if timeout 240 make test >>"$log" 2>&1; then tests=ok; fi
      fi ;;
    "pip+pytest")
      if timeout 240 pip install -q -e ".[dev]" >>"$log" 2>&1 || timeout 240 pip install -q -e . pytest >>"$log" 2>&1; then setup=ok
        pip install -q pytest >>"$log" 2>&1
        if timeout 240 $PYBIN -m pytest -q >>"$log" 2>&1; then tests=ok; fi
      fi ;;
    none) : ;;
  esac
  deactivate 2>/dev/null || true
  echo -e "$slug\t$entry\t$setup\t$tests\t$((SECONDS-t0))s" >> "$OUT"
}

for slug in "$@"; do run_pkg "$slug"; done
echo "=== $OUT ==="
cat "$OUT"
