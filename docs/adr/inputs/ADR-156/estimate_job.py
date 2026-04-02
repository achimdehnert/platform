"""
orchestrator-mcp/tools/estimate_job.py

Echter Job-Estimator für den Orchestrator-MCP — Fix H3 (kein Hardcode-Stub).

ADR-156 §5: Jeder Job MUSS dem User vor Start Dauer-Schätzung + Background-Fähigkeit
kommunizieren.

Architektur:
  - job_catalog.yaml: Maschinenlesbarer Katalog mit Referenzwerten
  - JobEstimator: Gewichteter Durchschnitt aus Katalog + optionaler Messhistorie
  - estimate_job(): Hauptfunktion für orchestrator-mcp

Kein Hardcode: Werte kommen aus YAML, nicht aus Python-Literals.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml  # pyyaml — bereits in platform_context requirements


class Executor(str, Enum):
    SERVER_SCRIPT = "server-script"
    CI = "ci"
    LOCAL = "local"
    LLM = "llm"
    MCP = "mcp"


@dataclass(frozen=True)
class JobEstimate:
    """Vollständige Job-Schätzung für MCP-Kommunikation.

    Alle Zeitangaben in Sekunden.
    """
    job_type: str
    estimated_seconds: int
    estimated_seconds_min: int
    estimated_seconds_max: int
    background_capable: bool
    executor: Executor
    steps: list[str]
    parallel_safe: bool
    recommended_model: str | None = None
    notification_channel: str | None = "discord"

    def format_for_agent(self, repo: str | None = None) -> str:
        """Formatiert die Schätzung für die Agent-Ausgabe (ADR-156 §5)."""
        start_ts = time.strftime("%H:%M:%S")
        end_ts = time.strftime(
            "%H:%M:%S",
            time.localtime(time.time() + self.estimated_seconds),
        )
        mode = "⚡ Background (Agent bleibt verfügbar)" if self.background_capable else "⏳ Foreground (Agent wartet)"
        repo_str = f" {repo}" if repo else ""
        steps_str = " + ".join(self.steps) if self.steps else "—"

        return (
            f"╔══════════════════════════════════════════════════════╗\n"
            f"║  Job: {self.job_type}{repo_str:<36}║\n"
            f"║  Geschätzte Dauer: ~{self.estimated_seconds}s ({steps_str[:40]})\n"
            f"║  Bereich: {self.estimated_seconds_min}s–{self.estimated_seconds_max}s\n"
            f"║  Start: {start_ts:<45}║\n"
            f"║  Geplantes Ende: ~{end_ts:<38}║\n"
            f"║  Modus: {mode:<43}║\n"
            f"║  Executor: {self.executor.value:<41}║\n"
            f"╚══════════════════════════════════════════════════════╝"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_type": self.job_type,
            "estimated_seconds": self.estimated_seconds,
            "estimated_seconds_min": self.estimated_seconds_min,
            "estimated_seconds_max": self.estimated_seconds_max,
            "background_capable": self.background_capable,
            "executor": self.executor.value,
            "steps": self.steps,
            "parallel_safe": self.parallel_safe,
            "recommended_model": self.recommended_model,
            "notification_channel": self.notification_channel,
        }


@dataclass
class JobEstimator:
    """Schätzt Job-Dauer aus Katalog + optionaler Messhistorie.

    catalog_path: Pfad zu job_catalog.yaml
    history: Dict {job_type: [measured_seconds, ...]} für Feedback-Loop
    """
    catalog_path: Path = field(
        default_factory=lambda: Path(__file__).parent / "job_catalog.yaml"
    )
    history: dict[str, list[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._catalog = self._load_catalog()

    def _load_catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                f"Job-Katalog nicht gefunden: {self.catalog_path}. "
                f"Bitte job_catalog.yaml anlegen (ADR-156 §Phase 2)."
            )
        with self.catalog_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def estimate(
        self,
        job_type: str,
        repo: str | None = None,
        *,
        context: dict[str, Any] | None = None,
    ) -> JobEstimate:
        """Schätzt Job-Dauer.

        Lookup-Reihenfolge:
          1. Repo-spezifischer Eintrag: jobs.<job_type>.repos.<repo>
          2. Job-Typ-Default: jobs.<job_type>
          3. Fallback: unknown_job

        Falls Messhistorie vorhanden: gewichteter Durchschnitt (70% Katalog, 30% gemessen).
        """
        jobs = self._catalog.get("jobs", {})

        # Lookup: repo-spezifisch → Job-Typ-Default → Fallback
        entry: dict[str, Any] = {}
        if job_type in jobs:
            base = jobs[job_type]
            entry = dict(base)
            if repo and "repos" in base and repo in base["repos"]:
                entry.update(base["repos"][repo])
        else:
            entry = self._catalog.get("fallback", {
                "estimated_seconds_min": 10,
                "estimated_seconds_max": 300,
                "background_capable": True,
                "executor": "server-script",
                "steps": ["(unbekannter Job-Typ)"],
                "parallel_safe": False,
            })

        # Basis-Schätzung: Mittelpunkt aus Min/Max
        min_s: int = entry.get("estimated_seconds_min", 10)
        max_s: int = entry.get("estimated_seconds_max", 300)
        catalog_estimate = (min_s + max_s) // 2

        # Feedback-Loop: Gemessene Werte einbeziehen (30% Gewicht)
        final_estimate = catalog_estimate
        if job_type in self.history and self.history[job_type]:
            measured_avg = sum(self.history[job_type][-10:]) / len(self.history[job_type][-10:])
            final_estimate = int(0.7 * catalog_estimate + 0.3 * measured_avg)

        return JobEstimate(
            job_type=job_type,
            estimated_seconds=final_estimate,
            estimated_seconds_min=min_s,
            estimated_seconds_max=max_s,
            background_capable=entry.get("background_capable", True),
            executor=Executor(entry.get("executor", "server-script")),
            steps=entry.get("steps", []),
            parallel_safe=entry.get("parallel_safe", False),
            recommended_model=entry.get("recommended_model"),
            notification_channel=entry.get("notification_channel", "discord"),
        )

    def record_measurement(self, job_type: str, elapsed_seconds: float) -> None:
        """Speichert gemessene Job-Dauer für Feedback-Loop.

        Maximal 50 Werte pro Job-Typ (Rolling Window).
        """
        if job_type not in self.history:
            self.history[job_type] = []
        self.history[job_type].append(elapsed_seconds)
        # Rolling Window
        self.history[job_type] = self.history[job_type][-50:]


# ── Modul-Level Instanz (Singleton für MCP-Tool) ─────────────────────────────

_estimator: JobEstimator | None = None


def get_estimator() -> JobEstimator:
    global _estimator
    if _estimator is None:
        _estimator = JobEstimator()
    return _estimator


def estimate_job(
    job_type: str,
    repo: str | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> JobEstimate:
    """MCP-Tool: Schätzt Job-Dauer und Background-Fähigkeit.

    Args:
        job_type: Aus job_catalog.yaml (z.B. "deploy", "migrate", "docker_build")
        repo: Optionaler Repo-Name für repo-spezifische Schätzung
        context: Zusätzlicher Kontext (z.B. {"cached": True} für docker_build)

    Returns:
        JobEstimate mit Dauer, Executor, Steps, Background-Flag

    Beispiel:
        estimate = estimate_job("deploy", "risk-hub")
        print(estimate.format_for_agent("risk-hub"))
        cascade_tool_result = estimate.to_dict()
    """
    return get_estimator().estimate(job_type, repo, context=context)
