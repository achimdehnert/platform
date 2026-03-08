"""
SkillRegistry — zentrale Registrierung und Discovery aller Agent-Skills.

Kein Magic via __init_subclass__: explizite Discovery via importlib.
Kein silentes Versagen: fehlende Skills werfen SkillNotFoundError.
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path

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
    log.info(
        "Skill registriert: %s v%s (domain=%s)",
        skill.name, skill.version, skill.domain,
    )


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


def _resolve_dependencies(
    skill: Skill,
    visited: set[str],
    stack: list[str] | None = None,
) -> None:
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

    Konvention: jedes Modul muss eine `SKILL`-Variable auf Modulebene
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
            log.error(
                "Skill-Modul '%s' konnte nicht geladen werden: %s",
                module_name, exc,
            )
            continue

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
            log.debug(
                "Modul '%s' hat keine SKILL Variable — wird übersprungen",
                module_name,
            )

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
