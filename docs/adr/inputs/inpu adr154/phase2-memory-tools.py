"""
orchestrator_mcp/tools/memory_tools.py

FastMCP Tool-Definitionen für Memory + Context.

Registriert:
  - agent_memory_upsert(...)
  - agent_memory_search(...)
  - agent_memory_context(...)   ← Top-K für session-start
  - get_full_context(...)       ← O-8 Unified Context API

WICHTIG: FastMCP läuft als standalone stdio-Prozess (kein ASGI).
asyncio ist hier direkt nutzbar — kein asgiref.async_to_sync nötig.
"""
from __future__ import annotations

import logging
from typing import Any

import fastmcp  # type: ignore

from orchestrator_mcp.services.context_service import ContextService
from orchestrator_mcp.services.memory_service import (
    MemoryService,
    MemoryEntrySchema,
    build_error_pattern_key,
    build_session_key,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FastMCP Tool: agent_memory_upsert
# ---------------------------------------------------------------------------

@fastmcp.tool
def agent_memory_upsert(
    entry_key: str,
    entry_type: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
    repo: str = "",
    structured_data: dict[str, Any] | None = None,
    tenant_id: int = 1,
) -> dict[str, Any]:
    """
    Erstellt oder aktualisiert einen Memory-Eintrag.

    entry_key: Deterministischer Key. Für Error-Patterns: build_error_pattern_key() nutzen.
    entry_type: error_pattern | lesson_learned | decision | context | task_result |
                rule_violation | repo_fact
    """
    try:
        entry = MemoryService.upsert_entry({
            "entry_key": entry_key,
            "entry_type": entry_type,
            "title": title,
            "content": content,
            "tags": tags or [],
            "repo": repo,
            "structured_data": structured_data,
            "tenant_id": tenant_id,
        })
        return {
            "success": True,
            "public_id": str(entry.public_id),
            "entry_key": entry_key,
            "message": f"Memory entry '{entry_key}' upserted.",
        }
    except Exception as exc:
        logger.error("agent_memory_upsert failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# FastMCP Tool: agent_memory_search
# ---------------------------------------------------------------------------

@fastmcp.tool
def agent_memory_search(
    query: str,
    entry_type: str | None = None,
    repo: str | None = None,
    top_k: int = 5,
    tenant_id: int = 1,
) -> dict[str, Any]:
    """
    Semantische Suche in Memory-Einträgen via pgvector.

    entry_type: Optional filter. Leer = alle Typen.
    repo: Optional filter. Leer = plattformweit + repo-spezifisch.
    """
    try:
        results = MemoryService.search_similar(
            query=query,
            tenant_id=tenant_id,
            entry_type=entry_type,
            repo=repo or None,
            top_k=top_k,
        )
        return {
            "success": True,
            "count": len(results),
            "results": results,
        }
    except Exception as exc:
        logger.error("agent_memory_search failed: %s", exc)
        return {"success": False, "error": str(exc), "results": []}


# ---------------------------------------------------------------------------
# FastMCP Tool: agent_memory_context (Warm-Start, O-3)
# ---------------------------------------------------------------------------

@fastmcp.tool
def agent_memory_context(
    task_description: str,
    repo: str = "",
    top_k: int = 5,
    tenant_id: int = 1,
) -> dict[str, Any]:
    """
    Warm-Start: Liefert Top-K relevante Memories für eine neue Session.

    Aufruf: Beim Session-Start, nach Repo-Detect.
    Gibt Memories aller entry_types zurück, sortiert nach Relevanz.
    """
    return agent_memory_search(
        query=task_description,
        entry_type=None,
        repo=repo or None,
        top_k=top_k,
        tenant_id=tenant_id,
    )


# ---------------------------------------------------------------------------
# FastMCP Tool: get_full_context (O-8)
# ---------------------------------------------------------------------------

@fastmcp.tool
async def get_full_context(
    repo: str,
    task_description: str,
    file_type: str = "python",
    include_issues: bool = True,
    tenant_id: int = 1,
) -> dict[str, Any]:
    """
    Unified Context API (O-8): Ein Aufruf für vollständigen Cascade-Kontext.

    Aggregiert parallel:
      - Repo-Facts (platform_context)
      - Rules + Banned Patterns
      - Relevante Memories (pgvector)
      - Outline Wiki-Treffer
      - Git-Log (letzten 5 Commits)
      - Offene GitHub Issues (optional)
      - Session-Delta (was hat sich seit letzter Session geändert)

    _warnings im Response = degradierte Backends (kein Fehler, nur Info).
    """
    try:
        service = _build_context_service(tenant_id)
        result = await service.get_full_context(
            repo=repo,
            task_description=task_description,
            file_type=file_type,
            include_issues=include_issues,
        )
        return {"success": True, **result.to_dict()}
    except Exception as exc:
        logger.error("get_full_context failed catastrophically: %s", exc)
        return {
            "success": False,
            "error": str(exc),
            "repo": repo,
            "task_description": task_description,
        }


# ---------------------------------------------------------------------------
# FastMCP Tool: log_error_pattern (Convenience-Wrapper für O-5)
# ---------------------------------------------------------------------------

@fastmcp.tool
def log_error_pattern(
    repo: str,
    error_type: str,
    symptom: str,
    root_cause: str,
    fix: str,
    prevention: str,
    file_path: str = "",
    tenant_id: int = 1,
) -> dict[str, Any]:
    """
    Erfasst ein Error-Pattern nach einem Bug-Fix (O-5).

    Nutzt deterministischen Hash-Key (R-09) zur Deduplizierung.
    """
    entry_key = build_error_pattern_key(repo, error_type, file_path)
    return agent_memory_upsert(
        entry_key=entry_key,
        entry_type="error_pattern",
        title=f"Error: {error_type[:100]}",
        content=(
            f"Symptom: {symptom}\n\n"
            f"Root Cause: {root_cause}\n\n"
            f"Fix: {fix}\n\n"
            f"Prevention: {prevention}"
        ),
        tags=[repo, "bugfix", error_type.lower().replace(" ", "-")[:50]],
        repo=repo,
        structured_data={
            "symptom": symptom,
            "root_cause": root_cause,
            "fix": fix,
            "prevention": prevention,
            "file_path": file_path,
        },
        tenant_id=tenant_id,
    )


# ---------------------------------------------------------------------------
# FastMCP Tool: end_session (session-ende Workflow, O-1)
# ---------------------------------------------------------------------------

@fastmcp.tool
def end_session(
    repo: str,
    task_summary: str,
    decisions_made: str = "",
    errors_encountered: str = "",
    lessons_learned: str = "",
    tenant_id: int = 1,
) -> dict[str, Any]:
    """
    Session-Ende: Schreibt Session-Summary in pgvector Memory (O-1).

    Aufruf: Am Ende jeder Cascade-Session automatisch via session-ende Workflow.
    """
    from orchestrator_mcp.models import AgentSession

    content_parts = [f"Task: {task_summary}"]
    if decisions_made:
        content_parts.append(f"Entscheidungen: {decisions_made}")
    if errors_encountered:
        content_parts.append(f"Fehler: {errors_encountered}")
    if lessons_learned:
        content_parts.append(f"Erkenntnisse: {lessons_learned}")

    entry_key = build_session_key(repo)
    result = agent_memory_upsert(
        entry_key=entry_key,
        entry_type="context",
        title=f"Session Summary: {repo} — {task_summary[:80]}",
        content="\n\n".join(content_parts),
        tags=[repo, "session-summary"],
        repo=repo,
        tenant_id=tenant_id,
    )

    # AgentSession abschließen (für Delta-Detection)
    try:
        from django.utils import timezone
        AgentSession.objects.filter(
            tenant_id=tenant_id,
            repo=repo,
            ended_at__isnull=True,
        ).update(ended_at=timezone.now())
    except Exception as exc:
        logger.warning("end_session: AgentSession update fehlgeschlagen: %s", exc)

    return result


# ---------------------------------------------------------------------------
# Factory (lazy init — Clients werden erst beim ersten Aufruf gebaut)
# ---------------------------------------------------------------------------

_context_service_cache: dict[int, ContextService] = {}


def _build_context_service(tenant_id: int) -> ContextService:
    if tenant_id in _context_service_cache:
        return _context_service_cache[tenant_id]

    from orchestrator_mcp.clients.platform_context_client import PlatformContextClient
    from orchestrator_mcp.clients.outline_client import OutlineClient
    from orchestrator_mcp.clients.github_client import GitHubClient

    service = ContextService(
        platform_context_client=PlatformContextClient(),
        memory_service_class=MemoryService,
        outline_client=OutlineClient(),
        github_client=GitHubClient(),
        tenant_id=tenant_id,
    )
    _context_service_cache[tenant_id] = service
    return service
