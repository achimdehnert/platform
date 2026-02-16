"""LoggingSessionBackend — transparent persistence wrapper.

Wraps any SessionBackend and additionally persists every message
to the ChatConversation + ChatMessage Django models.

Per ADR-037 §5: Zero code changes in views — only the agent
factory needs updating.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async
from chat_agent import ChatSession, SessionBackend

if TYPE_CHECKING:
    from .models import ChatConversation

logger = logging.getLogger(__name__)


class LoggingSessionBackend:
    """SessionBackend wrapper that logs conversations to SQL.

    Usage::

        from chat_logging import LoggingSessionBackend
        from chat_agent import InMemorySessionBackend

        backend = LoggingSessionBackend(
            wrapped=InMemorySessionBackend(),
            app_name="drifttales",
            user=request.user,
        )
        agent = ChatAgent(..., session_backend=backend)
    """

    def __init__(
        self,
        wrapped: SessionBackend,
        app_name: str,
        user: Any = None,
        tenant_id: str | None = None,
    ) -> None:
        self._wrapped = wrapped
        self._app_name = app_name
        self._user = user
        self._tenant_id = tenant_id
        self._message_counts: dict[str, int] = {}
        self._save_times: dict[str, float] = {}

    async def load(
        self, session_id: str
    ) -> ChatSession | None:
        """Load session from wrapped backend."""
        return await self._wrapped.load(session_id)

    async def save(self, session: ChatSession) -> None:
        """Save to wrapped backend + persist new messages."""
        start = time.monotonic()
        await self._wrapped.save(session)
        elapsed_ms = int(
            (time.monotonic() - start) * 1000
        )

        try:
            await self._persist_messages(
                session, elapsed_ms
            )
        except Exception:
            logger.exception(
                "Failed to persist messages for session %s",
                session.id,
            )

    async def delete(self, session_id: str) -> None:
        """Finalize conversation and delete from wrapped."""
        try:
            await self._finalize_conversation(session_id)
        except Exception:
            logger.exception(
                "Failed to finalize conversation %s",
                session_id,
            )
        await self._wrapped.delete(session_id)
        self._message_counts.pop(session_id, None)
        self._save_times.pop(session_id, None)

    async def _persist_messages(
        self,
        session: ChatSession,
        latency_ms: int = 0,
    ) -> None:
        """Persist only new messages since last save."""
        from .models import ChatConversation, ChatMessage  # noqa: F811

        session_id = session.id
        messages = session.messages
        prev_count = self._message_counts.get(
            session_id, 0
        )
        new_messages = messages[prev_count:]

        if not new_messages:
            return

        conversation = await sync_to_async(
            self._get_or_create_conversation
        )(session_id)

        msg_objects = []
        for msg in new_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "") or ""
            tool_calls = msg.get("tool_calls", [])
            tool_call_id = msg.get("tool_call_id", "")
            name = msg.get("name", "")
            model = msg.get("model", "")

            msg_objects.append(
                ChatMessage(
                    conversation=conversation,
                    role=role,
                    content=content,
                    model=model,
                    tool_calls=tool_calls,
                    tool_call_id=tool_call_id or "",
                    name=name or "",
                    latency_ms=(
                        latency_ms
                        if role == "assistant"
                        else 0
                    ),
                )
            )

        if msg_objects:
            saved = await sync_to_async(
                ChatMessage.objects.bulk_create
            )(msg_objects)

            # Auto-detect use-case candidates
            try:
                await self._detect_use_cases(
                    new_messages, conversation, saved
                )
            except Exception:
                logger.exception(
                    "Use-case detection failed for %s",
                    session_id,
                )

        # Update conversation metrics
        total = len(messages)
        tool_call_count = sum(
            len(m.get("tool_calls", []))
            for m in messages
        )
        models_used = list(
            {
                m.get("model", "")
                for m in messages
                if m.get("model")
            }
        )

        await sync_to_async(self._update_metrics)(
            conversation,
            message_count=total,
            total_tool_calls=tool_call_count,
            total_latency_ms=latency_ms,
            models_used=models_used,
        )

        self._message_counts[session_id] = total

    def _get_or_create_conversation(
        self, session_id: str
    ) -> ChatConversation:
        """Get or create a ChatConversation for this session."""
        from .models import ChatConversation  # noqa: F811

        conversation, created = (
            ChatConversation.objects.get_or_create(
                session_id=session_id,
                defaults={
                    "app_name": self._app_name,
                    "user": self._user,
                    "tenant_id": self._tenant_id,
                },
            )
        )
        if created:
            logger.debug(
                "Created conversation %s for session %s",
                conversation.id,
                session_id,
            )
        return conversation

    def _update_metrics(
        self,
        conversation: ChatConversation,
        message_count: int,
        total_tool_calls: int,
        total_latency_ms: int,
        models_used: list[str],
    ) -> None:
        """Update conversation metrics."""
        conversation.message_count = message_count
        conversation.total_tool_calls = total_tool_calls
        conversation.total_latency_ms += total_latency_ms
        conversation.models_used = models_used
        conversation.save(
            update_fields=[
                "message_count",
                "total_tool_calls",
                "total_latency_ms",
                "models_used",
            ]
        )

    async def _finalize_conversation(
        self, session_id: str
    ) -> None:
        """Mark conversation as ended."""
        from django.utils import timezone

        from .models import ChatConversation

        try:
            conversation = await sync_to_async(
                ChatConversation.objects.get
            )(session_id=session_id)
        except ChatConversation.DoesNotExist:
            return

        conversation.ended_at = timezone.now()

        # Auto-detect outcome if not already set
        if (
            conversation.outcome_status
            == ChatConversation.OutcomeStatus.PARTIAL
        ):
            if conversation.message_count < 3:
                conversation.outcome_status = (
                    ChatConversation.OutcomeStatus.ABANDONED
                )

        await sync_to_async(conversation.save)(
            update_fields=["ended_at", "outcome_status"]
        )

        # Auto-detect use-case candidates on finalize
        try:
            await self._detect_use_cases_finalize(
                conversation
            )
        except Exception:
            logger.exception(
                "Use-case detection (finalize) failed for %s",
                session_id,
            )

        logger.debug(
            "Finalized conversation %s (%s)",
            session_id,
            conversation.outcome_status,
        )

    async def _detect_use_cases(
        self,
        new_messages: list[dict],
        conversation: ChatConversation,
        saved_messages: list,
    ) -> None:
        """Run message-level use-case detection."""
        from .detection import run_detection_on_messages
        from .models import UseCaseCandidate

        candidates = run_detection_on_messages(
            new_messages, conversation, saved_messages
        )
        if candidates:
            await sync_to_async(
                UseCaseCandidate.objects.bulk_create
            )(candidates)
            logger.info(
                "Created %d use-case candidate(s) for %s",
                len(candidates),
                conversation.session_id,
            )

    async def _detect_use_cases_finalize(
        self,
        conversation: ChatConversation,
    ) -> None:
        """Run session-level use-case detection."""
        from .detection import run_detection_on_finalize
        from .models import UseCaseCandidate

        candidates = await sync_to_async(
            run_detection_on_finalize
        )(conversation)
        if candidates:
            await sync_to_async(
                UseCaseCandidate.objects.bulk_create
            )(candidates)
            logger.info(
                "Created %d use-case candidate(s) on finalize for %s",
                len(candidates),
                conversation.session_id,
            )
