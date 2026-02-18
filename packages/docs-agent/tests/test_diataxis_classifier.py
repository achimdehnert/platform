"""Tests for the DIATAXIS heuristic classifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from docs_agent.analyzer.diataxis_classifier import (
    classify_file,
    classify_repo,
)
from docs_agent.models import DiaxisQuadrant


@pytest.fixture()
def docs_dir(tmp_path: Path) -> Path:
    """Create a temp repo with docs/ containing various document types."""
    docs = tmp_path / "docs"
    docs.mkdir()

    (docs / "getting-started.md").write_text(
        "# Getting Started\n\n"
        "In this tutorial, we will learn how to set up the project.\n"
        "Step 1: Install dependencies.\n"
        "Step 2: Configure the database.\n"
        "By the end, you will have a working app.\n"
    )

    (docs / "how-to-deploy.md").write_text(
        "# How to Deploy\n\n"
        "This guide explains how to deploy the application.\n"
        "Configure your .env file.\n"
        "Deploy with docker compose up.\n"
        "Troubleshoot common issues.\n"
    )

    (docs / "api-reference.md").write_text(
        "# API Reference\n\n"
        "## Endpoints\n"
        "GET /api/v1/users \u2014 returns a list of users.\n"
        "Parameters: page (int), per_page (int).\n"
        "Schema: UserListResponse.\n"
    )

    (docs / "architecture.md").write_text(
        "# Architecture Overview\n\n"
        "This document explains why we chose Django.\n"
        "The design rationale is based on the concept of\n"
        "separation of concerns. Background on the decision.\n"
    )

    (docs / "empty.md").write_text("")

    # _archive should be skipped
    archive = docs / "_archive"
    archive.mkdir()
    (archive / "old-doc.md").write_text("archived content")

    return tmp_path


def test_should_classify_tutorial(docs_dir: Path) -> None:
    """Tutorial-like documents should be classified as TUTORIAL."""
    result = classify_file(docs_dir / "docs" / "getting-started.md")

    assert result.quadrant == DiaxisQuadrant.TUTORIAL
    assert result.confidence > 0.3


def test_should_classify_guide(docs_dir: Path) -> None:
    """How-to documents should be classified as GUIDE."""
    result = classify_file(docs_dir / "docs" / "how-to-deploy.md")

    assert result.quadrant == DiaxisQuadrant.GUIDE
    assert result.confidence > 0.3


def test_should_classify_reference(docs_dir: Path) -> None:
    """API docs should be classified as REFERENCE."""
    result = classify_file(docs_dir / "docs" / "api-reference.md")

    assert result.quadrant == DiaxisQuadrant.REFERENCE
    assert result.confidence > 0.3


def test_should_classify_explanation(docs_dir: Path) -> None:
    """Architecture docs should be classified as EXPLANATION."""
    result = classify_file(docs_dir / "docs" / "architecture.md")

    assert result.quadrant == DiaxisQuadrant.EXPLANATION
    assert result.confidence > 0.3


def test_should_return_unknown_for_empty(docs_dir: Path) -> None:
    """Empty files should be classified as UNKNOWN."""
    result = classify_file(docs_dir / "docs" / "empty.md")

    assert result.quadrant == DiaxisQuadrant.UNKNOWN
    assert result.confidence == 0.0


def test_should_boost_confidence_from_path(tmp_path: Path) -> None:
    """Path hints should boost confidence when matching."""
    guides = tmp_path / "docs" / "guides"
    guides.mkdir(parents=True)
    (guides / "deploy.md").write_text(
        "How to deploy the app. Configure and fix issues."
    )

    result = classify_file(guides / "deploy.md")
    assert result.quadrant == DiaxisQuadrant.GUIDE
    # Path hint \"guides\" should boost confidence
    assert result.confidence >= 0.5


def test_should_skip_archive_in_repo_scan(docs_dir: Path) -> None:
    """classify_repo should skip _archive/ directories."""
    results = classify_repo(docs_dir)

    files = {r.file_path.name for r in results}
    assert "old-doc.md" not in files
    assert "getting-started.md" in files


def test_should_classify_all_docs_in_repo(docs_dir: Path) -> None:
    """classify_repo should return results for all doc files."""
    results = classify_repo(docs_dir)

    assert len(results) == 5  # 4 docs + empty.md
