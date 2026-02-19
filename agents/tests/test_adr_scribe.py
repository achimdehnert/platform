"""Tests for ADR Scribe (Agent A3)."""
from __future__ import annotations

from pathlib import Path

from agents.adr_scribe import (
    AdrContext,
    AdrDraft,
    extract_keywords,
    find_next_adr_number,
    find_related_adrs,
    generate_adr,
    generate_title,
    slugify,
)


class TestFindNextAdrNumber:
    def test_should_find_next_number(self, tmp_path: Path):
        (tmp_path / "ADR-001-first.md").write_text("# ADR-001")
        (tmp_path / "ADR-005-fifth.md").write_text("# ADR-005")
        assert find_next_adr_number(tmp_path) == 6

    def test_should_return_1_for_empty_dir(
        self, tmp_path: Path,
    ):
        assert find_next_adr_number(tmp_path) == 1

    def test_should_handle_nonexistent_dir(self):
        assert find_next_adr_number(Path("/nonexistent")) == 1


class TestFindRelatedAdrs:
    def test_should_find_related_by_keyword(
        self, tmp_path: Path,
    ):
        (tmp_path / "ADR-010-governance.md").write_text(
            "---\ntitle: Governance\n---\n# Governance"
        )
        (tmp_path / "ADR-020-docs.md").write_text(
            "---\ntitle: Documentation\n---\n# Documentation"
        )
        related = find_related_adrs(
            tmp_path, ["governance"],
        )
        assert "ADR-010" in related
        assert "ADR-020" not in related

    def test_should_return_empty_for_no_matches(
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
            "background-jobs-fr-e-mail"
        )

    def test_should_truncate_long_slugs(self):
        long_text = "a" * 100
        assert len(slugify(long_text)) <= 60

    def test_should_handle_special_chars(self):
        slug = slugify("API/Key Management!")
        assert "/" not in slug
        assert "!" not in slug


class TestGenerateTitle:
    def test_should_return_short_problems_as_is(self):
        assert generate_title("Background Jobs") == (
            "Background Jobs"
        )

    def test_should_truncate_long_problems(self):
        long = "Wir brauchen eine L\u00f6sung " * 10
        title = generate_title(long)
        assert len(title) <= 60


class TestExtractKeywords:
    def test_should_extract_meaningful_words(self):
        keywords = extract_keywords(
            "Wir brauchen Background Jobs f\u00fcr E-Mail"
        )
        assert "background" in keywords
        assert "jobs" in keywords
        assert "wir" not in keywords
        assert "brauchen" not in keywords

    def test_should_limit_count(self):
        long = " ".join(f"keyword{i}" for i in range(50))
        assert len(extract_keywords(long)) <= 10


class TestGenerateAdr:
    def test_should_generate_valid_draft(
        self, tmp_path: Path,
    ):
        (tmp_path / "ADR-054-agents.md").write_text(
            "# ADR-054"
        )
        ctx = AdrContext(
            problem="Wir brauchen Background Jobs",
            project="travel-beat",
            author="Test Author",
        )
        draft = generate_adr(ctx, tmp_path)

        assert isinstance(draft, AdrDraft)
        assert draft.number == 55
        assert "ADR-055" in draft.filename
        assert "Background Jobs" in draft.content
        assert "PROPOSED" in draft.content
        assert "travel-beat" in draft.content

    def test_should_include_context(
        self, tmp_path: Path,
    ):
        ctx = AdrContext(
            problem="Celery vs RQ",
            context="Celery ist bereits in Benutzung",
        )
        draft = generate_adr(ctx, tmp_path)
        assert "Celery ist bereits" in draft.content

    def test_should_include_frontmatter(
        self, tmp_path: Path,
    ):
        ctx = AdrContext(problem="Test Problem")
        draft = generate_adr(ctx, tmp_path)
        assert draft.content.startswith("---")
        assert "status: PROPOSED" in draft.content
        assert "tags:" in draft.content

    def test_should_generate_dict(self, tmp_path: Path):
        ctx = AdrContext(problem="Test")
        draft = generate_adr(ctx, tmp_path)
        d = draft.to_dict()
        assert "number" in d
        assert "filename" in d
        assert d["gate"] == 2
