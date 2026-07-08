"""Tests für scripts/gen_adr_index.py (Issue #997, T-14).

Golden-File-Test mit synthetischen ADR-Frontmatter-Varianten in einem
Wegwerf-Verzeichnis (tmp_path) — prüft, dass index.json + INDEX.md aus
`supersedes`- und `archived`-Frontmatter korrekt erzeugt werden. Rein lokal,
keine echten Netz-/gh-Calls.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gen_adr_index.py"
_spec = importlib.util.spec_from_file_location("gen_adr_index", _SCRIPT)
gai = importlib.util.module_from_spec(_spec)
sys.modules["gen_adr_index"] = gai
_spec.loader.exec_module(gai)


ADR_001 = """\
---
status: accepted
date: 2026-01-01
domains: [platform]
implementation_status: implemented
---
# ADR-001: First Decision

Body of the first decision.
"""

ADR_002 = """\
---
status: accepted
date: 2026-02-01
domains: [platform]
supersedes: [ADR-001]
implementation_status: in_progress
---
# ADR-002: Second Decision Supersedes First

Body of the second decision.
"""

ADR_099_ARCHIVED = """\
---
date: 2020-01-01
domains: [legacy]
---
# ADR-099: Old Archived Thing

Historical body.
"""


def _make_adr_tree(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-first-decision.md").write_text(ADR_001, encoding="utf-8")
    (adr_dir / "ADR-002-second-decision.md").write_text(ADR_002, encoding="utf-8")
    archive_dir = adr_dir / "_archive"
    archive_dir.mkdir()
    (archive_dir / "ADR-099-old-archived-thing.md").write_text(
        ADR_099_ARCHIVED, encoding="utf-8"
    )
    return adr_dir


def _run_index_generation(adr_dir: Path):
    active, archived = gai.scan_adrs(adr_dir)
    all_nums = {r["number"] for r in active}
    all_records = active + [r for r in archived if r["number"] not in all_nums]
    gai.build_backward_refs(all_records)

    json_path = adr_dir / "index.json"
    index_path = adr_dir / "INDEX.md"
    gai.write_json(active, archived, json_path)
    gai.write_index_md(active, index_path)
    return active, archived, json_path, index_path


def test_should_scan_active_and_archived_separately(tmp_path):
    adr_dir = _make_adr_tree(tmp_path)

    active, archived = gai.scan_adrs(adr_dir)

    assert [r["number"] for r in active] == [1, 2]
    assert [r["number"] for r in archived] == [99]
    assert archived[0]["status"] == "archived"  # kein status im Frontmatter → Default


def test_should_build_supersedes_backward_ref(tmp_path):
    adr_dir = _make_adr_tree(tmp_path)
    active, _archived, _json_path, _index_path = _run_index_generation(adr_dir)

    adr_001 = next(r for r in active if r["number"] == 1)
    adr_002 = next(r for r in active if r["number"] == 2)

    assert adr_002["supersedes"] == ["ADR-001"]
    assert adr_001["superseded_by"] == ["ADR-002"]


def test_should_write_index_json_with_next_free_and_merged_archive(tmp_path):
    adr_dir = _make_adr_tree(tmp_path)
    _active, _archived, json_path, _index_path = _run_index_generation(adr_dir)

    assert json_path.exists()
    doc = json.loads(json_path.read_text(encoding="utf-8"))

    assert doc["total"] == 2  # nur aktive ADRs zählen
    assert doc["next_free"] == 3  # max(active) + 1, archive-Nummer (99) zählt nicht mit
    ids = {r["id"] for r in doc["adrs"]}
    assert ids == {"ADR-001", "ADR-002", "ADR-099"}  # archiv wird gemerged

    adr_001_json = next(r for r in doc["adrs"] if r["id"] == "ADR-001")
    assert adr_001_json["superseded_by"] == ["ADR-002"]
    # underscore-Keys (interne Marker) dürfen nicht exportiert werden
    assert not any(k.startswith("_") for r in doc["adrs"] for k in r)


def test_should_write_index_md_with_only_active_adrs(tmp_path):
    adr_dir = _make_adr_tree(tmp_path)
    _active, _archived, _json_path, index_path = _run_index_generation(adr_dir)

    assert index_path.exists()
    text = index_path.read_text(encoding="utf-8")

    assert "ADR-001" in text
    assert "ADR-002" in text
    assert "ADR-099" not in text  # archivierte ADRs erscheinen NICHT in INDEX.md
    assert "Next free ADR number: **3**" in text
    assert "First Decision" in text
    assert "Second Decision Supersedes First" in text


def test_should_map_implementation_status_to_emoji(tmp_path):
    adr_dir = _make_adr_tree(tmp_path)
    active, _archived, _json_path, index_path = _run_index_generation(adr_dir)

    adr_001 = next(r for r in active if r["number"] == 1)
    adr_002 = next(r for r in active if r["number"] == 2)

    assert adr_001["_impl_emoji"] == "✅"  # implemented
    assert adr_002["_impl_emoji"] == "🔶"  # in_progress

    text = index_path.read_text(encoding="utf-8")
    assert "✅" in text
    assert "🔶" in text


def test_should_mark_no_impl_emoji_for_archived_status():
    # archived-Status hat laut NO_IMPL_STATUSES kein Impl-Symbol, sondern "—"
    assert gai._impl_emoji("archived", "implemented") == "—"
    assert gai._impl_emoji("accepted", "") == "⬜"
