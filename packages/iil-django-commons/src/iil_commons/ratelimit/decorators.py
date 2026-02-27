import functools
import logging
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse

from iil_commons.ratelimit.middleware import _check_rate_limit, _parse_rate, _rate_limit_key

logger = logging.getLogger(__name__)


def rate_limit(
    requests: int,
    window: int = 3600,
    key: str = "ip",
) -> Callable:
    """View decorator for per-view rate limiting.

    Args:
        requests: Max requests allowed in the window.
        window:   Window in seconds (default: 3600 = 1h).
        key:      'ip' or 'user' (falls back to 'ip' for anonymous).

    Usage:
        @rate_limit(requests=10, window=60, key="user")
        def api_endpoint(request): ...
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            cache_key = f"iil:rl:view:{view_func.__name__}:{_rate_limit_key(request, key)}"
            allowed, remaining = _check_rate_limit(cache_key, requests, window)
            if not allowed:
                response = HttpResponse(
                    '{"error": "Rate limit exceeded"}',
                    content_type="application/json",
                    status=429,
                )
                response["Retry-After"] = str(window)
                response["X-RateLimit-Limit"] = str(requests)
                response["X-RateLimit-Remaining"] = "0"
                return response

            response = view_func(request, *args, **kwargs)
            response["X-RateLimit-Limit"] = str(requests)
            response["X-RateLimit-Remaining"] = str(remaining)
            return response

        return wrapper

    return decorator
