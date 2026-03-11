---
status: "accepted"
date: 2026-02-15
amended: 2026-03-11
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-022-platform-consistency-standard.md", "ADR-037-chat-conversation-logging.md"]
---

# Adopt a shared Django app `content_store` for AI-generated content persistence

> **Amended 2026-03-11**: Review-Fixes — UUID→BigAutoField, Alembic→Django ORM,
> creative-services→content_store Django App, ContentRelation definiert, CHECK-Constraints.

---

## Context and Problem Statement

Mehrere Platform-Apps (travel-beat, weltenhub, bfagent) generieren KI-Inhalte
(Reisegeschichten, Weltenbeschreibungen, Buchkapitel), die bisher ausschließlich im
jeweiligen App-Schema gespeichert werden. Dadurch sind Cross-App-Auswertung,
plattformweite Versionierung und ADR-Compliance-Tracking strukturell nicht möglich.

**Problem**: Es gibt keinen gemeinsamen, schema-isolierten Persistenzort für
KI-generierte Inhalte. Jede App verwaltet ihren eigenen Speicher ohne einheitliche
Schnittstelle, ohne Versionierung und ohne Tenant-Isolation auf Plattformebene.

---

## Decision Drivers

- **Cross-App-Auswertung**: Inhalte aus travel-beat, weltenhub und bfagent sollen
  vergleichbar und gemeinsam auswertbar sein
- **Versionierung**: Jede KI-Ausgabe braucht einen unveränderlichen Hash + Versionszähler
- **Tenant-Isolation**: Alle Inhalte und Compliance-Daten müssen per `tenant_id` isoliert sein
- **ADR-Compliance**: Drift-Detector soll Compliance-Ergebnisse persistieren können
- **Minimale Invasion**: Bestehende App-Schemas bleiben unverändert
- **ADR-022 Konformität**: Ausschließlich Django ORM, BigAutoField, kein hardcoded SQL

---

## Considered Options

### Option 1 — Shared Django App `content_store` mit DATABASE_ROUTER (gewählt)

Eine Django-App `content_store` mit eigenen Models, verwaltet über Django-Migrations.
Alle consumer-Apps binden die App via `INSTALLED_APPS` ein. Ein `ContentStoreRouter`
routet Queries an eine dedizierte DB-Verbindung (`content_store` in `DATABASES`).

**Pro:**
- Einheitliche Schnittstelle für alle Apps
- Plattformweites Reporting ohne Cross-Schema-Joins im App-Code
- Django ORM: BigAutoField, Migrations, Admin — alles Platform-konform (ADR-022)
- Ein Migrationssystem (Django) — kein Ops-Overhead durch Alembic

**Contra:**
- `DATABASES["content_store"]` muss in allen consuming Apps konfiguriert werden
- Django-App muss in jeder consuming App in `INSTALLED_APPS` stehen

---

### Option 2 — Separate Tabellen pro App-Schema

Jede App bekommt eigene `content_items`-Tabellen in ihrem Django-Schema.

**Pro:** Kein zusätzliches Infrastruktur-Setup

**Contra:**
- Cross-App-Queries erfordern Joins über Schema-Grenzen (nicht portabel)
- Keine einheitliche Versionierung oder Compliance-Tracking
- Duplizierter Code in jeder App

**Verworfen**: Löst das Cross-App-Problem strukturell nicht.

---

### Option 3 — Externe Dokumentendatenbank (MongoDB / Elasticsearch)

**Pro:** Flexibles Schema, gute Volltextsuche

**Contra:**
- Neuer Infrastruktur-Stack neben PostgreSQL (Betriebsaufwand, Kosten)
- Kein nativer Tenant-Isolation-Mechanismus
- Widerspricht Platform-Prinzip "PostgreSQL als einzige DB-Technologie"

**Verworfen**.

---

### ~~Option 4 — Alembic-verwaltetes Schema~~ (ursprünglich gewählt, revidiert)

**Verworfen bei Review 2026-03-11**: Zwei parallele Migrationssysteme (Django + Alembic)
widersprechen ADR-022 (Platform Consistency Standard). UUID PRIMARY KEY widerspricht
BigAutoField-Pflicht. Ersetzt durch Option 1.

---

## Decision Outcome

**Gewählt: Option 1** — Shared Django App `content_store` mit DATABASE_ROUTER.

### Positive Consequences

- Einheitliche, typisierte Schnittstelle für alle Apps
- Plattformweites Reporting ohne Cross-Schema-Joins im App-Code
- ADR-Compliance-Daten zentral und tenant-isoliert verfügbar
- Versionierung und SHA-256-Hashing out-of-the-box
- **ADR-022 konform**: BigAutoField, Django ORM, ein Migrationssystem

### Negative Consequences

- `DATABASES["content_store"]` DSN muss in allen consuming Apps konfiguriert werden
- Django-App muss als Package installiert oder per `INSTALLED_APPS` eingebunden werden

---

## Implementation Details

### Django Models (`content_store/models.py`)

```python
from django.db import models


class ContentSource(models.TextChoices):
    TRAVEL_BEAT = "travel-beat"
    WELTENHUB = "weltenhub"
    BFAGENT = "bfagent"


class ContentType(models.TextChoices):
    STORY = "story"
    CHAPTER = "chapter"
    WORLD = "world"
    ADR = "adr"


class ContentItem(models.Model):
    """KI-generierter Inhalt — plattformweit, tenant-isoliert."""

    tenant_id = models.BigIntegerField(db_index=True)
    source = models.CharField(max_length=30, choices=ContentSource.choices)
    type = models.CharField(max_length=30, choices=ContentType.choices)
    ref_id = models.CharField(
        max_length=255, help_text="App-seitige ID des Quellobjekts"
    )
    content = models.TextField()
    sha256 = models.CharField(max_length=64)
    version = models.PositiveIntegerField(default=1)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "content_store"
        indexes = [
            models.Index(fields=["tenant_id", "source"]),
            models.Index(fields=["tenant_id", "type"]),
            models.Index(fields=["ref_id"]),
        ]

    def save(self, *args, **kwargs):
        import hashlib
        self.sha256 = hashlib.sha256(self.content.encode()).hexdigest()
        super().save(*args, **kwargs)


class ContentRelation(models.Model):
    """Beziehung zwischen zwei ContentItems (z.B. Outline → Chapter)."""

    source_item = models.ForeignKey(
        ContentItem, on_delete=models.CASCADE, related_name="outgoing_relations"
    )
    target_item = models.ForeignKey(
        ContentItem, on_delete=models.CASCADE, related_name="incoming_relations"
    )
    relation_type = models.CharField(
        max_length=50, help_text="z.B. 'derived_from', 'chapter_of', 'revision_of'"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "content_store"
        unique_together = [("source_item", "target_item", "relation_type")]


class ComplianceStatus(models.TextChoices):
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"


class AdrCompliance(models.Model):
    """ADR Drift-Detector Compliance-Ergebnis — tenant-isoliert."""

    tenant_id = models.BigIntegerField(db_index=True)
    adr_id = models.CharField(max_length=20)
    checked_at = models.DateTimeField(auto_now_add=True)
    drift_score = models.FloatField()
    status = models.CharField(max_length=20, choices=ComplianceStatus.choices)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "content_store"
        indexes = [
            models.Index(fields=["tenant_id", "adr_id"]),
        ]
```

### DATABASE_ROUTER (`content_store/router.py`)

```python
class ContentStoreRouter:
    """Routet content_store Models an die dedizierte DB-Verbindung."""

    APP_LABEL = "content_store"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return "content_store"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return "content_store"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label == self.APP_LABEL
            or obj2._meta.app_label == self.APP_LABEL
        ):
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == self.APP_LABEL:
            return db == "content_store"
        return None
```

### Settings-Integration (consuming App)

```python
# settings/base.py
INSTALLED_APPS = [
    ...
    "content_store",
]

DATABASES = {
    "default": { ... },  # App-eigene DB
    "content_store": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("CONTENT_STORE_DB_NAME", default="content_store"),
        "USER": config("CONTENT_STORE_DB_USER", default="content_store"),
        "PASSWORD": config("CONTENT_STORE_DB_PASSWORD"),
        "HOST": config("CONTENT_STORE_DB_HOST", default="localhost"),
        "PORT": config("CONTENT_STORE_DB_PORT", default="5432"),
    },
}

DATABASE_ROUTERS = ["content_store.router.ContentStoreRouter"]
```

### Service Layer (`content_store/services.py`)

```python
import hashlib
import logging

from .models import AdrCompliance, ContentItem, ContentRelation

logger = logging.getLogger(__name__)


class ContentStoreService:
    """Service-Layer für Content Store Operationen (ADR-041)."""

    @staticmethod
    def save_content(
        tenant_id: int,
        source: str,
        content_type: str,
        ref_id: str,
        content: str,
        meta: dict | None = None,
    ) -> ContentItem:
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        existing = ContentItem.objects.using("content_store").filter(
            tenant_id=tenant_id, ref_id=ref_id, sha256=sha256
        ).first()
        if existing:
            return existing

        latest = (
            ContentItem.objects.using("content_store")
            .filter(tenant_id=tenant_id, ref_id=ref_id)
            .order_by("-version")
            .first()
        )
        version = (latest.version + 1) if latest else 1

        return ContentItem.objects.using("content_store").create(
            tenant_id=tenant_id,
            source=source,
            type=content_type,
            ref_id=ref_id,
            content=content,
            sha256=sha256,
            version=version,
            meta=meta or {},
        )

    @staticmethod
    def add_relation(
        source_item: ContentItem,
        target_item: ContentItem,
        relation_type: str,
    ) -> ContentRelation:
        rel, _ = ContentRelation.objects.using("content_store").get_or_create(
            source_item=source_item,
            target_item=target_item,
            relation_type=relation_type,
        )
        return rel

    @staticmethod
    def save_compliance(
        tenant_id: int,
        adr_id: str,
        drift_score: float,
        status: str,
        details: dict | None = None,
    ) -> AdrCompliance:
        return AdrCompliance.objects.using("content_store").create(
            tenant_id=tenant_id,
            adr_id=adr_id,
            drift_score=drift_score,
            status=status,
            details=details or {},
        )
```

### Rollback-Strategie

| Szenario | Verhalten | Mitigation |
|----------|-----------|-----------|
| `content_store` DB nicht erreichbar | `OperationalError` bei Query | Apps fangen Exception im Service-Layer, loggen Warning, fahren ohne Persistenz fort |
| Django-Migration fehlgeschlagen | `python manage.py migrate --database=content_store` bricht ab | Standard Django Rollback: `migrate content_store <previous_migration>` |
| Korruptes Schema | Queries schlagen fehl | `pg_dump -n content_store` vor jeder Migration als Backup |

### Drift Detector Integration

`orchestrator_mcp/drift_detector.py` persistiert Compliance-Ergebnisse via `--persist`
Flag über `ContentStoreService.save_compliance()` (mit `tenant_id` aus Konfiguration).

---

## Migration Tracking

| Schritt | Status | Datum |
|---------|--------|-------|
| ~~Alembic-Setup in `creative-services`~~ | ❌ revidiert | 2026-03-11 |
| Django App `content_store` erstellt | 🔲 pending | — |
| Django-Migration 0001 (ContentItem + ContentRelation + AdrCompliance) | 🔲 pending | — |
| `DATABASES["content_store"]` in consuming Apps konfiguriert | 🔲 pending | — |
| Schema auf Prod deployed (88.198.191.108) via `manage.py migrate` | 🔲 pending | — |
| Drift Detector auf `ContentStoreService` umgestellt | 🔲 pending | — |

---

## Consequences

### Risks

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| DB-Verbindung fehlt | LOW | Lazy-Init mit try/except im Service; Apps degradieren graceful |
| Migration-Konflikt bei mehreren consuming Apps | MEDIUM | `content_store` Migrations nur in einem Repo (platform oder dev-hub) ausführen |
| `tenant_id` Konsistenz über Apps | MEDIUM | `tenant_id` ist `BigIntegerField` — kompatibel mit BigAutoField PKs der Tenant-Models |

### Confirmation

- `python manage.py migrate --database=content_store` im Deploy-Workflow
- `compliance-check.yml` läuft bei jedem Push auf `platform/main`
- Drift-Score-Schwellwert: `> 0.5` = Warning, `> 0.8` = Violation (blockiert Merge)
- Alle Queries im Service-Layer filtern auf `tenant_id`
- Kein direkter `Model.objects.` Zugriff in Views — nur via `ContentStoreService` (ADR-041)

---

## Drift-Detector Governance Note

```yaml
adr: ADR-130
paths:
  - content_store/models.py
  - content_store/services.py
  - content_store/router.py
  - orchestrator_mcp/drift_detector.py
  - .github/workflows/compliance-check.yml
gate: NOTIFY
```
