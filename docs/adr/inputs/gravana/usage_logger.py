"""
llm_mcp_service/services/usage_logger.py

Non-blocking Usage-Logger für LLM-Calls — ADR-115

KRITISCH K-02 behoben:
- Synchrones DB-Write blockierte LLM-Call-Response
- Jetzt: Fire-and-Forget via FastAPI BackgroundTasks
- Fehler im Logger propagieren NIEMALS zum API-Client

Verwendung:
    # In FastAPI-Route:
    from fastapi import BackgroundTasks
    from llm_mcp_service.services.usage_logger import UsageLogger, LlmCallRecord

    @router.post("/chat")
    async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
        t_start = time.monotonic()
        result = await llm_gateway.call(request)
        duration_ms = int((time.monotonic() - t_start) * 1000)

        record = LlmCallRecord(
            tenant_id=request.tenant_id,
            model=result.model,
            prompt_tokens=result.usage.prompt_tokens,
            completion_tokens=result.usage.completion_tokens,
            duration_ms=duration_ms,
            source="discord_chat",
            task_id=request.task_id,
            repo=request.repo,
        )
        background_tasks.add_task(UsageLogger.log, record)
        return result
"""
from __future__ import annotations

import logging
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from llm_mcp_service.db import get_async_session
from llm_mcp_service.models.llm_call import LlmCall
from llm_mcp_service.services.pricing_service import pricing_service

logger = logging.getLogger(__name__)


@dataclass
class LlmCallRecord:
    """Value-Object für einen zu loggenden LLM-Call."""

    # Required
    tenant_id: int
    model: str
    prompt_tokens: int
    completion_tokens: int

    # Optional context
    task_id: Optional[str] = None
    repo: Optional[str] = None
    source: Optional[str] = None
    call_type: str = "chat"
    request_id: Optional[str] = None
    duration_ms: Optional[int] = None

    # Error tracking
    error: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Zeitstempel (wird beim Erstellen gesetzt)
    called_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def truncate_error_message(self, max_length: int = 1000) -> None:
        """Error-Message auf max_length Zeichen begrenzen."""
        if self.error_message and len(self.error_message) > max_length:
            self.error_message = self.error_message[:max_length] + "…[truncated]"


class UsageLogger:
    """Fire-and-Forget Usage-Logger.

    Niemals direkt awaiten — immer als BackgroundTask registrieren.
    Fehler werden geloggt, nie propagiert.
    """

    @staticmethod
    async def log(record: LlmCallRecord) -> None:
        """Loggt einen LLM-Call in die DB.

        Diese Methode ist für FastAPI BackgroundTasks ausgelegt.
        Fehler werden silent geloggt — ein fehlgeschlagenes Logging
        darf niemals den API-Client beeinflussen.
        """
        record.truncate_error_message()

        try:
            async with get_async_session() as session:
                await _write_record(session, record)
        except Exception as exc:  # noqa: BLE001
            # Intentionally broad: Logging-Fehler dürfen nie propagieren
            logger.warning(
                "LLM-Call-Logging fehlgeschlagen (non-critical): %s | "
                "model=%s tokens=%d task=%s",
                exc,
                record.model,
                record.prompt_tokens + record.completion_tokens,
                record.task_id,
                exc_info=False,  # Kein Stacktrace im Prod-Log für non-critical
            )

    @staticmethod
    async def log_error(
        tenant_id: int,
        model: str,
        error_code: str,
        error_message: str,
        *,
        task_id: Optional[str] = None,
        repo: Optional[str] = None,
        source: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Convenience-Methode für Fehler-Logging ohne Token-Zahlen."""
        record = LlmCallRecord(
            tenant_id=tenant_id,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            task_id=task_id,
            repo=repo,
            source=source,
            duration_ms=duration_ms,
            error=True,
            error_code=error_code,
            error_message=error_message,
        )
        await UsageLogger.log(record)


async def _write_record(session: AsyncSession, record: LlmCallRecord) -> None:
    """Interne Schreib-Funktion. Trennung für leichteres Testing."""
    # Kosten zum Call-Zeitpunkt kalkulieren (historisch korrekt)
    cost_result = await pricing_service.calculate_cost(
        session=session,
        model=record.model,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        at_time=record.called_at,
    )

    if cost_result.model_price.is_fallback:
        logger.debug(
            "Fallback-Preis verwendet für Modell '%s' — "
            "Preistabelle prüfen.",
            record.model,
        )

    stmt = insert(LlmCall).values(
        tenant_id=record.tenant_id,
        task_id=record.task_id,
        repo=record.repo,
        source=record.source,
        call_type=record.call_type,
        request_id=record.request_id,
        model=record.model,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        total_tokens=cost_result.total_tokens,
        cost_usd=cost_result.cost_usd,
        duration_ms=record.duration_ms,
        error=record.error,
        error_code=record.error_code,
        error_message=record.error_message,
        created_at=record.called_at,
    )

    await session.execute(stmt)
    await session.commit()
