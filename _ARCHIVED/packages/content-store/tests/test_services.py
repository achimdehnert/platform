"""Tests for content_store services (ADR-130, ADR-041)."""

from django.test import TestCase

from content_store.models import ContentSource, ContentType
from content_store.services import ContentStoreService


class ContentStoreServiceTest(TestCase):
    databases = {"default", "content_store"}

    def test_should_save_content_and_return_item(self):
        item = ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            content_type=ContentType.STORY,
            ref_id="trip-99",
            content="A fantastic journey.",
            model_used="gpt-4o-mini",
        )
        assert item.pk is not None
        assert item.version == 1
        assert item.model_used == "gpt-4o-mini"

    def test_should_deduplicate_by_sha256(self):
        content = "Identical content for dedup test"
        item1 = ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.BFAGENT,
            content_type=ContentType.ADR,
            ref_id="adr-test",
            content=content,
        )
        item2 = ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.BFAGENT,
            content_type=ContentType.ADR,
            ref_id="adr-test",
            content=content,
        )
        assert item1.pk == item2.pk

    def test_should_increment_version(self):
        ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.WELTENHUB,
            content_type=ContentType.WORLD,
            ref_id="world-42",
            content="Version 1 of the world.",
        )
        item2 = ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.WELTENHUB,
            content_type=ContentType.WORLD,
            ref_id="world-42",
            content="Version 2 of the world — updated.",
        )
        assert item2.version == 2

    def test_should_get_latest_version(self):
        ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            content_type=ContentType.CHAPTER,
            ref_id="ch-1",
            content="First version",
        )
        ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            content_type=ContentType.CHAPTER,
            ref_id="ch-1",
            content="Second version",
        )
        latest = ContentStoreService.get_latest(tenant_id=1, ref_id="ch-1")
        assert latest is not None
        assert latest.version == 2
        assert "Second" in latest.content

    def test_should_get_all_versions(self):
        for i in range(3):
            ContentStoreService.save_content(
                tenant_id=1,
                source=ContentSource.BFAGENT,
                content_type=ContentType.DRAFT,
                ref_id="draft-v",
                content=f"Draft version {i + 1}",
            )
        versions = ContentStoreService.get_versions(
            tenant_id=1, ref_id="draft-v",
        )
        assert len(versions) == 3
        assert versions[0].version == 3

    def test_should_add_relation(self):
        item1 = ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.WELTENHUB,
            content_type=ContentType.STORY,
            ref_id="story-rel",
            content="Story content",
        )
        item2 = ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.WELTENHUB,
            content_type=ContentType.CHAPTER,
            ref_id="chapter-rel",
            content="Chapter content",
        )
        rel = ContentStoreService.add_relation(
            source_item=item1,
            target_item=item2,
            relation_type="chapter_of",
        )
        assert rel.pk is not None
        assert rel.relation_type == "chapter_of"

    def test_should_save_compliance(self):
        record = ContentStoreService.save_compliance(
            tenant_id=0,
            adr_id="130",
            drift_score=0.05,
            status="compliant",
            details={"checked_files": 3},
        )
        assert record.pk is not None
        assert record.drift_score == 0.05

    def test_should_get_compliance_history(self):
        for score in [0.1, 0.3, 0.5]:
            ContentStoreService.save_compliance(
                tenant_id=0,
                adr_id="022",
                drift_score=score,
                status="compliant" if score < 0.5 else "warning",
            )
        history = ContentStoreService.get_compliance_history(
            tenant_id=0, adr_id="022",
        )
        assert len(history) == 3

    def test_should_search_by_source(self):
        ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            content_type=ContentType.STORY,
            ref_id="search-tb",
            content="Travel content",
        )
        ContentStoreService.save_content(
            tenant_id=1,
            source=ContentSource.WELTENHUB,
            content_type=ContentType.WORLD,
            ref_id="search-wh",
            content="World content",
        )
        results = ContentStoreService.search(
            tenant_id=1, source=ContentSource.TRAVEL_BEAT,
        )
        assert len(results) == 1
        assert results[0].source == "travel-beat"
