"""Django template context processors."""

from django.http import HttpRequest

from bfagent_core.context import get_context


def tenant_context(request: HttpRequest) -> dict:
    """
    Add tenant information to template context.
    
    Usage in settings.py:
        TEMPLATES = [{
            ...
            "OPTIONS": {
                "context_processors": [
                    ...
                    "bfagent_core.context_processors.tenant_context",
                ],
            },
        }]
    
    Available in templates:
        {{ tenant_id }}
        {{ tenant_slug }}
        {{ request_id }}
    """
    ctx = get_context()
    return {
        "tenant_id": ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "request_id": ctx.request_id,
    }
