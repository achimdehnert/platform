"""Tests for content_store models (ADR-130)."""

import pytest
from django.test import TestCase

from content_store.models import (
    AdrCompliance,
    ComplianceStatus,
    ContentItem,
    ContentRelation,
    ContentSource,
    ContentType,
)


class ContentItemModelTest(TestCase):
    databases = {"default", "content_store"}

    def test_should_create_content_item(self):
        item = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            type=ContentType.STORY,
            ref_id="trip-42",
            content="A wonderful journey through Bavaria.",
        )
        assert item.pk is not None
        assert item.version == 1
        assert len(item.sha256) == 64
        assert item.source == "travel-beat"

    def test_should_auto_compute_sha256_on_save(self):
        import hashlib

        content = "Test content for hashing"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()

        item = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.BFAGENT,
            type=ContentType.ADR,
            ref_id="adr-130",
            content=content,
        )
        assert item.sha256 == expected

    def test_should_store_metadata_as_json(self):
        meta = {"model": "gpt-4o", "tokens": 1500}
        item = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.WELTENHUB,
            type=ContentType.WORLD,
            ref_id="world-1",
            content="A dark forest realm.",
            meta=meta,
        )
        item.refresh_from_db()
        assert item.meta == meta


class ContentRelationModelTest(TestCase):
    databases = {"default", "content_store"}

    def test_should_create_relation(self):
        item1 = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            type=ContentType.STORY,
            ref_id="story-1",
            content="Once upon a time...",
        )
        item2 = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.TRAVEL_BEAT,
            type=ContentType.CHAPTER,
            ref_id="chapter-1",
            content="Chapter one begins.",
        )
        rel = ContentRelation.objects.using("content_store").create(
            source_item=item1,
            target_item=item2,
            relation_type="chapter_of",
        )
        assert rel.pk is not None
        assert rel.relation_type == "chapter_of"

    def test_should_enforce_unique_together(self):
        item1 = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.BFAGENT,
            type=ContentType.DRAFT,
            ref_id="draft-1",
            content="Draft content",
        )
        item2 = ContentItem.objects.using("content_store").create(
            tenant_id=1,
            source=ContentSource.BFAGENT,
            type=ContentType.DRAFT,
            ref_id="draft-2",
            content="Another draft",
        )
        ContentRelation.objects.using("content_store").create(
            source_item=item1,
            target_item=item2,
            relation_type="derived_from",
        )
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            ContentRelation.objects.using("content_store").create(
                source_item=item1,
                target_item=item2,
                relation_type="derived_from",
            )


class AdrComplianceModelTest(TestCase):
    databases = {"default", "content_store"}

    def test_should_create_compliance_record(self):
        record = AdrCompliance.objects.using("content_store").create(
            tenant_id=0,
            adr_id="130",
            drift_score=0.15,
            status=ComplianceStatus.COMPLIANT,
            details={"files_checked": 5},
        )
        assert record.pk is not None
        assert record.status == "compliant"
        assert record.details["files_checked"] == 5
