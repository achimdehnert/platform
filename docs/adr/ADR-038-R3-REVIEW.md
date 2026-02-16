# ADR-038 R3 Review — DSB Module (models.py + admin.py)

**Reviewer**: Cascade (AI)
**Datum**: 2026-02-16
**Scope**: `risk-hub/src/dsb/models.py` (1024 Zeilen), `admin.py` (463 Zeilen)
**Referenz**: ADR-038-v2, risk-hub Patterns (risk, identity, tenancy, substances)

---

## Befunde

### F1 — CRITICAL: `tenant_id` fehlt auf ThirdCountryTransfer + RetentionRule

**Befund**: `ThirdCountryTransfer` und `RetentionRule` sind tenant-spezifische
Daten (Kinder von `ProcessingActivity`), haben aber kein `tenant_id`-Feld.

**Risiko**: Verstößt gegen **globale Projektregel §3.3** ("Every user-data model
MUST have `tenant_id = UUIDField(db_index=True)`"). Service-Layer-Queries können
nicht mit `filter(tenant_id=...)` arbeiten. Bei einer zukünftigen API oder
List-View müsste man immer über `processing_activity__tenant_id` joinen — teuer,
fehleranfällig, und inkompatibel mit dem `SubdomainTenantMiddleware`-Pattern.

**Vergleich**: `risk.Hazard` (Kind von `Assessment`) hat `tenant_id` (Zeile 91).

**Empfehlung**: `tenant_id = models.UUIDField(db_index=True)` auf beide Models.

---

### F2 — CRITICAL: Missing UniqueConstraint auf ProcessingActivity.number

**Befund**: `ProcessingActivity.number` (laufende Nr. im Mandat) hat keine
Unique-Constraint `(tenant_id, mandate, number)`. Zwei Tätigkeiten können
dieselbe Nummer erhalten.

**Risiko**: Dateninkonsistenz. VVT-Nummerierung ist rechtsverbindlich
(Art. 30 DSGVO). Doppelte Nummern machen das Verzeichnis ungültig.

**Empfehlung**: `UniqueConstraint(fields=["tenant_id", "mandate", "number"],
name="uq_dsb_vvt_number_per_mandate")` hinzufügen.

---

### F3 — CRITICAL: CASCADE auf Mandate löscht gesamtes Compliance-Archiv

**Befund**: Alle 9 tenant-spezifischen Models haben `on_delete=models.CASCADE`
zum `Mandate`. Ein versehentliches Löschen eines Mandats vernichtet:
ProcessingActivities, TOM, AVVs, Audits, Findings, DeletionLogs, Breaches.

**Risiko**: Unwiederbringlicher Datenverlust rechtsverbindlicher Compliance-
Dokumentation. DSGVO Art. 5(2) verlangt Nachweispflicht — gelöschte Daten
können nicht nachgewiesen werden.

**Empfehlung**: `on_delete=models.PROTECT` auf allen FK→Mandate. Löschung nur
über expliziten Admin-Workflow (soft-delete oder Status "terminated" + Archiv).

---

### F4 — HIGH: models.py überschreitet 500-Zeilen-Limit (1024 Zeilen)

**Befund**: Projektregel §2.1 begrenzt Dateien auf max. 500 Zeilen.
`models.py` hat 1024 Zeilen — über das Doppelte.

**Risiko**: Wartbarkeit, Code-Review-Qualität, Merge-Konflikte.

**Empfehlung**: Aufteilen in `models/` Package:
```
dsb/models/__init__.py    # re-exports
dsb/models/lookups.py     # Category, SubjectGroup, Recipient, Purpose,
                          # TomCategory, StandardRetentionPeriod (~170 Zeilen)
dsb/models/mandate.py     # Mandate (~100 Zeilen)
dsb/models/vvt.py         # ProcessingActivity, ThirdCountryTransfer,
                          # RetentionRule (~200 Zeilen)
dsb/models/tom.py         # TechnicalMeasure, OrganizationalMeasure (~140 Zeilen)
dsb/models/dpa.py         # DataProcessingAgreement (~120 Zeilen)
dsb/models/audit.py       # PrivacyAudit, AuditFinding (~120 Zeilen)
dsb/models/deletion.py    # DeletionLog (~70 Zeilen)
dsb/models/breach.py      # Breach (~90 Zeilen)
```

**Aktion**: Wird als separater Commit empfohlen, NACH den Critical Fixes.

---

### F5 — HIGH: DeletionLog.confirmed_by ist harte FK zu AUTH_USER_MODEL

**Befund**: Zeile 906–912 — `confirmed_by = ForeignKey(settings.AUTH_USER_MODEL)`.
Alle anderen User-Referenzen sind lose gekoppelt via `UUIDField`
(`created_by_id`, `responsible_user_id`, etc.).

**Risiko**: Inkonsistente Architektur. Harte FK erzeugt Migration-Dependency
auf `identity` App. Bei Cross-App-Queries entsteht ein impliziter JOIN.
Wenn ein User gelöscht wird → `SET_NULL` verliert den Audit-Trail.

**Empfehlung**: Ersetzen durch `confirmed_by_id = models.UUIDField(null=True,
blank=True)` — konsistent mit allen anderen Models.

---

### F6 — HIGH: ProcessingActivity.ordering ist ["name"] statt ["mandate", "number"]

**Befund**: `Meta.ordering = ["name"]` (Zeile 365). Ein VVT wird aber
gesetzlich nach Mandate + Nummer sortiert, nicht alphabetisch.

**Risiko**: Default-Queries liefern falsche Reihenfolge. `__str__` zeigt
`"1. Bewerbermanagement"` — die Nummer impliziert numerische Sortierung.

**Empfehlung**: `ordering = ["mandate", "number"]`.

---

### F7 — MEDIUM: Duplizierte Status-TextChoices (TOM)

**Befund**: `TechnicalMeasure.Status` und `OrganizationalMeasure.Status` sind
identisch (planned/implemented/verified/obsolete). Ebenso `AuditFinding.Severity`
und `Breach.Severity` (low/medium/high/critical).

**Risiko**: Drift bei Änderung. DRY-Verstoß.

**Empfehlung**: Modul-level `MeasureStatus` und `SeverityLevel` extrahieren.

---

### F8 — MEDIUM: RetentionRuleInline fehlt `standard_period`

**Befund**: `RetentionRuleInline.fields` (admin.py Zeile 44) enthält nicht
das neu hinzugefügte `standard_period` FK-Feld.

**Risiko**: Admin-User können die Referenz auf Löschfristen-Stammdaten nicht
setzen — der Hauptzweck des FK wird nicht nutzbar.

**Empfehlung**: `standard_period` in `fields` aufnehmen.

---

### F9 — MEDIUM: PrivacyAudit fehlt title/scope Feld

**Befund**: `PrivacyAudit` hat `audit_type`, `scheduled_date`, `status`, aber
kein `title` oder `scope`. `__str__` liefert nur `"Intern @ 2026-02-16"`.

**Risiko**: Bei mehreren Audits pro Monat keine Unterscheidung möglich.
Admin-Liste zeigt identische Einträge.

**Empfehlung**: `title = CharField(max_length=300)` hinzufügen.

---

### F10 — MEDIUM: Breach.is_overdue — Lazy Import von timezone

**Befund**: `from django.utils import timezone` wird innerhalb der
`is_overdue` Property importiert (Zeile 1018).

**Risiko**: Kein technisches Risiko, aber verstößt gegen Code-Style-Regel
("Imports must always be at the top of the file").

**Empfehlung**: Import an Dateianfang verschieben.

---

### F11 — LOW: apps.py redundantes default_auto_field

**Befund**: `DsbConfig.default_auto_field = "django.db.models.BigAutoField"` —
identisch mit `settings.DEFAULT_AUTO_FIELD` (Zeile 96). Alle Models definieren
explizit `id = UUIDField(...)`.

**Risiko**: Kein funktionales Risiko. Noise.

**Empfehlung**: Zeile entfernen.

---

## Zusammenfassung

| # | Severity | Befund | Fix-Aufwand |
|---|----------|--------|-------------|
| F1 | CRITICAL | tenant_id fehlt auf 2 Child-Models | minimal |
| F2 | CRITICAL | UniqueConstraint number fehlt | minimal |
| F3 | CRITICAL | CASCADE→Mandate löscht Compliance-Archiv | minimal |
| F4 | HIGH | models.py > 500 Zeilen | mittel |
| F5 | HIGH | DeletionLog.confirmed_by harte FK | minimal |
| F6 | HIGH | ProcessingActivity.ordering falsch | minimal |
| F7 | MEDIUM | Duplizierte TextChoices | gering |
| F8 | MEDIUM | RetentionRuleInline fehlt standard_period | minimal |
| F9 | MEDIUM | PrivacyAudit fehlt title | minimal |
| F10 | MEDIUM | Lazy import timezone | minimal |
| F11 | LOW | Redundantes default_auto_field | minimal |

**Empfehlung**: F1–F3 + F5–F6 + F8–F10 als ein Commit fixen (minimaler Diff).
F4 + F7 als separater Refactoring-Commit.
