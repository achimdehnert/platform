"""
orchestrator_mcp/discord/handlers.py

Discord Slash Command Handler — Layer 1 + Layer 2.
Alle BLOCKER aus ADR-114 Review behoben:
  B1: Role Guards via @require_role
  B2: Async-safe httpx (kein asyncio.run())
  B3: Rate Limiter via @rate_limit
  B4: send_chunked() für lange Antworten
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

import discord
import httpx
from discord import app_commands

from .context_builder import build_system_prompt
from .guards import require_role
from .rate_limit import rate_limit
from .utils import (
    EmbedColor,
    build_llm_embed,
    send_chunked,
    send_error,
    send_success,
)

logger = logging.getLogger(__name__)


# ─── Einstellungen (aus Django settings oder env) ─────────────────────────────
# In Produktion: aus orchestrator_mcp.core.config importieren

class _Settings:
    LLM_MCP_URL: str = "http://llm-worker:8001"
    LLM_MCP_API_KEY: str = ""           # Aus Env: LLM_MCP_API_KEY
    PGVECTOR_URL: str = "http://pgvector-service:8002"
    GITHUB_TOKEN: str = ""              # Aus Env: GITHUB_TOKEN
    GITHUB_REPO: str = "iilgmbh/mcp-hub"
    LLM_MODEL: str = "openai/gpt-4o"
    AUDIT_CHANNEL_NAME: str = "log"


settings = _Settings()


# ─── Layer 1: Sofort-Steuerung ────────────────────────────────────────────────

async def cmd_health(interaction: discord.Interaction) -> None:
    """
    /health — Server-Status (erweiterter Health-Check, kein LLM).
    Prüft alle Layer-Dependencies.
    """
    await interaction.response.defer()

    checks: dict[str, bool] = {}

    # Layer 2 Health
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.LLM_MCP_URL}/health")
            checks["llm_mcp"] = r.status_code == 200
    except Exception:
        checks["llm_mcp"] = False

    # pgvector Health
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.PGVECTOR_URL}/health")
            checks["pgvector"] = r.status_code == 200
    except Exception:
        checks["pgvector"] = False

    # GitHub API Connectivity
    try:
        async with httpx.AsyncClient(
            timeout=3.0,
            headers={"Authorization": f"Bearer {settings.GITHUB_TOKEN}"},
        ) as client:
            r = await client.get("https://api.github.com/rate_limit")
            checks["github"] = r.status_code == 200
    except Exception:
        checks["github"] = False

    all_ok = all(checks.values())
    lines = [
        f"{'✅' if ok else '❌'} `{name}`"
        for name, ok in checks.items()
    ]
    embed = discord.Embed(
        title="🏥 Platform Health",
        description="\n".join(lines),
        color=EmbedColor.SUCCESS if all_ok else EmbedColor.ERROR,
    )
    await interaction.followup.send(embed=embed)
    await _audit_log(interaction, "health", f"all_ok={all_ok}")


@require_role("deploy")
@rate_limit("deploy")
async def cmd_deploy(interaction: discord.Interaction, service: str) -> None:
    """
    /deploy <service> — GitHub Actions Workflow triggern (nur platform-admin/devops).
    """
    await interaction.response.defer()

    correlation_id = str(uuid.uuid4())[:8]
    logger.info(
        "deploy_triggered",
        extra={
            "service": service,
            "user_id": interaction.user.id,
            "correlation_id": correlation_id,
        },
    )

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        ) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{settings.GITHUB_REPO}/actions/workflows/deploy.yml/dispatches",
                json={"ref": "main", "inputs": {"service": service}},
            )
            resp.raise_for_status()

        await send_success(
            interaction,
            "Deploy gestartet",
            f"Service `{service}` wird deployed.\nCorrelation-ID: `{correlation_id}`",
        )
    except httpx.HTTPStatusError as e:
        await send_error(
            interaction,
            "Deploy fehlgeschlagen",
            f"GitHub API Fehler: `{e.response.status_code}`\n```{e.response.text[:200]}```",
        )

    await _audit_log(interaction, "deploy", f"service={service} correlation={correlation_id}")


@require_role("approve")
@rate_limit("deploy")
async def cmd_approve(interaction: discord.Interaction, issue_number: int) -> None:
    """
    /approve <issue_number> — Gate-Entscheidung: Issue approven (nur platform-admin/devops).
    """
    await interaction.response.defer()
    await _set_issue_label(interaction, issue_number, label="approved", remove="rejected")
    await _audit_log(interaction, "approve", f"issue=#{issue_number}")


@require_role("reject")
@rate_limit("deploy")
async def cmd_reject(
    interaction: discord.Interaction,
    issue_number: int,
    reason: Optional[str] = None,
) -> None:
    """
    /reject <issue_number> [reason] — Gate-Entscheidung: Issue ablehnen.
    """
    await interaction.response.defer()
    await _set_issue_label(interaction, issue_number, label="rejected", remove="approved")
    if reason:
        await _add_issue_comment(issue_number, f"❌ Abgelehnt: {reason}")
    await _audit_log(interaction, "reject", f"issue=#{issue_number} reason={reason}")


# ─── Layer 2: LLM Gateway ─────────────────────────────────────────────────────

@require_role("chat")
@rate_limit("chat")
async def cmd_chat(
    interaction: discord.Interaction,
    message: str,
    thread: bool = False,
) -> None:
    """
    /chat <message> [thread=True] — LLM Gateway mit Platform-Kontext.

    B2-Fix: Vollständig async (kein asyncio.run()).
    B3-Fix: @rate_limit Decorator.
    B4-Fix: build_llm_embed() mit Chunking.
    K1-Fix: context_builder filtert Secrets.
    """
    await interaction.response.defer()   # Discord 3s Timeout umgehen

    correlation_id = str(uuid.uuid4())[:8]
    logger.info(
        "chat_request",
        extra={
            "user_id": interaction.user.id,
            "message_len": len(message),
            "correlation_id": correlation_id,
        },
    )

    # System-Prompt bauen (ADRs + pgvector, Secrets gefiltert)
    try:
        system_prompt = await build_system_prompt(
            user_query=message,
            pgvector_url=settings.PGVECTOR_URL,
            github_token=settings.GITHUB_TOKEN,
            github_repo=settings.GITHUB_REPO,
        )
    except Exception as e:
        logger.error("context_build_failed", extra={"error": str(e)})
        system_prompt = "Du bist ein KI-Assistent für die iil.gmbh Platform."

    # LLM-Aufruf (async, kein asyncio.run!)
    try:
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {settings.LLM_MCP_API_KEY}",
                "X-Correlation-ID": correlation_id,
            },
        ) as client:
            resp = await client.post(
                f"{settings.LLM_MCP_URL}/v1/chat",
                json={
                    "message": message,
                    "system_prompt": system_prompt,
                    "model": settings.LLM_MODEL,
                    "user_id": str(interaction.user.id),
                    "correlation_id": correlation_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        await send_error(
            interaction,
            "LLM Timeout",
            "Der LLM-Service antwortet nicht (>60s). Bitte später erneut versuchen.",
        )
        return
    except httpx.HTTPStatusError as e:
        await send_error(
            interaction,
            "LLM Fehler",
            f"Status `{e.response.status_code}` — Correlation-ID: `{correlation_id}`",
        )
        return

    answer: str = data.get("answer", "_Keine Antwort erhalten_")
    tokens_used: int = data.get("tokens_used", 0)
    model_used: str = data.get("model", settings.LLM_MODEL)

    # Embeds bauen (mit Chunking für lange Antworten — B4-Fix)
    embeds = build_llm_embed(
        question=message,
        answer=answer,
        user=interaction.user,
        model=model_used,
        tokens_used=tokens_used,
    )

    # Discord Thread optional anlegen
    target = interaction
    if thread and isinstance(interaction.channel, discord.TextChannel):
        created_thread = await interaction.channel.create_thread(
            name=f"Chat: {message[:50]}",
            auto_archive_duration=60,
        )
        for embed in embeds:
            await created_thread.send(embed=embed)
        await interaction.followup.send(
            f"Antwort in Thread: {created_thread.mention}", ephemeral=True
        )
    else:
        for embed in embeds:
            await interaction.followup.send(embed=embed)

    await _audit_log(
        interaction, "chat",
        f"tokens={tokens_used} model={model_used} correlation={correlation_id}",
    )


@require_role("ask")
@rate_limit("ask")
async def cmd_ask(interaction: discord.Interaction, question: str) -> None:
    """
    /ask <question> — Layer 3: GitHub Issue für Cascade anlegen.
    """
    await interaction.response.defer()

    issue_title = f"[cascade-task] {question[:100]}"
    issue_body = (
        f"**Von:** {interaction.user.mention} ({interaction.user})\n"
        f"**Kanal:** {getattr(interaction.channel, 'mention', 'DM')}\n\n"
        f"## Frage\n{question}\n\n"
        f"---\n_Automatisch erstellt via Discord `/ask` Command_"
    )

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        ) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{settings.GITHUB_REPO}/issues",
                json={
                    "title": issue_title,
                    "body": issue_body,
                    "labels": ["cascade-task"],
                },
            )
            resp.raise_for_status()
            issue = resp.json()

        issue_url = issue["html_url"]
        issue_number = issue["number"]

        embed = discord.Embed(
            title="📋 Cascade Task erstellt",
            description=(
                f"Issue [#{issue_number}]({issue_url}) wurde angelegt.\n"
                f"Cascade wird antworten und dich hier benachrichtigen.\n\n"
                f"⏱️ Erwartete Antwortzeit: **Minuten bis Stunden** "
                f"(Cascade muss die IDE öffnen)."
            ),
            color=EmbedColor.CASCADE,
        )
        await interaction.followup.send(embed=embed)

    except httpx.HTTPStatusError as e:
        await send_error(
            interaction, "GitHub Fehler",
            f"Issue konnte nicht erstellt werden: `{e.response.status_code}`",
        )
        return

    await _audit_log(interaction, "ask", f"issue=#{issue_number} question_len={len(question)}")


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

async def _set_issue_label(
    interaction: discord.Interaction,
    issue_number: int,
    label: str,
    remove: str,
) -> None:
    """Setzt Label auf GitHub Issue (idempotent)."""
    base_url = f"https://api.github.com/repos/{settings.GITHUB_REPO}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            # Bestehende Labels holen
            r = await client.get(base_url)
            r.raise_for_status()
            current_labels = [l["name"] for l in r.json().get("labels", [])]

            # remove herausnehmen, label hinzufügen (deduped)
            new_labels = list({l for l in current_labels if l != remove} | {label})
            await client.patch(base_url, json={"labels": new_labels})

        await send_success(
            interaction,
            f"Issue #{issue_number} {label}",
            f"Label `{label}` gesetzt.",
        )
    except Exception as e:
        await send_error(interaction, "GitHub Fehler", str(e))


async def _add_issue_comment(issue_number: int, comment: str) -> None:
    """Fügt Kommentar zu GitHub Issue hinzu."""
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        ) as client:
            await client.post(
                f"https://api.github.com/repos/{settings.GITHUB_REPO}/issues/{issue_number}/comments",
                json={"body": comment},
            )
    except Exception as e:
        logger.warning("add_comment_failed", extra={"error": str(e)})


async def _audit_log(
    interaction: discord.Interaction,
    command: str,
    details: str = "",
) -> None:
    """Sendet Audit-Log in #log Channel."""
    guild = interaction.guild
    if not guild:
        return

    log_channel = discord.utils.get(guild.text_channels, name=settings.AUDIT_CHANNEL_NAME)
    if not log_channel:
        return

    embed = discord.Embed(
        title=f"📋 /{command}",
        description=details or "—",
        color=EmbedColor.INFO,
    )
    embed.set_author(
        name=str(interaction.user),
        icon_url=str(interaction.user.display_avatar.url),
    )
    embed.set_footer(text=f"Channel: {getattr(interaction.channel, 'name', 'DM')}")

    try:
        await log_channel.send(embed=embed)
    except discord.Forbidden:
        logger.warning("audit_log_forbidden", extra={"channel": settings.AUDIT_CHANNEL_NAME})
