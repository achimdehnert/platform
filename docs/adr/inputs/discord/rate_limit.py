"""
orchestrator_mcp/discord/rate_limit.py

Token-Bucket Rate Limiter für Discord Slash Commands.
Löst BLOCKER B3 aus ADR-114 Review.

In-Memory (pro Bot-Instanz). Für Multi-Instance: Redis-Backend verwenden.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable

import discord

logger = logging.getLogger(__name__)

# Konfiguration pro Command-Gruppe
@dataclass
class BucketConfig:
    capacity: float      # max Tokens (burst)
    refill_rate: float   # Tokens/Sekunde


BUCKET_CONFIGS: dict[str, BucketConfig] = {
    "chat":    BucketConfig(capacity=5.0,  refill_rate=0.5),   # 1 alle 2s, burst 5
    "ask":     BucketConfig(capacity=3.0,  refill_rate=0.2),   # 1 alle 5s, burst 3
    "deploy":  BucketConfig(capacity=2.0,  refill_rate=0.1),   # 1 alle 10s, burst 2
    "task":    BucketConfig(capacity=5.0,  refill_rate=0.5),
    "default": BucketConfig(capacity=10.0, refill_rate=2.0),   # Liberal für Info-Commands
}


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


# user_id:command → Bucket
_buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(tokens=0.0))


def _get_config(command_name: str) -> BucketConfig:
    return BUCKET_CONFIGS.get(command_name, BUCKET_CONFIGS["default"])


def check_rate_limit(user_id: str | int, command_name: str) -> tuple[bool, float]:
    """
    Prüft Rate-Limit für user_id + command.

    Returns:
        (allowed, retry_after_seconds)
        allowed=True  → Request erlaubt, Token abgezogen
        allowed=False → Rate-Limit überschritten, retry_after > 0
    """
    key = f"{user_id}:{command_name}"
    cfg = _get_config(command_name)
    now = time.monotonic()

    bucket = _buckets[key]
    if bucket.tokens == 0.0 and bucket.last_refill == 0.0:
        # Neue Bucket initialisieren
        bucket.tokens = cfg.capacity
        bucket.last_refill = now

    elapsed = now - bucket.last_refill
    bucket.tokens = min(cfg.capacity, bucket.tokens + elapsed * cfg.refill_rate)
    bucket.last_refill = now

    if bucket.tokens >= 1.0:
        bucket.tokens -= 1.0
        return True, 0.0

    # Berechne Wartezeit bis 1 Token verfügbar
    retry_after = (1.0 - bucket.tokens) / cfg.refill_rate
    return False, retry_after


def rate_limit(command_name: str) -> Callable:
    """
    Decorator: Rate-Limit vor Command-Ausführung prüfen.

    Usage:
        @tree.command(name="chat")
        @require_role("chat")
        @rate_limit("chat")
        async def cmd_chat(interaction: discord.Interaction, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            user_id = interaction.user.id
            allowed, retry_after = check_rate_limit(user_id, command_name)

            if allowed:
                return await func(interaction, *args, **kwargs)

            logger.info(
                "rate_limit_hit",
                extra={
                    "command": command_name,
                    "user_id": user_id,
                    "retry_after": retry_after,
                },
            )
            embed = discord.Embed(
                title="⏱️ Rate Limit",
                description=(
                    f"Zu viele `/{command_name}` Anfragen.\n"
                    f"Bitte warte **{retry_after:.1f}s** und versuche es erneut."
                ),
                color=0xFEE75C,  # Discord Gelb
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        return wrapper
    return decorator
