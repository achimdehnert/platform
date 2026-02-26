"""Thread-safe channel registry (ADR-088).

Singleton pattern with lock for thread-safety (Gunicorn workers).
Reference: OpenClaw src/channels/registry.ts (MIT)
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from platform_notifications.channels.base import BaseChannel


class ChannelRegistry:
    """Thread-safe registry for notification channels."""

    _instance: ClassVar[ChannelRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._channels: dict[str, BaseChannel] = {}
        self._channel_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> ChannelRegistry:
        """Thread-safe singleton access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing only)."""
        with cls._lock:
            cls._instance = None

    def register(self, channel: BaseChannel) -> None:
        """Register a channel. Thread-safe."""
        with self._channel_lock:
            self._channels[channel.name] = channel

    def get(self, name: str) -> BaseChannel:
        """Get channel by name. Raises KeyError if not found."""
        with self._channel_lock:
            if name not in self._channels:
                raise KeyError(
                    f"Channel '{name}' not registered. "
                    f"Available: {list(self._channels.keys())}"
                )
            return self._channels[name]

    def list_channels(self) -> list[str]:
        """List registered channel names."""
        with self._channel_lock:
            return list(self._channels.keys())

    def health_check_all(
        self,
    ) -> dict[str, dict[str, bool | str]]:
        """Run health checks on all registered channels."""
        with self._channel_lock:
            channels = dict(self._channels)
        return {
            name: ch.health_check()
            for name, ch in channels.items()
        }
