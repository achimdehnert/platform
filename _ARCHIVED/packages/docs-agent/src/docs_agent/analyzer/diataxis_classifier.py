"""DIATAXIS heuristic classifier for documentation files.

Classifies Markdown/RST files into DIATAXIS quadrants using
trigger-word pattern matching. No LLM required for the heuristic pass.

LLM refinement (confidence < 0.7) is deferred to Phase 4.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from docs_agent.models import DiaxisClassification, DiaxisQuadrant

logger = logging.getLogger(__name__)

TRIGGER_PATTERNS: dict[DiaxisQuadrant, list[str]] = {
    DiaxisQuadrant.TUTORIAL: [
        r"step\s+\d",
        r"getting\s+started",
        r"\blearn\b",
        r"we\s+will",
        r"in\s+this\s+tutorial",
        r"let[\u2018\u2019']s\s+",
        r"follow\s+along",
        r"by\s+the\s+end\b",
        r"prerequisites",
    ],
    DiaxisQuadrant.GUIDE: [
        r"how\s+to\b",
        r"\bconfigure\b",
        r"\bdeploy\b",
        r"\bfix\b",
        r"troubleshoot",
        r"set\s+up\b",
        r"install\b",
        r"upgrade\b",
        r"migrat",
        r"recipe",
    ],
    DiaxisQuadrant.REFERENCE: [
        r"\bAPI\b",
        r"\bparameter[s]?\b",
        r"\breturn[s]?\b",
        r"type\s*:",
        r"automodule",
        r"endpoint[s]?\b",
        r"\bschema\b",
        r"class\s+\w+",
        r"field[s]?\b",
        r"\bargs\b",
        r"\bkwargs\b",
    ],
    DiaxisQuadrant.EXPLANATION: [
        r"\bwhy\b",
        r"architecture",
        r"\bdesign\b",
        r"rationale",
        r"background",
        r"concept[s]?\b",
        r"overview",
        r"philosophy",
        r"trade-?off",
        r"decision",
    ],
}

DOC_EXTENSIONS: set[str] = {".md", ".rst", ".txt"}

SKIP_DIRS: set[str] = {
    "_archive",
    "_build",
    "source",
    "node_modules",
    ".git",
    ".venv",
    "venv",
}


def _count_triggers(
    text: str,
    patterns: list[str],
) -> tuple[int, list[str]]:
    """Count trigger pattern matches in text.

    Args:
        text: Document text to scan.
        patterns: Regex patterns to match.

    Returns:
        Tuple of (match_count, list_of_matched_patterns).
    """
    count = 0
    matched: list[str] = []
    for pattern in patterns:
        hits = len(re.findall(pattern, text, re.IGNORECASE))
        if hits > 0:
            count += hits
            matched.append(pattern)
    return count, matched


def classify_file(file_path: Path) -> DiaxisClassification:
    """Classify a single document file into a DIATAXIS quadrant.

    Args:
        file_path: Path to the document file.

    Returns:
        DiaxisClassification with quadrant, confidence, and triggers.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Cannot read %s: %s", file_path, exc)
        return DiaxisClassification(
            file_path=file_path,
            quadrant=DiaxisQuadrant.UNKNOWN,
            confidence=0.0,
        )

    scores: dict[DiaxisQuadrant, int] = {}
    all_triggers: dict[DiaxisQuadrant, list[str]] = {}

    for quadrant, patterns in TRIGGER_PATTERNS.items():
        count, matched = _count_triggers(text, patterns)
        scores[quadrant] = count
        all_triggers[quadrant] = matched

    total = sum(scores.values())
    if total == 0:
        return DiaxisClassification(
            file_path=file_path,
            quadrant=DiaxisQuadrant.UNKNOWN,
            confidence=0.0,
        )

    best_quadrant = max(scores, key=lambda q: scores[q])
    best_score = scores[best_quadrant]
    confidence = best_score / total

    # Boost confidence if file path hints at quadrant
    path_lower = str(file_path).lower()
    path_hints: dict[str, DiaxisQuadrant] = {
        "tutorial": DiaxisQuadrant.TUTORIAL,
        "getting-started": DiaxisQuadrant.TUTORIAL,
        "guide": DiaxisQuadrant.GUIDE,
        "howto": DiaxisQuadrant.GUIDE,
        "how-to": DiaxisQuadrant.GUIDE,
        "reference": DiaxisQuadrant.REFERENCE,
        "api": DiaxisQuadrant.REFERENCE,
        "explanation": DiaxisQuadrant.EXPLANATION,
        "adr": DiaxisQuadrant.EXPLANATION,
        "architecture": DiaxisQuadrant.EXPLANATION,
    }
    for hint, quadrant in path_hints.items():
        if hint in path_lower:
            if quadrant == best_quadrant:
                confidence = min(confidence + 0.15, 1.0)
            break

    return DiaxisClassification(
        file_path=file_path,
        quadrant=best_quadrant,
        confidence=round(confidence, 3),
        triggers=all_triggers[best_quadrant],
    )


def classify_repo(
    repo_path: Path,
) -> list[DiaxisClassification]:
    """Classify all documentation files in a repository.

    Args:
        repo_path: Root path of the repository.

    Returns:
        List of DiaxisClassification results.
    """
    repo_path = repo_path.resolve()
    results: list[DiaxisClassification] = []

    docs_dir = repo_path / "docs"
    if not docs_dir.is_dir():
        logger.info("No docs/ directory in %s", repo_path)
        return results

    for doc_file in sorted(docs_dir.rglob("*")):
        if not doc_file.is_file():
            continue
        if doc_file.suffix not in DOC_EXTENSIONS:
            continue
        if any(
            part in SKIP_DIRS
            for part in doc_file.relative_to(repo_path).parts
        ):
            continue

        classification = classify_file(doc_file)
        results.append(classification)

    return results
