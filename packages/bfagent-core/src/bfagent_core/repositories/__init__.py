"""
Repository layer for data access.

Provides abstraction over Django ORM for testability.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence
from uuid import UUID

from bfagent_core.models import Tenant, TenantMembership, CoreUser


class TenantRepository:
    """Repository for Tenant data access."""
    
    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        return Tenant.objects.filter(id=tenant_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return Tenant.objects.by_slug(slug)
    
    def slug_exists(self, slug: str) -> bool:
        return Tenant.objects.filter(slug=slug).exists()
    
    def save(self, tenant: Tenant) -> Tenant:
        tenant.save()
        return tenant
    
    def list_active(self) -> List[Tenant]:
        return list(Tenant.objects.active())
    
    def get_by_ids(self, tenant_ids: Sequence[UUID]) -> List[Tenant]:
        """Bulk load for N+1 prevention."""
        return list(Tenant.objects.filter(id__in=tenant_ids))


class MembershipRepository:
    """Repository for TenantMembership data access."""
    
    def get_by_id(self, membership_id: UUID) -> Optional[TenantMembership]:
        return TenantMembership.objects.filter(id=membership_id).first()
    
    def get_membership(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Optional[TenantMembership]:
        return TenantMembership.objects.get_membership(tenant_id, user_id)
    
    def user_has_access(self, tenant_id: UUID, user_id: UUID) -> bool:
        return TenantMembership.objects.user_has_access(tenant_id, user_id)
    
    def save(self, membership: TenantMembership) -> TenantMembership:
        membership.save()
        return membership
    
    def list_for_tenant(self, tenant_id: UUID) -> List[TenantMembership]:
        return list(TenantMembership.objects.active().filter(tenant_id=tenant_id))
    
    def list_for_user(self, user_id: UUID) -> List[TenantMembership]:
        return list(TenantMembership.objects.active().filter(user_id=user_id))
    
    def get_by_ids(self, membership_ids: Sequence[UUID]) -> List[TenantMembership]:
        """Bulk load for N+1 prevention."""
        return list(TenantMembership.objects.filter(id__in=membership_ids))


class CoreUserRepository:
    """Repository for CoreUser data access."""
    
    def get_by_id(self, user_id: UUID) -> Optional[CoreUser]:
        return CoreUser.objects.filter(id=user_id).first()
    
    def get_by_legacy_id(self, legacy_user_id: int) -> Optional[CoreUser]:
        return CoreUser.objects.filter(legacy_user_id=legacy_user_id).first()
    
    def get_or_create_from_auth_user(self, auth_user) -> CoreUser:
        return CoreUser.objects.get_or_create_from_auth_user(auth_user)
    
    def save(self, user: CoreUser) -> CoreUser:
        user.save()
        return user


# Singleton instances
_tenant_repo = TenantRepository()
_membership_repo = MembershipRepository()
_user_repo = CoreUserRepository()


def get_tenant_repository() -> TenantRepository:
    return _tenant_repo


def get_membership_repository() -> MembershipRepository:
    return _membership_repo


def get_user_repository() -> CoreUserRepository:
    return _user_repo


__all__ = [
    "TenantRepository",
    "MembershipRepository",
    "CoreUserRepository",
    "get_tenant_repository",
    "get_membership_repository",
    "get_user_repository",
]
