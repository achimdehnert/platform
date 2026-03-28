---
status: proposed
date: 2026-03-27
decision-makers: Achim Dehnert
consulted: –
informed: –
---

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - tools/design_dna/
  - hub_dnas/
  - detection_patterns/
supersedes_check: ADR-049
-->

# ADR-051: Adopt Hub Visual Identity System with AI-Resistant Design DNA and Mutation Engine

## Metadaten

| Attribut          | Wert                                                                         |
|-------------------|------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                     |
| **Scope**         | platform                                                                     |
| **Erstellt**      | 2026-03-27                                                                   |
| **Autor**         | Achim Dehnert                                                                |
| **Reviewer**      | –                                                                            |
| **Supersedes**    | ADR-049 (Design Token System — wird erweitert, nicht ersetzt)                |
| **Superseded by** | –                                                                            |
| **Relates to**    | ADR-049 (Design Token System), ADR-040 (Frontend Completeness Gate), ADR-048 (HTMX Playbook), ADR-054 (Architecture Guardian) |

## Repo-Zugehörigkeit

| Repo             | Rolle    | Betroffene Pfade / Komponenten                        |
|------------------|----------|-------------------------------------------------------|
| `platform`       | Primär   | `tools/design_dna/`, `hub_dnas/`, `detection_patterns/`, `shared/styles/` |
| `bieterpilot`    | Sekundär | `shared/static/css/pui-tokens.css`, `base.html`        |
| `risk-hub`       | Sekundär | `shared/static/css/pui-tokens.css`, `base.html`        |
| `travel-beat`    | Sekundär | `shared/static/css/pui-tokens.css`, `base.html`        |
| alle weiteren Hubs | Sekundär | `shared/static/css/pui-tokens.css`, `base.html`      |

---

## Decision Drivers

- **KI-Fingerprint-Erkennung wächst**: Tools wie Originality.ai, GPTZero und visuelle Klassifikatoren (Google, Meta) erkennen generische AI-Slop-Designs zuverlässig an Schrift, Farbe, Layout und CSS-Mustern — das schadet SEO und Markwahrnehmung.
- **12+ Hubs, kein visuelles Profil**: Alle Hubs sehen identisch aus — gleiches Tailwind-Utility-Pattern, gleiche Spacing-Skala, gleiche Komponenten-Archetypen.
- **ADR-049 reicht nicht**: Das Token-System löst Konsistenz, aber nicht Einzigartigkeit. Semantic tokens sind ein Vehikel — nicht die Identität selbst.
- **Reaktionsfähigkeit auf Erkennungsevolution**: Neue Fingerprint-Kriterien müssen sofort plattformweit umgesetzt werden, nicht manuell Hub-für-Hub.
- **Kein Node.js-Build-Step erwünscht**: Platform-Standard ist `django-tailwind-cli` — keine npm-basierten Style-Dictionary-Pipelines.
- **Python-first**: Alle Werkzeuge müssen in Python implementiert sein und in die bestehende CI-Landschaft passen.

---

## 1. Context and Problem Statement

Die iil-Platform-Stack betreibt 14 Hub-Anwendungen für deutsche B2B-Märkte. Jede App hat eine eigenständige Marke (bieterpilot, DriftTales, Prezimo etc.), aber alle teilen identische Frontend-Charakteristika: Tailwind-Utility-Klassen, ADR-049-Token-System mit `--pui-*`-Variablen, und HTMX-Partials aus identischen Django-Template-Mustern.

Visuelle KI-Erkennung funktioniert heute auf drei Ebenen:

1. **Makro-Ebene** (Layout): Grid-Symmetrie, Card-Archetypen, Spacing-Vorhersagbarkeit
2. **Meso-Ebene** (Typographie/Farbe): Generische Schriftpaarungen (Inter + System-UI), mathematisch-perfekte Farbharmonien, vorhersagbare Opazitätsstufen
3. **Mikro-Ebene** (CSS-Muster): `border-radius: 8px` / `12px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.12)`, transition-Boilerplate

### 1.1 Ist-Zustand

| Problem                              | Impact                                        |
|--------------------------------------|-----------------------------------------------|
| Alle Hubs verwenden Inter/System-UI  | Stärkster Einzelindikator für AI-Generierung  |
| Identisches Spacing-System (4px-Grid)| Layoutmuster sind maschinell vorhersagbar     |
| Gleiche Farbharmonien hub-übergreifend | Kein visuelles Profil, keine Markenidentität|
| Kein Audit-Werkzeug                  | Keine Messung des aktuellen AI-Fingerprints   |
| Änderungen manuell pro Hub           | O(n)-Aufwand bei n=14 Hubs                   |

### 1.2 Ziel

Ein **Hub Visual Identity System** das:
- Jede Hub-Identität in einer einzigen `hub-dna.yaml` kodiert
- Deterministisch CSS-Tokens und Tailwind-Config aus der DNA generiert
- Den aktuellen AI-Fingerprint-Score jedes Hubs messbar macht (0–100)
- Bei Bedarf über Claude API neue DNA-Varianten generiert (Mutation Engine)
- Vollständig in CI integriert ist und ohne manuelle Eingriffe läuft

---

## 2. Decision Drivers (Details)

### 2.1 AI-Fingerprint-Kategorien (Stand 2026)

Basierend auf Analyse bekannter Erkennungssysteme (Originality.ai v3, GPTZero Design Classifier, interne Heuristiken von Google Lighthouse):

| Kategorie      | Erkennungsmerkmal                                    | Gewichtung |
|----------------|------------------------------------------------------|-----------|
| Typography     | Inter, Roboto, Arial, system-ui, Space Grotesk       | 35%       |
| Color Harmony  | Mathematisch-perfekte Triaden/Komplementärfarben     | 25%       |
| Spacing        | Strict 4px/8px-Grid ohne Variation                   | 15%       |
| Layout Patterns| Symmetrische Card-Grids, vorhersagbarer Whitespace   | 15%       |
| CSS Micro-Patterns | border-radius 8/12px, standard box-shadow        | 10%       |

---

## 3. Considered Options

### Option A — Manuell pro Hub (Status quo verbessern)
Jeder Hub bekommt manuell neue Fonts und Farben, ohne Systemebene.

**Pros:** Kein neues Tooling-Risiko  
**Cons:** O(n) Aufwand, keine Reaktionsfähigkeit, keine Messbarkeit

### Option B — Hub Visual Identity System mit Mutation Engine ✅ (gewählt)
Zentrales Python-Tool-Set: DNA-Schema → Pipeline → Audit → Mutation.

**Pros:** O(1)-Reaktion, messbar, automatisiert, Python-first, CI-integriert  
**Cons:** Initialer Aufwand ~16h, neue Toolchain zu warten

### Option C — Figma Tokens + Style Dictionary (npm-basiert)
Figma als Source of Truth, Style Dictionary transformiert zu CSS.

**Pros:** Industrie-Standard, Figma-Integration  
**Cons:** Node.js-Build-Step widerspricht Platform-Standard (ADR preference), Figma-Abhängigkeit, kein Mutation-Engine

---

## 4. Decision Outcome

**Gewählt: Option B** — Hub Visual Identity System mit Mutation Engine.

### 4.1 Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                   HUB VISUAL IDENTITY SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  hub_dnas/bieterpilot.yaml          hub_dnas/travel-beat.yaml       │
│  ┌──────────────────────┐           ┌──────────────────────┐        │
│  │  personality: ...    │           │  personality: ...    │        │
│  │  palette: { ... }    │           │  palette: { ... }    │        │
│  │  typography: { ... } │           │  typography: { ... } │        │
│  │  layout: { ... }     │           │  layout: { ... }     │        │
│  │  motion: { ... }     │           │  motion: { ... }     │        │
│  └──────────┬───────────┘           └──────────┬───────────┘        │
│             │                                  │                     │
│             └──────────────┬───────────────────┘                    │
│                            ↓                                         │
│             ┌──────────────────────────────┐                        │
│             │   tools/design_dna/          │                        │
│             │   pipeline.py                │                        │
│             │   (DNA → CSS Tokens)         │                        │
│             └──────────────┬───────────────┘                        │
│                            │                                         │
│              ┌─────────────┼──────────────┐                         │
│              ↓             ↓              ↓                          │
│   pui-tokens-bieterpilot.css  pui-tokens-travel-beat.css  ...       │
│              │             │                                         │
│              ↓             ↓                                         │
│   ┌────────────────────────────────────┐                            │
│   │   tools/design_dna/audit.py        │                            │
│   │   AI Fingerprint Scorer (0–100)    │                            │
│   │   → CI gate: score < 30 required   │                            │
│   └────────────────┬───────────────────┘                            │
│                    │ Score > 30                                      │
│                    ↓                                                 │
│   ┌────────────────────────────────────┐                            │
│   │   tools/design_dna/mutate.py       │                            │
│   │   Claude API Mutation Engine       │                            │
│   │   → Generiert neue DNA-Variante    │                            │
│   │   → Erhält Brand-Persönlichkeit    │                            │
│   │   → Umgeht bekannte Fingerprints   │                            │
│   └────────────────────────────────────┘                            │
│                                                                      │
│   .github/workflows/design-audit.yml     (täglich, jeder PR)        │
│   .github/workflows/design-mutate.yml    (manuell / scheduled)      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Hub DNA Schema

Jede Hub-Identität ist in einer YAML-Datei kodiert:

```yaml
# hub_dnas/bieterpilot.yaml
hub: bieterpilot
display_name: "bieterpilot"
personality: "precision, trust, industrial authority"
aesthetic: "institutional-minimalism"

palette:
  primary:        "#0A2540"   # Navy — Autorität, Verlässlichkeit
  primary_hover:  "#0D3063"
  accent:         "#F5A623"   # Amber — Entscheidung, Aktion
  surface:        "#FAFAF8"   # Off-White — nicht technisch-kalt
  surface_alt:    "#F0EEE9"
  foreground:     "#0A0A0A"
  muted:          "#6B6560"
  border:         "#D4CFC8"
  danger:         "#C0392B"
  success:        "#1A6B3C"
  warning:        "#D97706"

typography:
  display_font:   "Syne"
  body_font:      "Instrument Sans"
  mono_font:      "JetBrains Mono"
  display_weight: "700"
  body_weight:    "400,500,600"
  # Bunny Fonts URL (DSGVO-konform, kein Google Fonts)
  font_source:    "https://fonts.bunny.net/css?family=syne:700|instrument-sans:400,500,600|jetbrains-mono:400"

layout:
  radius_sm:   "2px"    # Kantig = professionell/industriell
  radius_md:   "4px"
  radius_lg:   "8px"
  radius_xl:   "12px"
  asymmetry_level: "medium"   # low | medium | high
  grid_variant: "bento"       # standard | bento | editorial | dashboard

motion:
  duration_fast:   "100ms"
  duration_normal: "200ms"
  easing_standard: "cubic-bezier(0.4, 0, 0.2, 1)"
  easing_spring:   "cubic-bezier(0.34, 1.4, 0.64, 1)"   # Nicht 1.56 — subtiler
  hover_lift:      "-2px"

fingerprint_score: null   # Wird von audit.py befüllt
last_mutated:      null
mutation_history:  []
```

---

## 5. Consequences

### Positive Konsequenzen

- **Messbarkeit**: Jeder Hub hat einen numerischen AI-Fingerprint-Score, der in CI sichtbar ist
- **O(1)-Reaktion**: Bei neuen Erkennungsalgorithmen → `detection_patterns/ai_patterns_v2.yaml` updaten → Pipeline neu ausführen
- **Brand-Konsistenz**: Jeder Hub hat eine kodierte Persönlichkeit, die alle CSS-Entscheidungen treibt
- **Mutation Engine**: Claude API generiert auf Knopfdruck neue DNA-Varianten, die Fingerprints umgehen aber Persönlichkeit erhalten
- **Auditierbarkeit**: `mutation_history` in DNA-YAML trackt alle Veränderungen mit Zeitstempel und Begründung

### Negative Konsequenzen

- **Initialer Aufwand**: ~16h für System-Aufbau + 14 Hub-DNA-Configs
- **Neue Abhängigkeit**: `mutation.py` benötigt Anthropic API Key (bereits vorhanden in Platform)
- **CSS-Generierung in Python**: Kein Style Dictionary — eigene Transforms müssen gepflegt werden
- **Per-Hub CSS-Files**: Statt eines globalen `pui-tokens.css` gibt es `pui-tokens-{hub}.css` — jeder Hub bindet seine eigene Datei ein

### Confirmation

Diese ADR gilt als implementiert wenn:
1. `python -m tools.design_dna audit --all` in CI läuft ohne Fehler
2. Alle 14 Hubs haben einen `fingerprint_score < 40`
3. `pui-tokens-{hub}.css` wird pro Hub generiert und in `base.html` eingebunden
4. `design-audit.yml` läuft auf jedem PR und blockiert bei Score > 60
5. **Externe Validierung**: Mindestens 1 Hub vorher/nachher durch einen externen AI-Detektor (z.B. Originality.ai Design Classifier) getestet — Ergebnis dokumentiert

> **Hinweis**: Der interne Fingerprint-Score (0–100) basiert auf einem eigenen Pattern-Katalog. Ohne externe Validierung ist er eine Heuristik, kein bewiesener AI-Resistenz-Indikator. Die externe Validierung in Phase 4 stellt sicher, dass der Score tatsächlich mit realer AI-Erkennung korreliert.

---

## 6. Migration Tracking

| Schritt                                         | Status        | Datum      | Notiz                          |
|-------------------------------------------------|---------------|------------|--------------------------------|
| ADR-051 erstellen                               | ✅ Done       | 2026-03-27 | Diese ADR                      |
| `tools/design_dna/schema.py` (Pydantic)         | ✅ Done       | 2026-03-27 | Vollständiges Validation-Schema |
| `tools/design_dna/pipeline.py` (DNA → CSS)      | ✅ Done       | 2026-03-27 | Python-native, kein Node.js    |
| `tools/design_dna/audit.py` (Fingerprint-Scorer)| ✅ Done       | 2026-03-27 | Score 0–100, Kategorie-Detail  |
| `tools/design_dna/mutate.py` (aifw)             | ✅ Done       | 2026-03-27 | Mutation Engine via aifw       |
| `detection_patterns/ai_patterns_v1.yaml`         | ✅ Done       | 2026-03-27 | 47 bekannte Fingerprints       |
| Alle 14 Hub-DNA-YAMLs                            | ✅ Done       | 2026-03-27 | Individuelle Persönlichkeiten  |
| `design-audit.yml` GitHub Action                 | ✅ Done       | 2026-03-27 | PR-Gate + täglicher Scan       |
| `design-mutate.yml` GitHub Action                | ✅ Done       | 2026-03-27 | Manuell + scheduled            |
| Integration in alle Hub-`base.html`              | ⏳ Pending    | –          | Nach erster Pipeline-Ausführung |
| CI-Gate Score-Threshold aktivieren               | ⏳ Pending    | –          | Nach Baseline-Messung          |
| `check_design_tokens.py` (ADR-049) erweitern    | ⏳ Pending    | –          | DNA-Score in bestehendes Tool  |
| Externe Validierung (Originality.ai o.ä.)        | ⏳ Pending    | –          | 1 Hub vorher/nachher testen    |

---

## 7. Implementation Plan

### Phase 1 — Foundation (Sprint 1, ~8h)
1. `tools/design_dna/` Package aufsetzen
2. Pydantic-Schema validiert alle DNA-YAMLs
3. Pipeline generiert `pui-tokens-{hub}.css` für alle 14 Hubs
4. `make generate-tokens` als Makefile-Target

### Phase 2 — Audit (Sprint 1, ~4h)
1. `audit.py` mit Pattern-Datenbank implementieren
2. Score-Report im JSON- und Terminal-Format
3. `design-audit.yml` CI-Workflow

### Phase 3 — Mutation Engine (Sprint 2, ~4h)
1. `mutate.py` via `aifw.service.sync_completion()` (kein direkter anthropic-Import, kein hardcoded Model)
2. `design-mutate.yml` GitHub Action (manuell triggerable, erstellt **Review-PR**, kein Auto-Commit)
3. Mutation History in DNA-YAML

### Phase 4 — Hub-Integration (~4h)
1. Generierte CSS-Files pro Hub deployen
2. `base.html` pro Hub anpassen (HTMX + Alpine.js **self-hosted** via `{% static %}`, keine CDN-Links)
3. CI-Gate mit Score-Threshold aktivieren
4. Externe Validierung: 1 Hub vorher/nachher durch Originality.ai testen

### Phase 5 — Grid-Varianten (Backlog)
1. Grid-Varianten (`bento`, `editorial`, `standard`) in `pipeline.py` implementieren (aktuell nur `dashboard`)
2. Hub-DNA `grid_variant` Feld mit tatsächlicher CSS-Generierung verbinden

---

## 8. More Information

- ADR-049: Design Token System — CSS Custom Properties + Tailwind Bridge
- ADR-040: Frontend Completeness Gate — Playwright E2E + UI Manifest
- ADR-048: HTMX Playbook — Anti-Pattern Enforcement
- ADR-054: Architecture Guardian — CI Compliance
- `tools/design_dna/` — Implementierung dieser ADR
- `hub_dnas/` — Individuelle Hub-Identitäten (Source of Truth)
- `detection_patterns/` — Bekannte AI-Fingerprint-Katalog
- Originality.ai Design Classifier: https://originality.ai
- Style Dictionary (Referenz, nicht verwendet): https://amzn.github.io/style-dictionary/
