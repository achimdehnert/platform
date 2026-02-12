# Framework Guideline: Odoo vs. Django vs. Hybrid

> **Status:** Active
> **Version:** 1.0
> **Datum:** 2026-02-12
> **Basis:** ADR-029 Input (Odoo Integration)

---

## Zweck

Wir betreiben Odoo und Django als gleichberechtigte Frameworks.
Das Team liefert Business-Applikationen mit einheitlichen Standards
für CI/CD, Security und Betrieb.

---

## 1. Wann Odoo?

Wähle **Odoo**, wenn mindestens 3 zutreffen:

- Backoffice/Management UI dominiert (Form/List/Kanban/Pivot/Graph)
- Rollen/Rechte, Freigaben, Workflows sind Kern
- Datenmodell-getriebene App: schnelle UI-Erstellung wichtiger als Custom UX
- ERP-nahe Domäne / Stammdaten / Prozessketten
- Customizing pro Kunde über Module soll schnell und sicher sein

**Typische Cases:**

- Reporting- und Management-Interfaces (prod-nah, read-only/ETL)
- Backoffice-Prozess-Apps (Genehmigungen, Dokumente, operative Steuerung)
- Branchenlösungen auf ERP-Backbone

---

## 2. Wann Django?

Wähle **Django**, wenn mindestens 3 zutreffen:

- API-first / Integrationshub / Services / event-driven
- Stark individuelles UX/Frontend (React/Vue), Odoo UI-Pattern passt nicht
- Realtime/Streaming/Performance-Patterns dominieren
- Strikte Architekturvorgaben (Clean Architecture / DDD) im Vordergrund
- Horizontales Scaling, Worker/Queue Patterns sind zentral

**Typische Cases:**

- Produktnahe Services/APIs
- Integrationsplattformen, Konnektoren
- Portale mit eigener UX

---

## 3. Wann Hybrid?

Hybrid ist erlaubt, wenn:

- Django liefert Daten/Integration/Processing
- Odoo liefert Management UI + Security + Workflow + Reporting
- Kopplung über stabile Schnittstellen: API, Events, ETL/Read-Model
- **Kein** direkter Zugriff Odoo auf Django-Prod-DB (außer explizit read-only Replica)

**Typische Cases:**

- Django erzeugt Read-Models/Aggregationen, Odoo zeigt sie an
- Odoo nutzt Django-API als Datenquelle (versioniert, rate-limited)
- Odoo als Admin/Backoffice für mehrere Django-Services

---

## 4. Gemeinsame Delivery Standards (verbindlich)

### 4.1 Build once, deploy many

- Release = immutable Container Image
- Deploy setzt nur `IMAGE_TAG` in `.env.prod`

### 4.2 Tagging und Releases

| Umgebung | Tag-Typ | Beispiel |
| --- | --- | --- |
| Staging | SHA (immutable) | `a1b2c3d4e5f6...` |
| Production | semver | `v1.2.3` |

- `latest` nur auf default branch, **nie** in Production referenzieren

### 4.3 GitHub Environments

- **staging:** Auto-Deploy nach CI success auf main
- **production:** Approval required + CI success gate

### 4.4 Migration und Rollback

- Migrations laufen **vor** Restart (expand-only)
- Bei Migration-Fail: kein Restart (Exit Code 4)
- Bei Healthcheck-Fail: automatischer Rollback auf `PREV_TAG`

---

## 5. Odoo Betriebsprinzipien

- DB + Filestore sind stateful — Backups müssen **beides** abdecken
- Modul-Upgrades via `compose --profile migration run --rm app-migrate`
- Healthcheck muss mehr als HTTP 200 prüfen (mind. Registry/DB erreichbar)
- Keine Kern-Überschreibungen — nur Erweiterung/Vererbung
- `--stop-after-init` für Migrations-Container (kein Runtime-Start)

---

## 6. Django Betriebsprinzipien

- Migration via `python manage.py migrate` im neuen Image vor Restart
- Static Handling ist Teil des Releaseprozesses (`collectstatic`)
- Service Layer Pattern: Views -> Services -> Models
- Worker als separater Celery-Container

---

## 7. Team-Modell

### Rollen

- **Platform Owners (2-3):** CI/CD Templates, deploy-remote, Infra, Monitoring
- **Framework Leads:**
  - Odoo Lead: Modul-Architektur, Upgrade-Disziplin, Security/Record Rules
  - Django Lead: API/Service Patterns, Migrations, Worker, Integration
- **Projekt-Engineer (rotierend):** Business Features, Tests, Releases

### Review-Regeln

- Odoo-PRs: mindestens ein Odoo Lead Review bei Models/Security/Upgrade
- Django-PRs: mindestens ein Django Lead Review bei DB/Infra/API
- Deploy-/Template-Änderungen: Platform Owner Review erforderlich

---

## 8. Templates

| Framework | Compose | CI | Dockerfile | Backup |
| --- | --- | --- | --- | --- |
| **Django** | Standard-Template | `_ci-python.yml` | App-spezifisch | `pg_dumpall` |
| **Odoo** | `deployment/templates/odoo/` | `_ci-odoo.yml` | `deployment/templates/odoo/Dockerfile` | `backup-odoo.sh` (DB + Filestore) |

---

## Verwandte Dokumente

- `docs/adr/inputs/odoo-integration.md` — ADR-029 Input-Dokument
- `docs/adr/ADR-022-platform-consistency-standard.md` — Compliance-Checkliste
- `deployment/README.md` — Deploy-Framework Dokumentation
