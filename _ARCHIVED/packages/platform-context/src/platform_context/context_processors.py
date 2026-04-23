"""Django template context processors."""

from django.http import HttpRequest

from platform_context.context import get_context


def tenant_context(request: HttpRequest) -> dict:
    """
    Add tenant information to template context.

    Usage in settings.py:
        TEMPLATES = [{
            ...
            "OPTIONS": {
                "context_processors": [
                    ...
                    "platform_context.context_processors.tenant_context",
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


def platform_context(request: HttpRequest) -> dict:
    """
    Add platform context to templates (tenant, permissions, membership).

    Usage in settings.py:
        'platform_context.context_processors.platform_context',

    Available in templates:
        {{ tenant }}           - Tenant object (if in tenant context)
        {{ tenant_id }}        - UUID
        {{ tenant_slug }}      - String
        {{ membership }}       - TenantMembership (if authenticated)
        {{ permissions }}      - FrozenSet of permission codes
        {{ user_role }}        - Role string (owner, admin, member, viewer)
        {{ is_tenant_admin }}  - Bool: owner or admin
        {{ request_id }}       - Correlation ID

    Permission check in templates:
        {% if 'stories.create' in permissions %}
            <a href="...">Create Story</a>
        {% endif %}
    """
    ctx = get_context()

    result = {
        "tenant_id": ctx.tenant_id,
        "tenant_slug": ctx.tenant_slug,
        "request_id": ctx.request_id,
        "tenant": getattr(request, "tenant", None),
        "membership": getattr(request, "membership", None),
        "permissions": getattr(request, "permissions", frozenset()),
        "user_role": None,
        "is_tenant_admin": False,
    }

    membership = result["membership"]
    if membership:
        result["user_role"] = membership.role
        result["is_tenant_admin"] = membership.role in ("owner", "admin")

    return result
