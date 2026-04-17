# ADR-163: Adopt Three-Tier REFLEX Quality Standard for All Platform Repositories

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - "*/reflex.yaml"
      - iil-reflex/reflex/
      - platform/docs/adr/ADR-163-*
  - supersedes_check: false
-->

| Attribut       | Wert                                            |
|----------------|--------------------------------------------------|
| **Status**     | Accepted                                         |
| **Scope**      | platform                                         |
| **Repo**       | platform                                         |
| **Erstellt**   | 2026-04-17                                       |
| **Autor**      | Achim Dehnert                                    |
| **Reviewer**   | Cascade (AI Review 2026-04-17)                   |
| **Supersedes** | –                                                |
| **Relates to** | ADR-058 (Testing Conventions), ADR-162 (REFLEX Methodology) |
| **implementation_status** | none                                |

---

## 1 Kontext

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

## 2 Entscheidung

**Wir führen ein dreistufiges REFLEX-Tiering als verbindlichen Platform Quality
Standard ein.**

### 2.1 Tier-Kriterien

| Tier | Kriterium | Pflicht-Artefakte |
|------|-----------|-------------------|
| **Tier 1 — Full Reflex** | App hat Endkunden-UI, Login-System, rollenbasierte Permissions | `reflex.yaml` (voll), `docs/use-cases/*.md`, Permission-Matrix, `reflex verify` + `reflex test-permissions` grün vor Deploy |
| **Tier 2 — Reflex Light** | App hat Docker-Deployment aber keine komplexe Endkunden-UI oder befindet sich in früher Phase | `reflex.yaml` (light: `test_routes` + `dev_cycle`), `reflex verify` grün vor Deploy |
| **Tier 3 — Kein Reflex** | Repo hat keine UI, keine Routes, kein Docker-Deployment | pytest + ruff genügen, kein `reflex.yaml` nötig |

### 2.2 Tier-Zuordnung (Stand 2026-04-17)

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

### 2.3 Scaffold-Befehl (`reflex init`)

```bash
# Tier 1: Vollständige YAML generieren (~80 Zeilen)
python -m reflex init --tier 1 --hub risk-hub --vertical chemical_safety --port 8003

# Tier 2: Minimal-YAML generieren (~25 Zeilen)
python -m reflex init --tier 2 --hub billing-hub --port 8006
```

Generiert `reflex.yaml` mit Hub-Name, Vertical, Port, Health-Routes und
Tier-spezifischen Sektionen. Tier 1 enthält zusätzlich: quality, viewports,
htmx_patterns, permissions_matrix (Skeleton), test_users (Skeleton), dev_cycle.

### 2.4 Platform-Report (`reflex platform`)

```bash
python -m reflex platform -c platform-reflex.yaml
python -m reflex platform -c platform-reflex.yaml --report docs/platform-health.md
```

Zentrale `platform-reflex.yaml` definiert alle Hubs mit Pfad, Config und Base-URL.
Report zeigt pro Hub: Health, UC-Count, Route-Pass-Rate, Permission-Pass-Rate.
Ausgabe als Terminal-Tabelle, Markdown oder JSON.

### 2.5 Governance-Gate

| Tier | Gate vor Production-Deploy |
|------|---------------------------|
| Tier 1 | `reflex verify` + `reflex test-permissions` grün |
| Tier 2 | `reflex verify` grün |
| Tier 3 | Kein REFLEX-Gate |

Integration in `/ship` Workflow: Vor `docker compose up` prüft das Deploy-Script
das passende Gate. Fehlschlag blockt den Deploy.

### 2.6 Tier-Wechsel

Tier-Hochstufung (2→1) erfolgt wenn eine App komplexe Endkunden-UI bekommt.
Erfordert nur YAML-Erweiterung (Permission-Matrix, Use Cases), keinen Code-Change.

Tier-Herabstufung (1→2) nur per explizitem ADR-Amendment mit Begründung.

Neue Repos erhalten ihren Tier bei Onboarding (`/onboard-repo` Workflow).

---

## 3 Betrachtete Alternativen

| Alternative | Pro | Contra | Entscheidung |
|---|---|---|---|
| **A: Kein Tiering — REFLEX für alle 37 Repos** | Einheitlich, einfach zu erklären | 16 Repos haben keine UI → Aufwand ohne Nutzen, PyPI-Packages werden belastet | **Abgelehnt** |
| **B: Kein Tiering — REFLEX nur für explizit markierte Repos** | Maximal flexibel | Kein Standard, jede App entscheidet selbst → Adoption bleibt bei 1-2 Repos | **Abgelehnt** |
| **C: Zwei Tiers (Full + None)** | Einfacher | 13 Apps ohne komplexe UI aber mit Docker-Deployment hätten gar kein Monitoring → P-1 bleibt | **Abgelehnt** |
| **D: Drei Tiers (Full + Light + None)** | Proportionaler Aufwand, alle Django-Apps haben Baseline, Packages unbelastet | Tier-Zuordnung muss bei neuen Repos entschieden werden | **Gewählt** |

---

## 4 Begründung im Detail

**Warum Drei Tiers statt Zwei?** 13 Django-Apps (trading-hub, billing-hub, etc.)
haben Docker-Deployment und Health-Endpoints, aber keine komplexe Endkunden-UI.
Sie komplett auszuschließen (Tier 3) hieße, dass Route-Fehler und Health-Probleme
erst in Production entdeckt werden. Tier 2 gibt diesen Apps eine Baseline mit
minimalem Aufwand (< 5 Minuten Onboarding).

**Warum Packages in Tier 3?** PyPI-Packages (aifw, promptfw, etc.) haben keine
Routes, keine UI, keine Permissions. Ihre Qualität wird durch pytest, ruff und
CI sichergestellt. REFLEX würde hier nur ein leeres YAML erzwingen.

**Warum Scaffold-Befehl?** Manuelles Anlegen von `reflex.yaml` mit korrekten
Routes, Ports und Health-Paths ist fehleranfällig und dauert 15-30 Minuten pro App.
`reflex init` reduziert das auf < 5 Minuten und erzeugt konsistente Konfigurationen.

**Warum Platform-Report?** Einzelne `reflex verify` Läufe pro App geben keinen
Gesamtüberblick. Der PlatformRunner aggregiert alle Ergebnisse und macht
Regressionen hub-übergreifend sichtbar.

---

## 5 Implementation Plan

### Phase 1 — Scaffold-Befehl (1 Session)

- `reflex init` implementieren mit `--tier`, `--hub`, `--vertical`, `--port`
- Tier 1 Template (~80 Zeilen) + Tier 2 Template (~25 Zeilen)
- CLI-Subparser in `reflex/__main__.py`
- Tests für Template-Generierung

### Phase 2 — Tier-1 Onboarding (1 Session pro App)

- writing-hub: `reflex.yaml` vervollständigen (Permission-Matrix, test_users)
- cad-hub, travel-beat, coach-hub, wedding-hub, pptx-hub, recruiting-hub:
  `reflex init --tier 1` + Use Cases schreiben + Permission-Matrix befüllen

### Phase 3 — Tier-2 Onboarding (1 Session für alle 13 Apps)

- `reflex init --tier 2` für alle 13 Tier-2 Apps
- Ergebnis: 13 Minimal-`reflex.yaml` mit Health-Routes und dev_cycle

### Phase 4 — PlatformRunner (1 Session)

- `platform-reflex.yaml` anlegen mit allen 21 Apps
- `reflex/platform_runner.py` implementieren
- CLI-Subparser `platform`
- Terminal-Tabelle, Markdown-Report, JSON-Ausgabe

### Phase 5 — Governance-Gate (1 Session)

- `/ship` Workflow erweitern: `reflex verify` vor Deploy (Tier 1+2)
- `/ship` Workflow: `reflex test-permissions` vor Deploy (nur Tier 1)
- Fehlschlag blockt Deploy mit klarer Fehlermeldung

---

## 6 Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Tier-Zuordnung subjektiv | Mittel | Niedrig | Klare Kriterien in §2.1, Review bei Onboarding |
| Scaffold generiert veraltete Ports | Niedrig | Niedrig | Ports aus `ports.yaml` lesen statt Hardcode |
| Governance-Gate blockt dringende Deploys | Niedrig | Mittel | `--skip-reflex` Flag für Hotfixes |
| Platform-Report wird nicht regelmäßig geprüft | Mittel | Niedrig | Cron-Job oder CI-Integration |

---

## 7 Open Questions

| # | Frage | Status | Antwort |
|---|-------|--------|---------|
| Q-1 | Wer entscheidet den Tier bei neuen Repos? | Beantwortet | Ersteller + Reviewer im `/onboard-repo` Workflow anhand Kriterien §2.1 |
| Q-2 | Was wenn `reflex verify` auf Tier-2 App fehlschlägt die noch keine Routes hat? | Beantwortet | Tier-2 Apps müssen mindestens `/livez/` + `/healthz/` in `test_routes` haben — Scaffold erzeugt dies automatisch |
| Q-3 | Playwright-Integration (Zirkel 2) — wann? | Deferred | Separat via ADR-162 Phase 2 — nicht Bestandteil dieses ADR |
| Q-4 | CI-Integration von `reflex platform` als GitHub Action? | Deferred | Folgt nach Phase 5 — eigener ADR wenn Scope klar |

---

## 8 Konsequenzen

### 8.1 Positiv

- Alle 21 Django-Apps haben mindestens Health + Route-Monitoring
- Aufwand proportional zum Risiko (Tier 1: voll, Tier 2: minimal, Tier 3: nichts)
- Platform-Report macht Gesamtgesundheit sichtbar
- Packages und Infra werden nicht mit UI-Methodik belastet
- Tier-Hochstufung (2→1) jederzeit möglich wenn App wächst
- Konsistente `reflex.yaml` durch Scaffold-Befehl

### 8.2 Trade-offs

- 13 Tier-2 Apps brauchen initiales `reflex.yaml` (einmalig ~2h für alle)
- Tier-Zuordnung muss bei neuen Repos bewusst entschieden werden
- `platform-reflex.yaml` ist eine weitere zentrale Konfiguration

### 8.3 Nicht in Scope

- Playwright-Integration (Zirkel 2) — bleibt per ADR-162 definiert, Rollout separat
- CI-Integration von `reflex platform` als GitHub Action — folgt nach Phase 5
- Automatische Tier-Erkennung anhand von Codebase-Analyse

---

## 9 Validation Criteria

### Phase 1 (Scaffold)

- [ ] `python -m reflex init --tier 1 --hub test-hub --vertical test --port 9000` generiert valide YAML
- [ ] `python -m reflex init --tier 2 --hub test-hub --port 9000` generiert Minimal-YAML
- [ ] Generierte YAML ist von `ReflexConfig.from_yaml()` ladbar

### Phase 2+3 (Onboarding)

- [ ] Mindestens 4 Tier-1 Apps haben vollständiges `reflex.yaml`
- [ ] Alle 13 Tier-2 Apps haben Minimal-`reflex.yaml`
- [ ] `reflex verify` läuft erfolgreich auf allen ongeboardeten Apps

### Phase 4 (PlatformRunner)

- [ ] `python -m reflex platform -c platform-reflex.yaml` zeigt Report für alle 21 Apps
- [ ] Report enthält: Health, Route-Count, Permission-Count pro Hub

### Phase 5 (Governance)

- [ ] `/ship` prüft `reflex verify` vor Deploy
- [ ] Deploy wird bei Failure geblockt (mit klarer Fehlermeldung)
- [ ] `--skip-reflex` Flag für Hotfixes dokumentiert

---

## 10 Confirmation

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

## 11 Referenzen

- [ADR-058](ADR-058-testing-conventions.md) — Testing Conventions
- [ADR-162](ADR-162-reflex-ui-testing-and-scraping.md) — REFLEX Methodology
- [iil-reflex v0.3.0](https://github.com/achimdehnert/iil-reflex) — Package
- [risk-hub reflex.yaml](https://github.com/achimdehnert/risk-hub/blob/main/reflex.yaml) — Referenz-Konfiguration

---

## 12 Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-04-17 | Achim Dehnert | Initial: Proposed |
| 2026-04-17 | Achim Dehnert | Review-Findings angewendet, Status: Proposed → Accepted |
