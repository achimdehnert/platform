"""LLM-based conversation evaluation for quality management.

Evaluates chat conversations on multiple quality metrics using
a cheap LLM (gpt-4o-mini). Stores results in EvaluationScore.

Per ADR-037 §8.2: Replaces heavy DeepEval dependency with
lightweight litellm-based scoring using structured prompts.

Configuration via Django settings::

    CHAT_LOGGING = {
        "EVALUATION_MODEL": "gpt-4o-mini",
        "EVALUATION_ENABLED": True,
    }

Usage::

    from chat_logging.evaluation import evaluate_conversation

    # Evaluate single conversation
    scores = await evaluate_conversation(conversation)

    # Batch evaluate
    from chat_logging.evaluation import batch_evaluate
    results = await batch_evaluate(app_name="drifttales", since_hours=24)
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async
from django.utils import timezone

if TYPE_CHECKING:
    from .models import ChatConversation, EvaluationScore

logger = logging.getLogger(__name__)


METRIC_PROMPTS: dict[str, str] = {
    "answer_relevancy": """\
Bewerte ob die Antworten des Assistenten relevant fuer die Fragen \
des Users sind.

Score 0.0 = komplett irrelevant, am Thema vorbei
Score 0.5 = teilweise relevant, aber weicht ab
Score 1.0 = perfekt relevant, beantwortet genau die Frage

Beruecksichtige:
- Geht der Assistent auf die konkrete Frage ein?
- Werden alle Aspekte der Frage adressiert?
- Ist die Antwort fokussiert (kein unnoetiiger Ballast)?
""",
    "helpfulness": """\
Bewerte wie hilfreich die Antworten des Assistenten sind.

Score 0.0 = voellig nutzlos, keine konkreten Informationen
Score 0.5 = teilweise hilfreich, aber unvollstaendig
Score 1.0 = sehr hilfreich, konkret und umsetzbar

Beruecksichtige:
- Gibt der Assistent konkrete, umsetzbare Hinweise?
- Werden Alternativen oder naechste Schritte vorgeschlagen?
- Ist die Antwort fuer den User wirklich nuetzlich?
""",
    "tool_correctness": """\
Bewerte ob der Assistent seine verfuegbaren Tools korrekt eingesetzt hat.

Score 0.0 = Tools falsch oder gar nicht genutzt (obwohl moeglich)
Score 0.5 = Tools teilweise korrekt genutzt
Score 1.0 = Tools perfekt und angemessen eingesetzt
Score N/A = keine Tool-Nutzung relevant -> score=0.8 (neutral)

Beruecksichtige:
- Wurden passende Tools fuer die Anfrage gewaehlt?
- Wurden Tool-Ergebnisse korrekt interpretiert?
- Haette der Assistent Tools nutzen sollen, hat es aber nicht?
""",
    "conversation_completeness": """\
Bewerte ob die Konversation das Ziel des Users erfuellt hat.

Score 0.0 = Ziel komplett verfehlt, User ist nicht weiter
Score 0.5 = teilweise erfuellt, User braucht noch Hilfe
Score 1.0 = Ziel vollstaendig erreicht

Beruecksichtige:
- Hat der User bekommen was er wollte?
- Wurde die Konversation natuerlich beendet?
- Blieben offene Fragen unbeantwortet?
""",
    "tone_quality": """\
Bewerte die Qualitaet von Ton und Sprache des Assistenten.

Score 0.0 = unhoeflich, verwirrend, unangemessen
Score 0.5 = akzeptabel aber verbesserungswuerdig
Score 1.0 = freundlich, klar, professionell, angemessen

Beruecksichtige:
- Ist der Ton freundlich und professionell?
- Ist die Sprache klar und verstaendlich?
- Passt die Ansprache zum Kontext?
- Antwortet der Assistent in der Sprache des Users?
""",
}

EVALUATION_SYSTEM_PROMPT = """\
Du bist ein QM-Evaluator fuer KI-Chat-Systeme.
Bewerte die folgende Konversation auf die angegebene Metrik.

Antworte NUR mit einem JSON-Objekt:
{{"score": 0.0-1.0, "reason": "Kurze Begruendung auf Deutsch (1-2 Saetze)"}}
"""


def _get_eval_config() -> dict[str, Any]:
    """Load evaluation config from Django settings."""
    from django.conf import settings

    defaults = {
        "EVALUATION_MODEL": "gpt-4o-mini",
        "EVALUATION_ENABLED": True,
    }
    config = getattr(settings, "CHAT_LOGGING", {})
    return {**defaults, **config}


def _format_conversation(conversation: ChatConversation) -> str:
    """Format a conversation's messages for evaluation."""
    messages = conversation.messages.order_by("created_at")
    lines = []
    for msg in messages:
        role = msg.role.upper()
        content = (msg.content or "")[:500]
        if msg.tool_calls:
            content += f" [Tool calls: {len(msg.tool_calls)}]"
        lines.append(f"[{role}]: {content}")
    return "\n".join(lines)


async def evaluate_metric(
    conversation_text: str,
    metric_name: str,
    app_name: str,
    model: str = "gpt-4o-mini",
) -> dict[str, Any] | None:
    """Evaluate a conversation on a single metric.

    Args:
        conversation_text: Formatted conversation text.
        metric_name: One of METRIC_PROMPTS keys.
        app_name: The app context.
        model: LLM model to use.

    Returns:
        Dict with 'score' and 'reason', or None on error.
    """
    metric_instruction = METRIC_PROMPTS.get(metric_name)
    if not metric_instruction:
        logger.warning("Unknown metric: %s", metric_name)
        return None

    prompt = (
        f"## Metrik: {metric_name}\n\n"
        f"{metric_instruction}\n\n"
        f"## App: {app_name}\n\n"
        f"## Konversation\n{conversation_text}\n\n"
        f"Bewerte jetzt diese Konversation."
    )

    try:
        import litellm

        response = await litellm.acompletion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": EVALUATION_SYSTEM_PROMPT,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        score = float(result.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        reason = result.get("reason", "")

        return {"score": score, "reason": reason}

    except ImportError:
        logger.warning(
            "litellm not installed — evaluation disabled"
        )
        return None
    except json.JSONDecodeError as exc:
        logger.warning(
            "LLM returned invalid JSON for %s: %s",
            metric_name,
            exc,
        )
        return None
    except Exception:
        logger.exception(
            "Evaluation failed for metric %s", metric_name
        )
        return None


async def evaluate_conversation(
    conversation: ChatConversation,
    metrics: list[str] | None = None,
    force: bool = False,
) -> list[EvaluationScore]:
    """Evaluate a conversation on all specified metrics.

    Args:
        conversation: The conversation to evaluate.
        metrics: List of metric names (default: all).
        force: Re-evaluate even if scores exist.

    Returns:
        List of created EvaluationScore instances.
    """
    from .models import EvaluationScore

    config = await sync_to_async(_get_eval_config)()
    if not config.get("EVALUATION_ENABLED", True):
        return []

    model = config.get("EVALUATION_MODEL", "gpt-4o-mini")
    metrics = metrics or list(METRIC_PROMPTS.keys())

    if not force:
        existing = await sync_to_async(
            lambda: set(
                conversation.evaluation_scores
                .filter(evaluator="custom")
                .values_list("metric_name", flat=True)
            )
        )()
        metrics = [m for m in metrics if m not in existing]

    if not metrics:
        logger.debug(
            "All metrics already scored for %s",
            conversation.session_id,
        )
        return []

    conversation_text = await sync_to_async(
        _format_conversation
    )(conversation)

    if not conversation_text.strip():
        return []

    scores: list[EvaluationScore] = []
    for metric_name in metrics:
        result = await evaluate_metric(
            conversation_text=conversation_text,
            metric_name=metric_name,
            app_name=conversation.app_name,
            model=model,
        )
        if result is None:
            continue

        score_obj = EvaluationScore(
            conversation=conversation,
            evaluator=EvaluationScore.Evaluator.CUSTOM,
            metric_name=metric_name,
            score=result["score"],
            reason=result["reason"],
            metadata={
                "model": model,
                "message_count": conversation.message_count,
            },
        )
        scores.append(score_obj)

    if scores:
        await sync_to_async(
            EvaluationScore.objects.bulk_create
        )(scores, ignore_conflicts=True)
        logger.info(
            "Evaluated %s: %d metrics scored",
            conversation.session_id,
            len(scores),
        )

    return scores


async def batch_evaluate(
    app_name: str | None = None,
    since_hours: int = 24,
    metrics: list[str] | None = None,
    force: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    """Batch evaluate recent conversations.

    Args:
        app_name: Filter by app (None = all apps).
        since_hours: Evaluate conversations from last N hours.
        metrics: Specific metrics (default: all).
        force: Re-evaluate existing scores.
        limit: Max conversations to evaluate.

    Returns:
        Summary dict with counts and average scores.
    """
    from .models import ChatConversation

    cutoff = timezone.now() - timedelta(hours=since_hours)
    qs = ChatConversation.objects.filter(
        started_at__gte=cutoff,
        message_count__gte=3,
    )
    if app_name:
        qs = qs.filter(app_name=app_name)

    conversations = await sync_to_async(
        lambda: list(qs.order_by("-started_at")[:limit])
    )()

    total_scored = 0
    total_metrics = 0
    all_scores: dict[str, list[float]] = {}

    for conv in conversations:
        scores = await evaluate_conversation(
            conv, metrics=metrics, force=force
        )
        if scores:
            total_scored += 1
            total_metrics += len(scores)
            for s in scores:
                all_scores.setdefault(
                    s.metric_name, []
                ).append(s.score)

    averages = {
        k: round(sum(v) / len(v), 3)
        for k, v in all_scores.items()
    }

    summary = {
        "conversations_found": len(conversations),
        "conversations_scored": total_scored,
        "total_metrics": total_metrics,
        "averages": averages,
    }

    logger.info("Batch evaluation complete: %s", summary)
    return summary
