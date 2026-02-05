"""
Core Platform Models
ADR-009: Database-driven, normalized, FK integers
Table naming: core_{entity}
"""

from django.db import models


class Plan(models.Model):
    """Subscription plans - database-driven pricing."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    max_users = models.IntegerField(default=5)
    max_storage_gb = models.IntegerField(default=10)
    price_month = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_plan"
        ordering = ["price_month"]

    def __str__(self) -> str:
        return f"{self.name} (€{self.price_month}/mo)"


class Tenant(models.Model):
    """Multi-tenant organization."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("deleted", "Deleted"),
    ]

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="tenants",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_tenant"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class User(models.Model):
    """Platform user - can belong to multiple tenants."""

    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_user"
        ordering = ["email"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Role(models.Model):
    """Roles are database-driven, not hardcoded."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_role"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Permission(models.Model):
    """Permissions are database-driven."""

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_permission"
        ordering = ["resource", "action"]
        unique_together = [["resource", "action"]]

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"


class RolePermission(models.Model):
    """Role-Permission mapping."""

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_role_permission"
        unique_together = [["role", "permission"]]

    def __str__(self) -> str:
        return f"{self.role.code} -> {self.permission.code}"


class Membership(models.Model):
    """User-Tenant-Role assignment."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    is_primary = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_membership"
        unique_together = [["user", "tenant"]]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.tenant.slug} ({self.role.code})"
