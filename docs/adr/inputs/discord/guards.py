"""
orchestrator_mcp/discord/guards.py

Role-based Access Control für Discord Slash Commands.
Löst BLOCKER B1 aus ADR-114 Review.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, Sequence

import discord

logger = logging.getLogger(__name__)

# Mapping: command_name → erlaubte Discord-Rollen
# Leere Liste = alle User erlaubt
COMMAND_ROLES: dict[str, list[str]] = {
    "deploy":  ["platform-admin", "devops"],
    "approve": ["platform-admin", "devops"],
    "reject":  ["platform-admin", "devops"],
    "task":    ["platform-admin", "devops", "developer"],
    "chat":    ["platform-admin", "devops", "developer"],
    "ask":     ["platform-admin", "devops", "developer"],
    "health":  [],
    "status":  [],
    "memory":  [],
}

EMBED_COLOR_DENIED = 0xED4245   # Discord Rot
EMBED_COLOR_OK     = 0x57F287   # Discord Grün


def require_role(command_name: str) -> Callable:
    """
    Decorator: Prüft Discord-Rollen vor Command-Ausführung.

    Usage:
        @tree.command(name="deploy")
        @require_role("deploy")
        async def cmd_deploy(interaction: discord.Interaction, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            required: list[str] = COMMAND_ROLES.get(command_name, [])

            # Kein Role-Requirement → direkt ausführen
            if not required:
                return await func(interaction, *args, **kwargs)

            # DM-Channels haben keine Rollen → verweigern
            if not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message(
                    embed=_denied_embed(command_name, required, dm=True),
                    ephemeral=True,
                )
                return

            user_roles: set[str] = {r.name for r in interaction.user.roles}
            if user_roles.intersection(required):
                logger.info(
                    "command_allowed",
                    extra={
                        "command": command_name,
                        "user": str(interaction.user),
                        "user_id": interaction.user.id,
                        "matched_roles": list(user_roles.intersection(required)),
                    },
                )
                return await func(interaction, *args, **kwargs)

            logger.warning(
                "command_denied",
                extra={
                    "command": command_name,
                    "user": str(interaction.user),
                    "user_id": interaction.user.id,
                    "user_roles": list(user_roles),
                    "required_roles": required,
                },
            )
            await interaction.response.send_message(
                embed=_denied_embed(command_name, required),
                ephemeral=True,
            )

        return wrapper
    return decorator


def _denied_embed(
    command_name: str,
    required: Sequence[str],
    dm: bool = False,
) -> discord.Embed:
    reason = (
        "Slash Commands können nicht aus DMs verwendet werden."
        if dm
        else f"Erforderliche Rolle: `{'`, `'.join(required)}`"
    )
    return discord.Embed(
        title="⛔ Keine Berechtigung",
        description=f"`/{command_name}` — {reason}",
        color=EMBED_COLOR_DENIED,
    )
