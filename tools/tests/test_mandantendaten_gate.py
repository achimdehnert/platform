"""Tests fuer tools/checks/mandantendaten_gate.py.

Der Gate vergleicht neue Zeilen gegen echte Namen aus lokalen Quellen. Geprueft
wird hier die Begriffsgewinnung — sie war in der ersten Fassung so grob, dass die
Bestandsaufnahme 13478 Treffer meldete und der Gate jeden Push blockiert haette.
Die Faelle unten halten genau diese Kalibrierung fest.

Stdlib-only, damit die Tests im `tools-tests.yml`-Job wirklich laufen und nicht
uebersprungen werden. Alle Beispieldaten sind erfunden — das Repo ist oeffentlich.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))

mg = pytest.importorskip("mandantendaten_gate")


class TestNamensteil:
    def test_should_drop_a_parenthetical_note(self):
        roh = "Muster-Werke Beispielstadt (Rechnung Juli, privat)"
        assert mg.namensteil(roh) == "Muster-Werke Beispielstadt"

    def test_should_drop_everything_after_a_slash(self):
        assert mg.namensteil("Beispiel AG / Herr Mustermann") == "Beispiel AG"

    def test_should_survive_an_empty_field(self):
        assert mg.namensteil("") == ""


class TestZerlege:
    def test_should_keep_the_full_name_and_its_distinctive_parts(self):
        begriffe = mg.zerlege("Musterwerke Recycling GmbH")
        assert "musterwerke recycling gmbh" in begriffe
        assert "musterwerke" in begriffe

    def test_should_drop_the_industry_word_as_a_standalone_term(self):
        # 'Recycling' benennt die Branche, nicht die Partei. Als Einzelbegriff
        # traf es Fliesstext im Repo; der kennzeichnende Namensteil schuetzt weiter.
        begriffe = mg.zerlege("Musterwerke Recycling GmbH")
        assert "recycling" not in begriffe
        assert "musterwerke" in begriffe

    def test_should_drop_generic_company_words(self):
        # 'gmbh' und 'holding' benennen niemanden — als Einzelbegriff wuerden sie
        # jeden Push blockieren.
        begriffe = mg.zerlege("Musterwerke Holding GmbH")
        assert "gmbh" not in begriffe
        assert "holding" not in begriffe

    def test_should_yield_nothing_for_a_purely_generic_name(self):
        assert mg.zerlege("Rechnung Vertrag GmbH") == set()

    def test_should_not_protect_the_own_identity(self):
        # Der eigene Name steht zu Recht ueberall im Repo (CODEOWNERS, Branches).
        assert "dehnert" not in mg.zerlege("Achim Dehnert")

    def test_should_drop_words_below_the_length_floor(self):
        # Kurze Fragmente wie 'ulm' treffen zu viel, um zu schuetzen.
        assert "ulm" not in mg.zerlege("Neu-Ulm Systems")


class TestAusnahmen:
    def test_should_ignore_comments_and_blank_lines(self, tmp_path, monkeypatch):
        datei = tmp_path / "ausnahmen.txt"
        datei.write_text(
            "# Kommentar\n\nbeispielbegriff   # Begruendung\n", encoding="utf-8"
        )
        monkeypatch.setattr(mg, "AUSNAHMEN", datei)
        assert mg.ausnahmen() == {"beispielbegriff"}

    def test_should_return_empty_without_the_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mg, "AUSNAHMEN", tmp_path / "fehlt.txt")
        assert mg.ausnahmen() == set()


class TestPruefung:
    def test_should_find_a_protected_term_case_insensitively(self):
        zeilen = [("test.py", 3, 'vorgang = "Musterwerke-AV-2026"')]
        funde = mg._pruefe(zeilen, {"musterwerke-av-2026"})
        assert funde == [("test.py", 3, "musterwerke-av-2026")]

    def test_should_stay_silent_on_invented_data(self):
        zeilen = [("test.py", 1, 'vorgang = "vorgang-a"')]
        assert mg._pruefe(zeilen, {"musterwerke-av-2026"}) == []

    def test_should_report_a_line_only_once(self):
        # Zwei Treffer in derselben Zeile sind ein Befund, nicht zwei.
        zeilen = [("t.py", 1, "musterwerke und beispiel-ag")]
        funde = mg._pruefe(zeilen, {"musterwerke", "beispiel-ag"})
        assert len(funde) == 1
