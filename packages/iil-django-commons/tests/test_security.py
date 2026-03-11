def test_security_headers_added(rf):
    from django.http import HttpResponse

    from iil_commons.security.middleware import SecurityHeadersMiddleware

    def get_response(request):
        return HttpResponse("ok")

    middleware = SecurityHeadersMiddleware(get_response)
    response = middleware(rf.get("/"))

    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["X-XSS-Protection"] == "1; mode=block"
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
    assert "Content-Security-Policy" in response


def test_security_headers_not_overwritten(rf):
    from django.http import HttpResponse

    from iil_commons.security.middleware import SecurityHeadersMiddleware

    def get_response(request):
        r = HttpResponse("ok")
        r["X-Frame-Options"] = "SAMEORIGIN"
        return r

    middleware = SecurityHeadersMiddleware(get_response)
    response = middleware(rf.get("/"))
    assert response["X-Frame-Options"] == "SAMEORIGIN"


def test_custom_csp_from_settings(rf, settings):
    from django.http import HttpResponse

    from iil_commons.security.middleware import SecurityHeadersMiddleware

    settings.IIL_COMMONS = {"CSP_POLICY": "default-src 'none'"}

    def get_response(request):
        return HttpResponse("ok")

    middleware = SecurityHeadersMiddleware(get_response)
    response = middleware(rf.get("/"))
    assert response["Content-Security-Policy"] == "default-src 'none'"


def test_csp_disabled_when_empty(rf, settings):
    from django.http import HttpResponse

    from iil_commons.security.middleware import SecurityHeadersMiddleware

    settings.IIL_COMMONS = {"CSP_POLICY": ""}

    def get_response(request):
        return HttpResponse("ok")

    middleware = SecurityHeadersMiddleware(get_response)
    response = middleware(rf.get("/"))
    assert "Content-Security-Policy" not in response
