"""LLM-based use-case candidate detection.

Uses a cheap LLM (gpt-4o-mini) to classify whether the assistant
declined a user request and extract the user's intent.
Replaces brittle regex patterns with semantic understanding.

Configuration via Django settings::

    CHAT_LOGGING = {
        "DETECTION_MODEL": "gpt-4o-mini",
        "DETECTION_ENABLED": True,
    }
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    from .models import (
        ChatConversation,
        ChatMessage,
        UseCaseCandidate,
    )

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """\
Du bist ein QM-Analyst fuer KI-Chat-Systeme.

Analysiere den folgenden Chat-Austausch zwischen einem User und einem \
KI-Assistenten. Bestimme ob der Assistent die Anfrage des Users \
ablehnen musste oder nicht erfuellen konnte.

## User-Nachricht
{user_message}

## Assistenten-Antwort
{assistant_message}

## App-Kontext
App: {app_name}

## Aufgabe
Antworte NUR mit einem JSON-Objekt (kein Markdown, kein Text drumherum):

{{
  "is_decline": true/false,
  "detection_method": "explicit_decline" | "no_tool_match" | \
"capability_gap" | "none",
  "user_intent": "Kurze Beschreibung was der User wollte (1 Satz, deutsch)",
  "missing_capability": "Was fehlt dem System? (1 Satz, deutsch, \
oder leer wenn kein Decline)",
  "priority": "low" | "medium" | "high",
  "confidence": 0.0-1.0
}}

Regeln:
- is_decline=true wenn der Assistent klar sagt dass er etwas NICHT kann
- detection_method="explicit_decline" bei direkter Ablehnung
- detection_method="no_tool_match" wenn Tools fehlen
- detection_method="capability_gap" wenn eine Faehigkeit grundsaetzlich fehlt
- detection_method="none" wenn keine Ablehnung vorliegt
- priority="high" wenn mehrere User das brauchen koennten
- priority="medium" fuer nuetzliche Ergaenzungen
- priority="low" fuer Randanforderungen
"""


def _get_detection_config() -> dict[str, Any]:
    """Load detection config from Django settings."""
    from django.conf import settings

    defaults = {
        "DETECTION_MODEL": "gpt-4o-mini",
        "DETECTION_ENABLED": True,
    }
    config = getattr(settings, "CHAT_LOGGING", {})
    return {**defaults, **config}


async def classify_exchange(
    user_message: str,
    assistant_message: str,
    app_name: str,
) -> dict[str, Any] | None:
    """Classify a user/assistant exchange via LLM.

    Args:
        user_message: The user's message text.
        assistant_message: The assistant's response text.
        app_name: The app context (e.g. drifttales).

    Returns:
        Classification dict or None on error/disabled.
    """
    config = await sync_to_async(_get_detection_config)()

    if not config.get("DETECTION_ENABLED", True):
        return None

    model = config.get("DETECTION_MODEL", "gpt-4o-mini")

    prompt = CLASSIFICATION_PROMPT.format(
        user_message=user_message[:1000],
        assistant_message=assistant_message[:2000],
        app_name=app_name,
    )

    try:
        import litellm

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        logger.debug(
            "LLM classification for %s: %s",
            app_name,
            result,
        )
        return result

    except ImportError:
        logger.warning(
            "litellm not installed — LLM detection disabled"
        )
        return None
    except json.JSONDecodeError as exc:
        logger.warning(
            "LLM returned invalid JSON: %s", exc
        )
        return None
    except Exception:
        logger.exception("LLM classification failed")
        return None


async def detect_via_llm(
    new_messages: list[dict],
    conversation: ChatConversation,
    saved_messages: list[ChatMessage] | None = None,
) -> list[UseCaseCandidate]:
    """Run LLM-based detection on new messages.

    Finds user→assistant pairs and classifies each.
    Only creates UseCaseCandidates for confirmed declines.

    Args:
        new_messages: Raw message dicts that were just saved.
        conversation: The parent conversation.
        saved_messages: Corresponding ChatMessage objects.

    Returns:
        List of unsaved UseCaseCandidate instances.
    """
    from .models import UseCaseCandidate

    candidates: list[UseCaseCandidate] = []

    last_user_content = ""
    for i, msg in enumerate(new_messages):
        role = msg.get("role", "")
        content = msg.get("content", "") or ""

        if role == "user":
            last_user_content = content

        if role == "assistant" and last_user_content:
            result = await classify_exchange(
                user_message=last_user_content,
                assistant_message=content,
                app_name=conversation.app_name,
            )

            if not result:
                continue

            if not result.get("is_decline", False):
                continue

            confidence = result.get("confidence", 0.5)
            if confidence < 0.6:
                logger.debug(
                    "Low confidence decline (%.2f), skipping",
                    confidence,
                )
                continue

            detection_method = result.get(
                "detection_method", "explicit_decline"
            )
            method_map = {
                "explicit_decline": (
                    UseCaseCandidate.DetectionMethod
                    .EXPLICIT_DECLINE
                ),
                "no_tool_match": (
                    UseCaseCandidate.DetectionMethod
                    .NO_TOOL_MATCH
                ),
                "capability_gap": (
                    UseCaseCandidate.DetectionMethod
                    .EXPLICIT_DECLINE
                ),
            }
            db_method = method_map.get(
                detection_method,
                UseCaseCandidate.DetectionMethod
                .EXPLICIT_DECLINE,
            )

            priority_map = {
                "low": UseCaseCandidate.Priority.LOW,
                "medium": UseCaseCandidate.Priority.MEDIUM,
                "high": UseCaseCandidate.Priority.HIGH,
            }
            db_priority = priority_map.get(
                result.get("priority", "medium"),
                UseCaseCandidate.Priority.MEDIUM,
            )

            trigger = (
                saved_messages[i]
                if saved_messages and i < len(saved_messages)
                else None
            )

            user_intent = result.get(
                "user_intent", last_user_content[:500]
            )
            missing = result.get("missing_capability", "")
            notes = (
                f"Missing: {missing}\n"
                f"Confidence: {confidence:.2f}\n"
                f"Method: {detection_method}"
            )

            candidates.append(
                UseCaseCandidate(
                    conversation=conversation,
                    trigger_message=trigger,
                    detection_method=db_method,
                    user_intent=user_intent[:500],
                    app_name=conversation.app_name,
                    status=UseCaseCandidate.Status.NEW,
                    priority=db_priority,
                    notes=notes,
                )
            )

            logger.info(
                "LLM detected decline in %s: %s (%.0f%%)",
                conversation.session_id,
                user_intent[:60],
                confidence * 100,
            )

    return candidates
