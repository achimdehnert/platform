"""
Repo Scan Skill — automatisches Repo-Onboarding via GitHub API.

Rate-Limit: exponential backoff, X-RateLimit-Remaining auswerten.
Auth: GITHUB_TOKEN Env-Var (aus GitHub Actions oder PROJECT_PAT).
Ergebnis: wird als REPO_CONTEXT Entry in AGENT_MEMORY.md gespeichert.
"""
from __future__ import annotations

import base64
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

from .base import GateLevel, Skill, SkillResult
from .memory_schema import EntryType, MemoryEntry
from .session_memory import MEMORY_FILE, _git_commit, _read_store, _write_store

log = logging.getLogger(__name__)

GITHUB_API   = "https://api.github.com"
DEFAULT_ORG = "achimdehnert"
MAX_RETRIES  = 3
BACKOFF_BASE = 2.0


def _github_request(
    endpoint: str,
    token: str,
    timeout: int = 30,
    attempt: int = 0,
) -> dict | list | None:
    """
    GitHub API GET mit Rate-Limit-Handling und exponential Backoff.

    Returns:
        Parsed JSON oder None bei 404
    """
    url = f"{GITHUB_API}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)

        remaining = int(response.headers.get("X-RateLimit-Remaining", 1000))
        if remaining < 10:
            reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
            wait = max(0, reset_ts - int(time.time())) + 1
            log.warning(
                "GitHub Rate-Limit fast erschöpft (%d remaining) — warte %ds",
                remaining, wait,
            )
            time.sleep(wait)

        if response.status_code == 404:
            log.warning("GitHub 404: %s", url)
            return None

        if response.status_code == 403 and "rate limit" in response.text.lower():
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** (attempt + 1)
                log.warning(
                    "Rate-Limit hit — Backoff %ds (attempt %d/%d)",
                    wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
                return _github_request(endpoint, token, timeout, attempt + 1)
            raise RuntimeError(
                f"GitHub Rate-Limit nach {MAX_RETRIES} Retries nicht überwunden"
            )

        response.raise_for_status()
        return response.json()

    except httpx.TimeoutException:
        if attempt < MAX_RETRIES:
            wait = BACKOFF_BASE ** (attempt + 1)
            log.warning("Timeout — Backoff %ds", wait)
            time.sleep(wait)
            return _github_request(endpoint, token, timeout, attempt + 1)
        raise


def _check_health(health_url: str, timeout: int = 10) -> str:
    """Health-URL prüfen."""
    if not health_url:
        return "⚠️ UNKNOWN (keine Health-URL)"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(health_url)
        if response.status_code < 400:
            return f"✅ OK ({response.status_code})"
        return f"❌ DOWN ({response.status_code})"
    except Exception as exc:
        return f"❌ ERROR ({type(exc).__name__})"


def _extract_health_url(compose_content: str | None) -> str:
    """Versucht Health-URL aus docker-compose.prod.yml zu extrahieren."""
    if not compose_content:
        return ""
    for line in compose_content.splitlines():
        if "VIRTUAL_HOST=" in line or "LETSENCRYPT_HOST=" in line:
            host = line.split("=", 1)[-1].strip().strip('"').strip("'")
            if host:
                return f"https://{host}/healthz/"
    return ""


class RepoScanSkill(Skill):
    """
    Scannt ein Repo und speichert den Kontext in AGENT_MEMORY.md.

    Erkennt: Framework, Health-URL, Migrations-Stand,
    offene Agent-Issues, AGENT_HANDOVER.md.
    """

    def invoke(
        self,
        repo_name: str = "",
        org: str = DEFAULT_ORG,
        branch: str = "main",
        github_token: str | None = None,
        commit: bool = True,
        dry_run: bool = False,
    ) -> SkillResult:
        if not repo_name:
            return SkillResult.fail(self.name, "repo_name ist erforderlich")

        token = (
            github_token
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("PROJECT_PAT")
        )
        if not token:
            return SkillResult.fail(
                self.name,
                "Kein GitHub Token verfügbar. Setze GITHUB_TOKEN oder PROJECT_PAT.",
            )

        full_name = f"{org}/{repo_name}"
        log.info("Starte Repo-Scan: %s", full_name)

        repo_info = _github_request(f"/repos/{full_name}", token)
        if repo_info is None:
            return SkillResult.fail(self.name, f"Repo '{full_name}' nicht gefunden")

        context: dict = {
            "repo": full_name,
            "branch": branch,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "private": repo_info.get("private", True),
            "description": repo_info.get("description", ""),
            "default_branch": repo_info.get("default_branch", "main"),
        }

        # Framework erkennen
        requirements = _github_request(
            f"/repos/{full_name}/contents/requirements.txt?ref={branch}", token,
        )
        if requirements and isinstance(requirements, dict):
            try:
                req_text = base64.b64decode(
                    requirements.get("content", "")
                ).decode("utf-8", errors="ignore")
                if "django" in req_text.lower():
                    context["framework"] = "Django"
                elif "fastapi" in req_text.lower():
                    context["framework"] = "FastAPI"
                else:
                    context["framework"] = "Unknown"
            except Exception:
                context["framework"] = "Unknown"

        # Health-URL aus docker-compose.prod.yml
        compose = _github_request(
            f"/repos/{full_name}/contents/docker-compose.prod.yml?ref={branch}", token,
        )
        compose_content = None
        if compose and isinstance(compose, dict):
            try:
                compose_content = base64.b64decode(
                    compose.get("content", "")
                ).decode("utf-8", errors="ignore")
            except Exception:
                pass

        health_url = _extract_health_url(compose_content)
        context["health_url"] = health_url
        context["health_status"] = _check_health(health_url) if health_url else "⚠️ UNKNOWN"

        # Migrations-Stand
        root = _github_request(
            f"/repos/{full_name}/contents?ref={branch}", token,
        )
        if root and isinstance(root, list):
            app_dirs = [f["name"] for f in root if f["type"] == "dir"]
            for app_dir in app_dirs[:5]:
                mig_dir = _github_request(
                    f"/repos/{full_name}/contents/{app_dir}/migrations?ref={branch}",
                    token,
                )
                if mig_dir and isinstance(mig_dir, list):
                    migration_files = sorted(
                        [
                            f["name"] for f in mig_dir
                            if f["name"].endswith(".py") and f["name"] != "__init__.py"
                        ],
                        reverse=True,
                    )
                    if migration_files:
                        context["latest_migration"] = f"{app_dir}/{migration_files[0]}"
                        context["has_migrations"] = True
                        break
            else:
                context["has_migrations"] = False

        # AGENT_HANDOVER.md
        handover = _github_request(
            f"/repos/{full_name}/contents/AGENT_HANDOVER.md?ref={branch}", token,
        )
        if handover and isinstance(handover, dict):
            try:
                handover_text = base64.b64decode(
                    handover.get("content", "")
                ).decode("utf-8", errors="ignore")
                context["has_handover"] = True
                context["handover_preview"] = handover_text[:500]
            except Exception:
                context["has_handover"] = False
        else:
            context["has_handover"] = False

        # Offene Agent-Issues
        issues = _github_request(
            f"/repos/{full_name}/issues?labels=agent-task&state=open&per_page=10",
            token,
        )
        context["open_agent_tasks"] = (
            [{"number": i["number"], "title": i["title"]} for i in issues]
            if issues and isinstance(issues, list)
            else []
        )

        log.info("Repo-Scan abgeschlossen: %s", full_name)

        if dry_run:
            return SkillResult.ok(
                skill_name=self.name,
                data={"repo_context": context, "dry_run": True},
                message=f"Dry Run: Kontext für '{full_name}' ermittelt (nicht gespeichert)",
            )

        entry = MemoryEntry(
            entry_id=f"R-{repo_name.upper().replace('-', '')[:20]}",
            entry_type=EntryType.REPO_CONTEXT,
            title=f"Repo-Kontext: {full_name}",
            content=str(context),
            agent=self.name,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            tags=["repo", org, repo_name],
            metadata=context,
        )
        store = _read_store()
        store.upsert(entry, agent=self.name)
        _write_store(store)

        if commit:
            _git_commit(
                MEMORY_FILE,
                f"agent-memory: repo-scan {full_name} [{context.get('health_status', '?')}]",
            )

        return SkillResult.ok(
            skill_name=self.name,
            data={"repo_context": context, "entry_id": entry.entry_id},
            message=f"Repo '{full_name}' gescannt und in AGENT_MEMORY.md gespeichert",
        )


SKILL = RepoScanSkill(
    name="repo_scan",
    version="1.0.0",
    domain="infra",
    description="Scannt ein GitHub-Repo und speichert Infra-Kontext in AGENT_MEMORY.md (Framework, Health, Migrations, offene Tasks)",
    mcp_tool_name="scan_repo",
    gate_level=GateLevel.NOTIFY,
    depends_on=["session_memory"],
)
