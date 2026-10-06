"""Tests für tools/sevdesk/paperless.py + ``--kostenstelle`` in beleg_entwurf.py.

Owner-Konvention 2026-09-21: Paperless-Tags tragen Mandant (``edv``/``iil``) und
Kostenstelle (Name wie in sevdesk, optional mit ID ``name 123``). Namen/IDs hier
synthetisch — öffentliches Repo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import beleg_entwurf as be  # noqa: E402
import paperless as pl  # noqa: E402

KOSTENSTELLEN = [
    {"id": "111", "name": "wagen-a"},
    {"id": "222", "name": "wagen-b"},
]


def test_should_pick_mandant_from_exactly_one_mandant_tag():
    assert pl.mandant_aus_tags(["2026", "EDV", "wagen-a"]) == "edv"


def test_should_refuse_to_guess_mandant_when_none_or_both_tags_present():
    assert pl.mandant_aus_tags(["2026", "wagen-a"]) is None
    assert pl.mandant_aus_tags(["edv", "iil"]) is None


def test_should_resolve_cost_centre_by_tag_name_case_insensitive():
    k = pl.kostenstelle_aus_tags(["2026", "Wagen-A"], KOSTENSTELLEN)
    assert k == KOSTENSTELLEN[0]


def test_should_accept_tag_with_matching_id_suffix():
    assert pl.tag_zerlegen("wagen-a 111") == ("wagen-a", "111")
    assert pl.kostenstelle_aus_tags(["wagen-a 111"], KOSTENSTELLEN) == KOSTENSTELLEN[0]


def test_should_reject_tag_whose_id_does_not_match_the_name():
    """ID-Kollision ueber Mandanten: lieber nichts als das Falsche."""
    assert pl.kostenstelle_aus_tags(["wagen-a 222"], KOSTENSTELLEN) is None


def test_should_return_none_when_two_tags_name_cost_centres():
    assert pl.kostenstelle_aus_tags(["wagen-a", "wagen-b"], KOSTENSTELLEN) is None


def test_should_ignore_tags_that_are_no_cost_centre():
    assert pl.kostenstelle_aus_tags(["2026", "Auto", "edv"], KOSTENSTELLEN) is None


def _client() -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path.endswith("/CostCentre")
        return httpx.Response(200, json={"objects": KOSTENSTELLEN})

    return httpx.Client(
        base_url="https://sevdesk.test/api/v1", transport=httpx.MockTransport(handler)
    )


def test_should_resolve_cost_centre_to_sevdesk_reference():
    assert be.kostenstelle_aufloesen(_client(), "wagen-b") == {
        "id": "222",
        "objectName": "CostCentre",
    }


def test_should_leave_cost_centre_empty_when_unknown(capsys):
    assert be.kostenstelle_aufloesen(_client(), "wagen-z") is None
    assert "Kostenstelle 'wagen-z'" in capsys.readouterr().out


# ── Lieferanten-Kontakt mit Bankdaten (#3342) ──────────────────────────────

RECHNUNGSTEXT = """Musterwerkstatt GmbH  Steuernummer: 123/456/78901
USt-IdNr.: DE 123456789
Bankverbindung: Musterbank
IBAN: DE89 3704 0044 0532 0130 00 - BIC
COBADEFFXXX
"""


def test_should_extract_bank_and_tax_ids_from_invoice_text():
    d = pl.bankdaten_aus_text(RECHNUNGSTEXT)
    assert d == {
        "iban": "DE89370400440532013000",
        "bic": "COBADEFFXXX",
        "ustid": "DE123456789",
        "steuernummer": "123/456/78901",
    }


def test_should_omit_fields_that_are_not_in_the_text():
    assert pl.bankdaten_aus_text("Rechnung ohne Bankdaten, Betrag 10,00 EUR") == {}


def _kontakt_client(kontakte: list[dict], angelegt: list[dict]) -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "GET" and req.url.path.endswith("/Contact"):
            return httpx.Response(200, json={"objects": kontakte})
        if req.method == "POST" and req.url.path.endswith("/Contact"):
            import json

            body = json.loads(req.content)
            angelegt.append(body)
            return httpx.Response(201, json={"objects": {"id": "k-neu", **body}})
        raise AssertionError(req.url.path)

    return httpx.Client(
        base_url="https://sevdesk.test/api/v1", transport=httpx.MockTransport(handler)
    )


def test_should_find_contact_by_substring_ignoring_case():
    kontakte = [
        {"id": "1", "name": "Musterwerkstatt GmbH"},
        {"id": "2", "name": "Anderer"},
    ]
    assert (
        be.kontakt_finden(_kontakt_client(kontakte, []), "musterwerkstatt")["id"] == "1"
    )


def test_should_not_guess_when_two_contacts_match():
    kontakte = [{"id": "1", "name": "Muster A"}, {"id": "2", "name": "Muster B"}]
    assert be.kontakt_finden(_kontakt_client(kontakte, []), "Muster") is None


def test_should_create_supplier_contact_with_bank_data():
    angelegt: list[dict] = []
    k = be.kontakt_anlegen(
        _kontakt_client([], angelegt),
        "Musterwerkstatt GmbH",
        {
            "iban": "DE89370400440532013000",
            "bic": "COBADEFFXXX",
            "ustid": "DE123456789",
        },
    )
    assert k["id"] == "k-neu"
    assert angelegt[0]["category"] == {
        "id": be.KATEGORIE_LIEFERANT,
        "objectName": "Category",
    }
    assert angelegt[0]["bankAccount"] == "DE89370400440532013000"
    assert angelegt[0]["bankNumber"] == "COBADEFFXXX"
    assert angelegt[0]["vatNumber"] == "DE123456789"
    assert "taxNumber" not in angelegt[0]
