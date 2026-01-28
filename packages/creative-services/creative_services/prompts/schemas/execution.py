"""
Prompt Execution schema - tracks individual template executions.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class ExecutionStatus(str, Enum):
    """Status of a prompt execution."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
    DRY_RUN = "dry_run"


class PromptExecution(BaseModel):
    """
    Record of a single prompt template execution.

    This schema captures all relevant information about an execution
    for monitoring, debugging, and analytics.
    """

    # === Identity ===
    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this execution",
    )

    template_key: str = Field(
        ...,
        description="Key of the template that was executed",
    )

    app_name: str = Field(
        default="unknown",
        description="Name of the application that triggered this execution",
    )

    user_id: str | None = Field(
        default=None,
        description="ID of the user who triggered this execution",
    )

    # === Input ===
    variables_provided: dict = Field(
        default_factory=dict,
        description="Variables provided for this execution",
    )

    rendered_system_prompt: str = Field(
        default="",
        description="Final rendered system prompt",
    )

    rendered_user_prompt: str = Field(
        default="",
        description="Final rendered user prompt",
    )

    # === Output ===
    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING,
        description="Current status of the execution",
    )

    response_text: str | None = Field(
        default=None,
        description="Raw response text from the LLM",
    )

    # === LLM Info ===
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider used (e.g., 'openai', 'anthropic')",
    )

    llm_model: str | None = Field(
        default=None,
        description="Specific model used (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )

    llm_tier: str | None = Field(
        default=None,
        description="LLM tier used (e.g., 'standard', 'premium')",
    )

    # === Metrics ===
    tokens_input: int = Field(
        default=0,
        ge=0,
        description="Number of input tokens",
    )

    tokens_output: int = Field(
        default=0,
        ge=0,
        description="Number of output tokens",
    )

    cost_dollars: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated cost in USD",
    )

    duration_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in seconds",
    )

    # === Error Info ===
    error_type: str | None = Field(
        default=None,
        description="Exception class name if failed",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if failed",
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retry attempts made",
    )

    # === Cache ===
    from_cache: bool = Field(
        default=False,
        description="Whether the response came from cache",
    )

    cache_key: str | None = Field(
        default=None,
        description="Cache key used (if caching enabled)",
    )

    # === Timestamps ===
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the execution started",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When the execution completed",
    )

    # === Computed Properties ===

    @computed_field
    @property
    def tokens_total(self) -> int:
        """Total tokens used (input + output)."""
        return self.tokens_input + self.tokens_output

    @computed_field
    @property
    def is_success(self) -> bool:
        """Whether the execution was successful."""
        return self.status in (ExecutionStatus.SUCCESS, ExecutionStatus.CACHED)

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Whether the execution has completed (success or failure)."""
        return self.status != ExecutionStatus.PENDING

    # === Methods ===

    def mark_success(
        self,
        response_text: str,
        tokens_input: int,
        tokens_output: int,
        cost_dollars: float,
        duration_seconds: float,
        from_cache: bool = False,
    ) -> "PromptExecution":
        """Create a new execution record marked as successful."""
        return self.model_copy(
            update={
                "status": ExecutionStatus.CACHED if from_cache else ExecutionStatus.SUCCESS,
                "response_text": response_text,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "cost_dollars": cost_dollars,
                "duration_seconds": duration_seconds,
                "from_cache": from_cache,
                "completed_at": datetime.now(timezone.utc),
            }
        )

    def mark_failed(
        self,
        error_type: str,
        error_message: str,
        duration_seconds: float,
        retry_count: int = 0,
    ) -> "PromptExecution":
        """Create a new execution record marked as failed."""
        return self.model_copy(
            update={
                "status": ExecutionStatus.FAILED,
                "error_type": error_type,
                "error_message": error_message,
                "duration_seconds": duration_seconds,
                "retry_count": retry_count,
                "completed_at": datetime.now(timezone.utc),
            }
        )

    def to_log_dict(self) -> dict:
        """Convert to a dictionary suitable for structured logging."""
        return {
            "execution_id": str(self.execution_id),
            "template_key": self.template_key,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "status": self.status.value,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "tokens_total": self.tokens_total,
            "cost_dollars": self.cost_dollars,
            "duration_seconds": self.duration_seconds,
            "from_cache": self.from_cache,
            "error_type": self.error_type,
            "retry_count": self.retry_count,
        }

    model_config = {"frozen": True}
