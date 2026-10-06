"""Drill fuer gh_poll_ohne_frist_scanner.py (Slug gh-poll-schleife-ohne-frist).

Realfall (2026-09-28, dev-hub#404): ein Deploy-Waechter pollte mit
`while true; … gh pr view …; gh run list …; sleep 60; done` und endete nur,
wenn alles fertig war — 306 gh-Aufrufe an einem Tag mit erschoepftem Kontingent.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "gh_poll_ohne_frist_scanner", _DIR / "gh_poll_ohne_frist_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

MODUL = _DIR / "gh_poll_ohne_frist_scanner.py"

#: Der Realfall, auf seine Struktur gekuerzt (Pfade und Repos neutralisiert).
REALFALL = """#!/bin/bash
declare -A fertig
while true; do
  offen=0
  while read -r r url; do
    st=$(gh pr view "$n" -R "$nwo" --json state --jq .state 2>/dev/null)
    zeile=$(gh run list -R "$nwo" --branch main --limit 10 --json status)
    [ -z "$zeile" ] && { offen=$((offen+1)); continue; }
  done < prs.txt
  [ "$offen" -eq 0 ] && { echo fertig; exit 0; }
  sleep 60
done
"""


# --- Fristlose Schleifen: melden --------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "until gh pr view 5 --json state | grep -q MERGED; do sleep 30; done",
        "while true; do gh run list -L1; sleep 60; done",
        "while :; do\n  gh api repos/x/y/actions/runs >/dev/null\n  sleep 20\ndone",
        "cd /tmp && while ! gh run view 1 --json status | grep -q completed; do sleep 5; done",
    ],
)
def test_should_flag_gh_poll_loop_without_deadline(cmd: str) -> None:
    assert scanner.befund(cmd) == "befehl"


def test_should_flag_realfall_script_started_via_bash(tmp_path: Path) -> None:
    skript = tmp_path / "deploy-watch.sh"
    skript.write_text(REALFALL, encoding="utf-8")

    assert scanner.befund(f"bash {skript}") == "deploy-watch.sh"
    assert scanner.befund(f"nohup bash {skript} > log 2>&1 &") == "deploy-watch.sh"


# --- Mit Frist oder ohne gh: still ------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        # Frist ueber timeout, $SECONDS, date +%s, benannte Grenze.
        "timeout 600 bash -c 'until gh pr view 5 | grep -q MERGED; do sleep 30; done'",
        "ende=$((SECONDS+900)); while [ $SECONDS -lt $ende ]; do gh run list -L1; sleep 60; done",
        "t0=$(date +%s); while true; do gh run list; [ $(( $(date +%s)-t0 )) -gt 600 ] && break; done",
        "for i in $(seq 1 $MAX_VERSUCHE); do gh pr view 1; done; while false; do gh pr view 1; done",
        # Schleife ohne gh, gh ohne Schleife, gh nur im Text.
        "while true; do curl -s localhost:8000/health; sleep 5; done",
        "gh pr view 5 --json state",
        "for pr in 1 2 3; do gh pr view $pr; done",
        "gh repo list o --json name -q '.[].name' | while read r; do gh issue view 1 -R o/$r; done",
        "while IFS= read -r url; do gh pr view \"$url\"; done < prs.txt",
        "echo 'while true; do nothing; done'; git log --grep 'gh pr view'",
        "",
    ],
)
def test_should_not_flag_bounded_or_unrelated_commands(cmd: str) -> None:
    assert scanner.befund(cmd) is None


def test_should_accept_script_when_timeout_wraps_the_call(tmp_path: Path) -> None:
    skript = tmp_path / "w.sh"
    skript.write_text(REALFALL, encoding="utf-8")

    assert scanner.befund(f"timeout 1800 bash {skript}") is None


def test_should_skip_missing_and_oversized_scripts(tmp_path: Path) -> None:
    gross = tmp_path / "gross.sh"
    gross.write_text(REALFALL + "#" * scanner.SKRIPT_MAX_BYTES, encoding="utf-8")

    assert scanner.befund(f"bash {tmp_path}/fehlt.sh") is None
    assert scanner.befund(f"bash {gross}") is None


# --- Hook-Vertrag ------------------------------------------------------------


def _lauf(payload: dict | str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(MODUL)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTEST_CURRENT_TEST": "drill"},
    )


def test_should_exit_zero_and_print_hint_for_deadline_free_loop() -> None:
    loop = "while true; do gh run list; done"
    for eingabe in ({"command": loop, "run_in_background": True}, {"command": f"nohup sh -c '{loop}' &"}):
        res = _lauf({"tool_name": "Bash", "tool_input": eingabe})

        assert res.returncode == 0
        assert "gh-poll-schleife-ohne-frist" in res.stdout


def test_should_stay_silent_in_foreground_because_tool_timeout_bounds_it() -> None:
    res = _lauf({"tool_name": "Bash", "tool_input": {"command": "while true; do gh run list; done"}})

    assert res.returncode == 0
    assert res.stdout == ""


@pytest.mark.parametrize(
    ("eingabe", "erwartet"),
    [
        ({"command": "x", "run_in_background": True}, True),
        ({"command": "nohup bash w.sh > log 2>&1 &"}, True),
        ({"command": "bash w.sh &\necho gestartet"}, True),
        ({"command": "bash w.sh > log 2>&1"}, False),
        ({"command": "a && b"}, False),
    ],
)
def test_should_detect_background_calls(eingabe: dict, erwartet: bool) -> None:
    assert scanner.im_hintergrund(eingabe) is erwartet


def test_should_stay_silent_for_other_tools_and_garbage() -> None:
    cmd = {"command": "while true; do gh run list; done", "run_in_background": True}

    for payload in ({"tool_name": "Monitor", "tool_input": cmd}, "kein json", "{}"):
        res = _lauf(payload)
        assert res.returncode == 0
        assert res.stdout == ""
