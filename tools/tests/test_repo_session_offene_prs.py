"""Tests für tools/repo_session_offene_prs.py (Gate parallel-session-pr-collision).

Retro 2026-09-10: #3030 und #3033 kollidierten acht Minuten auseinander, weil
nichts vor dem Start einer Aufgabe die offenen PRs des Tages zeigt. `--eingabe`
ersetzt `gh` hier durch eine JSON-Fixture, damit die Tests offline und
deterministisch laufen (kein echtes GitHub nötig).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "repo_session_offene_prs.py"


def _run(tmp_path: Path, prs: list[dict], extra_args: list[str] | None = None):
    eingabe = tmp_path / "prs.json"
    eingabe.write_text(json.dumps(prs), encoding="utf-8")
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--eingabe",
        str(eingabe),
        "--seit",
        "2026-09-10",
    ]
    cmd += extra_args or []
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


def test_should_list_two_open_prs_with_numbers(tmp_path):
    prs = [
        {"number": 3030, "title": "fix A", "author": "achim", "files": []},
        {"number": 3033, "title": "fix B", "author": "someone", "files": []},
    ]
    res = _run(tmp_path, prs)
    assert res.returncode == 0, res.stderr
    assert "Offene PRs seit 2026-09-10: 2" in res.stdout
    assert "#3030" in res.stdout and "#3033" in res.stdout


def test_should_report_keine_for_empty_list(tmp_path):
    res = _run(tmp_path, [])
    assert res.returncode == 0, res.stderr
    assert "keine" in res.stdout


def test_should_mark_pr_with_shared_path(tmp_path):
    prs = [
        {
            "number": 1,
            "title": "touches shared file",
            "author": "x",
            "files": [{"path": "tools/repo-session.sh"}],
        },
        {
            "number": 2,
            "title": "unrelated",
            "author": "y",
            "files": [{"path": "docs/foo.md"}],
        },
    ]
    res = _run(tmp_path, prs, ["--pfade", "tools/repo-session.sh"])
    line1 = next(ln for ln in res.stdout.splitlines() if ln.startswith("#1"))
    line2 = next(ln for ln in res.stdout.splitlines() if ln.startswith("#2"))
    assert "⚠ gleiche Datei" in line1
    assert "⚠ gleiche Datei" not in line2


def test_should_truncate_long_title_to_60_chars(tmp_path):
    prs = [{"number": 5, "title": "x" * 120, "author": "x", "files": []}]
    res = _run(tmp_path, prs)
    line = next(ln for ln in res.stdout.splitlines() if ln.startswith("#5"))
    title_field = line.split("#5  ", 1)[1].split("  @x")[0]
    assert len(title_field) <= 60
