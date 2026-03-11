def test_rate_limit_decorator_allows_first_request(rf):
    from django.http import HttpResponse

    from iil_commons.ratelimit.decorators import rate_limit

    @rate_limit(requests=5, window=60)
    def my_view(request):
        return HttpResponse("ok")

    response = my_view(rf.get("/"))
    assert response.status_code == 200
    assert response["X-RateLimit-Limit"] == "5"


def test_rate_limit_decorator_blocks_after_limit(rf):
    from django.http import HttpResponse

    from iil_commons.ratelimit.decorators import rate_limit

    @rate_limit(requests=2, window=60)
    def my_view(request):
        return HttpResponse("ok")

    request = rf.get("/", REMOTE_ADDR="10.0.0.1")
    my_view(request)
    my_view(request)
    response = my_view(request)
    assert response.status_code == 429
    assert "Retry-After" in response


def test_rate_limit_middleware_passes_by_default(rf, settings):
    from django.http import HttpResponse

    from iil_commons.ratelimit.middleware import RateLimitMiddleware

    settings.IIL_COMMONS = {}

    def get_response(request):
        return HttpResponse("ok")

    middleware = RateLimitMiddleware(get_response)
    response = middleware(rf.get("/"))
    assert response.status_code == 200


def test_rate_limit_middleware_blocks_path(rf, settings):
    from django.http import HttpResponse

    from iil_commons.ratelimit.middleware import RateLimitMiddleware

    settings.IIL_COMMONS = {
        "RATE_LIMIT_PATHS": {"/api/": "2/h"},
    }

    def get_response(request):
        return HttpResponse("ok")

    middleware = RateLimitMiddleware(get_response)
    request = rf.get("/api/data/", REMOTE_ADDR="10.0.0.2")
    middleware(request)
    middleware(request)
    response = middleware(request)
    assert response.status_code == 429


def test_parse_rate():
    from iil_commons.ratelimit.middleware import _parse_rate

    assert _parse_rate("100/h") == (100, 3600)
    assert _parse_rate("10/m") == (10, 60)
    assert _parse_rate("5/s") == (5, 1)
    assert _parse_rate("1000/d") == (1000, 86400)
    assert _parse_rate("invalid") == (100, 3600)
