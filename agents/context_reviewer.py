"""
agents/context_reviewer.py — Context Reviewer (Agent A6)

Reichert PR-Reviews mit Plattform-Kontext an:
  - Erkennt betroffene ADRs und Architekturprinzipien
  - Identifiziert betroffene Projekte und Module
  - Liefert Kontext-Kommentare (informativ, nie blockierend)
  - Unterschied zu Guardian: Kontext statt Regeln

Nutzung:
  python -m agents.context_reviewer --diff /path/to/diff.patch
  python -m agents.context_reviewer --format json

Gate-Integration:
  Context Review → Gate 1 (NOTIFY — Kommentare automatisch, nie blockierend)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("context_reviewer")


ADR_KEYWORDS: dict[str, list[str]] = {
    "ADR-009": [
        "architecture", "platform", "service-map",
    ],
    "ADR-021": [
        "deployment", "docker", "compose", "deploy",
    ],
    "ADR-028": [
        "platform-context", "middleware", "tenant",
    ],
    "ADR-035": [
        "tenant", "multi-tenant", "tenant_id",
        "organization",
    ],
    "ADR-040": [
        "frontend", "completeness", "template",
        "tailwind",
    ],
    "ADR-041": [
        "component", "templatetag", "inclusion_tag",
    ],
    "ADR-042": [
        "deploy", "workflow", "ci/cd", "github-actions",
    ],
    "ADR-043": [
        "ai", "llm", "mcp", "agent", "windsurf",
    ],
    "ADR-045": [
        "secret", "api-key", "env", "credential",
    ],
    "ADR-048": [
        "htmx", "hx-get", "hx-post", "hx-swap",
    ],
    "ADR-049": [
        "token", "design-token", "pui-", "tailwind",
    ],
    "ADR-050": [
        "knowledge", "documentation", "sphinx", "rag",
    ],
    "ADR-052": [
        "pgvector", "embedding", "query-agent", "rag",
    ],
    "ADR-054": [
        "agent", "guardian", "scribe", "drift",
        "coach", "reviewer",
    ],
}

PRINCIPLE_KEYWORDS: dict[str, list[str]] = {
    "P-001 Database-First": [
        "models.py", "migration", "makemigrations",
        "CharField", "ForeignKey",
    ],
    "P-002 Zero Breaking Changes": [
        "deprecat", "breaking", "backward",
        "expand/contract",
    ],
    "P-003 Tenant-Isolation": [
        "tenant_id", "tenant", "multi-tenant",
        "organization",
    ],
    "P-004 Minimal Diff": [],
    "P-005 Service Layer": [
        "services.py", "service_layer", "business_logic",
    ],
}

PROJECT_PATHS: dict[str, list[str]] = {
    "travel-beat": [
        "apps/trips", "apps/stories", "apps/locations",
        "apps/worlds", "apps/ai_services",
    ],
    "bfagent": [
        "apps/bfagent", "apps/writing_hub",
        "apps/control_center", "apps/expert_hub",
    ],
    "weltenhub": [
        "apps/worlds", "apps/characters", "apps/scenes",
        "apps/enrichment",
    ],
    "risk-hub": [
        "apps/risk", "apps/assessments", "apps/reports",
    ],
    "platform": [
        "agents/", "packages/", "docs/adr",
        "shared/", "tools/",
    ],
    "mcp-hub": [
        "orchestrator_mcp", "llm_mcp",
        "deployment_mcp", "query_agent_mcp",
    ],
}


@dataclass
class ContextInsight:
    """Ein Kontext-Hinweis für den Reviewer."""

    category: str
    reference: str
    message: str
    file: str | None = None
    confidence: float = 0.8

    def to_markdown_item(self) -> str:
        loc = f" (`{self.file}`)" if self.file else ""
        return (
            f"- **{self.category}** → "
            f"[{self.reference}]: {self.message}{loc}"
        )


@dataclass
class ReviewResult:
    """Ergebnis der Context-Review-Analyse."""

    insights: list[ContextInsight] = field(
        default_factory=list,
    )
    affected_adrs: list[str] = field(default_factory=list)
    affected_principles: list[str] = field(
        default_factory=list,
    )
    affected_projects: list[str] = field(
        default_factory=list,
    )
    files_checked: int = 0

    @property
    def has_insights(self) -> bool:
        return len(self.insights) > 0

    def to_markdown(self) -> str:
        if not self.has_insights:
            return (
                "## Context Reviewer\n\n"
                f"Checked {self.files_checked} files. "
                "No additional context found."
            )

        lines = [
            "## Context Reviewer\n",
            f"Checked {self.files_checked} files.\n",
        ]

        if self.affected_adrs:
            lines.append(
                "**Betroffene ADRs:** "
                + ", ".join(
                    f"[{a}](docs/adr/{a}.md)"
                    for a in self.affected_adrs
                )
            )

        if self.affected_principles:
            lines.append(
                "**Betroffene Prinzipien:** "
                + ", ".join(self.affected_principles)
            )

        if self.affected_projects:
            lines.append(
                "**Betroffene Projekte:** "
                + ", ".join(self.affected_projects)
            )

        lines.append("\n### Kontext-Hinweise\n")
        for insight in self.insights:
            lines.append(insight.to_markdown_item())

        lines.append(
            "\n---\n"
            "*Context Reviewer v0.1.0 — "
            "informativ, nie blockierend*"
        )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_checked": self.files_checked,
            "insights_count": len(self.insights),
            "affected_adrs": self.affected_adrs,
            "affected_principles": self.affected_principles,
            "affected_projects": self.affected_projects,
            "insights": [
                {
                    "category": i.category,
                    "reference": i.reference,
                    "message": i.message,
                    "file": i.file,
                    "confidence": i.confidence,
                }
                for i in self.insights
            ],
        }


def parse_diff(diff_text: str) -> list[dict[str, Any]]:
    """Parst unified diff in Datei-Abschnitte."""
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current:
                files.append(current)
            match = re.search(r"b/(.+)$", line)
            path = match.group(1) if match else "unknown"
            current = {
                "path": path,
                "added_lines": [],
                "removed_lines": [],
            }
        elif current is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current["added_lines"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current["removed_lines"].append(line[1:])

    if current:
        files.append(current)

    return files


def detect_affected_adrs(
    files: list[dict[str, Any]],
) -> list[str]:
    """Erkennt betroffene ADRs basierend auf Dateiinhalten."""
    found: set[str] = set()

    for f in files:
        all_text = (
            " ".join(f["added_lines"])
            + " "
            + " ".join(f["removed_lines"])
            + " "
            + f["path"]
        ).lower()

        for adr, keywords in ADR_KEYWORDS.items():
            if any(kw in all_text for kw in keywords):
                found.add(adr)

    return sorted(found)


def detect_affected_principles(
    files: list[dict[str, Any]],
) -> list[str]:
    """Erkennt betroffene Architekturprinzipien."""
    found: set[str] = set()

    total_changes = sum(
        len(f["added_lines"]) + len(f["removed_lines"])
        for f in files
    )
    if total_changes > 400:
        found.add("P-004 Minimal Diff")

    for f in files:
        all_text = (
            " ".join(f["added_lines"])
            + " "
            + f["path"]
        ).lower()

        for principle, keywords in PRINCIPLE_KEYWORDS.items():
            if any(kw.lower() in all_text for kw in keywords):
                found.add(principle)

    return sorted(found)


def detect_affected_projects(
    files: list[dict[str, Any]],
) -> list[str]:
    """Erkennt betroffene Projekte basierend auf Pfaden."""
    found: set[str] = set()

    for f in files:
        path = f["path"].lower()
        for project, paths in PROJECT_PATHS.items():
            if any(p in path for p in paths):
                found.add(project)

    return sorted(found)


def generate_insights(
    files: list[dict[str, Any]],
    adrs: list[str],
    principles: list[str],
    projects: list[str],
) -> list[ContextInsight]:
    """Erzeugt Kontext-Hinweise."""
    insights: list[ContextInsight] = []

    for adr in adrs:
        insights.append(ContextInsight(
            category="ADR",
            reference=adr,
            message=(
                f"Diese Änderung betrifft Bereiche "
                f"die in {adr} geregelt sind. "
                f"Bitte prüfen ob die Änderung "
                f"konform ist."
            ),
        ))

    for principle in principles:
        if principle == "P-004 Minimal Diff":
            total = sum(
                len(f["added_lines"])
                + len(f["removed_lines"])
                for f in files
            )
            insights.append(ContextInsight(
                category="Prinzip",
                reference=principle,
                message=(
                    f"PR hat {total} geänderte Zeilen. "
                    f"Erwäge Aufteilen wenn möglich."
                ),
                confidence=0.9,
            ))
        else:
            insights.append(ContextInsight(
                category="Prinzip",
                reference=principle,
                message=(
                    f"Änderung berührt {principle}. "
                    f"FYI für den Reviewer."
                ),
            ))

    for f in files:
        path = f["path"]
        added = "\n".join(f["added_lines"])

        if path.endswith("models.py") and "tenant_id" in added:
            insights.append(ContextInsight(
                category="Multi-Tenancy",
                reference="P-003",
                message=(
                    "tenant_id Feld gefunden — "
                    "stelle sicher dass alle Queries "
                    "per tenant_id filtern."
                ),
                file=path,
            ))

        if "services.py" in path:
            insights.append(ContextInsight(
                category="Architecture",
                reference="P-005",
                message=(
                    "Service-Layer-Änderung — "
                    "Business-Logik gehört hierhin, "
                    "nicht in views.py."
                ),
                file=path,
                confidence=0.7,
            ))

        if re.search(r"hx-(get|post|put|delete)", added):
            insights.append(ContextInsight(
                category="HTMX",
                reference="ADR-048",
                message=(
                    "HTMX-Attribute erkannt. "
                    "Siehe ADR-048 für Patterns "
                    "(Swap, Boost, OOB)."
                ),
                file=path,
            ))

        if re.search(r"#[0-9a-fA-F]{6}\b", added):
            insights.append(ContextInsight(
                category="Design Tokens",
                reference="ADR-049",
                message=(
                    "Hardcoded Farbwert erkannt. "
                    "Nutze pui-Token aus "
                    "pui-tokens.css stattdessen."
                ),
                file=path,
                confidence=0.85,
            ))

    return insights


def analyze_diff(diff_text: str) -> ReviewResult:
    """Hauptfunktion: Analysiert Diff für Kontext-Review."""
    files = parse_diff(diff_text)

    adrs = detect_affected_adrs(files)
    principles = detect_affected_principles(files)
    projects = detect_affected_projects(files)
    insights = generate_insights(
        files, adrs, principles, projects,
    )

    return ReviewResult(
        insights=insights,
        affected_adrs=adrs,
        affected_principles=principles,
        affected_projects=projects,
        files_checked=len(files),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Context Reviewer — PR-Kontext-Analyse",
    )
    parser.add_argument(
        "--diff", type=str,
        help="Pfad zu Diff-Datei (oder stdin)",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json"],
        default="markdown",
    )
    args = parser.parse_args()

    if args.diff:
        diff_text = Path(args.diff).read_text(
            encoding="utf-8",
        )
    else:
        diff_text = sys.stdin.read()

    result = analyze_diff(diff_text)

    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_markdown())

    sys.exit(0)


if __name__ == "__main__":
    main()
