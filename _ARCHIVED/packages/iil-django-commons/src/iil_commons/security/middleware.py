import logging
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware:
    """Adds security headers to every response.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: (restrictive defaults)
    - Content-Security-Policy: (configurable via IIL_COMMONS)

    Override CSP via settings:
        IIL_COMMONS = {
            "CSP_POLICY": "default-src 'self'; ...",
        }
    Set to None/empty string to disable CSP header.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        self._add_headers(response)
        return response

    def _add_headers(self, response: HttpResponse) -> None:
        for header, value in _SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value

        if "Content-Security-Policy" not in response:
            from iil_commons.settings import get_setting

            csp = get_setting("CSP_POLICY", _DEFAULT_CSP)
            if csp:
                response["Content-Security-Policy"] = csp
