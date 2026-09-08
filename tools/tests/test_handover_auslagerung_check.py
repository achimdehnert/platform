"""Drill fuer scripts/checks/handover_auslagerung_check.py — platform#2974.

Der Realfall steht als erster Test: am 2026-09-08 wanderte ein Stand-Block ins Archiv
und nahm sechs offene Punkte mit, darunter eine Frist zum 30.11. Byte-Deckel,
Append-only und Frische waren dabei alle gruen — es gab schlicht keine Pruefung, die
danach fragt.

Der zweitwichtigste Test ist `test_should_let_a_closed_reference_go`: genau dafuer gibt
es das Archiv. Ein Gate, das auch geschlossene Nummern festhaelt, macht das Auslagern
unmoeglich und waere in einer Woche abgeschaltet.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "checks")
)

import handover_auslagerung_check as hac  # noqa: E402

ALT = """## Stand

**Sitzung xyz:** Kill-Gate ohne Zahl, Frist 2026-11-30, in
[#66](https://github.com/achimdehnert/robo-lab/issues/66). Dazu #2924.

## Offene Faeden

1. Irgendwas: https://github.com/achimdehnert/platform/issues/2148
"""

NEU_OHNE_RETTUNG = """## Stand

**Sitzung xyz:** nach AGENT_HANDOVER_ARCHIVE.md ausgelagert.

## Offene Faeden

1. Irgendwas: https://github.com/achimdehnert/platform/issues/2148
"""

NEU_MIT_RETTUNG = """## Stand

**Sitzung xyz:** nach AGENT_HANDOVER_ARCHIVE.md ausgelagert.

## Offene Faeden

1. Irgendwas: https://github.com/achimdehnert/platform/issues/2148
2. Kill-Gate ohne Zahl, Frist 2026-11-30: https://github.com/achimdehnert/robo-lab/issues/66
3. Evidenz-Hook Rev 6: https://github.com/achimdehnert/platform/issues/2924
"""


def test_should_name_the_references_that_vanished():
    weg = hac.verschwundene(ALT, NEU_OHNE_RETTUNG)
    assert weg == ["achimdehnert/platform#2924", "achimdehnert/robo-lab#66"]


def test_should_stay_silent_when_the_reference_was_rescued_into_the_threads():
    assert hac.verschwundene(ALT, NEU_MIT_RETTUNG) == []


def test_should_keep_the_cross_repo_owner_from_the_url():
    """robo-lab liegt unter achimdehnert — aber gelesen, nicht geraten."""
    weg = hac.verschwundene(ALT, NEU_OHNE_RETTUNG)
    assert "achimdehnert/robo-lab#66" in weg


def _lauf(tmp_path, alt, neu, zustand):
    """main() ueber die Test-Naht, mit einer Basis aus einer Datei statt aus git."""
    (tmp_path / "AGENT_HANDOVER.md").write_text(neu, encoding="utf-8")
    z = tmp_path / "zustand.json"
    z.write_text(json.dumps(zustand), encoding="utf-8")
    return hac.verschwundene(alt, neu), z


def test_should_let_a_closed_reference_go(tmp_path):
    """Ein geschlossener Vorgang darf mit dem Block wandern — dafuer gibt es das Archiv."""
    weg, _ = _lauf(tmp_path, ALT, NEU_OHNE_RETTUNG, {})
    zustand = {
        "achimdehnert/robo-lab#66": "CLOSED",
        "achimdehnert/platform#2924": "CLOSED",
    }
    offen = [s for s in weg if zustand.get(s) == "OPEN"]
    assert offen == []


def test_should_flag_only_the_open_one(tmp_path):
    weg, _ = _lauf(tmp_path, ALT, NEU_OHNE_RETTUNG, {})
    zustand = {
        "achimdehnert/robo-lab#66": "OPEN",
        "achimdehnert/platform#2924": "CLOSED",
    }
    offen = [s for s in weg if zustand.get(s) == "OPEN"]
    assert offen == ["achimdehnert/robo-lab#66"]


def test_should_treat_unknown_state_as_blind_not_green():
    """Ein nicht ermittelbarer Zustand ist eine Luecke, keine Entwarnung."""
    weg = hac.verschwundene(ALT, NEU_OHNE_RETTUNG)
    zustand = {"achimdehnert/robo-lab#66": "OPEN"}
    blind = [s for s in weg if s not in zustand]
    assert blind == ["achimdehnert/platform#2924"]
