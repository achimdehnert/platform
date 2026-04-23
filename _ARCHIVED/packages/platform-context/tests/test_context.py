"""Tests for platform_context.context module."""

import uuid

from platform_context.context import (
    RequestContext,
    clear_context,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
)


class TestRequestContext:
    """Tests for RequestContext dataclass."""

    def test_should_return_empty_context_by_default(self):
        clear_context()
        ctx = get_context()
        assert ctx.request_id is None
        assert ctx.tenant_id is None
        assert ctx.tenant_slug is None
        assert ctx.user_id is None

    def test_should_set_and_get_request_id(self):
        clear_context()
        set_request_id("req-123")
        ctx = get_context()
        assert ctx.request_id == "req-123"

    def test_should_set_and_get_tenant(self):
        clear_context()
        tid = uuid.uuid4()
        set_tenant(tid, "demo")
        ctx = get_context()
        assert ctx.tenant_id == tid
        assert ctx.tenant_slug == "demo"

    def test_should_set_and_get_user_id(self):
        clear_context()
        uid = uuid.uuid4()
        set_user_id(uid)
        ctx = get_context()
        assert ctx.user_id == uid

    def test_should_report_is_authenticated(self):
        clear_context()
        ctx = get_context()
        assert ctx.is_authenticated is False

        set_user_id(uuid.uuid4())
        ctx = get_context()
        assert ctx.is_authenticated is True

    def test_should_report_has_tenant(self):
        clear_context()
        ctx = get_context()
        assert ctx.has_tenant is False

        set_tenant(uuid.uuid4(), "test")
        ctx = get_context()
        assert ctx.has_tenant is True

    def test_should_clear_context(self):
        set_request_id("req-456")
        set_tenant(uuid.uuid4(), "slug")
        set_user_id(uuid.uuid4())
        clear_context()
        ctx = get_context()
        assert ctx.request_id is None
        assert ctx.tenant_id is None
        assert ctx.user_id is None

    def test_should_be_frozen(self):
        clear_context()
        ctx = get_context()
        assert isinstance(ctx, RequestContext)
        try:
            ctx.request_id = "new"  # type: ignore
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass
