"""Paritätstest: Python-Parser und awk-Hook müssen dieselbe Sektion gleich lesen.

Hintergrund (Retro 2026-07-22, Befund B2): Dieselbe fachliche Regel — „welche Sektion
des AGENT_HANDOVER.md ist die aktive Prioritätenliste, und welche Items stehen darin" —
existiert zweimal:

  * `tools/next-sync/claude-next-sync`  (Python, erzeugt NEXT.md)
  * `tools/hooks/handover_prio_mirror.sh` (awk, spiegelt die Prio an den Session-Start)

Beide hatten eigene Golden-Tests und sind trotzdem auseinandergedriftet: bei einem
Dokument mit `## Nächste Schritte` VOR `## Prioritäten` gab der Hook die Items BEIDER
Sektionen aus, der Python-Parser nur die der exakten Sektion (awk 4 Items, Python 2).
Zwei getrennte Suiten können diese Klasse Fehler grundsätzlich nicht fangen — nur ein
Test, der beide über dasselbe Dokument fährt und die Ergebnisse vergleicht.

Die Fixtures unter `fixtures/handover_parity/` sind die gemeinsame Wahrheit. Wer eine
der beiden Implementierungen ändert, muss hier vorbeikommen.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parents[1]
_HOOK = _TOOLS / "hooks" / "handover_prio_mirror.sh"
_FIXTURES = sorted((Path(__file__).parent / "fixtures" / "handover_parity").glob("*.md"))

_SPEC = importlib.util.spec_from_loader(
    "claude_next_sync",
    importlib.machinery.SourceFileLoader(
        "claude_next_sync", str(_TOOLS / "next-sync" / "claude-next-sync")
    ),
)
cns = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cns)

# "  1. Aufgabentext  [Sonnet]" → "Aufgabentext"
_HOOK_LINE = re.compile(r"^\s*\d+\.\s+(?P<task>.*?)(?:\s\s+\[[^\]]+\])?\s*$")
# "[Sonnet] Aufgabentext" → "Aufgabentext"
_TIER_PREFIX = re.compile(r"^\[[^\]]+\]\s*")


def _python_tasks(repo: Path) -> list[str]:
    items = cns._read_handover(repo) or []
    return [_TIER_PREFIX.sub("", i).strip() for i in items]


def _awk_tasks(repo: Path) -> list[str]:
    out = subprocess.run(
        ["bash", str(_HOOK)], cwd=repo, capture_output=True, text=True, timeout=30
    ).stdout
    tasks: list[str] = []
    for line in out.splitlines():
        if line.startswith("⚑") or line.startswith("→") or not line.strip():
            continue
        m = _HOOK_LINE.match(line)
        if m:
            tasks.append(m.group("task").strip())
    return tasks


def _repo_from_fixture(tmp_path: Path, fixture: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()  # Hook läuft nur in Git-Repos
    (repo / "AGENT_HANDOVER.md").write_text(
        fixture.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return repo


def test_should_have_fixtures_available() -> None:
    """Schutz gegen ein still leeres Fixture-Verzeichnis (Test wäre sonst grün-blind)."""
    assert len(_FIXTURES) >= 10


@pytest.mark.parametrize("fixture", _FIXTURES, ids=lambda p: p.stem)
def test_should_read_identical_tasks_in_both_implementations(
    tmp_path: Path, fixture: Path
) -> None:
    """Beide Implementierungen liefern für dasselbe Dokument dieselben Aufgabentexte."""
    repo = _repo_from_fixture(tmp_path, fixture)
    py, awk = _python_tasks(repo), _awk_tasks(repo)
    assert py == awk, (
        f"Divergenz bei {fixture.name}:\n"
        f"  python: {py}\n"
        f"  awk   : {awk}\n"
        "Beide Implementierungen müssen dieselbe Sektion gleich lesen (Retro-Befund B2)."
    )


# Verankerte Erwartungen — Parität allein genügt nicht: beide könnten gemeinsam falsch
# liegen. Diese Fälle nageln fest, WAS richtig ist.
_EXPECTED = {
    "02_heuristic_before_exact": ["Exakt Gamma"],
    "04_partial_done": ["Trotz Teilerledigung sichtbar"],
    "05_archive_after_active": ["Aktives Item"],
    "06_archive_before_active": ["Aktives Item"],
    "07_prio_column_first": ["Aufgabentext statt Vokabel"],
}


@pytest.mark.parametrize("stem,expected", sorted(_EXPECTED.items()))
def test_should_extract_the_expected_tasks(
    tmp_path: Path, stem: str, expected: list[str]
) -> None:
    fixture = next(f for f in _FIXTURES if f.stem == stem)
    repo = _repo_from_fixture(tmp_path, fixture)
    assert _python_tasks(repo) == expected
    assert _awk_tasks(repo) == expected
