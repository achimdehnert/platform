"""Tests for tenant context decorators."""

import uuid

import pytest

from django_tenancy.context import clear_context, get_context
from django_tenancy.decorators import tenant_context, with_tenant_from_arg


@pytest.mark.django_db
class TestTenantContext:
    """Tests for tenant_context context manager."""

    def setup_method(self):
        clear_context()

    def teardown_method(self):
        clear_context()

    def test_should_set_and_clear_context(self):
        tid = uuid.uuid4()
        with tenant_context(tid, "test"):
            ctx = get_context()
            assert ctx.tenant_id == tid
            assert ctx.tenant_slug == "test"

        ctx = get_context()
        assert ctx.tenant_id is None

    def test_should_clear_on_exception(self):
        tid = uuid.uuid4()
        try:
            with tenant_context(tid):
                raise ValueError("boom")
        except ValueError:
            pass

        ctx = get_context()
        assert ctx.tenant_id is None


@pytest.mark.django_db
class TestWithTenantFromArg:
    """Tests for @with_tenant_from_arg decorator."""

    def setup_method(self):
        clear_context()

    def teardown_method(self):
        clear_context()

    def test_should_set_context_from_kwarg(self):
        captured = {}

        @with_tenant_from_arg("tenant_id")
        def my_func(tenant_id: str, data: str):
            ctx = get_context()
            captured["tid"] = ctx.tenant_id
            return "ok"

        tid = uuid.uuid4()
        result = my_func(tenant_id=str(tid), data="hello")
        assert result == "ok"
        assert captured["tid"] == tid

    def test_should_work_without_tenant_arg(self):
        @with_tenant_from_arg("tenant_id")
        def my_func(data: str):
            return data

        result = my_func(data="hello")
        assert result == "hello"
