"""Tests für tools/skill_phasen_deckung.py.

Die Prüfung hält die WARN-Deutungstabelle der Session-Skills an ihrem Runner
fest. Sie entstand, weil `0.7.4 prio-referenzen` am 2026-09-16 WARN meldete und
im Skill nirgends vorkam — weder Deutung noch Checklisten-Zeile.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from skill_phasen_deckung import ungedeutet, warn_phasen  # noqa: E402

RUNNER = '''
record "0.1 probe" "PASS" "alles gut"
record "0.7.4 prio-referenzen" "WARN" "zeigt auf Erledigtes"
record "0.7.9 gate-deckung" "WARN" "ungedeckt"
record "E.10 abgleich" "JUDGMENT" "urteilen"
'''


def test_should_collect_only_warn_capable_phases():
    """PASS-only-Phasen sind bewusst nicht deutungspflichtig."""
    assert warn_phasen(RUNNER) == ["0.7.4", "0.7.9", "E.10"]


def test_should_report_phase_missing_from_skill():
    skill = "| `0.7.9 gate-deckung` | ... |\n| `E.10 abgleich` | ... |"
    assert ungedeutet(RUNNER, skill) == ["0.7.4"]


def test_should_pass_when_every_phase_is_mentioned():
    skill = "0.7.4 und 0.7.9 und E.10 stehen alle drin"
    assert ungedeutet(RUNNER, skill) == []


def test_should_be_green_on_the_real_repo():
    """Positivkontrolle am echten Bestand — sonst ist der Prüfer nur Theorie."""
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "skill_phasen_deckung.py")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_should_fail_loudly_when_a_phase_is_removed_from_the_skill():
    """Gegenprobe: nimmt man die Zeile weg, muss der Prüfer sie vermissen."""
    runner = (REPO_ROOT / "tools" / "session_start_checks.sh").read_text(encoding="utf-8")
    skill = (REPO_ROOT / ".windsurf" / "workflows" / "session-start.md").read_text(
        encoding="utf-8"
    )
    assert ungedeutet(runner, skill) == []
    ohne = skill.replace("0.7.4", "X.X.X")
    assert "0.7.4" in ungedeutet(runner, ohne)
