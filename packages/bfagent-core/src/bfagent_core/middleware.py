"""
Django middleware for multi-tenancy and request context.
"""

import uuid
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from bfagent_core.context import set_request_id, set_tenant, set_user_id
from bfagent_core.db import set_db_tenant


def _parse_subdomain(host: str, base_domain: str) -> str | None:
    """
    Extract subdomain from host.
    
    Examples:
        - "demo.risk-hub.de" with base "risk-hub.de" -> "demo"
        - "risk-hub.de" with base "risk-hub.de" -> None
        - "demo.localhost" with base "localhost" -> "demo"
    """
    # Remove port if present
    host = host.split(":")[0].lower()
    base = base_domain.lower()
    
    if host == base:
        return None
    
    if host.endswith("." + base):
        return host[: -(len(base) + 1)]
    
    return None


class RequestContextMiddleware(MiddlewareMixin):
    """
    Middleware to set up request context (request_id, user_id).
    
    Should be placed early in the middleware stack.
    """
    
    def process_request(self, request: HttpRequest) -> None:
        # Get or generate request ID for correlation
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        set_request_id(request_id)
        
        # Set user ID if authenticated
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            set_user_id(user.id if hasattr(user, "id") else None)
        else:
            set_user_id(None)


class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Middleware for subdomain-based tenant resolution.
    
    Resolves tenant from subdomain (e.g., demo.risk-hub.de -> tenant "demo")
    and sets both the request context and Postgres session variable for RLS.
    
    Settings:
        TENANT_BASE_DOMAIN: Base domain (e.g., "risk-hub.de", "localhost")
        TENANT_ALLOW_LOCALHOST: Allow requests without tenant for admin (dev only)
        TENANT_MODEL: Dotted path to tenant model (default: "tenancy.Organization")
        TENANT_SLUG_FIELD: Field name for slug lookup (default: "slug")
        TENANT_ID_FIELD: Field name for tenant_id (default: "tenant_id")
    """
    
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        base_domain = getattr(settings, "TENANT_BASE_DOMAIN", "localhost")
        allow_localhost = getattr(settings, "TENANT_ALLOW_LOCALHOST", False)
        
        subdomain = _parse_subdomain(request.get_host(), base_domain)
        
        if not subdomain:
            # No subdomain - allow admin access in dev mode
            if allow_localhost and request.path.startswith("/admin/"):
                set_tenant(None, None)
                set_db_tenant(None)
                return None
            return HttpResponseForbidden("Missing tenant subdomain")
        
        # Look up tenant
        tenant = self._get_tenant(subdomain)
        if not tenant:
            return HttpResponseForbidden(f"Unknown tenant: {subdomain}")
        
        # Get tenant_id from the model
        tenant_id_field = getattr(settings, "TENANT_ID_FIELD", "tenant_id")
        tenant_id = getattr(tenant, tenant_id_field, None)
        
        # Set context and DB session variable
        set_tenant(tenant_id, subdomain)
        set_db_tenant(tenant_id)
        
        # Attach tenant to request for easy access in views
        request.tenant = tenant
        request.tenant_id = tenant_id
        request.tenant_slug = subdomain
        
        return None
    
    def _get_tenant(self, slug: str):
        """Look up tenant by slug."""
        model_path = getattr(settings, "TENANT_MODEL", "tenancy.Organization")
        slug_field = getattr(settings, "TENANT_SLUG_FIELD", "slug")
        
        try:
            from django.apps import apps
            app_label, model_name = model_path.rsplit(".", 1)
            model = apps.get_model(app_label, model_name)
            return model.objects.filter(**{slug_field: slug}).first()
        except Exception:
            return None
