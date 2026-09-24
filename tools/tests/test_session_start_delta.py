"""Tests fuer tools/session_start_delta.py — WARN-Zeilen gegen das Befund-Journal (#3495 V3).

Kriterium 3: WARN nur bei neuem Schluessel, geaendertem Zustand, abgelaufenem Anker
oder Wiedervorlage; der Rest als Summenzeile. Kriterium 5 (Auflage): ein
[INFRA]-Anker ruht hoechstens ``INFRA_RUHE_MAX_TAGE`` — Positivkontrolle ist der
Backup-Befund aus #3486, der 17 Naechte hinter seinem Anker schlief.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import session_start_delta as sd  # noqa: E402

_TOOLS = Path(__file__).resolve().parents[1]
_FIXTURE = _TOOLS / "tests" / "fixtures" / "session_start_delta_2026-09-24.json"
HEUTE = "2026-09-24"


def _eintrag(**felder) -> dict:
    basis = {
        "id": "0.7.9 beispiel::platform",
        "phase": "0.7.9 beispiel",
        "repo": "platform",
        "infra": False,
        "erstmals": "2026-09-20",
        "note": "3 Repos hinterher: a-hub, b-hub",
        "artefakt": "https://github.com/achimdehnert/platform/issues/1",
        "verzicht": None,
        "wiedervorlage": "2026-10-01",
        "urteil": None,
        "fix": None,
        "fix_ueberfaellig": False,
        "entscheiden_bis": "2026-09-27",
    }
    basis.update(felder)
    return basis


def _zeile(note: str = "3 Repos hinterher: a-hub, b-hub", repos=("platform",)) -> dict:
    return {
        "phase": "0.7.9 beispiel",
        "status": "WARN",
        "repos": list(repos),
        "note": note,
    }


def _klasse(eintrag: dict | None, zeile: dict | None = None, zustand=None) -> dict:
    ergebnis, _ = sd.delta(
        [zeile or _zeile()], [eintrag] if eintrag else [], HEUTE, zustand
    )
    return ergebnis[0]


def test_should_classify_unknown_key_as_neu():
    assert _klasse(None)["klasse"] == sd.NEU


def test_should_classify_changed_note_form_as_geaendert():
    z = _zeile(note="3 Repos hinterher: a-hub, c-hub")
    assert _klasse(_eintrag(), z)["klasse"] == sd.GEAENDERT


def test_should_not_flag_a_note_whose_only_change_is_a_counter():
    z = _zeile(note="5 Repos hinterher: a-hub, b-hub")
    assert _klasse(_eintrag(), z)["klasse"] == sd.VERANKERT


def test_should_classify_entry_without_anchor_as_ohne_anker():
    e = _eintrag(artefakt=None, wiedervorlage=None)
    k = _klasse(e)
    assert k["klasse"] == sd.OHNE_ANKER
    assert "2026-09-27" in k["grund"]


def test_should_treat_falsch_verdict_as_a_decision():
    e = _eintrag(artefakt=None, urteil="falsch")
    assert _klasse(e)["klasse"] == sd.VERANKERT


def test_should_classify_expired_wiedervorlage_as_anker_abgelaufen():
    e = _eintrag(wiedervorlage="2026-09-20")
    assert _klasse(e)["klasse"] == sd.ANKER_ABGELAUFEN


def test_should_classify_overdue_fix_measurement():
    e = _eintrag(
        fix={"gesetzt_am": "2026-09-10", "messung": "2026-09-17"}, fix_ueberfaellig=True
    )
    assert _klasse(e)["klasse"] == sd.FIX_UEBERFAELLIG


def test_should_keep_anchored_entry_quiet_and_report_its_due_date():
    e = _eintrag(fix={"gesetzt_am": "2026-09-20", "messung": "2026-09-28"})
    k = _klasse(e)
    assert k["klasse"] == sd.VERANKERT
    assert k["faellig"] == "2026-09-28"


def test_should_resubmit_infra_backup_finding_anchored_for_17_days():
    """Positivkontrolle #3486: Backup-Befund, seit 17 Tagen verankert, ohne Zustand."""
    e = _eintrag(
        id="0.7.17 backup-deckung::platform",
        phase="0.7.17 backup-deckung",
        infra=True,
        erstmals="2026-09-07",
        wiedervorlage="2026-10-10",
        note="Deckung NICHT messbar",
    )
    z = {**_zeile(note="Deckung NICHT messbar"), "phase": "0.7.17 backup-deckung"}
    k = _klasse(e, z)
    assert k["klasse"] == sd.WIEDERVORLAGE
    assert "2026-09-07" in k["grund"]


def test_should_resubmit_infra_finding_when_stored_rest_exceeds_limit():
    e = _eintrag(infra=True, erstmals="2026-09-01")
    zustand = {"anker": {e["id"]: {"signatur": sd._signatur(e), "seit": "2026-09-07"}}}
    assert _klasse(e, zustand=zustand)["klasse"] == sd.WIEDERVORLAGE


def test_should_keep_infra_finding_quiet_within_rest_limit():
    e = _eintrag(infra=True, erstmals="2026-09-01")
    zustand = {"anker": {e["id"]: {"signatur": sd._signatur(e), "seit": "2026-09-20"}}}
    k = _klasse(e, zustand=zustand)
    assert k["klasse"] == sd.VERANKERT
    assert k["faellig"] == "2026-09-27"


def test_should_restart_infra_rest_when_anchor_is_renewed():
    e = _eintrag(infra=True, erstmals="2026-09-01")
    zustand = {"anker": {e["id"]: {"signatur": "alt", "seit": "2026-09-01"}}}
    ergebnis, neu = sd.delta([_zeile()], [e], HEUTE, zustand)
    assert ergebnis[0]["klasse"] == sd.VERANKERT
    assert neu["anker"][e["id"]]["seit"] == HEUTE


def test_should_let_the_loudest_repo_decide_a_multi_repo_row():
    ruhig = _eintrag()
    neu_repo = _zeile(repos=("platform", "x-hub"))
    assert _klasse(ruhig, neu_repo)["klasse"] == sd.NEU


def test_should_leave_non_warn_rows_unclassified():
    zeilen = [{"phase": "0.1", "status": "PASS", "repos": ["platform"], "note": "ok"}]
    ergebnis, _ = sd.delta(zeilen, [], HEUTE)
    assert ergebnis[0]["klasse"] == ""


def test_should_sum_anchored_rows_with_next_due_date():
    zeilen = [_zeile(), {**_zeile(), "phase": "0.7.8 zwei"}]
    journal = [
        _eintrag(wiedervorlage="2026-10-03"),
        _eintrag(
            id="0.7.8 zwei::platform", phase="0.7.8 zwei", wiedervorlage="2026-09-29"
        ),
    ]
    ergebnis, _ = sd.delta(zeilen, journal, HEUTE)
    assert sd.summenzeile(ergebnis) == "2 verankert (naechste Faelligkeit 2026-09-29)"
    assert "keine neue" in sd.tabelle(ergebnis)


def test_should_reduce_todays_journal_to_at_most_three_new_or_changed_rows():
    """Messpunkt Kriterium 3: Journalstand + Runner-Lauf vom 2026-09-24 (8 WARN-Zeilen)."""
    fx = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    zeilen = [{**z, "repos": z["repo"].split()} for z in fx["zeilen"]]
    ergebnis, _ = sd.delta(zeilen, fx["journal"], fx["heute"], {})
    klassen = [z["klasse"] for z in ergebnis]
    assert len(klassen) == 8
    assert sum(k in (sd.NEU, sd.GEAENDERT) for k in klassen) <= 3
    assert klassen.count(sd.NEU) == 2
    assert klassen.count(sd.ANKER_ABGELAUFEN) == 3
    assert sd.summenzeile(ergebnis) == "3 verankert (naechste Faelligkeit 2026-09-24)"


@pytest.fixture
def cli(tmp_path):
    def laufen(
        tsv: str, journal: list | str
    ) -> tuple[subprocess.CompletedProcess, Path]:
        jpfad = tmp_path / "journal.json"
        jpfad.write_text(journal if isinstance(journal, str) else json.dumps(journal))
        klassen = tmp_path / "klassen.txt"
        r = subprocess.run(
            [
                sys.executable,
                str(_TOOLS / "session_start_delta.py"),
                "--journal",
                str(jpfad),
                "--zustand",
                str(tmp_path / "zustand.json"),
                "--heute",
                HEUTE,
                "--klassen-datei",
                str(klassen),
            ],
            input=tsv,
            capture_output=True,
            text=True,
        )
        return r, klassen

    return laufen


def test_should_write_one_class_line_per_runner_row(cli):
    tsv = "0.1 a\tPASS\tplatform\tok\n0.7.9 beispiel\tWARN\tplatform\tneu hier\n"
    r, klassen = cli(tsv, [])
    assert r.returncode == 0
    assert klassen.read_text().splitlines() == ["", "NEU"]
    assert "| 0.7.9 beispiel | platform | NEU |" in r.stdout
    assert "0 verankert" in r.stdout


def test_should_report_ungeprueft_and_exit_zero_on_unreadable_journal(cli):
    r, klassen = cli("0.7.9 beispiel\tWARN\tplatform\tx\n", "{kaputt")
    assert r.returncode == 0
    assert "UNGEPRUEFT" in r.stdout
    assert not klassen.exists()


def test_should_classify_before_the_journal_records_this_run():
    """Nach ``--aufnehmen`` traegt das Journal schon die Notizen dieses Laufs — zu spaet."""
    text = (_TOOLS / "session_start_checks.sh").read_text(encoding="utf-8")
    delta = text.index('session_start_delta.py" \\')
    assert delta < text.index('echo "| Phase | Status | Repo | Note |"')
    assert delta < text.index('befund_journal.py" --aufnehmen')
    assert 'SESSION_CHECKS_DELTA:-}" = "nur"' in text
