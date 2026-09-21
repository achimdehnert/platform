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
