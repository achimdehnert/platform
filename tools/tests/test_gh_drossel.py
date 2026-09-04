"""Drill fuer tools/gh_drossel.py (platform#2735).

Beide Richtungen, wie bei jedem Melder: die Probe muss die Drosselung FANGEN und
den gesunden Fall DURCHLASSEN. Ohne die zweite Haelfte waere eine Probe, die immer
„gedrosselt" sagt, ebenfalls gruen — und genau diese Sorte Null hat den Anlass-Fall
verursacht.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "gh_drossel.py"
_spec = importlib.util.spec_from_file_location("gh_drossel", _SCRIPT)
g = importlib.util.module_from_spec(_spec)
sys.modules["gh_drossel"] = g
_spec.loader.exec_module(g)

RATE_LIMIT = (1, "API rate limit exceeded for user ID 33293099")
GESUND = (0, "achimdehnert/platform\n")


# --- die Probe --------------------------------------------------------------


@pytest.mark.f3
def test_should_raise_when_the_api_is_throttled():
    with pytest.raises(g.DrosselFehler) as exc:
        g.probe(laeufer=lambda pfad, timeout=0: RATE_LIMIT)
    assert "rate limit" in str(exc.value)


@pytest.mark.f1
def test_should_pass_when_the_api_answers():
    """Positivkontrolle — ohne sie bestuende auch eine Probe, die immer wirft."""
    assert g.probe(laeufer=lambda pfad, timeout=0: GESUND) is True


@pytest.mark.f1
def test_should_return_false_instead_of_raising_when_asked_to():
    assert g.probe(werfen=False, laeufer=lambda pfad, timeout=0: RATE_LIMIT) is False


@pytest.mark.f1
def test_should_not_accept_an_answer_about_a_different_repo():
    """Subjektbindung: eine 200 ueber irgendetwas belegt nicht DIESES Repo."""
    assert (
        g.probe(werfen=False, laeufer=lambda pfad, timeout=0: (0, "wer/anders\n"))
        is False
    )


@pytest.mark.f2
@pytest.mark.parametrize(
    "rc,text", [(124, "timeout"), (127, "gh fehlt"), (1, "Not Found")]
)
def test_should_treat_every_failure_as_not_measurable(rc, text):
    assert g.probe(werfen=False, laeufer=lambda pfad, timeout=0: (rc, text)) is False


# --- die Sperre -------------------------------------------------------------


@pytest.mark.f1
def test_should_be_free_when_no_lock_file_exists(tmp_path):
    assert g.sperre_frei(tmp_path / "keine.json") is True


@pytest.mark.f1
def test_should_be_taken_while_a_fresh_lock_lies(tmp_path):
    p = tmp_path / "sperre.json"
    p.write_text(
        json.dumps({"name": "x", "seit": time.time(), "pid": 1}), encoding="utf-8"
    )
    assert g.sperre_frei(p) is False


@pytest.mark.f1
def test_should_ignore_a_lock_left_behind_by_a_dead_run(tmp_path):
    """Eine Sperre ohne Verfall waere schlimmer als keine — sie blockiert fuer immer."""
    p = tmp_path / "sperre.json"
    alt = time.time() - g.SPERR_ALTER_S - 60
    p.write_text(json.dumps({"name": "x", "seit": alt, "pid": 1}), encoding="utf-8")
    assert g.sperre_frei(p) is True


@pytest.mark.f3
def test_should_survive_a_corrupt_lock_file(tmp_path):
    p = tmp_path / "sperre.json"
    p.write_text("{kaputt", encoding="utf-8")
    assert g.sperre_frei(p) is True


@pytest.mark.f3
def test_should_refuse_a_second_fleet_run(tmp_path):
    p = tmp_path / "sperre.json"
    with g.flotten_sperre("erster", pfad=p):
        assert p.exists()
        with pytest.raises(g.DrosselFehler) as exc, g.flotten_sperre("zweiter", pfad=p):
            pytest.fail("der zweite Lauf haette nicht starten duerfen")
    assert "laeuft bereits" in str(exc.value)


@pytest.mark.f1
def test_should_release_the_lock_afterwards(tmp_path):
    p = tmp_path / "sperre.json"
    with g.flotten_sperre("erster", pfad=p):
        pass
    assert not p.exists()


@pytest.mark.f3
def test_should_release_the_lock_even_when_the_run_fails(tmp_path):
    p = tmp_path / "sperre.json"
    with pytest.raises(ValueError), g.flotten_sperre("erster", pfad=p):
        raise ValueError("Lauf gescheitert")
    assert not p.exists(), (
        "eine Sperre, die einen Absturz ueberlebt, blockiert die Flotte"
    )
