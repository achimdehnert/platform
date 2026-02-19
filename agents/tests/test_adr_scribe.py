"""Tests for ADR Scribe (Agent A3)."""
from __future__ import annotations

from pathlib import Path

from agents.adr_scribe import (
    extract_keywords,
    find_next_adr_number,
    find_related_adrs,
    generate_adr_draft,
    generate_title,
    slugify,
)


class TestFindNextAdrNumber:
    def test_should_find_next_after_existing(
        self, tmp_path: Path,
    ):
        (tmp_path / "ADR-001-test.md").write_text("# Test")
        (tmp_path / "ADR-002-other.md").write_text("# Other")
        assert find_next_adr_number(tmp_path) == 3

    def test_should_return_1_for_empty_dir(
        self, tmp_path: Path,
    ):
        assert find_next_adr_number(tmp_path) == 1

    def test_should_handle_gaps(self, tmp_path: Path):
        (tmp_path / "ADR-001-first.md").write_text("# 1")
        (tmp_path / "ADR-005-fifth.md").write_text("# 5")
        assert find_next_adr_number(tmp_path) == 6


class TestFindRelatedAdrs:
    def test_should_find_related_by_keyword(
        self, tmp_path: Path,
    ):
        (tmp_path / "ADR-001-deployment.md").write_text(
            "# Deployment Strategy\n\nDocker compose deploy."
        )
        related = find_related_adrs(
            tmp_path, ["deployment", "docker"],
        )
        assert len(related) >= 1
        assert "ADR-001" in related[0]

    def test_should_return_empty_for_no_match(
        self, tmp_path: Path,
    ):
        (tmp_path / "ADR-001-test.md").write_text("# Test")
        related = find_related_adrs(
            tmp_path, ["nonexistent_keyword"],
        )
        assert related == []


class TestSlugify:
    def test_should_create_slug(self):
        assert slugify("Background Jobs f\u00fcr E-Mail") == (
            "background-jobs-f\u00fcr-e-mail"
        )

    def test_should_truncate_long_slugs(self):
        long_text = "a" * 100
        assert len(slugify(long_text)) <= 60

    def test_should_handle_special_chars(self):
        slug = slugify("API/Key Management!")
        assert "/" not in slug
        assert "!" not in slug


class TestGenerateTitle:
    def test_should_use_problem_as_title(self):
        title = generate_title(
            "Wie sollen Background Jobs implementiert werden?",
        )
        assert isinstance(title, str)
        assert len(title) > 0

    def test_should_truncate_long_problems(self):
        long_problem = "x" * 200
        title = generate_title(long_problem)
        assert len(title) <= 100


class TestExtractKeywords:
    def test_should_extract_from_problem(self):
        keywords = extract_keywords(
            problem="Docker Compose Deployment Pipeline",
            context="CI/CD mit GitHub Actions",
        )
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_should_include_context_keywords(self):
        keywords = extract_keywords(
            problem="API Design",
            context="REST endpoints mit DRF",
        )
        assert any(
            k in ["api", "rest", "drf", "endpoints"]
            for k in keywords
        )

    def test_should_deduplicate(self):
        keywords = extract_keywords(
            problem="Docker Docker Docker",
            context="Docker setup",
        )
        assert keywords.count("docker") == 1


class TestGenerateAdrDraft:
    def test_should_generate_complete_draft(
        self, tmp_path: Path,
    ):
        draft = generate_adr_draft(
            adr_dir=tmp_path,
            problem="Background Jobs implementieren",
            project="travel-beat",
            context="Celery ist bereits eingerichtet",
        )
        assert "# ADR-001" in draft
        assert "Background Jobs" in draft
        assert "travel-beat" in draft
        assert "## Status" in draft
        assert "## Kontext" in draft
        assert "## Entscheidung" in draft

    def test_should_include_yaml_frontmatter(
        self, tmp_path: Path,
    ):
        draft = generate_adr_draft(
            adr_dir=tmp_path,
            problem="Test ADR",
            project="platform",
        )
        assert draft.startswith("---")
        assert "status: proposed" in draft
        assert "project: platform" in draft

    def test_should_find_related_adrs(
        self, tmp_path: Path,
    ):
        (tmp_path / "ADR-042-deployment.md").write_text(
            "# ADR-042 Deployment\n\nDocker compose deploy."
        )
        draft = generate_adr_draft(
            adr_dir=tmp_path,
            problem="Deployment Pipeline verbessern",
            project="platform",
            context="Docker und CI/CD",
        )
        assert "ADR-043" in draft or "043" in draft
