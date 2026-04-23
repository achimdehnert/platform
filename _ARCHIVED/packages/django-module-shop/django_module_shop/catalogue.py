"""Module catalogue — reads MODULE_SHOP_CATALOGUE from Django settings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class ModuleDefinition:
    code: str
    name: str
    description: str = ""
    icon: str = "box"
    price_month: float = 0.0
    price_year: float = 0.0
    stripe_price_id_month: str | None = None
    stripe_price_id_year: str | None = None
    category: str = "core"
    dependencies: list[str] = field(default_factory=list)

    @property
    def is_free(self) -> bool:
        return self.price_month == 0.0

    @property
    def yearly_discount_pct(self) -> int:
        if self.price_month == 0 or self.price_year == 0:
            return 0
        monthly_total = self.price_month * 12
        return round((1 - self.price_year / monthly_total) * 100)


def get_catalogue() -> dict[str, ModuleDefinition]:
    """Build catalogue from MODULE_SHOP_CATALOGUE setting."""
    raw: dict[str, Any] = getattr(settings, "MODULE_SHOP_CATALOGUE", {})
    result: dict[str, ModuleDefinition] = {}
    for code, data in raw.items():
        if isinstance(data, ModuleDefinition):
            result[code] = data
        else:
            result[code] = ModuleDefinition(
                code=code,
                name=data.get("name", code),
                description=data.get("description", ""),
                icon=data.get("icon", "box"),
                price_month=float(data.get("price_month", 0.0)),
                price_year=float(data.get("price_year", 0.0)),
                stripe_price_id_month=data.get("stripe_price_id_month"),
                stripe_price_id_year=data.get("stripe_price_id_year"),
                category=data.get("category", "core"),
                dependencies=list(data.get("dependencies", [])),
            )
    return result
