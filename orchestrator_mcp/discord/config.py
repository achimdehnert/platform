"""
orchestrator_mcp/discord/config.py

Discord-Command Model-Konfiguration — ADR-116 (K-02 Fix)

Discord-Commands sind KEINE Agenten im Agent Coding Team.
Sie nutzen eine eigene, einfache ENV-basierte Konfiguration —
kein RuleBasedBudgetRouter, kein ModelRouteConfig.

Begründung (K-02):
    Der Agent Coding Team Router (ADR-116) kennt Agent-Rollen:
    Developer, Tester, Guardian, Tech Lead, Planner, Re-Engineer,
    Security Auditor.
    Discord-Commands sind Eingabe-Kanäle, keine Coding-Agenten.
    Ihre Modell-Anforderungen (kurze Antwortzeiten, geringer Kontext)
    unterscheiden sich fundamental von Agent-Tasks (langer Kontext, Code).

Konfiguration via ENV — kein DB-Eintrag, kein Code-Deployment bei Änderung.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscordModelConfig:
    """Modell-Konfiguration für einen Discord-Command-Typ."""

    command_type: str
    model: str
    max_tokens: int = 1024
    temperature: float = 0.7


def get_discord_model(command_type: str) -> DiscordModelConfig:
    """Gibt die Modell-Config für einen Discord-Command-Typ zurück.

    Args:
        command_type: "status" | "ask" | "chat" | "code" | ...

    Returns:
        DiscordModelConfig mit model und Parametern.
        Unbekannte command_types erhalten das Default-Modell.
    """
    _CONFIG = {
        "status": DiscordModelConfig(
            command_type="status",
            model=os.environ.get(
                "DISCORD_STATUS_MODEL", "openai/gpt-4o-mini"
            ),
            max_tokens=512,
            temperature=0.3,
        ),
        "ask": DiscordModelConfig(
            command_type="ask",
            model=os.environ.get(
                "DISCORD_ASK_MODEL",
                "meta-llama/llama-3.1-8b-instruct",
            ),
            max_tokens=1024,
            temperature=0.7,
        ),
        "chat": DiscordModelConfig(
            command_type="chat",
            model=os.environ.get(
                "DISCORD_CHAT_MODEL", "openai/gpt-4o"
            ),
            max_tokens=2048,
            temperature=0.8,
        ),
        "code": DiscordModelConfig(
            command_type="code",
            model=os.environ.get(
                "DISCORD_CODE_MODEL", "openai/gpt-4o"
            ),
            max_tokens=4096,
            temperature=0.2,
        ),
    }

    return _CONFIG.get(
        command_type,
        DiscordModelConfig(
            command_type=command_type,
            model=os.environ.get(
                "DISCORD_DEFAULT_MODEL", "openai/gpt-4o-mini"
            ),
        ),
    )
