"""Base channel interface for notification channels (ADR-088)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field


class ChannelConfig(BaseModel):
    """Configuration for a notification channel."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(
        default=3, description="Max delivery retries"
    )
    retry_backoff: bool = Field(
        default=True, description="Exponential backoff"
    )
    retry_backoff_max: int = Field(
        default=300, description="Max backoff seconds"
    )
    timeout: int = Field(
        default=30, description="Delivery timeout seconds"
    )


class BaseChannel(ABC):
    """Abstract base for notification channels."""

    name: str
    config: ChannelConfig

    def __init__(
        self, config: ChannelConfig | None = None
    ) -> None:
        self.config = config or ChannelConfig()

    @abstractmethod
    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        """Deliver notification. Returns True on success."""
        ...

    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format."""
        ...

    def health_check(self) -> dict[str, bool | str]:
        """Check channel connectivity."""
        return {"healthy": True, "channel": self.name}
