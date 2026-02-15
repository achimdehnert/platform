"""Tests for contextvars-based tenant context."""

import uuid

from django_tenancy.context import (
    clear_context,
    get_context,
    set_request_id,
    set_tenant,
    set_user,
)


class TestContext:
    """Tests for context propagation."""

    def setup_method(self):
        clear_context()

    def teardown_method(self):
        clear_context()

    def test_should_default_to_none(self):
        ctx = get_context()
        assert ctx.tenant_id is None
        assert ctx.tenant_slug is None
        assert ctx.user_id is None
        assert ctx.request_id is None

    def test_should_set_tenant(self):
        tid = uuid.uuid4()
        set_tenant(tid, "acme")
        ctx = get_context()
        assert ctx.tenant_id == tid
        assert ctx.tenant_slug == "acme"

    def test_should_set_user(self):
        uid = uuid.uuid4()
        set_user(uid)
        ctx = get_context()
        assert ctx.user_id == uid

    def test_should_generate_request_id(self):
        rid = set_request_id()
        ctx = get_context()
        assert ctx.request_id == rid
        assert len(rid) == 36  # UUID string

    def test_should_accept_custom_request_id(self):
        set_request_id("custom-id")
        ctx = get_context()
        assert ctx.request_id == "custom-id"

    def test_should_clear_all(self):
        set_tenant(uuid.uuid4(), "test")
        set_user(uuid.uuid4())
        set_request_id()
        clear_context()
        ctx = get_context()
        assert ctx.tenant_id is None
        assert ctx.user_id is None
        assert ctx.request_id is None

    def test_should_be_frozen(self):
        ctx = get_context()
        with __import__("pytest").raises(AttributeError):
            ctx.tenant_id = uuid.uuid4()
