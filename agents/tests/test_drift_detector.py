"""Tests for Drift Detector (Agent A4)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agents.drift_detector import (
    DriftReport,
    DocStatus,
    KeyStatus,
    check_doc_freshness,
    extract_frontmatter,
    scan_docs,
)


DOC_CURRENT = """\
---
id: test-001
title: Test Document
status: current
owner: platform-team
last_verified: {today}
tags: [test]
---

# Test Document

Some content here.
"""

DOC_STALE = """\
---
id: test-002
title: Stale Document
status: current
owner: platform-team
last_verified: 2024-01-01
tags: [test]
---

# Stale Document

This doc is old.
"""

DOC_NO_FRONTMATTER = """\
# No Frontmatter

Just plain markdown.
"""

DOC_MISSING_FIELDS = """\
---
title: Incomplete
---

# Incomplete Doc
"""

DOC_DEPRECATED = """\
---
id: test-old
title: Old Feature
status: deprecated
owner: platform-team
last_verified: 2025-01-01
---

# Deprecated Feature
"""


class TestExtractFrontmatter:
    def test_should_extract_valid_frontmatter(
        self, tmp_path: Path,
    ):
        f = tmp_path / "doc.md"
        f.write_text(DOC_STALE)
        fm = extract_frontmatter(f)
        assert fm is not None
        assert fm["id"] == "test-002"
        assert fm["title"] == "Stale Document"

    def test_should_return_none_for_no_frontmatter(
        self, tmp_path: Path,
    ):
        f = tmp_path / "doc.md"
        f.write_text(DOC_NO_FRONTMATTER)
        assert extract_frontmatter(f) is None

    def test_should_handle_missing_file_gracefully(
        self, tmp_path: Path,
    ):
        f = tmp_path / "missing.md"
        f.write_text("---\ninvalid: [yaml\n---\n")
        assert extract_frontmatter(f) is None


class TestCheckDocFreshness:
    def test_should_detect_stale_document(
        self, tmp_path: Path,
    ):
        f = tmp_path / "stale.md"
        f.write_text(DOC_STALE)
        doc = check_doc_freshness(
            f, tmp_path, threshold_days=90,
        )
        assert doc.is_stale
        assert any("Stale" in i for i in doc.issues)

    def test_should_pass_current_document(
        self, tmp_path: Path,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        f = tmp_path / "current.md"
        f.write_text(DOC_CURRENT.format(today=today))
        doc = check_doc_freshness(
            f, tmp_path, threshold_days=90,
        )
        assert not doc.is_stale

    def test_should_detect_missing_frontmatter(
        self, tmp_path: Path,
    ):
        f = tmp_path / "plain.md"
        f.write_text(DOC_NO_FRONTMATTER)
        doc = check_doc_freshness(
            f, tmp_path, threshold_days=90,
        )
        assert doc.is_incomplete

    def test_should_detect_missing_required_fields(
        self, tmp_path: Path,
    ):
        f = tmp_path / "incomplete.md"
        f.write_text(DOC_MISSING_FIELDS)
        doc = check_doc_freshness(
            f, tmp_path, threshold_days=90,
        )
        assert doc.is_incomplete
        assert any(
            "Missing required" in i for i in doc.issues
        )


class TestScanDocs:
    def test_should_scan_directory(self, tmp_path: Path):
        (tmp_path / "current.md").write_text(
            DOC_CURRENT.format(
                today=datetime.now().strftime("%Y-%m-%d"),
            )
        )
        (tmp_path / "stale.md").write_text(DOC_STALE)
        (tmp_path / "deprecated.md").write_text(
            DOC_DEPRECATED,
        )

        report = scan_docs(tmp_path, threshold_days=90)
        assert report.docs_checked == 3
        assert len(report.stale_docs) == 1
        assert len(report.deprecated_docs) == 1

    def test_should_skip_underscore_files(
        self, tmp_path: Path,
    ):
        (tmp_path / "_private.md").write_text(DOC_STALE)
        (tmp_path / "public.md").write_text(DOC_STALE)

        report = scan_docs(tmp_path, threshold_days=90)
        assert report.docs_checked == 2
        assert len(report.stale_docs) == 1


class TestDriftReport:
    def test_should_report_no_issues(self):
        report = DriftReport(docs_checked=5)
        assert not report.has_issues
        md = report.to_markdown()
        assert "Keine Drift-Probleme" in md

    def test_should_report_stale_docs(self):
        report = DriftReport(
            docs_checked=5,
            stale_docs=[
                DocStatus(
                    path="old.md",
                    frontmatter={
                        "last_verified": "2024-01-01",
                        "owner": "team",
                    },
                    issues=["Stale: 400 days"],
                ),
            ],
        )
        assert report.has_issues
        md = report.to_markdown()
        assert "Veraltete Dokumente" in md
        assert "old.md" in md

    def test_should_report_invalid_keys(self):
        report = DriftReport(
            docs_checked=0,
            key_statuses=[
                KeyStatus(
                    service="OpenAI",
                    key_prefix="sk-proj-abc",
                    valid=False,
                    error="HTTP 401",
                ),
            ],
        )
        assert report.has_issues
        md = report.to_markdown()
        assert "API Key Health" in md
        assert "OpenAI" in md

    def test_should_generate_dict(self):
        report = DriftReport(docs_checked=10)
        d = report.to_dict()
        assert d["docs_checked"] == 10
        assert d["has_issues"] is False
