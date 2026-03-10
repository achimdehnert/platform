"""
llm_mcp_service/models/llm_call.py

LlmCall SQLAlchemy Model — ADR-115 (Post-Review, Blocker behoben)

Platform-Standards eingehalten:
- BIGSERIAL PK + public_id UUID
- tenant_id BIGINT (Platform-Standard)
- deleted_at TIMESTAMPTZ (Soft-Delete)
- created_at TIMESTAMPTZ NOT NULL DEFAULT now()
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from llm_mcp_service.db import Base


class LlmCall(Base):
    """Audit-Log aller LLM-Calls für Kosten- und Qualitäts-Controlling.

    Append-only — kein UPDATE nach dem Schreiben.
    Soft-Delete (deleted_at) per Platform-Standard vorhanden,
    wird für Policy-basierte Retention genutzt.
    """

    __tablename__ = "llm_calls"

    # --- PKs & Identifiers (Platform-Standard: BigAutoField + public_id) ---
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )

    # --- Multi-Tenancy (Platform-Standard: tenant_id BigInt, no FK) ---
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # --- Business-Kontext ---
    task_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    repo: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Aufruf-Quelle: discord_chat | discord_ask | mcp_tool | api_direct",
    )
    call_type: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default="chat",
        comment="LLM-Call-Typ: chat | embedding | rerank | moderation",
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Externe Korrelations-ID (z.B. OpenRouter Request-ID)",
    )

    # --- Model & Token-Verbrauch ---
    model: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Kosten (zum Schreib-Zeitpunkt kalkuliert — historisch korrekt) ---
    cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 8),
        nullable=False,
        default=0,
        comment="Kosten in USD, kalkuliert mit Preis zum Call-Zeitpunkt",
    )

    # --- Performance ---
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Gesamtdauer des LLM-Calls in Millisekunden",
    )
    latency_p95_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Für zukünftige Streaming-Latenz-Messung reserviert",
    )

    # --- Fehler-Tracking ---
    error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="rate_limit | timeout | upstream_error | context_length | etc.",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Rohe Fehlermeldung, max. 1000 Zeichen",
    )

    # --- Timestamps & Soft-Delete (Platform-Standard) ---
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMPTZ,
        nullable=True,
        default=None,
        comment="Soft-Delete: Platform-Standard. Wird für Retention-Policy genutzt.",
    )

    __table_args__ = (
        # Primäre Query-Patterns abdecken
        Index("llm_calls_created_at_desc_idx", created_at.desc()),
        Index("llm_calls_tenant_task_idx", "tenant_id", "task_id"),
        Index("llm_calls_tenant_repo_idx", "tenant_id", "repo"),
        Index("llm_calls_model_created_idx", "model", "created_at"),
        # Partial Index für aktive Records (Soft-Delete ausgeschlossen)
        Index(
            "llm_calls_active_idx",
            "tenant_id",
            "created_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<LlmCall id={self.id} model={self.model!r} "
            f"tokens={self.total_tokens} cost=${self.cost_usd:.6f}>"
        )
