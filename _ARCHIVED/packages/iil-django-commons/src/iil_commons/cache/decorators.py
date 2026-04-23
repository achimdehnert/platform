import functools
import hashlib
import logging
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse

from iil_commons.settings import get_setting

logger = logging.getLogger(__name__)


def _default_key_func(request: HttpRequest) -> str:
    return hashlib.md5(  # noqa: S324
        f"{request.path}:{request.GET.urlencode()}".encode(),
        usedforsecurity=False,
    ).hexdigest()


def cached_view(
    ttl: int | None = None,
    key_func: Callable[[HttpRequest], str] | None = None,
    cache_alias: str = "default",
) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            from django.core.cache import caches

            cache = caches[cache_alias]
            resolved_ttl = ttl if ttl is not None else get_setting("CACHE_DEFAULT_TTL", 300)
            resolved_key_func = key_func or _default_key_func
            cache_key = f"iil:view:{resolved_key_func(request)}"

            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            response = view_func(request, *args, **kwargs)
            if response.status_code == 200:
                cache.set(cache_key, response, resolved_ttl)
            return response

        return wrapper

    return decorator


def cached_method(
    ttl: int | None = None,
    key_prefix: str = "",
    cache_alias: str = "default",
) -> Callable:
    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            from django.core.cache import caches

            cache = caches[cache_alias]
            resolved_ttl = ttl if ttl is not None else get_setting("CACHE_DEFAULT_TTL", 300)
            key_parts = [
                "iil:method",
                key_prefix or f"{self.__class__.__name__}.{method.__name__}",
                hashlib.md5(  # noqa: S324
                    str(args).encode() + str(sorted(kwargs.items())).encode(),
                    usedforsecurity=False,
                ).hexdigest(),
            ]
            cache_key = ":".join(key_parts)

            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            result = method(self, *args, **kwargs)
            cache.set(cache_key, result, resolved_ttl)
            return result

        return wrapper

    return decorator
