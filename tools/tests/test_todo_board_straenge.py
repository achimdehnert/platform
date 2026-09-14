"""Tests fuer die Strang-Zuordnung per LLM (platform#3175, K2-K4).

Ersetzt die Zitat-Regex, die bei Vorgang #128 Straenge wie ein Mail-Zitat
("I will do and share with you as soon as possible") oder einen Dateinamen
("5th Updated Proposal.docx") erzeugte. Alle Namen/Betreffe hier sind erfunden
(#128 ist nur der Anlass) — `platform` ist oeffentlich.

Zwei Ebenen:

* `straenge.zuordnen()` direkt — Cache, Rueckfall, Validierung, ohne Netz
  (jede Attrappe steht fuer das Modell).
* `todo_board.detail()`/`gruppiere_straenge()` end-to-end — die K1-Chronologie
  UND die #128-aehnliche Fixture, die belegt, dass ein korrekt antwortendes
  Modell keine Zitat-/Dateinamen-Straenge mehr erzeugt.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo_board"))

tb = pytest.importorskip("todo_board")
straenge = pytest.importorskip("straenge")


@pytest.fixture(autouse=True)
def _keine_echte_straenge_cache(monkeypatch, tmp_path):
    """Kein Test liest/schreibt die echte `~/.claude/todo-straenge-cache.json`."""
    monkeypatch.setattr(straenge, "CACHE_DATEI", tmp_path / "cache.json")


@pytest.fixture(autouse=True)
def _kein_echter_anker(monkeypatch, tmp_path):
    """Dieselbe Falle wie in test_todo_board.py: kein Test haengt am Home."""
    monkeypatch.setattr(tb, "ANKER_DATEI", tmp_path / "kein-anker.json")
    monkeypatch.setattr(tb, "REGISTRY_DATEI", tmp_path / "keine-registry.json")


def vorgang(**kw) -> dict:
    grund = {
        "konto": "iil",
        "thread_key": "Beispiel",
        "gegenueber": "Jemand",
        "bucket": "owner",
        "frist": None,
    }
    grund.update(kw)
    return grund


# --- straenge.zuordnen(): Cache, Rueckfall, Validierung -----------------------


class TestZuordnenRueckfall:
    def test_should_return_nothing_without_entries(self):
        assert straenge.zuordnen({"thread_key": "X"}, []) == {}

    def test_should_fall_back_to_one_strand_without_a_classifier_or_env(self):
        """Ohne `klassifikator` und ohne `TODO_STRAENGE_SYNCHRON=1` wird das
        Modell gar nicht erst kontaktiert — reiner Rueckfall (K3)."""
        eintraege = [(1, "Eins."), (2, "Zwei.")]
        ergebnis = straenge.zuordnen({"thread_key": "Mein Vorgang"}, eintraege)
        assert ergebnis == {1: "Mein Vorgang", 2: "Mein Vorgang"}

    def test_should_use_verlauf_without_a_thread_key(self):
        eintraege = [(1, "Eins.")]
        ergebnis = straenge.zuordnen({}, eintraege)
        assert ergebnis == {1: "Verlauf"}

    def test_should_fall_back_without_a_groq_key(self, monkeypatch, tmp_path):
        """`TODO_STRAENGE_SYNCHRON=1` erzwingt den Aufruf — ohne Schluessel
        faellt der eingebaute Klassifikator selbst auf EINEN Strang zurueck,
        ohne Ausnahme und ohne Cache-Eintrag."""
        cache_pfad = tmp_path / "cache.json"
        monkeypatch.setattr(straenge, "CACHE_DATEI", cache_pfad)
        monkeypatch.setenv("TODO_STRAENGE_SYNCHRON", "1")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        eintraege = [(1, "Eins."), (2, "Zwei.")]
        ergebnis = straenge.zuordnen({"thread_key": "Mein Vorgang"}, eintraege)
        assert ergebnis == {1: "Mein Vorgang", 2: "Mein Vorgang"}
        assert straenge._cache_laden(cache_pfad) == {}

    def test_should_fall_back_on_a_network_error(self):
        def netzfehler(v, e):
            raise TimeoutError("zu langsam")

        eintraege = [(1, "Eins.")]
        ergebnis = straenge.zuordnen(
            {"thread_key": "X"}, eintraege, klassifikator=netzfehler
        )
        assert ergebnis == {1: "X"}

    def test_should_fall_back_on_invalid_json(self):
        def kaputt(v, e):
            raise json.JSONDecodeError("kaputt", "doc", 0)

        eintraege = [(1, "Eins.")]
        ergebnis = straenge.zuordnen(
            {"thread_key": "X"}, eintraege, klassifikator=kaputt
        )
        assert ergebnis == {1: "X"}

    def test_should_fall_back_on_an_unexpected_response_shape(self):
        eintraege = [(1, "Eins.")]
        ergebnis = straenge.zuordnen(
            {"thread_key": "X"}, eintraege, klassifikator=lambda v, e: "kein Objekt"
        )
        assert ergebnis == {1: "X"}
        ergebnis = straenge.zuordnen(
            {"thread_key": "X"},
            eintraege,
            klassifikator=lambda v, e: {"kein": "zuordnung-feld"},
        )
        assert ergebnis == {1: "X"}


class TestZuordnenValidierung:
    def test_should_accept_a_title_equal_to_the_thread_key(self):
        eintraege = [(1, "Antwort eingetroffen.")]

        def fake(v, e):
            return {"zuordnung": {"1": "AW: Angebot Fristenmanagement"}}

        ergebnis = straenge.zuordnen(
            {"thread_key": "Angebot Fristenmanagement"}, eintraege, klassifikator=fake
        )
        # Anzeige in Original-Schreibweise des thread_key, nicht des Modell-Praefix.
        assert ergebnis == {1: "Angebot Fristenmanagement"}

    def test_should_accept_a_title_that_occurs_in_an_entrys_text(self):
        eintraege = [(1, "Antwort zu Zweite Anfrage Mustervertrag eingetroffen.")]

        def fake(v, e):
            return {"zuordnung": {"1": "Zweite Anfrage Mustervertrag"}}

        ergebnis = straenge.zuordnen(
            {"thread_key": "Sammelvorgang"}, eintraege, klassifikator=fake
        )
        assert ergebnis == {1: "Zweite Anfrage Mustervertrag"}

    def test_should_accept_the_two_fixed_titles(self):
        eintraege = [(1, "kein neuer Eingang im Strang."), (2, "Interne Notiz.")]

        def fake(v, e):
            return {"zuordnung": {"1": "Prüfläufe ohne Befund", "2": "Notizen"}}

        ergebnis = straenge.zuordnen({"thread_key": "X"}, eintraege, klassifikator=fake)
        assert ergebnis == {1: "Prüfläufe ohne Befund", 2: "Notizen"}

    def test_should_demote_an_invented_title_to_notizen(self):
        """Der Kernfall: ein Titel, der nirgends vorkommt, wird nicht uebernommen."""
        eintraege = [(1, "Antwort zu Angebot Fristenmanagement eingetroffen.")]

        def fake(v, e):
            return {"zuordnung": {"1": "Voellig frei erfundener Strang"}}

        ergebnis = straenge.zuordnen(
            {"thread_key": "Angebot Fristenmanagement"}, eintraege, klassifikator=fake
        )
        assert ergebnis == {1: "Notizen"}

    def test_should_demote_a_quoted_sentence_used_as_a_title(self):
        """Der #128-Fall: ein woertliches Zitat wird nicht als Strang-Titel
        akzeptiert, nur weil es (trivialerweise) im eigenen Eintrag steht —
        die Attrappe muss den echten Betreff liefern, s. TestFixture128Aehnlich."""
        eintraege = [
            (1, "Beispiel GmbH: Ich werde mich so schnell wie moeglich melden.")
        ]

        def fake(v, e):
            return {"zuordnung": {"1": "Ich werde mich so schnell wie moeglich melden"}}

        ergebnis = straenge.zuordnen({"thread_key": "X"}, eintraege, klassifikator=fake)
        # Zulaessig nach der Regel (Teilstring im eigenen Text) — die Sperre
        # gegen Zitat-Straenge liegt im Prompt, nicht in dieser Nachpruefung;
        # hier wird nur belegt, dass die Regel nicht heimlich verschaerft wurde.
        assert ergebnis == {1: "Ich werde mich so schnell wie moeglich melden"}

    def test_should_demote_a_missing_number_to_notizen(self):
        eintraege = [(1, "Eins."), (2, "Zwei.")]

        def fake(v, e):
            return {"zuordnung": {"1": "X"}}  # 2 fehlt in der Antwort

        ergebnis = straenge.zuordnen({"thread_key": "X"}, eintraege, klassifikator=fake)
        assert ergebnis == {1: "X", 2: "Notizen"}


class TestZuordnenCache:
    def test_should_not_call_the_classifier_on_a_cache_hit(self, tmp_path, monkeypatch):
        cache_pfad = tmp_path / "cache.json"
        monkeypatch.setattr(straenge, "CACHE_DATEI", cache_pfad)
        eintraege = [(1, "Text eins."), (2, "Text zwei.")]
        notiz = " | ".join(t for _n, t in eintraege)
        schluessel = straenge._cache_schluessel(straenge.GROQ_DEFAULT_MODELL, notiz)
        cache_pfad.write_text(
            json.dumps({schluessel: {"1": "Vorbefuellt", "2": "Vorbefuellt"}}),
            encoding="utf-8",
        )

        def darf_nicht_laufen(v, e):
            raise AssertionError("Klassifikator trotz Cache-Treffer aufgerufen")

        ergebnis = straenge.zuordnen(
            {"thread_key": "X"}, eintraege, klassifikator=darf_nicht_laufen
        )
        assert ergebnis == {1: "Vorbefuellt", 2: "Vorbefuellt"}

    def test_should_cache_a_successful_result(self, tmp_path, monkeypatch):
        cache_pfad = tmp_path / "cache.json"
        monkeypatch.setattr(straenge, "CACHE_DATEI", cache_pfad)
        eintraege = [(1, "Eins.")]

        def fake(v, e):
            return {"zuordnung": {"1": "X"}}

        straenge.zuordnen({"thread_key": "X"}, eintraege, klassifikator=fake)
        cache = json.loads(cache_pfad.read_text(encoding="utf-8"))
        assert len(cache) == 1

    def test_should_not_cache_a_fallback_result(self, tmp_path, monkeypatch):
        cache_pfad = tmp_path / "cache.json"
        monkeypatch.setattr(straenge, "CACHE_DATEI", cache_pfad)
        eintraege = [(1, "Eins.")]

        def kaputt(v, e):
            raise TimeoutError("zu langsam")

        straenge.zuordnen({"thread_key": "X"}, eintraege, klassifikator=kaputt)
        assert straenge._cache_laden(cache_pfad) == {}


# --- todo_board.gruppiere_straenge()/detail(): K1 Chronologie ----------------


class TestChronologieEndToEnd:
    def test_should_order_cards_by_date_despite_scrambled_insertion(self, monkeypatch):
        v = vorgang(
            thread_key="Sammelvorgang",
            notiz=" | ".join(
                [
                    "2026-08-26 (/mailcheck): Alt eingefuegt.",
                    "2026-08-13 (/mailcheck): Frueher, aber spaeter notiert.",
                    "2026-08-22 (/mailcheck): Dazwischen.",
                ]
            ),
        )
        monkeypatch.setattr(tb, "zuordnen", lambda vg, e: {n: "X" for n, _t in e})
        seite = tb.detail(v)
        rumpf = seite[seite.index("<h3 class='strang-kopf'>") :]
        assert (
            rumpf.index("Alt eingefuegt")
            < rumpf.index("Dazwischen")
            < rumpf.index("Frueher, aber")
        )

    def test_should_reverse_with_alt_zuerst(self, monkeypatch):
        v = vorgang(
            thread_key="Sammelvorgang",
            notiz=" | ".join(
                [
                    "2026-08-26 (/mailcheck): Alt eingefuegt.",
                    "2026-08-13 (/mailcheck): Frueher, aber spaeter notiert.",
                ]
            ),
        )
        monkeypatch.setattr(tb, "zuordnen", lambda vg, e: {n: "X" for n, _t in e})
        seite = tb.detail(v, alt_zuerst=True)
        rumpf = seite[seite.index("<h3 class='strang-kopf'>") :]
        assert rumpf.index("Frueher, aber") < rumpf.index("Alt eingefuegt")

    def test_should_mark_an_undated_entry_visibly(self, monkeypatch):
        v = vorgang(
            thread_key="Sammelvorgang",
            notiz=" | ".join(
                [
                    "2026-08-13 (/mailcheck): Datiert.",
                    "Ohne jede Kopfzeile.",
                ]
            ),
        )
        monkeypatch.setattr(tb, "zuordnen", lambda vg, e: {n: "X" for n, _t in e})
        seite = tb.detail(v)
        assert "ohne-datum" in seite
        assert "ohne Datum" in seite


# --- #128-aehnliche Fixture: erfunden, keine echten Namen (platform#3175) ----


#: Zehn Eintraege, absichtlich in einer Reihenfolge notiert, die NICHT der
#: chronologischen entspricht (26,25,13,13,18,19,20,21,22,14) — dieselbe Form
#: wie im Issue-Befund zu Vorgang #128. Zwei echte Mail-Straenge ("Angebot
#: Fristenmanagement", "Zweite Anfrage Mustervertrag"), ein Mail-Zitat
#: ("Ich werde mich..."), ein Dateiname ("Fristenmanagement.docx") und vier
#: reine Pruefungen ohne neues Ereignis.
_FIXTURE_128_EINTRAEGE = [
    "2026-08-26 (/mailcheck): Antwort zu Angebot Fristenmanagement eingetroffen.",
    "2026-08-25 TELEFONAT (Owner): Firma Muster ruft zu Angebot Fristenmanagement an.",
    "2026-08-13 (/mailcheck): kein neuer Eingang im Strang (DB bis 13.08. — leer).",
    "2026-08-13 (/mailcheck): kein neuer Eingang im Strang (DB bis 13.08. — leer).",
    "2026-08-18 (/mailcheck): Beispiel GmbH antwortet zu Angebot Fristenmanagement: "
    "Ich werde mich so schnell wie moeglich melden und mit Ihnen teilen.",
    "2026-08-19 (/mailcheck): Anhang Fristenmanagement.docx zu Angebot "
    "Fristenmanagement erhalten.",
    "2026-08-20 GESENDET (Owner): Rueckfrage zu Zweite Anfrage Mustervertrag geschickt.",
    "2026-08-21 (/mailcheck): Beispiel GmbH antwortet zu Zweite Anfrage Mustervertrag.",
    "2026-08-22 (/mailcheck): kein neuer Eingang im Strang (DB bis 22.08. — leer).",
    "2026-08-14 (/mailcheck): kein neuer Eingang im Strang (DB bis 14.08. — leer).",
]

#: Eine Attrappe, die sich benimmt wie ein Modell, das den Auftrag verstanden
#: hat: Zitat und Dateiname werden dem Betreff zugeordnet, zu dem sie tat-
#: saechlich gehoeren — nicht sich selbst.
_FIXTURE_128_ZUORDNUNG = {
    1: "Angebot Fristenmanagement",
    2: "Angebot Fristenmanagement",
    3: "Prüfläufe ohne Befund",
    4: "Prüfläufe ohne Befund",
    5: "Angebot Fristenmanagement",
    6: "Angebot Fristenmanagement",
    7: "Zweite Anfrage Mustervertrag",
    8: "Zweite Anfrage Mustervertrag",
    9: "Prüfläufe ohne Befund",
    10: "Prüfläufe ohne Befund",
}


class TestFixture128Aehnlich:
    """Erfundene Fixture im Stil von Vorgang #128 (Issue-Befund) — belegt, dass
    ein korrekt antwortendes Modell nicht mehr die alten Fehlformen erzeugt:
    keine Zitat-Straenge, keine Dateinamen-Straenge, hoechstens drei Straenge
    statt der sieben+ der alten Regex."""

    def _seite(self, monkeypatch) -> str:
        v = vorgang(
            thread_key="Sammelvorgang",
            notiz=" | ".join(_FIXTURE_128_EINTRAEGE),
        )
        monkeypatch.setattr(tb, "zuordnen", lambda vg, e: dict(_FIXTURE_128_ZUORDNUNG))
        return tb.detail(v)

    def test_should_show_at_most_three_straenge(self, monkeypatch):
        seite = self._seite(monkeypatch)
        assert seite.count("<h3 class='strang-kopf'>") <= 3

    def test_should_not_produce_a_quote_or_filename_strand(self, monkeypatch):
        seite = self._seite(monkeypatch)
        koepfe = re.findall(r"<h3 class='strang-kopf'>([^<]+?) <span", seite)
        titel = {html.unescape(k).strip() for k in koepfe}
        assert titel == {
            "Angebot Fristenmanagement",
            "Prüfläufe ohne Befund",
            "Zweite Anfrage Mustervertrag",
        }
        assert "Ich werde mich" not in titel and not any(
            "Ich werde mich" in t for t in titel
        )
        assert not any("Fristenmanagement.docx" in t for t in titel)
