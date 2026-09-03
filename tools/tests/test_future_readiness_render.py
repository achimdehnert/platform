"""Renderer result.json → Markdown: Kopfzeile, Findings-Reihenfolge, Zellen-Hygiene.

Fixture synthetisch (kein echtes Repo). Prueft Invarianten, nicht den Wortlaut.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import future_readiness_render as fr  # noqa: E402


def _result(**over):
    d = {
        "repo": "example/repo",
        "analyzed_sha": "a" * 40,
        "run_date": "2026-09-03",
        "depth": "T1",
        "archetype": "python-package",
        "archetype_note": "pyproject mit [project]",
        "readiness": 42,
        "evidence_coverage": 0.5,
        "readiness_class": "insufficient-evidence",
        "criticality": {"value": "high", "source": "KNOWN_CRITICALITY"},
        "lifecycle": "active",
        "data_class": "internal",
        "findings": [
            {
                "severity": "P3",
                "question_id": "D09.2",
                "finding_type": "tool-versionen",
                "observation": "kein Pin",
                "requires_gate": "none",
            },
            {
                "severity": "P1",
                "question_id": "D06.3",
                "finding_type": "dependabot-alerts",
                "observation": "Zeile eins\nZeile zwei | mit Pipe",
                "requires_gate": "security-config",
            },
        ],
        "scores": {
            "D01": {"score": None, "coverage": 0.0},
            "D06": {"score": 2, "coverage": 1.0},
        },
    }
    d.update(over)
    return d


def test_should_render_header_with_counts_and_sha_prefix():
    md = fr.render(_result())
    assert md.splitlines()[0].startswith(
        "# example/repo — Future-Readiness (v2.3, T1, 2026-09-03"
    )
    assert "SHA `aaaaaaaa`" in md and "**Readiness 42**" in md
    assert "Findings 2 (P1 1, P2 0, P3 1)" in md


def test_should_sort_findings_by_severity_then_question_and_keep_cells_single_line():
    md = fr.render(_result())
    rows = [z for z in md.splitlines() if z.startswith("| P")]
    assert [r.split("|")[1].strip() for r in rows] == ["P1", "P3"]
    assert (
        "\n" not in rows[0].strip("\n")
        and "Zeile eins Zeile zwei / mit Pipe" in rows[0]
    )


def test_should_write_dash_for_unscored_dimension():
    md = fr.render(_result())
    assert "| D01 | – | 0.0 |" in md and "| D06 | 2 | 1.0 |" in md


def test_should_say_no_findings_when_list_empty():
    assert "Keine Findings." in fr.render(_result(findings=[]))
