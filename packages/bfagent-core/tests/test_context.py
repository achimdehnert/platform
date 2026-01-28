"""Tests for request context management."""

import uuid
import pytest
from bfagent_core.context import (
    RequestContext,
    get_context,
    set_request_id,
    set_tenant,
    set_user_id,
    clear_context,
)


class TestRequestContext:
    """Tests for RequestContext dataclass."""
    
    def setup_method(self):
        clear_context()
    
    def teardown_method(self):
        clear_context()
    
    def test_empty_context(self):
        """Empty context should have all None values."""
        ctx = get_context()
        assert ctx.request_id is None
        assert ctx.tenant_id is None
        assert ctx.tenant_slug is None
        assert ctx.user_id is None
        assert not ctx.is_authenticated
        assert not ctx.has_tenant
    
    def test_set_request_id(self):
        """Should set and get request ID."""
        set_request_id("test-123")
        ctx = get_context()
        assert ctx.request_id == "test-123"
    
    def test_set_tenant(self):
        """Should set and get tenant info."""
        tenant_id = uuid.uuid4()
        set_tenant(tenant_id, "demo")
        ctx = get_context()
        assert ctx.tenant_id == tenant_id
        assert ctx.tenant_slug == "demo"
        assert ctx.has_tenant
    
    def test_set_user_id(self):
        """Should set and get user ID."""
        user_id = uuid.uuid4()
        set_user_id(user_id)
        ctx = get_context()
        assert ctx.user_id == user_id
        assert ctx.is_authenticated
    
    def test_clear_context(self):
        """Should clear all context values."""
        set_request_id("test")
        set_tenant(uuid.uuid4(), "demo")
        set_user_id(uuid.uuid4())
        
        clear_context()
        
        ctx = get_context()
        assert ctx.request_id is None
        assert ctx.tenant_id is None
        assert ctx.user_id is None
    
    def test_context_is_immutable(self):
        """RequestContext should be immutable."""
        ctx = get_context()
        with pytest.raises(AttributeError):
            ctx.request_id = "new-value"
