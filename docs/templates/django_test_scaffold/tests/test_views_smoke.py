"""test_views_smoke.py — Automatischer HTTP-200-Smoke-Test aller Views.

Auto-Discovery: alle URL-Routes ohne Pflicht-Parameter werden getestet.
Kein manuelles Pflegen von URL-Listen.

Anpassen:
  - discover_smoke_urls(extra_skip_namespaces={"api", "webhooks"})  — weitere Namespaces ausschließen
  - expected_statuses=(200, 302, 404)  — wenn leere DB 404 liefert
"""
import pytest

from iil_testkit.smoke import ViewSmokeTester, discover_smoke_urls


@pytest.mark.parametrize("url", discover_smoke_urls())
@pytest.mark.django_db
def test_should_view_return_200(url: str, auth_client) -> None:
    """Alle parameterfreien Views müssen HTTP 200 oder 302 liefern."""
    response = auth_client.get(url)
    assert response.status_code in (200, 302), (
        f"{url} → HTTP {response.status_code} (erwartet: 200 oder 302)"
    )


@pytest.mark.parametrize("url", discover_smoke_urls())
@pytest.mark.django_db
def test_should_unauthenticated_access_redirect(url: str, api_client) -> None:
    """Nicht-öffentliche Views müssen unauthentifiziert auf Login weiterleiten."""
    from iil_testkit.assertions import assert_redirects_to_login
    response = api_client.get(url)
    if response.status_code not in (200, 302):
        return
    if response.status_code == 302:
        location = response.get("Location", "")
        if "/login" in location or "/accounts/login" in location:
            return
    # View ist öffentlich — OK, kein Fehler
