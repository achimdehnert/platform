"""Drill fuer tools/rueckstau_melder.py — Rueckstau in Posteingang/pruefen.

Kernaussage des Melders (siehe Modul-Docstring): Wachstum ist der Befund, nicht
die absolute Zahl. Der erste Test-Block prueft genau diese Unterscheidung;
danach folgen die beiden Pflicht-Faelle aus dem Auftrag — Erstlauf ohne
Vorwert bleibt gruen, und ein nicht beschreibbarer Zustandspfad darf den Lauf
nicht abbrechen (derselbe Fehler, der am 2026-09-10 in scan_melder.py behoben
wurde).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rueckstau_melder as rm  # noqa: E402

STAPEL = ["posteingang", "pruefen"]


def _stand(**werte: int) -> dict[str, dict]:
    return {
        name: {"anzahl": anzahl, "gemessen_am": 0} for name, anzahl in werte.items()
    }


# --- Wachstum ist das Signal -------------------------------------------------


def test_should_flag_growth_as_a_finding():
    alt = _stand(posteingang=331, pruefen=57)
    neu = {"posteingang": 332, "pruefen": 57}
    treffer = rm.gewachsene_stapel(alt, neu)
    assert [t["stapel"] for t in treffer] == ["posteingang"]
    assert treffer[0] == {"stapel": "posteingang", "alt": 331, "neu": 332, "delta": 1}


def test_should_not_flag_shrinkage():
    alt = _stand(posteingang=331, pruefen=57)
    neu = {"posteingang": 300, "pruefen": 57}
    assert rm.gewachsene_stapel(alt, neu) == []


def test_should_not_flag_an_unchanged_stack():
    alt = _stand(posteingang=331, pruefen=57)
    neu = {"posteingang": 331, "pruefen": 57}
    assert rm.gewachsene_stapel(alt, neu) == []


def test_should_respect_a_configured_tolerance():
    alt = _stand(posteingang=331)
    neu = {"posteingang": 332}
    assert rm.gewachsene_stapel(alt, neu, toleranz=1) == []
    assert rm.gewachsene_stapel(alt, neu, toleranz=0) != []


def test_should_report_each_grown_stack_independently():
    alt = _stand(posteingang=331, pruefen=57)
    neu = {"posteingang": 340, "pruefen": 60}
    treffer = rm.gewachsene_stapel(alt, neu)
    assert {t["stapel"] for t in treffer} == {"posteingang", "pruefen"}


def test_should_skip_comparison_for_a_newly_added_stack_without_failing_the_run():
    """Ein drittes Stichwort ohne Vorwert bricht NICHT den ganzen Vergleich ab."""
    alt = _stand(posteingang=331)
    neu = {"posteingang": 331, "vertrag": 5}
    assert rm.gewachsene_stapel(alt, neu) == []


# --- Erstlauf ohne Vorwert ---------------------------------------------------


def test_should_return_no_findings_on_first_run_without_prior_state():
    assert rm.gewachsene_stapel(None, {"posteingang": 331, "pruefen": 57}) == []


def test_should_say_explicitly_that_first_run_has_no_comparison():
    zeile = rm.kurzzeile(
        {"posteingang": 331, "pruefen": 57},
        gewachsene=[],
        erster_lauf=True,
        stand_geschrieben=True,
    )
    assert "erster Lauf" in zeile
    assert "naechsten Lauf" in zeile


def test_should_exit_0_on_first_run_via_main(tmp_path, monkeypatch):
    stand_pfad = tmp_path / "stand.json"

    def _fake_messe(stapel, ssh):
        return {"posteingang": 331, "pruefen": 57}, True

    monkeypatch.setattr(rm, "messe", _fake_messe)
    rc = rm.main(["--stand", str(stand_pfad), "--kurz"])
    assert rc == 0
    assert stand_pfad.exists()


def test_should_exit_1_when_a_stack_grew_via_main(tmp_path, monkeypatch, capsys):
    stand_pfad = tmp_path / "stand.json"
    stand_pfad.write_text(
        '{"stapel": {"posteingang": {"anzahl": 331, "gemessen_am": 0}, '
        '"pruefen": {"anzahl": 57, "gemessen_am": 0}}}',
        encoding="utf-8",
    )

    def _fake_messe(stapel, ssh):
        return {"posteingang": 340, "pruefen": 57}, True

    monkeypatch.setattr(rm, "messe", _fake_messe)
    rc = rm.main(["--stand", str(stand_pfad), "--kurz"])
    assert rc == 1
    zeile = capsys.readouterr().out
    assert "posteingang" in zeile
    assert "331" in zeile and "340" in zeile


def test_should_exit_0_when_stacks_shrank_or_stayed_equal_via_main(
    tmp_path, monkeypatch
):
    stand_pfad = tmp_path / "stand.json"
    stand_pfad.write_text(
        '{"stapel": {"posteingang": {"anzahl": 331, "gemessen_am": 0}, '
        '"pruefen": {"anzahl": 57, "gemessen_am": 0}}}',
        encoding="utf-8",
    )

    def _fake_messe(stapel, ssh):
        return {"posteingang": 300, "pruefen": 57}, True

    monkeypatch.setattr(rm, "messe", _fake_messe)
    rc = rm.main(["--stand", str(stand_pfad), "--kurz"])
    assert rc == 0


# --- Nicht beschreibbarer Zustandspfad --------------------------------------


def test_should_report_instead_of_crashing_when_state_path_is_unwritable(tmp_path):
    """Positivkontrolle folgt direkt danach: derselbe Aufruf schreibt auf freiem Pfad."""
    gesperrt = tmp_path / "gesperrt"
    gesperrt.mkdir(mode=0o500)
    assert (
        rm.schreibe_stand(gesperrt / "tief" / "stand.json", {"posteingang": 331})
        is False
    )


def test_should_confirm_a_writable_state_path(tmp_path):
    assert (
        rm.schreibe_stand(tmp_path / "tief" / "stand.json", {"posteingang": 331})
        is True
    )


def test_should_keep_running_and_exit_correctly_when_state_path_is_unwritable(
    tmp_path, monkeypatch, capsys
):
    gesperrt = tmp_path / "gesperrt"
    gesperrt.mkdir(mode=0o500)
    stand_pfad = gesperrt / "tief" / "stand.json"

    def _fake_messe(stapel, ssh):
        return {"posteingang": 331, "pruefen": 57}, True

    monkeypatch.setattr(rm, "messe", _fake_messe)
    rc = rm.main(["--stand", str(stand_pfad), "--kurz"])
    ausgabe = capsys.readouterr()
    assert rc != 2
    assert ausgabe.out.strip() != ""
    assert "nicht beschreibbar" in ausgabe.err


# --- unlesbare / leere DB-Antwort --------------------------------------------


def test_should_exit_2_on_unreadable_response_not_0(monkeypatch):
    def _fake_messe(stapel, ssh):
        return None, True

    monkeypatch.setattr(rm, "messe", _fake_messe)
    assert rm.main(["--stand", "", "--kurz"]) == 2


def test_should_exit_2_when_db_is_unreachable(monkeypatch):
    def _fake_messe(stapel, ssh):
        return None, False

    monkeypatch.setattr(rm, "messe", _fake_messe)
    assert rm.main(["--stand", "", "--kurz"]) == 2


def test_should_treat_empty_psql_response_as_unreadable_not_zero():
    assert rm.parse_zahlen("", STAPEL) is None
    assert rm.parse_zahlen("   \n", STAPEL) is None


def test_should_treat_malformed_line_as_unreadable():
    assert rm.parse_zahlen("Posteingang-331", STAPEL) is None
    assert rm.parse_zahlen("Posteingang|dreihundert", STAPEL) is None


# --- Parser mit echtem Antwortformat -----------------------------------------


def test_should_parse_real_psql_response_format():
    antwort = "Posteingang|331\npruefen|57\n"
    zahlen = rm.parse_zahlen(antwort, STAPEL)
    assert zahlen == {"posteingang": 331, "pruefen": 57}


def test_should_treat_a_stack_missing_from_the_response_as_zero():
    antwort = "Posteingang|331\n"
    zahlen = rm.parse_zahlen(antwort, STAPEL)
    assert zahlen == {"posteingang": 331, "pruefen": 0}


def test_should_merge_umlaut_and_ascii_spelling_of_the_same_stack():
    antwort = "prüfen|40\npruefen|17\n"
    zahlen = rm.parse_zahlen(antwort, ["pruefen"])
    assert zahlen == {"pruefen": 57}


def test_should_include_both_spellings_in_the_sql_filter():
    sql = rm.baue_sql(["pruefen"])
    assert "'pruefen'" in sql
    assert "'prüfen'" in sql


# --- Kurzzeile bleibt oeffentlich unbedenklich -------------------------------


def test_should_name_stack_and_old_and_new_value_in_the_short_line():
    zeile = rm.kurzzeile(
        {"posteingang": 340},
        gewachsene=[{"stapel": "posteingang", "alt": 331, "neu": 340, "delta": 9}],
        erster_lauf=False,
        stand_geschrieben=True,
    )
    assert "posteingang" in zeile
    assert "331" in zeile
    assert "340" in zeile
