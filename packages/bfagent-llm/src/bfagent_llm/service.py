"""
ResilientPromptService - LLM Calls with Resilience Patterns
============================================================

Provides resilient LLM calls with:
1. Retry with exponential backoff
2. Circuit Breaker per tier (prevent cascade failures)
3. Automatic tier fallback
4. Timeout handling
5. Cost tracking
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for a single tier.
    
    Prevents cascade failures by stopping requests to failing services.
    """
    
    tier_code: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_calls: int = 0
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit breaker {self.tier_code}: OPEN -> HALF_OPEN")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self) -> None:
        """Record successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker {self.tier_code}: HALF_OPEN -> CLOSED")
        else:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.tier_code}: HALF_OPEN -> OPEN")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.tier_code}: CLOSED -> OPEN")
    
    def reset(self) -> None:
        """Reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0


@dataclass
class LLMResponse:
    """Response from LLM call."""
    
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal("0"))
    raw_response: Optional[Dict[str, Any]] = None
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.tokens_in + self.tokens_out


@dataclass
class ExecutionResult:
    """Result of prompt execution."""
    
    success: bool
    response: Optional[LLMResponse] = None
    error: Optional[str] = None
    tier_used: Optional[str] = None
    retries: int = 0
    fallback_used: bool = False
    execution_id: Optional[int] = None


class LLMClientProtocol(Protocol):
    """Protocol for LLM clients."""
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> LLMResponse:
        """Execute LLM completion."""
        ...


@dataclass
class TierConfig:
    """Configuration for an LLM tier."""
    
    code: str
    model: str
    max_tokens: int = 2000
    temperature: float = 0.7
    fallback_tier: Optional[str] = None


class ResilientPromptService:
    """
    Resilient Prompt Service with retry, circuit breaker, and fallback.
    
    Usage:
        service = ResilientPromptService(llm_client)
        result = await service.execute(
            system_prompt="You are a helpful assistant.",
            user_prompt="Explain quantum computing.",
            tier="standard",
        )
    """
    
    # Default retry settings
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_RETRY_MULTIPLIER = 2.0
    DEFAULT_TIMEOUT = 60
    
    # Default tier configurations
    DEFAULT_TIERS = {
        "premium": TierConfig(
            code="premium",
            model="gpt-4o",
            max_tokens=4000,
            temperature=0.7,
            fallback_tier="standard",
        ),
        "standard": TierConfig(
            code="standard",
            model="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.7,
            fallback_tier="economy",
        ),
        "economy": TierConfig(
            code="economy",
            model="gpt-3.5-turbo",
            max_tokens=1000,
            temperature=0.7,
            fallback_tier=None,
        ),
    }
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        tiers: Optional[Dict[str, TierConfig]] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize ResilientPromptService.
        
        Args:
            llm_client: LLM client for API calls
            tiers: Optional tier configurations (default: standard tiers)
            max_retries: Maximum retry attempts
            timeout: Timeout in seconds
        """
        self.llm_client = llm_client
        self.tiers = tiers or self.DEFAULT_TIERS
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Circuit breakers per tier
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def _get_circuit_breaker(self, tier_code: str) -> CircuitBreaker:
        """Get or create circuit breaker for tier."""
        if tier_code not in self._circuit_breakers:
            self._circuit_breakers[tier_code] = CircuitBreaker(tier_code=tier_code)
        return self._circuit_breakers[tier_code]
    
    def _get_tier_chain(self, start_tier: str) -> List[TierConfig]:
        """Build tier fallback chain."""
        chain = []
        current = start_tier
        
        while current and current in self.tiers:
            tier = self.tiers[current]
            if tier in chain:
                break  # Prevent infinite loop
            chain.append(tier)
            current = tier.fallback_tier
        
        return chain
    
    def _estimate_cost(
        self,
        tokens_in: int,
        tokens_out: int,
        model: str,
    ) -> Decimal:
        """Estimate cost based on token usage."""
        PRICES = {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "claude-3-opus": {"input": 15.00, "output": 75.00},
            "claude-3-sonnet": {"input": 3.00, "output": 15.00},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
        }
        
        price = None
        for model_key, model_price in PRICES.items():
            if model_key in model.lower():
                price = model_price
                break
        
        if not price:
            price = {"input": 1.00, "output": 3.00}
        
        input_cost = Decimal(str(tokens_in * price["input"] / 1_000_000))
        output_cost = Decimal(str(tokens_out * price["output"] / 1_000_000))
        
        return input_cost + output_cost
    
    async def execute(
        self,
        system_prompt: str,
        user_prompt: str,
        tier: str = "standard",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute prompt with full resilience.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            tier: Starting tier (default: standard)
            model: Override model (optional)
            max_tokens: Override max tokens (optional)
            temperature: Override temperature (optional)
            
        Returns:
            ExecutionResult with response or error
        """
        tier_chain = self._get_tier_chain(tier)
        
        if not tier_chain:
            return ExecutionResult(
                success=False,
                error=f"Unknown tier: {tier}",
            )
        
        last_error = None
        total_retries = 0
        fallback_used = False
        
        for i, tier_config in enumerate(tier_chain):
            if i > 0:
                fallback_used = True
                logger.info(f"Falling back to tier: {tier_config.code}")
            
            # Check circuit breaker
            circuit = self._get_circuit_breaker(tier_config.code)
            if not circuit.can_execute():
                logger.warning(f"Circuit breaker OPEN for tier: {tier_config.code}")
                continue
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            # Get settings
            use_model = model or tier_config.model
            use_max_tokens = max_tokens or tier_config.max_tokens
            use_temperature = temperature if temperature is not None else tier_config.temperature
            
            # Try with retries
            result = await self._execute_with_retry(
                messages=messages,
                model=use_model,
                max_tokens=use_max_tokens,
                temperature=use_temperature,
                circuit=circuit,
            )
            
            total_retries += result.retries
            
            if result.success:
                result.tier_used = tier_config.code
                result.fallback_used = fallback_used
                result.retries = total_retries
                return result
            
            last_error = result.error
        
        return ExecutionResult(
            success=False,
            error=last_error or "All tiers failed",
            retries=total_retries,
            fallback_used=fallback_used,
        )
    
    async def _execute_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        circuit: CircuitBreaker,
    ) -> ExecutionResult:
        """Execute with retry logic."""
        last_error = None
        retries = 0
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                
                response = await asyncio.wait_for(
                    self.llm_client.complete(
                        messages=messages,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    ),
                    timeout=self.timeout,
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                response.latency_ms = latency_ms
                
                if response.cost == Decimal("0"):
                    response.cost = self._estimate_cost(
                        response.tokens_in,
                        response.tokens_out,
                        model,
                    )
                
                circuit.record_success()
                
                return ExecutionResult(
                    success=True,
                    response=response,
                    retries=retries,
                )
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout}s"
                logger.warning(f"LLM timeout (attempt {attempt + 1}): {last_error}")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM error (attempt {attempt + 1}): {e}")
            
            retries += 1
            
            if attempt < self.max_retries:
                delay = self.DEFAULT_RETRY_DELAY * (self.DEFAULT_RETRY_MULTIPLIER ** attempt)
                await asyncio.sleep(delay)
        
        circuit.record_failure()
        
        return ExecutionResult(
            success=False,
            error=last_error,
            retries=retries,
        )
    
    def execute_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        tier: str = "standard",
        **kwargs,
    ) -> ExecutionResult:
        """Synchronous wrapper for execute."""
        return asyncio.run(
            self.execute(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tier=tier,
                **kwargs,
            )
        )
    
    def get_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            code: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time,
            }
            for code, cb in self._circuit_breakers.items()
        }
    
    def reset_circuit(self, tier_code: str) -> None:
        """Reset circuit breaker for tier."""
        if tier_code in self._circuit_breakers:
            self._circuit_breakers[tier_code].reset()
            logger.info(f"Circuit breaker reset: {tier_code}")
