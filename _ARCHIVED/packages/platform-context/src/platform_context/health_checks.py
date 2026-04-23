"""
Django system checks for ADR-167 compliance.

Run automatically on ``manage.py check`` and on server startup. Catches
misconfiguration before the first request hits an invalid setting.

Check IDs:
    platform_context.E167.paths_type      — HEALTH_PROBE_PATHS must be iterable of str
    platform_context.E167.paths_format    — each path must start with "/" and end with "/"
    platform_context.W167.middleware_order — HealthBypassMiddleware must be first
    platform_context.E167.response_format  — HEALTH_RESPONSE_FORMAT must be "text" or "json"

References:
    - ADR-167 v1.1 § System Checks
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.checks import CheckMessage, Error, Warning, register

HEALTH_BYPASS_DOTTED_PATH = "platform_context.middleware.HealthBypassMiddleware"


@register("platform_context")
def check_health_probe_paths(
    app_configs: Any,  # noqa: ARG001
    **kwargs: Any,
) -> list[CheckMessage]:
    """Validate HEALTH_PROBE_PATHS setting."""
    errors: list[CheckMessage] = []
    paths = getattr(settings, "HEALTH_PROBE_PATHS", None)
    if paths is None:
        return errors  # Use middleware defaults — fine.

    if not isinstance(paths, (set, frozenset, list, tuple)):
        errors.append(
            Error(
                "HEALTH_PROBE_PATHS must be a set, frozenset, list, or tuple of strings.",
                hint="Example: HEALTH_PROBE_PATHS = frozenset({'/livez/', '/healthz/'})",
                id="platform_context.E167.paths_type",
            )
        )
        return errors

    for idx, path in enumerate(paths):
        if not isinstance(path, str):
            errors.append(
                Error(
                    f"HEALTH_PROBE_PATHS[{idx}]={path!r} is not a str.",
                    id="platform_context.E167.paths_type",
                )
            )
            continue
        if not path.startswith("/"):
            errors.append(
                Error(
                    f"HEALTH_PROBE_PATHS contains {path!r} which must start with '/'.",
                    hint="Django's request.path always starts with '/'.",
                    id="platform_context.E167.paths_format",
                )
            )
        if not path.endswith("/"):
            errors.append(
                Warning(
                    f"HEALTH_PROBE_PATHS contains {path!r} without trailing slash. "
                    "Django's APPEND_SLASH may redirect 301 before middleware chain.",
                    hint="Prefer '/livez/' over '/livez' to match APPEND_SLASH behavior.",
                    id="platform_context.W167.paths_format",
                )
            )
    return errors


@register("platform_context")
def check_middleware_order(
    app_configs: Any,  # noqa: ARG001
    **kwargs: Any,
) -> list[CheckMessage]:
    """Enforce HealthBypassMiddleware as the first entry in MIDDLEWARE."""
    errors: list[CheckMessage] = []
    middleware = getattr(settings, "MIDDLEWARE", [])
    if not middleware:
        errors.append(
            Warning(
                "MIDDLEWARE is empty; ADR-167 requires HealthBypassMiddleware.",
                id="platform_context.W167.middleware_order",
            )
        )
        return errors

    if HEALTH_BYPASS_DOTTED_PATH in middleware:
        if middleware[0] != HEALTH_BYPASS_DOTTED_PATH:
            errors.append(
                Error(
                    f"{HEALTH_BYPASS_DOTTED_PATH!r} must be MIDDLEWARE[0] (ADR-167), "
                    f"but is at position {middleware.index(HEALTH_BYPASS_DOTTED_PATH)}.",
                    hint="Health probes must bypass ALL other middleware.",
                    id="platform_context.E167.middleware_order",
                )
            )
    else:
        errors.append(
            Warning(
                f"{HEALTH_BYPASS_DOTTED_PATH!r} is not in MIDDLEWARE (ADR-167).",
                hint="Add it as MIDDLEWARE[0] for ADR-167 compliance.",
                id="platform_context.W167.middleware_order",
            )
        )
    return errors


@register("platform_context")
def check_response_format(
    app_configs: Any,  # noqa: ARG001
    **kwargs: Any,
) -> list[CheckMessage]:
    """Validate HEALTH_RESPONSE_FORMAT if set."""
    errors: list[CheckMessage] = []
    fmt = getattr(settings, "HEALTH_RESPONSE_FORMAT", None)
    if fmt is not None and fmt not in {"text", "json"}:
        errors.append(
            Error(
                f"HEALTH_RESPONSE_FORMAT={fmt!r} is invalid; must be 'text' or 'json'.",
                id="platform_context.E167.response_format",
            )
        )
    return errors
