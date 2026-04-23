import pytest


def test_prometheus_middleware_noop_without_package(rf, monkeypatch):
    from django.http import HttpResponse

    import iil_commons.monitoring.middleware as mod

    monkeypatch.setattr(mod, "_metrics_available", False)
    from iil_commons.monitoring.middleware import PrometheusMiddleware

    def get_response(request):
        return HttpResponse("ok")

    middleware = PrometheusMiddleware(get_response)
    response = middleware(rf.get("/"))
    assert response.status_code == 200


def test_metrics_view_without_package(rf):
    from iil_commons.monitoring.views import metrics_view

    try:
        import prometheus_client  # noqa: F401
        pytest.skip("prometheus_client is installed — skip no-package test")
    except ImportError:
        pass

    response = metrics_view(rf.get("/metrics/"))
    assert response.status_code == 503


def test_normalize_path():
    from iil_commons.monitoring.middleware import _normalize_path

    assert _normalize_path("/api/users/42/posts/7/") == "/api/users/{id}/posts/{id}/"
    assert _normalize_path("/livez/") == "/livez/"
    assert _normalize_path("/api/v1/items/") == "/api/v1/items/"
