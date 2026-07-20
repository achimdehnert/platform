"""Tests für scripts/checks/handover_refs.py (geteilter Referenz-Parser,
Konsumenten: agent_handover_reconcile.py + geplant platform#1252)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "checks"))

from handover_refs import extract_refs, open_section_lines  # noqa: E402

OWNER, REPO = "achimdehnert", "platform"

SAMPLE = """# Agent Handover

## ⚡ Aktueller Stand (2026-07-18)

- Kontext-Prosa mit https://github.com/achimdehnert/platform/pull/999 — NICHT offen.

## Nächste Schritte (kompakt)

1. Owner-Block [#1094](https://github.com/achimdehnert/platform/issues/1094) abarbeiten
2. Fleet-Follow-up shared-ci#20 fixen
3. coach-hub Deploy via achimdehnert/coach-hub#40 prüfen
4. nacktes Kürzel #77 erledigen

> **Erledigt 2026-07-15:** platform#1152 gemergt · [#1165](https://github.com/achimdehnert/platform/pull/1165)

## 0. Aktuelle Prioritäten

| 1 | ADR-242 Wave 3 [#811](https://github.com/achimdehnert/platform/issues/811) |
"""


def test_should_find_refs_only_in_open_sections():
    refs, _ = extract_refs(SAMPLE, OWNER, REPO)
    nums = {(r.owner, r.repo, r.number) for r in refs}
    assert (OWNER, REPO, 999) not in nums, "Referenz außerhalb offener Abschnitte gezählt"
    assert (OWNER, REPO, 811) not in nums, "Prio-Tabelle ist bewusste Parser-Grenze"
    assert (OWNER, REPO, 1094) in nums


def test_should_skip_erledigt_blockquotes():
    refs, _ = extract_refs(SAMPLE, OWNER, REPO)
    nums = {r.number for r in refs}
    assert 1152 not in nums and 1165 not in nums


def test_should_resolve_shorthand_and_bare_refs():
    refs, _ = extract_refs(SAMPLE, OWNER, REPO)
    triples = {(r.owner, r.repo, r.number) for r in refs}
    assert (OWNER, "shared-ci", 20) in triples, "repo#N → Default-Owner"
    assert ("achimdehnert", "coach-hub", 40) in triples, "owner/repo#N"
    assert (OWNER, REPO, 77) in triples, "nacktes #N → Default-Slug"


def test_should_dedupe_markdown_link_and_url():
    # [#1094](…/issues/1094) enthält dieselbe Referenz doppelt (Text + URL)
    refs, _ = extract_refs(SAMPLE, OWNER, REPO)
    assert sum(1 for r in refs if r.number == 1094) == 1


def test_should_report_skipped_sections_not_silently():
    _, skipped = extract_refs(SAMPLE, OWNER, REPO)
    assert any("Prioritäten" in s for s in skipped)


def test_should_handle_document_without_open_sections():
    refs, skipped = extract_refs("# Nur Titel\n\nProsa #12\n", OWNER, REPO)
    assert refs == []
    assert isinstance(skipped, list)


def test_should_collect_lines_with_line_numbers():
    lines, _ = open_section_lines(SAMPLE)
    assert all(isinstance(n, int) and n > 0 for n, _ in lines)
    joined = "\n".join(t for _, t in lines)
    assert "Owner-Block" in joined and "Erledigt" not in joined
