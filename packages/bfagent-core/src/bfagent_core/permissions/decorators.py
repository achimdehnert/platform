"""
Permission decorators for views and functions.

Usage:
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
    Decorator for permission check.
    
    Example:
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
            
            # Get user_id from CoreUser or auth_user
            user_id = _get_user_id(request)
            if user_id is None:
                raise PermissionDenied("No user context")
            
            checker = get_permission_checker()
            perm_code = permission.value if isinstance(permission, Permission) else permission
            result = checker.has_permission(user_id, perm_code)
            
            if not result.granted:
                error_msg = message or f"Permission denied: {perm_code}"
                logger.warning(
                    "Permission denied",
                    extra={
                        "user_id": str(user_id),
                        "permission": perm_code,
                        "function": func.__name__,
                        "source": result.source,
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
    Decorator for role check.
    
    Example:
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
            
            user_id = _get_user_id(request)
            if user_id is None:
                raise PermissionDenied("No user context")
            
            membership = TenantMembership.objects.get_membership(
                ctx.tenant_id,
                user_id,
            )
            
            if membership is None:
                raise PermissionDenied("No membership")
            
            if membership.role not in roles:
                error_msg = message or f"Required role: {', '.join(roles)}"
                logger.warning(
                    "Role check failed",
                    extra={
                        "user_id": str(user_id),
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
    Decorator for OR permissions.
    
    Example:
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
            
            user_id = _get_user_id(request)
            if user_id is None:
                raise PermissionDenied("No user context")
            
            checker = get_permission_checker()
            
            for permission in permissions:
                perm_code = permission.value if isinstance(permission, Permission) else permission
                if checker.has_permission(user_id, perm_code).granted:
                    return func(*args, **kwargs)
            
            perm_names = [
                p.value if isinstance(p, Permission) else p
                for p in permissions
            ]
            error_msg = message or f"One of these permissions required: {perm_names}"
            raise PermissionDenied(error_msg)
        return wrapper
    return decorator


def require_all_permissions(
    *permissions: Permission | str,
    message: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for AND permissions.
    
    Example:
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
            
            user_id = _get_user_id(request)
            if user_id is None:
                raise PermissionDenied("No user context")
            
            checker = get_permission_checker()
            missing = []
            
            for permission in permissions:
                perm_code = permission.value if isinstance(permission, Permission) else permission
                result = checker.has_permission(user_id, perm_code)
                if not result.granted:
                    missing.append(perm_code)
            
            if missing:
                error_msg = message or f"Missing permissions: {missing}"
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
    Decorator for tenant access (membership required, any role).
    
    Example:
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
            
            user_id = _get_user_id(request)
            if user_id is None:
                raise PermissionDenied("No user context")
            
            if not TenantMembership.objects.user_has_access(ctx.tenant_id, user_id):
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


def _get_user_id(request: HttpRequest):
    """Get CoreUser ID from request."""
    # Check if core_user is attached (by middleware)
    if hasattr(request, "core_user") and request.core_user:
        return request.core_user.id
    
    # Fallback: look up by legacy_user_id
    if request.user and request.user.is_authenticated:
        from bfagent_core.models import CoreUser
        core_user = CoreUser.objects.filter(legacy_user_id=request.user.id).first()
        if core_user:
            return core_user.id
    
    return None
