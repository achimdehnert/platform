"""
Domain services for business logic.

Services coordinate between repositories, enforce domain rules,
and orchestrate complex operations.
"""

from typing import FrozenSet, Optional
from uuid import UUID

from bfagent_core.context import get_context
from bfagent_core.permissions.checker import get_permission_checker


class AuthorizationService:
    """
    Service for authorization checks.
    
    Provides a high-level API for permission checks with
    proper error handling and logging.
    """
    
    def __init__(self):
        self.checker = get_permission_checker()
    
    def can(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """Check if user has permission."""
        return self.checker.has_permission(user_id, permission, tenant_id).granted
    
    def require(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """Require permission (raises on denial)."""
        self.checker.check_permission(user_id, permission, tenant_id)
    
    def get_permissions(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
    ) -> FrozenSet[str]:
        """Get all permissions for user."""
        return self.checker.get_permissions(user_id, tenant_id)
    
    def is_admin(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Check if user is admin or owner."""
        from bfagent_core.models import TenantMembership
        
        if tenant_id is None:
            ctx = get_context()
            tenant_id = ctx.tenant_id
        
        if tenant_id is None:
            return False
        
        membership = TenantMembership.objects.get_membership(tenant_id, user_id)
        return membership is not None and membership.is_admin
    
    def is_owner(self, user_id: UUID, tenant_id: Optional[UUID] = None) -> bool:
        """Check if user is owner."""
        from bfagent_core.models import TenantMembership
        
        if tenant_id is None:
            ctx = get_context()
            tenant_id = ctx.tenant_id
        
        if tenant_id is None:
            return False
        
        membership = TenantMembership.objects.get_membership(tenant_id, user_id)
        return membership is not None and membership.is_owner


class TenantLifecycleService:
    """
    Service for tenant lifecycle management.
    
    Handles complex lifecycle transitions with validation.
    """
    
    def check_trial_expiration(self, tenant) -> bool:
        """Check if trial has expired."""
        return tenant.is_trial_expired
    
    def can_activate(self, tenant) -> bool:
        """Check if tenant can be activated."""
        from bfagent_core.models import TenantStatus
        return tenant.status in (TenantStatus.TRIAL, TenantStatus.SUSPENDED)
    
    def can_suspend(self, tenant) -> bool:
        """Check if tenant can be suspended."""
        from bfagent_core.models import TenantStatus
        return tenant.status != TenantStatus.DELETED
    
    def can_delete(self, tenant) -> bool:
        """Check if tenant can be deleted."""
        from bfagent_core.models import TenantStatus
        return tenant.status != TenantStatus.DELETED


# Singletons
_auth_service = AuthorizationService()
_lifecycle_service = TenantLifecycleService()


def get_authorization_service() -> AuthorizationService:
    return _auth_service


def get_lifecycle_service() -> TenantLifecycleService:
    return _lifecycle_service


__all__ = [
    "AuthorizationService",
    "TenantLifecycleService",
    "get_authorization_service",
    "get_lifecycle_service",
]
