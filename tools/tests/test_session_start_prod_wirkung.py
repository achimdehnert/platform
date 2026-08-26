"""Tests fuer die Auswertung von Phase 0.7.12 (prod-wirkung) im Session-Start.

Die Auswertung ist ein Python-Schnipsel INNERHALB von `session_start_checks.sh`.
Genau deshalb gibt es diese Datei: ein Schnipsel in einer Shell-Heredoc wird von
`bash -n` als gueltig durchgewunken, auch wenn sein Python nicht laeuft — beim
Bau der Frist-Staffelung am 2026-08-26 war exakt das der Fall (verschachtelte
Anfuehrungszeichen im f-string, Shell-Syntax gruen, Python tot).

Getestet wird deshalb der **ausgelieferte** Text: das Schnipsel wird aus der
Datei geschnitten und ausgefuehrt, nicht aus einer Kopie im Test.

Fachlich geht es um eine Unterscheidung, die vorher fehlte: ein Repo mit
Prod-Gate deployt bei push nur nach staging, Prod verlangt eine bewusste
Freigabe. Sein Rueckstand ist bis zu einer Frist der Normalfall — danach ist
"wartet auf Freigabe" von "vergessen" nicht mehr zu unterscheiden.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SKRIPT = Path(__file__).resolve().parents[1] / "session_start_checks.sh"
_MARKER = "WIRK_OUT=$(printf '%s' \"$WIRK_JSON\" | python3 -c '"


def _schnipsel() -> str:
    """Das Auswertungs-Python aus dem Shell-Skript schneiden."""
    text = _SKRIPT.read_text(encoding="utf-8")
    start = text.index(_MARKER) + len(_MARKER)
    return text[start : text.index("\n' 2>/dev/null", start)]


def _auswerten(befunde: list[dict], geprueft: int = 0) -> tuple[str, str, str]:
    """Liefert (status, note, betroffene_repos) — wie der Runner sie liest."""
    ergebnis = subprocess.run(
        [sys.executable, "-c", _schnipsel()],
        input=json.dumps({"befunde": befunde, "geprueft": geprueft}),
        capture_output=True,
        text=True,
    )
    assert not ergebnis.stderr.strip(), ergebnis.stderr
    status, note, repos = ergebnis.stdout.strip().split("|")
    return status.replace("STATUS=", ""), note, repos


def test_should_stay_quiet_for_a_gated_backlog_within_the_grace_period():
    status, note, repos = _auswerten(
        [{"repo": "risk-hub", "rueckstand": True, "prod_gate": True, "alter_tage": 7}]
    )
    assert status == "PASS"
    assert "wartet auf Prod-Freigabe (kein Befund):risk-hub(7d)" in note
    assert "risk-hub" not in repos, "ein Wartestand ist kein Betroffener"


def test_should_speak_up_once_the_grace_period_has_passed():
    """Nach der Frist ist 'wartet auf Freigabe' von 'vergessen' nicht zu trennen."""
    status, note, repos = _auswerten(
        [{"repo": "tax-hub", "rueckstand": True, "prod_gate": True, "alter_tage": 30}]
    )
    assert status == "WARN"
    assert "RUECKSTAND:tax-hub" in note
    assert "tax-hub" in repos


def test_should_speak_up_immediately_without_a_prod_gate():
    """Die Gegenprobe. Ohne sie bestuende der Test auch, wenn die Frist alles stillstellte."""
    status, note, _ = _auswerten(
        [{"repo": "foo-hub", "rueckstand": True, "alter_tage": 7}]
    )
    assert status == "WARN"
    assert "RUECKSTAND:foo-hub" in note


def test_should_ignore_a_dormant_repo():
    status, note, _ = _auswerten(
        [
            {
                "repo": "alt-hub",
                "rueckstand": True,
                "ruhend": True,
                "lifecycle": "archived",
            }
        ]
    )
    assert status == "PASS"
    assert "alt-hub" not in note


def test_should_report_a_double_run_regardless_of_the_gate():
    """Ein Doppellauf ist kein Wartestand — zwei Hosts bedienen denselben Namen."""
    status, note, _ = _auswerten(
        [{"repo": "bar-hub", "doppellauf": True, "prod_gate": True, "alter_tage": 1}]
    )
    assert status == "WARN"
    assert "DOPPELLAUF:bar-hub" in note


def test_should_pass_when_nothing_is_behind():
    status, note, repos = _auswerten([], geprueft=9)
    assert status == "PASS"
    assert "9 Repo(s)" in note
    assert repos == ""


@pytest.mark.parametrize("kaputt", ["", "kein json", "{"])
def test_should_not_crash_on_unparseable_meter_output(kaputt: str):
    """Ein halb geparster Melder ist schlimmer als keiner — er darf nicht still sterben."""
    ergebnis = subprocess.run(
        [sys.executable, "-c", _schnipsel()],
        input=kaputt,
        capture_output=True,
        text=True,
    )
    assert ergebnis.stdout.startswith("STATUS=WARN"), ergebnis.stdout
