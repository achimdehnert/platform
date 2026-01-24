"""
Base LLM Client
===============

Abstract base class for all LLM provider clients.

Usage:
    from apps.core.services.llm import BaseLLMClient

    class MyClient(BaseLLMClient):
        def _generate(self, request):
            # Implementation
            pass
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional, Type, TypeVar

from .exceptions import LLMConnectionError, LLMException, LLMRateLimitError, LLMValidationError
from .models import LLM_PRICING, LLMConfig, LLMRequest, LLMResponse, ResponseFormat, TokenUsage

# Try to import Pydantic
try:
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = None
    PydanticValidationError = Exception
    PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseModel")


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    Provides common functionality:
    - Configuration management
    - Request/response handling
    - Token estimation
    - Cost calculation
    - Retry logic
    - Logging

    Subclasses must implement:
    - _generate(): Core generation logic
    - _generate_structured(): Structured output generation

    Example:
        class OpenAIClient(BaseLLMClient):
            def _generate(self, request):
                # OpenAI-specific implementation
                pass
    """

    # Provider identifier - override in subclasses
    provider: str = "base"

    def __init__(self, config: Optional[LLMConfig] = None, **kwargs):
        """
        Initialize LLM client.

        Args:
            config: LLMConfig instance
            **kwargs: Override config values
        """
        self.config = config or LLMConfig()

        # Apply kwargs overrides
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        self.logger = logging.getLogger(f"llm.{self.provider}")
        self._client = None

        # Initialize provider client
        self._init_client()

    @abstractmethod
    def _init_client(self) -> None:
        """
        Initialize the provider-specific client.

        Called during __init__. Should set self._client.

        Raises:
            LLMConnectionError: If client initialization fails
        """
        pass

    @abstractmethod
    def _generate(self, request: LLMRequest) -> LLMResponse:
        """
        Core generation logic - must be implemented by subclasses.

        Args:
            request: LLMRequest with generation parameters

        Returns:
            LLMResponse with generated content
        """
        pass

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text from prompt.

        This is the main public interface for text generation.

        Args:
            prompt: User prompt
            system_prompt: System/instruction prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse with generated content

        Example:
            response = client.generate(
                prompt="Write a haiku about coding",
                temperature=0.9
            )
            print(response.content)
        """
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or self.config.default_max_tokens,
            **kwargs,
        )

        return self._execute_with_retry(request)

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> T:
        """
        Generate structured output matching a Pydantic model.

        Uses function calling or JSON mode to ensure output
        matches the provided schema.

        Args:
            prompt: User prompt
            response_model: Pydantic model class
            system_prompt: System/instruction prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Instance of response_model with validated data

        Raises:
            LLMValidationError: If output doesn't match schema

        Example:
            class BookInfo(BaseModel):
                title: str
                author: str
                year: int

            book = client.generate_structured(
                prompt="Parse: 1984 by George Orwell, 1949",
                response_model=BookInfo
            )
            print(book.title)  # "1984"
        """
        if not PYDANTIC_AVAILABLE:
            raise LLMException("Pydantic required for structured output")

        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or self.config.default_max_tokens,
            response_format=ResponseFormat.STRUCTURED,
            response_schema=response_model,
            **kwargs,
        )

        response = self._execute_with_retry(request)

        if not response.success:
            raise LLMValidationError(f"Generation failed: {response.error}")

        if response.structured_output:
            return response.structured_output

        # Fallback: try to parse content as JSON
        try:
            import json

            data = json.loads(response.content)
            return response_model.model_validate(data)
        except Exception as e:
            raise LLMValidationError(
                f"Failed to parse structured output: {e}", content=response.content
            )

    def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate text with streaming.

        Yields chunks of generated text as they become available.

        Args:
            prompt: User prompt
            system_prompt: System/instruction prompt
            **kwargs: Additional parameters

        Yields:
            Text chunks as they are generated

        Example:
            for chunk in client.generate_stream("Tell me a story"):
                print(chunk, end="", flush=True)
        """
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            stream=True,
            temperature=kwargs.get("temperature", self.config.default_temperature),
            max_tokens=kwargs.get("max_tokens", self.config.default_max_tokens),
            **kwargs,
        )

        yield from self._generate_stream(request)

    def _generate_stream(self, request: LLMRequest) -> Generator[str, None, None]:
        """
        Streaming generation - override in subclasses.

        Default implementation falls back to non-streaming.
        """
        response = self._generate(request)
        if response.success and response.content:
            yield response.content

    def _execute_with_retry(self, request: LLMRequest) -> LLMResponse:
        """
        Execute request with retry logic.

        Retries on transient errors (rate limits, connection issues).
        """
        last_error = None

        for attempt in range(self.config.retry_count + 1):
            try:
                start_time = time.perf_counter()
                response = self._generate(request)

                # Add latency if not set
                if response.latency_ms is None:
                    response.latency_ms = int((time.perf_counter() - start_time) * 1000)

                return response

            except LLMRateLimitError as e:
                last_error = e
                if attempt < self.config.retry_count:
                    wait_time = e.retry_after or (self.config.retry_delay * (2**attempt))
                    self.logger.warning(
                        f"Rate limited, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.config.retry_count})"
                    )
                    time.sleep(wait_time)

            except LLMConnectionError as e:
                last_error = e
                if attempt < self.config.retry_count:
                    wait_time = self.config.retry_delay * (2**attempt)
                    self.logger.warning(
                        f"Connection error, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.config.retry_count})"
                    )
                    time.sleep(wait_time)

            except LLMException:
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error in LLM call: {e}")
                raise LLMException(f"Unexpected error: {e}") from e

        # All retries exhausted
        raise last_error or LLMException("All retry attempts failed")

    # ==================== Utility Methods ====================

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a rough approximation (~4 characters per token for English).
        For more accurate counts, use tiktoken for OpenAI models.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def calculate_cost(self, usage: TokenUsage, model: Optional[str] = None) -> float:
        """
        Calculate cost for token usage.

        Args:
            usage: TokenUsage with token counts
            model: Model name (uses config model if not provided)

        Returns:
            Estimated cost in USD
        """
        model = model or self.config.effective_model

        # Find pricing
        provider_pricing = LLM_PRICING.get(self.provider, {})
        model_pricing = provider_pricing.get(model, {})

        if not model_pricing:
            # Try partial match
            for m, p in provider_pricing.items():
                if m in model or model in m:
                    model_pricing = p
                    break

        if not model_pricing:
            self.logger.warning(f"No pricing found for {self.provider}/{model}")
            return 0.0

        input_cost = (usage.prompt_tokens / 1000) * model_pricing.get("input", 0)
        output_cost = (usage.completion_tokens / 1000) * model_pricing.get("output", 0)

        return input_cost + output_cost

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the configured model.

        Returns:
            Dict with model information
        """
        return {
            "provider": self.provider,
            "model": self.config.effective_model,
            "endpoint": self.config.effective_endpoint,
            "default_temperature": self.config.default_temperature,
            "default_max_tokens": self.config.default_max_tokens,
        }

    def health_check(self) -> bool:
        """
        Check if the client is properly configured and can connect.

        Returns:
            True if healthy
        """
        try:
            response = self.generate(prompt="Say 'OK'", max_tokens=5)
            return response.success
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
