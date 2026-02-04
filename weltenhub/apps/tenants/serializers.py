"""
Weltenhub Tenants Serializers
"""

from rest_framework import serializers
from .models import Tenant, TenantUser


class TenantSerializer(serializers.ModelSerializer):
    """Tenant serializer."""

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "settings",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]


class TenantUserSerializer(serializers.ModelSerializer):
    """Tenant user membership serializer."""

    tenant_name = serializers.CharField(
        source="tenant.name",
        read_only=True
    )
    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    class Meta:
        model = TenantUser
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "user",
            "username",
            "role",
            "is_active",
            "joined_at",
        ]
        read_only_fields = ["id", "joined_at"]
