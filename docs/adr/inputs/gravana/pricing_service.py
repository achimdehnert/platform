"""
llm_mcp_service/services/pricing_service.py

Preisberechnung für LLM-Calls — ADR-115

- Preise aus DB (llm_model_pricing), nicht hardcodiert
- In-Memory-Cache mit 5 Minuten TTL (kein Redis erforderlich)
- Fallback auf konservative Schätzung wenn Preis unbekannt
- Thread-safe (asyncio.Lock)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from llm_mcp_service.models.model_pricing import LlmModelPricing

logger = logging.getLogger(__name__)

# Fallback-Preis wenn kein DB-Eintrag (konservativ hoch → kein Under-Reporting)
_FALLBACK_INPUT_PER_1M = Decimal("5.00")
_FALLBACK_OUTPUT_PER_1M = Decimal("20.00")

# Cache-TTL in Sekunden
_CACHE_TTL_SECONDS = 300  # 5 Minuten


@dataclass(frozen=True, slots=True)
class ModelPrice:
    model: str
    input_per_1m_usd: Decimal
    output_per_1m_usd: Decimal
    is_fallback: bool = False


@dataclass(frozen=True, slots=True)
class CostResult:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal
    model_price: ModelPrice

    @property
    def cost_cents(self) -> Decimal:
        return self.cost_usd * 100


class PricingService:
    """Service für LLM-Kosten-Kalkulation mit DB-Cache.

    Instanziierung: einmal als Singleton in der FastAPI-App (lifespan).
    Thread-safe für asyncio-Umgebungen.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[ModelPrice, float]] = {}
        self._lock = asyncio.Lock()

    async def calculate_cost(
        self,
        session: AsyncSession,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        at_time: Optional[datetime] = None,
    ) -> CostResult:
        """Kalkuliert die Kosten eines LLM-Calls.

        Args:
            session: Async DB-Session
            model: OpenRouter Model-ID
            prompt_tokens: Input-Token-Anzahl
            completion_tokens: Output-Token-Anzahl
            at_time: Zeitpunkt des Calls (für historische Kalkulation).
                     Default: jetzt (für aktuelle Calls)

        Returns:
            CostResult mit allen Token-Zahlen und Gesamtkosten
        """
        at_time = at_time or datetime.now(tz=timezone.utc)
        price = await self._get_price(session, model, at_time)

        cost = (
            Decimal(prompt_tokens) / Decimal("1_000_000") * price.input_per_1m_usd
            + Decimal(completion_tokens) / Decimal("1_000_000") * price.output_per_1m_usd
        )

        return CostResult(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost.quantize(Decimal("0.00000001")),  # 8 Dezimalstellen
            model_price=price,
        )

    async def _get_price(
        self, session: AsyncSession, model: str, at_time: datetime
    ) -> ModelPrice:
        """Gibt den Preis für ein Modell zurück. Cache-first, dann DB, dann Fallback."""
        import time

        now = time.monotonic()

        async with self._lock:
            cached = self._cache.get(model)
            if cached is not None:
                price, cached_at = cached
                if now - cached_at < _CACHE_TTL_SECONDS:
                    return price

        # DB-Lookup (außerhalb des Locks um Contention zu vermeiden)
        price = await self._fetch_from_db(session, model, at_time)
        if price is None:
            logger.warning(
                "Kein Preis für Modell '%s' in DB. Verwende Fallback-Preis.", model
            )
            price = ModelPrice(
                model=model,
                input_per_1m_usd=_FALLBACK_INPUT_PER_1M,
                output_per_1m_usd=_FALLBACK_OUTPUT_PER_1M,
                is_fallback=True,
            )

        async with self._lock:
            self._cache[model] = (price, now)

        return price

    async def _fetch_from_db(
        self, session: AsyncSession, model: str, at_time: datetime
    ) -> Optional[ModelPrice]:
        """Liest aktuell gültigen Preis aus der DB."""
        stmt = (
            select(LlmModelPricing)
            .where(
                LlmModelPricing.model == model,
                LlmModelPricing.valid_from <= at_time,
                (LlmModelPricing.valid_until.is_(None))
                | (LlmModelPricing.valid_until > at_time),
                LlmModelPricing.deleted_at.is_(None),
            )
            .order_by(LlmModelPricing.valid_from.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return ModelPrice(
            model=row.model,
            input_per_1m_usd=Decimal(str(row.input_per_1m_usd)),
            output_per_1m_usd=Decimal(str(row.output_per_1m_usd)),
        )

    def invalidate_cache(self, model: Optional[str] = None) -> None:
        """Cache leeren (nach Preisänderung im Admin)."""
        if model:
            self._cache.pop(model, None)
        else:
            self._cache.clear()


# Singleton-Instanz (in FastAPI lifespan initialisieren)
pricing_service = PricingService()
