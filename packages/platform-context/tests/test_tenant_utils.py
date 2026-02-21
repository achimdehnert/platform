"""
Tests for platform_context.tenant_utils (ADR-056 Phase 0).

Tests run WITHOUT django-tenants installed — all django-tenants imports
are lazy/optional, so the module must work standalone.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# middleware
# ---------------------------------------------------------------------------

class TestTenantPropagationMiddleware:
    def _make_middleware(self, get_response=None):
        from platform_context.tenant_utils.middleware import TenantPropagationMiddleware
        return TenantPropagationMiddleware(get_response or (lambda r: r))

    def test_should_pass_through_when_tenant_already_set(self):
        mw = self._make_middleware()
        request = MagicMock()
        request.tenant = MagicMock()  # already set by django-tenants
        request.headers = {"X-Tenant-Schema": "acme"}
        mw(request)
        # No schema switching expected

    def test_should_pass_through_when_no_header(self):
        mw = self._make_middleware()
        request = MagicMock(spec=["headers"])
        request.headers = {}
        mw(request)  # must not raise

    def test_should_reject_unsafe_schema_name(self):
        from platform_context.tenant_utils.middleware import _is_safe_schema_name
        assert not _is_safe_schema_name("acme; DROP TABLE")
        assert not _is_safe_schema_name("acme-corp")
        assert not _is_safe_schema_name("")
        assert not _is_safe_schema_name("ACME")

    def test_should_accept_safe_schema_name(self):
        from platform_context.tenant_utils.middleware import _is_safe_schema_name
        assert _is_safe_schema_name("acme_corp")
        assert _is_safe_schema_name("tenant_1")
        assert _is_safe_schema_name("test_tenant_a")


# ---------------------------------------------------------------------------
# http_client
# ---------------------------------------------------------------------------

class TestTenantAwareHttpClient:
    def _make_client(self, base_url="http://service-b:8000"):
        from platform_context.tenant_utils.http_client import TenantAwareHttpClient
        return TenantAwareHttpClient(base_url)

    def test_should_include_tenant_header_in_get(self):
        client = self._make_client()
        with patch("platform_context.tenant_utils.http_client.httpx") as mock_httpx:
            mock_httpx.get.return_value = MagicMock(status_code=200)
            with patch(
                "platform_context.tenant_utils.http_client._get_current_schema",
                return_value="acme_corp",
            ):
                client.get("/api/v1/items/")
            call_headers = mock_httpx.get.call_args[1]["headers"]
            assert call_headers["X-Tenant-Schema"] == "acme_corp"

    def test_should_include_tenant_header_in_post(self):
        client = self._make_client()
        with patch("platform_context.tenant_utils.http_client.httpx") as mock_httpx:
            mock_httpx.post.return_value = MagicMock(status_code=201)
            with patch(
                "platform_context.tenant_utils.http_client._get_current_schema",
                return_value="contoso",
            ):
                client.post("/api/v1/items/", json={"name": "test"})
            call_headers = mock_httpx.post.call_args[1]["headers"]
            assert call_headers["X-Tenant-Schema"] == "contoso"

    def test_should_strip_trailing_slash_from_base_url(self):
        from platform_context.tenant_utils.http_client import TenantAwareHttpClient
        client = TenantAwareHttpClient("http://service-b:8000/")
        assert client.base_url == "http://service-b:8000"

    def test_should_fallback_to_public_schema_when_no_connection(self):
        from platform_context.tenant_utils.http_client import _get_current_schema
        with patch("platform_context.tenant_utils.http_client.connection") as mock_conn:
            mock_conn.schema_name = None
            result = _get_current_schema()
        assert result == "public"

    def test_should_merge_extra_headers(self):
        from platform_context.tenant_utils.http_client import TenantAwareHttpClient
        client = TenantAwareHttpClient(
            "http://service-b:8000",
            extra_headers={"Authorization": "Bearer token123"},
        )
        with patch(
            "platform_context.tenant_utils.http_client._get_current_schema",
            return_value="acme",
        ):
            headers = client._headers()
        assert headers["Authorization"] == "Bearer token123"
        assert headers["X-Tenant-Schema"] == "acme"


# ---------------------------------------------------------------------------
# celery
# ---------------------------------------------------------------------------

class TestCeleryUtils:
    def test_should_inject_tenant_schema_into_task_kwargs(self):
        from platform_context.tenant_utils.celery import send_cross_service_task
        with patch("platform_context.tenant_utils.celery.current_app") as mock_app:
            with patch(
                "platform_context.tenant_utils.celery._get_current_schema",
                return_value="acme_corp",
            ):
                send_cross_service_task(
                    "risk_hub.tasks.sync_assessment",
                    kwargs={"assessment_id": 42},
                )
            call_kwargs = mock_app.send_task.call_args[1]["kwargs"]
            assert call_kwargs["_tenant_schema"] == "acme_corp"
            assert call_kwargs["assessment_id"] == 42

    def test_should_use_empty_args_by_default(self):
        from platform_context.tenant_utils.celery import send_cross_service_task
        with patch("platform_context.tenant_utils.celery.current_app") as mock_app:
            with patch(
                "platform_context.tenant_utils.celery._get_current_schema",
                return_value="public",
            ):
                send_cross_service_task("some.task")
            call_args = mock_app.send_task.call_args[1]["args"]
            assert call_args == []

    def test_tenant_aware_task_should_pop_schema_from_kwargs(self):
        from platform_context.tenant_utils.celery import TenantAwareTask

        class ConcreteTask(TenantAwareTask):
            received_kwargs: dict = {}

            def __call__(self, *args, **kwargs):
                ConcreteTask.received_kwargs = kwargs

        task = ConcreteTask()
        with patch(
            "platform_context.tenant_utils.celery.schema_context",
            side_effect=ImportError,
        ):
            task(_tenant_schema="acme", data="value")

        assert "_tenant_schema" not in ConcreteTask.received_kwargs
        assert ConcreteTask.received_kwargs.get("data") == "value"


# ---------------------------------------------------------------------------
# provisioning
# ---------------------------------------------------------------------------

class TestProvisioning:
    def test_should_reject_invalid_schema_name(self):
        from platform_context.tenant_utils.provisioning import _validate_schema_name
        with pytest.raises(ValueError, match="Invalid schema_name"):
            _validate_schema_name("ACME-Corp")

    def test_should_reject_reserved_schema_names(self):
        from platform_context.tenant_utils.provisioning import _validate_schema_name
        with pytest.raises(ValueError, match="Reserved"):
            _validate_schema_name("public")
        with pytest.raises(ValueError, match="Reserved"):
            _validate_schema_name("pg_catalog")

    def test_should_accept_valid_schema_name(self):
        from platform_context.tenant_utils.provisioning import _validate_schema_name
        _validate_schema_name("acme_corp")  # must not raise
        _validate_schema_name("tenant_42")

    def test_should_dispatch_to_services(self):
        from platform_context.tenant_utils.provisioning import (
            TenantProvisioningRequest,
            _dispatch_to_services,
        )
        req = TenantProvisioningRequest(
            schema_name="acme_corp",
            name="ACME",
            company_name="ACME GmbH",
            contact_email="admin@acme.de",
        )
        with patch("platform_context.tenant_utils.provisioning.current_app") as mock_app:
            mock_app.send_task.return_value = MagicMock(id="task-123")
            result = _dispatch_to_services(req, ["risk_hub", "travel_beat"])
        assert len(result) == 2
        assert mock_app.send_task.call_count == 2

    def test_should_return_empty_list_when_no_services(self):
        from platform_context.tenant_utils.provisioning import (
            TenantProvisioningRequest,
            _dispatch_to_services,
        )
        req = TenantProvisioningRequest(
            schema_name="acme_corp",
            name="ACME",
            company_name="ACME GmbH",
            contact_email="admin@acme.de",
        )
        result = _dispatch_to_services(req, [])
        assert result == []


# ---------------------------------------------------------------------------
# __init__ exports
# ---------------------------------------------------------------------------

class TestTenantUtilsInit:
    def test_should_export_tenant_header_constant(self):
        from platform_context.tenant_utils import TENANT_HEADER
        assert TENANT_HEADER == "X-Tenant-Schema"
