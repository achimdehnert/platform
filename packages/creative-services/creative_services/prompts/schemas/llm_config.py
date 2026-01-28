"""
LLM configuration schema for prompt templates.
"""

from pydantic import BaseModel, Field


class RetryConfig(BaseModel):
    """Configuration for retry behavior on LLM errors."""

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts",
    )

    initial_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial delay before first retry",
    )

    max_delay_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Maximum delay between retries",
    )

    exponential_base: float = Field(
        default=2.0,
        ge=1.0,
        le=4.0,
        description="Base for exponential backoff",
    )

    retry_on_status_codes: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes that trigger a retry",
    )

    model_config = {"frozen": True}


class LLMConfig(BaseModel):
    """
    LLM configuration for a prompt template.

    Uses tier-based selection instead of direct model references
    for flexibility across different applications.
    """

    # Tier-based selection (preferred)
    tier: str = Field(
        default="standard",
        pattern=r"^(fast|standard|quality|premium)$",
        description="LLM tier: fast (cheap), standard, quality, premium (expensive)",
    )

    # Direct model override (optional)
    provider: str | None = Field(
        default=None,
        description="Override: specific provider (openai, anthropic, etc.)",
    )

    model: str | None = Field(
        default=None,
        description="Override: specific model name",
    )

    # Generation parameters
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0=deterministic, 2=creative)",
    )

    max_tokens: int = Field(
        default=1000,
        ge=1,
        le=128000,
        description="Maximum tokens in response",
    )

    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )

    frequency_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token frequency",
    )

    presence_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token presence",
    )

    # Timeout
    timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=600.0,
        description="Request timeout in seconds",
    )

    # Retry configuration
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry configuration for failed requests",
    )

    # Context limit (for pre-flight checks)
    context_limit: int | None = Field(
        default=None,
        ge=1000,
        description="Max context tokens (for pre-flight validation)",
    )

    model_config = {"frozen": True}

    def get_effective_model(self, tier_mapping: dict[str, tuple[str, str]]) -> tuple[str, str]:
        """
        Get the effective provider and model.

        Args:
            tier_mapping: Dict mapping tier names to (provider, model) tuples

        Returns:
            Tuple of (provider, model)
        """
        if self.provider and self.model:
            return self.provider, self.model

        if self.tier in tier_mapping:
            return tier_mapping[self.tier]

        # Fallback to standard tier
        return tier_mapping.get("standard", ("openai", "gpt-4o-mini"))
