"""Tests fuer die gemeinsame Lesart von Mail-Referenzen (platform#2592 K2/K3).

Geprueft wird die EINE Lesart, die Renderer, Verankerung und Ordner-Pruefer
teilen — nicht drei Kopien davon.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

rf = pytest.importorskip("referenzen")


class TestFinde:
    def test_should_find_a_number_with_its_folder(self):
        (ref,) = rf.finde("Klimm (INBOX #164024) meldet")
        assert (ref.uid, ref.ordner, ref.slug) == ("164024", "INBOX", "inbox")

    def test_should_reach_the_folder_through_quotes_and_a_bracket(self):
        (ref,) = rf.finde("Beleg im Ordner 'Gesendete Objekte' (#34349).")
        assert ref.ordner == "Gesendete Objekte"
        assert ref.slug == "gesendete-objekte"

    def test_should_read_the_escaped_form_the_renderer_passes(self):
        (ref,) = rf.finde("Ordner &#x27;Gesendete Objekte&#x27; (#34349)")
        assert ref.ordner == "Gesendete Objekte"

    def test_should_not_borrow_a_folder_from_another_sentence_part(self):
        refs = rf.finde(
            "Vorfassung UID 23588 in Geloeschte Objekte verschoben, gueltig ist UID 23589."
        )
        assert [(r.uid, r.ordner) for r in refs] == [("23588", None), ("23589", None)]

    def test_should_apply_the_folder_to_a_whole_enumeration(self):
        """Reale Formen aus dem Ledger (Bestandsaufnahme 2026-09-01): drei Nummern
        hinter EINEM Ordner, ein Bereich mit `bis`, zwei mit Schraegstrich."""
        refs = rf.finde("frei am 24.08. (INBOX #164084, #164091, #164109)")
        assert [r.ordner for r in refs] == ["INBOX"] * 3
        refs = rf.finde("abgelegt (Entwuerfe #23761 bis #23780)")
        assert [r.ordner for r in refs] == ["Entwürfe", "Entwürfe"] or [
            r.ordner for r in refs
        ] == ["Entwuerfe", "Entwuerfe"]
        refs = rf.finde("'Gesendete Elemente' (#29644/#29645, 28.08.)")
        assert [r.ordner for r in refs] == ["Gesendete Elemente"] * 2

    def test_should_ignore_github_references(self):
        assert rf.finde("korrigiert in meiki-lra/meiki-hub#146 und platform#2183") == []

    def test_should_keep_positions_of_the_original_text_next_to_a_github_reference(
        self,
    ):
        text = "platform#2183 dazu INBOX #164024"
        (ref,) = rf.finde(text)
        assert text[ref.start : ref.end] == "#164024"

    def test_should_find_nothing_in_prose_without_numbers(self):
        assert rf.finde("Telefonat mit Bittner, kein Schriftwechsel") == []


class TestSchluessel:
    def test_should_carry_the_folder_when_named(self):
        assert rf.schluessel("hnu", "entwuerfe", "23611") == "hnu-entwuerfe-23611"

    def test_should_omit_the_folder_when_absent(self):
        assert rf.schluessel("hnu", None, "23611") == "hnu-23611"

    def test_should_offer_the_bare_key_as_second_candidate_for_a_folder_reference(self):
        (ref,) = rf.finde("Entwuerfe #23611")
        assert rf.schluessel_kandidaten("hnu", ref) == (
            "hnu-entwuerfe-23611",
            "hnu-23611",
        )

    def test_should_offer_only_the_bare_key_without_a_folder(self):
        (ref,) = rf.finde("UID 23611")
        assert rf.schluessel_kandidaten("hnu", ref) == ("hnu-23611",)


class TestDatum:
    def test_should_read_the_leading_date(self):
        assert rf.eintrag_datum("2026-08-21 (/mailcheck): kein Eingang") == date(
            2026, 8, 21
        )

    def test_should_read_a_date_behind_the_neu_marker(self):
        assert rf.eintrag_datum("NEU 2026-08-13: Bittner schickt") == date(2026, 8, 13)

    def test_should_return_none_without_a_date(self):
        assert rf.eintrag_datum("Bittner schickt zwei Vorlagen") is None


def _ledger(*notizen: str) -> dict:
    return {
        "vorgaenge": [
            {"nr": i + 1, "konto": "hnu", "notiz": n} for i, n in enumerate(notizen)
        ]
    }


class TestPruefeOrdner:
    def test_should_flag_a_bare_number_after_the_cutoff(self):
        ab, davor = rf.pruefe_ordner(_ledger("2026-09-05: Entwurf UID 23611 liegt"), {})
        assert [(x.nr, x.uid) for x in ab] == [(1, "23611")]
        assert davor == []

    def test_should_count_but_not_blame_before_the_cutoff(self):
        ab, davor = rf.pruefe_ordner(_ledger("2026-08-10: Entwurf UID 23611 liegt"), {})
        assert ab == []
        assert len(davor) == 1

    def test_should_pass_a_number_with_its_folder(self):
        ab, davor = rf.pruefe_ordner(_ledger("2026-09-05: Entwuerfe #23611 liegt"), {})
        assert (ab, davor) == ([], [])

    def test_should_look_into_the_capped_archive_too(self):
        archiv = {"1": ["2026-09-05: alt UID 100 gekappt"]}
        ab, _ = rf.pruefe_ordner(_ledger("2026-09-06: INBOX #200"), archiv)
        assert [(x.eintrag, x.uid) for x in ab] == [(1, "100")]

    def test_should_name_the_entry_within_the_case(self):
        ab, _ = rf.pruefe_ordner(
            _ledger("2026-09-05: ok INBOX #1001 | 2026-09-06: UID 2002"), {}
        )
        assert [(x.nr, x.eintrag) for x in ab] == [(1, 2)]


class TestCli:
    def test_should_exit_nonzero_on_a_violation_and_name_it(self, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger("2026-09-05: UID 23611 wartet")), "utf-8")
        lauf = subprocess.run(
            [
                sys.executable,
                str(Path(rf.__file__)),
                "--pruefe-ordner",
                "--ledger",
                str(ledger),
                "--verlauf-archiv",
                str(tmp_path / "fehlt.json"),
            ],
            capture_output=True,
            text=True,
        )
        assert lauf.returncode == 1
        assert "#1-1 2026-09-05 UID 23611" in lauf.stdout

    def test_should_exit_zero_on_a_clean_ledger(self, tmp_path):
        ledger = tmp_path / "l.json"
        ledger.write_text(json.dumps(_ledger("2026-09-05: INBOX #1001")), "utf-8")
        lauf = subprocess.run(
            [
                sys.executable,
                str(Path(rf.__file__)),
                "--pruefe-ordner",
                "--ledger",
                str(ledger),
            ],
            capture_output=True,
            text=True,
        )
        assert lauf.returncode == 0
        assert "0 ab 2026-09-01" in lauf.stdout
