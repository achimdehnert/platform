"""Data models for docs-agent analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ItemKind(str, Enum):
    """Kind of Python code item."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class DiaxisQuadrant(str, Enum):
    """DIATAXIS documentation quadrant."""

    TUTORIAL = "tutorial"
    GUIDE = "guide"
    REFERENCE = "reference"
    EXPLANATION = "explanation"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CodeItem:
    """A single documentable code item."""

    name: str
    kind: ItemKind
    line: int
    has_docstring: bool
    file_path: Path


@dataclass
class ModuleCoverage:
    """Docstring coverage for a single Python module."""

    file_path: Path
    total_items: int = 0
    documented_items: int = 0
    items: list[CodeItem] = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        """Coverage percentage (0.0\u2013100.0)."""
        if self.total_items == 0:
            return 100.0
        return (self.documented_items / self.total_items) * 100.0

    @property
    def undocumented(self) -> list[CodeItem]:
        """Items missing a docstring."""
        return [item for item in self.items if not item.has_docstring]


@dataclass
class RepoCoverage:
    """Aggregated docstring coverage for an entire repository."""

    repo_path: Path
    modules: list[ModuleCoverage] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        """Total documentable items across all modules."""
        return sum(m.total_items for m in self.modules)

    @property
    def documented_items(self) -> int:
        """Total documented items across all modules."""
        return sum(m.documented_items for m in self.modules)

    @property
    def coverage_pct(self) -> float:
        """Overall coverage percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.documented_items / self.total_items) * 100.0

    @property
    def undocumented_count(self) -> int:
        """Total undocumented items."""
        return self.total_items - self.documented_items


@dataclass(frozen=True)
class DiaxisClassification:
    """DIATAXIS classification result for a document."""

    file_path: Path
    quadrant: DiaxisQuadrant
    confidence: float
    triggers: list[str] = field(default_factory=list)
