"""
discord/config.py

Discord-Command Model-Konfiguration — ADR-116 (K-02 Fix)

Discord-Commands sind KEINE Agenten im Agent Coding Team.
Sie nutzen eine eigene, einfache ENV-basierte Konfiguration —
kein ModelSelector, kein RuleBasedBudgetRouter.

Begründung (K-02):
    Der Agent Coding Team Router (ADR-068/ADR-116) kennt Agent-Rollen:
    Developer, Tester, Guardian, Tech Lead, Planner, Re-Engineer.
    Discord-Commands sind Eingabe-Kanäle, keine Coding-Agenten.
    Ihre Modell-Anforderungen (kurze Antwortzeiten, geringer Kontext)
    unterscheiden sich fundamental von Agent-Tasks (langer Kontext, Code).

Konfiguration via ENV — kein DB-Eintrag, kein Code-Deployment bei Änderung.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DiscordModelConfig:
    model: str
    max_tokens: int
    temperature: float


# --- Discord-Command-Modelle aus ENV ---
_DISCORD_MODELS: dict[str, DiscordModelConfig] = {
    # Status-Commands: Ultra-günstig, kurze Antworten
    "status": DiscordModelConfig(
        model=os.environ.get("DISCORD_STATUS_MODEL", "openai/gpt-4o-mini"),
        max_tokens=256,
        temperature=0.1,
    ),
    # Ask-Commands: Günstig, informative Antworten
    "ask": DiscordModelConfig(
        model=os.environ.get("DISCORD_ASK_MODEL", "meta-llama/llama-3.1-8b-instruct"),
        max_tokens=1024,
        temperature=0.3,
    ),
    # Chat-Commands: Standard-Qualität, konversationell
    "chat": DiscordModelConfig(
        model=os.environ.get("DISCORD_CHAT_MODEL", "openai/gpt-4o"),
        max_tokens=2048,
        temperature=0.7,
    ),
    # Code-Commands: Hohe Qualität für Code-Erklärungen
    "code": DiscordModelConfig(
        model=os.environ.get("DISCORD_CODE_MODEL", "anthropic/claude-3.5-sonnet"),
        max_tokens=4096,
        temperature=0.0,
    ),
}

_DEFAULT_DISCORD_CONFIG = DiscordModelConfig(
    model=os.environ.get("DISCORD_DEFAULT_MODEL", "openai/gpt-4o-mini"),
    max_tokens=512,
    temperature=0.3,
)


def get_discord_model(command_type: str) -> DiscordModelConfig:
    """Gibt die Model-Config für einen Discord-Command-Typ zurück.

    Args:
        command_type: 'status' | 'ask' | 'chat' | 'code'

    Returns:
        DiscordModelConfig mit model, max_tokens, temperature.
        Falls unbekannt: Default-Config (gpt-4o-mini).
    """
    config = _DISCORD_MODELS.get(command_type.lower())
    if config is None:
        logger.warning(
            "Unbekannter Discord-Command-Typ '%s', verwende Default: %s",
            command_type,
            _DEFAULT_DISCORD_CONFIG.model,
        )
        return _DEFAULT_DISCORD_CONFIG
    return config


def get_all_discord_models() -> dict[str, DiscordModelConfig]:
    """Gibt alle konfigurierten Discord-Modelle zurück (für Logging/Debug)."""
    return dict(_DISCORD_MODELS)
