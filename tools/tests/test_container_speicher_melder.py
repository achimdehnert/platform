"""Drill fuer tools/container_speicher_melder.py (#3400).

Die Fixture ist die echte Messung von gotenberg auf prod am 2026-09-23 (cgroup v2,
nur lesend): 512 MiB Limit, anon 217 MiB, file 186 MiB, kernel 64 MiB,
`memory.events max` 1036, `oom_kill` 0. `docker stats` zeigte dafuer 92 % — der
Melder darf daraus KEINEN Befund machen (Negativkontrolle), muss aber jede der drei
Regeln feuern, sobald ihre Lage eintritt (Positivkontrollen).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import container_speicher_melder as csm  # noqa: E402
import melder_ergebnis  # noqa: E402

NAME = "iil_dochub_gotenberg"
JETZT = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)

# Echte Messwerte 2026-09-23, in der Form, die FERNSKRIPT auf prod ausgibt.
FERNAUSGABE_ECHT = f"""\
@@ {NAME} 536870912 495308800 538357760
s anon 227434496
s file 195129344
s kernel 67432448
e low 0
e high 0
e max 1036
e oom 0
e oom_kill 0
e oom_group_kill 0
"""

ECHT = {
    "max": 536870912,
    "current": 495308800,
    "peak": 538357760,
    "anon": 227434496,
    "file": 195129344,
    "kernel": 67432448,
    "ev_max": 1036,
    "oom_kill": 0,
}


def _zeile(t: datetime, **ueberschreibe) -> dict:
    c = dict(ECHT, **ueberschreibe)
    return {"ts": csm._iso(t), "host": "hetzner-prod", "container": {NAME: c}, "_t": t}


def _reihe(tage: float, pro_tag: float, ende: datetime, start_max: int = 1036):
    """Laeufe alle 15 min ueber `tage` mit gleichmaessiger max-Rate."""
    schritte = int(tage * 96)
    return [
        _zeile(
            ende - timedelta(minutes=15 * (schritte - i)),
            ev_max=start_max + round(pro_tag * i / 96),
        )
        for i in range(schritte + 1)
    ]


# --- Parsen -------------------------------------------------------------------


def test_should_parse_real_gotenberg_sample_exactly():
    assert csm.parse_fernausgabe(FERNAUSGABE_ECHT) == {NAME: ECHT}


def test_should_ignore_containers_block_without_numbers():
    text = "@@ kaputt max 1 2\ns anon 5\n" + FERNAUSGABE_ECHT
    assert set(csm.parse_fernausgabe(text)) == {NAME}


def test_should_keep_missing_peak_as_none():
    text = FERNAUSGABE_ECHT.replace("495308800 538357760", "495308800 -")
    assert csm.parse_fernausgabe(text)[NAME]["peak"] is None


# --- Negativkontrolle ---------------------------------------------------------


def test_should_stay_silent_on_real_sample_with_steady_rate():
    """Echte Lage: 42 % anon, 13 Limit-Treffer/Tag gleichmaessig, kein OOM."""
    journal = _reihe(7, 13, JETZT)
    e = csm.bewerte(journal, JETZT)
    assert e["befunde"] == [] and e["status"] == "ok"
    c = e["container"][0]
    assert c["anon_anteil"] == round(227434496 / 536870912, 3)
    assert c["trend"]["stand"] == "belastbar"
    assert csm.exitcode(e) == 0


def test_should_report_sammelphase_on_first_run_not_all_clear():
    e = csm.bewerte([_zeile(JETZT)], JETZT)
    assert e["befunde"] == [] and e["trend_sammelphase"]
    assert "SAMMELPHASE" in csm.kurzzeile(e)
    assert e["container"][0]["oom_delta"] is None


# --- Positivkontrollen --------------------------------------------------------


def test_should_raise_error_when_oom_kill_increases():
    journal = [
        _zeile(JETZT - timedelta(minutes=15)),
        _zeile(JETZT, oom_kill=1),
    ]
    e = csm.bewerte(journal, JETZT)
    assert [(b["stufe"], b["text"]) for b in e["befunde"]] == [
        ("FEHLER", "oom_kill +1")
    ]
    assert csm.exitcode(e) == 1


def test_should_count_oom_after_restart_reset_counter():
    """Neustart setzt den Zaehler zurueck: 3 -> 1 heisst 1 neuer Kill, nicht -2."""
    journal = [
        _zeile(JETZT - timedelta(minutes=15), oom_kill=3),
        _zeile(JETZT, oom_kill=1),
    ]
    assert csm.bewerte(journal, JETZT)["container"][0]["oom_delta"] == 1


def test_should_warn_when_anon_exceeds_seventy_percent():
    anon_75 = int(0.75 * ECHT["max"])
    e = csm.bewerte([_zeile(JETZT, anon=anon_75)], JETZT)
    assert [(b["stufe"], b["text"]) for b in e["befunde"]] == [
        ("WARN", "anon 75% vom Limit")
    ]


def test_should_not_warn_at_exactly_seventy_percent():
    e = csm.bewerte([_zeile(JETZT, anon=int(0.70 * ECHT["max"]))], JETZT)
    assert e["befunde"] == []


def test_should_flag_trend_when_max_rate_doubles():
    """Sechs Tage 13/Tag, dann 30 in den letzten 24 h -> mehr als doppelt."""
    basis = _reihe(6, 13, JETZT - timedelta(days=1))
    letzte = basis[-1]["container"][NAME]["ev_max"]
    neu = _reihe(1, 30, JETZT, start_max=letzte)[1:]
    e = csm.bewerte(basis + neu, JETZT)
    tr = e["container"][0]["trend"]
    assert tr["feuert"] and tr["ereignisse_24h"] == 30
    assert [b["stufe"] for b in e["befunde"]] == ["TREND"]


def test_should_not_flag_trend_below_minimum_event_count():
    """0/Tag Basis, dann 3 Treffer: verdoppelt, aber zu wenig, um zu rufen."""
    basis = _reihe(6, 0, JETZT - timedelta(days=1))
    neu = _reihe(1, 3, JETZT, start_max=1036)[1:]
    assert csm.bewerte(basis + neu, JETZT)["befunde"] == []


def test_should_not_judge_trend_with_less_than_two_days_basis():
    basis = _reihe(1, 1, JETZT - timedelta(days=1))
    neu = _reihe(1, 50, JETZT, start_max=basis[-1]["container"][NAME]["ev_max"])[1:]
    tr = csm.bewerte(basis + neu, JETZT)["container"][0]["trend"]
    assert tr["stand"] == "sammelphase" and not tr["feuert"]


# --- Entscheidungsgrundlage, Journal, Lesen ------------------------------------


def test_should_report_anon_peak_over_journal_for_decision():
    journal = [
        _zeile(JETZT - timedelta(hours=2), anon=int(0.65 * ECHT["max"])),
        _zeile(JETZT),
    ]
    c = csm.bewerte(journal, JETZT)["container"][0]
    assert c["anon_spitze"] == 0.65 > csm.ENTSCHEID_ANTEIL
    assert "⚑" in csm.vollbericht(csm.bewerte(journal, JETZT))


def test_should_append_one_line_per_run_and_drop_old_lines(tmp_path):
    pfad = tmp_path / "j.jsonl"
    alt = _zeile(JETZT - timedelta(days=csm.JOURNAL_TAGE + 1))
    mitte = _zeile(JETZT - timedelta(days=1))
    csm.schreibe_journal(pfad, [alt, mitte], _zeile(JETZT), JETZT)
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 2
    assert json.loads(zeilen[-1])["container"][NAME] == ECHT
    assert [z["ts"] for z in csm.lies_journal(pfad)] == [mitte["ts"], csm._iso(JETZT)]


def test_should_read_fresh_result_and_reject_stale_one(tmp_path):
    pfad = tmp_path / "e.json"
    e = csm.bewerte([_zeile(JETZT, oom_kill=0)], JETZT)
    melder_ergebnis.schreibe(pfad, melder=csm.MELDER, ergebnis=e, gemessen_am=JETZT)
    text, rc = csm.lesen(pfad, JETZT + timedelta(minutes=20))
    assert text.startswith("OK: 1 Container") and rc == 0
    text, rc = csm.lesen(pfad, JETZT + timedelta(minutes=csm.LESEN_MAX_ALTER_MIN + 1))
    assert text.startswith("NICHT GELAUFEN") and rc == 2
    text, rc = csm.lesen(tmp_path / "fehlt.json", JETZT)
    assert text.startswith("NICHT GELAUFEN") and rc == 2


def test_should_exit_blind_when_host_unreachable(tmp_path, monkeypatch):
    monkeypatch.setattr(csm, "messe", lambda host: (None, f"{host}: Zeitlimit"))
    rc = csm.main(
        [
            "--kurz",
            "--journal",
            str(tmp_path / "j.jsonl"),
            "--ergebnis-datei",
            str(tmp_path / "e.json"),
        ]
    )
    assert rc == 2
    assert not (tmp_path / "j.jsonl").exists()
    assert csm.lesen(tmp_path / "e.json", datetime.now(timezone.utc))[1] == 2
