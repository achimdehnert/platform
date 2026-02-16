# ADR-038: DSB-Modul — Externer Datenschutzbeauftragter

**Status**: Proposed
**Datum**: 2026-02-16
**Autoren**: Achim Dehnert

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

## Entscheidung

### ✅ Empfehlung: risk-hub (schutztat.de) um DSB-App erweitern

**Kein separates Repository.** Das DSB-Modul wird als neue Django-App `src/dsb/`
innerhalb von risk-hub implementiert.

### Begründung

| Kriterium | risk-hub erweitern | Separates Repo |
|-----------|:------------------:|:--------------:|
| Multi-Tenancy | ✅ vorhanden | ❌ neu aufbauen |
| Audit Trail | ✅ vorhanden | ❌ neu aufbauen |
| Dokumentenverwaltung | ✅ `documents` App | ❌ neu aufbauen |
| Reporting/Export | ✅ `reporting` App | ❌ neu aufbauen |
| Aktionen/Workflows | ✅ `actions` + `approvals` | ❌ neu aufbauen |
| AI-Analyse | ✅ `ai_analysis` App | ❌ neu aufbauen |
| Benutzer/Rollen | ✅ `identity` + `permissions` | ❌ neu aufbauen |
| Deployment | ✅ existiert | ❌ neuer Container |
| Domäne | ✅ Compliance/Regulatorik | ✅ eigenständig |
| Branding | ✅ schutztat.de passt | ⚠️ neue Domain nötig |
| Kundenstamm | ✅ Überschneidung Arbeitsschutz↔Datenschutz | ❌ getrennt |

**Synergien**:
- Unternehmen, die einen externen DSB beauftragen, haben oft auch einen
  externen Sicherheitsbeauftragten (SiFa) → gleicher Mandant, gleiche Nutzer
- schutztat.de als Compliance-Plattform positionierbar (Arbeitsschutz + Datenschutz)
- Gemeinsame Infrastruktur: Dokumentenablage, Audit-Trail, Reporting

## Architektur

### Neue Django-App: `src/dsb/`

```text
src/dsb/
├── models/
│   ├── __init__.py
│   ├── client.py          # DSBClient (Mandant des DSB)
│   ├── vvt.py             # ProcessingActivity (Verarbeitungsverzeichnis)
│   ├── tom.py             # TechnicalMeasure, OrganizationalMeasure
│   ├── dsfa.py            # DataProtectionImpactAssessment
│   ├── deletion.py        # DeletionConcept, DeletionLog
│   ├── audit.py           # PrivacyAudit, AuditFinding
│   ├── breach.py          # DataBreach, BreachNotification
│   ├── training.py        # TrainingRecord
│   └── avv.py             # ProcessorAgreement (AVV)
├── services/
│   ├── vvt_service.py     # VVT-Verwaltung + Export
│   ├── audit_service.py   # Audit-Planung + Durchführung
│   ├── deletion_service.py # Löschfristen + Protokolle
│   ├── report_service.py  # Jahresbericht-Generierung
│   └── breach_service.py  # Datenpannen-Workflow (72h-Frist)
├── views/
│   ├── dashboard.py       # DSB-Dashboard
│   ├── vvt_views.py       # VVT CRUD
│   ├── audit_views.py     # Audit-Management
│   └── report_views.py    # Berichts-Export
├── templates/dsb/
│   ├── dashboard.html
│   ├── vvt/
│   ├── audit/
│   └── report/
├── api/
│   └── serializers.py     # DRF Serializer
├── admin.py
├── urls.py
└── apps.py
```

### Kern-Models

```python
class DSBClient(TenantAwareModel):
    """Mandant des externen Datenschutzbeauftragten."""
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    employee_count = models.IntegerField(null=True)
    dsb_appointed_date = models.DateField()
    contract_end_date = models.DateField(null=True)
    supervisory_authority = models.CharField(max_length=200)
    status = models.CharField(choices=STATUS_CHOICES)

class ProcessingActivity(TenantAwareModel):
    """Verarbeitungstätigkeit gemäß Art. 30 DSGVO (VVT)."""
    client = models.ForeignKey(DSBClient, on_delete=models.CASCADE)
    name = models.CharField(max_length=300)
    purpose = models.TextField()
    legal_basis = models.CharField(max_length=100)  # Art. 6 Abs. 1 lit. a-f
    data_categories = models.JSONField()             # Datenkategorien
    data_subjects = models.JSONField()               # Betroffene Gruppen
    recipients = models.JSONField()                  # Empfänger
    third_country_transfer = models.BooleanField(default=False)
    retention_period = models.CharField(max_length=200)
    tom_reference = models.ForeignKey("TOM", null=True)
    risk_level = models.CharField(choices=RISK_CHOICES)
    dsfa_required = models.BooleanField(default=False)

class PrivacyAudit(TenantAwareModel):
    """Datenschutz-Audit."""
    client = models.ForeignKey(DSBClient, on_delete=models.CASCADE)
    audit_type = models.CharField(choices=AUDIT_TYPE_CHOICES)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True)
    status = models.CharField(choices=AUDIT_STATUS_CHOICES)
    findings = models.JSONField(default=list)
    report = models.ForeignKey("documents.Document", null=True)

class DeletionLog(TenantAwareModel):
    """Löschprotokoll."""
    client = models.ForeignKey(DSBClient, on_delete=models.CASCADE)
    processing_activity = models.ForeignKey(ProcessingActivity)
    requested_at = models.DateTimeField()
    executed_at = models.DateTimeField(null=True)
    data_category = models.CharField(max_length=200)
    record_count = models.IntegerField(null=True)
    method = models.CharField(max_length=100)  # Löschmethode
    confirmed_by = models.ForeignKey(User, null=True)

class DataBreach(TenantAwareModel):
    """Datenpanne gemäß Art. 33 DSGVO."""
    client = models.ForeignKey(DSBClient, on_delete=models.CASCADE)
    discovered_at = models.DateTimeField()
    reported_to_authority_at = models.DateTimeField(null=True)
    deadline_72h = models.DateTimeField()  # Auto-calculated
    severity = models.CharField(choices=SEVERITY_CHOICES)
    affected_data = models.JSONField()
    affected_count = models.IntegerField(null=True)
    root_cause = models.TextField(blank=True)
    measures_taken = models.TextField(blank=True)
    notified_subjects = models.BooleanField(default=False)  # Art. 34
```

### Dashboard-Features

1. **Mandantenübersicht** — alle DSB-Kunden mit Status
2. **Fristenkalender** — Löschfristen, Audit-Termine, AVV-Laufzeiten
3. **Datenpannen-Tracker** — 72h-Frist-Countdown, Meldestatus
4. **VVT-Status** — Vollständigkeit pro Mandant
5. **Jahresbericht-Generator** — PDF-Export pro Mandant
6. **Schulungsübersicht** — ausstehende/absolvierte Schulungen

### URL-Struktur

```text
/dsb/                        → DSB-Dashboard
/dsb/clients/                → Mandantenverwaltung
/dsb/clients/<id>/vvt/       → Verarbeitungsverzeichnis
/dsb/clients/<id>/audits/    → Audit-Management
/dsb/clients/<id>/deletions/ → Löschprotokolle
/dsb/clients/<id>/breaches/  → Datenpannen
/dsb/clients/<id>/report/    → Jahresbericht
/api/dsb/                    → REST API
```

## Integration mit bestehenden risk-hub Apps

| Bestehende App  | Nutzung durch DSB-Modul                         |
|-----------------|--------------------------------------------------|
| `documents`     | VVT-Dokumente, Audit-Berichte, AVV-Verträge     |
| `actions`       | Maßnahmen aus Audits, Löschaufträge              |
| `approvals`     | Freigabe-Workflows für TOM-Änderungen            |
| `reporting`     | Jahresbericht-Templates, PDF-Export              |
| `audit`         | Audit-Trail aller DSB-Aktivitäten                |
| `notifications` | Fristenwarnungen, Datenpannen-Alerts             |
| `ai_analysis`   | TOM-Bewertung, Risiko-Einschätzung VVT          |

## Implementierungsplan

### Phase 1: Kern-Models + CRUD (1-2 Wochen)
- DSBClient, ProcessingActivity (VVT), TOM
- Basis-Views mit HTMX
- Dashboard-Grundgerüst

### Phase 2: Workflows + Fristen (1-2 Wochen)
- DeletionLog mit Fristenverwaltung
- PrivacyAudit mit Befund-Tracking
- Datenpannen-Workflow (72h-Frist)

### Phase 3: Reporting + AI (1 Woche)
- Jahresbericht-Generator (PDF)
- AI-gestützte VVT-Vorschläge
- TOM-Vollständigkeitsprüfung

### Phase 4: AVV + Schulungen (1 Woche)
- Auftragsverarbeitungsverträge
- Schulungsverwaltung + Nachweise

## Konsequenzen

### Positiv
- Sofortige Nutzung der risk-hub Infrastruktur (Tenancy, Auth, Audit, Docs)
- Einheitliche Compliance-Plattform unter schutztat.de
- Kunden-Synergie: Arbeitsschutz + Datenschutz aus einer Hand
- Keine zusätzliche Deployment-Infrastruktur

### Negativ
- risk-hub wird komplexer (mehr Apps)
- DSB-Modul muss sich an risk-hub Patterns halten
- Bei sehr unterschiedlichen Nutzerbasen könnte späteres Splitting nötig werden

### Risiken
- Scope Creep: DSB-Bereich ist groß, Phase-basierte Umsetzung wichtig
- DSGVO-Konformität der App selbst (Ironie!) → eigenes VVT für schutztat.de
