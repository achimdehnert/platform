"""
Skill Registry — Base Classes und Exceptions.

Platform-Standards:
- Pydantic v2 (nicht @dataclass)
- SkillResult statt naktem dict
- Vollständige Exception-Hierarchy
- gate_level 0-4 (ADR-107 kompatibel)
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
    AUTONOMOUS  = 0  # kein menschlicher Eingriff
    NOTIFY      = 1  # Mensch informiert
    APPROVE     = 2  # Mensch muss zustimmen
    SYNCHRONOUS = 3  # Mensch live dabei
    HUMAN_ONLY  = 4  # nur Mensch führt aus


class SkillResult(BaseModel):
    """
    Typsicheres Rückgabeobjekt für Skill.invoke().

    Attributes:
        success:      True wenn Skill erfolgreich war
        data:         Strukturiertes Ergebnis (JSON-serialisierbar)
        message:      Menschenlesbare Zusammenfassung
        skill_name:   Name des ausführenden Skills
        duration_ms:  Ausführungszeit in Millisekunden
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
            description: str = "Liefert Infrastruktur-Kontext"
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
        description="False = Skill wird nicht registriert",
    )

    def invoke(self, **kwargs: Any) -> SkillResult:
        """
        Skill ausführen. Muss in Subklassen überschrieben werden.

        Darf KEINE Exception werfen — gibt SkillResult.fail() zurück bei Fehler.
        """
        raise NotImplementedError(
            f"Skill '{self.name}' hat invoke() nicht implementiert. "
            "Bitte in der Subklasse überschreiben."
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
                data={
                    "exception_type": type(exc).__name__,
                    "duration_ms": duration_ms,
                },
            )
