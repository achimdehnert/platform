---
status: proposed
date: 2026-02-16
decision-makers: Achim Dehnert
---

# ADR-038: DSB-Modul — Externer Datenschutzbeauftragter

**Status**: Proposed (R1 + R2 eingearbeitet — siehe ADR-038-REVIEW.md)
**Datum**: 2026-02-16
**Autoren**: Achim Dehnert
**Reviewer**: Cascade (AI Architect), 2026-02-16

## Kontext

Externe Datenschutzbeauftragte (DSB) verwalten für mehrere Mandanten (Kunden)
DSGVO-Unterlagen und koordinieren datenschutzrelevante Tätigkeiten:

- **Verarbeitungsverzeichnis** (VVT) gemäß Art. 30 DSGVO
- **Technische und organisatorische Maßnahmen** (TOM) gemäß Art. 32 DSGVO
- **Datenschutz-Folgenabschätzung** (DSFA) gemäß Art. 35 DSGVO
- **Löschkonzept** und Löschprotokolle gemäß Art. 17 DSGVO
- **Datenschutz-Audits** (intern/extern)
- **Jahresbericht** an die Geschäftsführung
- **Datenpannen-Meldungen** gemäß Art. 33/34 DSGVO
- **Schulungsnachweise** für Mitarbeiter
- **Auftragsverarbeitungsverträge** (AVV) gemäß Art. 28 DSGVO

### Tenant-Modell (R1: F-3/F-5)

Der Tenant (Organization) ist das **DSB-Büro**. Betreute Unternehmen sind
`Mandate` — Subentitäten, **keine** eigenständigen Tenants.

```text
Organization (Tenant = DSB-Büro)
  └── Mandate (betreutes Unternehmen)
       ├── ProcessingActivity (VVT)
       ├── TechnicalMeasure / OrganizationalMeasure (TOM)
       ├── PrivacyAudit → AuditFinding
       ├── DeletionLog
       └── Breach
```

## Entscheidung

### Empfehlung: risk-hub (schutztat.de) um DSB-App erweitern

**Kein separates Repository.** Neue Django-App `src/dsb/` in risk-hub.

**Synergien**:
- Arbeitsschutz + Datenschutz → gleicher Mandant, gleiche Nutzer
- Gemeinsame Infrastruktur: Dokumentenablage, Audit-Trail, Reporting

## Architektur

### Neue Django-App: `src/dsb/`

```text
src/dsb/
├── models/
│   ├── __init__.py
│   ├── mandate.py         # Mandate (betreutes Unternehmen)
│   ├── lookups.py         # Category, SubjectGroup, Recipient
│   ├── vvt.py             # ProcessingActivity
│   ├── tom.py             # TechnicalMeasure, OrganizationalMeasure
│   ├── dsfa.py            # DataProtectionImpactAssessment
│   ├── deletion.py        # DeletionConcept, DeletionLog
│   ├── audit.py           # PrivacyAudit, AuditFinding
│   ├── breach.py          # Breach (Datenpanne)
│   ├── training.py        # TrainingRecord
│   └── avv.py             # ProcessorAgreement (AVV)
├── services/
│   ├── vvt_service.py
│   ├── audit_service.py
│   ├── deletion_service.py
│   ├── report_service.py
│   └── breach_service.py
├── views/
│   ├── dashboard.py
│   ├── vvt_views.py
│   ├── audit_views.py
│   └── report_views.py
├── templates/dsb/
├── admin.py
├── urls.py
└── apps.py
```

### Kern-Models (R1 + R2 eingearbeitet)

Pattern-Konformität mit risk-hub Production-Code (R1):

- `models.Model` + explizites `tenant_id` — F-1
- UUID-PKs auf jedem Model — F-2
- Explizites `on_delete` auf allen ForeignKeys — F-3
- Normalisierte Lookup-Tabellen statt JSONField — F-4
- `settings.AUTH_USER_MODEL` statt direktem User-Import — F-6
- `db_table`, benannte Constraints und Indexes — F-7
- Innere TextChoices mit max_length — F-8
- AuditFinding als eigenständiges Model — F-9
- `deadline_72h` als Property statt stored field — F-10
- `created_by_id` / `updated_by_id` Audit-Felder — F-11

Zusätzlich eingearbeitet (R2):

- Model-Namen ohne redundanten App-Prefix — R2-F1
- TechnicalMeasure / OrganizationalMeasure spezifiziert — R2-F2
- Recipient als normalisiertes Lookup + M2M — R2-F3
- Breach.affected_categories als M2M — R2-F4
- LegalBasis als TextChoices (Art. 6 Abs. 1) — R2-F5
- Industry als TextChoices — R2-F6
- DeletionLog.data_category als FK — R2-F7
- `verbose_name`, `help_text`, `ordering` — R2-F8/F9/F10

#### Designentscheidung: Cross-App-Referenzen (R2-F12)

Beide Patterns existieren in Production:

- **Loose (UUIDField)**: `risk.Assessment.site_id`, `actions.ActionItem`
- **Tight (ForeignKey)**: `substances.SdsRevision` → `documents.DocumentVersion`

DSB nutzt **UUIDField** für `report_document_id`, `action_item_id` —
keine Migration-Dependency auf andere Apps, lose Kopplung bevorzugt.

#### Designentscheidung: Globale Lookup-Tabellen (R2-F13)

`Category`, `SubjectGroup`, `Recipient` haben **kein `tenant_id`** —
DSGVO-Kategorien sind standardisiert (wie `substances.HazardStatementRef`).
Für tenant-spezifische Erweiterungen: Hybrid-Pattern nach
`explosionsschutz.TenantScopedMasterData`.

```python
# src/dsb/models/mandate.py
import uuid

from django.db import models


class Mandate(models.Model):
    """Betreutes Unternehmen des DSB. KEIN Tenant — Subentität."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        PAUSED = "paused", "Pausiert"
        TERMINATED = "terminated", "Beendet"

    class Industry(models.TextChoices):
        HEALTHCARE = "healthcare", "Gesundheitswesen"
        FINANCE = "finance", "Finanzwesen"
        PUBLIC_SECTOR = "public_sector", "Öffentlicher Dienst"
        EDUCATION = "education", "Bildung"
        IT_TELECOM = "it_telecom", "IT & Telekommunikation"
        MANUFACTURING = "manufacturing", "Produzierendes Gewerbe"
        RETAIL = "retail", "Handel"
        LOGISTICS = "logistics", "Logistik"
        ENERGY = "energy", "Energie"
        OTHER = "other", "Sonstige"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=200)
    industry = models.CharField(
        max_length=20, choices=Industry.choices,
        blank=True, default="",
        help_text="Branche des betreuten Unternehmens",
    )
    employee_count = models.IntegerField(
        null=True, blank=True,
        help_text="Anzahl Beschäftigte (für Meldepflichten relevant)",
    )
    dsb_appointed_date = models.DateField(
        help_text="Datum der DSB-Bestellung",
    )
    contract_end_date = models.DateField(
        null=True, blank=True,
        help_text="Vertragsende (NULL = unbefristet)",
    )
    supervisory_authority = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Zuständige Aufsichtsbehörde (z.B. LfDI Baden-Württemberg)",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_mandate"
        verbose_name = "Mandat"
        verbose_name_plural = "Mandate"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_dsb_mandate_name_per_tenant",
            ),
            models.CheckConstraint(
                check=models.Q(
                    status__in=["active", "paused", "terminated"],
                ),
                name="ck_dsb_mandate_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_mandate_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.name
```

```python
# src/dsb/models/lookups.py — Globale Referenzdaten (kein tenant_id)
import uuid

from django.db import models


class Category(models.Model):
    """Lookup: Datenkategorie (Art. 9 DSGVO). Global, nicht tenant-spezifisch."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)
    is_special_category = models.BooleanField(
        default=False,
        help_text="Art. 9 besondere Kategorie (Gesundheit, Religion, etc.)",
    )

    class Meta:
        db_table = "dsb_category"
        verbose_name = "Datenkategorie"
        verbose_name_plural = "Datenkategorien"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class SubjectGroup(models.Model):
    """Lookup: Betroffenengruppe (z.B. Beschäftigte, Kunden, Patienten)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)

    class Meta:
        db_table = "dsb_subject_group"
        verbose_name = "Betroffenengruppe"
        verbose_name_plural = "Betroffenengruppen"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class Recipient(models.Model):
    """Lookup: Empfängerkategorie (Art. 30 Abs. 1 lit. d DSGVO)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)

    class Meta:
        db_table = "dsb_recipient"
        verbose_name = "Empfängerkategorie"
        verbose_name_plural = "Empfängerkategorien"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label
```

```python
# src/dsb/models/vvt.py
class ProcessingActivity(models.Model):
    """Verarbeitungstätigkeit gemäß Art. 30 DSGVO (VVT)."""

    class LegalBasis(models.TextChoices):
        CONSENT = "consent", "Art. 6(1)(a) Einwilligung"
        CONTRACT = "contract", "Art. 6(1)(b) Vertragserfüllung"
        LEGAL_OBLIGATION = "legal_obligation", "Art. 6(1)(c) Rechtl. Verpflichtung"
        VITAL_INTEREST = "vital_interest", "Art. 6(1)(d) Lebenswichtige Interessen"
        PUBLIC_INTEREST = "public_interest", "Art. 6(1)(e) Öffentliches Interesse"
        LEGITIMATE_INTEREST = "legitimate_interest", "Art. 6(1)(f) Berechtigtes Interesse"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        VERY_HIGH = "very_high", "Sehr hoch"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate, on_delete=models.CASCADE,
        related_name="processing_activities",
    )
    name = models.CharField(max_length=300)
    purpose = models.TextField(
        help_text="Zweck der Verarbeitung",
    )
    legal_basis = models.CharField(
        max_length=30, choices=LegalBasis.choices,
        help_text="Rechtsgrundlage nach Art. 6 Abs. 1 DSGVO",
    )
    data_categories = models.ManyToManyField(
        Category, blank=True,
        help_text="Kategorien personenbezogener Daten",
    )
    data_subjects = models.ManyToManyField(
        SubjectGroup, blank=True,
        help_text="Kategorien betroffener Personen",
    )
    recipients = models.ManyToManyField(
        Recipient, blank=True,
        help_text="Empfängerkategorien (Art. 30 Abs. 1 lit. d)",
    )
    third_country_transfer = models.BooleanField(
        default=False,
        help_text="Übermittlung in Drittland (Art. 44ff DSGVO)",
    )
    retention_period = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Aufbewahrungsfrist / Löschfrist",
    )
    tom_reference_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="Referenz auf TechnicalMeasure (lose Kopplung)",
    )
    risk_level = models.CharField(
        max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW,
    )
    dsfa_required = models.BooleanField(
        default=False,
        help_text="DSFA erforderlich (Art. 35 DSGVO)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_processing_activity"
        verbose_name = "Verarbeitungstätigkeit"
        verbose_name_plural = "Verarbeitungstätigkeiten"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "name"],
                name="uq_dsb_vvt_name_per_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_vvt_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return self.name
```

```python
# src/dsb/models/audit.py
class PrivacyAudit(models.Model):
    """Datenschutz-Audit."""

    class AuditType(models.TextChoices):
        INTERNAL = "internal", "Intern"
        EXTERNAL = "external", "Extern"
        SPOT_CHECK = "spot_check", "Stichprobe"

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IN_PROGRESS = "in_progress", "In Durchführung"
        COMPLETED = "completed", "Abgeschlossen"
        CANCELLED = "cancelled", "Abgebrochen"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate, on_delete=models.CASCADE, related_name="audits",
    )
    audit_type = models.CharField(
        max_length=20, choices=AuditType.choices,
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED,
    )
    report_document_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="FK zu documents.Document (lose Kopplung)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_privacy_audit"
        verbose_name = "Datenschutz-Audit"
        verbose_name_plural = "Datenschutz-Audits"
        ordering = ["-scheduled_date"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_audit_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_audit_type_display()} @ {self.scheduled_date}"


class AuditFinding(models.Model):
    """Einzelbefund eines Audits. Normalisiert (R1: F-9)."""

    class Severity(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        CRITICAL = "critical", "Kritisch"

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        RESOLVED = "resolved", "Behoben"
        ACCEPTED = "accepted", "Akzeptiert"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    audit = models.ForeignKey(
        PrivacyAudit, on_delete=models.CASCADE,
        related_name="findings",
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    severity = models.CharField(
        max_length=20, choices=Severity.choices,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN,
    )
    action_item_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="FK zu actions.ActionItem (lose Kopplung)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_audit_finding"
        verbose_name = "Audit-Befund"
        verbose_name_plural = "Audit-Befunde"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_finding_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title
```

```python
# src/dsb/models/deletion.py
class DeletionLog(models.Model):
    """Löschprotokoll gemäß Art. 17 DSGVO."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate, on_delete=models.CASCADE,
        related_name="deletion_logs",
    )
    processing_activity = models.ForeignKey(
        ProcessingActivity, on_delete=models.PROTECT,
        related_name="deletion_logs",
    )
    requested_at = models.DateTimeField()
    executed_at = models.DateTimeField(null=True, blank=True)
    data_category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        help_text="Gelöschte Datenkategorie",
    )
    record_count = models.IntegerField(
        null=True, blank=True,
        help_text="Anzahl gelöschter Datensätze",
    )
    method = models.CharField(
        max_length=100,
        help_text="Löschmethode (z.B. 'DB DELETE', 'Aktenvernichtung')",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_deletion_log"
        verbose_name = "Löschprotokoll"
        verbose_name_plural = "Löschprotokolle"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_deletion_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return f"Löschung {self.data_category} @ {self.requested_at:%Y-%m-%d}"
```

```python
# src/dsb/models/breach.py
class Breach(models.Model):
    """Datenpanne gemäß Art. 33 DSGVO."""

    class Severity(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        CRITICAL = "critical", "Kritisch"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate, on_delete=models.CASCADE,
        related_name="breaches",
    )
    discovered_at = models.DateTimeField()
    reported_to_authority_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Meldezeitpunkt an Aufsichtsbehörde",
    )
    severity = models.CharField(
        max_length=20, choices=Severity.choices,
    )
    affected_categories = models.ManyToManyField(
        Category, blank=True,
        help_text="Betroffene Datenkategorien (Art. 33 Abs. 3 lit. a)",
    )
    affected_count = models.IntegerField(
        null=True, blank=True,
        help_text="Ungefähre Anzahl betroffener Personen",
    )
    root_cause = models.TextField(blank=True, default="")
    measures_taken = models.TextField(
        blank=True, default="",
        help_text="Ergriffene Abhilfemaßnahmen (Art. 33 Abs. 3 lit. d)",
    )
    notified_subjects = models.BooleanField(
        default=False,
        help_text="Betroffene benachrichtigt (Art. 34 DSGVO)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_breach"
        verbose_name = "Datenpanne"
        verbose_name_plural = "Datenpannen"
        ordering = ["-discovered_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "severity"],
                name="idx_dsb_breach_tenant_severity",
            ),
        ]

    def __str__(self) -> str:
        return f"Datenpanne {self.discovered_at:%Y-%m-%d} ({self.get_severity_display()})"

    @property
    def deadline_72h(self):
        """72h-Meldefrist (Art. 33). Property statt stored field (R1: F-10)."""
        return self.discovered_at + timedelta(hours=72)

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        return (
            self.reported_to_authority_at is None
            and timezone.now() > self.deadline_72h
        )
```

```python
# src/dsb/models/tom.py
class TechnicalMeasure(models.Model):
    """Technische Maßnahme gemäß Art. 32 DSGVO."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IMPLEMENTED = "implemented", "Umgesetzt"
        VERIFIED = "verified", "Verifiziert"
        OBSOLETE = "obsolete", "Obsolet"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate, on_delete=models.CASCADE,
        related_name="technical_measures",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED,
    )
    responsible_user_id = models.UUIDField(
        null=True, blank=True,
        help_text="Verantwortliche Person (User-ID)",
    )
    review_date = models.DateField(
        null=True, blank=True,
        help_text="Nächster Überprüfungstermin",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_technical_measure"
        verbose_name = "Technische Maßnahme"
        verbose_name_plural = "Technische Maßnahmen"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "title"],
                name="uq_dsb_tech_measure_per_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_tech_measure_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class OrganizationalMeasure(models.Model):
    """Organisatorische Maßnahme gemäß Art. 32 DSGVO."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IMPLEMENTED = "implemented", "Umgesetzt"
        VERIFIED = "verified", "Verifiziert"
        OBSOLETE = "obsolete", "Obsolet"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate, on_delete=models.CASCADE,
        related_name="organizational_measures",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED,
    )
    responsible_user_id = models.UUIDField(
        null=True, blank=True,
        help_text="Verantwortliche Person (User-ID)",
    )
    review_date = models.DateField(
        null=True, blank=True,
        help_text="Nächster Überprüfungstermin",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_organizational_measure"
        verbose_name = "Organisatorische Maßnahme"
        verbose_name_plural = "Organisatorische Maßnahmen"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "title"],
                name="uq_dsb_org_measure_per_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_org_measure_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title
```

> **Phase 4 — TBD**: `DataProtectionImpactAssessment` (DSFA),
> `ProcessorAgreement` (AVV), `TrainingRecord` werden in separatem ADR
> spezifiziert, sobald Phase 1-3 implementiert sind.

### URL-Struktur (R1: F-14 — flach, konform mit risk-hub)

```text
/dsb/                     → DSB-Dashboard
/dsb/mandates/            → Mandatsverwaltung
/dsb/vvt/                 → VVT (Filter per Mandat)
/dsb/audits/              → Audit-Management
/dsb/deletions/           → Löschprotokolle
/dsb/breaches/            → Datenpannen
/dsb/reports/             → Jahresbericht
/api/v1/dsb/              → REST API (NinjaAPI)
```

### Cross-App-Referenzen

Lose Kopplung via UUIDField (Begründung: siehe Designentscheidung oben):

- `PrivacyAudit.report_document_id` → `documents.Document.id`
- `AuditFinding.action_item_id` → `actions.ActionItem.id`
- `ProcessingActivity.tom_reference_id` → `dsb.TechnicalMeasure.id`
- `TechnicalMeasure.responsible_user_id` → `identity.User.id`

Additive Migrationen für bestehende Apps (idempotent, da TextChoices-Erweiterung):

- `Document.Category` += `dsb_vvt`, `dsb_audit`, `dsb_avv`
- `Notification.Category` += `breach_deadline`, `deletion_due`
- `ApprovalWorkflow.WorkflowType` += `tom_approval`, `vvt_approval`

## Integration mit bestehenden risk-hub Apps

| App             | Nutzung durch DSB-Modul                      |
|-----------------|----------------------------------------------|
| `documents`     | VVT-Dokumente, Audit-Berichte, AVV-Verträge |
| `actions`       | Maßnahmen aus Audits, Löschaufträge          |
| `approvals`     | Freigabe-Workflows für TOM-Änderungen        |
| `reporting`     | Jahresbericht-Templates, PDF-Export          |
| `audit`         | Audit-Trail aller DSB-Aktivitäten            |
| `notifications` | Fristenwarnungen, Datenpannen-Alerts         |
| `ai_analysis`   | TOM-Bewertung, Risiko-Einschätzung VVT      |

## Implementierungsplan

### Phase 1: Kern-Models + CRUD (1-2 Wochen)

- Mandate, ProcessingActivity (VVT), Lookup-Tabellen (Category, SubjectGroup, Recipient)
- TechnicalMeasure, OrganizationalMeasure (TOM)
- Basis-Views mit HTMX, Dashboard-Grundgerüst
- Additive Migrationen für Document.Category, Notification.Category

### Phase 2: Workflows + Fristen (1-2 Wochen)

- DeletionLog mit Fristenverwaltung
- PrivacyAudit + AuditFinding mit Befund-Tracking
- Breach-Workflow (72h-Meldefrist Art. 33)

### Phase 3: Reporting + AI (1 Woche)

- Jahresbericht-Generator (PDF)
- AI-gestützte VVT-Vorschläge
- TOM-Vollständigkeitsprüfung

### Phase 4: DSFA + AVV + Schulungen (separater ADR)

- DataProtectionImpactAssessment (DSFA, Art. 35)
- ProcessorAgreement (AVV, Art. 28)
- TrainingRecord (Schulungsnachweise)

## Konsequenzen

### Positiv

- Sofortige Nutzung der risk-hub Infrastruktur
- Einheitliche Compliance-Plattform unter schutztat.de
- Kein zusätzliches Deployment

### Negativ

- risk-hub wird komplexer (mehr Apps)
- DSB-Modul muss sich an risk-hub Patterns halten

### Risiken

- Scope Creep → Phase-basierte Umsetzung
- DSGVO-Konformität der App selbst → eigenes VVT für schutztat.de
