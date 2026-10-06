"""Tests für tools/sevdesk/verbuchen_wache.py — Paperless-Tag ``verbuchen`` → Beleg.

Nur die reine Planlogik (kein sevdesk, kein Paperless, kein ssh). Texte,
Lieferanten und Regeln sind synthetisch — öffentliches Repo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import verbuchen_wache as vw  # noqa: E402

TEXT = """Musterwerkstatt GmbH
Rechnungs-Nr.: 4711
Belegdatum: 09.08.2026
Pos. Bezeichnung Betrag EUR
1 Arbeit 100,00
Summe: 100,00
19,00 % USt. auf EUR 100,00: 19,00
Endbetrag: 119,00
IBAN: DE89 3704 0044 0532 0130 00 BIC COBADEFFXXX
"""
REGELN = [
    {"muster": "musterwerkstatt", "konto": "6540", "bezeichnung": "KFZ-Reparaturen"}
]
KOSTENSTELLEN = [{"id": "1", "name": "wagen-a"}]


def _dok(**extra):
    d = {
        "id": 1,
        "title": "2026-08-09 - Musterwerkstatt - Rechnung",
        "tags": ["2026", "edv", "wagen-a"],
        "correspondent": None,
        "content": TEXT,
    }
    d.update(extra)
    return d


def test_should_build_a_complete_plan_from_text_tags_and_rules():
    plan = vw.plan_fuer(_dok(), REGELN, KOSTENSTELLEN)
    assert plan["mandant"] == "edv"
    assert (plan["brutto"], plan["steuer"], plan["datum"]) == (
        "119.00",
        "19.00",
        "2026-08-09",
    )
    assert plan["beschreibung"] == "Rechnung 4711"
    assert plan["taxrule"] == "9"
    assert plan["konto"] == "6540"
    assert plan["kostenstelle"] == "wagen-a"
    assert plan["bankdaten"]["iban"] == "DE89370400440532013000"


def test_should_prefer_the_paperless_correspondent_as_supplier():
    plan = vw.plan_fuer(
        _dok(correspondent="Musterwerkstatt GmbH"), REGELN, KOSTENSTELLEN
    )
    assert plan["lieferant"] == "Musterwerkstatt GmbH"


def test_should_leave_account_empty_without_an_owner_rule():
    plan = vw.plan_fuer(_dok(), [], KOSTENSTELLEN)
    assert plan["konto"] is None


def test_should_not_guess_between_two_matching_rules():
    regeln = REGELN + [{"muster": "werkstatt", "konto": "6530"}]
    assert vw.konto_aus_regeln("Musterwerkstatt GmbH", "Rechnung 4711", regeln) is None


def test_should_mark_document_unclear_without_mandant_tag():
    with pytest.raises(vw.Unklar, match="Mandanten-Tag"):
        vw.plan_fuer(_dok(tags=["2026"]), REGELN, KOSTENSTELLEN)


def test_should_mark_document_unclear_without_amount():
    with pytest.raises(vw.Unklar, match="Bruttobetrag"):
        vw.plan_fuer(_dok(content="Hallo, kein Betrag hier"), REGELN, KOSTENSTELLEN)


def test_should_refuse_foreign_currency():
    text = TEXT.replace("EUR", "USD").replace("Endbetrag: 119,00", "Endbetrag: $119.00")
    with pytest.raises(vw.Unklar, match="Waehrung"):
        vw.plan_fuer(_dok(content=text), REGELN, KOSTENSTELLEN)


def test_should_write_a_note_that_names_missing_account():
    plan = vw.plan_fuer(_dok(), [], KOSTENSTELLEN)
    text = vw.notiz_fertig(plan, {"beleg_id": "v-1", "dublette": False})
    assert (
        "Beleg v-1 angelegt" in text
        and "Konto LEER" in text
        and "Kostenstelle wagen-a" in text
    )


def test_should_say_when_the_voucher_already_existed():
    plan = vw.plan_fuer(_dok(), REGELN, KOSTENSTELLEN)
    assert "bestand schon" in vw.notiz_fertig(
        plan, {"beleg_id": "v-9", "dublette": True}
    )


def test_should_match_account_rule_against_the_letterhead_when_supplier_is_only_first_line():
    """Ohne Korrespondent ist der Lieferant die erste Zeile; der Regelname steht
    im Briefkopf darunter (Echtprobe 2026-09-21)."""
    text = "KFZ - Meisterbetrieb\nHerrn Muster Nadlerhof, Musterweg 1\n" + TEXT.replace(
        "Musterwerkstatt GmbH\n", ""
    )
    regeln = [{"muster": "nadlerhof", "konto": "6540"}]
    plan = vw.plan_fuer(_dok(content=text), regeln, KOSTENSTELLEN)
    assert plan["lieferant"] == "KFZ - Meisterbetrieb"
    assert plan["konto"] == "6540"
    assert plan["korrespondent_fehlt"] is True


def test_should_ask_for_a_correspondent_in_the_note_when_supplier_came_from_text():
    plan = vw.plan_fuer(_dok(), REGELN, KOSTENSTELLEN)
    assert "Korrespondent in Paperless setzen" in vw.notiz_fertig(
        plan, {"beleg_id": "v-1"}
    )
    plan = vw.plan_fuer(
        _dok(correspondent="Musterwerkstatt GmbH"), REGELN, KOSTENSTELLEN
    )
    assert "Korrespondent" not in vw.notiz_fertig(plan, {"beleg_id": "v-1"})
