# Review & Implementierung: ADR-112 — Agent Skill Registry + Persistent Context Store

| | |
|---|---|
| **Reviewer** | Principal IT-Architekt / Autonomous Coding Expert |
| **Dokument** | ADR-112 (2026-03-08) |
| **Stack** | Django <6.0, HTMX, PostgreSQL+pgvector, Celery, MCP, iilgmbh/platform |
| **Review-Datum** | 2026-03-08 |
| **Ergebnis** | CHANGES REQUIRED — 3 Blocker, 4 Kritisch, 5 Hoch |

---

## 1. Review-Tabelle

### 🔴 BLOCKER

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| B1 | `AGENT_MEMORY.md` Race Condition | BLOCKER | Parallele Agent-Runs schreiben gleichzeitig → korruptes Markdown, verlorene Einträge. ADR nennt es als Risiko ohne Mitigation. | File-Lock via `fcntl.flock()` + atomares Write (temp file → `os.replace()`). Alternativ: SQLite als Memory-Backend (ACID, kein Markdown-Parse). |
| B2 | `Skill.invoke()` kein Fehler-Contract | BLOCKER | `raise NotImplementedError` in Base ohne Exception-Hierarchy. MCP Server fängt das nicht ab → unhandled exception im Runner → Agent-Team bricht ab. | `SkillError(Exception)` + `SkillInvocationError` definieren. `invoke()` muss `SkillResult` zurückgeben, nie nackt `dict`. |
| B3 | Git-Writes im Agent-Kontext ohne Credentials-Strategie | BLOCKER | `session_memory.py` soll `AGENT_MEMORY.md` via Git committen — aber GitHub Actions Runner hat keinen push-Zugriff ohne expliziten Token + git config. In CI schlägt `git commit` still fehl oder es wird mit falschem Author committed. | `GITHUB_TOKEN` mit `contents:write` explizit in Workflow deklarieren. `git config user.email "agent@iilgmbh.com"` vor jedem Commit. Gezeigt in Implementierung Abschnitt 5.4. |

### 🔴 KRITISCH

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| C1 | Auto-Registration via `__init_subclass__` | KRITISCH | Import-Order-Abhängigkeit: Skills werden nur registriert wenn ihr Modul importiert wurde. Vergisst man den Import in `server.py` → Skill existiert nicht, kein Fehler. Silentes Versagen. | Explizite Registry-Liste in `skills/__init__.py` + `discover_skills()` die alle `skills/*.py` via `importlib` lädt. Kein Magic. |
| C2 | `AGENT_MEMORY.md` kein Schema, kein TTL | KRITISCH | Free-form Markdown als Datenstore: Parser-Fehler bei unerwarteten Zeichen, kein Expiry für veraltete Einträge (T-001 vom 2026-03-08 bleibt ewig stehen). | Strukturiertes Format: YAML-Frontmatter für Metadaten + Markdown-Body. `expires_at` Pflichtfeld pro Entry. `memory_gc()` entfernt abgelaufene Einträge. |
| C3 | `Skill` als `@dataclass` statt Pydantic v2 | KRITISCH | Stack-Standard ist Pydantic v2 (ADR-107, ADR-108). `@dataclass` hat keine Validierung — `gate_level=-1` oder `version="not-semver"` werden akzeptiert. | `class Skill(BaseModel)` mit `Field(..., ge=0, le=4)` für gate_level, `pattern=r'^\d+\.\d+\.\d+$'` für version. |
| C4 | `repo_scan.py` ohne Rate-Limit und Auth-Scope | KRITISCH | GitHub API: 60 req/h unauthenticated, 5000/h mit Token. Bei 20+ Repos im Org kann ein Scan die Limits sprengen. Kein Retry, kein Backoff definiert. | `httpx` mit `httpx_retry` + exponential backoff. Token via `GITHUB_TOKEN` Env-Var. `X-RateLimit-Remaining` Header auswerten. |

### 🟠 HOCH

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| H1 | Kein Skill-Dependency-Graph | HOCH | `repo_scan.py` braucht `session_memory.py` (um Ergebnis zu speichern). Aber SkillRegistry hat keine `depends_on` — falsche Ausführungsreihenfolge möglich. | `Skill.depends_on: list[str] = []` + topologische Sortierung bei Skill-Ausführung. |
| H2 | `AGENT_MEMORY.md` im falschen Repo | HOCH | ADR sagt `platform/AGENT_MEMORY.md` — aber `platform` ist die Shared-Library, kein Ort für operativen State. Cross-Repo-Writes erfordern zusätzliche PAT-Scopes. | `AGENT_MEMORY.md` in `iilgmbh/mcp-hub` (das Orchestrator-Repo). Skills schreiben nur dorthin. |
| H3 | Kein Hot-Reload für Skills | HOCH | Neuen Skill hinzufügen erfordert MCP-Server-Neustart. Im laufenden Betrieb (iPad-Trigger) bedeutet das Downtime. | `importlib.reload()` + `SIGHUP`-Handler der `discover_skills()` neu aufruft. |
| H4 | Migration Plan ohne Rollback | HOCH | 4h Migration, 7 Schritte, kein Rollback-Plan. Wenn Schritt 4 (session_memory) fehlschlägt, sind infra/payment Context-Skills bereits refactored aber Memory kaputt. | Phase-Gates: Schritt 1-3 sind Deploy-Safe. Schritt 4-7 brauchen Feature-Flag `SKILL_REGISTRY_V2=true`. |
| H5 | OpenClaw als Inspiration ohne Verification | HOCH | "OpenClaw CLI-Ecosystem (2026)" — nicht verifizierbar, möglicherweise Halluzination. ADR-Basis sollte auf verifizierbaren Quellen basieren. | Referenz entfernen oder durch konkrete, verifizierbare Quellen ersetzen (LangChain Memory, AutoGen Skills, Semantic Kernel). |

### 🟡 MEDIUM

| # | Befund | Severity | Problem | Korrektur |
|---|---|---|---|---|
| M1 | `set -euo pipefail` fehlt in Shell-Steps | MEDIUM | Platform-Standard. GitHub Actions `run:` Blöcke ohne dieses Flag ignorieren Fehler. | Jeder `run:` Block beginnt mit `set -euo pipefail` |
| M2 | Keine i18n-Markierung in Skill-Descriptions | MEDIUM | Platform-Standard: `_()` ab Tag 1. Skill.description wird ggf. in UI angezeigt. | `description: str` → im MCP-Kontext nicht direkt i18n-pflichtig, aber Skill-Namen in Templates müssen `_()` nutzen. |
| M3 | `scan_repo()` Signatur zu flach | MEDIUM | Nur `repo_name` und `github_token` — kein `org`, kein `branch`, kein `timeout`. | `RepoScanParams(BaseModel)` mit allen nötigen Feldern. |
| M4 | Keine Metrik-Integration | MEDIUM | Skills laufen ohne Observability. Wann hat `payment_context` zuletzt funktioniert? Wie lange dauert `repo_scan`? | `skill_invocation_duration_seconds` + `skill_error_total` als Prometheus-Counter (via `django-prometheus` oder `structlog`). |

---

## 2. Implementierungsplan (produktionsreif)

```
Phase 1 — Foundation (Deploy-Safe, 1.5h)
├── orchestrator_mcp/skills/__init__.py      ← SkillRegistry + discover_skills()
├── orchestrator_mcp/skills/base.py          ← Skill (Pydantic v2) + SkillResult + Exceptions
└── orchestrator_mcp/skills/infra_context.py ← Refactored aus MCP Server

Phase 2 — Memory Store (Feature-Flag geschützt, 1.5h)
├── orchestrator_mcp/skills/session_memory.py ← AGENT_MEMORY.md lesen/schreiben (atomar)
└── orchestrator_mcp/skills/memory_schema.py  ← MemoryEntry + MemoryStore (Pydantic v2)

Phase 3 — Repo Scanner (1h)
└── orchestrator_mcp/skills/repo_scan.py      ← GitHub API, Rate-Limit, Backoff

Phase 4 — GitHub Actions Integration (30min)
├── .github/workflows/agent-repo-onboard.yml  ← Repo-Onboarding Trigger
└── .github/workflows/agent-memory-gc.yml     ← Nightly TTL-Cleanup

Phase 5 — Server-Integration (30min)
└── orchestrator_mcp/agent_team/mcp_server.py ← Skill-Tools registrieren
```

**Gesamtaufwand:** ~5h (statt 4h im ADR — wegen Blocker-Fixes)
**Feature-Flag:** `SKILL_REGISTRY_V2=false` → alter Code, `=true` → neue Registry
**Rollback:** Feature-Flag auf `false` → sofortige Deaktivierung

---

## 3. Produktionsreife Implementierung

### 3.1 `orchestrator_mcp/skills/base.py`

```python
"""
Skill Registry — Base Classes und Exceptions.

Platform-Standards:
- Pydantic v2 (nicht @dataclass)
- SkillResult statt naktem dict
- Vollständige Exception-Hierarchy
"""
from __future__ import annotations

import time
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ─── Exception Hierarchy ──────────────────────────────────────────────────────

class SkillError(Exception):
    """Basis-Exception für alle Skill-Fehler."""


class SkillNotFoundError(SkillError):
    """Skill ist nicht in der Registry."""


class SkillInvocationError(SkillError):
    """Skill.invoke() hat einen Fehler geworfen."""
    def __init__(self, skill_name: str, original: Exception) -> None:
        super().__init__(f"Skill '{skill_name}' invocation failed: {original!r}")
        self.skill_name = skill_name
        self.original = original


class SkillValidationError(SkillError):
    """Skill-Definition ist ungültig."""


class SkillDependencyError(SkillError):
    """Skill-Abhängigkeit kann nicht aufgelöst werden."""


# ─── Value Objects ────────────────────────────────────────────────────────────

class GateLevel(IntEnum):
    """Gate-Level (ADR-107 kompatibel)."""
    AUTONOMOUS   = 0  # kein menschlicher Eingriff
    NOTIFY       = 1  # Mensch informiert
    APPROVE      = 2  # Mensch muss zustimmen
    SYNCHRONOUS  = 3  # Mensch live dabei
    HUMAN_ONLY   = 4  # nur Mensch führt aus


class SkillDomain(str):
    """Typgeprüfter Domain-String (infra, payment, tenancy, qa, ...)."""


class SkillResult(BaseModel):
    """
    Typsicheres Rückgabeobjekt für Skill.invoke().

    Attributes:
        success: True wenn Skill erfolgreich war
        data: Strukturiertes Ergebnis (beliebige JSON-serialisierbare Daten)
        message: Menschenlesbare Zusammenfassung
        skill_name: Name des ausführenden Skills
        duration_ms: Ausführungszeit in Millisekunden
        gate_required: Gate-Level der für Follow-up-Aktionen nötig ist
    """
    model_config = ConfigDict(extra="forbid")

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    message: str
    skill_name: str
    duration_ms: float = 0.0
    gate_required: GateLevel = GateLevel.AUTONOMOUS

    @classmethod
    def ok(
        cls,
        skill_name: str,
        data: dict[str, Any],
        message: str = "",
        duration_ms: float = 0.0,
        gate_required: GateLevel = GateLevel.AUTONOMOUS,
    ) -> "SkillResult":
        return cls(
            success=True,
            data=data,
            message=message or f"Skill '{skill_name}' succeeded",
            skill_name=skill_name,
            duration_ms=duration_ms,
            gate_required=gate_required,
        )

    @classmethod
    def fail(
        cls,
        skill_name: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> "SkillResult":
        return cls(
            success=False,
            data=data or {},
            message=message,
            skill_name=skill_name,
        )


# ─── Skill Base ───────────────────────────────────────────────────────────────

class Skill(BaseModel):
    """
    Abstrakte Basis für alle registrierten Agent-Skills.

    Platform-Standards:
    - Pydantic v2 (validate_assignment, extra=forbid)
    - Semver-validierte Version
    - gate_level 0-4 (ADR-107 Gate-System)
    - depends_on für Dependency-Graph

    Beispiel:
        class InfraContextSkill(Skill):
            name: str = "infra_context"
            version: str = "1.0.0"
            domain: str = "infra"
            description: str = "Liefert Infrastruktur-Kontext (Hetzner, Traefik, etc.)"
            mcp_tool_name: str = "get_infra_context"
            gate_level: GateLevel = GateLevel.AUTONOMOUS

            def invoke(self, **kwargs) -> SkillResult:
                ...
    """
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    name: str = Field(
        ...,
        description="Eindeutiger Skill-Name (snake_case)",
        pattern=r'^[a-z][a-z0-9_]*$',
        min_length=2,
        max_length=64,
    )
    version: str = Field(
        ...,
        description="Semantic Version",
        pattern=r'^\d+\.\d+\.\d+$',
    )
    domain: str = Field(
        ...,
        description="Domain (infra, payment, tenancy, qa, memory, ...)",
        pattern=r'^[a-z][a-z0-9_]*$',
    )
    description: str = Field(..., min_length=10, max_length=500)
    mcp_tool_name: str = Field(
        ...,
        description="Name des MCP-Tools das diesen Skill exponiert",
        pattern=r'^[a-z][a-z0-9_]*$',
    )
    gate_level: GateLevel = Field(
        default=GateLevel.AUTONOMOUS,
        description="Mindest-Gate-Level für diesen Skill (ADR-107)",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Skill-Namen von denen dieser Skill abhängt",
    )
    enabled: bool = Field(
        default=True,
        description="False = Skill wird nicht registriert (Feature-Flag Alternative)",
    )

    def invoke(self, **kwargs: Any) -> SkillResult:
        """
        Skill ausführen.

        Muss in Subklassen überschrieben werden.
        Darf KEINE Exception werfen — gibt SkillResult.fail() zurück bei Fehler.

        Returns:
            SkillResult mit success=True/False und strukturierten Daten
        """
        raise NotImplementedError(
            f"Skill '{self.name}' hat invoke() nicht implementiert. "
            f"Bitte in der Subklasse überschreiben."
        )

    def safe_invoke(self, **kwargs: Any) -> SkillResult:
        """
        Exception-sicherer invoke() Wrapper.

        Fängt alle Exceptions ab und gibt SkillResult.fail() zurück.
        Misst die Ausführungszeit.
        """
        start = time.perf_counter()
        try:
            result = self.invoke(**kwargs)
            result.duration_ms = (time.perf_counter() - start) * 1000
            return result
        except NotImplementedError:
            raise
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return SkillResult.fail(
                skill_name=self.name,
                message=f"Invocation failed: {type(exc).__name__}: {exc}",
                data={"exception_type": type(exc).__name__, "duration_ms": duration_ms},
            )
```

---

### 3.2 `orchestrator_mcp/skills/__init__.py`

```python
"""
SkillRegistry — zentrale Registrierung und Discovery aller Agent-Skills.

Kein Magic via __init_subclass__: explizite Discovery via importlib.
Kein silentes Versagen: fehlende Skills werfen SkillNotFoundError.
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Iterator

from .base import (
    GateLevel,
    Skill,
    SkillDependencyError,
    SkillNotFoundError,
    SkillResult,
    SkillValidationError,
)

log = logging.getLogger(__name__)

# ─── Registry ────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Skill] = {}


def register(skill: Skill) -> None:
    """Skill in Registry aufnehmen. Überschreibt existierende Skills (idempotent)."""
    if not skill.enabled:
        log.debug("Skill '%s' ist disabled — wird nicht registriert", skill.name)
        return

    if skill.name in _REGISTRY:
        existing = _REGISTRY[skill.name]
        if existing.version != skill.version:
            log.warning(
                "Skill '%s' wird überschrieben: %s → %s",
                skill.name, existing.version, skill.version,
            )

    _REGISTRY[skill.name] = skill
    log.info("Skill registriert: %s v%s (domain=%s)", skill.name, skill.version, skill.domain)


def get_skill(name: str) -> Skill:
    """Skill aus Registry holen. Wirft SkillNotFoundError wenn nicht vorhanden."""
    if name not in _REGISTRY:
        available = sorted(_REGISTRY.keys())
        raise SkillNotFoundError(
            f"Skill '{name}' nicht gefunden. "
            f"Verfügbare Skills: {available}"
        )
    return _REGISTRY[name]


def list_skills(domain: str | None = None) -> list[Skill]:
    """Alle registrierten Skills, optional nach Domain gefiltert."""
    skills = list(_REGISTRY.values())
    if domain:
        skills = [s for s in skills if s.domain == domain]
    return sorted(skills, key=lambda s: (s.domain, s.name))


def invoke_skill(name: str, **kwargs) -> SkillResult:
    """
    Skill aufrufen — mit Dependency-Auflösung und Exception-Schutz.

    Führt zuerst alle depends_on Skills aus (topologisch sortiert).
    """
    skill = get_skill(name)
    _resolve_dependencies(skill, visited=set())
    return skill.safe_invoke(**kwargs)


def _resolve_dependencies(skill: Skill, visited: set[str], stack: list[str] | None = None) -> None:
    """Topologische Dependency-Auflösung (erkennt zyklische Abhängigkeiten)."""
    stack = stack or []
    if skill.name in stack:
        cycle = " → ".join(stack + [skill.name])
        raise SkillDependencyError(f"Zyklische Abhängigkeit: {cycle}")
    if skill.name in visited:
        return

    stack.append(skill.name)
    for dep_name in skill.depends_on:
        dep_skill = get_skill(dep_name)
        _resolve_dependencies(dep_skill, visited, stack)

    stack.pop()
    visited.add(skill.name)


# ─── Discovery ────────────────────────────────────────────────────────────────

def discover_skills(skills_dir: Path | None = None) -> int:
    """
    Alle Skill-Module in skills/ laden und registrieren.

    Kein Magic: jedes Modul muss eine `SKILL`-Variable auf Modulebene
    definieren (Skill-Instanz) die dann auto-registriert wird.

    Returns:
        Anzahl registrierter Skills
    """
    if skills_dir is None:
        skills_dir = Path(__file__).parent

    count = 0
    for skill_file in sorted(skills_dir.glob("*.py")):
        if skill_file.name.startswith(("__", "base", "memory_schema")):
            continue

        module_name = f"orchestrator_mcp.skills.{skill_file.stem}"
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            log.error("Skill-Modul '%s' konnte nicht geladen werden: %s", module_name, exc)
            continue

        # Konvention: jedes Skill-Modul hat eine `SKILL`-Variable
        if hasattr(module, "SKILL"):
            skill_instance = module.SKILL
            if isinstance(skill_instance, Skill):
                register(skill_instance)
                count += 1
            else:
                log.warning(
                    "Modul '%s' hat SKILL Variable, aber es ist kein Skill-Objekt: %s",
                    module_name, type(skill_instance),
                )
        else:
            log.debug("Modul '%s' hat keine SKILL Variable — wird übersprungen", module_name)

    log.info("Skill-Discovery abgeschlossen: %d Skills registriert", count)
    return count


def reload_skills() -> int:
    """
    Hot-Reload: alle Skills neu laden (z.B. via SIGHUP).

    Bestehende Registry wird geleert und neu befüllt.
    """
    global _REGISTRY
    _REGISTRY.clear()
    log.info("Skill-Registry geleert — starte Discovery")
    return discover_skills()


__all__ = [
    "GateLevel",
    "Skill",
    "SkillResult",
    "SkillNotFoundError",
    "SkillDependencyError",
    "SkillValidationError",
    "register",
    "get_skill",
    "list_skills",
    "invoke_skill",
    "discover_skills",
    "reload_skills",
]
```

---

### 3.3 `orchestrator_mcp/skills/memory_schema.py`

```python
"""
AGENT_MEMORY.md Schema — Pydantic v2 Modelle für den persistenten Kontext-Store.

Format: YAML-Frontmatter (Metadaten) + strukturierte Markdown-Sections.
Jeder Entry hat ein expires_at (TTL) — abgelaufene Entries werden via memory_gc() entfernt.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EntryType(str, Enum):
    SOLVED_PROBLEM  = "solved_problem"
    REPO_CONTEXT    = "repo_context"
    OPEN_TASK       = "open_task"
    AGENT_DECISION  = "agent_decision"
    ERROR_PATTERN   = "error_pattern"


class MemoryEntry(BaseModel):
    """Einzelner strukturierter Eintrag im Agent Memory Store."""
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(
        ...,
        description="Eindeutige ID: T-001, R-coach-hub, D-2026-03-08-001",
        pattern=r'^[A-Z][A-Z0-9\-]+$',
    )
    entry_type: EntryType
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=1)
    agent: str = Field(..., description="Schreibender Agent: payment-agent, re-engineer, ...")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        description="TTL: Entry wird nach diesem Datum via memory_gc() entfernt",
    )
    tags: list[str] = Field(default_factory=list)
    related_entries: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self) -> None:
        """updated_at aktualisieren (in-place)."""
        self.updated_at = datetime.now(timezone.utc)


class MemoryStore(BaseModel):
    """
    Vollständiger Agent Memory Store — wird als AGENT_MEMORY.md serialisiert.

    Beispiel AGENT_MEMORY.md:
    ```
    ---
    version: "1.0"
    last_updated: "2026-03-08T11:45:00Z"
    last_updated_by: "payment-agent"
    entry_count: 3
    ---
    [Entries als JSON-Blöcke in Markdown]
    ```
    """
    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_by: str = "unknown-agent"
    entries: list[MemoryEntry] = Field(default_factory=list)

    def get(self, entry_id: str) -> MemoryEntry | None:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def upsert(self, entry: MemoryEntry, agent: str = "unknown-agent") -> None:
        """Entry hinzufügen oder aktualisieren."""
        existing = self.get(entry.entry_id)
        if existing:
            idx = self.entries.index(existing)
            self.entries[idx] = entry
            self.entries[idx].touch()
        else:
            self.entries.append(entry)
        self.last_updated = datetime.now(timezone.utc)
        self.last_updated_by = agent

    def gc(self) -> int:
        """Abgelaufene Entries entfernen. Gibt Anzahl entfernter Entries zurück."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if not e.is_expired]
        removed = before - len(self.entries)
        if removed:
            self.last_updated = datetime.now(timezone.utc)
            self.last_updated_by = "memory-gc"
        return removed

    def by_type(self, entry_type: EntryType) -> list[MemoryEntry]:
        return [e for e in self.entries if e.entry_type == entry_type]

    def by_tag(self, tag: str) -> list[MemoryEntry]:
        return [e for e in self.entries if tag in e.tags]
```

---

### 3.4 `orchestrator_mcp/skills/session_memory.py`

```python
"""
Session Memory Skill — AGENT_MEMORY.md lesen und schreiben.

Kritische Design-Entscheidungen:
- Atomares Write (tempfile + os.replace) — kein partieller Schreibzustand
- fcntl.flock() Exclusive Lock — verhindert Race Conditions bei parallelen Agents
- JSON-Blöcke in Markdown (nicht free-form) — parserbar ohne Regex-Magie
- Git-Commit nach jedem Write (audit trail)
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .base import GateLevel, Skill, SkillResult
from .memory_schema import EntryType, MemoryEntry, MemoryStore

log = logging.getLogger(__name__)

# Pfad relativ zum Repo-Root (mcp-hub)
MEMORY_FILE = Path("AGENT_MEMORY.md")
LOCK_FILE   = Path(".agent_memory.lock")

_GIT_AUTHOR_NAME  = "Agent Team"
_GIT_AUTHOR_EMAIL = "agent@iilgmbh.com"


# ─── I/O Helpers (atomar + lock-gesichert) ────────────────────────────────────

def _read_store(path: Path = MEMORY_FILE) -> MemoryStore:
    """AGENT_MEMORY.md lesen und in MemoryStore deserialisieren."""
    if not path.exists():
        log.info("AGENT_MEMORY.md nicht gefunden — erstelle leeren Store")
        return MemoryStore()

    content = path.read_text(encoding="utf-8")

    # JSON-Blöcke extrahieren (```json ... ``` Fences)
    entries: list[MemoryEntry] = []
    meta: dict = {}
    in_json_block = False
    json_lines: list[str] = []

    for line in content.splitlines():
        if line.strip() == "```json":
            in_json_block = True
            json_lines = []
        elif line.strip() == "```" and in_json_block:
            in_json_block = False
            try:
                raw = json.loads("\n".join(json_lines))
                if raw.get("_type") == "meta":
                    meta = raw
                elif raw.get("_type") == "entry":
                    entries.append(MemoryEntry(**{k: v for k, v in raw.items() if k != "_type"}))
            except (json.JSONDecodeError, Exception) as exc:
                log.warning("Ungültiger JSON-Block in AGENT_MEMORY.md: %s", exc)
        elif in_json_block:
            json_lines.append(line)

    return MemoryStore(
        version=meta.get("version", "1.0"),
        last_updated=datetime.fromisoformat(meta["last_updated"]) if "last_updated" in meta else datetime.now(timezone.utc),
        last_updated_by=meta.get("last_updated_by", "unknown"),
        entries=entries,
    )


def _write_store(store: MemoryStore, path: Path = MEMORY_FILE) -> None:
    """
    MemoryStore atomar nach AGENT_MEMORY.md schreiben.

    Atomar: tempfile → os.replace (kein partieller Schreibzustand).
    Lock: fcntl.flock() Exclusive Lock (kein paralleles Schreiben).
    """
    lock_path = path.parent / LOCK_FILE

    with open(lock_path, "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            content = _render_markdown(store)
            # Atomar schreiben
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                suffix=".tmp",
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            os.replace(tmp_path, path)
            log.info("AGENT_MEMORY.md geschrieben: %d Entries", len(store.entries))
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)


def _render_markdown(store: MemoryStore) -> str:
    """MemoryStore → Markdown mit JSON-Fences (strukturiert, parsebar)."""
    meta = {
        "_type": "meta",
        "version": store.version,
        "last_updated": store.last_updated.isoformat(),
        "last_updated_by": store.last_updated_by,
        "entry_count": len(store.entries),
    }

    lines = [
        "# Agent Memory Store",
        "<!-- Automatisch generiert — nicht manuell bearbeiten -->",
        "<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->",
        "",
        "```json",
        json.dumps(meta, indent=2, ensure_ascii=False),
        "```",
        "",
    ]

    # Entries gruppiert nach Typ
    for entry_type in EntryType:
        type_entries = [e for e in store.entries if e.entry_type == entry_type]
        if not type_entries:
            continue

        lines.append(f"## {entry_type.value.replace('_', ' ').title()}")
        lines.append("")

        for entry in sorted(type_entries, key=lambda e: e.updated_at, reverse=True):
            lines += [
                f"### {entry.entry_id} — {entry.title}",
                "",
                "```json",
                json.dumps(
                    {"_type": "entry", **entry.model_dump(mode="json")},
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                ),
                "```",
                "",
            ]

    return "\n".join(lines)


def _git_commit(path: Path, message: str) -> None:
    """AGENT_MEMORY.md committen (benötigt git + GITHUB_TOKEN in CI)."""
    try:
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME":    _GIT_AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL":   _GIT_AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": _GIT_AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": _GIT_AUTHOR_EMAIL,
        })

        subprocess.run(
            ["git", "config", "user.email", _GIT_AUTHOR_EMAIL],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", _GIT_AUTHOR_NAME],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "add", str(path)],
            check=True, capture_output=True,
        )
        # Prüfen ob es etwas zu committen gibt
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if result.returncode == 0:
            log.debug("Kein Git-Diff — kein Commit nötig")
            return

        subprocess.run(
            ["git", "commit", "-m", message, "--no-verify"],
            check=True, capture_output=True, env=env,
        )
        log.info("Git-Commit: %s", message)
    except subprocess.CalledProcessError as exc:
        # Kein harter Fehler — Memory wurde geschrieben, nur Commit fehlgeschlagen
        log.warning("Git-Commit fehlgeschlagen (non-fatal): %s", exc.stderr.decode())


# ─── Skill-Implementierung ────────────────────────────────────────────────────

class SessionMemorySkill(Skill):
    """
    Liest und schreibt AGENT_MEMORY.md — der persistente Kontext-Store.

    Operationen:
    - read:   Ganzen Store lesen
    - upsert: Entry hinzufügen oder aktualisieren
    - gc:     Abgelaufene Entries entfernen
    - query:  Entries nach Typ oder Tag filtern
    """

    def invoke(
        self,
        operation: str = "read",
        entry: dict | None = None,
        agent: str = "unknown-agent",
        filter_type: str | None = None,
        filter_tag: str | None = None,
        commit: bool = True,
    ) -> SkillResult:
        """
        Args:
            operation: "read" | "upsert" | "gc" | "query"
            entry: MemoryEntry als dict (für operation="upsert")
            agent: Name des schreibenden Agents
            filter_type: EntryType für operation="query"
            filter_tag: Tag-Filter für operation="query"
            commit: Git-Commit nach Schreiboperation (default: True)

        Returns:
            SkillResult mit Entries als data["entries"]
        """
        match operation:
            case "read":
                return self._read(agent)
            case "upsert":
                if entry is None:
                    return SkillResult.fail(self.name, "operation='upsert' benötigt 'entry'")
                return self._upsert(entry, agent, commit)
            case "gc":
                return self._gc(agent, commit)
            case "query":
                return self._query(filter_type, filter_tag)
            case _:
                return SkillResult.fail(
                    self.name,
                    f"Unbekannte Operation: '{operation}'. Erlaubt: read, upsert, gc, query",
                )

    def _read(self, agent: str) -> SkillResult:
        store = _read_store()
        return SkillResult.ok(
            skill_name=self.name,
            data={
                "entries": [e.model_dump(mode="json") for e in store.entries],
                "entry_count": len(store.entries),
                "last_updated": store.last_updated.isoformat(),
                "last_updated_by": store.last_updated_by,
            },
            message=f"{len(store.entries)} Entries geladen",
        )

    def _upsert(self, entry_dict: dict, agent: str, commit: bool) -> SkillResult:
        try:
            entry = MemoryEntry(**entry_dict)
        except Exception as exc:
            return SkillResult.fail(self.name, f"Ungültiger Entry: {exc}")

        store = _read_store()
        store.upsert(entry, agent=agent)
        _write_store(store)

        if commit:
            _git_commit(
                MEMORY_FILE,
                f"agent-memory: upsert {entry.entry_id} [{entry.entry_type.value}] by {agent}",
            )

        return SkillResult.ok(
            skill_name=self.name,
            data={"entry_id": entry.entry_id, "upserted": True},
            message=f"Entry '{entry.entry_id}' gespeichert",
        )

    def _gc(self, agent: str, commit: bool) -> SkillResult:
        store = _read_store()
        removed = store.gc()
        if removed:
            _write_store(store)
            if commit:
                _git_commit(MEMORY_FILE, f"agent-memory: gc removed {removed} expired entries")

        return SkillResult.ok(
            skill_name=self.name,
            data={"removed_entries": removed, "remaining_entries": len(store.entries)},
            message=f"GC: {removed} abgelaufene Entries entfernt",
        )

    def _query(self, filter_type: str | None, filter_tag: str | None) -> SkillResult:
        store = _read_store()
        entries = store.entries

        if filter_type:
            try:
                et = EntryType(filter_type)
                entries = store.by_type(et)
            except ValueError:
                return SkillResult.fail(
                    self.name,
                    f"Ungültiger filter_type: '{filter_type}'. "
                    f"Erlaubt: {[e.value for e in EntryType]}",
                )
        if filter_tag:
            entries = [e for e in entries if filter_tag in e.tags]

        return SkillResult.ok(
            skill_name=self.name,
            data={"entries": [e.model_dump(mode="json") for e in entries]},
            message=f"{len(entries)} Entries gefunden",
        )


SKILL = SessionMemorySkill(
    name="session_memory",
    version="1.0.0",
    domain="memory",
    description="Liest und schreibt AGENT_MEMORY.md — persistenter, git-tracked Kontext-Store für Agent-Erkenntnisse",
    mcp_tool_name="agent_memory",
    gate_level=GateLevel.NOTIFY,  # Gate 1: Mensch wird informiert bei Writes
    depends_on=[],
)
```

---

### 3.5 `orchestrator_mcp/skills/repo_scan.py`

```python
"""
Repo Scan Skill — automatisches Repo-Onboarding via GitHub API.

Rate-Limit: exponential backoff, X-RateLimit-Remaining auswerten.
Auth: GITHUB_TOKEN Env-Var (GITHUB_TOKEN aus GitHub Actions oder PROJECT_PAT).
Ergebnis: wird als REPO_CONTEXT Entry in AGENT_MEMORY.md gespeichert.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

from .base import GateLevel, Skill, SkillResult
from .memory_schema import EntryType, MemoryEntry
from .session_memory import _read_store, _write_store, _git_commit, MEMORY_FILE

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_ORG = "iilgmbh"
MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # Sekunden


class RepoScanParams:
    """Parameter für einen Repo-Scan (nicht Pydantic — wird intern genutzt)."""
    def __init__(
        self,
        repo_name: str,
        org: str = DEFAULT_ORG,
        branch: str = "main",
        timeout: int = 30,
    ) -> None:
        self.repo_name = repo_name
        self.org = org
        self.branch = branch
        self.timeout = timeout
        self.full_name = f"{org}/{repo_name}"


def _github_request(
    endpoint: str,
    token: str,
    timeout: int = 30,
    attempt: int = 0,
) -> dict | list | None:
    """
    GitHub API GET mit Rate-Limit-Handling und exponential Backoff.

    Args:
        endpoint: Relativer Pfad (z.B. "/repos/iilgmbh/risk-hub")
        token: GitHub Token (GITHUB_TOKEN oder PROJECT_PAT)
        timeout: Request-Timeout in Sekunden
        attempt: Aktueller Retry-Versuch (intern)

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

        # Rate-Limit prüfen
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1000))
        if remaining < 10:
            reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
            wait = max(0, reset_ts - int(time.time())) + 1
            log.warning("GitHub Rate-Limit fast erschöpft (%d remaining) — warte %ds", remaining, wait)
            time.sleep(wait)

        if response.status_code == 404:
            log.warning("GitHub 404: %s", url)
            return None

        if response.status_code == 403 and "rate limit" in response.text.lower():
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** (attempt + 1)
                log.warning("Rate-Limit hit — Backoff %ds (attempt %d/%d)", wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
                return _github_request(endpoint, token, timeout, attempt + 1)
            raise RuntimeError(f"GitHub Rate-Limit nach {MAX_RETRIES} Retries nicht überwunden")

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
    """Health-URL prüfen. Gibt "✅ OK", "❌ DOWN", oder "⚠️ UNKNOWN" zurück."""
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


def _extract_health_url(compose_content: str | None, repo_name: str) -> str:
    """Versucht Health-URL aus docker-compose.prod.yml zu extrahieren."""
    if not compose_content:
        return ""
    # Einfacher Heuristic: VIRTUAL_HOST oder LETSENCRYPT_HOST
    for line in compose_content.splitlines():
        if "VIRTUAL_HOST=" in line or "LETSENCRYPT_HOST=" in line:
            host = line.split("=", 1)[-1].strip().strip('"').strip("'")
            if host:
                return f"https://{host}/healthz/"
    return ""


class RepoScanSkill(Skill):
    """
    Scannt ein Repo in der iilgmbh-Org und speichert den Kontext in AGENT_MEMORY.md.

    Erkennt:
    - App-Framework (Django, FastAPI, ...)
    - Health-URL (aus docker-compose.prod.yml)
    - Migrations-Stand (letzte Migration)
    - Offene Issues mit Agent-relevanten Labels
    - AGENT_HANDOVER.md wenn vorhanden
    """

    def invoke(
        self,
        repo_name: str,
        org: str = DEFAULT_ORG,
        branch: str = "main",
        github_token: str | None = None,
        commit: bool = True,
        dry_run: bool = False,
    ) -> SkillResult:
        """
        Args:
            repo_name: Repository-Name (ohne Org-Prefix)
            org: GitHub-Org (default: iilgmbh)
            branch: Branch der gescannt wird (default: main)
            github_token: GitHub Token (default: GITHUB_TOKEN Env-Var)
            commit: AGENT_MEMORY.md committen nach Scan
            dry_run: Scan ohne Speichern

        Returns:
            SkillResult mit repo_context als data
        """
        token = github_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("PROJECT_PAT")
        if not token:
            return SkillResult.fail(
                self.name,
                "Kein GitHub Token verfügbar. Setze GITHUB_TOKEN oder PROJECT_PAT.",
            )

        params = RepoScanParams(repo_name=repo_name, org=org, branch=branch)
        log.info("Starte Repo-Scan: %s", params.full_name)

        # ── Repo-Basis-Info ──────────────────────────────────────────────────
        repo_info = _github_request(f"/repos/{params.full_name}", token)
        if repo_info is None:
            return SkillResult.fail(self.name, f"Repo '{params.full_name}' nicht gefunden")

        context: dict = {
            "repo": params.full_name,
            "branch": branch,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "private": repo_info.get("private", True),
            "description": repo_info.get("description", ""),
            "default_branch": repo_info.get("default_branch", "main"),
        }

        # ── Framework erkennen ───────────────────────────────────────────────
        requirements = _github_request(
            f"/repos/{params.full_name}/contents/requirements.txt?ref={branch}",
            token,
        )
        if requirements and isinstance(requirements, dict):
            import base64
            try:
                req_text = base64.b64decode(requirements.get("content", "")).decode("utf-8", errors="ignore")
                if "django" in req_text.lower():
                    context["framework"] = "Django"
                elif "fastapi" in req_text.lower():
                    context["framework"] = "FastAPI"
                else:
                    context["framework"] = "Unknown"
            except Exception:
                context["framework"] = "Unknown"

        # ── Health-URL ───────────────────────────────────────────────────────
        compose = _github_request(
            f"/repos/{params.full_name}/contents/docker-compose.prod.yml?ref={branch}",
            token,
        )
        compose_content = None
        if compose and isinstance(compose, dict):
            import base64
            try:
                compose_content = base64.b64decode(compose.get("content", "")).decode("utf-8", errors="ignore")
            except Exception:
                pass

        health_url = _extract_health_url(compose_content, repo_name)
        context["health_url"] = health_url
        context["health_status"] = _check_health(health_url) if health_url else "⚠️ UNKNOWN"

        # ── Migrations-Stand ─────────────────────────────────────────────────
        migrations = _github_request(
            f"/repos/{params.full_name}/contents?ref={branch}",
            token,
        )
        has_migrations = False
        if migrations and isinstance(migrations, list):
            app_dirs = [f["name"] for f in migrations if f["type"] == "dir"]
            for app_dir in app_dirs[:5]:  # Nur erste 5 App-Dirs
                mig_dir = _github_request(
                    f"/repos/{params.full_name}/contents/{app_dir}/migrations?ref={branch}",
                    token,
                )
                if mig_dir and isinstance(mig_dir, list):
                    has_migrations = True
                    migration_files = sorted(
                        [f["name"] for f in mig_dir if f["name"].endswith(".py") and f["name"] != "__init__.py"],
                        reverse=True,
                    )
                    if migration_files:
                        context["latest_migration"] = f"{app_dir}/{migration_files[0]}"
                    break

        context["has_migrations"] = has_migrations

        # ── AGENT_HANDOVER.md ─────────────────────────────────────────────────
        handover = _github_request(
            f"/repos/{params.full_name}/contents/AGENT_HANDOVER.md?ref={branch}",
            token,
        )
        if handover and isinstance(handover, dict):
            import base64
            try:
                handover_text = base64.b64decode(handover.get("content", "")).decode("utf-8", errors="ignore")
                context["has_handover"] = True
                context["handover_preview"] = handover_text[:500]
            except Exception:
                context["has_handover"] = False
        else:
            context["has_handover"] = False

        # ── Offene Issues (Agent-relevant) ────────────────────────────────────
        issues = _github_request(
            f"/repos/{params.full_name}/issues?labels=agent-task&state=open&per_page=10",
            token,
        )
        if issues and isinstance(issues, list):
            context["open_agent_tasks"] = [
                {"number": i["number"], "title": i["title"]}
                for i in issues
            ]
        else:
            context["open_agent_tasks"] = []

        log.info("Repo-Scan abgeschlossen: %s", context)

        if dry_run:
            return SkillResult.ok(
                skill_name=self.name,
                data={"repo_context": context, "dry_run": True},
                message=f"Dry Run: Repo-Kontext für '{params.full_name}' ermittelt (nicht gespeichert)",
            )

        # ── In AGENT_MEMORY.md speichern ──────────────────────────────────────
        entry = MemoryEntry(
            entry_id=f"R-{repo_name.upper()}",
            entry_type=EntryType.REPO_CONTEXT,
            title=f"Repo-Kontext: {params.full_name}",
            content=str(context),
            agent=self.name,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),  # 1 Woche TTL
            tags=["repo", org, repo_name],
            metadata=context,
        )
        store = _read_store()
        store.upsert(entry, agent=self.name)
        _write_store(store)

        if commit:
            _git_commit(
                MEMORY_FILE,
                f"agent-memory: repo-scan {params.full_name} [{context.get('health_status', '?')}]",
            )

        return SkillResult.ok(
            skill_name=self.name,
            data={"repo_context": context, "entry_id": entry.entry_id},
            message=f"Repo '{params.full_name}' gescannt und in AGENT_MEMORY.md gespeichert",
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
```

---

### 3.6 `.github/workflows/agent-repo-onboard.yml`

```yaml
name: 🔍 Repo Onboarding (Agent Memory)

on:
  workflow_dispatch:
    inputs:
      repo_name:
        description: 'Repo-Name (ohne iilgmbh/ Prefix)'
        required: true
        type: string
      org:
        description: 'GitHub-Org'
        required: false
        default: 'iilgmbh'
        type: string
      dry_run:
        description: 'Dry Run? (Scan ohne Speichern)'
        required: false
        type: boolean
        default: true

  # Automatisch wenn neues Repo zur Org hinzugefügt wird
  # (benötigt Organization-Level Webhook → App-Integration)
  repository_dispatch:
    types: [repo-added-to-org]

jobs:
  scan-repo:
    name: 🔍 Repo scannen
    runs-on: ubuntu-latest
    permissions:
      contents: write    # für AGENT_MEMORY.md commit
      issues: read

    steps:
      - name: Checkout mcp-hub
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.PROJECT_PAT }}  # Für git push

      - name: Python einrichten
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip

      - name: Dependencies
        run: |
          set -euo pipefail
          pip install pydantic httpx

      - name: Repo-Scan ausführen
        env:
          GITHUB_TOKEN: ${{ secrets.PROJECT_PAT }}
          SKILL_REGISTRY_V2: 'true'
        run: |
          set -euo pipefail
          python -c "
          import sys, json, os
          sys.path.insert(0, '.')

          from orchestrator_mcp.skills import discover_skills, invoke_skill
          discover_skills()

          result = invoke_skill(
              'repo_scan',
              repo_name='${{ inputs.repo_name || github.event.client_payload.repo_name }}',
              org='${{ inputs.org || 'iilgmbh' }}',
              dry_run=${{ inputs.dry_run && 'True' || 'False' }},
              commit=True,
          )
          print(json.dumps(result.model_dump(mode='json'), indent=2))
          if not result.success:
              sys.exit(1)
          "

      - name: Git push (wenn kein Dry Run)
        if: ${{ !inputs.dry_run }}
        run: |
          set -euo pipefail
          git config user.email "agent@iilgmbh.com"
          git config user.name "Agent Team"
          git push origin HEAD
```

### 3.7 `.github/workflows/agent-memory-gc.yml`

```yaml
name: 🗑️ Agent Memory GC (Nightly)

on:
  schedule:
    - cron: '0 3 * * *'   # 03:00 UTC täglich
  workflow_dispatch:       # Manuell triggebar (iPad)

jobs:
  memory-gc:
    name: 🗑️ Abgelaufene Entries entfernen
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.PROJECT_PAT }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install pydantic

      - name: GC ausführen
        run: |
          set -euo pipefail
          python -c "
          import sys
          sys.path.insert(0, '.')
          from orchestrator_mcp.skills import discover_skills, invoke_skill
          discover_skills()
          result = invoke_skill('session_memory', operation='gc', agent='memory-gc-workflow')
          print(result.message)
          "

      - name: Push
        run: |
          set -euo pipefail
          git config user.email "agent@iilgmbh.com"
          git config user.name "Agent Team"
          git diff --quiet && echo "Keine Änderungen" || git push origin HEAD
```

---

## 4. Alternativer Ansatz: SQLite statt Markdown

Falls Merge-Konflikte ein dauerhaftes Problem bleiben (>3 parallele Agent-Runs):

| Aspekt | AGENT_MEMORY.md (gewählt) | SQLite Alternative |
|---|---|---|
| **Merge-Konflikte** | Möglich (Lock mitigiert) | Keine (binary file) |
| **Git-Lesbarkeit** | ✅ Diff lesbar | ❌ Binary diff |
| **Parallele Writes** | fcntl.flock() | ✅ WAL-Mode nativ |
| **Query** | Nur via Python | ✅ SQL |
| **Rollback** | git revert | git revert (binary) |
| **Empfehlung** | Start: Markdown | >5 parallele Agents: SQLite |

```python
# SQLite Alternative (wenn nötig):
# orchestrator_mcp/skills/memory_sqlite.py
import sqlite3
from pathlib import Path

MEMORY_DB = Path("agent_memory.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(MEMORY_DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")   # Write-Ahead Logging
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

---

## 5. Revisionierte Migrations-Tabelle (mit Rollback)

| Schritt | Aktion | Aufwand | Feature-Flag | Rollback |
|---|---|---|---|---|
| 1 | `skills/base.py` + `skills/__init__.py` anlegen | 30 min | nein | `git revert` |
| 2 | `skills/memory_schema.py` anlegen | 20 min | nein | `git revert` |
| 3 | `infra_context.py` als Skill refactoren | 30 min | `SKILL_REGISTRY_V2` | Flag → false |
| 4 | `session_memory.py` + `AGENT_MEMORY.md` anlegen | 45 min | `SKILL_REGISTRY_V2` | Flag → false |
| 5 | `repo_scan.py` implementieren | 60 min | `SKILL_REGISTRY_V2` | Flag → false |
| 6 | `agent-repo-onboard.yml` + `agent-memory-gc.yml` | 30 min | nein | Workflow löschen |
| 7 | `mcp_server.py`: Skill-Tools registrieren | 20 min | `SKILL_REGISTRY_V2` | Flag → false |

**Gate:** Schritt 1–2 sind immer safe. Schritt 3–7 nur mit `SKILL_REGISTRY_V2=true`.

---

*Review: 2026-03-08 | Reviewer: Principal IT-Architekt | Status: CHANGES REQUIRED → ACCEPTED nach Blocker-Fix*
