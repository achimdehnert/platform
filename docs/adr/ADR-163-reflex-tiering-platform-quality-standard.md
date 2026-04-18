---
parent: Decisions
nav_order: 163
title: "ADR-163: Adopt Three-Tier REFLEX Quality Standard for All Platform Repositories"
status: accepted
date: 2026-04-17
amended: 2026-04-18
deciders: Achim Dehnert
consulted: Cascade AI
informed: []
related: ["ADR-058-testing-conventions.md", "ADR-162-reflex-ui-testing-and-scraping.md"]
implementation_status: partial
implementation_evidence:
  - "iil-reflex/reflex/scaffold.py — reflex init --tier 1|2 (Phase 1)"
  - "iil-reflex/reflex/platform_runner.py — reflex platform (Phase 4)"
  - "iil-reflex/reflex/dashboard.py — reflex dashboard (Phase 4 bonus)"
  - "platform/platform-reflex.yaml — 21 hubs registered (Phase 4)"
  - "iil-reflex v0.5.0 released with all CLI commands"
---

# Adopt Three-Tier REFLEX Quality Standard for All Platform Repositories

<!-- Drift-Detector-Felder
staleness_months: 12
drift_check_paths:
  - "*/reflex.yaml"
  - iil-reflex/reflex/
  - platform/docs/adr/ADR-163-*
supersedes_check: false
-->

---

## 1. Context and Problem Statement

### 1.1 Ausgangslage

Die Platform umfasst 37 Repositories in drei Kategorien:

| Kategorie | Anzahl | Beispiele |
|-----------|--------|-----------|
| Django-Apps | 21 | risk-hub, writing-hub, cad-hub, travel-beat, coach-hub |
| PyPI-Packages | 12 | aifw, promptfw, learnfw, authoringfw, nl2cad |
| Infra-Repos | 4 | platform, mcp-hub, infra-deploy, iil-relaunch |

ADR-162 definierte REFLEX als Standard-Methodik. Das Package `iil-reflex` (v0.3.0)
implementiert: DomainAgent, UCQualityChecker, FailureClassifier, UCDialogEngine,
PermissionRunner, CycleRunner und 10 CLI-Kommandos.

### 1.2 Problem / Lücken

**P-1 — Fragmentierte Adoption.**
Nur risk-hub hat ein vollständiges `reflex.yaml` mit Use Cases und Permission-Matrix.
writing-hub hat ein partielles `reflex.yaml`. Die übrigen 19 Django-Apps haben
kein `reflex.yaml` — Route-Fehler, Permission-Lücken und Health-Probleme werden
erst in Production entdeckt.

**P-2 — Fehlende Differenzierung.**
ADR-162 beschreibt die Methodik, definiert aber nicht welche Repos sie in welchem
Umfang nutzen müssen. REFLEX auf PyPI-Packages (aifw, promptfw) oder Infra-Repos
(platform, mcp-hub) anzuwenden wäre Aufwand ohne Nutzen — diese haben keine UI,
keine Routes, keine Permissions.

**P-3 — Kein Platform-weiter Überblick.**
Es gibt keinen konsolidierten Report über den Qualitätszustand aller Apps.
Jeder Hub wird isoliert betrachtet.

### 1.3 Constraints

- Onboarding pro App muss in < 5 Minuten möglich sein (Scaffold-Befehl)
- Packages und Infra-Repos dürfen nicht belastet werden
- Bestehende CI/CD-Pipelines (pytest, ruff, GitHub Actions) bleiben unverändert
- REFLEX ergänzt, ersetzt nicht

---

## 2. Decision Drivers

- **D-01**: Alle 21 Django-Apps müssen mindestens Health- und Route-Monitoring haben
- **D-02**: Aufwand muss proportional zum Risiko sein — Packages ohne UI brauchen kein REFLEX
- **D-03**: Onboarding < 5 Minuten pro App (Scaffold-Befehl)
- **D-04**: Konsolidierter Platform-Report statt isolierter Einzelprüfungen
- **D-05**: Bestehende CI/CD-Pipelines bleiben unverändert

---

## 3. Considered Options

### Option A: Kein Tiering — REFLEX für alle 37 Repos

- *Good*: Einheitlich, einfach zu erklären
- *Bad*: 16 Repos haben keine UI → Aufwand ohne Nutzen
- *Bad*: PyPI-Packages werden mit UI-Methodik belastet

### Option B: Kein Tiering — REFLEX nur für explizit markierte Repos

- *Good*: Maximal flexibel
- *Bad*: Kein Standard, jede App entscheidet selbst → Adoption bleibt bei 1-2 Repos

### Option C: Zwei Tiers (Full + None)

- *Good*: Einfacher als drei Tiers
- *Bad*: 13 Apps ohne komplexe UI aber mit Docker-Deployment hätten gar kein Monitoring → P-1 bleibt

### Option D: Drei Tiers (Full + Light + None) — **gewählt**

- *Good*: Proportionaler Aufwand — alle Django-Apps haben Baseline
- *Good*: Packages unbelastet
- *Good*: Upgrade-Pfad: Tier 2 → Tier 1 wenn App wächst
- *Bad*: Tier-Zuordnung muss bei neuen Repos entschieden werden (mitigiert durch klare Kriterien §4.1)

---

## 4. Decision Outcome

**Gewählt: Option D — Drei Tiers (Full + Light + None)**

Begründung: Proportionaler Aufwand bei maximaler Abdeckung.

### 4.1 Tier-Kriterien

| Tier | Kriterium | Pflicht-Artefakte |
|------|-----------|-------------------|
| **Tier 1 — Full Reflex** | App hat Endkunden-UI, Login-System, rollenbasierte Permissions | `reflex.yaml` (voll), `docs/use-cases/*.md`, Permission-Matrix, `reflex verify` + `reflex test-permissions` grün vor Deploy |
| **Tier 2 — Reflex Light** | App hat Docker-Deployment aber keine komplexe Endkunden-UI oder befindet sich in früher Phase | `reflex.yaml` (light: `test_routes` + `dev_cycle`), `reflex verify` grün vor Deploy |
| **Tier 3 — Kein Reflex** | Repo hat keine UI, keine Routes, kein Docker-Deployment | pytest + ruff genügen, kein `reflex.yaml` nötig |

### 4.2 Tier-Zuordnung (Stand 2026-04-17)

**Tier 1 — Full Reflex (8 Apps)**

| App | Vertical | Production-URL | Status |
|-----|----------|---------------|--------|
| risk-hub | chemical_safety | schutztat.de | ✅ reflex.yaml vorhanden |
| writing-hub | creative_writing | writing.iil.pet | 🔶 reflex.yaml teilweise |
| cad-hub | engineering | cad.iil.pet | ⬜ Onboarding ausstehend |
| travel-beat | travel | travel-beat.iil.pet | ⬜ Onboarding ausstehend |
| coach-hub | coaching | coach.iil.pet | ⬜ Onboarding ausstehend |
| wedding-hub | events | wedding.iil.pet | ⬜ Onboarding ausstehend |
| pptx-hub | presentations | pptx.iil.pet | ⬜ Onboarding ausstehend |
| recruiting-hub | recruiting | recruiting.iil.pet | ⬜ Onboarding ausstehend |

**Tier 2 — Reflex Light (13 Apps)**

| App | Grund für Tier 2 |
|-----|-------------------|
| trading-hub | Interne Analytics-UI |
| billing-hub | Backend-fokussiert, minimale UI |
| weltenhub | Content-Management intern |
| bfagent | Agent-Tool, kein klassisches Web-UI |
| ausschreibungs-hub | Frühe Entwicklungsphase |
| research-hub | Intern |
| learn-hub | Intern |
| illustration-hub | Pipeline-Tool |
| odoo-hub | Odoo-Wrapper |
| 137-hub | Nischenanwendung |
| dev-hub | Entwickler-intern |
| tax-hub | Frühe Entwicklungsphase |
| lastwar-bot | Bot ohne Web-UI |

**Tier 3 — Kein Reflex (16 Repos)**

aifw, promptfw, learnfw, authoringfw, weltenfw, researchfw, outlinefw,
illustration-fw, nl2cad, iil-fieldprefill, iil-reflex, testkit,
platform, mcp-hub, infra-deploy, iil-relaunch.

### 4.3 Scaffold-Befehl (`reflex init`)

```bash
# Tier 1: Vollständige YAML generieren (~80 Zeilen)
python -m reflex init --tier 1 --hub risk-hub --vertical chemical_safety --port <from ports.yaml>

# Tier 2: Minimal-YAML generieren (~25 Zeilen)
python -m reflex init --tier 2 --hub billing-hub --port <from ports.yaml>
```

Generiert `reflex.yaml` mit Hub-Name, Vertical, Port, Health-Routes und
Tier-spezifischen Sektionen. Tier 1 enthält zusätzlich: quality, viewports,
htmx_patterns, permissions_matrix (Skeleton), test_users (Skeleton), dev_cycle.

### 4.4 Platform-Report (`reflex platform`)

```bash
python -m reflex platform -c platform-reflex.yaml
python -m reflex platform -c platform-reflex.yaml --report docs/platform-health.md
```

Zentrale `platform-reflex.yaml` definiert alle Hubs mit Pfad, Config und Base-URL.
Report zeigt pro Hub: Health, UC-Count, Route-Pass-Rate, Permission-Pass-Rate.
Ausgabe als Terminal-Tabelle, Markdown oder JSON.

### 4.5 Governance-Gate

| Tier | Gate vor Production-Deploy |
|------|---------------------------|
| Tier 1 | `reflex verify` + `reflex test-permissions` grün |
| Tier 2 | `reflex verify` grün |
| Tier 3 | Kein REFLEX-Gate |

Integration in `/ship` Workflow: Vor `docker compose up` prüft das Deploy-Script
das passende Gate. Fehlschlag blockt den Deploy.

### 4.6 Tier-Wechsel

Tier-Hochstufung (2→1) erfolgt wenn eine App komplexe Endkunden-UI bekommt.
Erfordert nur YAML-Erweiterung (Permission-Matrix, Use Cases), keinen Code-Change.

Tier-Herabstufung (1→2) nur per explizitem ADR-Amendment mit Begründung.

Neue Repos erhalten ihren Tier bei Onboarding (`/onboard-repo` Workflow).

---

## 5. Consequences

### 5.1 Positive

- Alle 21 Django-Apps haben mindestens Health + Route-Monitoring
- Aufwand proportional zum Risiko (Tier 1: voll, Tier 2: minimal, Tier 3: nichts)
- Platform-Report macht Gesamtgesundheit sichtbar
- Packages und Infra werden nicht mit UI-Methodik belastet
- Tier-Hochstufung (2→1) jederzeit möglich wenn App wächst
- Konsistente `reflex.yaml` durch Scaffold-Befehl

### 5.2 Negative / Trade-offs

- 13 Tier-2 Apps brauchen initiales `reflex.yaml` (einmalig ~2h für alle)
- Tier-Zuordnung muss bei neuen Repos bewusst entschieden werden
- `platform-reflex.yaml` ist eine weitere zentrale Konfiguration

### 5.3 Not in Scope

- Playwright-Integration (Zirkel 2) — bleibt per ADR-162 definiert, Rollout separat
- CI-Integration von `reflex platform` als GitHub Action — folgt nach Phase 5
- Automatische Tier-Erkennung anhand von Codebase-Analyse

### 5.4 Confirmation

Diese Entscheidung gilt als bestätigt wenn:

1. `python -m reflex init --tier 1` und `--tier 2` generieren valide YAML
   die von `ReflexConfig.from_yaml()` ladbar ist
2. Mindestens 4 Tier-1 Apps haben vollständiges `reflex.yaml` mit Use Cases
3. Alle 13 Tier-2 Apps haben Minimal-`reflex.yaml` mit Health-Routes
4. `python -m reflex platform -c platform-reflex.yaml` zeigt konsolidierten
   Report für alle 21 Apps
5. `/ship` Workflow prüft `reflex verify` vor Deploy (Tier 1+2)

Überprüfung: 3 Monate nach Rollout-Start (ca. Juli 2026).
Staleness-Review in 12 Monaten: Sind alle Tier-1 Apps vollständig ongeboardet?
Ist der PlatformRunner in CI integriert?

---

## 6. Risks

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Tier-Zuordnung subjektiv | Mittel | Niedrig | Klare Kriterien in §4.1, Review bei Onboarding |
| Scaffold generiert veraltete Ports | Niedrig | Niedrig | Ports aus `ports.yaml` lesen statt Hardcode |
| Governance-Gate blockt dringende Deploys | Niedrig | Mittel | `--skip-reflex` Flag für Hotfixes |
| Platform-Report wird nicht regelmäßig geprüft | Mittel | Niedrig | Cron-Job oder CI-Integration |

---

## 7. Open Questions

| # | Frage | Status | Antwort |
|---|-------|--------|---------|
| Q-1 | Wer entscheidet den Tier bei neuen Repos? | Beantwortet | Ersteller + Reviewer im `/onboard-repo` Workflow anhand Kriterien §4.1 |
| Q-2 | Was wenn `reflex verify` auf Tier-2 App fehlschlägt die noch keine Routes hat? | Beantwortet | Tier-2 Apps müssen mindestens `/livez/` + `/healthz/` in `test_routes` haben — Scaffold erzeugt dies automatisch |
| Q-3 | Playwright-Integration (Zirkel 2) — wann? | Deferred | Separat via ADR-162 Phase 2 — nicht Bestandteil dieses ADR |
| Q-4 | CI-Integration von `reflex platform` als GitHub Action? | Deferred | Folgt nach Phase 5 — eigener ADR wenn Scope klar |

---

## 8. Implementation Plan

| Phase | Task | Status | Evidenz |
|-------|------|--------|---------|
| 1 | Scaffold-Befehl (`reflex init --tier 1\|2`) | ✅ | `iil-reflex/reflex/scaffold.py`, Tests in `tests/test_scaffold.py` |
| 2 | Tier-1 Onboarding (writing-hub, cad-hub, travel-beat, coach-hub, wedding-hub, pptx-hub, recruiting-hub) | ⬜ | 1/8 done (risk-hub), writing-hub partial |
| 3 | Tier-2 Onboarding (13 Apps: `reflex init --tier 2`) | ⬜ | 0/13 done |
| 4 | PlatformRunner + Dashboard | ✅ | `platform_runner.py`, `dashboard.py`, `platform-reflex.yaml` |
| 5 | Governance-Gate in `/ship` | ⬜ | Not yet integrated |

---

## 9. More Information

- [ADR-058](ADR-058-testing-conventions.md) — Testing Conventions
- [ADR-162](ADR-162-reflex-ui-testing-and-scraping.md) — REFLEX Methodology
- [iil-reflex v0.5.0](https://github.com/achimdehnert/iil-reflex) — Package
- [risk-hub reflex.yaml](https://github.com/achimdehnert/risk-hub/blob/main/reflex.yaml) — Referenz-Konfiguration

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-04-17 | Achim Dehnert | Initial: Proposed |
| 2026-04-17 | Achim Dehnert | Review-Findings angewendet, Status: Proposed → Accepted |
| 2026-04-18 | Cascade AI | ADR-Review: YAML frontmatter, Decision Drivers, MADR structure, impl_status partial, evidence |
