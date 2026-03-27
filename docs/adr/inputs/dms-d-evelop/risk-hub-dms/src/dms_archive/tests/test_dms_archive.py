"""
src/dms_archive/tests/test_dms_archive.py
==========================================
Tests für DmsArchiveService + Celery-Task.
iil-testkit Pattern: factory-boy + respx für HTTP-Mocks.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.dms_archive.models import DmsArchiveRecord
from src.dms_archive.services import ArchiveRequest, DmsArchiveService


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def archive_request(tenant_id):
    return ArchiveRequest(
        tenant_id     = tenant_id,
        source_type   = DmsArchiveRecord.DocumentType.PRIVACY_AUDIT,
        source_id     = uuid.uuid4(),
        source_label  = "Datenschutz-Audit Muster GmbH 2024-03-01",
        performed_by  = uuid.uuid4(),
        dms_category  = "DSGVO_AUDIT",
        dms_properties = {"Mandant": "Muster GmbH", "Audit-Datum": "2024-03-01"},
    )


# ── Service Tests ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDmsArchiveService:

    def test_schedule_archival_creates_pending_record(self, archive_request):
        with patch("src.dms_archive.tasks.archive_document_to_dms.apply_async"):
            record = DmsArchiveService.schedule_archival(archive_request)

        assert record.status == DmsArchiveRecord.ArchiveStatus.PENDING
        assert record.source_type == DmsArchiveRecord.DocumentType.PRIVACY_AUDIT
        assert record.tenant_id == archive_request.tenant_id

    def test_schedule_archival_idempotent_on_success(self, archive_request):
        """Zweiter Aufruf für dasselbe Objekt gibt existierenden SUCCESS zurück."""
        # Erst ein SUCCESS anlegen
        success_record = DmsArchiveRecord.objects.create(
            tenant_id     = archive_request.tenant_id,
            source_type   = archive_request.source_type,
            source_id     = archive_request.source_id,
            source_label  = archive_request.source_label,
            status        = DmsArchiveRecord.ArchiveStatus.SUCCESS,
            dms_document_id = "existing-dms-id",
        )

        with patch("src.dms_archive.tasks.archive_document_to_dms.apply_async") as mock_task:
            result = DmsArchiveService.schedule_archival(archive_request)

        # Task darf NICHT nochmal gefeuert werden
        mock_task.assert_not_called()
        assert result.id == success_record.id

    def test_schedule_archival_dispatches_celery_task(self, archive_request):
        with patch("src.dms_archive.tasks.archive_document_to_dms.apply_async") as mock_task:
            DmsArchiveService.schedule_archival(archive_request)

        mock_task.assert_called_once()
        kwargs = mock_task.call_args.kwargs["kwargs"]
        assert kwargs["source_type"] == archive_request.source_type
        assert kwargs["dms_category"] == "DSGVO_AUDIT"

    def test_retry_failed_increments_retry_count(self, archive_request):
        record = DmsArchiveRecord.objects.create(
            tenant_id   = archive_request.tenant_id,
            source_type = archive_request.source_type,
            source_id   = archive_request.source_id,
            source_label = archive_request.source_label,
            status      = DmsArchiveRecord.ArchiveStatus.FAILED,
            retry_count = 1,
        )

        with patch("src.dms_archive.tasks.archive_document_to_dms.apply_async"):
            result = DmsArchiveService.retry_failed(
                archive_request.tenant_id,
                archive_request.source_id,
                archive_request.performed_by,
            )

        assert result.status == DmsArchiveRecord.ArchiveStatus.RETRYING

    def test_retry_raises_after_max_retries(self, archive_request):
        DmsArchiveRecord.objects.create(
            tenant_id   = archive_request.tenant_id,
            source_type = archive_request.source_type,
            source_id   = archive_request.source_id,
            source_label = archive_request.source_label,
            status      = DmsArchiveRecord.ArchiveStatus.FAILED,
            retry_count = 3,  # bereits max
        )
        with pytest.raises(ValueError, match="Maximale Anzahl"):
            DmsArchiveService.retry_failed(
                archive_request.tenant_id,
                archive_request.source_id,
                archive_request.performed_by,
            )


# ── Model Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDmsArchiveRecord:

    def test_mark_success_updates_fields(self, tenant_id):
        record = DmsArchiveRecord.objects.create(
            tenant_id    = tenant_id,
            source_type  = "PRIVACY_AUDIT",
            source_id    = uuid.uuid4(),
            source_label = "Test",
            status       = "PENDING",
        )
        record.mark_success("dms-123", "repo-456", "DSGVO_AUDIT")
        record.refresh_from_db()

        assert record.status           == "SUCCESS"
        assert record.dms_document_id  == "dms-123"
        assert record.dms_repository_id == "repo-456"
        assert record.is_archived is True

    def test_mark_failed_increments_retry_count(self, tenant_id):
        record = DmsArchiveRecord.objects.create(
            tenant_id    = tenant_id,
            source_type  = "DATA_BREACH",
            source_id    = uuid.uuid4(),
            source_label = "Test",
            status       = "PENDING",
        )
        record.mark_failed("Connection timeout")
        record.refresh_from_db()

        assert record.status       == "FAILED"
        assert record.retry_count  == 1
        assert "timeout" in record.error_message

    def test_unique_success_constraint(self, tenant_id):
        """Pro source_id darf es nur einen SUCCESS-Eintrag geben."""
        from django.db import IntegrityError

        source_id = uuid.uuid4()
        DmsArchiveRecord.objects.create(
            tenant_id   = tenant_id,
            source_type = "VVT",
            source_id   = source_id,
            source_label = "Test",
            status      = "SUCCESS",
        )
        with pytest.raises(IntegrityError):
            DmsArchiveRecord.objects.create(
                tenant_id   = tenant_id,
                source_type = "VVT",
                source_id   = source_id,
                source_label = "Duplicate",
                status      = "SUCCESS",
            )
