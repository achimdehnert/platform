"""
Weltenhub Core Tests
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, TenantUser
from apps.core.middleware import (
    TenantMiddleware,
    get_current_tenant,
    set_current_tenant,
    clear_current_tenant,
)

User = get_user_model()


class TenantMiddlewareTests(TestCase):
    """Tests for TenantMiddleware."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        TenantUser.objects.create(
            tenant=self.tenant,
            user=self.user,
            role="owner"
        )

    def tearDown(self):
        clear_current_tenant()

    def test_set_and_get_current_tenant(self):
        """Test thread-local tenant storage."""
        set_current_tenant(self.tenant)
        self.assertEqual(get_current_tenant(), self.tenant)

    def test_clear_current_tenant(self):
        """Test clearing tenant context."""
        set_current_tenant(self.tenant)
        clear_current_tenant()
        self.assertIsNone(get_current_tenant())

    def test_middleware_with_header(self):
        """Test tenant resolution from X-Tenant-ID header."""
        request = self.factory.get("/")
        request.META["HTTP_X_TENANT_ID"] = str(self.tenant.id)
        request.user = self.user
        request.session = {}

        def get_response(req):
            return None

        middleware = TenantMiddleware(get_response)
        middleware(request)

        self.assertEqual(request.tenant, self.tenant)


class HealthCheckTests(TestCase):
    """Tests for health check endpoint."""

    def test_health_check_returns_ok(self):
        """Test /health/ endpoint returns 200."""
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
