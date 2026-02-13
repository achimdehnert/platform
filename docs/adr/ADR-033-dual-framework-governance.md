# ADR-033: Dual-Framework-Governance (Django + Odoo)

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Proposed |
| **Date**    | 2026-02-13 |
| **Author**  | Achim Dehnert |
| **Related** | ADR-022 (Platform Consistency), ADR-030 (Odoo Management App) |
| **Input**   | `docs/adr/inputs/odoo-integration.md` (2026-02-12) |

---

## 1. Context

Die Platform betreibt **7+ Django-Apps** auf einem Hetzner-Server (88.198.191.108).
Seit Februar 2026 läuft ein **Odoo 18-Server** (46.225.127.211) für neue,
ERP-nahe Business Cases.

**Problem:** Beide Frameworks haben fundamental verschiedene Patterns für ORM,
Middleware, Auth, Migrations und UI. Ohne klare Governance entstehen:

- Doppelte Abstractions die keinem Framework gerecht werden
- Falsche Framework-Wahl für neue Features
- Inkonsistente Ops-Patterns (Deploy, Backup, Monitoring)
- Wissens-Silos pro Framework

### 1.1 Koexistenz-Modell

| Entscheidung | Wert |
| ------------ | ---- |
| Django | Bleibt dauerhaft für bestehende 7+ Apps |
| Odoo | Neue Apps für ERP-nahe Business Cases |
| Team | Ein Entwicklungsteam betreut beide Frameworks |
| Zeithorizont | Dauerhaft parallel, kein Exit aus Django |

---

## 2. Decision

### 2.1 Framework-Entscheidungsmatrix

Jede neue App MUSS anhand dieser Matrix bewertet werden:

| Kriterium | Django wählen | Odoo wählen |
| --------- | ------------- | ----------- |
| UI-Typ | Custom (Tailwind + HTMX) | Standard Backoffice (Form/List/Kanban) |
| ERP-Funktionen | Nicht sinnvoll | Invoicing, CRM, Inventory nativ |
| Multi-Tenancy | Subdomain-basiert (platform-core) | res.company / Multi-DB |
| API-First | DRF + REST | JSON-RPC / REST (OCA) |
| Business Logic | Service Layer Pattern | Odoo Model Methods |
| Reporting | Custom (Charts.js, PDF) | QWeb Reports, Pivot nativ |
| Workflow | Celery + Custom | Automated Actions nativ |
| Rapid Prototyping | Django-Templates | Odoo Views + Studio |

### 2.2 Infrastruktur: Separate Server

| Aspekt | Django-Server | Odoo-Server |
| ------ | ------------- | ----------- |
| IP | 88.198.191.108 | 46.225.127.211 |
| Typ | CX (8 GB, 4 vCPU) | CPX32 (8 GB, 4 vCPU) |
| Location | nbg1, Nürnberg | nbg1-dc3, Nürnberg |
| Container | 32 (7 Django-Apps + Infra) | 2 (Odoo + PostgreSQL) |
| RAM | ~50% (3.9 GB) | ~11% (870 MB) |

**Begründung:**

1. **Blast Radius:** Zwei Business Cases = zwei Ausfalldomänen
2. **Ressourcen:** Django-Server bei 50% RAM
3. **PostgreSQL:** Odoo hat spezifische PG-Anforderungen (unaccent, Locale)
4. **Unabhängige Skalierung:** Jeder Server nach Bedarf dimensionierbar
5. **Experiment-Exit:** Server löschen ohne Cleanup auf Prod

### 2.3 Shared Governance (Framework-agnostisch)

Was über beide Frameworks geteilt wird:

| Concern | Mechanismus |
| ------- | ----------- |
| ADRs | `platform/docs/adr/` — zentral für alle Entscheidungen |
| Naming Conventions | Commit Messages, Branch Names, Modul-Namen |
| CI/CD Basis-Patterns | Docker Build → GHCR Push → SSH Deploy |
| API-Contracts | Pydantic / JSON-Schema für Inter-Service-Kommunikation |
| Infrastructure | Docker, Nginx, PostgreSQL 16, TLS (Let's Encrypt) |
| Monitoring | Health Endpoints, Structured Logging |
| Backup | pg_dump-basiert, tägliche Rotation |
| Firewall | Hetzner Firewall (TCP 22/80/443, ICMP) |
| Code Quality | Ruff Linting (ADR-022 Amendment), Gitleaks |

### 2.4 Nicht-teilbare Concerns

Diese Aspekte sind Framework-spezifisch und dürfen NICHT abstrahiert werden:

| Aspekt | Warum nicht teilbar |
| ------ | ------------------- |
| ORM Models | Django ORM und Odoo ORM fundamental inkompatibel |
| Middleware / Controller | Verschiedene Request Lifecycles |
| Template-System | Django Templates / Jinja2 vs. QWeb |
| Auth / Session | Django Auth vs. Odoo Auth (res.users) |
| Migrations | Explizit (Django) vs. Auto (Odoo ORM) |
| Context Management | contextvars + RequestContext vs. self.env |

**Anti-Patterns (verboten):**

- Shared ORM Base-Class über beide Frameworks
- Shared Middleware/Controller-Abstraktion
- Shared Context-Management-Layer
- Abstraktes Permission-System über ir.rule + Django RBAC

### 2.5 Release-Standards

| Regel | Staging | Production |
| ----- | ------- | ---------- |
| Image Tag | SHA (immutable) | semver vX.Y.Z |
| Trigger | CI success auf main | Push tag v* |
| Approval | Automatisch | Required Reviewers |
| Rollback | Tag zurücksetzen | deploy-remote.sh --rollback-to |

### 2.6 Odoo-spezifische Standards

**Compose-Design:**

| Service | Funktion | Restart |
| ------- | -------- | ------- |
| app-web | Odoo Runtime (proxy_mode, Workers) | unless-stopped |
| app-migrate | `--stop-after-init -u modules` (Profil: migration) | no |
| postgres | PostgreSQL 16 mit Healthcheck | unless-stopped |
| nginx | Reverse Proxy mit WebSocket-Support | unless-stopped |

**Deploy-Mapping (vs. Django):**

| Aspekt | Django | Odoo |
| ------ | ------ | ---- |
| Migration | `python manage.py migrate` | `--stop-after-init -u modules` |
| Health Port | 8000 | 8069 |
| Health Endpoint | `/healthz/` | `/web/login` (oder custom) |
| collectstatic | `manage.py collectstatic` | Entfällt (Odoo Assets nativ) |
| Backup | `pg_dumpall` | `pg_dump -Fc` + Filestore-Snapshot |
| Worker | Celery Worker Service | Odoo Workers (integriert) |

**Odoo Best Practices:**

- Standard-Module als Backbone, Custom nur für Differenzierung
- Modularisierung nach Domänen: pro Domäne ein Modul
- Upgrade-Fähigkeit als NFR: Vererbung statt Monkey-Patches
- `__manifest__.py` mit korrekten Abhängigkeiten
- `ir.model.access.csv` für alle Models
- `security.xml` für Record Rules

**CI für Odoo:**

- Reusable Workflow: `_ci-odoo.yml` (neu)
- Lint: Ruff auf Custom Addons
- Test: Odoo mit `--test-enable --stop-after-init`
- Build/Push: Identisch zum Django-Standard (GHCR, semver + SHA)

### 2.7 Compliance-Erweiterung (ADR-022)

Zusätzliche Checkliste für Odoo-Projekte:

```text
[ ] __manifest__.py mit korrekten Abhängigkeiten
[ ] ir.model.access.csv für alle Models
[ ] security.xml für Record Rules
[ ] Docker-Setup folgt Odoo Compose-Pattern (§2.6)
[ ] Nginx Reverse Proxy mit WebSocket-Support
[ ] CI mit ruff + pylint-odoo Linting
[ ] Backup: pg_dump -Fc + Filestore-Snapshot
[ ] Health Endpoint erreichbar
```

---

## 3. Auswirkungen auf bestehende ADRs

| ADR | Auswirkung |
| --- | ---------- |
| ADR-022 (Platform Consistency) | Compliance-Checkliste um Odoo-Sektion ergänzen |
| ADR-022 Amendment (Code Quality) | Ruff-Config gilt auch für Odoo Custom Addons |
| ADR-028 (Platform Context) | Scope explizit Django-only, kein Odoo-Anspruch |
| ADR-030 (Odoo Management App) | Erster konkreter Use Case unter ADR-033 Governance |
| ADR-010 (MCP Tool Governance) | deployment-mcp verwaltet beide Server |

---

## 4. Rejected Alternatives

### A: Mono-Server für Django + Odoo

- Django-Server bei 50% RAM, Odoo braucht weitere 1-2 GB
- PostgreSQL-Konflikte (Locale, Extensions)
- Kein Blast-Radius-Isolation

### B: Abstraktions-Layer über beide Frameworks

- ORM, Middleware, Auth sind zu verschieden
- Abstraktion wird "Lowest Common Denominator"
- Maintenance-Kosten übersteigen Nutzen

### C: Migration von Django zu Odoo

- 7+ produktive Django-Apps, Investment nicht aufgeben
- Odoo ist kein Universal-Framework (UI/UX-Grenzen)
- Koexistenz ist strategisch richtig

### D: Odoo Enterprise statt Community

- Community (LGPL) ausreichend für aktuelle Use Cases
- Enterprise nur wenn konkrete Features (Studio, BI) gebraucht
- Lizenzkosten vs. Nutzen noch nicht gerechtfertigt

---

## 5. Open Questions

| Nr | Frage | Priorität |
| -- | ----- | --------- |
| Q1 | Welche konkreten Business Cases werden in Odoo umgesetzt? | Hoch |
| Q2 | API-Kommunikation zwischen Django-Apps und Odoo? | Hoch |
| Q3 | Community vs. Enterprise Edition? | Hoch |
| Q4 | Shared Authentication (SSO) zwischen Django und Odoo? | Mittel |
| Q5 | Domain-Strategie (odoo.example.com vs. app.example.com)? | Mittel |
| Q6 | Hetzner Private Network für Inter-Server-Kommunikation? | Niedrig |
| Q7 | Backup-Rotation und Monitoring für zweiten Server? | Mittel |

---

## 6. Consequences

### Positive

- **Klare Trennlinie** zwischen Django- und Odoo-Domänen
- **Shared Governance** für Ops ohne Framework-Kopplung
- **Richtige-Tool-für-den-Job** statt One-Size-Fits-All
- **Blast-Radius-Isolation** durch separate Server
- **Bestehende Django-Apps** bleiben unangetastet

### Negative

- **Zweiter Server** = zusätzliche Infrastruktur-Kosten (~€20/Monat)
- **Skill-Split** im Team (Django + Odoo Know-how nötig)
- **Zwei CI-Pipelines** zu warten (_ci-python + _ci-odoo)
- **Monitoring-Overhead** für zweiten Server

### Neutral

- `platform-core` bleibt Django-only, kein Äquivalent für Odoo
- Odoo bringt Multi-Tenancy, RBAC, Audit nativ mit
- Inter-Service-API erst bei konkretem Bedarf implementieren

---

## 7. Changelog

| Datum | Änderung |
| ----- | -------- |
| 2026-02-13 | Initial: ADR-033 proposed based on odoo-integration.md Input |
