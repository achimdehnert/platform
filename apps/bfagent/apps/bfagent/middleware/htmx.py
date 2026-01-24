"""
BF Agent HTMX Middleware - Phase 1: Core Implementation
SAFETY-FIRST: Non-breaking, additive-only functionality
"""

import logging
from typing import Any, Callable, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class HTMXRequest:
    """Enhanced request object with HTMX capabilities"""

    def __init__(self, request: HttpRequest):
        self.request = request
        self._htmx_headers = {}
        self._parse_htmx_headers()

    def _parse_htmx_headers(self):
        """Parse all HTMX-related headers from request"""
        # Safety check for META attribute
        if not hasattr(self.request, "META") or self.request.META is None:
            return

        htmx_header_mapping = {
            "HX-Request": "HTTP_HX_REQUEST",
            "HX-Trigger": "HTTP_HX_TRIGGER",
            "HX-Trigger-Name": "HTTP_HX_TRIGGER_NAME",
            "HX-Target": "HTTP_HX_TARGET",
            "HX-Current-URL": "HTTP_HX_CURRENT_URL",
            "HX-Prompt": "HTTP_HX_PROMPT",
            "HX-Boosted": "HTTP_HX_BOOSTED",
            "HX-History-Restore-Request": "HTTP_HX_HISTORY_RESTORE_REQUEST",
        }

        for header_name, meta_key in htmx_header_mapping.items():
            value = self.request.META.get(meta_key)
            if value:
                self._htmx_headers[header_name] = value

    @property
    def is_htmx(self) -> bool:
        """Check if this is an HTMX request"""
        return "HX-Request" in self._htmx_headers

    @property
    def htmx_trigger(self) -> Optional[str]:
        """Get the HTMX trigger element ID"""
        return self._htmx_headers.get("HX-Trigger")

    @property
    def htmx_trigger_name(self) -> Optional[str]:
        """Get the HTMX trigger name"""
        return self._htmx_headers.get("HX-Trigger-Name")

    @property
    def htmx_target(self) -> Optional[str]:
        """Get the HTMX target element ID"""
        return self._htmx_headers.get("HX-Target")

    @property
    def htmx_current_url(self) -> Optional[str]:
        """Get the current URL from HTMX"""
        return self._htmx_headers.get("HX-Current-URL")

    @property
    def is_boosted(self) -> bool:
        """Check if this is a boosted request"""
        return "HX-Boosted" in self._htmx_headers

    @property
    def is_history_restore(self) -> bool:
        """Check if this is a history restore request"""
        return "HX-History-Restore-Request" in self._htmx_headers

    def get_htmx_prompt(self) -> Optional[str]:
        """Get the prompt value if present"""
        return self._htmx_headers.get("HX-Prompt")

    def get_all_htmx_headers(self) -> dict:
        """Get all HTMX headers as dict"""
        return self._htmx_headers.copy()


class HTMXMiddleware(MiddlewareMixin):
    """
    Phase 1: Core HTMX Middleware

    SAFETY FEATURES:
    - Only ADDS functionality, never removes
    - Preserves all existing request/response behavior
    - Optional activation via settings
    - Comprehensive logging for debugging
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        super().__init__(get_response)
        self.enabled = getattr(settings, "HTMX_MIDDLEWARE_ENABLED", True)
        self.debug = getattr(settings, "HTMX_DEBUG", settings.DEBUG)

        if self.debug:
            logger.info("HTMXMiddleware initialized (Phase 1)")

    def process_request(self, request: HttpRequest) -> None:
        """
        Process incoming request and add HTMX capabilities
        SAFETY: Only adds attributes, never modifies existing ones
        """
        if not self.enabled:
            return

        try:
            # Add HTMX helper to request (non-breaking)
            if not hasattr(request, "htmx_helper"):
                request.htmx_helper = HTMXRequest(request)

            # Add convenience properties (backward compatible)
            if not hasattr(request, "htmx"):
                request.htmx = request.htmx_helper.is_htmx

            # Add individual properties for easy access
            if not hasattr(request, "htmx_trigger"):
                request.htmx_trigger = request.htmx_helper.htmx_trigger

            if not hasattr(request, "htmx_target"):
                request.htmx_target = request.htmx_helper.htmx_target

            if self.debug and request.htmx_helper.is_htmx:
                logger.debug(f"HTMX Request detected: {request.path}")
                logger.debug(f"HTMX Headers: {request.htmx_helper.get_all_htmx_headers()}")

        except Exception as e:
            # SAFETY: Never break the request pipeline
            logger.error(f"HTMXMiddleware error in process_request: {e}")

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Process response - Phase 1 only adds debugging info
        SAFETY: Never modifies response unless explicitly requested
        """
        if not self.enabled:
            return response

        try:
            # Add debug headers if enabled
            if self.debug and hasattr(request, "htmx_helper"):
                if request.htmx_helper.is_htmx:
                    response["X-HTMX-Debug"] = "true"
                    response["X-HTMX-Middleware"] = "phase1"

                    if self.debug:
                        logger.debug(f"HTMX Response for {request.path}: {response.status_code}")

        except Exception as e:
            # SAFETY: Never break the response pipeline
            logger.error(f"HTMXMiddleware error in process_response: {e}")

        return response


class HTMXResponseHelper:
    """
    Helper class for building HTMX responses
    Phase 1: Basic response building without auto-modification
    """

    def __init__(self, content: str = "", status: int = 200):
        self.content = content
        self.status = status
        self.headers = {}

    def trigger(self, event_name: str, data: dict = None) -> "HTMXResponseHelper":
        """Add HX-Trigger header"""
        if data:
            import json

            self.headers["HX-Trigger"] = json.dumps({event_name: data})
        else:
            self.headers["HX-Trigger"] = event_name
        return self

    def trigger_after_settle(self, event_name: str, data: dict = None) -> "HTMXResponseHelper":
        """Add HX-Trigger-After-Settle header"""
        if data:
            import json

            self.headers["HX-Trigger-After-Settle"] = json.dumps({event_name: data})
        else:
            self.headers["HX-Trigger-After-Settle"] = event_name
        return self

    def trigger_after_swap(self, event_name: str, data: dict = None) -> "HTMXResponseHelper":
        """Add HX-Trigger-After-Swap header"""
        if data:
            import json

            self.headers["HX-Trigger-After-Swap"] = json.dumps({event_name: data})
        else:
            self.headers["HX-Trigger-After-Swap"] = event_name
        return self

    def redirect(self, url: str) -> "HTMXResponseHelper":
        """Add HX-Redirect header"""
        self.headers["HX-Redirect"] = url
        return self

    def refresh(self) -> "HTMXResponseHelper":
        """Add HX-Refresh header"""
        self.headers["HX-Refresh"] = "true"
        return self

    def retarget(self, target: str) -> "HTMXResponseHelper":
        """Add HX-Retarget header"""
        self.headers["HX-Retarget"] = target
        return self

    def reswap(self, swap: str) -> "HTMXResponseHelper":
        """Add HX-Reswap header"""
        self.headers["HX-Reswap"] = swap
        return self

    def push_url(self, url: str) -> "HTMXResponseHelper":
        """Add HX-Push-Url header"""
        self.headers["HX-Push-Url"] = url
        return self

    def replace_url(self, url: str) -> "HTMXResponseHelper":
        """Add HX-Replace-Url header"""
        self.headers["HX-Replace-Url"] = url
        return self

    def to_response(self) -> HttpResponse:
        """Convert to Django HttpResponse"""
        response = HttpResponse(self.content, status=self.status)
        for header, value in self.headers.items():
            response[header] = value
        return response


def HTMXResponse(content: str = "", status: int = 200) -> HTMXResponseHelper:
    """
    Convenience function for creating HTMX responses
    Usage: return HTMXResponse("Success").trigger('updated').to_response()
    """
    return HTMXResponseHelper(content, status)


# Decorator for HTMX-only views (Phase 1: Basic implementation)
def htmx_only(view_func):
    """
    Decorator to restrict view to HTMX requests only
    SAFETY: Returns 400 for non-HTMX requests instead of breaking
    """

    def wrapper(request, *args, **kwargs):
        if not hasattr(request, "htmx_helper") or not request.htmx_helper.is_htmx:
            from django.http import HttpResponseBadRequest

            return HttpResponseBadRequest("This endpoint requires HTMX")
        return view_func(request, *args, **kwargs)

    return wrapper


# Settings validation
def validate_htmx_settings():
    """Validate HTMX middleware settings"""
    warnings = []

    if not hasattr(settings, "HTMX_MIDDLEWARE_ENABLED"):
        warnings.append("HTMX_MIDDLEWARE_ENABLED not set, defaulting to True")

    if not hasattr(settings, "HTMX_DEBUG"):
        warnings.append("HTMX_DEBUG not set, defaulting to DEBUG setting")

    return warnings
