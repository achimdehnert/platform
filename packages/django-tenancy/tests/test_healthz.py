"""Tests for health check endpoints."""

import pytest
from django.test import Client

from django_tenancy.healthz import HEALTH_PATHS


class TestHealthPaths:
    """Tests for HEALTH_PATHS constant."""

    def test_should_contain_livez(self):
        assert "/livez/" in HEALTH_PATHS

    def test_should_contain_healthz(self):
        assert "/healthz/" in HEALTH_PATHS

    def test_should_contain_health_compat(self):
        assert "/health/" in HEALTH_PATHS

    def test_should_be_frozen(self):
        assert isinstance(HEALTH_PATHS, frozenset)


@pytest.mark.django_db
class TestLiveness:
    """Tests for liveness endpoint."""

    def test_should_return_200(self):
        client = Client()
        response = client.get("/livez/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_should_reject_post(self):
        client = Client()
        response = client.post("/livez/")
        assert response.status_code == 405


@pytest.mark.django_db
class TestReadiness:
    """Tests for readiness endpoint."""

    def test_should_return_200_with_db_check(self):
        client = Client()
        response = client.get("/healthz/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["checks"]["database"]["status"] == "ok"
        assert "latency_ms" in data["checks"]["database"]
