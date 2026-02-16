# ADR-038 REVIEW — DSB-Modul

**Reviewer**: Cascade (AI Architect) | **Datum**: 2026-02-16
**Referenz**: `risk-hub/src/` Production

---

## KRITISCH (Blockierend)

### F-1: `TenantAwareModel` existiert nicht in risk-hub

**Befund**: ADR nutzt `class DSBClient(TenantAwareModel)`. risk-hub erbt von `models.Model` mit explizitem `tenant_id = UUIDField(db_index=True)`.
**Risiko**: KRITISCH — ImportError, Deployment blockiert.
**Empfehlung**: `models.Model` + explizites `tenant_id`-Feld.

### F-2: Fehlende UUID-Primary-Keys

**Befund**: Kein Model definiert `id`. Django erzeugt BigAutoField. Alle risk-hub-Models verwenden UUID-PKs.
**Risiko**: KRITISCH — AuditEvent.resource_id (UUID) kann Integer-PKs nicht referenzieren.
**Empfehlung**: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`

### F-3: Fehlende `on_delete` auf ForeignKeys

**Befund**: 4 ForeignKeys ohne `on_delete` (Pflicht seit Django 2.0): tom_reference, processing_activity, confirmed_by, report.
**Risiko**: KRITISCH — Migration kann nicht erzeugt werden.
**Empfehlung**: Explizites `on_delete=PROTECT/SET_NULL/CASCADE` je nach Semantik.

### F-4: JSONField statt Normalisierung

**Befund**: `data_categories`, `data_subjects`, `recipients` als JSONField. Vorgabe: "konsequente Normalisierung".
**Risiko**: HOCH — Kein DB-Filter, keine referentielle Integrität, kein Reporting.
**Empfehlung**: Lookup-Tabellen (`dsb_data_category`, `dsb_data_subject_group`) + M2M.

---

## SCHWERWIEGEND (Hohe Priorität)

### F-5: Tenant-Hierarchie unklar — Name `DSBClient`

**Befund**: `DSBClient` = "Mandant des DSB", aber `Organization` = Tenant. Doppelte Mandantenebene.
**Risiko**: HOCH — Entwicklerverwirrung, falscher tenant_id-Filter.
**Empfehlung**: Umbenennung zu `DSBMandate`. Docstring: "Subentität, kein Tenant."

### F-6: `User`-Import statt `settings.AUTH_USER_MODEL`

**Befund**: `confirmed_by = ForeignKey(User)` — risk-hub nutzt `AUTH_USER_MODEL = "identity.User"`.
**Risiko**: HOCH — Falsches User-Model.
**Empfehlung**: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True)`

### F-7: Fehlende db_table, Constraints, Indexes

**Befund**: Kein Model hat `class Meta`. risk-hub-Pattern: explizite `db_table`, benannte Constraints, Composite-Indexes auf `[tenant_id, ...]`.
**Risiko**: HOCH — Performance, unbenannte Constraints.
**Empfehlung**: Jedes Model: `db_table = "dsb_<model>"`, Indexes, UniqueConstraints.

### F-8: Status ohne TextChoices + max_length

**Befund**: `status = CharField(choices=STATUS_CHOICES)` — undefiniert, kein max_length.
**Risiko**: MITTEL — Migration-Fehler.
**Empfehlung**: Innere `class Status(models.TextChoices)` mit max_length=20.

### F-9: `findings = JSONField()` — Normalisierung verletzt

**Befund**: Audit-Befunde als JSON statt eigenem Model. Nicht filterbar, kein Status pro Befund.
**Risiko**: HOCH — Kein "offene Befunde"-Report, keine actions-Integration.
**Empfehlung**: Eigenes Model `AuditFinding` mit FK auf PrivacyAudit.

### F-10: `deadline_72h` als Stored Field

**Befund**: Kommentiert als "Auto-calculated" aber stored. Stale bei discovered_at-Änderung.
**Risiko**: MITTEL — Falsche Fristen.
**Empfehlung**: `@property` statt Feld: `return self.discovered_at + timedelta(hours=72)`

### F-11: Fehlende created_by_id / updated_by_id

**Befund**: Architekturprinzip: "created_by, updated_by auf allen Models". ADR hat nur Timestamps.
**Risiko**: MITTEL — Keine Nachvollziehbarkeit (für DSB-Compliance kritisch).
**Empfehlung**: `created_by_id = UUIDField(null=True, blank=True)` auf allen Models.

---

## SEITENEFFEKTE

### F-12: Document.Category braucht DSB-Werte

**Befund**: Aktuell 5 Werte (brandschutz, ..., general). DSB braucht: vvt, audit_report, avv, dsfa.
**Risiko**: HOCH — Migration auf Production-Tabelle `documents_document`.
**Empfehlung**: Additive TextChoices-Erweiterung oder eigene dsb_document-Tabelle.

### F-13: Notification.Category + ApprovalWorkflow.WorkflowType erweitern

**Befund**: Beide brauchen DSB-spezifische Werte (breach_deadline, tom_approval, etc.).
**Risiko**: MITTEL — Additive Migrationen auf bestehenden Tabellen.
**Empfehlung**: Additive Erweiterung, alte Werte beibehalten.

### F-14: URL-Pattern nicht konform

**Befund**: ADR: `/dsb/clients/<id>/vvt/` (verschachtelt). risk-hub: flach (`/risk/`, `/actions/`).
**Risiko**: NIEDRIG — Inkonsistenz.
**Empfehlung**: `/dsb/`, `/dsb/mandates/`, `/dsb/vvt/`, `/dsb/audits/` (flach, Filter per Mandat).

### F-15: Cross-App FK vs. UUID-Pattern

**Befund**: ADR plant `ForeignKey("documents.Document")`. risk-hub-Pattern: `assessment_id = UUIDField()` (lose Kopplung).
**Risiko**: MITTEL — Migration-Ordering-Abhängigkeiten.
**Empfehlung**: Für cross-app: UUIDField. Für dsb-interne Refs: ForeignKey.

---

## ZUSAMMENFASSUNG

| Severity | Count | IDs                              |
|----------|------:|----------------------------------|
| KRITISCH |     3 | F-1, F-2, F-3                    |
| HOCH     |     6 | F-4, F-5, F-6, F-7, F-9, F-12   |
| MITTEL   |     5 | F-8, F-10, F-11, F-13, F-14     |
| NIEDRIG  |     1 | F-15                             |

**Verdict R1**: ADR-038 war in der Originalform **nicht implementierbar**.
3 kritische Syntaxfehler, 6 schwerwiegende Pattern-Verletzungen.
Alle R1-Befunde wurden in ADR-038-v2 eingearbeitet.

---

## REVIEW R2 — ADR-038-v2 (2026-02-16)

Systematische Prüfung der v2 gegen:
- `src/explosionsschutz/models.py` (1211 Zeilen, reifste App)
- `src/substances/models.py` (655 Zeilen, Abstract-Base-Pattern)
- `src/risk/models.py`, `src/approvals/models.py`, `src/notifications/models.py`
- Qualitätsvorgaben: DB-getrieben, konsequente Normalisierung, Naming

---

### R2-F1: Redundanter `DSB`-Prefix auf Model-Namen (Naming)

**Befund**: `DSBMandate`, `DataCategory`, `DataSubjectGroup`, `DataBreach`.
Production-Pattern: Models nutzen **kurze Namen innerhalb des App-Namespace**:
- `risk.Assessment` (nicht `RiskAssessment`)
- `explosionsschutz.Area` (nicht `ExArea`)
- `substances.Party` (nicht `SubstancesParty`)

`DSBMandate` ist redundant — die App heißt `dsb`, also `from dsb.models import Mandate`.

**Risiko**: MITTEL — Verbose Imports, inkonsistent mit Codebase.
**Empfehlung**: Rename:
- `DSBMandate` → `Mandate`
- `DataCategory` → `Category` (oder belassen, da `Category` zu generisch)
- `DataSubjectGroup` → `SubjectGroup`
- `DataBreach` → `Breach`

---

### R2-F2: 4 Models in Verzeichnisbaum definiert aber nicht spezifiziert

**Befund**: `src/dsb/models/` listet `tom.py`, `dsfa.py`, `avv.py`, `training.py`.
ADR definiert **keinen einzigen** dieser Models. `tom_reference_id` auf
ProcessingActivity referenziert ein nicht-existierendes Model.

**Risiko**: HOCH — ADR ist unvollständig. Implementierer muss raten.
**Empfehlung**: Mindestens Stub-Definitionen für Phase-1-relevante Models
(TechnicalMeasure, OrganizationalMeasure). Restliche als "Phase 4, TBD" markieren.

---

### R2-F3: `recipients` ersatzlos entfernt (Normalisierung)

**Befund**: Original hatte `recipients = JSONField()`. v2 hat das Feld
komplett entfernt. Art. 30 DSGVO verlangt die Angabe von Empfängern
("Kategorien von Empfängern") pro Verarbeitungstätigkeit.

**Risiko**: HOCH — Gesetzliche Anforderung nicht erfüllt.
**Empfehlung**: Neues Lookup-Model `Recipient` + M2M auf ProcessingActivity:
```python
class Recipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)
    class Meta:
        db_table = "dsb_recipient"
```

---

### R2-F4: `affected_data` ersatzlos entfernt aus Breach (Normalisierung)

**Befund**: Original hatte `affected_data = JSONField()`. v2 hat es entfernt.
Art. 33 Abs. 3 lit. a verlangt "Art der Verletzung des Schutzes
personenbezogener Daten" — welche Datenkategorien betroffen waren.

**Risiko**: HOCH — Art. 33 Meldung unvollständig.
**Empfehlung**: M2M auf DataCategory (bereits vorhanden):
```python
class Breach(models.Model):
    affected_categories = models.ManyToManyField(
        "Category", blank=True, related_name="breaches",
    )
```

---

### R2-F5: `legal_basis` als Freitext statt TextChoices (Normalisierung)

**Befund**: `legal_basis = CharField(max_length=100)` — Freitext.
DSGVO Art. 6 Abs. 1 hat exakt 6 Rechtsgrundlagen (lit. a-f).
Dies ist ein **geschlossenes Werteset** → muss normalisiert werden.

**Risiko**: MITTEL — "Einwilligung" vs "einwilligung" vs "Art. 6 Abs. 1 lit. a".
**Empfehlung**: TextChoices:
```python
class LegalBasis(models.TextChoices):
    CONSENT = "consent", "Art. 6(1)(a) Einwilligung"
    CONTRACT = "contract", "Art. 6(1)(b) Vertragserfüllung"
    LEGAL_OBLIGATION = "legal_obligation", "Art. 6(1)(c) Rechtliche Verpflichtung"
    VITAL_INTEREST = "vital_interest", "Art. 6(1)(d) Lebenswichtige Interessen"
    PUBLIC_INTEREST = "public_interest", "Art. 6(1)(e) Öffentliches Interesse"
    LEGITIMATE_INTEREST = "legitimate_interest", "Art. 6(1)(f) Berechtigtes Interesse"
```

---

### R2-F6: `industry` als Freitext statt Normalisierung

**Befund**: `industry = CharField(max_length=100, blank=True)`.
Führt zu "IT" vs "Informationstechnologie" vs "Software".

**Risiko**: NIEDRIG — Kein Reporting-Bruch, aber unsauber.
**Empfehlung**: TextChoices mit gängigen Branchen oder Lookup-Tabelle.

---

### R2-F7: `DeletionLog.data_category` — CharField statt FK zu DataCategory

**Befund**: Es gibt eine normalisierte `DataCategory`-Tabelle, aber
`DeletionLog.data_category` ist ein `CharField(max_length=200)`.

**Risiko**: MITTEL — Inkonsistenz. Kein Join möglich.
**Empfehlung**: `data_category = ForeignKey(DataCategory, on_delete=PROTECT)`

---

### R2-F8: Fehlende `verbose_name` / `verbose_name_plural` (Naming)

**Befund**: Kein v2-Model hat `verbose_name`. Production-Pattern
(explosionsschutz, substances): jedes Model hat deutsche verbose_names.

**Risiko**: NIEDRIG — Admin-UI zeigt englische Auto-Namen.
**Empfehlung**: Alle Models mit deutschen verbose_names:
```python
class Meta:
    verbose_name = "Mandat"
    verbose_name_plural = "Mandate"
```

---

### R2-F9: Fehlende `help_text` auf Feldern (Dokumentation)

**Befund**: Kein Feld in v2 hat `help_text`. Production-Pattern
(explosionsschutz: 40+ help_text, substances: 30+).

**Risiko**: NIEDRIG — Admin-UI ohne Erklärungen.
**Empfehlung**: Mindestens auf fachlich nicht-offensichtlichen Feldern:
`dsb_appointed_date`, `supervisory_authority`, `legal_basis`,
`tom_reference_id`, `third_country_transfer`.

---

### R2-F10: Fehlende `ordering` in Meta

**Befund**: Kein Model hat `ordering`. Production:
- `AuditEvent`: `ordering = ["-created_at"]`
- `Notification`: `ordering = ["-created_at"]`
- `ApprovalRequest`: `ordering = ["-requested_at"]`
- `Substance`: `ordering = ["name"]`

**Risiko**: NIEDRIG — Ungeordnete Querysets im Admin/Views.
**Empfehlung**:
- `Mandate`: `ordering = ["name"]`
- `PrivacyAudit`: `ordering = ["-scheduled_date"]`
- `AuditFinding`: `ordering = ["-created_at"]`
- `Breach`: `ordering = ["-discovered_at"]`

---

### R2-F11: `DeletionLog` fehlt `updated_at`

**Befund**: Alle anderen Models haben `created_at` + `updated_at`.
DeletionLog hat nur `created_at`. Aber `executed_at` wird nachträglich
gesetzt → Record wird updated.

**Risiko**: NIEDRIG — Kein Tracking wann Log aktualisiert wurde.
**Empfehlung**: `updated_at = models.DateTimeField(auto_now=True)` ergänzen.

---

### R2-F12: Cross-App FK sind in Production erlaubt

**Befund**: R1-F15 empfahl UUIDField für cross-app Referenzen.
Aber `substances.SdsRevision` nutzt
`ForeignKey("documents.DocumentVersion", on_delete=PROTECT)` in Production.

Beide Patterns existieren:
- **Loose**: `assessment_id = UUIDField()` (actions, risk)
- **Tight**: `ForeignKey("documents.DocumentVersion")` (substances)

**Risiko**: NIEDRIG — v2-Ansatz (UUIDField) ist valide, aber die
Entscheidung sollte explizit dokumentiert und begründet sein.
**Empfehlung**: Trade-off im ADR dokumentieren:
UUIDField = keine Migration-Dependency, kein DB-enforced Constraint.
ForeignKey = referentielle Integrität auf DB-Ebene.

---

### R2-F13: Lookup-Tabellen ohne tenant_id — korrekt aber undokumentiert

**Befund**: `DataCategory` und `DataSubjectGroup` haben kein `tenant_id`.
Dies folgt dem substances-Pattern (`HazardStatementRef`, `PictogramRef`
— globale Referenzdaten ohne Tenant).

DSGVO-Datenkategorien sind standardisiert → global korrekt.

**Risiko**: NIEDRIG — Aber: Tenant-spezifische Erweiterungen nicht möglich.
**Empfehlung**: Explizit im ADR dokumentieren: "Global, nicht tenant-spezifisch.
Für tenant-spezifische Erweiterungen: Hybrid-Pattern wie
`explosionsschutz.TenantScopedMasterData`."

---

## R2 ZUSAMMENFASSUNG

| Severity | Anz. | IDs                                    |
|----------|-----:|----------------------------------------|
| HOCH     |    3 | R2-F2, R2-F3, R2-F4                   |
| MITTEL   |    4 | R2-F1, R2-F5, R2-F7, R2-F12           |
| NIEDRIG  |    6 | R2-F6, R2-F8, R2-F9, R2-F10, R2-F11, R2-F13 |

**Verdict R2**: v2 hat alle kritischen R1-Befunde korrekt behoben.
3 neue HOHE Befunde:
- **R2-F2**: Unvollständige Model-Spezifikation (TOM, DSFA, AVV, Training)
- **R2-F3**: `recipients` fehlt (Art. 30 Pflichtangabe)
- **R2-F4**: `affected_data` fehlt aus Breach (Art. 33 Pflichtangabe)

Die 4 MITTLEREN und 6 NIEDRIGEN Befunde betreffen Naming-Konventionen,
Normalisierung von Freitext-Feldern, und fehlende Meta-Attribute.

**Empfehlung**: R2-F2 bis R2-F5 einarbeiten, dann Proposed-Status.
