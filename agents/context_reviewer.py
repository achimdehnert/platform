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
import importlib.util
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any


def _lade_review_regeln():
    """`tools/review_regeln.py` ohne sys.path-Eingriff laden (agents/ ist ein Paket, tools/ nicht)."""
    pfad = Path(__file__).resolve().parents[1] / "tools" / "review_regeln.py"
    spec = importlib.util.spec_from_file_location("review_regeln", pfad)
    modul = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modul)
    return modul


review_regeln = _lade_review_regeln()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("context_reviewer")


# Muster kommen aus registry/review-regeln.yaml (Konsument `context-reviewer`,
# KONZ-platform-070 Z1, #3903). Die Namen bleiben fuer Aufrufer stabil; die Werte
# sind Regex-Alternativen (IGNORECASE) bzw. Pfad-Globs statt Substrings.
_MUSTER = review_regeln.context_muster()

#: {ADR-Referenz: [Regex, ...]} — gesucht in hinzugefuegten + entfernten Zeilen + Pfad.
ADR_KEYWORDS: dict[str, list[str]] = _MUSTER["adr"]
#: {Prinzip: [Regex, ...]} — gesucht in hinzugefuegten Zeilen + Pfad.
PRINCIPLE_KEYWORDS: dict[str, list[str]] = _MUSTER["prinzipien"]
#: [{referenz, max_zeilen, konfidenz}] — Umfangs-Schwellen (P-004 Minimal Diff).
UMFANG_REGELN: list[dict[str, Any]] = _MUSTER["umfang"]
#: {Projekt: [Glob, ...]} — gegen den kleingeschriebenen Pfad.
PROJECT_PATHS: dict[str, list[str]] = _MUSTER["projekte"]
#: Datei-Hinweise mit eigener Meldung (tenant_id, services.py, HTMX, Farbwerte), in Dateireihenfolge.
INSIGHT_REGELN: list[dict[str, Any]] = _MUSTER["insights"]


def _trifft(muster: list[str], text: str, exakt: bool = False) -> bool:
    flags = 0 if exakt else re.IGNORECASE
    return any(re.search(m, text, flags) for m in muster)


def _pfad_trifft(pfad: str, globs: list[str]) -> bool:
    return any(fnmatchcase(pfad, g) for g in globs)


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
        return f"- **{self.category}** → [{self.reference}]: {self.message}{loc}"


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
                + ", ".join(f"[{a}](docs/adr/{a}.md)" for a in self.affected_adrs)
            )

        if self.affected_principles:
            lines.append(
                "**Betroffene Prinzipien:** " + ", ".join(self.affected_principles)
            )

        if self.affected_projects:
            lines.append(
                "**Betroffene Projekte:** " + ", ".join(self.affected_projects)
            )

        lines.append("\n### Kontext-Hinweise\n")
        for insight in self.insights:
            lines.append(insight.to_markdown_item())

        lines.append("\n---\n*Context Reviewer v0.1.0 — informativ, nie blockierend*")

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

        for adr, muster in ADR_KEYWORDS.items():
            if _trifft(muster, all_text):
                found.add(adr)

    return sorted(found)


def detect_affected_principles(
    files: list[dict[str, Any]],
) -> list[str]:
    """Erkennt betroffene Architekturprinzipien."""
    found: set[str] = set()

    total_changes = sum(len(f["added_lines"]) + len(f["removed_lines"]) for f in files)
    for regel in UMFANG_REGELN:
        if total_changes > regel["max_zeilen"]:
            found.add(regel["referenz"])

    for f in files:
        all_text = (" ".join(f["added_lines"]) + " " + f["path"]).lower()

        for principle, muster in PRINCIPLE_KEYWORDS.items():
            if _trifft(muster, all_text):
                found.add(principle)

    return sorted(found)


def detect_affected_projects(
    files: list[dict[str, Any]],
) -> list[str]:
    """Erkennt betroffene Projekte basierend auf Pfaden."""
    found: set[str] = set()

    for f in files:
        path = f["path"].lower()
        for project, globs in PROJECT_PATHS.items():
            if _pfad_trifft(path, globs):
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
        insights.append(
            ContextInsight(
                category="ADR",
                reference=adr,
                message=(
                    f"Diese Änderung betrifft Bereiche "
                    f"die in {adr} geregelt sind. "
                    f"Bitte prüfen ob die Änderung "
                    f"konform ist."
                ),
            )
        )

    umfang = {r["referenz"]: r for r in UMFANG_REGELN}
    for principle in principles:
        if principle in umfang:
            total = sum(len(f["added_lines"]) + len(f["removed_lines"]) for f in files)
            insights.append(
                ContextInsight(
                    category="Prinzip",
                    reference=principle,
                    message=(
                        f"PR hat {total} geänderte Zeilen. "
                        f"Erwäge Aufteilen wenn möglich."
                    ),
                    confidence=umfang[principle]["konfidenz"],
                )
            )
        else:
            insights.append(
                ContextInsight(
                    category="Prinzip",
                    reference=principle,
                    message=(f"Änderung berührt {principle}. FYI für den Reviewer."),
                )
            )

    for f in files:
        path = f["path"]
        added = "\n".join(f["added_lines"])

        for regel in INSIGHT_REGELN:
            if _insight_trifft(regel, path, added):
                a = regel["ausgabe"]
                insights.append(
                    ContextInsight(
                        category=a["kategorie"],
                        reference=a["referenz"],
                        message=a["meldung"],
                        file=path,
                        confidence=a.get("konfidenz", 0.8),
                    )
                )

    return insights


def _insight_trifft(regel: dict[str, Any], path: str, added: str) -> bool:
    """Geltung (Pfad-Globs) und Detektor (pfad | regex auf hinzugefuegte Zeilen) einer Insight-Regel."""
    if not _pfad_trifft(path, regel["geltung"]["pfade"]):
        return False
    d = regel["detektor"]
    if d["typ"] == "pfad":
        return _pfad_trifft(path, d["muster"])
    if d["typ"] == "regex":
        return _trifft(d["muster"], added, exakt=d.get("gross_klein") == "exakt")
    return False


def analyze_diff(diff_text: str) -> ReviewResult:
    """Hauptfunktion: Analysiert Diff für Kontext-Review."""
    files = parse_diff(diff_text)

    adrs = detect_affected_adrs(files)
    principles = detect_affected_principles(files)
    projects = detect_affected_projects(files)
    insights = generate_insights(
        files,
        adrs,
        principles,
        projects,
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
        "--diff",
        type=str,
        help="Pfad zu Diff-Datei (oder stdin)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
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
