"""
orchestrator_mcp/discord/utils.py

Discord Message Utilities: Chunker, Embeds, Formatierung.
Löst BLOCKER B4 aus ADR-114 Review.
"""
from __future__ import annotations

import textwrap
from enum import IntEnum
from typing import Sequence

import discord

DISCORD_MSG_LIMIT = 1990    # Discord Limit = 2000, -10 als Puffer
DISCORD_EMBED_LIMIT = 4000  # Embed description Limit


class EmbedColor(IntEnum):
    SUCCESS = 0x57F287   # Grün
    INFO    = 0x5865F2   # Discord Blau
    WARNING = 0xFEE75C   # Gelb
    ERROR   = 0xED4245   # Rot
    CASCADE = 0x9B59B6   # Lila (für Cascade-Antworten)
    LLM     = 0x3498DB   # Hellblau (für LLM-Gateway)


async def send_chunked(
    interaction: discord.Interaction,
    text: str,
    title: str = "",
    color: int = EmbedColor.INFO,
    footer: str = "",
) -> None:
    """
    Sendet Text als Discord Embed(s). Splittet bei Überschreitung des Limits.

    Für Antworten nach interaction.defer() → nutzt followup.send().
    """
    chunks = _split_text(text, DISCORD_EMBED_LIMIT)
    total = len(chunks)

    for idx, chunk in enumerate(chunks, start=1):
        part_title = f"{title} ({idx}/{total})" if total > 1 and title else title
        if total > 1 and not title:
            part_title = f"Teil {idx}/{total}"

        embed = discord.Embed(
            title=part_title or None,
            description=chunk,
            color=color,
        )
        if footer:
            embed.set_footer(text=footer)

        await interaction.followup.send(embed=embed)


async def send_error(
    interaction: discord.Interaction,
    title: str,
    description: str,
    ephemeral: bool = True,
) -> None:
    """Sendet eine Error-Embed Nachricht."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=EmbedColor.ERROR,
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


async def send_success(
    interaction: discord.Interaction,
    title: str,
    description: str,
    ephemeral: bool = False,
) -> None:
    """Sendet eine Success-Embed Nachricht."""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=EmbedColor.SUCCESS,
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


def build_llm_embed(
    question: str,
    answer: str,
    user: discord.User | discord.Member,
    model: str = "gpt-4o",
    tokens_used: int | None = None,
) -> list[discord.Embed]:
    """
    Erstellt strukturierte Embeds für LLM-Gateway Antworten.
    Gibt Liste zurück (bei langen Antworten mehrere Embeds).
    """
    chunks = _split_text(answer, DISCORD_EMBED_LIMIT)
    embeds: list[discord.Embed] = []

    for idx, chunk in enumerate(chunks, start=1):
        title = "💬 LLM Gateway"
        if len(chunks) > 1:
            title += f" ({idx}/{len(chunks)})"

        embed = discord.Embed(
            title=title,
            description=chunk,
            color=EmbedColor.LLM,
        )

        if idx == 1:
            # Erste Embed: Frage als Field
            short_q = textwrap.shorten(question, width=200, placeholder="…")
            embed.add_field(name="📝 Frage", value=short_q, inline=False)
            embed.set_author(
                name=str(user.display_name),
                icon_url=str(user.display_avatar.url) if user.display_avatar else None,
            )

        if idx == len(chunks):
            # Letzte Embed: Footer mit Metadaten
            footer_parts = [f"Modell: {model}"]
            if tokens_used:
                footer_parts.append(f"Tokens: {tokens_used:,}")
            embed.set_footer(text=" · ".join(footer_parts))

        embeds.append(embed)

    return embeds


def _split_text(text: str, limit: int) -> list[str]:
    """
    Splittet Text bei Zeilenumbrüchen, nie mitten in einem Wort.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    lines = text.splitlines(keepends=True)
    current = ""

    for line in lines:
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current.rstrip())
            # Einzelne Zeile > Limit: hart splitten
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current += line

    if current.strip():
        chunks.append(current.rstrip())

    return chunks if chunks else [text[:limit]]
