"""
orchestrator_mcp/agent_team/budget_tracker.py

PostgreSQL-backed Budget-Tracker für ADR-116

BLOCKER B-02 behoben:
- Kein In-Memory-Counter — aggregiert llm_calls Tabelle (ADR-115)
- Multi-Container-safe: alle Container lesen dieselbe DB
- Redis-Cache (60s TTL) vermeidet DB-Hit bei jedem Routing-Call
- Tages-Reset ist automatisch (UTC-Datumswechsel in der SQL-Query)

Abhängigkeiten:
- llm_calls Tabelle (ADR-115) — kein neues Schema
- Redis (bereits im Stack)
- ENV: MODEL_SELECTOR_DAILY_BUDGET_USD, MODEL_SELECTOR_BUDGET_WARNING_PCT
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_mcp.models.model_route_config import BudgetMode

logger = logging.getLogger(__name__)

# Konfiguration aus ENV
DAILY_BUDGET_USD = Decimal(os.environ.get("MODEL_SELECTOR_DAILY_BUDGET_USD", "10.0"))
BUDGET_WARNING_PCT = float(os.environ.get("MODEL_SELECTOR_BUDGET_WARNING_PCT", "0.80"))
BUDGET_EMERGENCY_PCT = float(os.environ.get("MODEL_SELECTOR_BUDGET_EMERGENCY_PCT", "1.00"))
BUDGET_CACHE_TTL = int(os.environ.get("MODEL_SELECTOR_BUDGET_CACHE_TTL", "60"))

_CACHE_KEY = "model_selector:budget:today"


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    spent_usd: Decimal
    limit_usd: Decimal
    pct: float
    mode: BudgetMode
    checked_at: datetime

    @property
    def remaining_usd(self) -> Decimal:
        return max(Decimal("0"), self.limit_usd - self.spent_usd)

    @property
    def is_cost_sensitive(self) -> bool:
        return self.mode in (BudgetMode.COST_SENSITIVE, BudgetMode.EMERGENCY)

    def __str__(self) -> str:
        return (
            f"BudgetStatus(spent=${self.spent_usd:.4f}/{self.limit_usd:.2f} "
            f"[{self.pct*100:.1f}%] mode={self.mode.value})"
        )


class BudgetTracker:
    """Tages-Budget-Tracker über llm_calls-Tabelle.

    Design:
    - Primäre Datenquelle: PostgreSQL (llm_calls SUM-Aggregation)
    - Cache: Redis (60s TTL) — für Performance
    - Fallback bei Redis-Ausfall: direkte DB-Query
    - Tages-Reset: automatisch über UTC-Datumstrunkierung in SQL

    Thread-safe: asyncio.Lock schützt Cache-Refresh.
    Multi-Container: alle Container lesen dieselbe DB.
    """

    def __init__(self, redis_client=None) -> None:
        """
        Args:
            redis_client: Optional. Wenn None, wird direkt gegen DB abgefragt
                          (kein Caching). Im Produktionsbetrieb immer Redis übergeben.
        """
        self._redis = redis_client
        self._lock = asyncio.Lock()

    async def get_status(self, session: AsyncSession) -> BudgetStatus:
        """Gibt aktuellen Budget-Status zurück.

        Reihenfolge: Redis-Cache → DB-Query → Fallback
        """
        # 1. Versuche Redis-Cache
        if self._redis is not None:
            try:
                cached = await self._redis.get(_CACHE_KEY)
                if cached:
                    data = json.loads(cached)
                    return _status_from_dict(data)
            except Exception as exc:
                logger.warning("Redis budget cache read failed: %s", exc)

        # 2. DB-Query (async, Lock verhindert concurrent refreshes)
        async with self._lock:
            # Double-check nach Lock-Erwerb
            if self._redis is not None:
                try:
                    cached = await self._redis.get(_CACHE_KEY)
                    if cached:
                        return _status_from_dict(json.loads(cached))
                except Exception:
                    pass

            status = await self._query_db(session)

            # 3. Zurück in Cache schreiben
            if self._redis is not None:
                try:
                    await self._redis.setex(
                        _CACHE_KEY,
                        BUDGET_CACHE_TTL,
                        json.dumps(_status_to_dict(status)),
                    )
                except Exception as exc:
                    logger.warning("Redis budget cache write failed: %s", exc)

        return status

    async def _query_db(self, session: AsyncSession) -> BudgetStatus:
        """Aggregiert llm_calls für den aktuellen UTC-Tag."""
        stmt = text("""
            SELECT COALESCE(SUM(cost_usd), 0) AS spent_today
            FROM llm_calls
            WHERE
                created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
                AND deleted_at IS NULL
        """)

        result = await session.execute(stmt)
        row = result.fetchone()
        spent = Decimal(str(row.spent_today)) if row else Decimal("0")

        pct = float(spent / DAILY_BUDGET_USD) if DAILY_BUDGET_USD > 0 else 0.0

        if pct >= BUDGET_EMERGENCY_PCT:
            mode = BudgetMode.EMERGENCY
        elif pct >= BUDGET_WARNING_PCT:
            mode = BudgetMode.COST_SENSITIVE
        else:
            mode = BudgetMode.NORMAL

        status = BudgetStatus(
            spent_usd=spent,
            limit_usd=DAILY_BUDGET_USD,
            pct=pct,
            mode=mode,
            checked_at=datetime.now(tz=timezone.utc),
        )

        logger.debug("Budget status: %s", status)
        return status

    async def invalidate_cache(self) -> None:
        """Cache nach manuellem Budget-Update invalidieren."""
        if self._redis is not None:
            with asyncio.suppress(Exception):
                await self._redis.delete(_CACHE_KEY)


def _status_to_dict(status: BudgetStatus) -> dict:
    return {
        "spent_usd": str(status.spent_usd),
        "limit_usd": str(status.limit_usd),
        "pct": status.pct,
        "mode": status.mode.value,
        "checked_at": status.checked_at.isoformat(),
    }


def _status_from_dict(data: dict) -> BudgetStatus:
    return BudgetStatus(
        spent_usd=Decimal(data["spent_usd"]),
        limit_usd=Decimal(data["limit_usd"]),
        pct=data["pct"],
        mode=BudgetMode(data["mode"]),
        checked_at=datetime.fromisoformat(data["checked_at"]),
    )
