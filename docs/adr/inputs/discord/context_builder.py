"""
orchestrator_mcp/discord/context_builder.py

System-Prompt Builder für Layer 2 LLM Gateway.
- Lädt ADRs aus Filesystem (gecacht, 5min TTL)
- Filtert Credentials/Secrets heraus (K1-Fix aus ADR-114 Review)
- pgvector Similarity-Search für relevante Memories
- Token-Budget Management
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ─── Konfiguration ────────────────────────────────────────────────────────────

ADR_DIRECTORY = Path("/app/adrs")           # Gemountetes ADR-Verzeichnis
ADR_CACHE_TTL = 300                         # 5 Minuten Cache
MAX_ADR_TOKENS = 3000                       # Token-Budget für ADRs
MAX_MEMORY_TOKENS = 2000                    # Token-Budget für pgvector Memories
MAX_TOTAL_CONTEXT_TOKENS = 6000             # Gesamt-Budget

# Patterns die aus ADRs herausgefiltert werden (K1-Fix)
SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?i)(api[_\s]?key|token|secret|password|passwd|credential)[s]?\s*[=:]\s*\S+'),
    re.compile(r'(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*'),
    re.compile(r'[A-Za-z0-9]{32,}'),        # Lange zufällige Strings (potentielle Keys)
    re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),  # IP-Adressen
    re.compile(r'(?i)ssh-rsa\s+\S+'),
    re.compile(r'(?i)-----BEGIN .+?-----'),
]

PLATFORM_CONTEXT_TEMPLATE = """\
# Platform Stack Context

Du bist ein KI-Assistent für die iil.gmbh Platform (KI-ohne-Risiko™).

## Stack
- Backend: Django 4.2, HTMX, PostgreSQL + pgvector, Celery, Redis
- Deployment: Hetzner VPS, Docker Compose, Traefik, GitHub Actions
- Services: orchestrator_mcp, platform_context, llm_mcp, risk-hub, cad-hub, weltenhub
- AI: OpenRouter (GPT-4o, Claude), FastMCP, Windsurf/Cascade

## Aktive ADRs (gefiltert, keine Credentials)
{adr_context}

## Relevante Memories aus pgvector
{memory_context}

## Offene GitHub Issues (Top 5)
{issue_context}

## Wichtige Constraints
- Platform-Standard: BigAutoField PK, tenant_id, Soft-Delete, Service-Layer-Pattern
- Alle Antworten auf Deutsch, Code-Kommentare auf Englisch
- Keine Credentials oder IPs in Antworten nennen
"""


# ─── Cache ────────────────────────────────────────────────────────────────────

@dataclass
class _CacheEntry:
    content: str
    loaded_at: float = field(default_factory=time.monotonic)

    def is_valid(self) -> bool:
        return time.monotonic() - self.loaded_at < ADR_CACHE_TTL


_adr_cache: Optional[_CacheEntry] = None


# ─── Public API ───────────────────────────────────────────────────────────────

async def build_system_prompt(
    user_query: str,
    pgvector_url: str,
    github_token: str,
    github_repo: str,
) -> str:
    """
    Baut den System-Prompt für Layer 2 LLM Gateway.

    Args:
        user_query:    Die Frage des Users (für pgvector Similarity-Search)
        pgvector_url:  URL des pgvector Memory-Service
        github_token:  GitHub PAT für Issue-Abfrage
        github_repo:   z.B. "iilgmbh/mcp-hub"
    """
    adr_ctx = await _load_adrs_cached()
    memory_ctx = await _load_relevant_memories(user_query, pgvector_url)
    issue_ctx = await _load_open_issues(github_token, github_repo)

    prompt = PLATFORM_CONTEXT_TEMPLATE.format(
        adr_context=adr_ctx or "_Keine ADRs geladen_",
        memory_context=memory_ctx or "_Keine relevanten Memories_",
        issue_context=issue_ctx or "_Keine offenen Issues_",
    )

    token_estimate = len(prompt.split()) * 1.3  # Grobe Schätzung
    logger.info(
        "system_prompt_built",
        extra={"estimated_tokens": int(token_estimate), "query_len": len(user_query)},
    )
    return prompt


# ─── ADR Loader ───────────────────────────────────────────────────────────────

async def _load_adrs_cached() -> str:
    global _adr_cache
    if _adr_cache and _adr_cache.is_valid():
        return _adr_cache.content

    content = await _load_adrs_from_disk()
    _adr_cache = _CacheEntry(content=content)
    logger.info("adr_cache_refreshed", extra={"char_count": len(content)})
    return content


async def _load_adrs_from_disk() -> str:
    """Lädt alle ADR .md Dateien, filtert Secrets, kürzt auf Token-Budget."""
    if not ADR_DIRECTORY.exists():
        logger.warning("adr_directory_not_found", extra={"path": str(ADR_DIRECTORY)})
        return ""

    adr_files = sorted(ADR_DIRECTORY.glob("ADR-*.md"), reverse=True)  # Neueste zuerst
    if not adr_files:
        return ""

    parts: list[str] = []
    total_chars = 0
    char_budget = MAX_ADR_TOKENS * 4  # ~4 chars per token

    for adr_file in adr_files:
        try:
            raw = adr_file.read_text(encoding="utf-8")
            clean = _filter_secrets(raw)

            # Nur Header + Status + Entscheidung laden (nicht kompletter ADR)
            summary = _extract_adr_summary(clean, adr_file.name)

            if total_chars + len(summary) > char_budget:
                logger.debug(
                    "adr_skipped_budget",
                    extra={"file": adr_file.name, "total_chars": total_chars},
                )
                break

            parts.append(summary)
            total_chars += len(summary)

        except Exception as e:
            logger.warning("adr_load_error", extra={"file": str(adr_file), "error": str(e)})

    return "\n\n---\n\n".join(parts)


def _filter_secrets(text: str) -> str:
    """Entfernt Credentials und sensible Daten aus ADR-Text."""
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def _extract_adr_summary(adr_text: str, filename: str) -> str:
    """Extrahiert relevante Teile eines ADRs (Status, Entscheidung, Konsequenzen)."""
    lines = adr_text.splitlines()
    relevant: list[str] = []
    in_section = False
    keep_sections = {"# ", "## status", "## entscheidung", "## decision",
                     "## konsequenzen", "## consequences", "## problemstellung"}

    for line in lines:
        line_lower = line.lower().strip()
        if any(line_lower.startswith(s) for s in keep_sections):
            in_section = True
        elif line.startswith("## ") and not any(line_lower.startswith(s) for s in keep_sections):
            in_section = False

        if in_section:
            relevant.append(line)

    return f"### {filename}\n" + "\n".join(relevant[:50])  # max 50 Zeilen pro ADR


# ─── pgvector Memory Loader ───────────────────────────────────────────────────

async def _load_relevant_memories(query: str, pgvector_url: str) -> str:
    """Lädt relevante Memories via pgvector Similarity-Search."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{pgvector_url}/search",
                json={"query": query, "limit": 5, "min_score": 0.7},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])

        if not results:
            return ""

        parts = [
            f"- [{r.get('created_at', '')[:10]}] {r.get('content', '')[:300]}"
            for r in results
        ]
        return "\n".join(parts)

    except Exception as e:
        logger.warning("pgvector_load_failed", extra={"error": str(e)})
        return "_Memory-Service nicht erreichbar_"


# ─── GitHub Issues Loader ─────────────────────────────────────────────────────

async def _load_open_issues(github_token: str, repo: str) -> str:
    """Lädt die 5 neuesten offenen GitHub Issues."""
    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        ) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/issues",
                params={"state": "open", "per_page": 5, "sort": "updated"},
            )
            resp.raise_for_status()
            issues = resp.json()

        if not issues:
            return ""

        parts = [
            f"- #{i['number']} [{', '.join(l['name'] for l in i.get('labels', []))}] "
            f"{i['title']}"
            for i in issues
        ]
        return "\n".join(parts)

    except Exception as e:
        logger.warning("github_issues_load_failed", extra={"error": str(e)})
        return "_GitHub nicht erreichbar_"
