"""
Composite Score Tree (Design #2).

Hierarchical scoring with weighted categories.
Each node can explain WHY a hub scores high, not just THAT it does.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoreNode:
    """
    A node in the composite score tree.

    Leaf nodes have raw_score set directly by auditors.
    Branch nodes compute their score from children.
    """

    name: str
    weight: float = 1.0
    children: list[ScoreNode] = field(default_factory=list)
    raw_score: float = 0.0
    max_score: float = 100.0
    details: list[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        """Compute weighted score recursively."""
        if self.children:
            total = sum(
                c.weighted_score * c.weight for c in self.children
            )
            weight_sum = sum(c.weight for c in self.children)
            if weight_sum == 0:
                return 0.0
            return min(total / weight_sum, self.max_score)
        return min(self.raw_score, self.max_score)

    @property
    def grade(self) -> str:
        """Letter grade based on score (lower = better)."""
        score = self.weighted_score
        if score < 15:
            return "A"
        if score < 25:
            return "B"
        if score < 35:
            return "C"
        if score < 50:
            return "D"
        return "F"

    @property
    def passed(self) -> bool:
        """Whether this node passes (grade A or B)."""
        return self.grade in ("A", "B")

    def find(self, name: str) -> ScoreNode | None:
        """Find a child node by name (recursive)."""
        if self.name == name:
            return self
        for child in self.children:
            found = child.find(name)
            if found:
                return found
        return None

    def explain(self, depth: int = 0) -> str:
        """Human-readable score breakdown."""
        indent = "  " * depth
        score = self.weighted_score
        icon = "✅" if self.passed else "⚠️"
        line = (
            f"{indent}{icon} {self.name}: "
            f"{score:.1f}/100 ({self.grade})"
        )
        if self.details:
            for detail in self.details[:3]:
                line += f"\n{indent}   → {detail}"
            if len(self.details) > 3:
                extra = len(self.details) - 3
                line += f"\n{indent}   → ...+{extra} more"
        if self.children:
            for child in self.children:
                line += "\n" + child.explain(depth + 1)
        return line

    def to_dict(self) -> dict:
        """Serialize for JSON reports."""
        result = {
            "name": self.name,
            "score": round(self.weighted_score, 1),
            "grade": self.grade,
            "passed": self.passed,
            "weight": self.weight,
        }
        if self.details:
            result["details"] = self.details
        if self.children:
            result["children"] = [
                c.to_dict() for c in self.children
            ]
        return result


class ScoreTree:
    """
    Factory for building the standard score tree.

    HubIdentityScore (0-100)
    ├── VisualScore (40% weight)
    │   ├── Typography (50%)
    │   ├── Color (30%)
    │   └── Layout (20%)
    └── LinguisticScore (60% weight)
        ├── Vocabulary (40%)
        ├── Structure (30%)
        └── MicroCopy (30%)
    """

    @staticmethod
    def create() -> ScoreNode:
        """Create the standard hub identity score tree."""
        return ScoreNode(
            name="HubIdentityScore",
            children=[
                ScoreNode(
                    name="VisualScore",
                    weight=0.4,
                    children=[
                        ScoreNode(
                            name="Typography", weight=0.5,
                        ),
                        ScoreNode(
                            name="Color", weight=0.3,
                        ),
                        ScoreNode(
                            name="Layout", weight=0.2,
                        ),
                    ],
                ),
                ScoreNode(
                    name="LinguisticScore",
                    weight=0.6,
                    children=[
                        ScoreNode(
                            name="Vocabulary", weight=0.4,
                        ),
                        ScoreNode(
                            name="Structure", weight=0.3,
                        ),
                        ScoreNode(
                            name="MicroCopy", weight=0.3,
                        ),
                    ],
                ),
            ],
        )
