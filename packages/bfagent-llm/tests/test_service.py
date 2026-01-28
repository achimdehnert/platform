"""Tests for ResilientPromptService."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from bfagent_llm.service import (
    ResilientPromptService,
    CircuitBreaker,
    CircuitState,
    LLMResponse,
    TierConfig,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    def test_initial_state_closed(self):
        """Should start in CLOSED state."""
        cb = CircuitBreaker(tier_code="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()
    
    def test_opens_after_threshold(self):
        """Should open after failure threshold."""
        cb = CircuitBreaker(tier_code="test", failure_threshold=3)
        
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()
    
    def test_success_resets_failure_count(self):
        """Should reset failure count on success."""
        cb = CircuitBreaker(tier_code="test", failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED
    
    def test_reset(self):
        """Should reset to initial state."""
        cb = CircuitBreaker(tier_code="test", failure_threshold=1)
        cb.record_failure()
        
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


class TestLLMResponse:
    """Tests for LLMResponse."""
    
    def test_total_tokens(self):
        """Should calculate total tokens."""
        response = LLMResponse(
            content="test",
            model="gpt-4o-mini",
            tokens_in=100,
            tokens_out=50,
        )
        assert response.total_tokens == 150


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, response: LLMResponse = None, error: Exception = None):
        self.response = response or LLMResponse(
            content="Test response",
            model="gpt-4o-mini",
            tokens_in=10,
            tokens_out=20,
        )
        self.error = error
        self.call_count = 0
    
    async def complete(self, messages, model, max_tokens, temperature, **kwargs):
        self.call_count += 1
        if self.error:
            raise self.error
        return self.response


class TestResilientPromptService:
    """Tests for ResilientPromptService."""
    
    @pytest.fixture
    def mock_client(self):
        return MockLLMClient()
    
    @pytest.fixture
    def service(self, mock_client):
        return ResilientPromptService(
            llm_client=mock_client,
            max_retries=2,
            timeout=10,
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, service):
        """Should execute successfully."""
        result = await service.execute(
            system_prompt="You are helpful.",
            user_prompt="Hello!",
            tier="standard",
        )
        
        assert result.success
        assert result.response is not None
        assert result.response.content == "Test response"
    
    @pytest.mark.asyncio
    async def test_execute_with_retries(self, mock_client):
        """Should retry on failure."""
        # Fail twice, then succeed
        call_count = 0
        original_complete = mock_client.complete
        
        async def failing_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return await original_complete(*args, **kwargs)
        
        mock_client.complete = failing_complete
        
        service = ResilientPromptService(
            llm_client=mock_client,
            max_retries=3,
            timeout=10,
        )
        
        result = await service.execute(
            system_prompt="",
            user_prompt="Hello!",
        )
        
        assert result.success
        assert result.retries == 2
    
    @pytest.mark.asyncio
    async def test_tier_fallback(self):
        """Should fall back to next tier on failure."""
        # Create client that fails for premium but works for standard
        class TierAwareClient:
            async def complete(self, messages, model, **kwargs):
                if "gpt-4o" in model and "mini" not in model:
                    raise Exception("Premium tier unavailable")
                return LLMResponse(
                    content="Fallback response",
                    model=model,
                    tokens_in=10,
                    tokens_out=20,
                )
        
        service = ResilientPromptService(
            llm_client=TierAwareClient(),
            max_retries=1,
        )
        
        result = await service.execute(
            system_prompt="",
            user_prompt="Hello!",
            tier="premium",
        )
        
        assert result.success
        assert result.fallback_used
        assert result.tier_used == "standard"
    
    def test_get_circuit_status(self, service):
        """Should return circuit breaker status."""
        # Trigger circuit breaker
        service._get_circuit_breaker("test")
        
        status = service.get_circuit_status()
        assert "test" in status
        assert status["test"]["state"] == "closed"
    
    def test_reset_circuit(self, service):
        """Should reset circuit breaker."""
        cb = service._get_circuit_breaker("test")
        cb.record_failure()
        cb.record_failure()
        
        service.reset_circuit("test")
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
