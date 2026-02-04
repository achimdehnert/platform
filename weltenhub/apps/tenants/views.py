"""
Weltenhub Tenants API Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Tenant, TenantUser
from .serializers import TenantSerializer, TenantUserSerializer


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Tenants.

    Users can only see tenants they belong to.
    """

    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only tenants user has access to."""
        return Tenant.objects.filter(
            members__user=self.request.user,
            members__is_active=True,
            is_active=True
        ).distinct()

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Get current tenant from middleware."""
        from apps.core.middleware import get_current_tenant

        tenant = get_current_tenant()
        if tenant:
            serializer = self.get_serializer(tenant)
            return Response(serializer.data)
        return Response({"detail": "No tenant selected"}, status=400)

    @action(detail=True, methods=["post"])
    def select(self, request, pk=None):
        """Select this tenant for current session."""
        tenant = self.get_object()
        request.session["tenant_id"] = str(tenant.id)
        return Response({"status": "Tenant selected", "tenant": tenant.name})


class TenantUserViewSet(viewsets.ModelViewSet):
    """API endpoint for Tenant memberships."""

    serializer_class = TenantUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return memberships for current user."""
        return TenantUser.objects.filter(
            user=self.request.user
        ).select_related("tenant", "user")
