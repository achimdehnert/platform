---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-146  # risk-hub DMS Audit Trail — identisches Muster
  - ADR-148  # KI-Klassifikation (Phase 3 — Gate)
  - ADR-150  # DMS Rollout-Plan (Phase 4)
  - ADR-036  # Chat-Agent Ecosystem (research-hub Kontext)
  - ADR-045  # Secrets Management
staleness_months: 6
drift_check_paths:
  - research-hub/apps/archive/
---

# ADR-151: Adopt d.velop DMS als Langzeitarchiv für research-hub Quelldokumente

## Metadaten

| Attribut       | Wert                                                              |
|----------------|-------------------------------------------------------------------|
| **Status**     | Proposed                                                          |
| **Scope**      | research-hub                                                      |
| **Erstellt**   | 2026-03-25                                                        |
| **Autor**      | Achim Dehnert                                                     |
| **Relates to** | ADR-146, ADR-148, ADR-150, ADR-036, ADR-045                       |

## Repo-Zugehörigkeit

| Repo            | Rolle    | Betroffene Pfade                                    |
|-----------------|----------|-----------------------------------------------------|
| `research-hub`  | Primär   | `apps/archive/` (neu), `apps/research/services.py`  |
| `platform`      | Referenz | `docs/adr/`                                         |

---

## Decision Drivers

- **Recherche-Quellen verschwinden**: URLs werden ungültig, Preprints werden
  zurückgezogen, Paywalls sperren Inhalte. Einmal heruntergeladene PDFs müssen
  dauerhaft archiviert werden — die research-hub-Datenbank ist kein Archiv.
- **Identisches Muster wie ADR-146**: `DmsArchiveRecord` → `ResearchArchiveRecord`,
  `DmsArchiveService` → `ResearchArchiveService`. Gleiche Struktur, gleicher Client,
  anderer Aufrufpunkt (`finalize_source()`).
- **Volltext-Suche über d.velop**: Archivierte Quellen sind über
  `dvelop_search` (ADR-147) auffindbar — auch wenn die Original-URL nicht mehr
  existiert.
- **Gate: Phase 3 Done**: KI-Klassifikation (ADR-148) muss produktiv sein, damit
  archivierte Quellen automatisch mit der korrekten d.velop-Kategorie
  `RESEARCH_SOURCE` abgelegt werden.
- **Unabhängig von Phasen 1–3**: research-hub hat keinen Scanner — der
  Archivierungs-Trigger ist `finalize_source()`, nicht `process_scan_directory`.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

`Source`-Objekte in research-hub haben `url`, `doi`, `title`, `authors`, `year`,
`abstract` — aber keine persistente Kopie des Dokuments selbst. Nach Abschluss
einer Recherche ist die Quelle nur über die Original-URL erreichbar.

### 1.2 Ziel

Nach `finalize_source()` — dem Schritt, bei dem eine Quelle als relevant markiert
und abgeschlossen wird — wird ein Celery-Task getriggert, der:

1. Das PDF der Quelle herunterlädt (via DOI-Resolver oder direkter URL)
2. Es in d.velop unter Kategorie `RESEARCH_SOURCE` archiviert
3. Den `ResearchArchiveRecord` mit `dms_document_id` befüllt

```
[finalize_source()]           ← in apps/research/services.py
       │  transaction.on_commit()
       ▼
[archive_research_source]     ← Celery, Queue "dms"
       │
       ├─ PDF via DOI / URL laden
       ├─ d.velop Upload (Kategorie RESEARCH_SOURCE)
       └─ ResearchArchiveRecord.mark_success(...)
```

---

## 2. Considered Options

### Option A — Neue Django-App `archive` in research-hub (gewählt) ✅

Analog ADR-146 (`dms_archive` in risk-hub). Gleiche Model-Struktur,
gleicher `DvelopDmsClient`, anderer Aufrufpunkt.

**Pro:** Bewährtes Muster, minimaler neuer Code, kein neuer Hub.

**Con:** `DvelopDmsClient` zum dritten Mal kopiert (dms-hub, dvelop_mcp,
jetzt research-hub). Technische Schuld — bis zur Extraktion als
gemeinsames Package akzeptabel.

### Option B — research-hub ruft dms-hub REST-API auf

research-hub POSTet an dms-hub `/api/v1/archive/`, dms-hub leitet weiter.

**Abgelehnt**: Netzwerk-Abhängigkeit zwischen zwei Hubs zur Laufzeit.
research-hub auf Hetzner, dms-hub auf Hetzner — zusätzlicher Hop ohne
Mehrwert. Beim Ausfall von dms-hub schlägt auch research-hub-Archivierung fehl.

### Option B-alt — iil-researchfw direkt im Task (abgelehnt)

`iil-researchfw` ist bereits im research-hub installiert und hat
`AcademicSearchService` + `CitationService.from_doi()` — damit kann der
Task DOI → Metadaten → PDF-URL auflösen ohne eigenen HTTP-Code.

**Abgelehnt für direkte Task-Nutzung ohne Wrapper**: `iil-researchfw` ist
async-first (`asyncio.gather()`). Im Celery-Task ist `asyncio.run()` verboten
(ASGI-Kontext). Lösung: `asgiref.async_to_sync` als Adapter — das ist der
korrekte Plattform-Standard (ADR-045/Platform-Regel). Der Wrapper ist
minimal (~5 Zeilen) und liegt in `services.py`, nicht im Task direkt.

### Option C — Paperless-ngx als Zwischenstufe

Quelle → Paperless → d.velop.

**Abgelehnt**: Gleiche Ablehnung wie in ADR-149 §3. Behördendokumente
sollen nicht durch IIL-interne Infrastruktur laufen. Doppelte Datenhaltung.

---

## 3. Decision Outcome

**Gewählt: Option A** — neue App `apps/archive/` in research-hub,
analoges Muster zu ADR-146.

---

## 4. Implementation — Schritte

### Schritt 1 — App-Skeleton

```
research-hub/apps/archive/
├── __init__.py
├── apps.py              # ArchiveConfig
├── models.py            # ResearchArchiveRecord
├── services.py          # ResearchArchiveService
├── tasks.py             # archive_research_source (Celery)
├── migrations/
│   └── 0001_initial.py  # SeparateDatabaseAndState
└── tests/
    └── test_archive.py
```

`INSTALLED_APPS` in `config/settings/base.py` ergänzen:
```python
"apps.archive",
```

---

### Schritt 2 — `models.py`

Analog `DmsArchiveRecord` (ADR-146), aber für research-hub `Source`-Objekte:

```python
# apps/archive/models.py
from __future__ import annotations
import uuid
from django.db import models


class ResearchArchiveRecord(models.Model):
    """
    Audit-Trail jeder DMS-Archivierung einer research-hub Quelle.
    Unveränderlich nach Anlage. Nie löschen.
    """

    class ArchiveStatus(models.TextChoices):
        PENDING    = "PENDING",    "Ausstehend"
        SUCCESS    = "SUCCESS",    "Erfolgreich archiviert"
        FAILED     = "FAILED",     "Fehlgeschlagen"
        NO_PDF     = "NO_PDF",     "Kein PDF verfügbar"

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id        = models.UUIDField(db_index=True)

    # Referenz auf research-hub Source (lose Kopplung)
    source_id        = models.UUIDField(db_index=True,
                         help_text="UUID des Source-Objekts in research-hub")
    source_doi       = models.CharField(max_length=200, blank=True)
    source_url       = models.URLField(blank=True)
    source_title     = models.CharField(max_length=500)

    # DMS-Ergebnis
    dms_document_id  = models.CharField(max_length=255, blank=True, db_index=True)
    dms_repository_id = models.CharField(max_length=255, blank=True)

    status           = models.CharField(
        max_length=10, choices=ArchiveStatus.choices,
        default=ArchiveStatus.PENDING, db_index=True,
    )
    retry_count      = models.PositiveSmallIntegerField(default=0)
    error_message    = models.TextField(blank=True)
    celery_task_id   = models.CharField(max_length=255, blank=True)

    created_at       = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "research_archive_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "source_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "source_id"],
                condition=models.Q(status="SUCCESS"),
                name="uq_research_archive_one_success_per_source",
            )
        ]

    def mark_success(self, dms_doc_id: str, repo_id: str) -> None:
        self.status            = self.ArchiveStatus.SUCCESS
        self.dms_document_id   = dms_doc_id
        self.dms_repository_id = repo_id
        self.error_message     = ""
        self.save(update_fields=[
            "status", "dms_document_id", "dms_repository_id",
            "error_message", "updated_at",
        ])

    def mark_failed(self, error: str) -> None:
        self.status        = self.ArchiveStatus.FAILED
        self.error_message = error
        self.retry_count  += 1
        self.save(update_fields=["status", "error_message", "retry_count", "updated_at"])

    @property
    def is_archived(self) -> bool:
        return self.status == self.ArchiveStatus.SUCCESS
```

---

### Schritt 3 — `services.py`

```python
# apps/archive/services.py
from __future__ import annotations
import logging
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

logger = logging.getLogger(__name__)


@dataclass
class ArchiveSourceRequest:
    tenant_id:    UUID
    source_id:    UUID
    source_title: str
    source_doi:   str = ""
    source_url:   str = ""
    performed_by: UUID | None = None


class ResearchArchiveService:

    @staticmethod
    @transaction.atomic
    def schedule(request: ArchiveSourceRequest) -> "ResearchArchiveRecord":
        """
        Legt PENDING-Record an, dispatcht Celery-Task nach Commit.
        Idempotent: gibt bestehenden SUCCESS zurück ohne neuen Task.
        """
        from .models import ResearchArchiveRecord  # noqa: PLC0415
        from .tasks import archive_research_source  # noqa: PLC0415

        existing = ResearchArchiveRecord.objects.filter(
            tenant_id=request.tenant_id,
            source_id=request.source_id,
            status=ResearchArchiveRecord.ArchiveStatus.SUCCESS,
        ).first()
        if existing:
            logger.info("research_archive.already_archived source_id=%s", request.source_id)
            return existing

        record = ResearchArchiveRecord.objects.create(
            tenant_id     = request.tenant_id,
            source_id     = request.source_id,
            source_title  = request.source_title,
            source_doi    = request.source_doi,
            source_url    = request.source_url,
        )

        transaction.on_commit(
            lambda: archive_research_source.apply_async(
                kwargs={"record_id": str(record.id)},
                queue="dms",
            )
        )
        return record
```

---

### Schritt 4 — `tasks.py`

```python
# apps/archive/tasks.py
from __future__ import annotations
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    queue="dms",
    name="research_archive.archive_source",
    acks_late=True,
    reject_on_worker_lost=True,
)
def archive_research_source(self, *, record_id: str) -> dict:
    """
    Lädt PDF der Forschungsquelle und archiviert es in d.velop.
    Drei Quellen in Priorität: DOI-Resolver → direkte URL → kein PDF.
    """
    from platform_context.secrets import read_secret  # noqa: PLC0415
    from .models import ResearchArchiveRecord

    try:
        record = ResearchArchiveRecord.objects.get(id=record_id)
    except ResearchArchiveRecord.DoesNotExist:
        logger.error("research_archive: record %s nicht gefunden", record_id)
        return {"status": "error"}

    record.celery_task_id = self.request.id
    record.save(update_fields=["celery_task_id"])

    try:
        pdf_bytes, filename = _fetch_pdf(record)
    except NoPdfAvailable:
        record.status = ResearchArchiveRecord.ArchiveStatus.NO_PDF
        record.save(update_fields=["status", "updated_at"])
        logger.info("research_archive: kein PDF für %s", record.source_title[:60])
        return {"status": "no_pdf"}
    except Exception as exc:
        record.mark_failed(f"PDF-Download: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    try:
        api_key  = read_secret("DVELOP_API_KEY")
        base_url = settings.DVELOP_BASE_URL
        repo_id  = settings.DVELOP_DEFAULT_REPO_ID

        from dms_hub.client.dvelop_client import DvelopDmsClient  # noqa: PLC0415
        with DvelopDmsClient(base_url=base_url, api_key=api_key) as client:
            doc_id = client.upload_document(
                repo_id,
                filename=filename,
                file_content=pdf_bytes,
                category="RESEARCH_SOURCE",
                properties={
                    "Titel":  record.source_title[:255],
                    "DOI":    record.source_doi,
                    "URL":    record.source_url,
                    "Quelle": "research-hub",
                },
            )
        record.mark_success(dms_doc_id=doc_id, repo_id=repo_id)
        logger.info("research_archive: archiviert %s → %s", record.source_title[:60], doc_id)
        return {"status": "success", "dms_doc_id": doc_id}

    except Exception as exc:
        record.mark_failed(f"d.velop Upload: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


class NoPdfAvailable(Exception):
    pass


def _fetch_pdf(record: "ResearchArchiveRecord") -> tuple[bytes, str]:
    """
    Löst DOI → AcademicPaper.pdf_url über iil-researchfw auf.
    Sync-Wrapper via asgiref.async_to_sync (ADR-Plattformregel: kein asyncio.run).

    Reihenfolge:
    1. DOI  → AcademicSearchService.get_paper_by_doi(doi) → paper.pdf_url
    2. URL  → source_url direkt wenn auf .pdf endet
    3. DOI  → AcademicSearchService.search(doi, max_results=1) → paper.pdf_url
    4. NoPdfAvailable

    AcademicPaper-Felder (iil-researchfw):
        pdf_url: str | None   ← primäres Ziel-Attribut
        url:     str           ← Landing-Page, kein direktes PDF
        doi:     str | None
    """
    import httpx  # noqa: PLC0415
    from asgiref.sync import async_to_sync  # noqa: PLC0415
    from iil_researchfw.search.academic import AcademicSearchService  # noqa: PLC0415

    svc = AcademicSearchService()

    # 1. DOI → get_paper_by_doi → pdf_url (präzisester Treffer)
    if record.source_doi:
        try:
            @async_to_sync
            async def _by_doi() -> str | None:
                paper = await svc.get_paper_by_doi(record.source_doi)
                return paper.pdf_url if paper else None

            pdf_url = _by_doi()
            if pdf_url:
                resp = httpx.get(pdf_url, timeout=30, follow_redirects=True)
                resp.raise_for_status()
                safe_doi = record.source_doi.replace("/", "_").replace(":", "_")
                return resp.content, f"{safe_doi}.pdf"
        except Exception as exc:
            logger.debug("get_paper_by_doi fehlgeschlagen für %s: %s", record.source_doi, exc)

    # 2. Direkte URL (arXiv-PDFs, Institutional Repos)
    if record.source_url and record.source_url.lower().endswith(".pdf"):
        try:
            resp = httpx.get(record.source_url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            filename = record.source_url.rstrip("/").split("/")[-1] or "source.pdf"
            return resp.content, filename
        except Exception as exc:
            logger.debug("Direkter PDF-Download fehlgeschlagen: %s", exc)

    # 3. DOI → Volltext-Suche als Fallback (liefert mehr Quellen als get_paper_by_doi)
    if record.source_doi:
        try:
            @async_to_sync
            async def _search_fallback() -> str | None:
                papers = await svc.search(record.source_doi, max_results=1)
                return papers[0].pdf_url if papers and papers[0].pdf_url else None

            pdf_url = _search_fallback()
            if pdf_url:
                resp = httpx.get(pdf_url, timeout=30, follow_redirects=True)
                resp.raise_for_status()
                safe_doi = record.source_doi.replace("/", "_").replace(":", "_")
                return resp.content, f"{safe_doi}_fallback.pdf"
        except Exception as exc:
            logger.debug("search-Fallback fehlgeschlagen: %s", exc)

    raise NoPdfAvailable(
        f"Kein PDF verfügbar für source_id={record.source_id} "
        f"doi={record.source_doi!r} url={record.source_url!r}"
    )
```

---

### Schritt 5 — Integration in `apps/research/services.py`

Am Ende von `finalize_source()` einfügen — **nach** `emit_audit_event()`,
innerhalb des bestehenden `transaction.atomic()`-Blocks:

```python
# apps/research/services.py — Ergänzung in finalize_source()

from apps.archive.services import ResearchArchiveService, ArchiveSourceRequest

ResearchArchiveService.schedule(ArchiveSourceRequest(
    tenant_id    = source.tenant_id,
    source_id    = source.id,
    source_title = source.title,
    source_doi   = source.doi or "",
    source_url   = source.url or "",
    performed_by = performed_by,
))
```

---

### Schritt 6 — Migration `0001_initial.py`

```python
# apps/archive/migrations/0001_initial.py
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ResearchArchiveRecord",
                    fields=[
                        ("id",              models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                        ("tenant_id",       models.UUIDField(db_index=True)),
                        ("source_id",       models.UUIDField(db_index=True)),
                        ("source_doi",      models.CharField(max_length=200, blank=True, default="")),
                        ("source_url",      models.URLField(blank=True)),
                        ("source_title",    models.CharField(max_length=500)),
                        ("dms_document_id", models.CharField(max_length=255, blank=True, default="")),
                        ("dms_repository_id", models.CharField(max_length=255, blank=True, default="")),
                        ("status",          models.CharField(max_length=10, default="PENDING")),
                        ("retry_count",     models.PositiveSmallIntegerField(default=0)),
                        ("error_message",   models.TextField(blank=True, default="")),
                        ("celery_task_id",  models.CharField(max_length=255, blank=True, default="")),
                        ("created_at",      models.DateTimeField(auto_now_add=True)),
                        ("updated_at",      models.DateTimeField(auto_now=True)),
                    ],
                    options={"db_table": "research_archive_record", "ordering": ["-created_at"]},
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS research_archive_record (
                        id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id         UUID        NOT NULL,
                        source_id         UUID        NOT NULL,
                        source_doi        VARCHAR(200) NOT NULL DEFAULT '',
                        source_url        TEXT        NOT NULL DEFAULT '',
                        source_title      VARCHAR(500) NOT NULL,
                        dms_document_id   VARCHAR(255) NOT NULL DEFAULT '',
                        dms_repository_id VARCHAR(255) NOT NULL DEFAULT '',
                        status            VARCHAR(10) NOT NULL DEFAULT 'PENDING',
                        retry_count       SMALLINT    NOT NULL DEFAULT 0,
                        error_message     TEXT        NOT NULL DEFAULT '',
                        celery_task_id    VARCHAR(255) NOT NULL DEFAULT '',
                        created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS idx_research_archive_tenant
                        ON research_archive_record(tenant_id, status);
                    CREATE INDEX IF NOT EXISTS idx_research_archive_source
                        ON research_archive_record(tenant_id, source_id);
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_research_archive_success
                        ON research_archive_record(tenant_id, source_id)
                        WHERE status = 'SUCCESS';
                    """,
                    reverse_sql="DROP TABLE IF EXISTS research_archive_record;",
                )
            ],
        )
    ]
```

**Abhängigkeiten** — kein neues Package nötig:
`iil-researchfw` ist bereits in research-hub installiert.
`asgiref` ist Platform-Standard (bereits vorhanden).

```
# requirements.txt — keine Änderung nötig
# iil-researchfw[scraping] bereits vorhanden für Brave Search
```

---

### Schritt 7 — Tests (`apps/archive/tests/test_archive.py`)

```python
# apps/archive/tests/test_archive.py
import uuid
from unittest.mock import MagicMock, patch

import pytest
from apps.archive.models import ResearchArchiveRecord
from apps.archive.services import ArchiveSourceRequest, ResearchArchiveService


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def req(tenant_id):
    return ArchiveSourceRequest(
        tenant_id    = tenant_id,
        source_id    = uuid.uuid4(),
        source_title = "Open Access Paper über Django",
        source_doi   = "10.1234/test.2024",
        source_url   = "https://example.com/paper.pdf",
    )


@pytest.mark.django_db
class TestResearchArchiveService:

    def test_schedule_creates_pending_record(self, req):
        with patch("apps.archive.tasks.archive_research_source.apply_async"):
            record = ResearchArchiveService.schedule(req)
        assert record.status == ResearchArchiveRecord.ArchiveStatus.PENDING
        assert record.source_doi == req.source_doi

    def test_schedule_idempotent_on_success(self, req):
        existing = ResearchArchiveRecord.objects.create(
            tenant_id=req.tenant_id, source_id=req.source_id,
            source_title=req.source_title,
            status=ResearchArchiveRecord.ArchiveStatus.SUCCESS,
            dms_document_id="existing-id",
        )
        with patch("apps.archive.tasks.archive_research_source.apply_async") as mock_task:
            result = ResearchArchiveService.schedule(req)
        mock_task.assert_not_called()
        assert result.id == existing.id

    def test_mark_success_sets_fields(self, tenant_id):
        r = ResearchArchiveRecord.objects.create(
            tenant_id=tenant_id, source_id=uuid.uuid4(),
            source_title="Test", status="PENDING",
        )
        r.mark_success("dms-doc-123", "repo-456")
        r.refresh_from_db()
        assert r.status == "SUCCESS"
        assert r.dms_document_id == "dms-doc-123"
        assert r.is_archived is True

    def test_mark_failed_increments_retry(self, tenant_id):
        r = ResearchArchiveRecord.objects.create(
            tenant_id=tenant_id, source_id=uuid.uuid4(),
            source_title="Test", status="PENDING",
        )
        r.mark_failed("Timeout")
        r.refresh_from_db()
        assert r.status == "FAILED"
        assert r.retry_count == 1

    def test_no_pdf_status_on_missing_pdf(self, req):
        """NO_PDF ist kein Fehler — kein Retry, kein Alert."""
        record = ResearchArchiveRecord.objects.create(
            tenant_id=req.tenant_id, source_id=req.source_id,
            source_title=req.source_title,
        )
        record.status = ResearchArchiveRecord.ArchiveStatus.NO_PDF
        record.save(update_fields=["status", "updated_at"])
        record.refresh_from_db()
        assert record.status == "NO_PDF"
        assert record.is_archived is False


@pytest.mark.django_db
class TestFetchPdf:
    """Unit-Tests für _fetch_pdf mit gemocktem AcademicSearchService."""

    def test_get_paper_by_doi_with_pdf_url(self, req):
        """AcademicPaper.pdf_url vorhanden → direkt herunterladen."""
        import dataclasses
        from iil_researchfw.search.academic import AcademicPaper
        from unittest.mock import AsyncMock, patch
        import respx, httpx

        paper = AcademicPaper(
            title="Test Paper",
            authors=["Dehnert, A."],
            categories=[],
            pdf_url="https://arxiv.org/pdf/2024.12345.pdf",
        )
        fake_record = type("R", (), {
            "source_doi": "10.1234/test",
            "source_url": "",
            "source_id": req.source_id,
        })()

        with patch("iil_researchfw.search.academic.AcademicSearchService.get_paper_by_doi",
                   new=AsyncMock(return_value=paper)):
            with respx.mock:
                respx.get("https://arxiv.org/pdf/2024.12345.pdf").mock(
                    return_value=httpx.Response(200, content=b"%PDF-1.4 test")
                )
                from apps.archive.tasks import _fetch_pdf
                content, filename = _fetch_pdf(fake_record)

        assert content == b"%PDF-1.4 test"
        assert filename.endswith(".pdf")

    def test_no_pdf_url_raises_no_pdf_available(self, req):
        """paper.pdf_url is None und keine direkte URL → NoPdfAvailable."""
        import dataclasses
        from iil_researchfw.search.academic import AcademicPaper
        from unittest.mock import AsyncMock, patch
        from apps.archive.tasks import _fetch_pdf, NoPdfAvailable

        paper = AcademicPaper(
            title="Paywalled Paper",
            authors=["Author, B."],
            categories=[],
            pdf_url=None,   # kein Open-Access-PDF
        )
        fake_record = type("R", (), {
            "source_doi": "10.9999/paywalled",
            "source_url": "https://publisher.com/article",  # keine .pdf URL
            "source_id": req.source_id,
        })()

        with patch("iil_researchfw.search.academic.AcademicSearchService.get_paper_by_doi",
                   new=AsyncMock(return_value=paper)):
            with patch("iil_researchfw.search.academic.AcademicSearchService.search",
                       new=AsyncMock(return_value=[])):
                with pytest.raises(NoPdfAvailable):
                    _fetch_pdf(fake_record)
```

---

## 5. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-151 erstellt | ✅ Done | 2026-03-25 | |
| ADR-151 Review | ⬜ Pending | – | Gate: Phase 3 (ADR-148) Done |
| App-Skeleton + apps.py | ⬜ Pending | – | Schritt 1 |
| models.py + Migration | ⬜ Pending | – | Schritte 2 + 6 |
| services.py | ⬜ Pending | – | Schritt 3 |
| tasks.py + _fetch_pdf | ⬜ Pending | – | Schritt 4 |
| Hook in finalize_source() | ⬜ Pending | – | Schritt 5 |
| Tests grün | ⬜ Pending | – | Schritt 7 |
| 5 echte Quellen archiviert | ⬜ Pending | – | **Done-Kriterium** |

---

## 6. Consequences

### 6.1 Good

- Quelldokumente bleiben verfügbar auch wenn Original-URL verschwindet
- `NO_PDF`-Status für Quellen ohne Open-Access-PDF — kein Fehler, kein Alarm
- Volltext-Suche über `dvelop_search` (ADR-147) findet archivierte Quellen
- Identisches Muster zu ADR-146 — Cascade kennt die Struktur bereits
- Kein neues Package nötig: `iil-researchfw` bereits in research-hub installiert
- 3-stufige PDF-Auflösung: `CitationService` → direkte URL → `AcademicSearchService`

### 6.2 Bad

- `DvelopDmsClient` dreifach kopiert (dms-hub, mcp-hub, research-hub).
  Mittelfristig als `platform_context.dms_client` extrahieren.
- `async_to_sync`-Wrapper für `iil-researchfw` im synchronen Celery-Task
  ist ein notwendiges Adapter-Pattern — nicht elegant, aber plattformkonform.
- `CitationService.from_doi()` API-Antwortzeit: ~1–3s je nach Semantic Scholar Load.

### 6.3 Nicht in Scope

- Volltext-Indexierung der archivierten PDFs in research-hub (nutzt d.velop-Index)
- Automatisches Re-Archivieren wenn URL sich ändert
- Archivierung von HTML-Seiten (nur PDFs)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| `CitationService.from_doi()` kennt `pdf_url`-Attribut nicht (API-Änderung in iil-researchfw) | Niedrig | Mittel | `getattr(..., None)` — Fallback auf direkte URL + AcademicSearchService |
| Quelle hat kein Open-Access-PDF | Hoch | Niedrig | `NO_PDF`-Status — kein Fehler, kein Retry |
| `iil-researchfw`-Version inkompatibel nach Update | Niedrig | Mittel | Version in requirements.txt pinnen: `iil-researchfw>=x.y,<x+1` |
| `async_to_sync` Deadlock wenn nested in async Kontext | Niedrig | Hoch | Celery-Task ist sync — kein async-Kontext; nur asyncio.run() wäre Problem |

---

## 8. Confirmation

1. `pytest apps/archive/tests/ -v` — alle Tests grün
2. `finalize_source()` → `ResearchArchiveRecord(status=SUCCESS)` in DB
3. Archiviertes Dokument via `dvelop_search("RESEARCH_SOURCE")` auffindbar
4. Quelle ohne PDF → `status=NO_PDF`, kein Task-Retry, kein Alarm
5. `DVELOP_API_KEY` nur via `read_secret()` — kein Klartext

---

## 9. More Information

| Referenz | Inhalt |
|----------|--------|
| ADR-146 | `DmsArchiveRecord` — identisches Muster, dort zuerst implementiert |
| ADR-148 | Phase-3-Gate; KI-Klassifikation läuft auf Queue `"ai"` |
| ADR-150 | Roadmap: Phase 4 von 5 |
| iil-researchfw PyPI | https://pypi.org/project/iil-researchfw/ — `CitationService`, `AcademicSearchService` |
| asgiref async_to_sync | Platform-Standard für sync Wrapper in Celery-Tasks (kein asyncio.run) |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
