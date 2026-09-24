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


def _lauf(
    zeilen: list[str],
    pfad: Path,
    lauf_repo: str = "platform",
    register: list[dict] | None = None,
) -> tuple[list[str], dict]:
    daten = bj.lade(pfad)
    meldungen = bj.aufnehmen(
        bj._zeilen_lesen("\n".join(zeilen)),
        daten,
        lauf_repo=lauf_repo,
        register=register,
    )
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


# ── #3470: Heilung zielgebundener Phasen nur bei gleichem Zielrepo ──────────
# Realfall 2026-09-24: TARGET_REPO=platform legte `0.7.26 ci-deckung::platform`
# an, ein PARALLELER Lauf mit TARGET_REPO=robo-lab loeschte ihn wieder, weil die
# Phase im eigenen (robo-lab-)Lauf "geurteilt" hatte — ohne das platform-Zielrepo
# je erreichen zu koennen. `laeufe`/`erstmals`/`entscheiden_bis`/Anker gingen
# verloren.

_ZIELGEBUNDEN = [{"phase": "0.7.4 prio-referenzen", "zielgebunden": True}]


def test_should_keep_zielgebundener_befund_when_a_run_with_another_target_repo_judges(
    journal: Path,
) -> None:
    _lauf(
        ["0.7.4 prio-referenzen\tWARN\tplatform\tstale"],
        journal,
        lauf_repo="platform",
        register=_ZIELGEBUNDEN,
    )
    bj.main(
        [
            "--verankert",
            "0.7.4 prio-referenzen::platform",
            "https://github.com/achimdehnert/platform/issues/1",
            "--datei",
            str(journal),
        ]
    )
    vor = bj.lade(journal)["befunde"]["0.7.4 prio-referenzen::platform"]

    # Paralleler Lauf: dieselbe Phase lief, meldete aber nur robo-lab.
    _, daten = _lauf(
        ["0.7.4 prio-referenzen\tWARN\trobo-lab\tstale"],
        journal,
        lauf_repo="robo-lab",
        register=_ZIELGEBUNDEN,
    )
    nach = daten["befunde"]["0.7.4 prio-referenzen::platform"]
    assert nach["laeufe"] == vor["laeufe"]
    assert nach["erstmals"] == vor["erstmals"]
    assert nach["entscheiden_bis"] == vor["entscheiden_bis"]
    assert nach["artefakt"] == vor["artefakt"]


def test_should_still_heal_fleet_wide_phase_regardless_of_target_repo(
    journal: Path,
) -> None:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal, lauf_repo="platform")
    _, daten = _lauf(
        ["0.7 deploy-scan\tWARN\ttravel-beat\tanderes"], journal, lauf_repo="robo-lab"
    )
    assert "0.7 deploy-scan::cad-hub" not in daten["befunde"]


def test_should_heal_zielgebundener_befund_when_same_target_repo_stops_reporting(
    journal: Path,
) -> None:
    _lauf(
        ["0.7.4 prio-referenzen\tWARN\tplatform\tstale"],
        journal,
        lauf_repo="platform",
        register=_ZIELGEBUNDEN,
    )
    _, daten = _lauf(
        ["0.7.4 prio-referenzen\tPASS\tplatform\tnicht mehr stale"],
        journal,
        lauf_repo="platform",
        register=_ZIELGEBUNDEN,
    )
    assert "0.7.4 prio-referenzen::platform" not in daten["befunde"]


def test_should_default_to_fleet_wide_and_warn_when_phase_missing_from_register(
    journal: Path,
) -> None:
    _lauf(
        ["0.7.4 prio-referenzen\tWARN\tplatform\tstale"],
        journal,
        lauf_repo="platform",
        register=[],
    )
    meldungen, daten = _lauf(
        ["0.7.4 prio-referenzen\tWARN\trobo-lab\tstale"],
        journal,
        lauf_repo="robo-lab",
        register=[],
    )
    # Ohne Register-Eintrag gilt der alte Default (flottenweit) — der Eintrag
    # heilt trotz fremdem Zielrepo, genau wie vor #3470.
    assert "0.7.4 prio-referenzen::platform" not in daten["befunde"]
    assert any("ohne Eintrag" in m and "0.7.4 prio-referenzen" in m for m in meldungen)


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


# ── Wiedervorlage (platform#2215) ───────────────────────────────────────────
#
# Der Anlass ist gemessen, nicht ausgedacht: der Deploy-Befund zu coach-hub war
# seit dem 2026-08-20 in coach-hub#67 verankert und erschien trotzdem in 22
# aufeinanderfolgenden Laeufen wortgleich. `--verankert` hing eine URL an und
# aenderte nichts an der Lautstaerke.

ZEILE = "0.7 deploy-scan\tWARN\tcoach-hub\tfailure: coach-hub"


def _n_laeufe(pfad: Path, n: int, zeile: str = ZEILE) -> list[str]:
    for _ in range(n - 1):
        _lauf([zeile], pfad)
    meldungen, _ = _lauf([zeile], pfad)
    return meldungen


def test_should_report_old_finding_loudly_while_nobody_decided(journal: Path) -> None:
    meldungen = _n_laeufe(journal, 4)
    assert any("⏳ ALTBEFUND" in m for m in meldungen)


def test_should_silence_anchored_finding_until_the_deadline(journal: Path) -> None:
    _n_laeufe(journal, 4)
    assert (
        bj.main(
            [
                "--verankert",
                "0.7 deploy-scan::coach-hub",
                "https://x/67",
                "--datei",
                str(journal),
            ]
        )
        == 0
    )
    meldungen = _n_laeufe(journal, 1)
    assert not any("⏳ ALTBEFUND" in m for m in meldungen)
    assert any("ruhen bis zur Wiedervorlage" in m for m in meldungen)


def test_should_never_let_a_resting_finding_vanish_without_trace(journal: Path) -> None:
    """Schweigen darf nicht von Vergessen ununterscheidbar sein."""
    _n_laeufe(journal, 4)
    bj.main(
        [
            "--verankert",
            "0.7 deploy-scan::coach-hub",
            "https://x/67",
            "--datei",
            str(journal),
        ]
    )
    meldungen = _n_laeufe(journal, 1)
    assert len([m for m in meldungen if "⏸" in m]) == 1
    assert "--bericht" in "".join(meldungen)


def test_should_wake_the_finding_when_the_deadline_passed(journal: Path) -> None:
    _n_laeufe(journal, 4)
    bj.main(
        [
            "--verankert",
            "0.7 deploy-scan::coach-hub",
            "https://x/67",
            "--frist",
            "0",
            "--datei",
            str(journal),
        ]
    )
    daten = json.loads(journal.read_text(encoding="utf-8"))
    daten["befunde"]["0.7 deploy-scan::coach-hub"]["wiedervorlage"] = "2020-01-01"
    journal.write_text(json.dumps(daten), encoding="utf-8")
    meldungen = _n_laeufe(journal, 1)
    assert any("⏰ WIEDERVORLAGE" in m for m in meldungen)
    assert any("2020-01-01 abgelaufen" in m for m in meldungen)


def test_should_wake_the_finding_when_the_symptom_changed(journal: Path) -> None:
    """Eine Parkerlaubnis gilt dem Befund, der beim Parken vorlag — keinem anderen."""
    _n_laeufe(journal, 4)
    bj.main(
        [
            "--verankert",
            "0.7 deploy-scan::coach-hub",
            "https://x/67",
            "--datei",
            str(journal),
        ]
    )
    ruhig = _n_laeufe(journal, 1)
    assert not any("⏳ ALTBEFUND" in m for m in ruhig)

    anders = "0.7 deploy-scan\tWARN\tcoach-hub\tfailure: coach-hub UND apo-hub"
    meldungen = _n_laeufe(journal, 1, zeile=anders)
    assert any("⏳ ALTBEFUND" in m for m in meldungen)


def test_should_apply_the_longer_deadline_to_a_deliberate_waiver(journal: Path) -> None:
    _n_laeufe(journal, 4)
    bj.main(
        [
            "--verzichtet",
            "0.7 deploy-scan::coach-hub",
            "Repo wird stillgelegt",
            "--datei",
            str(journal),
        ]
    )
    e = json.loads(journal.read_text(encoding="utf-8"))["befunde"][
        "0.7 deploy-scan::coach-hub"
    ]
    assert e["wiedervorlage"] == bj._frist(bj.FRIST_VERZICHT_TAGE)
    assert bj.ruhezustand(e, bj._heute()) == "ruht"


def test_should_treat_a_finding_without_deadline_as_loud(journal: Path) -> None:
    """Kein gesetzter Zustand ist kein Ruhe-Zustand — die Vorgabe muss laut sein."""
    assert bj.ruhezustand({"letzte_note": "x"}, "2026-08-23") == "laut"


def test_should_show_the_deadline_in_the_full_report(journal: Path) -> None:
    _n_laeufe(journal, 4)
    bj.main(
        [
            "--verankert",
            "0.7 deploy-scan::coach-hub",
            "https://x/67",
            "--datei",
            str(journal),
        ]
    )
    text = bj.bericht(bj.lade(journal), "platform")
    assert "ruht bis" in text
    assert "https://x/67" in text


# ── KONZ-054 E2: Infra-Befunde im Gate, Entscheidungsfrist, Belege, JSON ─────


def test_should_flag_infra_finding_even_in_own_repo(journal: Path) -> None:
    """Der Anlass: 7 von 17 offenen Befunden waren platform-eigene Infra-Befunde
    und fielen durch die Eigen-Repo-Ausnahme."""
    _lauf(["0.7.18 speicher\tWARN\tplatform\tprod Swap 99,8 %"], journal)
    offen = bj._cross_repo_offen(bj.lade(journal), "platform")
    assert [fid for fid, _ in offen] == ["0.7.18 speicher::platform"]


def test_should_still_exempt_local_conditions_in_own_repo(journal: Path) -> None:
    _lauf(["0.4 repo-sync\tWARN\tplatform\tGUARD(dirty)"], journal)
    assert bj._cross_repo_offen(bj.lade(journal), "platform") == []


def test_should_give_every_new_finding_a_decision_deadline(journal: Path) -> None:
    _, daten = _lauf([ZEILE], journal)
    e = next(iter(daten["befunde"].values()))
    assert e["entscheiden_bis"] > e["erstmals"]


def test_should_not_silence_a_new_finding_because_of_its_deadline(
    journal: Path,
) -> None:
    """entscheiden_bis ist KEINE Ruhefrist — sonst waere jeder neue Befund stumm."""
    _, daten = _lauf([ZEILE], journal)
    e = next(iter(daten["befunde"].values()))
    assert bj.ruhezustand(e, bj._heute()) == "laut"


def test_should_mark_finding_overdue_after_the_deadline_without_decision(
    journal: Path,
) -> None:
    _, daten = _lauf([ZEILE], journal)
    fid, e = next(iter(daten["befunde"].items()))
    assert not bj.ueberfaellig(e, e["entscheiden_bis"])
    assert bj.ueberfaellig(e, "2099-01-01")
    e["artefakt"] = "https://example/issue/1"
    assert not bj.ueberfaellig(e, "2099-01-01")


def test_should_backfill_deadline_for_legacy_entries_on_next_run(journal: Path) -> None:
    _, daten = _lauf([ZEILE], journal)
    e = next(iter(daten["befunde"].values()))
    del e["entscheiden_bis"]
    bj.sichere(daten, journal)
    _, daten = _lauf([ZEILE], journal)
    assert next(iter(daten["befunde"].values())).get("entscheiden_bis")


def test_should_store_evidence_columns_from_the_runner(journal: Path) -> None:
    zeile = "0.7.18 speicher\tWARN\tplatform\tSwap voll\t\tprod\tfree -m\t4087/4095 MB\tfree -m auf prod-b -> 0/0"
    _, daten = _lauf([zeile], journal)
    e = daten["befunde"]["0.7.18 speicher::platform"]
    assert e["knoten"] == "prod"
    assert e["kommando"] == "free -m"
    assert e["ausgabe"] == "4087/4095 MB"
    assert e["positivkontrolle"].startswith("free -m auf prod-b")


def test_should_attach_evidence_later_via_cli(journal: Path, capsys) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    rc = bj.main(
        [
            "--beleg",
            fid,
            "--knoten",
            "prod",
            "--kommando",
            "df -h /",
            "--datei",
            str(journal),
        ]
    )
    assert rc == 0
    e = bj.lade(journal)["befunde"][fid]
    assert (e["knoten"], e["kommando"]) == ("prod", "df -h /")


def test_should_refuse_beleg_without_any_field(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    assert bj.main(["--beleg", fid, "--datei", str(journal)]) == 2


def test_should_emit_complete_json_for_a_reading_surface(journal: Path, capsys) -> None:
    _lauf(["0.7.18 speicher\tWARN\tplatform\tSwap voll\t\tprod\tfree -m"], journal)
    assert (
        bj.main(["--bericht", "--json", "--repo", "platform", "--datei", str(journal)])
        == 0
    )
    saetze = json.loads(capsys.readouterr().out)
    assert len(saetze) == 1
    s = saetze[0]
    assert s["infra"] is True and s["im_gate"] is True and s["ueberfaellig"] is False
    assert s["kommando"] == "free -m" and s["knoten"] == "prod"
    assert set(bj.BELEG_FELDER) <= set(s)


def test_should_show_missing_evidence_in_the_text_report(journal: Path) -> None:
    _lauf([ZEILE], journal)
    text = bj.bericht(bj.lade(journal), "platform")
    assert "ohne Beleg" in text
    assert "entscheiden bis" in text


def test_should_reject_unknown_id_for_echt_and_falsch(journal: Path, capsys) -> None:
    """#2863: eine erfundene ID darf kein Urteil unter einem Phantom-Schluessel anlegen."""
    _lauf([ZEILE], journal)
    vor = journal.read_bytes()
    rc = bj.main(["--echt", "phantom::nirgendwo", "Notiz", "--datei", str(journal)])
    assert rc == 2
    assert "Kein Befund mit ID" in capsys.readouterr().err
    assert journal.read_bytes() == vor


def test_should_complete_id_without_phase_prefix(journal: Path, capsys) -> None:
    """Der Runner druckt `0.7 deploy-scan::x` — der Praefix ist Teil des Schluessels,
    aber eine ID ohne ihn darf treffen, wenn GENAU ein Befund passt."""
    _lauf(["0.7 deploy-scan\tWARN\tx\tfailure"], journal)
    rc = bj.main(["--echt", "deploy-scan::x", "Notiz", "--datei", str(journal)])
    assert rc == 0
    fehler = capsys.readouterr().err
    assert "vervollständigt" in fehler
    daten = bj.lade(journal)
    assert daten["urteile"][0]["fid"] == "0.7 deploy-scan::x"
    assert daten["befunde"]["0.7 deploy-scan::x"]["urteil"] == "echt"


def test_should_accept_id_known_only_from_urteile_history(journal: Path) -> None:
    """Ein geheilter (nicht mehr gemeldeter) Befund bleibt urteilbar, wenn er
    schon einmal beurteilt wurde — das macht die ID bekannt, kein Phantom."""
    fid = "0.7 deploy-scan::x"
    _lauf(["0.7 deploy-scan\tWARN\tx\tfailure"], journal)
    bj.main(["--echt", fid, "erste Notiz", "--datei", str(journal)])
    _lauf(["0.7 deploy-scan\tPASS\tplatform\talles gruen"], journal)  # heilt x
    daten = bj.lade(journal)
    assert fid not in daten["befunde"]
    rc = bj.main(["--falsch", fid, "zweite Notiz", "--datei", str(journal)])
    assert rc == 0
    daten = bj.lade(journal)
    assert daten["urteile"][-1] == {
        "fid": fid,
        "phase": "0.7 deploy-scan",
        "repo": "x",
        "urteil": "falsch",
        # Der Befund ist geheilt und steht nicht mehr in `befunde` — sein
        # Meldetext ist damit weg. `eingabe` sagt das ehrlich als None, statt
        # ersatzweise den `grund` einzusetzen. Folge fuers Lernen: ein Urteil,
        # das erst NACH der Heilung faellt, taugt nicht als Beispiel (#3337).
        "eingabe": None,
        "grund": "zweite Notiz",
        "datum": daten["urteile"][-1]["datum"],
    }


def test_should_print_concrete_ids_in_offen_cross_repo_hint(
    journal: Path, capsys
) -> None:
    """Die Hilfe druckt den vollen Schluessel, nicht `<ID>` — sonst trifft der
    naechste `--echt`-Aufruf ohne Praefix ins Leere."""
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    rc = bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
    assert rc == 1
    ausgabe = capsys.readouterr().out
    assert "--echt '0.7 deploy-scan::cad-hub'" in ausgabe
    assert "--verankert '0.7 deploy-scan::cad-hub'" in ausgabe


# --- praezision() mit geschaerft_am (#2895, Folge-PR zu #2890) --------------


def _urteil(phase: str, urteil: str, datum: str) -> dict:
    return {
        "fid": f"{phase}::x",
        "phase": phase,
        "repo": "x",
        "urteil": urteil,
        "grund": "Testfixture",
        "datum": datum,
    }


def _register_mit_nullstellung(phase: str, geschaerft_am: str) -> list[dict]:
    return [{"phase": phase, "geschaerft_am": geschaerft_am}]


def test_should_ignore_urteile_before_geschaerft_am() -> None:
    """Urteile VOR der Nullstellung zaehlen nicht mehr in die Trefferquote —
    genau der Fall aus #2895: PR #2890 hat den Melder geschaerft, die alten
    Fehlalarme sollen die Quote nicht laenger drosseln."""
    daten = {
        "urteile": [
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-08-20"),
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-09-04"),
            _urteil("0.7.4 prio-referenzen", "echt", "2026-09-05"),
            _urteil("0.7.4 prio-referenzen", "echt", "2026-09-08"),
        ]
    }
    register = _register_mit_nullstellung("0.7.4 prio-referenzen", "2026-09-07")
    zeilen = bj.praezision(daten, register)
    z = zeilen[0]
    assert z["urteile"] == 1
    assert z["echt"] == 1
    assert z["falsch"] == 0
    assert z["geschaerft_am"] == "2026-09-07"


def test_should_leave_phases_without_geschaerft_am_unchanged() -> None:
    """Ohne das Feld zaehlt weiterhin jedes Urteil — kein Verhaltensbruch fuer
    die anderen Melder-Phasen ohne Nullstellung."""
    daten = {
        "urteile": [
            _urteil("0.7 deploy-scan", "echt", "2026-01-01"),
            _urteil("0.7 deploy-scan", "falsch", "2026-01-02"),
        ]
    }
    zeilen = bj.praezision(daten, register=[])
    z = zeilen[0]
    assert z["urteile"] == 2
    assert z["echt"] == 1
    assert z["falsch"] == 1
    assert z["geschaerft_am"] is None


def test_should_mark_nullstellung_as_not_bewertbar_without_new_urteile() -> None:
    """Ein geschaerfter Melder mit 0 Urteilen SEIT der Nullstellung ist NICHT
    bewertbar — Regel MIN_URTEILE gilt unveraendert, also kein WARN, sondern
    sichtbar '0 Urteile seit ...' statt spurlosem Verschwinden."""
    daten = {
        "urteile": [
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-08-20"),
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-09-02"),
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-09-04"),
        ]
    }
    register = _register_mit_nullstellung("0.7.4 prio-referenzen", "2026-09-07")
    zeilen = bj.praezision(daten, register)
    z = zeilen[0]
    assert z["urteile"] == 0
    assert z["bewertbar"] is False
    assert z["praezision"] is None
    bericht = bj.praezisions_bericht(daten, register)
    assert "(seit 2026-09-07, 0 Urteile)" in bericht
    assert "NICHT bewertbar" in bericht
    assert "🚨" not in bericht


def test_should_still_warn_on_three_false_judgements_after_geschaerft_am() -> None:
    """Positivkontrolle: schaerft das Feld die Quote nicht kuenstlich weich,
    bleiben drei Fehlalarme NACH der Nullstellung weiterhin WARN-wuerdig."""
    daten = {
        "urteile": [
            _urteil(
                "0.7.4 prio-referenzen", "echt", "2026-08-20"
            ),  # vor Nullstellung, zaehlt nicht
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-09-07"),
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-09-08"),
            _urteil("0.7.4 prio-referenzen", "falsch", "2026-09-09"),
        ]
    }
    register = _register_mit_nullstellung("0.7.4 prio-referenzen", "2026-09-07")
    zeilen = bj.praezision(daten, register)
    z = zeilen[0]
    assert z["urteile"] == 3
    assert z["bewertbar"] is True
    assert z["praezision"] == 0.0
    bericht = bj.praezisions_bericht(daten, register)
    assert "🚨" in bericht
    assert "(seit 2026-09-07, 3 Urteile)" in bericht


# ── Urteil haelt den beurteilten Text fest (#3337) ──────────────────────────


def test_should_store_the_judged_note_as_eingabe() -> None:
    """Ein Urteil ohne seinen Meldetext ist ein Etikett ohne Gegenstand.

    Befund aus Stufe 0 zu #3337: 51 Urteile lagen vor, aber kein einziger der
    beurteilten Meldetexte — als Lerndaten damit wertlos.
    """
    daten = {
        "befunde": {
            "0.7 deploy-scan::travel-beat": {
                "phase": "0.7 deploy-scan",
                "repo": "travel-beat",
                "letzte_note": "failure:travel-beat — Deploy rot seit 12.07.",
            }
        }
    }

    bj.urteile_dazu(daten, "0.7 deploy-scan::travel-beat", "echt", "war real rot")

    urteil = daten["urteile"][-1]
    assert urteil["eingabe"] == "failure:travel-beat — Deploy rot seit 12.07."
    assert urteil["grund"] == "war real rot"


def test_should_keep_eingabe_separate_from_grund() -> None:
    """`grund` entsteht nach dem Urteil und nennt es mit — er darf die Eingabe
    nicht ersetzen, sonst verraet der Lerndatensatz seine eigene Antwort."""
    daten = {
        "befunde": {
            "0.7.4 prio-referenzen::platform": {
                "phase": "0.7.4 prio-referenzen",
                "repo": "platform",
                "letzte_note": "2 Prio-Referenz(en) zeigen auf Erledigtes",
            }
        }
    }

    bj.urteile_dazu(
        daten,
        "0.7.4 prio-referenzen::platform",
        "falsch",
        "Zitiert einen gemergten PR als historischen Kontext",
    )

    urteil = daten["urteile"][-1]
    assert urteil["eingabe"] != urteil["grund"]
    assert "gemergten PR" not in urteil["eingabe"]


def test_should_record_eingabe_as_none_when_befund_is_unknown() -> None:
    """Urteil zu einem Befund, den das Journal nicht (mehr) kennt: kein Text,
    aber auch kein Absturz — und `eingabe` sagt ehrlich None statt zu raten."""
    daten: dict = {}

    bj.urteile_dazu(daten, "0.9 staging::mcp-hub", "echt", "nachgetragen")

    assert daten["urteile"][-1]["eingabe"] is None


# ── #3495 V4: Fix in Arbeit — laufende Reparatur je Befund ──────────────────


def test_should_set_fix_in_arbeit_via_cli(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    rc = bj.main(
        [
            "--fix",
            fid,
            "--pr",
            "https://github.com/achimdehnert/platform/pull/3479",
            "--wirkung",
            "Reconcile meldet nicht mehr faelschlich C0",
            "--messung",
            "2026-09-26",
            "--datei",
            str(journal),
        ]
    )
    assert rc == 0
    e = bj.lade(journal)["befunde"][fid]
    assert e["fix"]["pr"] == "https://github.com/achimdehnert/platform/pull/3479"
    assert e["fix"]["wirkung"] == "Reconcile meldet nicht mehr faelschlich C0"
    assert e["fix"]["messung"] == "2026-09-26"
    assert e["fix"]["gesetzt_am"] == bj._heute()


def test_should_default_the_measurement_date_when_missing(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    bj.main(
        [
            "--fix",
            fid,
            "--pr",
            "https://github.com/achimdehnert/platform/pull/1",
            "--wirkung",
            "Behebt X",
            "--datei",
            str(journal),
        ]
    )
    e = bj.lade(journal)["befunde"][fid]
    assert e["fix"]["messung"] == bj._frist(bj.FRIST_FIX_MESSUNG_TAGE)


def _fix_args(fid: str, pr: str, journal: Path) -> list[str]:
    return [
        "--fix",
        fid,
        "--pr",
        pr,
        "--wirkung",
        "erste Wirkung",
        "--messung",
        "2026-09-26",
        "--datei",
        str(journal),
    ]


def test_should_overwrite_fix_in_arbeit_idempotently(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    bj.main(_fix_args(fid, "https://example/pull/1", journal))
    bj.main(_fix_args(fid, "https://example/pull/2", journal))
    e = bj.lade(journal)["befunde"][fid]
    assert e["fix"]["pr"] == "https://example/pull/2"


def test_should_reject_fix_for_unknown_key(journal: Path, capsys) -> None:
    _lauf([ZEILE], journal)
    rc = bj.main(
        [
            "--fix",
            "phantom::nirgendwo",
            "--pr",
            "https://example/pull/1",
            "--wirkung",
            "irrelevant",
            "--datei",
            str(journal),
        ]
    )
    assert rc != 0
    assert "phantom::nirgendwo" not in bj.lade(journal)["befunde"]
    assert "Kein Befund" in capsys.readouterr().err


def test_should_reject_fix_without_wirkung(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    rc = bj.main(
        ["--fix", fid, "--pr", "https://example/pull/1", "--datei", str(journal)]
    )
    assert rc != 0
    assert "fix" not in bj.lade(journal)["befunde"][fid]


def test_should_show_fix_in_arbeit_line_in_report(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    bj.main(
        [
            "--fix",
            fid,
            "--pr",
            "https://example/pull/1",
            "--wirkung",
            "behebt den Melder",
            "--messung",
            "2099-01-01",
            "--datei",
            str(journal),
        ]
    )
    text = bj.bericht(bj.lade(journal), "platform")
    assert "🔧 Fix in Arbeit: https://example/pull/1 — behebt den Melder" in text
    assert "Messung 2099-01-01" in text
    assert "überfällig" not in text


def test_should_flag_fix_measurement_as_overdue(journal: Path) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    bj.main(
        [
            "--fix",
            fid,
            "--pr",
            "https://example/pull/1",
            "--wirkung",
            "behebt den Melder",
            "--messung",
            "2000-01-01",
            "--datei",
            str(journal),
        ]
    )
    e = bj.lade(journal)["befunde"][fid]
    assert bj.fix_ueberfaellig(e, bj._heute()) is True
    text = bj.bericht(bj.lade(journal), "platform")
    assert "⏰ Fix-Messung überfällig" in text


def test_should_not_flag_fix_measurement_without_a_fix(journal: Path) -> None:
    assert bj.fix_ueberfaellig({"letzte_note": "x"}, bj._heute()) is False


def test_should_include_fix_in_json_report(journal: Path, capsys) -> None:
    _lauf([ZEILE], journal)
    fid = next(iter(bj.lade(journal)["befunde"]))
    bj.main(
        [
            "--fix",
            fid,
            "--pr",
            "https://example/pull/1",
            "--wirkung",
            "behebt den Melder",
            "--messung",
            "2000-01-01",
            "--datei",
            str(journal),
        ]
    )
    capsys.readouterr()  # Ausgabe des --fix-Aufrufs verwerfen, nur der Bericht zaehlt.
    bj.main(["--bericht", "--json", "--repo", "platform", "--datei", str(journal)])
    saetze = json.loads(capsys.readouterr().out)
    satz = next(s for s in saetze if s["id"] == fid)
    assert satz["fix"]["pr"] == "https://example/pull/1"
    assert satz["fix_ueberfaellig"] is True


# ── Deklarationen mit Pflicht-Ablauf (#3495 V2) ──────────────────────────────


@pytest.fixture
def dekl(tmp_path: Path) -> Path:
    """Nie die echte governance/deklarationen.json."""
    return tmp_path / "deklarationen.json"


def _dekl_cli(dekl: Path, *args: str) -> int:
    return bj.main([*args, "--deklarationen", str(dekl)])


def test_should_set_and_read_declaration(dekl, capsys):
    rc = _dekl_cli(
        dekl,
        "--deklaration",
        "gpu-box",
        "--art",
        "auf_zuruf",
        "--grund",
        "Owner-Entscheid",
        "--gueltig-bis",
        "2099-12-31",
    )
    assert rc == 0
    assert "Deklaration gesetzt: gpu-box [auf_zuruf]" in capsys.readouterr().out
    treffer = bj.deklarationen_fuer("gpu-box", "2026-09-24", art="auf_zuruf", pfad=dekl)
    assert [d["gueltig_bis"] for d in treffer] == ["2099-12-31"]
    assert (
        bj.deklarationen_fuer("gpu-box", "2026-09-24", art="stundung", pfad=dekl) == []
    )
    assert bj.deklarationen_fuer("gx10", "2026-09-24", pfad=dekl) == []


def test_should_replace_declaration_with_same_target_and_kind(dekl):
    bj.setze_deklaration("gpu-box", "auf_zuruf", "alt", "2099-01-01", pfad=dekl)
    bj.setze_deklaration("gpu-box", "auf_zuruf", "neu", "2099-06-30", pfad=dekl)
    alle = bj.lade_deklarationen(dekl)
    assert [(d["grund"], d["gueltig_bis"]) for d in alle] == [("neu", "2099-06-30")]


def test_should_refuse_declaration_without_expiry(dekl, capsys):
    rc = _dekl_cli(
        dekl, "--deklaration", "gpu-box", "--art", "auf_zuruf", "--grund", "x"
    )
    assert rc == 2
    assert "--gueltig-bis" in capsys.readouterr().err
    assert not dekl.exists()
    with pytest.raises(ValueError, match="gueltig_bis fehlt"):
        bj.setze_deklaration("gpu-box", "auf_zuruf", "x", "", pfad=dekl)


def test_should_refuse_declaration_with_past_expiry_on_cli(dekl, capsys):
    rc = _dekl_cli(
        dekl,
        "--deklaration",
        "gpu-box",
        "--art",
        "auf_zuruf",
        "--grund",
        "x",
        "--gueltig-bis",
        "2000-01-01",
    )
    assert rc == 2
    assert "Vergangenheit" in capsys.readouterr().err


def test_should_ignore_hand_written_declaration_without_expiry(dekl):
    """Ein Eintrag ohne `gueltig_bis` (von Hand ins JSON geschrieben) wirkt nie."""
    dekl.write_text(
        json.dumps(
            {"deklarationen": [{"ziel": "gpu-box", "art": "auf_zuruf", "grund": "x"}]}
        ),
        encoding="utf-8",
    )
    assert bj.deklarationen_fuer("gpu-box", "2026-09-24", pfad=dekl) == []
    zeilen = bj.deklarations_zeilen(bj.lade_deklarationen(dekl), "2026-09-24")
    assert any("ungueltig (gueltig_bis fehlt" in z for z in zeilen)


def test_should_expire_declaration_the_day_after_gueltig_bis(dekl):
    """Positivkontrolle: am Tag `gueltig_bis` wirkt sie, am Tag danach nicht."""
    bj.setze_deklaration("gpu-box", "auf_zuruf", "x", "2026-09-23", pfad=dekl)
    assert bj.deklarationen_fuer("gpu-box", "2026-09-23", pfad=dekl)
    assert bj.deklarationen_fuer("gpu-box", "2026-09-24", pfad=dekl) == []


def test_should_show_active_sum_and_expired_lines_in_report(dekl, journal, capsys):
    bj.setze_deklaration("gpu-box", "auf_zuruf", "x", "2099-12-31", pfad=dekl)
    bj.setze_deklaration("svc-a", "stundung", "y", "2099-03-01", pfad=dekl)
    bj.setze_deklaration("gx10", "auf_zuruf", "z", "2000-01-01", pfad=dekl)
    bj.main(["--bericht", "--datei", str(journal), "--deklarationen", str(dekl)])
    out = capsys.readouterr().out
    assert "Journal leer" in out
    assert "2 Deklaration(en) aktiv, nächste Fälligkeit 2099-03-01" in out
    assert "⏰ Deklaration abgelaufen: gx10 [auf_zuruf] gueltig bis 2000-01-01" in out


def test_should_leave_report_json_format_unchanged_by_declarations(
    dekl, journal, capsys
):
    """`--bericht --json` bleibt eine Liste von Befunden — der Session-Start-
    Runner und flottenbild.lese_melder lesen genau dieses Format."""
    bj.setze_deklaration("gpu-box", "auf_zuruf", "x", "2099-12-31", pfad=dekl)
    bj.main(
        ["--bericht", "--json", "--datei", str(journal), "--deklarationen", str(dekl)]
    )
    assert json.loads(capsys.readouterr().out) == []


def test_should_not_declare_auf_zuruf_in_hosts_yaml():
    """Eine Quelle: `betrieb: auf_zuruf` in infra/hosts.yaml waere eine zweite,
    ablauflose Deklaration neben governance/deklarationen.json (#3495 V2)."""
    import yaml  # noqa: PLC0415

    wurzel = Path(__file__).resolve().parents[2]
    hosts = yaml.safe_load((wurzel / "infra/hosts.yaml").read_text(encoding="utf-8"))
    mit_feld = sorted(
        name
        for name, h in (hosts.get("hosts") or {}).items()
        if isinstance(h, dict) and h.get("betrieb") == "auf_zuruf"
    )
    assert mit_feld == [], f"auf_zuruf gehoert in die Deklaration: {mit_feld}"


def test_should_keep_every_real_declaration_valid():
    """Jede Deklaration im Repo hat Art, Ziel, Grund und `gueltig_bis`."""
    alle = bj.lade_deklarationen(
        Path(__file__).resolve().parents[2] / bj.DEKLARATIONEN_REL
    )
    fehler = [(d.get("ziel"), bj.deklarations_fehler(d)) for d in alle]
    assert [f for f in fehler if f[1]] == []


# ── V2-Rest (#3507): Verzicht ueber deklarationen_fuer, verankert_am, --gilt ──

_WURZEL = Path(__file__).resolve().parents[2]
_FID = "0.7 deploy-scan::cad-hub"


def _gestern() -> str:
    from datetime import date, timedelta  # noqa: PLC0415

    return (date.fromisoformat(bj._heute()) - timedelta(days=1)).isoformat()


def _verzichtet(journal: Path, dekl: Path) -> dict:
    _lauf(["0.7 deploy-scan\tWARN\tcad-hub\tfailure"], journal)
    assert (
        bj.main(
            [
                "--verzichtet",
                _FID,
                "Repo ist eingefroren",
                "--datei",
                str(journal),
                "--deklarationen",
                str(dekl),
            ]
        )
        == 0
    )
    return bj.lade(journal)


def test_should_read_journal_waiver_through_deklarationen_fuer(journal, dekl):
    daten = _verzichtet(journal, dekl)
    treffer = bj.deklarationen_fuer(_FID, art="verzicht", pfad=dekl, journal=daten)
    assert [d["grund"] for d in treffer] == ["Repo ist eingefroren"]
    assert treffer[0]["gueltig_bis"] == daten["befunde"][_FID]["wiedervorlage"]
    # Ohne Journal nur die Repo-Datei — dort steht kein Verzicht.
    assert bj.deklarationen_fuer(_FID, art="verzicht", pfad=dekl) == []


def test_should_bring_finding_back_into_gate_when_waiver_expired_yesterday(
    journal, dekl, monkeypatch, capsys
):
    """Positivkontrolle #3507: Verzicht-Ablauf einen Tag zurueck -> wirkungslos.

    Bis #3507 zaehlte ein Verzicht im Gate unbefristet, auch nach seiner
    Wiedervorlage."""
    monkeypatch.setenv("BEFUND_DEKLARATIONEN_DATEI", str(dekl))
    daten = _verzichtet(journal, dekl)
    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 0
    )
    daten["befunde"][_FID]["wiedervorlage"] = _gestern()
    bj.sichere(daten, journal)
    capsys.readouterr()

    assert (
        bj.main(["--offen-cross-repo", "--repo", "platform", "--datei", str(journal)])
        == 1
    )
    assert not bj.verzicht_gilt(daten["befunde"][_FID])
    bj.main(["--bericht", "--datei", str(journal), "--deklarationen", str(dekl)])
    out = capsys.readouterr().out
    assert f"⏰ Deklaration abgelaufen: {_FID} [verzicht]" in out
    assert "Verlaengern: --verzichtet" in out


def test_should_set_verankert_am_on_every_decision(journal, dekl, capsys):
    _lauf(
        [
            "0.7 deploy-scan\tWARN\tcad-hub\tfailure",
            "0.7 deploy-scan\tWARN\ttax-hub\tfailure",
            "0.7 deploy-scan\tWARN\tapo-hub\tfailure",
        ],
        journal,
    )
    d = ["--datei", str(journal)]
    assert bj.main(["--verankert", _FID, "https://example/issues/1", *d]) == 0
    assert bj.main(["--verzichtet", "0.7 deploy-scan::tax-hub", "Grund", *d]) == 0
    assert bj.main(["--falsch", "0.7 deploy-scan::apo-hub", "Fehlalarm", *d]) == 0
    capsys.readouterr()
    bj.main(["--bericht", "--json", *d, "--deklarationen", str(dekl)])
    saetze = {s["id"]: s for s in json.loads(capsys.readouterr().out)}
    heute = bj._heute()
    assert {fid: s["verankert_am"] for fid, s in saetze.items()} == {
        _FID: heute,
        "0.7 deploy-scan::tax-hub": heute,
        "0.7 deploy-scan::apo-hub": heute,
    }
    assert saetze["0.7 deploy-scan::tax-hub"]["verzicht_gilt"] is True
    assert saetze[_FID]["verzicht_gilt"] is False


def test_should_answer_gilt_with_exit_code(dekl, capsys):
    bj.setze_deklaration("gpu-box", "auf_zuruf", "x", "2099-12-31", pfad=dekl)
    bj.setze_deklaration("gx10", "auf_zuruf", "x", _gestern(), pfad=dekl)
    gilt = ["--art", "auf_zuruf", "--deklarationen", str(dekl)]
    assert bj.main(["--gilt", "gpu-box", *gilt]) == 0
    assert bj.main(["--gilt", "gx10", *gilt]) == 1, "abgelaufen wirkt nicht"
    assert bj.main(["--gilt", "odoo", *gilt]) == 1
    assert "keine gueltige Deklaration fuer odoo" in capsys.readouterr().out


def test_should_declare_every_real_betriebsstatus_exception_with_expiry():
    """Eine Ausnahme ohne Deklaration ist seit #3507 wirkungslos — der Melder
    meldet den Dienst. Diese Invariante faengt das VOR dem Merge ab (Schema, nicht
    Datum: ein faelliger Ablauf soll im Melder hochkommen, nicht im CI)."""
    import yaml  # noqa: PLC0415

    ports = yaml.safe_load((_WURZEL / "infra/ports.yaml").read_text(encoding="utf-8"))
    ausnahmen = sorted(
        name
        for name, v in (ports.get("services") or {}).items()
        if isinstance(v, dict) and v.get("betriebsstatus", "aktiv") != "aktiv"
    )
    deklariert = {
        d["ziel"]
        for d in bj.lade_deklarationen(_WURZEL / bj.DEKLARATIONEN_REL)
        if d.get("art") == "betriebsstatus" and bj.deklarations_fehler(d) is None
    }
    assert ausnahmen, "Fixture-Sanity: ports.yaml fuehrt Ausnahmen"
    assert [n for n in ausnahmen if n not in deklariert] == []


def test_should_keep_stundungen_in_one_place():
    """Die Stundungen der Registry-Live-Drift stehen seit #3507 nur noch in
    governance/deklarationen.json — die alte YAML darf nicht nachwachsen."""
    assert not (_WURZEL / "infra/reconcile-baseline.yaml").exists()
    stundungen = [
        d
        for d in bj.lade_deklarationen(_WURZEL / bj.DEKLARATIONEN_REL)
        if d.get("art") == "stundung"
    ]
    assert stundungen, "Migration aus reconcile-baseline.yaml fehlt"
