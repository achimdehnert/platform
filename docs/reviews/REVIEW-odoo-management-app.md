# Kritischer Review: Erste Odoo Management-App

> **Reviewer:** Cascade (IT-Architekt-Perspektive)
> **Datum:** 2026-02-12
> **Gegenstand:** Konzept "Management-Interface für produktionsnahe Daten" auf Odoo
> **Input:** `docs/adr/inputs/odoo-integration.md`, Server-Setup 46.225.127.211
> **Ziel-ADR:** ADR-030

---

## Executive Summary

Das Konzept ist **strategisch sinnvoll**, hat aber **drei kritische Lücken**,
die vor der Implementierung geschlossen werden müssen:

1. **Kein konkreter Business Case definiert** — "produktionsnahe Daten" ist zu vage
2. **Datenstrategie ungeklärt** — Read-Replica vs. ETL vs. API nicht entschieden
3. **Team-Readiness für Odoo nicht validiert** — Odoo-Erfahrung im Team unklar

**Empfehlung:** ADR-030 mit konkretem Scope (eine App, eine Datenquelle) und
Proof-of-Concept vor Vollausbau.

---

## 1. Was gut ist

### 1.1 Infrastruktur steht

- Odoo-Server (46.225.127.211) ist eingerichtet und funktional
- Docker + Compose + Nginx + Certbot — gleicher Stack wie Django-Seite
- RAM-Nutzung bei 11% — massiv Headroom für erste App
- Firewall konfiguriert, SSH-Zugang funktional

### 1.2 Framework-Wahl ist plausibel

Odoo als Management/Reporting-UI macht Sinn, wenn:

- Backoffice-Views dominieren (Form/List/Kanban/Pivot/Graph — alles nativ)
- Rollen/Rechte-Verwaltung komplex ist (ir.rule, res.groups — nativ)
- Reporting/Export gebraucht wird (QWeb Reports, Pivot — nativ)
- Kein Custom-Frontend nötig ist

Für ein "Management-Interface" treffen alle vier Punkte zu.

### 1.3 Server-Trennung ist richtig

Separate Server für Django und Odoo:

- Kein Blast-Radius-Risiko
- Unabhängige Skalierung
- Sauberer Experiment-Exit möglich
- PostgreSQL-Anforderungen kollidieren nicht

### 1.4 Governance-Framework ist vorbereitet

- Shared ADRs, CI/CD-Patterns, Backup-Strategie
- `_ci-odoo.yml` Reusable Workflow existiert
- Compose-Templates + Dockerfile-Baseline vorhanden
- Framework-Guideline dokumentiert Entscheidungsmatrix

---

## 2. Kritische Lücken (Blocker)

### B-01: Kein konkreter Business Case

**Problem:** "Management-Interface für produktionsnahe Daten" beschreibt eine
Kategorie, keinen Use Case. Es fehlt:

- **Welche Daten?** (bfagent Books? risk-hub Assessments? travel-beat Trips?)
- **Welche Aktionen?** (Read-only Reporting? CRUD? Workflows/Approvals?)
- **Welche Nutzer?** (Admins? Business-User? Kunden?)
- **Welches Problem wird gelöst?** (Django Admin reicht nicht? Warum?)

**Risiko:** Ohne konkreten Scope wird die erste App zum Feature-Creep-Projekt,
das nie fertig wird und keine klare Erfolgsmessung hat.

**Empfehlung:** Einen konkreten Use Case auswählen, z. B.:

| Option | Datenquelle | Komplexität | Odoo-Fit |
| --- | --- | --- | --- |
| A: Book Factory Dashboard | bfagent (Books, Chapters, Agents) | Mittel | Hoch |
| B: Safety Assessment Manager | risk-hub (Assessments, Measures) | Hoch | Sehr hoch |
| C: Travel Story Analytics | travel-beat (Trips, Chapters, Stats) | Niedrig | Mittel |
| D: Cross-App KPI Dashboard | Alle Apps (aggregiert) | Sehr hoch | Mittel |

**Meine Empfehlung:** Option A oder B — überschaubarer Scope, klarer Mehrwert,
guter Odoo-Fit (Backoffice + Reporting + Rechte).

### B-02: Datenstrategie nicht entschieden

**Problem:** Das Input-Dokument nennt drei Optionen, ohne eine zu wählen:

1. **Read-Replica:** PostgreSQL Streaming Replication von Django-DB → Odoo-DB
2. **ETL/Sync:** Periodischer Datenabzug (Cronjob, Airflow, Custom Script)
3. **API:** Odoo ruft Django-API (DRF) in Echtzeit ab

Jede Option hat fundamental verschiedene Implikationen:

| Aspekt | Read-Replica | ETL/Sync | API |
| --- | --- | --- | --- |
| **Latenz** | Sekunden | Minuten–Stunden | Echtzeit |
| **Komplexität** | Hoch (PG Config) | Mittel (Script) | Niedrig (HTTP) |
| **Daten-Ownership** | Django besitzt | Kopie in Odoo | Django besitzt |
| **Schema-Kopplung** | Stark (gleiche Tabellen) | Mittel (Transform) | Schwach (Contract) |
| **Odoo-Models** | Foreign Tables / Views | Native Odoo Models | Transient Models |
| **Write-Back** | Nicht möglich | Kompliziert | Möglich (POST) |
| **Cross-Server** | PG Streaming nötig | Einfacher Transport | HTTP reicht |

**Risiko:** Falsche Wahl führt zu Architektur-Sackgasse:

- Read-Replica bindet Odoo an Django-Schema (Upgrade-Blocker)
- ETL ohne klaren Scope wird zum Daten-Sumpf
- API ohne Contract-Management wird fragil

**Empfehlung:** Für den ersten Use Case **API-First** (Option 3):

- Geringste Kopplung zwischen den Frameworks
- Django-DRF Endpoints existieren teilweise bereits
- Odoo kann über `requests` / External API Daten abrufen
- Späterer Wechsel zu ETL für Reporting-Workloads möglich

### B-03: Team-Readiness

**Problem:** Es gibt keinen Nachweis, dass das Team Odoo-Entwicklung beherrscht:

- Wer kennt Odoo ORM (`self.env`, Recordsets, `_inherit`)?
- Wer kann `ir.model.access.csv` + `security.xml` korrekt konfigurieren?
- Wer hat Erfahrung mit Odoo Modul-Architektur (`__manifest__.py`)?
- Wer debuggt Odoo-spezifische Probleme (Assets, QWeb, Registry)?

**Risiko:** Ohne Odoo-Expertise werden Django-Patterns 1:1 auf Odoo übertragen,
was zu unwartbarem Code führt (Anti-Pattern: "Django in Odoo-Kleidung").

**Empfehlung:**

- Ersten Use Case als **Lern-Projekt** framen (2-3 Wochen Timeframe)
- Offizielle Odoo-Tutorials durcharbeiten (insb. Module Development)
- Code-Review mit Odoo-Checkliste (Security, Manifest, Tests)

---

## 3. Signifikante Findings (kein Blocker, aber wichtig)

### S-01: Domain-Strategie fehlt

Kein DNS für Odoo-Server konfiguriert. Offene Fragen:

- `odoo.iil.pet`? `reporting.iil.pet`? Eigene Domain?
- SSL-Zertifikat erst nach DNS möglich
- Ohne Domain kein produktiver Zugang für Business-User

### S-02: Backup-Strategie unvollständig

`backup-odoo.sh` existiert, aber:

- Kein Cronjob eingerichtet
- Kein Off-Server Backup (aktuell nur lokal auf `/opt/odoo/backups/`)
- Kein Restore-Test dokumentiert

### S-03: Monitoring fehlt

- Kein Health-Check-Monitoring (UptimeRobot, Healthchecks.io o. ä.)
- Kein Log-Aggregation
- Kein Alert bei Container-Crash

### S-04: Lizenz-Entscheidung offen

Community (LGPL) vs. Enterprise nicht entschieden.
Für ein Management-Interface reicht Community in 90% der Fälle.
Enterprise nur nötig bei: Studio, Multi-Company Consolidation, Full Accounting.

---

## 4. Empfohlene Vorgehensweise

### Phase 0: Scope definieren (1 Tag)

- [ ] Konkreten Use Case wählen (B-01)
- [ ] Datenstrategie entscheiden (B-02)
- [ ] Domain festlegen (S-01)
- [ ] Lizenz bestätigen: Community (S-04)

### Phase 1: Proof-of-Concept (2 Wochen)

- [ ] Ein Odoo-Modul mit 3-5 Models
- [ ] Daten von einer Django-App via API laden
- [ ] Basis-Views (List + Form + Pivot)
- [ ] Security (2 Gruppen: Reader, Manager)
- [ ] CI grün (`_ci-odoo.yml`)
- [ ] Deployed auf 46.225.127.211

### Phase 2: Production-Ready (2 Wochen)

- [ ] Domain + SSL
- [ ] Backup-Cronjob + Off-Server Copy
- [ ] Monitoring
- [ ] User-Acceptance-Test mit echten Daten
- [ ] ADR-030 Status → Accepted

### Phase 3: Ausbau (nach Bedarf)

- [ ] Weitere Datenquellen anbinden
- [ ] ETL für Reporting-Workloads (wenn API zu langsam)
- [ ] Weitere Odoo-Module

---

## 5. Bewertung

| Kriterium | Bewertung | Begründung |
| --- | --- | --- |
| **Strategische Passung** | Gut | Dual-Framework-Ansatz ist plausibel |
| **Infrastruktur-Readiness** | Gut | Server steht, Templates vorhanden |
| **Konzept-Reife** | Mangelhaft | Zu vage, keine konkreten Use Cases |
| **Team-Readiness** | Unklar | Odoo-Expertise nicht nachgewiesen |
| **Risiko** | Mittel | Beherrschbar durch Scoping + PoC |

**Gesamtbewertung: Konzept freigeben mit Auflagen (B-01, B-02, B-03 lösen).**
