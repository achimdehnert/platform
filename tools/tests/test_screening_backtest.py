"""Tests fuer die Rueckrechnung des Technologiescreenings (KONZ-platform-063).

Geprueft wird die Entscheidung, an der alles haengt: welche Namen aus einem
Titel ueberhaupt Kandidaten werden und ob ein Fenster je TAG statt je Lauf
zaehlt. Die Beispiele stammen aus dem echten Korpus vom 2026-09-22 — auch der
Fehltreffer, damit ein spaeterer „Fix" der Wortliste nicht unbemerkt die
Messlatte verschiebt.
"""

import importlib.util
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "screening_backtest.py"
_spec = importlib.util.spec_from_file_location("screening_backtest", _SRC)
sb = importlib.util.module_from_spec(_spec)
sys.modules["screening_backtest"] = sb
_spec.loader.exec_module(sb)


def test_should_extract_product_names_from_real_titles():
    treffer = sb.namen("Two New OCR Models Land on Hugging Face")
    assert "Hugging Face" in treffer


def test_should_keep_versioned_product_names():
    # Die Kette laeuft bis zum naechsten Nicht-Namen weiter und nimmt „Demos"
    # mit. Das bleibt bewusst so: jede Erweiterung der Wortliste zieht die
    # naechste generische Vokabel nach (news-hub#33 hat genau diese Runde
    # fuenfmal gedreht). Der Rand-Unschaerfe wegen ist die Regel in KONZ-063
    # als untauglich bewertet — nicht wegen der Wortliste.
    assert "GPT-6 Astra Demos" in sb.namen("I Broke Down 4 Viral GPT-6 Astra Demos")


def test_should_ignore_first_word_because_every_title_starts_capitalised():
    # „Kernels" steht am Satzanfang und ist dort kein Beleg fuer einen Eigennamen.
    assert not any(n.startswith("Kernels") for n in sb.namen("Kernels lets you swap"))


def test_should_drop_generic_capitalised_words():
    assert sb.namen("Warum OpenAI expects AI development to slow") == ["OpenAI"]


def test_should_still_produce_the_measured_false_positive():
    # Gemessen am 2026-09-22: dieser Newsletter-Fliesstext war einer von zwei
    # Treffern der Variante A. Er steht hier, weil KONZ-063 §13 die Zahl der
    # Fehltreffer als Kill-Kriterium fuehrt — verschwindet er durch eine
    # Wortlisten-Aenderung, muss die Schwelle neu bewertet werden.
    assert "Sequence Radar Issue Last" in sb.namen(
        "The Sequence Radar Issue Last Week in AI"
    )


def test_should_count_days_not_runs():
    zeilen = [
        ("T", sb.date(2026, 9, 20), "Ein Titel ueber Mistral Mensch"),
        ("T", sb.date(2026, 9, 20), "Noch ein Lauf desselben Tages: Mistral Mensch"),
    ]
    tage = sb.nennungen(zeilen)
    assert tage["Mistral Mensch"] == {sb.date(2026, 9, 20)}


def test_should_not_call_a_name_new_when_it_appeared_in_the_baseline():
    tage = {"Astra": {sb.date(2026, 8, 30), sb.date(2026, 9, 20), sb.date(2026, 9, 21)}}
    f = sb.fenster_auswerten(tage, sb.date(2026, 9, 21), 7, 21, 2)
    assert f["variante_a"] == []


def test_should_report_riser_when_baseline_is_clean():
    tage = {"Astra": {sb.date(2026, 9, 20), sb.date(2026, 9, 21)}}
    f = sb.fenster_auswerten(tage, sb.date(2026, 9, 21), 7, 21, 2)
    assert f["variante_a"] == [{"name": "Astra", "tage": 2}]


def test_should_skip_malformed_lines_instead_of_failing(tmp_path):
    pfad = tmp_path / "korpus.tsv"
    pfad.write_text(
        "T\t2026-09-21\tEin Titel ueber Hugging Face\n"
        "kaputt\n"
        "T\tkein-datum\tirgendwas\n"
        "T\t2026-09-21\t\n",
        encoding="utf-8",
    )
    assert len(sb.korpus_lesen(str(pfad))) == 1


def test_should_exit_2_on_empty_corpus(tmp_path, capsys):
    pfad = tmp_path / "leer.tsv"
    pfad.write_text("", encoding="utf-8")
    assert sb.main([str(pfad)]) == 2
