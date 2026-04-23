"""Tests for TenantModelAdmin (ADR-137)."""

from unittest.mock import MagicMock, patch

from django_tenancy.admin import TenantModelAdmin
from django_tenancy.module_models import ModuleSubscription


class TestTenantModelAdmin:
    """Test that TenantModelAdmin bypasses auto-filter."""

    def test_should_call_unscoped_when_available(self):
        admin_instance = TenantModelAdmin(
            ModuleSubscription, MagicMock()
        )
        mock_manager = MagicMock()
        mock_manager.unscoped.return_value = MagicMock()

        with patch.object(
            type(ModuleSubscription),
            "_default_manager",
            new_callable=lambda: property(lambda self: mock_manager),
        ):
            admin_instance.get_queryset(MagicMock())

        mock_manager.unscoped.assert_called_once()

    def test_should_fallback_to_get_queryset(self):
        admin_instance = TenantModelAdmin(
            ModuleSubscription, MagicMock()
        )
        mock_manager = MagicMock(spec=["get_queryset"])
        del mock_manager.unscoped  # no unscoped method

        with patch.object(
            type(ModuleSubscription),
            "_default_manager",
            new_callable=lambda: property(lambda self: mock_manager),
        ):
            admin_instance.get_queryset(MagicMock())

        mock_manager.get_queryset.assert_called_once()
