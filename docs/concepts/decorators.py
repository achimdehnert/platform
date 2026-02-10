"""
Permission-Decorators für Views und Funktionen.

Verwendung:
    @require_permission(Permission.STORIES_CREATE)
    def create_story(request):
        ...
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from bfagent_core.context import get_context
from bfagent_core.permissions.enums import Permission
from bfagent_core.permissions.checker import get_permission_checker

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def require_permission(
    permission: Permission | str,
    *,
    message: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator für Permission-Check.
    
    Beispiel:
        @require_permission(Permission.STORIES_CREATE)
        def create_story(request):
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_request(args)
            
            if request is None or not hasattr(request, "user"):
                raise PermissionDenied("No request context")
            
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            checker = get_permission_checker()
            result = checker.has_permission(request.user.id, permission)
            
            if not result.granted:
                error_msg = message or f"Permission denied: {result.permission}"
                logger.warning(
                    "Permission denied",
                    extra={
                        "user_id": request.user.id,
                        "permission": result.permission,
                        "function": func.__name__,
                    },
                )
                raise PermissionDenied(error_msg)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(
    *roles: str,
    message: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator für Role-Check.
    
    Beispiel:
        @require_role("owner", "admin")
        def admin_dashboard(request):
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_request(args)
            
            if request is None or not hasattr(request, "user"):
                raise PermissionDenied("No request context")
            
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            from bfagent_core.models import TenantMembership
            ctx = get_context()
            
            if ctx.tenant_id is None:
                raise PermissionDenied("No tenant context")
            
            membership = TenantMembership.objects.get_membership(
                ctx.tenant_id,
                request.user.id,
            )
            
            if membership is None:
                raise PermissionDenied("No membership")
            
            if membership.role not in roles:
                error_msg = message or f"Required role: {', '.join(roles)}"
                logger.warning(
                    "Role check failed",
                    extra={
                        "user_id": request.user.id,
                        "required": roles,
                        "actual": membership.role,
                    },
                )
                raise PermissionDenied(error_msg)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(
    *permissions: Permission | str,
    message: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator für OR-Permissions.
    
    Beispiel:
        @require_any_permission(Permission.STORIES_EDIT, Permission.STORIES_DELETE)
        def modify_story(request, story_id):
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_request(args)
            
            if request is None or not hasattr(request, "user"):
                raise PermissionDenied("No request context")
            
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            checker = get_permission_checker()
            
            for permission in permissions:
                if checker.has_permission(request.user.id, permission).granted:
                    return func(*args, **kwargs)
            
            perm_names = [
                p.value if isinstance(p, Permission) else p
                for p in permissions
            ]
            error_msg = message or f"One required: {perm_names}"
            raise PermissionDenied(error_msg)
        return wrapper
    return decorator


def require_all_permissions(
    *permissions: Permission | str,
    message: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator für AND-Permissions.
    
    Beispiel:
        @require_all_permissions(Permission.STORIES_EDIT, Permission.STORIES_PUBLISH)
        def publish_story(request, story_id):
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_request(args)
            
            if request is None or not hasattr(request, "user"):
                raise PermissionDenied("No request context")
            
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            checker = get_permission_checker()
            missing = []
            
            for permission in permissions:
                result = checker.has_permission(request.user.id, permission)
                if not result.granted:
                    missing.append(result.permission)
            
            if missing:
                error_msg = message or f"Missing: {missing}"
                raise PermissionDenied(error_msg)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_access(
    func: Callable[P, R] | None = None,
    *,
    message: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]:
    """
    Decorator für Tenant-Zugang (nur Membership nötig).
    
    Beispiel:
        @require_tenant_access
        def tenant_dashboard(request):
            ...
    """
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_request(args)
            
            if request is None or not hasattr(request, "user"):
                raise PermissionDenied("No request context")
            
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            from bfagent_core.models import TenantMembership
            ctx = get_context()
            
            if ctx.tenant_id is None:
                raise PermissionDenied("No tenant context")
            
            if not TenantMembership.objects.user_has_access(
                ctx.tenant_id, request.user.id
            ):
                error_msg = message or "No access to tenant"
                raise PermissionDenied(error_msg)
            
            return fn(*args, **kwargs)
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def _extract_request(args: tuple) -> HttpRequest | None:
    """Extract HttpRequest from args."""
    for arg in args:
        if isinstance(arg, HttpRequest):
            return arg
        if hasattr(arg, "request"):
            req = getattr(arg, "request", None)
            if isinstance(req, HttpRequest):
                return req
    return None
