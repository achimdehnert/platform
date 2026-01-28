"""
Generic LLM client implementations.

Provides ready-to-use clients for popular LLM providers.
"""

from typing import Any

from ..execution import LLMResponse
from ..exceptions import LLMError


class OpenAIClient:
    """
    OpenAI API client for the Prompt Template System.
    
    Requires: pip install openai
    
    Example:
        client = OpenAIClient(api_key="sk-...")
        response = await client.generate(
            system_prompt="You are helpful.",
            user_prompt="Hello!",
            model="gpt-4",
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        organization: str | None = None,
        base_url: str | None = None,
        default_model: str = "gpt-4",
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
            organization: OpenAI organization ID
            base_url: Custom API base URL
            default_model: Default model to use
        """
        try:
            import openai
            self._openai = openai
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAIClient. "
                "Install with: pip install openai"
            )
        
        self._api_key = api_key
        self._organization = organization
        self._base_url = base_url
        self._default_model = default_model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create async OpenAI client."""
        if self._client is None:
            self._client = self._openai.AsyncOpenAI(
                api_key=self._api_key,
                organization=self._organization,
                base_url=self._base_url,
            )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate response from OpenAI.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name (uses default if not provided)
            temperature: Temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            LLMResponse with content and metadata
        """
        client = self._get_client()
        model = model or self._default_model
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            
            # Extract usage
            usage = response.usage
            tokens_input = usage.prompt_tokens if usage else 0
            tokens_output = usage.completion_tokens if usage else 0
            
            # Calculate cost
            cost = self._calculate_cost(model, tokens_input, tokens_output)
            
            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=model,
                provider="openai",
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_dollars=cost,
                finish_reason=response.choices[0].finish_reason or "stop",
                raw_response=response.model_dump(),
            )
            
        except self._openai.RateLimitError as e:
            raise LLMError(
                message=str(e),
                provider="openai",
                status_code=429,
                retryable=True,
            )
        except self._openai.APITimeoutError as e:
            raise LLMError(
                message=str(e),
                provider="openai",
                retryable=True,
            )
        except self._openai.APIError as e:
            raise LLMError(
                message=str(e),
                provider="openai",
                status_code=getattr(e, "status_code", None),
                retryable=getattr(e, "status_code", 500) >= 500,
            )

    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost based on model and tokens."""
        # Pricing per 1K tokens (as of 2024)
        pricing = {
            "gpt-4": (0.03, 0.06),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4-turbo-preview": (0.01, 0.03),
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "gpt-3.5-turbo-16k": (0.003, 0.004),
        }
        
        input_rate, output_rate = pricing.get(model, (0.01, 0.03))
        return (tokens_input / 1000 * input_rate) + (tokens_output / 1000 * output_rate)


class AnthropicClient:
    """
    Anthropic API client for the Prompt Template System.
    
    Requires: pip install anthropic
    
    Example:
        client = AnthropicClient(api_key="sk-ant-...")
        response = await client.generate(
            system_prompt="You are helpful.",
            user_prompt="Hello!",
            model="claude-3-sonnet-20240229",
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "claude-3-sonnet-20240229",
    ):
        """
        Initialize Anthropic client.
        
        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            base_url: Custom API base URL
            default_model: Default model to use
        """
        try:
            import anthropic
            self._anthropic = anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required for AnthropicClient. "
                "Install with: pip install anthropic"
            )
        
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create async Anthropic client."""
        if self._client is None:
            self._client = self._anthropic.AsyncAnthropic(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate response from Anthropic.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name
            temperature: Temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with content and metadata
        """
        client = self._get_client()
        model = model or self._default_model
        
        try:
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            
            # Extract content
            content = ""
            if response.content:
                content = response.content[0].text if response.content[0].type == "text" else ""
            
            # Extract usage
            tokens_input = response.usage.input_tokens if response.usage else 0
            tokens_output = response.usage.output_tokens if response.usage else 0
            
            # Calculate cost
            cost = self._calculate_cost(model, tokens_input, tokens_output)
            
            return LLMResponse(
                content=content,
                model=model,
                provider="anthropic",
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_dollars=cost,
                finish_reason=response.stop_reason or "stop",
                raw_response=response.model_dump(),
            )
            
        except self._anthropic.RateLimitError as e:
            raise LLMError(
                message=str(e),
                provider="anthropic",
                status_code=429,
                retryable=True,
            )
        except self._anthropic.APITimeoutError as e:
            raise LLMError(
                message=str(e),
                provider="anthropic",
                retryable=True,
            )
        except self._anthropic.APIError as e:
            raise LLMError(
                message=str(e),
                provider="anthropic",
                status_code=getattr(e, "status_code", None),
                retryable=getattr(e, "status_code", 500) >= 500,
            )

    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost based on model and tokens."""
        # Pricing per 1K tokens (as of 2024)
        pricing = {
            "claude-3-opus-20240229": (0.015, 0.075),
            "claude-3-sonnet-20240229": (0.003, 0.015),
            "claude-3-haiku-20240307": (0.00025, 0.00125),
            "claude-3-5-sonnet-20240620": (0.003, 0.015),
        }
        
        input_rate, output_rate = pricing.get(model, (0.003, 0.015))
        return (tokens_input / 1000 * input_rate) + (tokens_output / 1000 * output_rate)


def create_llm_client(
    provider: str = "openai",
    api_key: str | None = None,
    **kwargs: Any,
) -> OpenAIClient | AnthropicClient:
    """
    Factory function to create an LLM client.
    
    Args:
        provider: Provider name ("openai" or "anthropic")
        api_key: API key
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Configured LLM client
        
    Example:
        client = create_llm_client("openai", api_key="sk-...")
        client = create_llm_client("anthropic")
    """
    if provider.lower() == "openai":
        return OpenAIClient(api_key=api_key, **kwargs)
    elif provider.lower() == "anthropic":
        return AnthropicClient(api_key=api_key, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: openai, anthropic")
