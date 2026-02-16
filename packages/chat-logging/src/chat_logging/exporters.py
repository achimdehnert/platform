"""Export utilities for chat conversations.

Supports JSONL and CSV export for analysis, fine-tuning,
and evaluation pipelines.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def export_conversations_jsonl(
    queryset: QuerySet,
    include_messages: bool = True,
) -> str:
    """Export conversations as JSONL string.

    Each line is a JSON object with conversation metadata
    and optionally all messages.

    Args:
        queryset: ChatConversation queryset to export.
        include_messages: Include full message history.

    Returns:
        JSONL-formatted string.
    """
    lines: list[str] = []

    for conv in queryset.prefetch_related("messages"):
        record: dict[str, Any] = {
            "session_id": conv.session_id,
            "app_name": conv.app_name,
            "goal_type": conv.goal_type,
            "goal_summary": conv.goal_summary,
            "outcome_status": conv.outcome_status,
            "outcome_summary": conv.outcome_summary,
            "outcome_artifacts": conv.outcome_artifacts,
            "message_count": conv.message_count,
            "total_tool_calls": conv.total_tool_calls,
            "total_tokens": conv.total_tokens,
            "models_used": conv.models_used,
            "started_at": (
                conv.started_at.isoformat()
                if conv.started_at
                else None
            ),
            "ended_at": (
                conv.ended_at.isoformat()
                if conv.ended_at
                else None
            ),
            "review_status": conv.review_status,
            "improvement_tags": conv.improvement_tags,
        }

        if include_messages:
            record["messages"] = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "model": msg.model,
                    "tool_calls": msg.tool_calls,
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name,
                    "tokens_used": msg.tokens_used,
                    "latency_ms": msg.latency_ms,
                    "created_at": (
                        msg.created_at.isoformat()
                        if msg.created_at
                        else None
                    ),
                }
                for msg in conv.messages.all()
            ]

        lines.append(json.dumps(record, ensure_ascii=False))

    return "\n".join(lines)


def export_conversations_csv(
    queryset: QuerySet,
) -> str:
    """Export conversation summaries as CSV.

    Args:
        queryset: ChatConversation queryset to export.

    Returns:
        CSV-formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "session_id",
        "app_name",
        "user",
        "goal_type",
        "goal_summary",
        "outcome_status",
        "outcome_summary",
        "message_count",
        "total_tool_calls",
        "total_tokens",
        "models_used",
        "review_status",
        "improvement_tags",
        "started_at",
        "ended_at",
        "duration_seconds",
    ])

    for conv in queryset.select_related("user"):
        writer.writerow([
            conv.session_id,
            conv.app_name,
            (
                conv.user.email
                if conv.user
                else ""
            ),
            conv.goal_type,
            conv.goal_summary,
            conv.outcome_status,
            conv.outcome_summary,
            conv.message_count,
            conv.total_tool_calls,
            conv.total_tokens,
            json.dumps(conv.models_used),
            conv.review_status,
            json.dumps(conv.improvement_tags),
            (
                conv.started_at.isoformat()
                if conv.started_at
                else ""
            ),
            (
                conv.ended_at.isoformat()
                if conv.ended_at
                else ""
            ),
            conv.duration_seconds or "",
        ])

    return output.getvalue()
