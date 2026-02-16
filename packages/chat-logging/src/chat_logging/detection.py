"""Use-case candidate auto-detection from conversation messages.

Detects unmet user needs by analyzing assistant responses and
conversation patterns. Per ADR-037 §8.1.

Detection methods:
- explicit_decline: Agent says it cannot do something
- no_tool_match: User requests action, agent responds without tools
- session_abandoned: Short session with no outcome artifacts
- tool_error: Tool dispatch error in conversation
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import (
        ChatConversation,
        ChatMessage,
        UseCaseCandidate,
    )

logger = logging.getLogger(__name__)

# Patterns indicating the agent explicitly declined a request.
# German and English variants.
DECLINE_PATTERNS: list[re.Pattern] = [
    # German: "Ich kann leider nicht...", "kann ich nicht..."
    re.compile(
        r"kann (ich )?(leider |zurzeit |momentan )?nicht",
        re.IGNORECASE,
    ),
    # German: "kann keine/kein/keinen" (negation with indef. article)
    re.compile(
        r"kann (ich )?(leider )?keine[nr]?\b",
        re.IGNORECASE,
    ),
    # German: "Nein, ich kann..." (explicit refusal start)
    re.compile(
        r"^Nein,? ich kann ",
        re.IGNORECASE | re.MULTILINE,
    ),
    # German: "ist mir leider nicht möglich"
    re.compile(
        r"ist mir (leider )?nicht m.glich",
        re.IGNORECASE,
    ),
    # German: "habe ich keinen Zugriff", "habe keinen Zugriff"
    re.compile(
        r"habe (ich )?(leider )?keinen Zugriff",
        re.IGNORECASE,
    ),
    # German: "liegt außerhalb meiner"
    re.compile(
        r"(liegt|f.llt) (leider )?au.erhalb meiner",
        re.IGNORECASE,
    ),
    # German: "steht mir nicht zur Verfügung"
    re.compile(
        r"steh(t|en) mir (leider )?nicht zur Verf.gung",
        re.IGNORECASE,
    ),
    # English: "I can't", "I cannot", "I'm unable to"
    re.compile(
        r"I (unfortunately )?(can'?t|cannot|am unable to)",
        re.IGNORECASE,
    ),
    # English: "I don't have access"
    re.compile(
        r"I don'?t have (access|the ability)",
        re.IGNORECASE,
    ),
    # English: "outside my capabilities"
    re.compile(
        r"outside (of )?my (capabilities|scope)",
        re.IGNORECASE,
    ),
    # German: "nicht über die Tools"
    re.compile(
        r"nicht .ber die( entsprechenden)? Tools",
        re.IGNORECASE,
    ),
    # German: "verfügbaren Tools beschränken sich"
    re.compile(
        r"verf.gbaren Tools beschr.nken sich",
        re.IGNORECASE,
    ),
    # German: "nicht direkt auf externe Systeme zugreifen"
    re.compile(
        r"nicht direkt auf externe",
        re.IGNORECASE,
    ),
    # German: "Das liegt außerhalb", "Das kann ich nicht"
    re.compile(
        r"leider nicht (direkt |in der Lage )",
        re.IGNORECASE,
    ),
]


def detect_explicit_decline(
    assistant_content: str,
    user_content: str,
    conversation: ChatConversation,
    trigger_message: ChatMessage | None = None,
) -> UseCaseCandidate | None:
    """Check if the assistant explicitly declined a user request.

    Args:
        assistant_content: The assistant's response text.
        user_content: The preceding user message text.
        conversation: The parent conversation.
        trigger_message: The assistant ChatMessage (for FK).

    Returns:
        A UseCaseCandidate instance (unsaved) or None.
    """
    from .models import UseCaseCandidate

    if not assistant_content or not user_content:
        return None

    for pattern in DECLINE_PATTERNS:
        if pattern.search(assistant_content):
            logger.info(
                "Detected explicit_decline in %s: '%s'",
                conversation.session_id,
                user_content[:80],
            )
            return UseCaseCandidate(
                conversation=conversation,
                trigger_message=trigger_message,
                detection_method=(
                    UseCaseCandidate.DetectionMethod
                    .EXPLICIT_DECLINE
                ),
                user_intent=user_content[:500],
                app_name=conversation.app_name,
                status=UseCaseCandidate.Status.NEW,
                priority=UseCaseCandidate.Priority.MEDIUM,
            )

    return None


def detect_tool_error(
    messages: list[dict],
    conversation: ChatConversation,
) -> UseCaseCandidate | None:
    """Check if a tool call resulted in an error.

    Looks for tool-role messages containing error indicators.

    Args:
        messages: Raw message dicts from the session.
        conversation: The parent conversation.

    Returns:
        A UseCaseCandidate instance (unsaved) or None.
    """
    from .models import UseCaseCandidate

    error_patterns = [
        "error",
        "exception",
        "failed",
        "traceback",
    ]

    last_user_msg = ""
    for msg in messages:
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "") or ""
        if msg.get("role") == "tool":
            content = (msg.get("content", "") or "").lower()
            if any(p in content for p in error_patterns):
                logger.info(
                    "Detected tool_error in %s",
                    conversation.session_id,
                )
                return UseCaseCandidate(
                    conversation=conversation,
                    detection_method=(
                        UseCaseCandidate.DetectionMethod
                        .TOOL_ERROR
                    ),
                    user_intent=(
                        last_user_msg[:500]
                        or "Tool execution error"
                    ),
                    app_name=conversation.app_name,
                    status=UseCaseCandidate.Status.NEW,
                    priority=UseCaseCandidate.Priority.HIGH,
                )

    return None


def detect_session_abandoned(
    conversation: ChatConversation,
) -> UseCaseCandidate | None:
    """Check if a session was abandoned early.

    A session is considered abandoned if it has fewer than 4
    messages (system + user + assistant = 3 minimum for one
    exchange) and no outcome artifacts.

    Args:
        conversation: The conversation being finalized.

    Returns:
        A UseCaseCandidate instance (unsaved) or None.
    """
    from .models import UseCaseCandidate

    if (
        conversation.message_count <= 3
        and not conversation.outcome_artifacts
    ):
        first_user_msg = (
            conversation.messages
            .filter(role="user")
            .values_list("content", flat=True)
            .first()
        )
        if first_user_msg:
            logger.info(
                "Detected session_abandoned in %s",
                conversation.session_id,
            )
            return UseCaseCandidate(
                conversation=conversation,
                detection_method=(
                    UseCaseCandidate.DetectionMethod
                    .SESSION_ABANDONED
                ),
                user_intent=first_user_msg[:500],
                app_name=conversation.app_name,
                status=UseCaseCandidate.Status.NEW,
                priority=UseCaseCandidate.Priority.LOW,
            )

    return None


def run_detection_on_messages(
    new_messages: list[dict],
    conversation: ChatConversation,
    saved_messages: list[ChatMessage] | None = None,
) -> list[UseCaseCandidate]:
    """Run all message-level detectors on new messages.

    Called after each save() with the newly persisted messages.

    Args:
        new_messages: Raw message dicts that were just saved.
        conversation: The parent conversation.
        saved_messages: The corresponding ChatMessage objects.

    Returns:
        List of unsaved UseCaseCandidate instances.
    """
    candidates: list[UseCaseCandidate] = []

    last_user_content = ""
    for i, msg in enumerate(new_messages):
        role = msg.get("role", "")
        content = msg.get("content", "") or ""

        if role == "user":
            last_user_content = content

        if role == "assistant" and last_user_content:
            trigger = (
                saved_messages[i]
                if saved_messages and i < len(saved_messages)
                else None
            )
            candidate = detect_explicit_decline(
                assistant_content=content,
                user_content=last_user_content,
                conversation=conversation,
                trigger_message=trigger,
            )
            if candidate:
                candidates.append(candidate)

    # Check for tool errors
    tool_err = detect_tool_error(
        new_messages, conversation
    )
    if tool_err:
        candidates.append(tool_err)

    return candidates


def run_detection_on_finalize(
    conversation: ChatConversation,
) -> list[UseCaseCandidate]:
    """Run session-level detectors when a conversation ends.

    Called during _finalize_conversation().

    Args:
        conversation: The conversation being finalized.

    Returns:
        List of unsaved UseCaseCandidate instances.
    """
    candidates: list[UseCaseCandidate] = []

    abandoned = detect_session_abandoned(conversation)
    if abandoned:
        candidates.append(abandoned)

    return candidates
