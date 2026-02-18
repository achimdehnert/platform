"""HTMX utilities for Django views (ADR-048).

Provides:
- is_htmx_request(): Portable HTMX detection (no django_htmx dependency)
- HtmxResponseMixin: CBV mixin for partial/full template switching
- HtmxErrorMiddleware: Convert 4xx/5xx into HTMX-safe toast notifications

All code uses raw header detection for portability across apps.
Apps with django_htmx installed MAY use request.htmx in app-specific code,
but shared middleware and mixins MUST NOT depend on it.
"""

import json
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse


def is_htmx_request(request: HttpRequest) -> bool:
    """Portable HTMX detection. Works with or without django_htmx."""
    return request.headers.get("HX-Request") == "true"


class HtmxResponseMixin:
    """Mixin for CBVs that return partials for HTMX requests.

    Set ``partial_template_name`` to the HTMX partial template.
    The full template is resolved via standard ``get_template_names()``.

    Example::

        class TripListView(HtmxResponseMixin, LoginRequiredMixin, ListView):
            model = Trip
            template_name = "trips/trip_list.html"
            partial_template_name = "trips/partials/_trip_list.html"
    """

    partial_template_name: str = ""

    def get_template_names(self) -> list[str]:
        """Return partial template for HTMX requests, full otherwise."""
        if is_htmx_request(self.request):
            if not self.partial_template_name:
                raise ImproperlyConfigured(
                    f"{self.__class__.__name__} requires partial_template_name"
                )
            return [self.partial_template_name]
        return super().get_template_names()


ERROR_MESSAGES: dict[int, str] = {
    400: "Bad request.",
    403: "Permission denied.",
    404: "Resource not found.",
    405: "Method not allowed.",
    409: "Conflict.",
    429: "Too many requests. Please wait.",
    500: "Internal server error. Please try again.",
    502: "Service temporarily unavailable.",
    503: "Service temporarily unavailable.",
}


class HtmxErrorMiddleware:
    """Convert 4xx/5xx into HTMX-safe responses with toast notifications.

    Works without django_htmx -- uses raw header detection.
    Skips 422 responses (form validation errors, see HP-006).

    Install AFTER TenantMiddleware and auth middleware::

        MIDDLEWARE = [
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            # ... auth middleware ...
            "platform_context.middleware.SubdomainTenantMiddleware",
            "platform_context.htmx.HtmxErrorMiddleware",
            # ...
        ]
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and intercept errors for HTMX requests."""
        response = self.get_response(request)

        if not is_htmx_request(request):
            return response

        if response.status_code == 422:
            return response

        if response.status_code >= 400:
            response["HX-Reswap"] = "none"
            response["HX-Trigger"] = json.dumps({
                "showToast": {
                    "level": "error" if response.status_code >= 500 else "warning",
                    "message": ERROR_MESSAGES.get(
                        response.status_code, "An error occurred."
                    ),
                }
            })

        return response
