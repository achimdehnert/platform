from django.http import HttpRequest, HttpResponse


def metrics_view(request: HttpRequest) -> HttpResponse:
    """Expose Prometheus metrics at /metrics/.

    Add to urls.py:
        from iil_commons.monitoring.views import metrics_view
        urlpatterns += [path("metrics/", metrics_view)]
    """
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        data = generate_latest()
        return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return HttpResponse(
            "prometheus_client not installed",
            content_type="text/plain",
            status=503,
        )
