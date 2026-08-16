"""Drill fuer tools/befund_journal.py (platform#2004).

Geprueft wird das Verhalten, nicht der Quelltext — die Lehre vom 2026-08-15:
`assert '…' in quelle` bricht bei jeder Umformulierung und haelt jede
Verhaltensaenderung fuer in Ordnung.

Der teuerste Fall steht in `test_should_not_heal_when_repo_was_unreachable`:
eine Abdeckungsluecke darf nicht wie eine Heilung aussehen, sonst ist jeder
wiederkehrende Befund ewig jung und K3 waere vakuum erfuellt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import befund_journal as bj  # noqa: E402


@pytest.fixture
def journal(tmp_path: Path) -> Path:
    """Nie in das echte ~/.claude/befund-journal.json schreiben.

    Dieselbe Isolation wie bei den Welle-1-Scannern: ein Messapparat, den seine
    eigenen Tests bedienen koennen, misst irgendwann sich selbst (#1986).
    """
    return tmp_path / "befund-journal.json"


def _lauf(zeilen: list[str], pfad: Path) -> tuple[list[str], dict]:
    daten = bj.lade(pfad)
    meldungen = bj.aufnehmen(bj._zeilen_lesen("\n".join(zeilen)), daten)
    bj.sichere(daten, pfad)
    return meldungen, daten


def test_should_record_finding_with_target_repo(journal: Path) -> None:
    _, daten = _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure:cad-hub"], journal)
    assert "0.7 deploy-scan::cad-hub" in daten["befunde"]
    assert daten["befunde"]["0.7 deploy-scan::cad-hub"]["repo"] == "cad-hub"


def test_should_split_one_warn_into_one_entry_per_repo(journal: Path) -> None:
    _, daten = _lauf(
        ["0.7 deploy-scan\tWARN\tcad-hub travel-beat\tfailure: beide"], journal
    )
    assert set(daten["befunde"]) == {
        "0.7 deploy-scan::cad-hub",
        "0.7 deploy-scan::travel-beat",
    }


def test_should_age_across_runs(journal: Path) -> None:
    zeile = ["0.7 deploy-scan\tWARN\tcad-hub\tfailure:cad-hub"]
    for _ in range(3):
        meldungen, daten = _lauf(zeile, journal)
    assert daten["befunde"]["0.7 deploy-scan::cad-hub"]["laeufe"] == 3
    assert any("ALTBEFUND" in m for m in meldungen)


def test_should_stay_quiet_below_the_age_threshold(journal: Path) -> None:
    meldungen, _ = _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert meldungen == []


def test_should_not_let_changing_numbers_reset_the_age(journal: Path) -> None:
    """Der Fingerabdruck darf die Notiz nicht enthalten.

    Die Notizen tragen wechselnde Zahlen (`9/10 Repos`). Waeren sie Teil des
    Schluessels, waere jeder Lauf ein neuer Befund und nichts wuerde je altern —
    K3 waere gebaut und wirkungslos.
    """
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure (9/10 Repos)"], journal)
    _, daten = _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure (8/10 Repos)"], journal)
    assert daten["befunde"]["0.7 deploy-scan::cad-hub"]["laeufe"] == 2


def test_should_heal_when_phase_reports_pass(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    _, daten = _lauf(["0.7 deploy-scan\tPASS\tplatform\talles gruen"], journal)
    assert daten["befunde"] == {}


def test_should_heal_repo_no_longer_named_by_the_same_phase(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub travel-beat\tzwei"], journal)
    _, daten = _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tnur noch einer"], journal)
    assert set(daten["befunde"]) == {"0.7 deploy-scan::cad-hub"}


def test_should_not_heal_when_repo_was_unreachable(journal: Path) -> None:
    """Abdeckungsluecke ist keine Heilung — der teuerste Fehler dieses Werkzeugs.

    `trading-hub` ist fuer 0.7 regelmaessig nicht abfragbar. Ohne die
    ungeprueft-Spalte verschwaende der Befund still und taeuchte beim naechsten
    erfolgreichen Scan als neu wieder auf: ewig jung, nie eskaliert.
    """
    _lauf(["0.7 deploy-scan\tWARN\ttrading-hub\tfailure"], journal)
    _, daten = _lauf(
        ["0.7 deploy-scan\tWARN\tcad-hub\tanderes Repo\ttrading-hub"], journal
    )
    assert "0.7 deploy-scan::trading-hub" in daten["befunde"]
    assert daten["befunde"]["0.7 deploy-scan::trading-hub"]["laeufe"] == 1


def test_should_not_heal_when_phase_did_not_run_at_all(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    _, daten = _lauf(["0.1 server-probe\tPASS\tplatform\tok"], journal)
    assert "0.7 deploy-scan::cad-hub" in daten["befunde"]


def test_should_flag_foreign_repo_finding_as_open(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 1
    )


def test_should_not_flag_own_repo_finding(journal: Path) -> None:
    _lauf(["0.7.4 prio-referenzen\tWARN\tplatform\tstale"], journal)
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 0
    )


def test_should_not_demand_an_artifact_for_a_local_condition(journal: Path) -> None:
    """Der Fehlalarm, den der erste scharfe Lauf zeigte (2026-08-16).

    `0.4 repo-sync` nennt `risk-hub`, weil dort ein dirty Arbeitsbaum liegt. Das
    ist ein lokaler Zustand, kein Defekt im Repo — ein Issue in `risk-hub` waere
    Unsinn. Das Alter wird trotzdem gefuehrt; nur die Artefakt-Pflicht greift nicht.
    """
    _lauf(["0.4 repo-sync\tWARN\trisk-hub\tGUARD(dirty)"], journal)
    daten = bj.lade(journal)
    assert "0.4 repo-sync::risk-hub" in daten["befunde"]
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 0
    )


def test_should_clear_the_gate_once_an_artifact_is_recorded(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert (
        bj.main(
            [
                "--verankert",
                "0.7 deploy-scan::cad-hub",
                "https://github.com/achimdehnert/cad-hub/issues/1",
                "--datei",
                str(journal),
            ]
        )
        == 0
    )
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 0
    )


def test_should_reject_a_waiver_without_a_reason(journal: Path) -> None:
    """Ein Verzicht ohne Grund ist kein Verzicht, sondern ein stilles Weglassen."""
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert (
        bj.main(
            ["--verzichtet", "0.7 deploy-scan::cad-hub", "   ", "--datei", str(journal)]
        )
        == 2
    )
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 1
    )


def test_should_accept_a_waiver_with_a_reason(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert (
        bj.main(
            [
                "--verzichtet",
                "0.7 deploy-scan::cad-hub",
                "Repo ist eingefroren",
                "--datei",
                str(journal),
            ]
        )
        == 0
    )
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 0
    )


def test_should_survive_a_corrupt_journal(journal: Path) -> None:
    """Der Runner darf an diesem Werkzeug nie scheitern."""
    journal.write_text("{kaputt", encoding="utf-8")
    _, daten = _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert "0.7 deploy-scan::cad-hub" in daten["befunde"]


def test_should_ignore_broken_input_lines(journal: Path) -> None:
    _, daten = _lauf(["", "nur-eine-spalte", "0.1 x\tPASS"], journal)
    assert daten["befunde"] == {}


def test_should_write_valid_json(journal: Path) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert json.loads(journal.read_text(encoding="utf-8"))["befunde"]


def test_should_report_ungeprueft_when_the_journal_does_not_exist(tmp_path) -> None:
    """Kein Journal = keine Datenbasis = kein Urteil (Retro 9d861a, Befund #9).

    Beim allerersten Lauf meldete dieses Gate `OK`, obwohl die Datei gar nicht
    existierte — ein vakuum wahres Freigabe-Signal. Genau die Fehlform, die am
    2026-08-15 schon einmal ein „0 Fehlalarme"-Urteil wertlos machte.
    """
    fehlt = tmp_path / "gibt-es-nicht.json"
    assert not fehlt.exists()
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(fehlt)])
        == 0
    )


def test_should_report_ok_only_with_an_existing_journal(journal: Path, capsys) -> None:
    """Positivkontrolle: mit vorhandenem Journal ist OK weiterhin OK."""
    _lauf(["0.1 server-probe\tPASS\tplatform\tok"], journal)
    assert journal.exists()
    bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
    aus = capsys.readouterr().out
    assert "RESULT: OK" in aus and "UNGEPRUEFT" not in aus
