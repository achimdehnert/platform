"""Anthropic-Preistabelle — einzige Quelle für alle Kosten-Werkzeuge.

Ausgelagert aus `log_llm_call.py` (Kosten-Qualitäts-Auswertung, #2919-ff):
`log_llm_call.py` löst auf Modulebene eine DB-URL auf (`DB_URL = _resolve_db_url()`,
liest ggf. `~/.secrets/orchestrator_mcp_db_password`) — ein reiner Preistabellen-
Import aus dieser Datei triggert diesen Nebeneffekt ungewollt mit. Diese Datei hat
KEINE Nebeneffekte auf Modulebene (kein DB-Zugriff, kein Netzwerk, kein Secrets-Read)
und darf daher gefahrlos von jedem read-only Auswertungswerkzeug importiert werden.

`log_llm_call.py` importiert seinerseits von HIER (siehe dortigen Kommentar) — es
gibt nur noch eine Preisliste, nicht zwei, die auseinanderlaufen können.
"""

from __future__ import annotations

# Anthropic pricing per 1M tokens (USD). Source: Claude-API-Referenz (Skill
# `claude-api`, Modelltabelle Stand 2026-06-24) — Opus 4.6/4.7/4.8 kosten seit
# Opus 4.5 $5/$25, nicht mehr $15/$75 wie Opus 4/4.1.
# Cache pricing relative to input: write_5m=1.25x, write_1h=2x, read=0.1x.
PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-fable-5-1": {"input": 10.0, "output": 50.0},
    "claude-fable-5": {"input": 10.0, "output": 50.0},
    "claude-mythos-5-1": {"input": 10.0, "output": 50.0},
    "claude-opus-5": {"input": 5.0, "output": 25.0},
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-opus-4-7": {"input": 5.0, "output": 25.0},
    "claude-opus-4-6": {"input": 5.0, "output": 25.0},
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-5": {"input": 2.0, "output": 10.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5-20251022": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def normalize_model(model: str) -> str:
    """Kontextvarianten-Suffix abschneiden (`claude-fable-5[1m]` → `claude-fable-5`).

    Die Preistabelle kennt nur den nackten Modellnamen.
    """
    return model.split("[", 1)[0].strip()


def price_for(model: str) -> dict[str, float]:
    """Preis je 1 Mio Token für `model`, mit Fallback auf `DEFAULT_PRICING`."""
    return PRICING_USD_PER_MTOK.get(normalize_model(model), DEFAULT_PRICING)
