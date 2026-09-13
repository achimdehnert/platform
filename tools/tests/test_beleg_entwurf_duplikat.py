"""Dedup-Regel von tools/sevdesk/beleg_entwurf.py — Gegenrichtung nur fuer Kennungen mit Ziffer.

Realfall 2026-09-13: ein Altbeleg mit description "scribd" (ohne Ziffer) steckte in
jeder Eigenbeleg-Kennung "EIGENBELEG-SCRIBD-<datum>" und meldete 13 falsche
Dubletten. Alle Werte synthetisch (oeffentliches Repo).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import beleg_entwurf as be  # noqa: E402


def _bestand(*beschreibungen: str) -> list[dict]:
    return [{"id": str(i), "description": b} for i, b in enumerate(beschreibungen, 1)]


def test_should_match_number_inside_grown_description():
    assert (
        be.duplikat(
            _bestand("Anbieter Invoice ABCD1234-0017 — Zeitraum"), "ABCD1234-0017"
        )
        == "1"
    )


def test_should_match_existing_number_inside_new_key_when_it_has_digits():
    assert (
        be.duplikat(_bestand("R-2026-000123"), "EIGENBELEG-R-2026-000123-KOPIE") == "1"
    )


def test_should_not_treat_word_only_description_as_duplicate():
    bestand = _bestand("scribd", "scribd ", "anbieter")
    assert be.duplikat(bestand, "EIGENBELEG-SCRIBD-2026-08-21") is None


def test_should_still_match_exact_word_only_description():
    assert be.duplikat(_bestand("scribd"), "scribd") == "1"


def test_should_keep_short_keys_exact_only():
    assert be.duplikat(_bestand("0025 Rechnung"), "0025") is None
