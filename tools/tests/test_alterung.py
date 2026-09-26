"""Tests fuer tools/mail_agent/alterung.py — Ueberfaellige owner-Vorgaenge altern (V6, #3015 K4).

Geprueft wird die EINE Regel: `bucket == owner` UND Frist >= `--tage` (Default 7)
verstrichen UND seit der Frist kein neuer Verlaufseintrag — dann wandert der
Vorgang nach `warten`, sichtbar und umkehrbar. Kein Test fasst den echten
Ledger unter `~/.claude/` an — alle Pfade sind auf tmp_path umgebogen.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

alterung = pytest.importorskip("alterung")
board = pytest.importorskip("board")


def _v(nr, bucket, frist=None, notiz="", **felder):
    grund = {
        "nr": nr,
        "kurz": f"Vorgang {nr}",
        "konto": "hnu",
        "typ": "vorgang",
        "bucket": bucket,
        "frist": frist,
        "notiz": notiz,
    }
    return {**grund, **felder}


def _ledger(*vorgaenge):
    return {"vorgaenge": list(vorgaenge), "naechste_nr": 100}


class TestAltern:
    def test_should_move_a_candidate_seven_days_overdue_without_a_new_entry(self):
        ledger = _ledger(
            _v(
                1,
                "owner",
                frist="2026-09-05",
                notiz="2026-09-01 [ANGELEGT] (Quelle): eroeffnet",
            )
        )
        geaendert = alterung.altern(ledger, date(2026, 9, 12), tage=7)
        assert [v["nr"] for v in geaendert] == [1]
        vorgang = ledger["vorgaenge"][0]
        assert vorgang["bucket"] == "warten"
        assert vorgang["frist"] is None
        assert "2026-09-05" in vorgang["frist_grund"]
        assert vorgang["zustand"] == "ueberfaellig-seit-2026-09-05-owner-wort-offen"
        assert vorgang["notiz"].endswith("Offen: Owner-Wort.")
        assert "2026-09-12 (alterung.py)" in vorgang["notiz"]

    def test_should_not_move_a_candidate_only_six_days_overdue(self):
        ledger = _ledger(_v(2, "owner", frist="2026-09-06", notiz=""))
        geaendert = alterung.altern(ledger, date(2026, 9, 12), tage=7)
        assert geaendert == []
        assert ledger["vorgaenge"][0]["bucket"] == "owner"
        assert ledger["vorgaenge"][0]["frist"] == "2026-09-06"

    def test_should_not_move_when_a_new_entry_came_after_the_deadline(self):
        ledger = _ledger(
            _v(
                3,
                "owner",
                frist="2026-09-01",
                notiz=(
                    "2026-08-20 [ANGELEGT] (Quelle): eroeffnet | "
                    "2026-09-10 [NACHFASS] (Owner): noch dran"
                ),
            )
        )
        geaendert = alterung.altern(ledger, date(2026, 9, 12), tage=7)
        assert geaendert == []
        assert ledger["vorgaenge"][0]["bucket"] == "owner"

    def test_should_leave_waiting_and_done_buckets_untouched(self):
        ledger = _ledger(
            _v(4, "warten", frist="2026-09-01", notiz=""),
            _v(5, "erledigt", frist="2026-09-01", notiz=""),
        )
        geaendert = alterung.altern(ledger, date(2026, 9, 12), tage=7)
        assert geaendert == []
        assert ledger["vorgaenge"][0]["bucket"] == "warten"
        assert ledger["vorgaenge"][1]["bucket"] == "erledigt"

    def test_should_be_idempotent_on_a_second_run(self):
        ledger = _ledger(_v(6, "owner", frist="2026-09-01", notiz=""))
        erster = alterung.altern(ledger, date(2026, 9, 12), tage=7)
        vorher = json.dumps(ledger, sort_keys=True)
        zweiter = alterung.altern(ledger, date(2026, 9, 12), tage=7)
        assert len(erster) == 1
        assert zweiter == []
        assert json.dumps(ledger, sort_keys=True) == vorher

    def test_should_report_no_violation_after_aging_because_frist_grund_is_set(self):
        ledger = _ledger(_v(7, "owner", frist="2026-09-01", notiz=""))
        alterung.altern(ledger, date(2026, 9, 12), tage=7)
        befunde = board.pruefe_fristen(board.vorgaenge_von(ledger))
        assert befunde == []


class TestZurueck:
    def test_should_reactivate_an_aged_vorgang_via_cli(self, tmp_path):
        ledger_pfad = tmp_path / "ledger.json"
        ledger = _ledger(_v(8, "owner", frist="2026-09-01", notiz=""))
        alterung.altern(ledger, date(2026, 9, 12), tage=7)
        assert ledger["vorgaenge"][0]["bucket"] == "warten"
        ledger_pfad.write_text(json.dumps(ledger), encoding="utf-8")

        rc = alterung.main(["--ledger", str(ledger_pfad), "--zurueck", "8"])
        assert rc == 0

        neu = json.loads(ledger_pfad.read_text(encoding="utf-8"))
        vorgang = neu["vorgaenge"][0]
        assert vorgang["bucket"] == "owner"
        assert vorgang["frist"] is None
        assert "reaktiviert" in vorgang["frist_grund"]
        assert "reaktiviert" in vorgang["notiz"]

    def test_should_be_a_no_op_when_already_at_owner(self, tmp_path):
        ledger_pfad = tmp_path / "ledger.json"
        ledger_pfad.write_text(json.dumps(_ledger(_v(9, "owner"))), encoding="utf-8")

        rc = alterung.main(["--ledger", str(ledger_pfad), "--zurueck", "9"])
        assert rc == 0
        neu = json.loads(ledger_pfad.read_text(encoding="utf-8"))
        assert neu["vorgaenge"][0]["notiz"] == ""


class TestCliPruefe:
    def test_should_list_a_candidate_without_writing_the_ledger(self, tmp_path):
        ledger_pfad = tmp_path / "ledger.json"
        vor = json.dumps(_ledger(_v(10, "owner", frist="2026-09-01", notiz="")))
        ledger_pfad.write_text(vor, encoding="utf-8")

        rc = alterung.main(
            ["--ledger", str(ledger_pfad), "--pruefe", "--stichtag", "2026-09-12"]
        )
        assert rc == 0
        assert ledger_pfad.read_text(encoding="utf-8") == vor
