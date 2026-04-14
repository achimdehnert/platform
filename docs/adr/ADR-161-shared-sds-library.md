---
status: proposed
date: 2026-03-26
amended: 2026-04-14
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-022 (Platform Consistency Standard — BigAutoField)
  - ADR-035 (Shared Django Tenancy)
repo: risk-hub
implementation_status: none
# Drift-Detector
staleness_months: 6
drift_check_paths:
  - risk-hub/src/apps/substances/models/
  - risk-hub/src/apps/substances/services/
  - risk-hub/src/apps/gbu/services/progress.py
supersedes_check: null
---

<!-- Drift-Detector-Felder: staleness_months=6, drift_check_paths=[risk-hub/src/apps/substances/], supersedes_check=null -->

# ADR-161: Adopt Two-Layer-Schema with Hybrid-RLS for Tenant-Spanning SDS Data

| Metadaten | |
|-----------|---|
| **Status** | Proposed |
| **Version** | 3.1 |
| **Datum** | 2026-03-26 |
| **Amended** | 2026-04-14 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Reviewer** | Cascade (Platform-Review 2026-04-14) |
| **Depends On** | ADR-022 (BigAutoField), ADR-035 (Shared Django Tenancy) |
| **Repo** | `risk-hub` |
| **GitHub Issues** | risk-hub #9 (Epic), #10 (Phase 0), #11 (Phase 1), #12 (Phase 2), #13 (Phase 3) |
| **Betrifft** | `substances`, `tenancy`, `platform` |

### Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-03-26 | Initiale Version: Two-Layer-Schema, globale Stammdaten |
| 2.0 | 2026-03-26 | Erweitert um Upload-Pipeline (3 Stufen), Supersession-Lifecycle, Impact-Klassifizierung, Compliance-Dashboard |
| 2.1 | 2026-03-26 | Review-Findings eingearbeitet: RLS-Strategie (B-1), Schema-Ownership (B-2), Diff-Persistenz (M-1), Outbox-Schema (M-2), approved_by-Constraint (M-3), konfigurierbare Settings (N-1), Zyklus-Constraint (N-2), Test-Konzept (N-3) |
| 3.0 | 2026-04-14 | Platform-Review: Renummiert als ADR-161. Compliance-Fixes identifiziert: BigAutoField statt UUID-PK, BaseProgressService-Konsolidierung, Fuzzy-Matching-Performance. 4-Phasen-Implementierungsplan als GitHub Issues (#9–#13). |
| 3.1 | 2026-04-14 | ADR-Review: MADR 4.0 Frontmatter, BigAutoField in Code-Snippets, Confirmation-Sektion, Drift-Detector, ADR-072-Abweichung begründet, Alternativen erweitert, Migration-Tracking. |

---

## 📋 Executive Summary

ADR-002 hat `Substance` und `SdsRevision` als **tenant-spezifische** Models implementiert.
Dieses ADR revidiert diese Entscheidung partiell:

Faktische SDS-Daten (CAS-Nummern, H-Sätze, AGW-Werte, Inhaltsstoffe) sind
objektive, herstellerdefinierte Informationen — sie sind für alle Tenants identisch.
Die aktuelle Architektur speichert das Mankiewicz-SDS für 2-Butoxyethanol N-mal
(einmal pro Tenant) und riskiert inkonsistente Datenqualität.

**Kernentscheidungen:**

| # | Entscheidung |
|---|---|
| 1 | `Substance`, `SdsRevision`, `SdsComponent`, `SdsExposureLimit` → **global**, kein `tenant_id` |
| 2 | `SdsUsage` bleibt tenant-isoliert und enthält Freigabe, Notizen, Update-Status |
| 3 | Upload-Pipeline erkennt Duplikate (SHA-256), löst Identität auf (CAS/Fuzzy) und erkennt Versionen automatisch |
| 4 | SDS-Updates lösen impact-klassifizierten Supersession-Workflow aus (SAFETY_CRITICAL / REGULATORY / INFORMATIONAL) |
| 5 | LLM ist Qualitäts-Gate für den Parser, kein Fallback |
| 6 | Compliance-Dashboard visualisiert Überprüfungspflichten mit Deadline-Ampel |
| 7 | Globale Tabellen erhalten **Hybrid-RLS**: SELECT für alle, INSERT/UPDATE/DELETE nur via Service-Account (analog ADR-001 v5) |
| 8 | Schema-Ownership: Globale Tabellen leben im `substances`-App des risk-hub mit `app_label="global_sds"` — Extraktion in Platform-Package bei zweitem Hub |

**Zentraler Mehrwert:** Ein Tenant lädt ein SDS hoch → nach Verifikation profitieren
alle Tenants. Bei Hersteller-Updates werden alle betroffenen Tenants automatisch
benachrichtigt und GBU/Ex-Schutz-Dokumente entsprechend geflaggt.

---

## 1. Kontext und Problemstellung

### 1.1 Aktuelle Situation (ADR-002)

```
Tenant A:  Substance(id=1, cas="111-76-2", tenant_id="A") + SdsRevision(tenant_id="A")
Tenant B:  Substance(id=2, cas="111-76-2", tenant_id="B") + SdsRevision(tenant_id="B")
Tenant C:  Substance(id=3, cas="111-76-2", tenant_id="C") + SdsRevision(tenant_id="C")
           ──────────────────────────────────────────────────────────────────────────
           3× gespeichert, 3× geparst, möglicherweise 3× unterschiedliche AGW-Werte
```

### 1.2 Identifizierte Probleme

| # | Problem | Auswirkung |
|---|---------|------------|
| P-1 | Datenduplizierung | Storage-Kosten, keine Single Source of Truth |
| P-2 | Inkonsistente Parsergebnisse | Tenant A hat H302, Tenant B nicht (Parser-Bug) |
| P-3 | Kein Netzwerkeffekt | 100 Tenants = 100× denselben Parse-Aufwand |
| P-4 | Kein Update-Mechanismus | Mankiewicz aktualisiert SDS → jeder Tenant manuell |
| P-5 | Keine Versionserkennung | Ob ein hochgeladenes PDF eine neue Version ist, bleibt unklar |
| P-6 | Kein Downstream-Impact | Geänderte H-Sätze lösen keine GBU-Review-Pflicht aus |

### 1.3 Auslöser

Das Sicherheitsdatenblatt CELEROL-Decklack 362-26 (Mankiewicz, Version 4, 03.01.2024)
enthält 5 Inhaltsstoffe mit jeweils eigenen CAS-Nummern, H-Sätzen und Konzentrations-
bereichen sowie AGW/DNEL/PNEC-Werte aus Abschnitt 8. Diese Daten sind objektiv —
2-Butoxyethanol (CAS 111-76-2) hat denselben AGW von 10 ppm (TRGS 900) für jeden
deutschen Arbeitgeber.

---

## 2. Entscheidungstreiber

| ID | Treiber | Gewichtung |
|----|---------|------------|
| D-1 | Datenqualität und Konsistenz | Hoch |
| D-2 | Netzwerkeffekt (SaaS-Skalierung) | Hoch |
| D-3 | Tenant-Datenisolation (DSGVO, Wettbewerb) | Kritisch |
| D-4 | Rückwärtskompatibilität zu ADR-002 | Mittel |
| D-5 | GefStoffV §7 Abs. 7: Überprüfungspflicht bei SDS-Änderungen | Kritisch |
| D-6 | Automatische Versionserkennung ohne manuelle Nutzerinteraktion | Hoch |
| D-7 | Parser-Qualität durch LLM-Qualitätscheck | Mittel |

---

## 3. Architektur-Entscheidung: Two-Layer-Schema

```
┌──────────────────────────────────────────────────────────────────────┐
│  PLATFORM LAYER  (schema: platform)  — kein tenant_id, global        │
│                                                                       │
│  Substance ──────────────── SdsRevision ◄─── superseded_by (self)   │
│  CAS als Natural Key         SHA-256 als Idempotenz-Key              │
│                              revision_date, version_number           │
│                                    │                                  │
│                             SdsComponent      SdsExposureLimit        │
│                             Inhaltsstoffe     AGW/DNEL/PNEC           │
│                                                                       │
│  Status-Flow: PENDING → VERIFIED → SUPERSEDED                        │
└──────────────────────────────────────────────────────────────────────┘
                                │
                    FK (PROTECT, read-only für Tenants)
                                │
┌──────────────────────────────────────────────────────────────────────┐
│  TENANT LAYER  (schema: tenant_{id})  — RLS-geschützt                │
│                                                                       │
│  SdsUsage                    SiteInventoryItem                        │
│  ├── FK → SdsRevision        ├── FK → Substance                      │
│  ├── approved_by (User FK)   ├── Standort, Menge                     │
│  ├── status                  └── tenant_id                           │
│  ├── pending_update_revision                                          │
│  ├── review_deadline                                                  │
│  └── update_deferred_reason                                           │
│                                                                       │
│  GBU / Ex-Schutz / Betriebsanweisung                                 │
│  └── FK → SdsUsage  (NICHT direkt SdsRevision!)                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.1 Sichtbarkeitsregel

```python
class SdsRevisionQuerySet(models.QuerySet):
    def visible_for_tenant(self, tenant_id: str) -> "SdsRevisionQuerySet":
        """
        VERIFIED/SUPERSEDED: global sichtbar (alle Tenants).
        PENDING/REJECTED: nur für den hochladenden Tenant.
        """
        return self.filter(
            Q(status__in=[SdsRevision.Status.VERIFIED, SdsRevision.Status.SUPERSEDED])
            | Q(status=SdsRevision.Status.PENDING, uploaded_by_tenant_id=tenant_id)
        )
```

### 3.2 RLS-Strategie für globale Tabellen (B-1)

Globale Tabellen haben kein `tenant_id`, müssen aber dennoch in die
Plattform-RLS integriert werden. Analog ADR-001 v5 (Hybrid-Isolation):

```sql
-- Gilt für: substances_substance, substances_sdsrevision,
--           substances_sdscomponent, substances_sdsexposurelimit

ALTER TABLE substances_substance ENABLE ROW LEVEL SECURITY;
ALTER TABLE substances_substance FORCE ROW LEVEL SECURITY;

-- SELECT: global sichtbar für alle authentifizierten DB-Verbindungen
CREATE POLICY global_sds_read ON substances_substance
    FOR SELECT USING (true);

-- INSERT: nur via Service-Account (Upload-Pipeline, Migrations)
CREATE POLICY global_sds_insert ON substances_substance
    FOR INSERT WITH CHECK (
        current_setting('app.is_service_account', true)::boolean = true
    );

-- UPDATE/DELETE: nie erlaubt (Immutabilität nach Anlage)
CREATE POLICY global_sds_no_update ON substances_substance
    FOR UPDATE USING (false);

CREATE POLICY global_sds_no_delete ON substances_substance
    FOR DELETE USING (false);
```

> **Abweichung von ADR-001:** Dort dürfen Tenants eigene Stammdaten schreiben.
> Hier schreiben **ausschließlich** Service-Accounts — da globale SDS-Daten
> nie tenant-spezifisch sind, gibt es keine Tenant-Write-Berechtigung.

> **Bewusste Abweichung von ADR-072 (Schema-Isolation):** ADR-072 empfiehlt
> Schema-pro-Tenant für neue Multi-Tenant-Apps. Globale SDS-Tabellen haben
> *kein* `tenant_id` und existieren bewusst außerhalb des Tenant-Schemas —
> sie sind Shared Infrastructure (analog `auth_user` oder `django_content_type`).
> Nur `SdsUsage` ist tenant-scoped und folgt dem ADR-072-Pattern.
> Hybrid-RLS auf globalen Tabellen ist die korrekte Strategie weil:
> 1. Schema-Isolation keinen Sinn ergibt für Daten die alle Tenants lesen sollen
> 2. `FORCE ROW LEVEL SECURITY` verhindert versehentliche Writes durch Application-Code
> 3. Service-Account-Pattern ist bereits in ADR-001 v5 etabliert

### 3.3 Schema-Ownership (B-2)

Globale Tabellen leben im `substances`-App des risk-hub mit explizitem `app_label`:

```python
# src/apps/substances/apps.py
class SubstancesConfig(AppConfig):
    name = "apps.substances"
    label = "substances"

# Globale Models bekommen ein eigenes app_label damit Migrations
# sauber trennbar bleiben:
class Substance(models.Model):
    class Meta:
        app_label = "global_sds"  # Eigene Migrations-Gruppe
        db_table = "global_sds_substance"

class SdsRevision(models.Model):
    class Meta:
        app_label = "global_sds"
        db_table = "global_sds_sdsrevision"
```

**Extraktion-Trigger:** Sobald ein zweites Hub-Produkt auf diese Daten zugreift,
werden `global_sds`-Models in `platform/packages/global-sds/` extrahiert.
Bis dahin bleibt alles im risk-hub ohne Mehraufwand.

---

## 4. Datenmodell

### 4.1 Globale Models (kein TenantModel)

```python
class Substance(models.Model):
    """Globale Gefahrstoff-Stammdaten. CAS ist natürlicher Schlüssel."""
    # BigAutoField (Django default) — ADR-022 Platform Consistency
    cas_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    cas_number_normalized = models.CharField(
        max_length=20, blank=True, db_index=True,
        help_text="CAS ohne Bindestriche/Leerzeichen — auto-generiert via save()",
    )
    ec_number = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=512)
    synonyms = models.JSONField(default=list, blank=True)
    chemical_formula = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["cas_number"])]


class SdsRevision(models.Model):
    """Versioniertes SDS — global, SHA-256 als Idempotenz-Key."""
    class Status(models.TextChoices):
        PENDING    = "PENDING",    "Ausstehend (nur Uploader)"
        VERIFIED   = "VERIFIED",   "Verifiziert (global)"
        REJECTED   = "REJECTED",   "Abgelehnt"
        SUPERSEDED = "SUPERSEDED", "Abgelöst"

    # BigAutoField (Django default) — ADR-022 Platform Consistency
    substance = models.ForeignKey(Substance, on_delete=models.PROTECT, related_name="revisions")
    source_hash = models.CharField(max_length=64, unique=True)
    superseded_by = models.OneToOneField(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="supersedes"
    )

    class Meta:
        app_label = "global_sds"
        db_table = "global_sds_sdsrevision"
        constraints = [
            # N-2: Direkte Selbstreferenz verhindern
            # Tiefere Zyklen (A→B→C→A) werden durch latest_revision() Loop-Guard abgefangen
            models.CheckConstraint(
                check=~Q(superseded_by=models.F("id")),
                name="chk_sdsrevision_no_self_supersession",
            )
        ]
        indexes = [
            models.Index(fields=["source_hash"]),
            models.Index(fields=["status", "uploaded_by_tenant_id"]),
        ]
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    uploaded_by_tenant_id = models.UUIDField(db_index=True)

    # Metadaten
    manufacturer_name = models.CharField(max_length=256, blank=True)
    product_name = models.CharField(max_length=512)
    revision_date = models.DateField(null=True, blank=True)
    version_number = models.CharField(max_length=20, blank=True)

    # Regulatorisch (Abschnitt 15)
    wgk = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_class_trgs510 = models.CharField(max_length=5, blank=True)
    voc_percent = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    voc_g_per_l = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Ex-relevant (Abschnitt 9)
    flash_point_c = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    ignition_temperature_c = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    lower_explosion_limit = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    upper_explosion_limit = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    # Parser-Qualität
    parse_confidence = models.FloatField(null=True, blank=True)
    llm_corrections = models.JSONField(default=list, blank=True)

    # CLP/GHS (Abschnitt 2)
    signal_word = models.CharField(max_length=20, blank=True)
    hazard_statements = models.ManyToManyField("HazardStatementRef", blank=True)
    precautionary_statements = models.ManyToManyField("PrecautionaryStatementRef", blank=True)
    pictograms = models.ManyToManyField("PictogramRef", blank=True)

    objects = SdsRevisionQuerySet.as_manager()

    @property
    def is_current(self) -> bool:
        return self.superseded_by_id is None and self.status == self.Status.VERIFIED


class SdsComponent(models.Model):
    """Inhaltsstoff eines Gemischs (SDS Abschnitt 3.2). Global."""
    sds_revision = models.ForeignKey(SdsRevision, on_delete=models.CASCADE,
                                     related_name="components")
    chemical_name = models.CharField(max_length=512)
    cas_number = models.CharField(max_length=20, blank=True, db_index=True)
    ec_number = models.CharField(max_length=20, blank=True)
    concentration_min = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    concentration_max = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    concentration_note = models.CharField(max_length=100, blank=True)
    hazard_statements = models.ManyToManyField("HazardStatementRef", blank=True)
    m_factor_acute = models.PositiveSmallIntegerField(null=True, blank=True)
    m_factor_chronic = models.PositiveSmallIntegerField(null=True, blank=True)


class SdsExposureLimit(models.Model):
    """AGW/DNEL/PNEC pro Inhaltsstoff (Abschnitt 8.1). Global."""
    class LimitType(models.TextChoices):
        AGW           = "AGW",    "Arbeitsplatzgrenzwert (TRGS 900)"
        STEL          = "STEL",   "Kurzzeitgrenzwert"
        TWA           = "TWA",    "Zeitgewichteter Mittelwert"
        BGW           = "BGW",    "Biologischer Grenzwert (TRGS 903)"
        DNEL_WORKER   = "DNEL_W", "DNEL Arbeitnehmer"
        DNEL_CONSUMER = "DNEL_C", "DNEL Verbraucher"
        PNEC          = "PNEC",   "PNEC Umwelt"

    class ExposureRoute(models.TextChoices):
        INHALATION = "INH",  "Einatmung"
        DERMAL     = "DERM", "Haut"
        ORAL       = "ORAL", "Oral"
        FRESH_WATER= "FW",   "Süßwasser"
        MARINE     = "MW",   "Meerwasser"
        SOIL       = "SOIL", "Boden"
        STP        = "STP",  "Abwasserkläranlage"

    component = models.ForeignKey(SdsComponent, on_delete=models.CASCADE,
                                  related_name="exposure_limits", null=True, blank=True)
    sds_revision = models.ForeignKey(SdsRevision, on_delete=models.CASCADE,
                                     related_name="exposure_limits")
    limit_type = models.CharField(max_length=10, choices=LimitType.choices)
    route = models.CharField(max_length=10, choices=ExposureRoute.choices)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=40)
    effect_type = models.CharField(max_length=100, blank=True)
    basis = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sds_revision", "component", "limit_type", "route"],
                name="unique_exposure_limit_per_component_route",
            )
        ]


class SdsRevisionDiffRecord(models.Model):
    """
    Persistierter Diff zwischen zwei globalen Revisionen (M-1).
    Wird beim Supersede einmalig durch SdsRevisionDiffService angelegt.
    Immutable nach Anlage — kein UPDATE erlaubt (RLS-Policy + keine save()-Logik).
    Ermöglicht Audit-Trail: In 5 Jahren nachvollziehbar warum GBU-Review nötig war.
    """
    old_revision = models.ForeignKey(
        SdsRevision, on_delete=models.PROTECT, related_name="diffs_as_old"
    )
    new_revision = models.ForeignKey(
        SdsRevision, on_delete=models.PROTECT, related_name="diffs_as_new"
    )
    overall_impact = models.CharField(max_length=20, choices=ImpactLevel.choices)
    field_diffs = models.JSONField()           # Serialisierte FieldDiff-Liste
    added_h_codes = models.JSONField(default=list)
    removed_h_codes = models.JSONField(default=list)
    changed_components = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "global_sds"
        db_table = "global_sds_revisiondiff"
        constraints = [
            models.UniqueConstraint(
                fields=["old_revision", "new_revision"],
                name="unique_diff_per_revision_pair",
            )
        ]
```

### 4.2 Tenant-spezifisches Model

```python
class SdsUsage(TenantModel):
    """
    Verknüpft eine globale SdsRevision mit einem Tenant.
    Enthält Freigabe-Workflow und Update-Tracking.
    ALLE EHS-Module (GBU, Ex-Schutz) referenzieren SdsUsage,
    niemals direkt SdsRevision.
    """
    class Status(models.TextChoices):
        ACTIVE           = "ACTIVE",           "Aktiv"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Wartet auf Freigabe"
        REVIEW_REQUIRED  = "REVIEW_REQUIRED",  "Überprüfung erforderlich (Safety Critical)"
        UPDATE_AVAILABLE = "UPDATE_AVAILABLE", "Update verfügbar (Regulatory)"
        SUPERSEDED       = "SUPERSEDED",       "Abgelöst"
        WITHDRAWN        = "WITHDRAWN",        "Zurückgezogen"

    sds_revision = models.ForeignKey(
        SdsRevision, on_delete=models.PROTECT,  # BetrSichV Audit-Immutabilität
        related_name="usages"
    )
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PENDING_APPROVAL)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="approved_sds_usages"
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    internal_note = models.TextField(blank=True)

    # Update-Tracking (befüllt durch SdsSupersessionService)
    pending_update_revision = models.ForeignKey(
        SdsRevision, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="pending_for_usages"
    )
    pending_update_impact = models.CharField(max_length=20, blank=True)
    review_deadline = models.DateField(null=True, blank=True)

    # Zurückstell-Nachweis — GefStoffV §7 Compliance-Dokumentation
    # Serverseitig erzwungen: defer_update() wirft ValueError wenn reason leer
    update_deferred_reason = models.TextField(blank=True)
    update_deferred_until = models.DateField(null=True, blank=True)
    update_deferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="deferred_sds_updates"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "sds_revision"],
                name="unique_sds_usage_per_tenant"
            ),
            # M-3: GefStoffV §6(4) — aktive Nutzung erfordert namentliche Freigabe
            models.CheckConstraint(
                check=(
                    ~Q(status="ACTIVE")                # Nicht ACTIVE ...
                    | Q(approved_by__isnull=False)     # ... ODER approved_by gesetzt
                ),
                name="chk_sds_usage_active_requires_approver",
            ),
        ]
```

---

## 5. Upload-Pipeline: Automatische Versions- und Identitätserkennung

Beim Upload eines PDF durchläuft das System drei Stufen in `SdsUploadPipeline`.
Erst am Ende von Stufe 3 wird der `SdsRevisionDiffService` aufgerufen.

```
PDF Upload
    │
    ▼
Stufe 1: SHA-256 Deduplizierung
    ├─ match  → STOP (bereits importiert, idempotent)
    └─ kein match → weiter
    │
    ▼
Regex-Parser → SdsParseResult (CAS, Name, Hersteller, Datum, Version, ...)
    │
    ▼
Stufe 2: Identitätsauflösung  [SdsIdentityResolver]
    ├─ CAS exact match                   conf 0.98 → bekannte Substance (auto)
    ├─ Fuzzy Name+Hersteller ≥ 0.95      conf hoch → bekannte Substance (auto)
    ├─ Fuzzy 0.70–0.95                   unsicher  → Confirmation-Queue (Nutzer)
    └─ < 0.70                            kein Match → neue Substance anlegen
    │
    ▼
Stufe 3: Versionserkennung  [SdsVersionDetector]
    ├─ revision_date neu > alt           → Supersession
    ├─ version_number neu > alt          → Supersession
    ├─ Datum/Version konfliktär          → Kuration-Queue (Admin)
    └─ erste Revision dieser Substance   → direkt VERIFIED
    │
    ▼ (nur bei Supersession)
SdsRevisionDiffService.compute_diff(old_revision, new_revision)
    │
    └─ SdsSupersessionService.supersede()
          └─ Outbox → Tenant-Notifications + GBU/Ex flaggen
```

### 5.1 Upload-Outcome-Enum

```python
class UploadOutcome(StrEnum):
    DUPLICATE       = "DUPLICATE"        # SHA-256 bekannt → Skip
    NEW_SUBSTANCE   = "NEW_SUBSTANCE"    # Neue Substanz, kein Match
    NEW_REVISION    = "NEW_REVISION"     # Neue Version einer bekannten Substanz
    CONFLICT        = "CONFLICT"         # Version unklar → manuelle Prüfung
    IDENTITY_REVIEW = "IDENTITY_REVIEW"  # Match unsicher → Nutzerbestätigung
```

### 5.2 Konfidenz-Schwellenwerte (Identitätsauflösung)

| Schwelle | Wert | Verhalten |
|----------|------|-----------|
| `CONFIDENCE_AUTO_MATCH` | 0.95 | Automatisch als neue Version akzeptiert |
| `CONFIDENCE_ASK_USER` | 0.70 | Nutzer-Bestätigung erforderlich (HTMX-View) |
| unter 0.70 | — | Neue Substance anlegen |

Konservative Schwellenwerte sind bewusst gewählt: Lieber einmal mehr fragen
als zwei verschiedene Stoffe fälschlich zusammenführen.

### 5.3 Versionserkennung — Konflikt-Fälle

| Fall | Ursache | Auflösung |
|------|---------|-----------|
| Gleiche Versionsnummer, anderer Inhalt | Hersteller-Fehler? | Kuration-Queue: Admin entscheidet |
| Neues SDS älter als bestehendes | Retrograde Upload | Nutzer bestätigt explizit |
| Datum/Version nicht parsebar | Parser-Fehler | LLM-Qualitätscheck, sonst manuelle Eingabe |

### 5.4 Identitätsauflösung durch Nutzer (HTMX-View)

Bei `IDENTITY_REVIEW` sieht der Nutzer einen Side-by-Side-Vergleich:
- Hochgeladenes SDS (Produktname, Hersteller, CAS)
- Kandidat aus DB (mit letzter bekannter Version)

Aktionen:
- **"Ja, das ist eine neue Version von X"** → Supersession wird ausgelöst
- **"Nein, das ist eine andere Substanz"** → neue `Substance` anlegen

---

## 6. SDS-Update-Lifecycle: Supersession und Impact-Klassifizierung

### 6.1 Impact-Klassifizierung

Nicht jede SDS-Änderung hat dieselbe Compliance-Relevanz. `SdsRevisionDiffService`
klassifiziert jeden Feldunterschied:

| Impact | Felder (Auswahl) | Downstream-Konsequenz |
|--------|-----------------|----------------------|
| `SAFETY_CRITICAL` | H300–H372 (neu), Flammpunkt, AGW (TRGS 900), UEG/OEG | `SdsUsage → REVIEW_REQUIRED`, 4-Wochen-Frist, GBU + Ex-Schutz flaggen |
| `REGULATORY` | WGK, Lagerklasse (TRGS 510), VOC, neue Inhaltsstoffe | `SdsUsage → UPDATE_AVAILABLE`, keine Pflichtfrist |
| `INFORMATIONAL` | Hersteller-Adresse, Formatierung, Versionsnummer ohne Inhalt | Kein Status-Wechsel, Changelog sichtbar |

Gesamtimpact = höchster Einzelimpact aller geänderten Felder.

### 6.2 Supersession-Ablauf

```
Neue SdsRevision VERIFIED
        │
        ▼
SdsRevisionDiffService.compute_diff(old, new)
        │
        ├── SAFETY_CRITICAL ─────────────────────────────────────────┐
        │                                                             │
        ├── REGULATORY ──────────────────────────────────┐           │
        │                                                │           │
        └── INFORMATIONAL                                ▼           ▼
                │                               SdsUsage.status      SdsUsage.status
                │                               UPDATE_AVAILABLE     REVIEW_REQUIRED
                │                               Outbox: low prio     review_deadline = +4W
                ▼                                                    GBU + Ex flaggen
        SdsUsage bleibt ACTIVE                                       Outbox: high prio
        Changelog sichtbar
```

### 6.3 Downstream-Flagging bei SAFETY_CRITICAL

```python
# Via SdsSupersessionService (delegiert in Module, kennt keine direkten FKs)
def _flag_gbu_assessments(self, old_revision, diff):
    HazardAssessment.objects.filter(
        sds_usage__sds_revision=old_revision,
        status__in=["APPROVED", "ACTIVE"],
    ).update(review_required=True, review_reason=...)

def _flag_ex_concepts(self, old_revision, diff):
    ExplosionConcept.objects.filter(
        substance__revisions=old_revision, status="APPROVED"
    ).update(review_required=True, review_reason=...)
```

### 6.4 Tenant-seitige Aktionen

| Aktion | Beschreibung | Compliance-Nachweis |
|--------|-------------|---------------------|
| `SdsUsageService.adopt_update()` | Neue Revision übernehmen | Outbox-Event mit `adopted_by` User-ID |
| `SdsUsageService.defer_update()` | Zurückstellen mit Pflichtbegründung | `update_deferred_reason + update_deferred_by` im Audit-Trail |

`defer_update()` wirft `ValueError` wenn `reason` leer — serverseitig erzwungen.

### 6.5 Outbox-Event-Schema (M-2)

Alle Events fließen über `emit_audit_event()` in die Outbox. Das Schema ist
verbindlich — Consumer-Services programmieren dagegen.

```python
# 1. Neue Revision global verifiziert
emit_audit_event(
    tenant_id=uploaded_by_tenant_id,
    event_type="sds.revision_verified",
    entity_type="SdsRevision",
    entity_id=str(new_revision.id),
    payload={
        "substance_cas": str,
        "product_name": str,
        "version_number": str,
        "parse_confidence": float,
    },
)

# 2. Supersession — pro betroffenem Tenant (N Outbox-Events bei N Tenants)
emit_audit_event(
    tenant_id=str(usage.tenant_id),
    event_type="sds.revision_superseded",
    entity_type="SdsUsage",
    entity_id=str(usage.id),
    payload={
        "old_revision_id": str,
        "new_revision_id": str,
        "diff_record_id": str,          # FK → SdsRevisionDiffRecord
        "impact_level": str,            # "SAFETY_CRITICAL" | "REGULATORY" | "INFORMATIONAL"
        "added_h_codes": list[str],
        "removed_h_codes": list[str],
        "requires_gbu_review": bool,
        "requires_ex_review": bool,
        "review_deadline": str | None,  # ISO 8601 oder null
    },
)

# 3. Tenant übernimmt Update
emit_audit_event(
    tenant_id=str(usage.tenant_id),
    event_type="sds.usage_update_adopted",
    entity_type="SdsUsage",
    entity_id=str(new_usage.id),
    payload={
        "old_usage_id": str,
        "new_usage_id": str,
        "adopted_by_user_id": str,
    },
)

# 4. Tenant stellt zurück — GefStoffV §7 Pflichtnachweis
emit_audit_event(
    tenant_id=str(usage.tenant_id),
    event_type="sds.usage_update_deferred",
    entity_type="SdsUsage",
    entity_id=str(usage.id),
    payload={
        "deferred_by_user_id": str,
        "reason": str,                  # Pflicht, nie leer
        "deferred_until": str,          # ISO 8601
        "impact_level": str,
    },
)
```

---

## 7. Parser-Qualitätscheck: LLM als Validator

### 7.1 Designprinzip

LLM ist kein Fallback (wird aufgerufen wenn Regex scheitert), sondern ein
**Qualitäts-Gate** (wird aufgerufen wenn Regex-Konfidenz zu niedrig ist).
Das ermöglicht einen nachvollziehbaren Audit-Trail über Korrekturen.

```
PDF
 │
 ▼
Regex-Parser (immer — schnell, deterministisch, kostenlos)
 │  overall_confidence
 ├─ ≥ 0.85 ──────────────────────────→ Ergebnis direkt verwenden
 └─ < 0.85
       │
       ▼
  LLM-Qualitätscheck
  Input: Regex-Ergebnis + SDS-Text (Abschnitte 1, 3, 8, 15)
  Prompt: "Bestätige oder korrigiere dieses Extraktionsergebnis"
       │
       ▼
  Merge mit Hysterese:
  LLM überschreibt Regex-Wert nur wenn
  LLM-Konfidenz > Regex-Konfidenz + 0.1
       │
       ▼
  SdsParseResult.llm_corrections[]  ← Audit-Trail
```

### 7.2 ParsedField mit Konfidenz-Tracking

```python
@dataclass
class ParsedField:
    value: Any
    confidence: float      # 0.0 – 1.0
    source: str            # "regex" | "llm" | "merged"

@dataclass
class SdsParseResult:
    product_name:       ParsedField
    cas_number:         ParsedField
    components:         list[ComponentData]
    regulatory:         dict[str, ParsedField]
    overall_confidence: float
    llm_corrections:    list[dict]  # {"field", "regex_value", "llm_value", "reason"}
```

### 7.3 Konfigurierbare Schwellenwerte (N-1)

Alle kritischen Zahlenwerte sind als Django-Settings ausgelagert.
Ein Betreiber könnte legitim argumentieren dass für seinen Betrieb
eine längere Frist GefStoffV §7-konform ist.

```python
# config/settings.py

# Review-Fristen
SDS_REVIEW_DEADLINE_DAYS: int = 28           # GefStoffV §7 "unverzüglich" — konservativer Default

# Parser-Qualitätsschwellen
SDS_PARSER_LLM_CONFIDENCE_THRESHOLD: float = 0.85   # Unterhalb: LLM-Qualitätscheck
SDS_PARSER_GLOBAL_PROMOTION_THRESHOLD: float = 0.90  # Unterhalb: manuelle Kuration

# Identitätsauflösung
SDS_IDENTITY_AUTO_MATCH_THRESHOLD: float = 0.95      # Oberhalb: automatischer Substanz-Match
SDS_IDENTITY_ASK_USER_THRESHOLD: float = 0.70        # Unterhalb: neue Substanz anlegen
```

---

## 8. Compliance-Dashboard

### 8.1 Funktion

Primäre Arbeitsoberfläche für den Sicherheitsbeauftragten. Zeigt alle
Überprüfungspflichten aus Hersteller-Updates mit Deadline-Ampel.

### 8.2 KPI-Kacheln

| KPI | Quelle |
|-----|--------|
| Überprüfung fällig (Safety-Critical) | `SdsUsage.status = REVIEW_REQUIRED` |
| Update verfügbar (Regulatory) | `SdsUsage.status = UPDATE_AVAILABLE` |
| GBU geflaggt | `HazardAssessment.review_required = True` |
| Aktuelle SDS | `SdsUsage.status = ACTIVE` |

### 8.3 Deadline-Ampel

| Status | Bedingung | Farbe im Dashboard |
|--------|-----------|-------------------|
| `overdue` | `review_deadline < today` | Rot |
| `soon` | `review_deadline ≤ today + 14d` | Amber |
| `ok` | `review_deadline > today + 14d` | Grau |

### 8.4 HTMX-Aktionen

| Endpoint | Beschreibung |
|----------|-------------|
| `POST /compliance/adopt/<id>/` | Neue Version übernehmen |
| `POST /compliance/defer/<id>/save/` | Zurückstellen (Pflichtbegründung) |
| `GET /compliance/diff/<id>/` | Diff-Panel laden (added/removed/changed) |

---

## 9. Test-Konzept (N-3)

ADR-002 dokumentierte 66 Tests. Dieses ADR führt erheblich mehr Logik
ein — die Mindestanforderung für Review-Freigabe:

| Komponente | Test-Typ | Mindest-Testfälle | Besondere Grenzfälle |
|---|---|---|---|
| `SdsIdentityResolver` | Unit | 8 | CAS mit Leerzeichen/Bindestriche, fehlende CAS, identischer Name anderer Hersteller |
| `SdsVersionDetector` | Unit | 10 | Datum-Gleichheit, nicht-numerische Versionsnummer, fehlendes Datum, retrograder Upload |
| `SdsRevisionDiffService` | Unit | 12 | Alle Impact-Stufen, H-Satz hinzugefügt/entfernt, leerer Diff |
| `SdsUploadPipeline` | Integration | 6 | Duplikat (SHA-256), neue Substance, neue Revision, Konflikt, Identity-Review |
| `SdsSupersessionService` | Integration | 6 | Multi-Tenant (3 Tenants betroffen), SAFETY_CRITICAL flaggt GBU, INFORMATIONAL kein Event |
| `compliance_dashboard` View | Integration | 4 | Overdue, Soon, adopt_update(), defer_update() ohne Begründung → 400 |
| RLS-Policies | DB-Test | 4 | Service-Account darf schreiben, normaler DB-User darf nicht |

---

## 10. Migration von ADR-002

**Vorgehen:** Backward-Compatible in 3 Schritten, kein Big-Bang.

### Schritt 1 — Neue globale Tabellen anlegen (ohne Entfernen)
```sql
-- Neue Tabellen mit global_sds app_label
CREATE TABLE global_sds_substance (...);
CREATE TABLE global_sds_sdsrevision (...);
CREATE TABLE global_sds_sdscomponent (...);
CREATE TABLE global_sds_sdsexposurelimit (...);
CREATE TABLE global_sds_revisiondiff (...);

-- Bridge-Spalte auf alten Tenant-Tabellen (BigAutoField → BIGINT FK)
ALTER TABLE substances_sdsrevision
    ADD COLUMN global_revision_id BIGINT REFERENCES global_sds_sdsrevision(id);
```

### Schritt 2 — Idempotenter Migrations-Command
```
python manage.py migrate_to_global_sds [--dry-run] [--force]

Logik:
  - update_or_create Substance auf CAS (natural key)
  - get_or_create SdsRevision auf source_hash
  - SdsUsage(status=ACTIVE) für jeden tenant_revision
  - Exit 1 bei Fehlern (außer --force)
```

### Schritt 3 — Alt-Tabellen droppen
Erst nach vollständiger Verifikation in Produktion, eigenem ADR-Amendment.

---

## 11. Offene Fragen

| # | Frage | Empfehlung | Status |
|---|-------|------------|--------|
| OQ-1 | Wer darf neue `Substance`-Einträge anlegen? | Upload-Pipeline: Tenant-Upload → PENDING → Auto-Promotion bei Konfidenz ≥ SDS_PARSER_GLOBAL_PROMOTION_THRESHOLD | **Gelöst durch §5 + §7.3** |
| OQ-2 | Wie wird ein fehlerhafter globaler Parse korrigiert? | Platform-Admin-Interface mit manuellem Diff-Edit + `SdsRevisionDiffRecord`-Korrektur | Offen — Follow-Up: risk-hub Issue TBD (Phase 4) |
| OQ-3 | `pdf_file` global oder per-Tenant in S3? | Global — SDS sind öffentliche Herstellerdokumente (REACH Art. 31) | Offen — Follow-Up: risk-hub Issue TBD (Phase 4) |
| OQ-4 | DSGVO: Enthält SDS personenbezogene Daten? | Nein | **Geklärt** |
| OQ-5 | Sieht Tenant A welche Stoffe Tenant B nutzt? | Nein — `SdsUsage` + `SiteInventoryItem` strikt tenant-isoliert | **Geklärt** |
| OQ-6 | 4-Wochen-Frist gesetzlich normiert? | Nicht explizit; `SDS_REVIEW_DEADLINE_DAYS=28` als konfigurierbarer Default | **Gelöst durch §7.3** |

---

## 12. Konsequenzen

### 12.1 Positiv

| # | Konsequenz |
|---|-----------|
| + | Single Source of Truth für Gefahrstoffdaten |
| + | Automatische Versionserkennung — kein manuelles Mapping nötig |
| + | Impact-Klassifizierung verhindert Alarm-Fatigue bei kosmetischen Updates |
| + | GBU und Ex-Schutz werden automatisch geflaggt bei Safety-Critical-Änderungen |
| + | `SdsRevisionDiffRecord` liefert lückenlosen Audit-Trail für Behördenprüfungen |
| + | Zurückstellungen mit Pflichtbegründung + User dokumentiert (GefStoffV §7) |
| + | `approved_by`-Constraint erzwingt GefStoffV §6(4) auf DB-Ebene |
| + | Alle Schwellenwerte per Settings konfigurierbar — kein Code-Deploy für Anpassungen |
| + | Netzwerkeffekt: jeder Upload verbessert alle Tenants |

### 12.2 Negativ / Risiken

| # | Risiko | Mitigation |
|---|--------|-----------|
| - | Datenmigration komplex | 3-Schritt, `--dry-run`, idempotent |
| - | Schlechter Parse schadet global | PENDING bleibt tenant-lokal bis Konfidenz ≥ `SDS_PARSER_GLOBAL_PROMOTION_THRESHOLD` |
| - | Fuzzy-Matching kann zwei Stoffe fälschlich mergen | Auto-Match-Schwelle 0.95; darunter Nutzer-Bestätigung |
| - | `on_delete=PROTECT` blockiert Löschung alter Revisionen | Gewünscht — BetrSichV/GefStoffV Audit-Immutabilität |
| - | Kuration-Queue kann Bottleneck werden | Auto-Promotion reduziert manuelle Arbeit erheblich |
| - | `SdsRevisionDiffRecord` wächst mit der Zeit | Kein Problem — immutable, kompakt (JSON), seltene Writes |

### 12.3 Confirmation

Compliance mit diesem ADR wird wie folgt verifiziert:

1. **BigAutoField**: `ruff` Custom-Rule + `python manage.py makemigrations --check` — kein `UUIDField(primary_key=True)` in neuen Models
2. **RLS-Policies**: DB-Integrationstest: normaler User darf nicht INSERT auf `global_sds_*` Tabellen
3. **Service-Layer**: Architecture Guardian prüft: keine `Model.objects.` Aufrufe in `views.py`
4. **Audit-Trail**: Jede Status-Transition erzeugt Outbox-Event (verifiziert durch Integration-Tests)
5. **GefStoffV §6(4)**: CheckConstraint `chk_sds_usage_active_requires_approver` — DB-Ebene erzwungen
6. **GefStoffV §7**: `defer_update()` wirft `ValueError` bei leerem `reason` — Unit-Test
7. **Drift-Detector**: `staleness_months=6`, `drift_check_paths` im Frontmatter — automatische Stale-Warnung

---

## 13. Betrachtete Optionen

### Option A: Status quo — Tenant-spezifische SDS (abgelehnt)

- **Pro:** Keine Migration, kein RLS-Aufwand, bewährtes Muster
- **Pro:** Tenant-Isolation trivial (jeder Tenant hat eigene Tabellen)
- **Contra:** Kein Netzwerkeffekt — 100 Tenants = 100× derselbe Parse-Aufwand
- **Contra:** Keine automatische Update-Erkennung bei Hersteller-Revisionen
- **Contra:** Inkonsistente Datenqualität zwischen Tenants (Parser-Bugs)

### Option B: Vollständig global ohne SdsUsage (abgelehnt)

- **Pro:** Einfachstes Datenmodell, keine Bridge-Tabelle
- **Pro:** Maximaler Netzwerkeffekt
- **Contra:** Keine tenant-spezifische Freigabe dokumentierbar — **GefStoffV §6(4) verletzt**
- **Contra:** Kein Zurückstell-Nachweis möglich — **GefStoffV §7 verletzt**
- **Contra:** Kein Audit-Trail wer wann welche Revision für welchen Betrieb freigegeben hat

### Option C: Externes SDS-Provider-API (abgelehnt)

- **Pro:** Sofort verfügbar, professionell kuratiert
- **Pro:** Kein Parser-Entwicklungsaufwand
- **Contra:** Vendor Lock-in, API-Kosten pro Abfrage
- **Contra:** Kein Offline-Betrieb möglich (z.B. Baustelle ohne Internet)
- **Contra:** Kein Einfluss auf Datenqualität und Aktualität

### Option D: **Gewählt — Two-Layer + Upload-Pipeline + Supersession-Lifecycle**

- **Pro:** Single Source of Truth mit Netzwerkeffekt
- **Pro:** GefStoffV-konforme Freigabe und Zurückstellung pro Tenant
- **Pro:** Automatische Versionserkennung und Impact-Klassifizierung
- **Pro:** Audit-Trail über `SdsRevisionDiffRecord` und Outbox-Events
- **Contra:** Datenmigration komplex (3-Schritt, Expand-Contract)
- **Contra:** Schlechter Parse schadet global (Mitigation: PENDING bis Konfidenz-Schwelle)
- **Contra:** Fuzzy-Matching-Risiko (Mitigation: konservative Schwellenwerte + Human-Review)

---

## 14. Service-Übersicht

| Service | Verantwortung |
|---------|---------------|
| `SdsUploadPipeline` | Orchestriert Stufen 1–3, gibt `UploadResult` zurück |
| `SdsIdentityResolver` | CAS-Lookup (conf 0.98) + Fuzzy-Match (conf 0.70–0.95) |
| `SdsVersionDetector` | Datum/Versionsnummer-Vergleich, Konflikt-Erkennung |
| `SdsRevisionDiffService` | Feldvergleich, H-Satz-Diff, Impact-Klassifizierung, persistiert `SdsRevisionDiffRecord` |
| `SdsSupersessionService` | Supersession-Kette, Tenant-Notifications, GBU/Ex-Flagging |
| `SdsUsageService` | `adopt_update()`, `defer_update()` mit Audit-Events |
| `SdsParserService` | PDF-Extraktion, Regex + LLM-Qualitätsgate (conf < `SDS_PARSER_LLM_CONFIDENCE_THRESHOLD`) |

---

## 15. Implementierungsplan

> **Tracking:** Siehe GitHub Issues risk-hub #9 (Epic), #10–#13 (Phasen).
> Geschätzt: ~67 SP (bereinigt nach Platform-Review).

| Phase | Issue | Deliverable | SP | Status |
|-------|-------|-------------|---:|--------|
| 0 | #10 | BigAutoField-Migration, BaseProgressService-Konsolidierung, Tenant-Middleware-Doku | 7 | ⬜ Open |
| 1.1 | #11 | `HazardStatementRef` + Seed-Command | 2 | ⬜ Open |
| 1.2 | #11 | `Substance` + `SdsRevision` + QuerySets | 3 | ⬜ Open |
| 1.3 | #11 | `SdsComponent` + `SdsExposureLimit` + `SdsRevisionDiffRecord` | 4 | ⬜ Open |
| 1.4 | #11 | `SdsPropertyDefinition` + `SdsRevisionProperty` + Seed | 3 | ⬜ Open |
| 1.5 | #11 | `SdsUsage` + RLS-Policies | 4 | ⬜ Open |
| 1.6 | #11 | `GbuHazardCategoryMapping` + Seed | 2 | ⬜ Open |
| 2.1 | #12 | `SdsIdentityResolver` mit pg_trgm | 5 | ⬜ Open |
| 2.2 | #12 | `SdsVersionDetector` | 2 | ⬜ Open |
| 2.3 | #12 | `SdsUploadPipeline` Orchestrator | 5 | ⬜ Open |
| 2.4 | #12 | `SdsRevisionDiffService` + Impact-Klassifizierung | 6 | ⬜ Open |
| 2.5 | #12 | `SdsSupersessionService` + Event-System | 5 | ⬜ Open |
| 3.1 | #13 | Progress Rail HTMX-Partial | 4 | ⬜ Open |
| 3.2 | #13 | GBU-Editor mit Progress-Service | 5 | ⬜ Open |
| 3.3 | #13 | Ex-Konzept-Editor mit Progress-Service | 5 | ⬜ Open |
| 3.4 | #13 | Compliance-Dashboard | 5 | ⬜ Open |

---

## 16. Referenzen

### Platform-ADRs
- [ADR-022: Platform Consistency Standard](./ADR-022-platform-consistency-standard.md) — BigAutoField-Pflicht
- [ADR-035: Shared Django Tenancy](./ADR-035-shared-django-tenancy.md) — Multi-Tenant-Pattern
- [ADR-041: Django Component Pattern](./ADR-041-django-component-pattern.md) — Service-Layer
- [ADR-045: Secrets Management](./ADR-045-secrets-management.md) — `decouple.config()`

### risk-hub-interne ADRs (im risk-hub Repo)
- ADR-002: Substances/SDS-Modul (wird partiell revidiert)
- ADR-003: Multi-Tenant & RBAC
- ADR-006: Audit & Compliance

### Regulierung
- REACH-Verordnung (EG) Nr. 1907/2006, Art. 31 (SDS-Pflicht)
- GefStoffV §6 (Gefahrstoffverzeichnis, Freigabe-Pflicht)
- GefStoffV §7 Abs. 7 (Überprüfungspflicht bei geänderten Arbeitsbedingungen)
- GefStoffV §14 (40-Jahre-Aufbewahrung CMR-Stoffe)
- TRGS 400 (Informationsermittlung aus SDS)
- TRGS 510 (Lagerung von Gefahrstoffen)
- CLP-Verordnung (EG) Nr. 1272/2008

### Sonstige
- Sicherheitsdatenblatt CELEROL-Decklack 362-26, Mankiewicz, Version 4, 03.01.2024
