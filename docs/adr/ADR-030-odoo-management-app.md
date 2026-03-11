---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "odoo-hub: Odoo management app deployed on 46.225.127.211"
---

# ADR-030: Erste Odoo Management-App — Dual-Framework-Governance

_Einführung von Odoo als zweite Applikationsplattform neben Django, mit konkretem erstem Use Case_

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-030 |
| **Titel** | Erste Odoo Management-App — Dual-Framework-Governance |
| **Status** | Accepted (v3) |
| **Datum** | 2026-02-12 |
| **Autor** | Achim Dehnert / Cascade (IT-Architekt-Perspektive) |
| **Reviewer** | — |
| **Betrifft** | Odoo-Server (46.225.127.211), risk-hub (Schutztat), platform |
| **Related ADRs** | ADR-021 (Unified Deployment), ADR-022 (Platform Consistency), ADR-027 (Shared Backend Services), ADR-028 (Platform Context) |
| **Supersedes** | — |
| **Blocking** | — |

---

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| v1 | 2026-02-12 | Initialer Entwurf. Basiert auf Input-Dokument `docs/adr/inputs/odoo-integration.md` und Review `docs/reviews/REVIEW-odoo-management-app.md`. |
| v2 | 2026-02-12 | Scope-Entscheidung: risk-hub (Schutztat) als erste Datenquelle. Datenstrategie: API-First + Read-Replica (phasenweise). Konkrete Odoo-Models aus Django-Domain abgeleitet. DRF-API-Voraussetzungen dokumentiert. |
| v3 | 2026-02-12 | Status → **Accepted**. Phase 0 abgeschlossen. Phase 1 teilweise implementiert: schutztat_reporting deployed auf 46.225.127.211, Sync läuft, Domain + SSL aktiv. CI-Odoo-Workflow-Template erstellt. Implementierungsplan-Checkliste aktualisiert. |

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

Die Plattform umfasst **7 Django-basierte Produktions-Apps** auf einem Hetzner-Server (88.198.191.108). Alle Apps folgen dem Service-Layer-Pattern, nutzen Tailwind + HTMX für UI und werden über ein einheitliches CI/CD-Framework deployt.

Es gibt wiederkehrende Anforderungen, die Django nur mit erheblichem Custom-Aufwand erfüllt:

- **Management-Dashboards** mit Pivot/Graph/Kanban Views
- **Rollenbasierte Backoffice-UIs** für Business-User (nicht Entwickler)
- **Reporting** mit nativen Export-Funktionen (PDF, Excel)
- **Workflow-Automatisierung** mit Genehmigungsschritten

### 1.2 Probleme mit dem Status Quo

| Problem | Auswirkung |
| --- | --- |
| **P-01:** Django Admin ist für Entwickler, nicht Business-User | Business-User brauchen Custom-Views für jede Übersicht |
| **P-02:** Reporting erfordert Custom-Code | Charts.js + PDF-Templates für jede Auswertung |
| **P-03:** RBAC ist pro App individuell | Keine einheitliche Rollen/Rechte-Verwaltung über Apps |
| **P-04:** Workflow-Logik ist verstreut | Celery Tasks + Custom State Machines pro App |

### 1.3 Warum Odoo?

Odoo löst P-01 bis P-04 **nativ**:

| Concern | Django (Custom) | Odoo (Built-in) |
| --- | --- | --- |
| Business-UI | Custom Views + Templates | Form/List/Kanban/Pivot/Graph nativ |
| Reporting | Charts.js + Custom PDF | QWeb Reports + Pivot nativ |
| RBAC | Per-App CorePermission | res.groups + ir.rule deklarativ |
| Workflows | Celery + Custom States | Automated Actions + Statusbar nativ |
| Audit Trail | Custom AuditEvent | mail.tracking.value + Chatter nativ |

---

## 2. Entscheidung

### 2.1 Dual-Framework-Governance

**Wir führen Odoo als zweite gleichberechtigte Applikationsplattform ein.**

| Aspekt | Entscheidung |
| --- | --- |
| **Django** | Bleibt dauerhaft für alle bestehenden 7+ Apps |
| **Odoo** | Neue Management-/Reporting-Apps auf separatem Server |
| **Team** | Ein Entwicklungsteam betreut beide Frameworks |
| **Governance** | Gemeinsame ADRs, CI/CD-Patterns, Naming, Backup-Strategie |
| **Kein Exit aus Django** | Kein Migrations-Szenario — beide Plattformen sind dauerhaft |

### 2.2 Erste Management-App: risk-hub (Schutztat)

**Datenquelle:** risk-hub (Schutztat) — Occupational Safety SaaS

Die erste App dient als **Proof-of-Concept** für die Dual-Framework-Strategie:

- **Datenquelle:** risk-hub Django-App (88.198.191.108)
- **Domain:** Gefährdungsbeurteilungen (Assessments), Gefährdungen (Hazards), Maßnahmen (Actions)
- **Scope:** 5 Odoo-Models, Basis-Views (List/Form/Pivot/Graph), 2 Security-Gruppen
- **Ziel:** Validierung von Datenstrategie, CI/CD, Team-Readiness
- **Timeframe:** 4 Wochen (2 Wochen PoC + 2 Wochen Production-Ready)

#### Django-Quell-Models (risk-hub)

| Django Model | Tabelle | Schlüsselfelder | Odoo-Relevanz |
| --- | --- | --- | --- |
| `Assessment` | `risk_assessment` | title, category, status, tenant_id, site_id | Kern-Model: Pivot nach Status/Kategorie |
| `Hazard` | `risk_hazard` | severity, probability, risk_score, mitigation | Risikomatrix: Severity × Probability |
| `ActionItem` | `actions_action_item` | status, priority, due_date, assigned_to_id | Kanban: Offene Maßnahmen, Fälligkeit |
| `ApprovalRequest` | `approvals_request` | status, entity_type, current_step | Workflow-Tracking |
| `ApprovalDecision` | `approvals_decision` | outcome, comment, decided_by | Audit Trail |

#### Odoo-Fit (warum risk-hub?)

- **Pivot/Graph nativ:** Risk Score Matrix (Severity × Probability) als Heatmap
- **Kanban nativ:** Maßnahmen-Board (Open → In Progress → Completed)
- **Statusbar nativ:** Assessment Workflow (Draft → In Review → Approved)
- **RBAC nativ:** Leser (Sachbearbeiter) vs. Manager (Freigabe-Berechtigung)
- **Chatter nativ:** Approval-Entscheidungen als Audit Trail

### 2.3 Datenstrategie: API-First + Read-Replica (phasenweise)

**Zwei komplementäre Datenkanäle — API für Echtzeit, Read-Replica für Reporting.**

#### Phase 1: API-First (PoC)

Odoo konsumiert Daten via Django-REST-API (Scheduled Actions):

- **Geringste Kopplung** — Odoo ist nicht an Django-DB-Schema gebunden
- **Contract-basiert** — API-Versioning (`/api/v1/`) und JSON-Schema
- **Cross-Server** — HTTP zwischen 88.198.191.108 ↔ 46.225.127.211
- **Upgrade-sicher** — Django und Odoo können unabhängig migriert werden

**Voraussetzung:** DRF-API-Endpoints für risk-hub müssen erst erstellt werden
(aktuell existieren nur HTML-Views, keine REST-Endpoints für Assessments/Hazards/Actions).

#### Phase 2: Read-Replica (Reporting-Workloads)

PostgreSQL Streaming Replication von risk-hub-DB → Odoo-Server:

- **Latenz:** Sekunden (near-realtime)
- **Volumen:** Alle Datensätze, nicht nur API-Paginierung
- **Use Case:** Pivot/Graph Views über große Datenmengen
- **Odoo-Zugriff:** `dblink` oder Foreign Data Wrapper (FDW) auf Read-Replica
- **Kein Write-Back** — Read-Replica ist read-only

#### Abgrenzung der Kanäle

| Aspekt | API (Phase 1) | Read-Replica (Phase 2) |
| --- | --- | --- |
| **Latenz** | Minuten (Cron-Intervall) | Sekunden (Streaming) |
| **Datenvolumen** | Paginiert (100er Batches) | Vollständig |
| **Schema-Kopplung** | Schwach (JSON Contract) | Stark (Django-Tabellen) |
| **Odoo-Models** | Native Odoo Models (Kopie) | Foreign Tables / DB Views |
| **Write-Back** | Möglich (POST an Django) | Nicht möglich |
| **Komplexität** | Niedrig (HTTP + JSON) | Mittel (PG Streaming Config) |
| **Primär-Nutzen** | CRUD, Sync, Aktionen | Pivot, Graph, Massen-Reports |

### 2.4 Infrastruktur: Separate Server

| Aspekt | Django-Server | Odoo-Server |
| --- | --- | --- |
| **IP** | 88.198.191.108 | 46.225.127.211 |
| **Typ** | CX (8 GB, 4 vCPU) | CPX32 (8 GB, 4 vCPU) |
| **Container** | 32 (7 Apps + Infra) | 2 (Odoo + PostgreSQL) |
| **RAM** | ~50% (3.9 GB) | ~11% (870 MB) |
| **Stack** | Django 5.x + PostgreSQL 16 | Odoo 18.0 + PostgreSQL 16 |

---

## 3. Architektur

### 3.1 Datenfluss

```text
┌──────────────────────┐              ┌──────────────────────┐
│  risk-hub (Django)    │    HTTP      │   Odoo Server        │
│  88.198.191.108       │  ─────────►  │   46.225.127.211     │
│                       │  REST/JSON   │                      │
│  /api/v1/assessments/ │  (Phase 1)   │  schutztat_reporting │
│  /api/v1/hazards/     │              │                      │
│  /api/v1/actions/     │              │  ┌────────────────┐  │
│                       │              │  │ Assessment     │  │
│  PostgreSQL 16        │  PG Stream   │  │ Hazard         │  │
│  risk_hub DB          │  ─────────►  │  │ ActionItem     │  │
│  (Source of Truth)    │  (Phase 2)   │  │ ApprovalLog    │  │
│                       │              │  │ SyncLog        │  │
│                       │              │  └────────────────┘  │
│                       │              │                      │
│                       │              │  PostgreSQL 16       │
│                       │              │  odoo DB + Replica   │
└──────────────────────┘              └──────────────────────┘
```

### 3.2 Odoo-Modul-Architektur

```text
addons/
└── schutztat_reporting/
    ├── __manifest__.py              # Modul-Metadaten + Abhängigkeiten
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   ├── assessment.py            # schutztat.assessment
    │   ├── hazard.py                # schutztat.hazard
    │   ├── action_item.py           # schutztat.action.item
    │   ├── approval_log.py          # schutztat.approval.log
    │   └── sync_log.py              # schutztat.sync.log
    ├── views/
    │   ├── assessment_views.xml     # List + Form + Pivot + Graph
    │   ├── hazard_views.xml         # List + Form + Risk Matrix
    │   ├── action_item_views.xml    # List + Form + Kanban
    │   ├── approval_log_views.xml   # List (read-only)
    │   └── menu.xml                 # Top-Level Menü
    ├── security/
    │   ├── ir.model.access.csv      # Model Access Rights
    │   └── security.xml             # Gruppen + Record Rules
    ├── data/
    │   └── cron.xml                 # Scheduled Actions (Sync alle 15 Min)
    ├── report/
    │   └── assessment_report.xml    # QWeb PDF Report
    └── tests/
        ├── __init__.py
        ├── test_assessment.py
        └── test_sync.py
```

### 3.3 Odoo-Models (konkret)

```python
# addons/schutztat_reporting/models/assessment.py
from odoo import models, fields, api


class Assessment(models.Model):
    _name = "schutztat.assessment"
    _description = "Gefährdungsbeurteilung (synced from risk-hub)"
    _order = "synced_at desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    django_id = fields.Char(
        string="Django UUID", required=True, index=True, copy=False,
    )
    tenant_id = fields.Char(string="Tenant UUID", required=True, index=True)
    title = fields.Char(string="Titel", required=True, tracking=True)
    description = fields.Text(string="Beschreibung")
    category = fields.Selection(
        [
            ("brandschutz", "Brandschutz"),
            ("explosionsschutz", "Explosionsschutz"),
            ("arbeitssicherheit", "Arbeitssicherheit"),
            ("arbeitsschutz", "Arbeitsschutz"),
            ("general", "Allgemein"),
        ],
        string="Kategorie",
        default="general",
        tracking=True,
    )
    status = fields.Selection(
        [
            ("draft", "Entwurf"),
            ("in_review", "In Prüfung"),
            ("approved", "Freigegeben"),
            ("archived", "Archiviert"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    hazard_ids = fields.One2many(
        "schutztat.hazard", "assessment_id", string="Gefährdungen",
    )
    hazard_count = fields.Integer(
        compute="_compute_hazard_count", store=True,
    )
    max_risk_score = fields.Integer(
        compute="_compute_max_risk_score", store=True,
    )
    synced_at = fields.Datetime(string="Letzte Synchronisation", readonly=True)

    _sql_constraints = [
        ("django_id_uniq", "unique(django_id)", "Django UUID must be unique"),
    ]

    @api.depends("hazard_ids")
    def _compute_hazard_count(self):
        for rec in self:
            rec.hazard_count = len(rec.hazard_ids)

    @api.depends("hazard_ids.risk_score")
    def _compute_max_risk_score(self):
        for rec in self:
            scores = rec.hazard_ids.mapped("risk_score")
            rec.max_risk_score = max(scores) if scores else 0
```

```python
# addons/schutztat_reporting/models/hazard.py
from odoo import models, fields, api


class Hazard(models.Model):
    _name = "schutztat.hazard"
    _description = "Gefährdung (synced from risk-hub)"

    django_id = fields.Char(
        string="Django UUID", required=True, index=True, copy=False,
    )
    tenant_id = fields.Char(string="Tenant UUID", required=True, index=True)
    assessment_id = fields.Many2one(
        "schutztat.assessment", string="Beurteilung",
        ondelete="cascade", required=True,
    )
    title = fields.Char(string="Titel", required=True)
    description = fields.Text(string="Beschreibung")
    severity = fields.Selection(
        [(1, "Gering"), (2, "Mittel"), (3, "Hoch"),
         (4, "Sehr hoch"), (5, "Kritisch")],
        string="Schwere", default=1,
    )
    probability = fields.Selection(
        [(1, "Unwahrscheinlich"), (2, "Selten"), (3, "Gelegentlich"),
         (4, "Wahrscheinlich"), (5, "Häufig")],
        string="Wahrscheinlichkeit", default=1,
    )
    risk_score = fields.Integer(
        string="Risikobewertung", compute="_compute_risk_score", store=True,
    )
    mitigation = fields.Text(string="Schutzmaßnahme")
    synced_at = fields.Datetime(string="Letzte Synchronisation", readonly=True)

    _sql_constraints = [
        ("django_id_uniq", "unique(django_id)", "Django UUID must be unique"),
    ]

    @api.depends("severity", "probability")
    def _compute_risk_score(self):
        for rec in self:
            rec.risk_score = (rec.severity or 0) * (rec.probability or 0)
```

```python
# addons/schutztat_reporting/models/action_item.py
from odoo import models, fields


class ActionItem(models.Model):
    _name = "schutztat.action.item"
    _description = "Maßnahme (synced from risk-hub)"
    _order = "due_date asc, priority desc"

    django_id = fields.Char(
        string="Django UUID", required=True, index=True, copy=False,
    )
    tenant_id = fields.Char(string="Tenant UUID", required=True, index=True)
    title = fields.Char(string="Titel", required=True)
    description = fields.Text(string="Beschreibung")
    status = fields.Selection(
        [
            ("open", "Offen"),
            ("in_progress", "In Bearbeitung"),
            ("completed", "Erledigt"),
            ("cancelled", "Abgebrochen"),
        ],
        string="Status", default="open",
    )
    priority = fields.Selection(
        [(1, "Niedrig"), (2, "Mittel"), (3, "Hoch"), (4, "Kritisch")],
        string="Priorität", default=2,
    )
    due_date = fields.Date(string="Fälligkeitsdatum")
    is_overdue = fields.Boolean(
        compute="_compute_is_overdue", store=True,
    )
    assessment_django_id = fields.Char(string="Assessment UUID", index=True)
    hazard_django_id = fields.Char(string="Hazard UUID", index=True)
    synced_at = fields.Datetime(string="Letzte Synchronisation", readonly=True)

    _sql_constraints = [
        ("django_id_uniq", "unique(django_id)", "Django UUID must be unique"),
    ]

    def _compute_is_overdue(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_overdue = (
                rec.due_date and rec.due_date < today
                and rec.status in ("open", "in_progress")
            )
```

### 3.4 Daten-Sync-Pattern (API-First)

```python
# addons/schutztat_reporting/models/sync_log.py
from odoo import models, fields, api
import logging
import requests

_logger = logging.getLogger(__name__)

DJANGO_API_BASE = "http://88.198.191.108"


class SyncLog(models.Model):
    _name = "schutztat.sync.log"
    _description = "Sync Log (API calls to risk-hub)"
    _order = "started_at desc"

    model_name = fields.Char(required=True)
    started_at = fields.Datetime(required=True)
    finished_at = fields.Datetime()
    records_created = fields.Integer(default=0)
    records_updated = fields.Integer(default=0)
    status = fields.Selection(
        [("running", "Running"), ("done", "Done"), ("error", "Error")],
        default="running",
    )
    error_message = fields.Text()

    @api.model
    def sync_assessments(self):
        """Scheduled Action: Sync assessments from risk-hub API."""
        self._sync_model(
            model_name="schutztat.assessment",
            endpoint="/api/v1/risk/assessments/",
            field_mapping={
                "id": "django_id",
                "tenant_id": "tenant_id",
                "title": "title",
                "description": "description",
                "category": "category",
                "status": "status",
            },
        )

    @api.model
    def sync_hazards(self):
        """Scheduled Action: Sync hazards from risk-hub API."""
        self._sync_model(
            model_name="schutztat.hazard",
            endpoint="/api/v1/risk/hazards/",
            field_mapping={
                "id": "django_id",
                "tenant_id": "tenant_id",
                "title": "title",
                "description": "description",
                "severity": "severity",
                "probability": "probability",
                "mitigation": "mitigation",
            },
        )

    @api.model
    def sync_actions(self):
        """Scheduled Action: Sync action items from risk-hub API."""
        self._sync_model(
            model_name="schutztat.action.item",
            endpoint="/api/v1/actions/",
            field_mapping={
                "id": "django_id",
                "tenant_id": "tenant_id",
                "title": "title",
                "description": "description",
                "status": "status",
                "priority": "priority",
                "due_date": "due_date",
                "assessment_id": "assessment_django_id",
                "hazard_id": "hazard_django_id",
            },
        )

    def _sync_model(self, model_name, endpoint, field_mapping):
        """Generic sync: pull data from Django Ninja API (offset/limit)."""
        api_url = self.env["ir.config_parameter"].sudo().get_param(
            "schutztat.django_api_url", default=DJANGO_API_BASE,
        )
        api_key = self.env["ir.config_parameter"].sudo().get_param(
            "schutztat.django_api_key",
        )
        if not api_key:
            _logger.warning("schutztat.django_api_key not configured")
            return

        log = self.create({
            "model_name": model_name,
            "started_at": fields.Datetime.now(),
        })
        target = self.env[model_name].sudo()
        created, updated = 0, 0
        batch_size = 100

        try:
            offset = 0
            while True:
                resp = requests.get(
                    f"{api_url}{endpoint}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    params={"limit": batch_size, "offset": offset},
                    timeout=30,
                )
                resp.raise_for_status()
                items = resp.json()  # Django Ninja returns plain list

                if not items:
                    break

                for item in items:
                    vals = {
                        odoo_field: item.get(django_field)
                        for django_field, odoo_field in field_mapping.items()
                    }
                    vals["synced_at"] = fields.Datetime.now()

                    existing = target.search(
                        [("django_id", "=", vals["django_id"])], limit=1,
                    )
                    if existing:
                        existing.write(vals)
                        updated += 1
                    else:
                        target.create(vals)
                        created += 1

                offset += batch_size
                if len(items) < batch_size:
                    break

            log.write({
                "finished_at": fields.Datetime.now(),
                "records_created": created,
                "records_updated": updated,
                "status": "done",
            })
        except Exception as exc:
            log.write({
                "finished_at": fields.Datetime.now(),
                "status": "error",
                "error_message": str(exc),
            })
            _logger.exception("Sync failed for %s", model_name)
```

---

## 4. Shared Governance

### 4.1 Was Framework-übergreifend geteilt wird

| Concern | Mechanismus | Ort |
| --- | --- | --- |
| **ADRs** | Markdown | `platform/docs/adr/` |
| **CI/CD Patterns** | Reusable Workflows | `platform/.github/workflows/` |
| **Naming** | Governance-Dokument | `platform/docs/guides/FRAMEWORK-GUIDE.md` |
| **Compose Templates** | YAML | `platform/deployment/templates/odoo/` |
| **Backup-Scripts** | Bash | `platform/deployment/scripts/` |
| **Firewall-Rules** | Hetzner API | Identisches Pattern (22/80/443/ICMP) |

### 4.2 Was NICHT geteilt wird

| Aspekt | Begründung |
| --- | --- |
| **ORM Models** | Django ORM ≠ Odoo ORM |
| **Middleware** | Verschiedene Request Lifecycles |
| **Templates** | Django Templates ≠ QWeb |
| **Auth/Session** | Django Auth ≠ Odoo Auth |
| **Shared Packages** | `platform-core` bleibt Django-only |

### 4.3 Release-Standards (identisch)

| Umgebung | Image Tag | Trigger | Approval |
| --- | --- | --- | --- |
| Staging | SHA (immutable) | CI success auf main | Automatisch |
| Production | semver vX.Y.Z | Push tag v* | Required Reviewers |

---

## 5. CI/CD

### 5.1 Odoo CI Pipeline

Reusable Workflow `ci-odoo.yml` (Template in `deployment/workflows/`):

1. **Lint:** `ruff check` auf Custom Addons
2. **Test:** `odoo --test-enable --stop-after-init` gegen PostgreSQL Service
3. **Build:** Docker Image → GHCR (`ghcr.io/achimdehnert/<repo>:tag`)
4. **Deploy:** `docker compose pull && up -d --force-recreate` auf Odoo-Server

### 5.2 Deployment

Identisches Pattern wie Django (deploy-remote.sh), mit Anpassungen:

| Schritt | Django | Odoo |
| --- | --- | --- |
| Migration | `python manage.py migrate` | `compose --profile migration run --rm app-migrate` |
| Health Port | 8000 | 8069 |
| Health Endpoint | `/healthz/` | `/web/login` (oder custom `/healthz`) |
| Static | `collectstatic` | Entfällt (Odoo Assets nativ) |
| Backup | `pg_dumpall` | `pg_dump -Fc` + Filestore |

---

## 6. Security

### 6.1 Odoo-Modul Security (Pflicht)

Jedes Modul MUSS enthalten:

- `security/ir.model.access.csv` — Model-Level Access (CRUD pro Gruppe)
- `security/security.xml` — Record Rules (Row-Level Filtering)
- Mindestens 2 Gruppen: `group_reader` (read-only), `group_manager` (CRUD)

### 6.2 API-Kommunikation

- Django → Odoo: Nicht vorgesehen (Odoo initiiert Sync)
- Odoo → Django: Token-basierte Auth (`Authorization: Bearer <key>`)
- API-Keys als `ir.config_parameter` in Odoo (nicht hardcoded)
- HTTPS zwischen Servern (nach SSL-Setup)

### 6.3 Netzwerk

- Beide Server im Hetzner nbg1 Datacenter
- Kommunikation über Public IP (zunächst) oder Private Network (später)
- Firewall: Nur Ports 22, 80, 443 offen

---

## 7. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| --- | --- | --- | --- |
| **R-01:** Team hat keine Odoo-Erfahrung | Hoch | Mittel | PoC als Lern-Projekt, Odoo-Tutorials, Code-Reviews mit Checkliste |
| **R-02:** Scope Creep bei erster App | Mittel | Hoch | Strikter Scope: risk-hub only, 5 Models, 4 Wochen |
| **R-03:** API-Latenz zu hoch für Reporting | Niedrig | Mittel | Read-Replica als Phase-2 vorgesehen |
| **R-04:** Odoo-Upgrade bricht Custom Modules | Niedrig | Hoch | Nur Erweiterung/Vererbung, keine Kern-Überschreibungen |
| **R-05:** Zwei Frameworks erhöhen Wartungsaufwand | Mittel | Mittel | Shared Governance, identische CI/CD-Patterns |
| **R-06:** Security-Fehlkonfiguration in Odoo | Mittel | Hoch | Pflicht: ir.model.access.csv + security.xml, Review-Checklist |
| **R-07:** ~~risk-hub hat keine API-Endpoints~~ (gelöst) | ~~Hoch~~ | ~~Hoch~~ | Hazards-Endpoint erstellt, Pagination ergänzt |
| **R-08:** Read-Replica Schema-Kopplung | Mittel | Mittel | FDW mit DB-Views als Abstraktionsschicht, nicht direkte Tabellen |

---

## 8. Entscheidungen

### 8.1 Entschieden

| Nr | Entscheidung | Gewählt | Begründung |
| --- | --- | --- | --- |
| **D-01** | Use Case | **risk-hub (Schutztat)** | Bester Odoo-Fit: Pivot, Kanban, Statusbar, RBAC, Chatter |
| **D-02** | Datenstrategie | **API-First + Read-Replica** | API für Sync/CRUD, Replica für Massen-Reporting |
| **D-03** | Lizenz | **Community (LGPL)** | Reicht für Management-App, kein Enterprise-Lock-in |
| **D-04** | Domain | **schutztat.iil.pet** | Brand-konsistent mit Schutztat-Produkt |
| **D-05** | SSO | **Kein SSO (Phase 1)** | OAuth2 als Phase-2+ Option vorgehalten |
| **D-06** | Netzwerk | **Public IP (Phase 1)** | Private Network als Phase-2+ Option vorgehalten |

---

## 9. Implementierungsplan

### Phase 0: Voraussetzungen (1 Woche) — ✅ ABGESCHLOSSEN

**Django-Seite (risk-hub) — Django Ninja API (`/api/v1/`):**

risk-hub nutzt **Django Ninja** (nicht DRF) mit `ApiKeyAuth` (Bearer Token via `ApiKey` Model).

- [x] `GET /api/v1/risk/assessments` — List + Detail + Create + Approve
- [x] `GET /api/v1/actions` — List + Detail + Create
- [x] ApiKey-basierte Auth (Bearer Token, setzt tenant_id via Context)
- [x] Offset/Limit Pagination auf allen List-Endpoints
- [x] `GET /api/v1/risk/hazards` — List (mit assessment_id Filter) + Detail
- [x] ApiKey für Odoo Service-Account konfiguriert (ir.config_parameter)
- [ ] Tests für Hazards-Endpoint

**Infrastruktur:**

- [x] D-03 bis D-06 entschieden (Community, schutztat.iil.pet, kein SSO, Public IP)
- [x] GitHub-Repository: `schutztat-reporting` (deployed via addons/ volume)
- [x] `.env` auf Odoo-Server (46.225.127.211) konfiguriert
- [x] Domain schutztat.iil.pet + SSL (Certbot)
- [x] Firewall fw-odoo-prod (TCP 22/80/443, ICMP)

### Phase 1: Proof-of-Concept (2 Wochen) — 🚧 IN PROGRESS

**Odoo-Modul `schutztat_reporting`:**

- [x] 5 Models: Assessment, Hazard, ActionItem, ApprovalLog, SyncLog
- [x] Sync-Engine: `SyncLog._sync_model()` mit Pagination + ISO-8601 Datetime-Parsing
- [x] Scheduled Actions: 3 Crons (Assessments, Hazards, Actions) alle 15 Min
- [x] Views: List + Form für alle Models
- [ ] Views: Pivot (Assessments nach Status × Kategorie)
- [ ] Views: Graph (Risk Score Verteilung)
- [ ] Views: Kanban (ActionItems nach Status)
- [x] Security: `group_schutztat_reader` + `group_schutztat_manager`
- [x] `ir.model.access.csv` + `security.xml`
- [ ] CI grün (`ci-odoo.yml` — Template erstellt in `deployment/workflows/`)
- [x] Deployed auf 46.225.127.211

### Phase 2: Production-Ready (2 Wochen)

- [x] Domain + SSL (Certbot) — schutztat.iil.pet
- [ ] Backup-Cronjob (daily, 10 Retention) — Script: `deployment/scripts/backup-odoo.sh`
- [ ] Off-Server Backup Copy
- [ ] Health-Monitoring
- [ ] QWeb PDF Report (Assessment-Bericht)
- [ ] User-Acceptance-Test mit echten risk-hub Daten
- [ ] Read-Replica Setup (PG Streaming von risk-hub-DB)
- [x] ADR-030 Status → **Accepted**

### Phase 3: Ausbau (nach Bedarf)

- [ ] FDW/DB-Views auf Read-Replica für Massen-Reporting
- [ ] Weitere Django-Apps als Datenquellen
- [ ] Weitere Odoo-Module (Workflows, Approvals)
- [ ] SSO-Integration (OAuth2)

---

## 10. Compliance-Checkliste (ADR-022 Ergänzung)

Jedes Odoo-Modul MUSS folgende Artefakte haben:

- [ ] `__manifest__.py` mit korrekten Abhängigkeiten und Versionierung
- [ ] `security/ir.model.access.csv` für alle Models
- [ ] `security/security.xml` für Record Rules
- [ ] `tests/` mit mindestens Unit Tests für Business-Logik
- [ ] Docker-Setup folgt `deployment/templates/odoo/` Pattern
- [ ] CI Pipeline via `ci-odoo.yml`
- [ ] Backup via `deployment/scripts/backup-odoo.sh`
- [ ] Keine Kern-Überschreibungen (nur Erweiterung/Vererbung)
- [ ] Nginx Reverse Proxy mit SSL

---

## Verwandte Dokumente

- `docs/adr/inputs/odoo-integration.md` — Vollständiges Input-Dokument
- `docs/reviews/REVIEW-odoo-management-app.md` — Kritischer Review
- `docs/guides/FRAMEWORK-GUIDE.md` — Wann Odoo, wann Django, wann Hybrid
- `deployment/templates/odoo/docker-compose.prod.yml` — Odoo Compose Template
- `deployment/templates/odoo/Dockerfile` — Odoo Image Baseline
- `deployment/templates/odoo/nginx/default.conf` — Nginx Reverse Proxy
- `deployment/workflows/ci-odoo.yml` — Odoo CI Workflow Template
- `deployment/scripts/backup-odoo.sh` — DB + Filestore Backup Script
