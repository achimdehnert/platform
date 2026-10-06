"""Tests fuer die Deckblatt-Meta-Tabelle (deckblatt_meta.meta_rows).

Das meiki-Deckblatt stempelt jedes PDF mit "Vertraulich – nur fuer Konsortium
MEiKI". An einen Hersteller oder eine Behoerde ausserhalb des Konsortiums geht
damit ein Dokument, dessen Seite 1 dem Empfaenger sagt, er duerfe es nicht
haben — dreimal passiert (2026-09-22 zweimal, 2026-09-23 erneut am
PROSOZ-Anhang, obwohl das Profil `meiki-extern` dafuer angelegt worden war:
es setzte nur Kopf- und Deckblattzeile, nicht die Meta-Tabelle).

Die Tests pruefen beide Richtungen: der Stempel faellt weg, wenn ein Profil
`meta_vertraulichkeit: ""` setzt — und er steht da, wenn keines es tut
(Positivkontrolle, sonst misst der Test nichts).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODUL = Path(__file__).resolve().parents[1] / "deckblatt_meta.py"
_spec = importlib.util.spec_from_file_location("deckblatt_meta", _MODUL)
pa = importlib.util.module_from_spec(_spec)
sys.modules["deckblatt_meta"] = pa
_spec.loader.exec_module(pa)

_META = {"stand": "2026-09-23 · erster Aufschlag"}


def _labels(rows):
    return [label for label, _ in rows]


def test_should_stamp_confidentiality_for_the_default_meiki_profile():
    rows = pa.meta_rows(_META, {"meta_template": "meiki"}, "konzept")
    assert ("Vertraulichkeit", pa.DEFAULT_VERTRAULICHKEIT) in rows


def test_should_drop_confidentiality_when_the_profile_clears_it():
    design = {"meta_template": "meiki", "meta_vertraulichkeit": ""}
    rows = pa.meta_rows(_META, design, "prosoz-anforderungen")
    assert "Vertraulichkeit" not in _labels(rows)
    # Der Rest des Deckblatts bleibt — sonst waere die Tabelle einfach leer.
    assert _labels(rows) == ["Dokument-ID", "Konsortium", "Stand", "Projektlaufzeit"]


def test_should_use_a_profile_specific_confidentiality_text():
    design = {"meta_template": "meiki", "meta_vertraulichkeit": "Nur fuer den Kreistag"}
    rows = pa.meta_rows(_META, design, "vorlage")
    assert ("Vertraulichkeit", "Nur fuer den Kreistag") in rows


def test_should_return_no_rows_without_a_stand_line():
    assert pa.meta_rows({}, {"meta_template": "meiki"}, "irgendwas") == []


def test_should_keep_the_iil_offer_rows():
    meta = {"angebot_nr": "2026-014", "datum": "2026-09-23", "gueltig_bis": "2026-10-31"}
    rows = pa.meta_rows(meta, {"meta_template": "iil"}, "angebot")
    assert _labels(rows) == ["Angebot-Nr.", "Datum", "Gültig bis", "Auftragnehmer"]


def test_should_not_claim_a_contractor_role_without_offer_context():
    rows = pa.meta_rows({"status": "Entwurf"}, {"meta_template": "iil"}, "pruefbogen")
    assert "Auftragnehmer" not in _labels(rows)


def test_should_prefer_the_document_target_group_over_the_profile_default():
    design = {"zielgruppe_default": "Externe Adressaten"}
    assert pa.cover_zielgruppe({"zielgruppe": "Rechtsamt"}, design) == "Rechtsamt"
    assert pa.cover_zielgruppe({}, design) == "Externe Adressaten"
    assert pa.cover_zielgruppe({}, {}) == pa.DEFAULT_ZIELGRUPPE
