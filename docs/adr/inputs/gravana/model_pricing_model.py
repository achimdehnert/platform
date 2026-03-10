"""
llm_mcp_service/models/model_pricing.py

ModelPricing SQLAlchemy Model — ADR-115

Historisierte Preis-Tabelle: Preise werden mit Gültigkeitszeitraum gespeichert.
Kosten in llm_calls werden zum Call-Zeitpunkt mit dem damals gültigen Preis
kalkuliert — retrospektive Preisänderungen verfälschen historische Daten nicht.

Verwaltung via Django Admin (dev-hub) oder direktem DB-Insert.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from llm_mcp_service.db import Base


class LlmModelPricing(Base):
    """Historisierte OpenRouter-Modellpreise.

    Lookup-Logik:
      SELECT * FROM llm_model_pricing
      WHERE model = :model
        AND valid_from <= :call_time
        AND (valid_until IS NULL OR valid_until > :call_time)
        AND deleted_at IS NULL
      ORDER BY valid_from DESC
      LIMIT 1;

    Der Partial-Unique-Index stellt sicher, dass pro Modell maximal
    ein Eintrag ohne valid_until (= aktuell gültig) existiert.
    """

    __tablename__ = "llm_model_pricing"

    # --- PKs & Identifiers ---
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        unique=True,
    )

    # --- Kein tenant_id: Preise sind global/systemweit, kein User-Data ---

    # --- Preis-Daten ---
    model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="OpenRouter Model-ID, z.B. 'openai/gpt-4o'",
    )
    provider: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Provider-Name zur Gruppierung, z.B. 'openai', 'anthropic'",
    )
    input_per_1m_usd: Mapped[float] = mapped_column(
        Numeric(12, 8),
        nullable=False,
        comment="Kosten pro 1 Million Input-Token in USD",
    )
    output_per_1m_usd: Mapped[float] = mapped_column(
        Numeric(12, 8),
        nullable=False,
        comment="Kosten pro 1 Million Output-Token in USD",
    )

    # --- Gültigkeitszeitraum ---
    valid_from: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        server_default=func.now(),
        comment="Preise gültig ab diesem Zeitpunkt",
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMPTZ,
        nullable=True,
        default=None,
        comment="NULL = aktuell gültig. Beim Anlegen neuer Preise wird hier das "
                "Datum gesetzt, ab dem der neue Preis gilt.",
    )

    # --- Timestamps & Soft-Delete ---
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMPTZ,
        nullable=True,
        default=None,
    )

    __table_args__ = (
        # Nur ein "aktueller" Preis pro Modell (partial unique)
        UniqueConstraint(
            "model",
            name="uq_llm_model_pricing_current",
            postgresql_where="valid_until IS NULL AND deleted_at IS NULL",
        ),
        Index("llm_model_pricing_model_idx", "model"),
        Index("llm_model_pricing_valid_idx", "model", "valid_from"),
    )

    def __repr__(self) -> str:
        return (
            f"<LlmModelPricing model={self.model!r} "
            f"in=${self.input_per_1m_usd}/1M out=${self.output_per_1m_usd}/1M>"
        )


# --- Seed-Daten (Stand 2026-03, OpenRouter) ---
INITIAL_PRICING_SEED = [
    {
        "model": "openai/gpt-4o",
        "provider": "openai",
        "input_per_1m_usd": 2.50,
        "output_per_1m_usd": 10.00,
    },
    {
        "model": "openai/gpt-4o-mini",
        "provider": "openai",
        "input_per_1m_usd": 0.15,
        "output_per_1m_usd": 0.60,
    },
    {
        "model": "anthropic/claude-3.5-sonnet",
        "provider": "anthropic",
        "input_per_1m_usd": 3.00,
        "output_per_1m_usd": 15.00,
    },
    {
        "model": "anthropic/claude-opus-4",
        "provider": "anthropic",
        "input_per_1m_usd": 15.00,
        "output_per_1m_usd": 75.00,
    },
    {
        "model": "meta-llama/llama-3.1-70b-instruct",
        "provider": "meta",
        "input_per_1m_usd": 0.52,
        "output_per_1m_usd": 0.75,
    },
    {
        "model": "google/gemini-2.0-flash-001",
        "provider": "google",
        "input_per_1m_usd": 0.10,
        "output_per_1m_usd": 0.40,
    },
]
