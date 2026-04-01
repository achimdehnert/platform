"""
orchestrator_mcp/services/context_service.py

ContextService — implementiert O-8: get_full_context() als Unified Context API.

Design-Entscheidungen:
  - asyncio.gather() für parallele Backend-Calls (R-04: Latenz < 1s statt 5s seriell)
  - asyncio.wait_for(timeout=3.0) pro Call — kein einzelner Call kann blockieren
  - Partial-Result-Pattern: jeder Backend-Fehler liefert None, nicht Exception (R-08)
  - Nur Felder in Response die tatsächlich vorhanden sind (kein null-padding)

WICHTIG: Diese Datei läuft im orchestrator_mcp FastMCP Server (standalone asyncio,
NICHT Django ASGI). asyncio.gather() ist hier korrekt.
Für Aufruf aus Django-Kontext: asgiref.sync_to_async(run_in_thread) nutzen.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result-Typen
# ---------------------------------------------------------------------------

@dataclass
class ContextResult:
    """Partial-Result-Pattern: jedes Feld kann None sein wenn Backend-Fehler."""
    repo: str
    task_description: str
    repo_facts: dict[str, Any] | None = None
    applicable_rules: list[dict] | None = None
    banned_patterns: list[str] | None = None
    memories: list[dict] | None = None
    outline_hits: list[dict] | None = None
    recent_commits: list[str] | None = None
    open_issues: list[dict] | None = None
    delta_since_last_session: dict[str, Any] | None = None
    backend_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Für MCP-Response: nur vorhandene Daten."""
        d: dict[str, Any] = {
            "repo": self.repo,
            "task_description": self.task_description,
        }
        if self.repo_facts is not None:
            d["repo_facts"] = self.repo_facts
        if self.applicable_rules is not None:
            d["applicable_rules"] = self.applicable_rules
        if self.banned_patterns is not None:
            d["banned_patterns"] = self.banned_patterns
        if self.memories is not None:
            d["memories"] = self.memories
        if self.outline_hits is not None:
            d["outline_hits"] = self.outline_hits
        if self.recent_commits is not None:
            d["recent_commits"] = self.recent_commits
        if self.open_issues is not None:
            d["open_issues"] = self.open_issues
        if self.delta_since_last_session is not None:
            d["delta_since_last_session"] = self.delta_since_last_session
        if self.backend_errors:
            d["_warnings"] = [f"Backend degraded: {e}" for e in self.backend_errors]
        return d


# ---------------------------------------------------------------------------
# ContextService
# ---------------------------------------------------------------------------

BACKEND_TIMEOUT = 3.0  # Sekunden pro Backend-Call


class ContextService:
    """
    Unified Context API (O-8).

    Aggregiert in einem Aufruf:
      - Repo-Facts (platform_context_mcp)
      - Rules + Banned Patterns
      - pgvector Memories (MemoryService)
      - Outline-Treffer
      - Git-Log (Delta)
      - GitHub Issues
      - Session-Delta (AgentSession)
    """

    def __init__(
        self,
        platform_context_client: Any,
        memory_service_class: Any,
        outline_client: Any | None = None,
        github_client: Any | None = None,
        tenant_id: int = 1,
    ) -> None:
        self._pc = platform_context_client
        self._memory_cls = memory_service_class
        self._outline = outline_client
        self._github = github_client
        self._tenant_id = tenant_id

    async def get_full_context(
        self,
        repo: str,
        task_description: str,
        file_type: str = "python",
        top_k_memories: int = 5,
        include_issues: bool = True,
    ) -> ContextResult:
        """
        Parallel-Aggregation aller Context-Quellen.

        Jeder Backend-Call hat eigenständigen Timeout + Fehler-Isolation (R-04, R-08).
        """
        result = ContextResult(repo=repo, task_description=task_description)

        # Alle Calls parallel starten
        tasks = {
            "repo_facts": self._safe_call(
                self._fetch_repo_facts(repo), "repo_facts"
            ),
            "rules": self._safe_call(
                self._fetch_rules(repo, file_type), "rules"
            ),
            "banned": self._safe_call(
                self._fetch_banned(file_type), "banned"
            ),
            "memories": self._safe_call(
                self._fetch_memories(task_description, repo, top_k_memories), "memories"
            ),
            "outline": self._safe_call(
                self._fetch_outline(task_description), "outline"
            ),
            "git_log": self._safe_call(
                self._fetch_git_log(repo), "git_log"
            ),
            "session_delta": self._safe_call(
                self._fetch_session_delta(repo), "session_delta"
            ),
        }
        if include_issues and self._github:
            tasks["issues"] = self._safe_call(
                self._fetch_issues(repo), "issues"
            )

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=False)
        named_results = dict(zip(tasks.keys(), gathered))

        # Results zuweisen, Errors sammeln
        for key, (value, error) in named_results.items():
            if error:
                result.backend_errors.append(f"{key}: {error}")
                logger.warning("get_full_context: Backend '%s' degraded: %s", key, error)
            else:
                if key == "repo_facts":
                    result.repo_facts = value
                elif key == "rules":
                    result.applicable_rules = value
                elif key == "banned":
                    result.banned_patterns = value
                elif key == "memories":
                    result.memories = value
                elif key == "outline":
                    result.outline_hits = value
                elif key == "git_log":
                    result.recent_commits = value
                elif key == "issues":
                    result.open_issues = value
                elif key == "session_delta":
                    result.delta_since_last_session = value

        logger.info(
            "get_full_context: repo=%s backends_ok=%s degraded=%s",
            repo,
            len(tasks) - len(result.backend_errors),
            len(result.backend_errors),
        )
        return result

    # ------------------------------------------------------------------
    # Backend-Fetcher (alle mit individuellem Timeout)
    # ------------------------------------------------------------------

    async def _fetch_repo_facts(self, repo: str) -> dict:
        return await asyncio.wait_for(
            asyncio.to_thread(self._pc.get_repo_facts, repo),
            timeout=BACKEND_TIMEOUT,
        )

    async def _fetch_rules(self, repo: str, file_type: str) -> list[dict]:
        return await asyncio.wait_for(
            asyncio.to_thread(self._pc.get_rules_for_context, repo, file_type),
            timeout=BACKEND_TIMEOUT,
        )

    async def _fetch_banned(self, file_type: str) -> list[str]:
        return await asyncio.wait_for(
            asyncio.to_thread(self._pc.get_banned_patterns, file_type),
            timeout=BACKEND_TIMEOUT,
        )

    async def _fetch_memories(
        self, task_description: str, repo: str, top_k: int
    ) -> list[dict]:
        return await asyncio.wait_for(
            asyncio.to_thread(
                self._memory_cls.search_similar,
                task_description,
                self._tenant_id,
                None,  # alle entry_types
                repo,
                top_k,
            ),
            timeout=BACKEND_TIMEOUT,
        )

    async def _fetch_outline(self, query: str) -> list[dict]:
        if not self._outline:
            return []
        return await asyncio.wait_for(
            asyncio.to_thread(self._outline.search, query, limit=3),
            timeout=BACKEND_TIMEOUT,
        )

    async def _fetch_git_log(self, repo: str) -> list[str]:
        """Git-Log der letzten 5 Commits via subprocess."""
        import subprocess
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "git", "-C", f"/repos/{repo}", "log",
                "--oneline", "-5",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            ),
            timeout=BACKEND_TIMEOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip().splitlines() if stdout else []

    async def _fetch_issues(self, repo: str) -> list[dict]:
        if not self._github:
            return []
        return await asyncio.wait_for(
            asyncio.to_thread(
                self._github.list_issues, repo, state="open", per_page=5
            ),
            timeout=BACKEND_TIMEOUT,
        )

    async def _fetch_session_delta(self, repo: str) -> dict:
        """
        Delta seit letzter Session (O-9 / R-11).
        Nutzt AgentSession-Tabelle statt pgvector-Timestamps.
        """
        return await asyncio.wait_for(
            asyncio.to_thread(self._compute_session_delta, repo),
            timeout=BACKEND_TIMEOUT,
        )

    def _compute_session_delta(self, repo: str) -> dict:
        """Sync-Methode für asyncio.to_thread()."""
        try:
            from orchestrator_mcp.models import AgentSession
            last_session = (
                AgentSession.objects
                .filter(tenant_id=self._tenant_id, repo=repo)
                .order_by("-started_at")
                .first()
            )
            if not last_session:
                return {"first_session": True}
            return {
                "last_session_started": last_session.started_at.isoformat(),
                "last_session_errors": last_session.error_count,
                "last_session_corrections": last_session.correction_count,
                "sessions_on_repo": AgentSession.objects.filter(
                    tenant_id=self._tenant_id, repo=repo
                ).count(),
            }
        except Exception as exc:
            logger.warning("_compute_session_delta: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Helper: Safe-Call Wrapper
    # ------------------------------------------------------------------

    @staticmethod
    async def _safe_call(
        coro: Any, name: str
    ) -> tuple[Any, str | None]:
        """
        Führt Coroutine aus und gibt (result, error_str) zurück.
        Kein Backend-Fehler kann get_full_context() zum Absturz bringen (R-08).
        """
        try:
            result = await coro
            return result, None
        except asyncio.TimeoutError:
            return None, f"timeout after {BACKEND_TIMEOUT}s"
        except Exception as exc:
            return None, str(exc)[:200]
