"""
Permission mixins for class-based views.

Usage:
    class StoryListView(TenantPermissionMixin, ListView):
        required_permission = Permission.STORIES_VIEW
"""

from typing import FrozenSet, Optional

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from bfagent_core.context import get_context
from bfagent_core.permissions.enums import Permission
from bfagent_core.permissions.checker import get_permission_checker


class TenantPermissionMixin:
    """
    Mixin for class-based views requiring tenant permission.
    
    Attributes:
        required_permission: Permission code or Permission enum
        required_role: Role name (alternative to permission)
    
    Example:
        class StoryListView(TenantPermissionMixin, ListView):
            required_permission = Permission.STORIES_VIEW
            model = Story
        
        class AdminView(TenantPermissionMixin, TemplateView):
            required_role = "admin"
    """
    
    required_permission: Optional[Permission | str] = None
    required_role: Optional[str] = None
    
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """Check permission before dispatching."""
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
        
        user_id = self._get_user_id(request)
        if user_id is None:
            raise PermissionDenied("No user context")
        
        # Check role if specified
        if self.required_role:
            self._check_role(request, user_id)
        
        # Check permission if specified
        if self.required_permission:
            self._check_permission(request, user_id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def _check_permission(self, request: HttpRequest, user_id) -> None:
        """Check if user has required permission."""
        checker = get_permission_checker()
        perm = self.required_permission
        perm_code = perm.value if isinstance(perm, Permission) else perm
        
        result = checker.has_permission(user_id, perm_code)
        if not result.granted:
            raise PermissionDenied(f"Permission denied: {perm_code}")
    
    def _check_role(self, request: HttpRequest, user_id) -> None:
        """Check if user has required role."""
        from bfagent_core.models import TenantMembership
        ctx = get_context()
        
        if ctx.tenant_id is None:
            raise PermissionDenied("No tenant context")
        
        membership = TenantMembership.objects.get_membership(ctx.tenant_id, user_id)
        if membership is None:
            raise PermissionDenied("No membership")
        
        roles = self.required_role if isinstance(self.required_role, (list, tuple)) else [self.required_role]
        if membership.role not in roles:
            raise PermissionDenied(f"Required role: {', '.join(roles)}")
    
    def _get_user_id(self, request: HttpRequest):
        """Get CoreUser ID from request."""
        if hasattr(request, "core_user") and request.core_user:
            return request.core_user.id
        
        if request.user and request.user.is_authenticated:
            from bfagent_core.models import CoreUser
            core_user = CoreUser.objects.filter(legacy_user_id=request.user.id).first()
            if core_user:
                return core_user.id
        
        return None
    
    def get_user_permissions(self) -> FrozenSet[str]:
        """Get all permissions for current user (for use in templates)."""
        request = self.request
        user_id = self._get_user_id(request)
        if user_id is None:
            return frozenset()
        
        checker = get_permission_checker()
        return checker.get_permissions(user_id)
    
    def has_permission(self, permission: str | Permission) -> bool:
        """Check if current user has permission (for use in templates)."""
        request = self.request
        user_id = self._get_user_id(request)
        if user_id is None:
            return False
        
        checker = get_permission_checker()
        perm_code = permission.value if isinstance(permission, Permission) else permission
        return checker.has_permission(user_id, perm_code).granted


class TenantAdminRequiredMixin(TenantPermissionMixin):
    """Mixin requiring admin or owner role."""
    required_role = ("owner", "admin")


class TenantOwnerRequiredMixin(TenantPermissionMixin):
    """Mixin requiring owner role."""
    required_role = "owner"


class TenantAPIPermissionMixin:
    """
    Permission mixin for DRF API views.
    
    Example:
        class StoryListAPI(TenantAPIPermissionMixin, ListAPIView):
            required_permission = Permission.STORIES_VIEW
            serializer_class = StorySerializer
    """
    
    required_permission: Optional[Permission | str] = None
    required_role: Optional[str] = None
    
    def check_permissions(self, request):
        """Override DRF's check_permissions."""
        super().check_permissions(request)
        
        if not request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated()
        
        user_id = self._get_user_id(request)
        if user_id is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No user context")
        
        # Check role if specified
        if self.required_role:
            self._check_role_api(request, user_id)
        
        # Check permission if specified
        if self.required_permission:
            self._check_permission_api(request, user_id)
    
    def _check_permission_api(self, request, user_id) -> None:
        """Check permission for API."""
        from rest_framework.exceptions import PermissionDenied
        
        checker = get_permission_checker()
        perm = self.required_permission
        perm_code = perm.value if isinstance(perm, Permission) else perm
        
        result = checker.has_permission(user_id, perm_code)
        if not result.granted:
            raise PermissionDenied(f"Permission denied: {perm_code}")
    
    def _check_role_api(self, request, user_id) -> None:
        """Check role for API."""
        from rest_framework.exceptions import PermissionDenied
        from bfagent_core.models import TenantMembership
        ctx = get_context()
        
        if ctx.tenant_id is None:
            raise PermissionDenied("No tenant context")
        
        membership = TenantMembership.objects.get_membership(ctx.tenant_id, user_id)
        if membership is None:
            raise PermissionDenied("No membership")
        
        roles = self.required_role if isinstance(self.required_role, (list, tuple)) else [self.required_role]
        if membership.role not in roles:
            raise PermissionDenied(f"Required role: {', '.join(roles)}")
    
    def _get_user_id(self, request):
        """Get CoreUser ID from request."""
        if hasattr(request, "core_user") and request.core_user:
            return request.core_user.id
        
        if request.user and request.user.is_authenticated:
            from bfagent_core.models import CoreUser
            core_user = CoreUser.objects.filter(legacy_user_id=request.user.id).first()
            if core_user:
                return core_user.id
        
        return None
