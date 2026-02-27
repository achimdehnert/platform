import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from iil_commons.settings import get_setting

logger = logging.getLogger(__name__)

_WINDOW_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse '100/h' → (100, 3600). Returns (requests, window_seconds)."""
    try:
        count_str, unit = rate.split("/")
        return int(count_str), _WINDOW_UNITS[unit]
    except (ValueError, KeyError):
        return 100, 3600


def _rate_limit_key(request: HttpRequest, key_type: str = "ip") -> str:
    if key_type == "user" and hasattr(request, "user") and request.user.is_authenticated:
        return f"iil:rl:user:{request.user.pk}"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "unknown")
    return f"iil:rl:ip:{ip}"


def _check_rate_limit(cache_key: str, limit: int, window: int) -> tuple[bool, int]:
    """Returns (allowed, remaining). Uses sliding window via cache."""
    try:
        from django.core.cache import cache

        now = int(time.time())
        window_key = f"{cache_key}:{now // window}"
        current = cache.get(window_key, 0)
        if current >= limit:
            return False, 0
        cache.set(window_key, current + 1, window * 2)
        return True, max(0, limit - current - 1)
    except Exception as exc:
        logger.warning("rate limit check failed (allowing request): %s", exc)
        return True, -1


class RateLimitMiddleware:
    """Global rate limiting middleware driven by IIL_COMMONS config.

    Checks RATE_LIMIT_DEFAULT and RATE_LIMIT_PATHS against request IP.
    Returns 429 with Retry-After header when limit exceeded.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        rate_str = self._get_rate_for_path(request.path)
        if rate_str:
            limit, window = _parse_rate(rate_str)
            cache_key = _rate_limit_key(request)
            allowed, remaining = _check_rate_limit(cache_key, limit, window)
            if not allowed:
                response = HttpResponse(
                    '{"error": "Rate limit exceeded"}',
                    content_type="application/json",
                    status=429,
                )
                response["Retry-After"] = str(window)
                response["X-RateLimit-Limit"] = str(limit)
                response["X-RateLimit-Remaining"] = "0"
                return response

        return self.get_response(request)

    def _get_rate_for_path(self, path: str) -> str | None:
        path_rates: dict = get_setting("RATE_LIMIT_PATHS", {})
        for prefix, rate in path_rates.items():
            if path.startswith(prefix):
                return rate
        return get_setting("RATE_LIMIT_DEFAULT", None)
