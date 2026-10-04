"""Tests fuer tools/sandbox/benchmark.py (platform#3685) — Rechnung auf Fixtures, keine Drills."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "benchmark.py"
_spec = importlib.util.spec_from_file_location("benchmark", _SCRIPT)
b = importlib.util.module_from_spec(_spec)
sys.modules["benchmark"] = b
_spec.loader.exec_module(b)


def _journal(tmp_path: Path, saetze: list[dict]) -> Path:
    pfad = tmp_path / "journal.jsonl"
    pfad.write_text("\n".join(json.dumps(s) for s in saetze) + "\nkein json\n")
    return pfad


KW39 = "2026-09-22T10:00:00+00:00"
KW40 = "2026-09-29T10:00:00+00:00"


def test_should_count_absolute_weekly_values_for_b1(tmp_path):
    journal = _journal(
        tmp_path,
        [
            {"ts": KW39, "repo": "o/a", "pr": 1, "owner_wort": "go", "state": "OPEN"},
            {"ts": KW39, "repo": "o/a", "pr": 1, "owner_wort": "go", "state": "OPEN"},
            {"ts": KW39, "repo": "o/a", "pr": 2, "erlaubt": True, "dry_run": False},
            {"ts": KW40, "repo": "o/a", "pr": 3, "erlaubt": False, "dry_run": False},
            {"ts": KW40, "repo": "o/a", "pr": 4, "owner_wort": "ok", "state": "OPEN"},
        ],
    )
    assert b.b1_owner_belastung(journal)["wochen"] == {
        "2026-W39": {
            "owner_wort_ereignisse": 2,
            "prs_mit_owner_wort": 1,
            "merges": 1,
            "abbrueche": 0,
        },
        "2026-W40": {
            "owner_wort_ereignisse": 1,
            "prs_mit_owner_wort": 1,
            "merges": 0,
            "abbrueche": 1,
        },
    }


def test_should_keep_rows_without_timestamp_separate_for_b1(tmp_path):
    journal = _journal(
        tmp_path,
        [
            {"repo": "o/a", "pr": 1, "erlaubt": True, "dry_run": False},
            {"repo": "o/a", "pr": 2, "erlaubt": False, "dry_run": False},
            {"repo": "o/a", "pr": 3, "erlaubt": True, "dry_run": True},
            {"ts": KW39, "repo": "o/a", "pr": 4, "owner_wort": "", "state": "OPEN"},
        ],
    )
    assert b.b1_owner_belastung(journal) == {
        "wochen": {},
        "ohne_zeitstempel": {"merges": 1, "abbrueche": 1},
    }


def _lauf(wurzel: Path, name: str, **status) -> None:
    ausgang = wurzel / name / "ausgang"
    ausgang.mkdir(parents=True)
    (ausgang / "status.json").write_text(json.dumps(status))


def test_should_rate_only_fertig_runs_as_done_for_b2_and_sum_costs_for_b6(tmp_path):
    _lauf(tmp_path, "l1", status="fertig", dauer_min=2.0, kosten_usd=0.5)
    _lauf(
        tmp_path,
        "l2",
        status="abgebrochen: Budget (max_tokens)",
        dauer_min=9.0,
        kosten_usd=1.0,
    )
    _lauf(tmp_path, "l3", status="fertig", dauer_min=4.0, kosten_usd=1.5)
    laeufe = b.laeufe(tmp_path)
    assert b.b2_durchlauf(laeufe) == {
        "laeufe": 3,
        "fertig": 2,
        "quote_pct": 66.7,
        "median_dauer_min": 4.0,
    }
    assert b.b6_kosten(laeufe) == {"summe_usd": 3.0, "je_lauf_usd": 1.0}


def test_should_exit_with_hard_stop_when_replay_below_100(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(
        b,
        "b5_replay",
        lambda: {"gates": 2, "gruen": 1, "quote_pct": 50.0, "rot": ["x"]},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark.py",
            "--journal",
            str(_journal(tmp_path, [])),
            "--laeufe",
            str(tmp_path),
            "--mit-replay",
        ],
    )
    assert b.main() == b.EXIT_REPLAY_ROT


def test_should_not_claim_replay_result_without_measuring(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark.py",
            "--journal",
            str(_journal(tmp_path, [])),
            "--laeufe",
            str(tmp_path),
            "--json",
        ],
    )
    assert b.main() == 0
    assert "ausstehend" in b.messen(_journal(tmp_path, []), tmp_path, False)["B5"]
