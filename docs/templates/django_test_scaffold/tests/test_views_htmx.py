"""test_views_htmx.py — HTMX-Partials und data-testid Enforcement.

Prüft:
  1. HTMX-Responses liefern keine vollständige HTML-Seite (ADR-048)
  2. Alle hx-* Elemente haben data-testid (ADR-048)

Anpassen: HTMX_URLS mit den tatsächlichen HTMX-Endpoints des Repos füllen.
Nur URLs eintragen die auf HX-Request reagieren (partials liefern).
"""
import pytest

from iil_testkit.assertions import assert_data_testids, assert_htmx_response


HTMX_URLS: list[str] = [
    # Hier HTMX-Endpoints eintragen die partials liefern:
    # "/dashboard/items/",
    # "/projects/list/",
]


@pytest.mark.parametrize("url", HTMX_URLS)
@pytest.mark.django_db
def test_should_htmx_response_be_fragment(url: str, auth_client) -> None:
    """HTMX-Endpoints müssen Fragmente liefern, keine vollen Seiten."""
    response = auth_client.get(url, HTTP_HX_REQUEST="true")
    assert_htmx_response(response)


@pytest.mark.parametrize("url", HTMX_URLS)
@pytest.mark.django_db
def test_should_htmx_elements_have_data_testid(url: str, auth_client) -> None:
    """Alle hx-* Elemente müssen data-testid haben (ADR-048)."""
    response = auth_client.get(url)
    assert_data_testids(response)
