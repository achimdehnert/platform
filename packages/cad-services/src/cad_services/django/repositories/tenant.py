"""
Tenant Repository
ADR-009: Data access layer for Tenant operations
"""

from django.db.models import Count, QuerySet

from cad_services.django.models.core import Membership, Tenant, User
from cad_services.django.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant CRUD and queries."""

    model_class = Tenant

    def get_by_slug(self, slug: str) -> Tenant | None:
        try:
            return Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist:
            return None

    def get_active(self) -> QuerySet[Tenant]:
        return Tenant.objects.filter(status="active")

    def get_with_user_count(self) -> QuerySet[Tenant]:
        return Tenant.objects.annotate(user_count=Count("memberships")).order_by("-created_at")

    def get_users(self, tenant_id: int) -> QuerySet[User]:
        return User.objects.filter(memberships__tenant_id=tenant_id).distinct()

    def add_user(
        self,
        tenant_id: int,
        user_id: int,
        role_id: int,
        is_primary: bool = False,
    ) -> Membership:
        return Membership.objects.create(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role_id,
            is_primary=is_primary,
        )

    def remove_user(self, tenant_id: int, user_id: int) -> bool:
        deleted, _ = Membership.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
        ).delete()
        return deleted > 0

    def suspend(self, tenant_id: int) -> Tenant | None:
        return self.update(tenant_id, status="suspended")

    def activate(self, tenant_id: int) -> Tenant | None:
        return self.update(tenant_id, status="active")
