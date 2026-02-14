"""SessionBackend Protocol + implementations.

Provides pluggable session storage for chat history:
- InMemorySessionBackend: testing / simple use
- RedisSessionBackend: production (requires redis extra)
"""

from __future__ import annotations

import json
import logging
from typing import Protocol, runtime_checkable

from .models import ChatSession

logger = logging.getLogger(__name__)


@runtime_checkable
class SessionBackend(Protocol):
    """Protocol for session storage implementations."""

    async def load(self, session_id: str) -> ChatSession | None:
        """Load a session by ID. Returns None if not found."""
        ...

    async def save(self, session: ChatSession) -> None:
        """Persist a session."""
        ...

    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        ...


class InMemorySessionBackend:
    """In-memory session store for testing and development."""

    def __init__(self) -> None:
        self._store: dict[str, ChatSession] = {}

    async def load(self, session_id: str) -> ChatSession | None:
        return self._store.get(session_id)

    async def save(self, session: ChatSession) -> None:
        self._store[session.id] = session

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)


class RedisSessionBackend:
    """Redis-backed session store for production.

    Requires ``redis`` package: ``pip install chat-agent[redis]``

    Args:
        redis_client: An async Redis client instance.
        prefix: Key prefix for session keys.
        ttl_seconds: Time-to-live for sessions (default 24h).
    """

    def __init__(
        self,
        redis_client: object,
        prefix: str = "chat:session:",
        ttl_seconds: int = 86400,
    ) -> None:
        self._redis = redis_client
        self._prefix = prefix
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    async def load(self, session_id: str) -> ChatSession | None:
        raw = await self._redis.get(self._key(session_id))  # type: ignore[union-attr]
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return ChatSession(**data)
        except (json.JSONDecodeError, Exception):
            logger.warning(
                "Failed to deserialize session %s", session_id
            )
            return None

    async def save(self, session: ChatSession) -> None:
        key = self._key(session.id)
        payload = session.model_dump_json()
        await self._redis.set(key, payload, ex=self._ttl)  # type: ignore[union-attr]

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(self._key(session_id))  # type: ignore[union-attr]
