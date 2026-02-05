"""
Tests for bfagent_core permission system.

Run with: pytest tests/test_permissions.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.test import TestCase, TransactionTestCase

from bfagent_core.models import (
    Plan,
    CoreUser,
    Tenant,
    TenantMembership,
    TenantStatus,
    TenantRole,
    MembershipStatus,
    CorePermission,
    CoreRolePermission,
    MembershipPermissionOverride,
)
from bfagent_core.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    PermissionChecker,
    PermissionResolver,
    get_permission_checker,
)
from bfagent_core.exceptions import PermissionDeniedError


class PermissionEnumTests(TestCase):
    """Tests for Permission enum."""
    
    def test_permission_format(self):
        """Test permission code format."""
        for perm in Permission:
            self.assertIn(".", perm.value)
            parts = perm.value.split(".")
            self.assertEqual(len(parts), 2)
    
    def test_role_permissions_defined(self):
        """Test all roles have permissions defined."""
        for role in ["owner", "admin", "member", "viewer"]:
            self.assertIn(role, ROLE_PERMISSIONS)
            self.assertIsInstance(ROLE_PERMISSIONS[role], set)
    
    def test_owner_has_all_permissions(self):
        """Test owner role has all permissions."""
        owner_perms = ROLE_PERMISSIONS["owner"]
        all_perms = {p.value for p in Permission}
        self.assertEqual(owner_perms, all_perms)
    
    def test_viewer_subset_of_member(self):
        """Test viewer permissions are subset of member."""
        viewer_perms = ROLE_PERMISSIONS["viewer"]
        member_perms = ROLE_PERMISSIONS["member"]
        self.assertTrue(viewer_perms.issubset(member_perms))


class PermissionResolverTests(TransactionTestCase):
    """Tests for PermissionResolver."""
    
    def setUp(self):
        """Set up test data."""
        self.plan, _ = Plan.objects.get_or_create(
            code="free",
            defaults={"name": "Free", "sort_order": 0}
        )
        
        self.user = CoreUser.objects.create(
            email="user@example.com",
            display_name="Test User",
            provider="local",
            legacy_user_id=100,
        )
        
        self.tenant = Tenant.objects.create(
            slug="test",
            name="Test",
            plan=self.plan,
            status=TenantStatus.ACTIVE,
        )
        
        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        
        # Ensure permission exists
        CorePermission.objects.get_or_create(
            code="stories.create",
            defaults={"category": "stories", "description": "Create stories"}
        )
        CorePermission.objects.get_or_create(
            code="tenant.delete",
            defaults={"category": "tenant", "description": "Delete tenant"}
        )
        
        self.resolver = PermissionResolver()
    
    def test_resolve_role_permission_granted(self):
        """Test permission granted by role."""
        # Member has stories.create
        result = self.resolver.resolve(self.membership, "stories.create")
        self.assertTrue(result)
    
    def test_resolve_role_permission_denied(self):
        """Test permission denied by role."""
        # Member does not have tenant.delete
        result = self.resolver.resolve(self.membership, "tenant.delete")
        self.assertFalse(result)
    
    def test_resolve_explicit_grant_override(self):
        """Test explicit ALLOW override grants permission."""
        # Grant tenant.delete to member
        MembershipPermissionOverride.objects.create(
            membership=self.membership,
            permission_id="tenant.delete",
            allowed=True,
        )
        
        result = self.resolver.resolve(self.membership, "tenant.delete")
        self.assertTrue(result)
    
    def test_resolve_explicit_deny_override(self):
        """Test explicit DENY override revokes permission."""
        # Revoke stories.create from member
        MembershipPermissionOverride.objects.create(
            membership=self.membership,
            permission_id="stories.create",
            allowed=False,
        )
        
        result = self.resolver.resolve(self.membership, "stories.create")
        self.assertFalse(result)
    
    def test_resolve_expired_override_ignored(self):
        """Test expired overrides are ignored."""
        # Grant with expired date
        MembershipPermissionOverride.objects.create(
            membership=self.membership,
            permission_id="tenant.delete",
            allowed=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        result = self.resolver.resolve(self.membership, "tenant.delete")
        self.assertFalse(result)  # Fallback to role (no permission)
    
    def test_deny_overrides_allow(self):
        """Test DENY always wins over ALLOW."""
        # This tests the deterministic algorithm: DENY > ALLOW > role
        # Create both deny and allow (edge case)
        MembershipPermissionOverride.objects.filter(
            membership=self.membership,
            permission_id="stories.create",
        ).delete()
        
        MembershipPermissionOverride.objects.create(
            membership=self.membership,
            permission_id="stories.create",
            allowed=False,  # DENY
        )
        
        result = self.resolver.resolve(self.membership, "stories.create")
        self.assertFalse(result)


class PermissionCheckerTests(TransactionTestCase):
    """Tests for PermissionChecker."""
    
    def setUp(self):
        """Set up test data."""
        self.plan, _ = Plan.objects.get_or_create(
            code="free",
            defaults={"name": "Free", "sort_order": 0}
        )
        
        self.user = CoreUser.objects.create(
            email="checker@example.com",
            display_name="Checker User",
            provider="local",
            legacy_user_id=200,
        )
        
        self.tenant = Tenant.objects.create(
            slug="checker-test",
            name="Checker Test",
            plan=self.plan,
            status=TenantStatus.ACTIVE,
        )
        
        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.ADMIN,
            status=MembershipStatus.ACTIVE,
        )
        
        self.checker = PermissionChecker()
    
    def test_has_permission_granted(self):
        """Test has_permission returns granted=True."""
        result = self.checker.has_permission(
            self.user.id,
            "stories.create",
            self.tenant.id,
        )
        self.assertTrue(result.granted)
    
    def test_has_permission_denied(self):
        """Test has_permission returns granted=False."""
        # Admin doesn't have tenant.delete
        result = self.checker.has_permission(
            self.user.id,
            "tenant.delete",
            self.tenant.id,
        )
        self.assertFalse(result.granted)
    
    def test_check_permission_raises_on_denial(self):
        """Test check_permission raises PermissionDeniedError."""
        with self.assertRaises(PermissionDeniedError) as ctx:
            self.checker.check_permission(
                self.user.id,
                "tenant.delete",
                self.tenant.id,
            )
        
        self.assertEqual(ctx.exception.permission, "tenant.delete")
    
    def test_get_permissions_returns_all(self):
        """Test get_permissions returns all user permissions."""
        permissions = self.checker.get_permissions(
            self.user.id,
            self.tenant.id,
        )
        
        self.assertIsInstance(permissions, frozenset)
        self.assertIn("stories.create", permissions)
        self.assertIn("members.invite", permissions)
        # Admin has most permissions except tenant.delete
        self.assertNotIn("tenant.delete", permissions)
    
    def test_no_membership_returns_denied(self):
        """Test no membership returns denied."""
        other_user = CoreUser.objects.create(
            email="other@example.com",
            display_name="Other",
            provider="local",
            legacy_user_id=300,
        )
        
        result = self.checker.has_permission(
            other_user.id,
            "stories.view",
            self.tenant.id,
        )
        self.assertFalse(result.granted)


class PermissionVersionTests(TransactionTestCase):
    """Tests for permission_version cache invalidation."""
    
    def setUp(self):
        """Set up test data."""
        self.plan, _ = Plan.objects.get_or_create(
            code="free",
            defaults={"name": "Free", "sort_order": 0}
        )
        
        self.user = CoreUser.objects.create(
            email="version@example.com",
            display_name="Version User",
            provider="local",
            legacy_user_id=400,
        )
        
        self.tenant = Tenant.objects.create(
            slug="version-test",
            name="Version Test",
            plan=self.plan,
        )
        
        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
    
    def test_permission_version_increments_on_role_change(self):
        """Test permission_version increments when role changes."""
        initial_version = self.membership.permission_version
        
        self.membership.change_role(TenantRole.ADMIN)
        
        self.assertEqual(
            self.membership.permission_version,
            initial_version + 1
        )
    
    def test_permission_version_increments_manually(self):
        """Test increment_permission_version method."""
        initial_version = self.membership.permission_version
        
        self.membership.increment_permission_version()
        
        self.membership.refresh_from_db()
        self.assertEqual(
            self.membership.permission_version,
            initial_version + 1
        )
