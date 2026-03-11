import json

import pytest


@pytest.mark.django_db
def test_liveness(rf):
    from iil_commons.health.views import liveness

    response = liveness(rf.get("/livez/"))
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["status"] == "alive"


@pytest.mark.django_db
def test_readiness_db_ok(rf):
    from iil_commons.health.views import readiness

    response = readiness(rf.get("/healthz/"))
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["status"] == "ok"
    assert "db" in data["checks"]
    assert data["checks"]["db"]["status"] == "ok"
    assert "latency_ms" in data["checks"]["db"]


@pytest.mark.django_db
def test_readiness_db_check_directly():
    from iil_commons.health.checks import DatabaseCheck

    check = DatabaseCheck()
    ok, detail = check.check()
    assert ok is True
    assert detail == "ok"


def test_readiness_unknown_check_skipped(rf, settings):
    settings.IIL_COMMONS = {"HEALTH_CHECKS": ["nonexistent"]}
    from iil_commons.health.views import readiness

    response = readiness(rf.get("/readyz/"))
    assert response.status_code == 200
