"""
Tests for bfagent_core handlers.

Run with: pytest tests/test_handlers.py -v
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
)
from bfagent_core.handlers import (
    TenantCreateCommand,
    TenantCreateHandler,
    TenantActivateCommand,
    TenantActivateHandler,
    TenantSuspendCommand,
    TenantSuspendHandler,
    MembershipInviteCommand,
    MembershipInviteHandler,
    MembershipAcceptCommand,
    MembershipAcceptHandler,
)
from bfagent_core.exceptions import (
    TenantSlugExistsError,
    TenantNotFoundError,
    UserNotFoundError,
    MembershipExistsError,
    InvitationExpiredError,
)


class TenantHandlerTests(TransactionTestCase):
    """Tests for tenant handlers."""
    
    def setUp(self):
        """Set up test data."""
        # Ensure plan exists
        self.plan, _ = Plan.objects.get_or_create(
            code="free",
            defaults={"name": "Free", "sort_order": 0}
        )
        
        # Create test user
        self.owner = CoreUser.objects.create(
            email="owner@example.com",
            display_name="Test Owner",
            provider="local",
            legacy_user_id=1,
        )
    
    def test_tenant_create_success(self):
        """Test successful tenant creation."""
        handler = TenantCreateHandler()
        cmd = TenantCreateCommand(
            slug="acme",
            name="ACME Corp",
            plan_code="free",
            owner_user_id=self.owner.id,
            trial_days=14,
        )
        
        result = handler.handle(cmd)
        
        # Verify tenant created
        tenant = Tenant.objects.get(id=result.tenant_id)
        self.assertEqual(tenant.slug, "acme")
        self.assertEqual(tenant.name, "ACME Corp")
        self.assertEqual(tenant.status, TenantStatus.TRIAL)
        
        # Verify owner membership created
        membership = TenantMembership.objects.get(id=result.membership_id)
        self.assertEqual(membership.tenant_id, tenant.id)
        self.assertEqual(membership.user_id, self.owner.id)
        self.assertEqual(membership.role, TenantRole.OWNER)
        self.assertEqual(membership.status, MembershipStatus.ACTIVE)
    
    def test_tenant_create_slug_exists(self):
        """Test tenant creation with existing slug fails."""
        # Create first tenant
        Tenant.objects.create(
            slug="existing",
            name="Existing Tenant",
            plan=self.plan,
        )
        
        handler = TenantCreateHandler()
        cmd = TenantCreateCommand(
            slug="existing",
            name="Another Tenant",
            plan_code="free",
            owner_user_id=self.owner.id,
        )
        
        with self.assertRaises(TenantSlugExistsError):
            handler.handle(cmd)
    
    def test_tenant_create_user_not_found(self):
        """Test tenant creation with non-existent user fails."""
        handler = TenantCreateHandler()
        cmd = TenantCreateCommand(
            slug="test",
            name="Test",
            plan_code="free",
            owner_user_id=uuid4(),  # Non-existent user
        )
        
        with self.assertRaises(UserNotFoundError):
            handler.handle(cmd)
    
    def test_tenant_activate_success(self):
        """Test successful tenant activation."""
        tenant = Tenant.objects.create(
            slug="trial-tenant",
            name="Trial Tenant",
            plan=self.plan,
            status=TenantStatus.TRIAL,
        )
        
        handler = TenantActivateHandler()
        cmd = TenantActivateCommand(tenant_id=tenant.id)
        
        handler.handle(cmd)
        
        tenant.refresh_from_db()
        self.assertEqual(tenant.status, TenantStatus.ACTIVE)
    
    def test_tenant_suspend_success(self):
        """Test successful tenant suspension."""
        tenant = Tenant.objects.create(
            slug="active-tenant",
            name="Active Tenant",
            plan=self.plan,
            status=TenantStatus.ACTIVE,
        )
        
        handler = TenantSuspendHandler()
        cmd = TenantSuspendCommand(
            tenant_id=tenant.id,
            reason="Non-payment",
        )
        
        handler.handle(cmd)
        
        tenant.refresh_from_db()
        self.assertEqual(tenant.status, TenantStatus.SUSPENDED)
        self.assertEqual(tenant.suspended_reason, "Non-payment")


class MembershipHandlerTests(TransactionTestCase):
    """Tests for membership handlers."""
    
    def setUp(self):
        """Set up test data."""
        self.plan, _ = Plan.objects.get_or_create(
            code="free",
            defaults={"name": "Free", "sort_order": 0}
        )
        
        self.owner = CoreUser.objects.create(
            email="owner@example.com",
            display_name="Owner",
            provider="local",
            legacy_user_id=10,
        )
        
        self.user = CoreUser.objects.create(
            email="user@example.com",
            display_name="User",
            provider="local",
            legacy_user_id=20,
        )
        
        self.tenant = Tenant.objects.create(
            slug="test-tenant",
            name="Test Tenant",
            plan=self.plan,
            status=TenantStatus.ACTIVE,
        )
        
        # Create owner membership
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.owner,
            role=TenantRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
    
    def test_membership_invite_success(self):
        """Test successful membership invitation."""
        handler = MembershipInviteHandler()
        cmd = MembershipInviteCommand(
            tenant_id=self.tenant.id,
            user_id=self.user.id,
            role=TenantRole.MEMBER,
            invited_by_id=self.owner.id,
            expires_in_days=7,
        )
        
        result = handler.handle(cmd)
        
        membership = TenantMembership.objects.get(id=result.membership_id)
        self.assertEqual(membership.status, MembershipStatus.PENDING)
        self.assertEqual(membership.role, TenantRole.MEMBER)
        self.assertIsNotNone(membership.invitation_expires_at)
    
    def test_membership_invite_already_exists(self):
        """Test invitation fails if active membership exists."""
        # Create existing membership
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        
        handler = MembershipInviteHandler()
        cmd = MembershipInviteCommand(
            tenant_id=self.tenant.id,
            user_id=self.user.id,
            role=TenantRole.MEMBER,
            invited_by_id=self.owner.id,
        )
        
        with self.assertRaises(MembershipExistsError):
            handler.handle(cmd)
    
    def test_membership_accept_success(self):
        """Test successful invitation acceptance."""
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.MEMBER,
            status=MembershipStatus.PENDING,
            invited_by=self.owner,
            invited_at=datetime.now(timezone.utc),
            invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        handler = MembershipAcceptHandler()
        cmd = MembershipAcceptCommand(membership_id=membership.id)
        
        handler.handle(cmd)
        
        membership.refresh_from_db()
        self.assertEqual(membership.status, MembershipStatus.ACTIVE)
        self.assertIsNotNone(membership.accepted_at)
    
    def test_membership_accept_expired(self):
        """Test accepting expired invitation fails."""
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.MEMBER,
            status=MembershipStatus.PENDING,
            invited_by=self.owner,
            invited_at=datetime.now(timezone.utc) - timedelta(days=10),
            invitation_expires_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        
        handler = MembershipAcceptHandler()
        cmd = MembershipAcceptCommand(membership_id=membership.id)
        
        with self.assertRaises(InvitationExpiredError):
            handler.handle(cmd)
