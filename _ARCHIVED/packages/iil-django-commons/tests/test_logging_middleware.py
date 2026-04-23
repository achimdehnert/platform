def test_correlation_id_generated(rf):
    from django.http import HttpResponse

    from iil_commons.logging.middleware import CorrelationIDMiddleware, get_correlation_id

    def get_response(request):
        return HttpResponse()

    middleware = CorrelationIDMiddleware(get_response)
    request = rf.get("/")
    response = middleware(request)

    correlation_id = get_correlation_id(request)
    assert correlation_id != ""
    assert response["X-Correlation-ID"] == correlation_id


def test_correlation_id_forwarded(rf):
    from django.http import HttpResponse

    from iil_commons.logging.middleware import CorrelationIDMiddleware, get_correlation_id

    def get_response(request):
        return HttpResponse()

    middleware = CorrelationIDMiddleware(get_response)
    request = rf.get("/", HTTP_X_CORRELATION_ID="my-custom-id")
    middleware(request)

    assert get_correlation_id(request) == "my-custom-id"


def test_request_log_middleware_runs(rf):
    from django.http import HttpResponse

    from iil_commons.logging.middleware import RequestLogMiddleware

    def get_response(request):
        return HttpResponse()

    middleware = RequestLogMiddleware(get_response)
    request = rf.get("/some/path/")
    response = middleware(request)
    assert response.status_code == 200
