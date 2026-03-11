---
status: "accepted"
date: 2026-02-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-065-adr-numbering-filesystem-first.md"]
related: ["ADR-020-documentation-strategy.md", "ADR-015-platform-governance-system.md"]
implementation_status: implemented
---

# ADR-083: Hybrid ADR Governance — Platform + Repo-lokale ADRs

---

## Context and Problem Statement

Das Ökosystem wächst. Neben den bestehenden Projekten (bfagent, travel-beat,
risk-hub, mcp-hub) kommt mit **137-hub** (137herz.de / 137herz.ai) ein Projekt
hinzu, das durch seine Größe und fachliche Eigenständigkeit eine hohe Dichte
an architekturellen Entscheidungen erzeugt.

Bisher werden **alle ADRs zentral** in `platform/docs/adr/` verwaltet.
Das führt zu folgenden Problemen:

1. **Kontextverlust**: Repo-spezifische Entscheidungen (z.B. "Warum nutzt
   137-hub Django+HTMX statt Next.js?") liegen weit entfernt vom Code und
   den fachlichen Konzept-Dokumenten.
2. **KI-Agent-Ineffizienz**: Coding-KIs, die am 137-hub arbeiten, müssen in
   ein fremdes Repo schauen, um Architekturentscheidungen zu verstehen.
3. **Skalierungsproblem**: Bei 80+ ADRs in `platform` wird der Katalog
   unübersichtlich. Repo-spezifische ADRs verwässern den zentralen Index.
4. **Self-Containment**: Ein neuer Entwickler, der `137-hub` klont, hat keinen
   vollständigen Architekturkontext — er muss wissen, dass er in `platform`
   nachschauen muss.

---

## Decision Drivers

- **Self-Contained Repos**: Jedes Repo soll für sich verständlich sein
- **Zentrale Governance**: Ökosystem-weite Regeln müssen an einem Ort leben
- **KI-Agent-Kompatibilität**: Agents arbeiten repo-lokal und brauchen Kontext
- **Keine Duplikation**: Cross-cutting Entscheidungen dürfen nicht in
  mehreren Repos widersprüchlich existieren
- **Rückwärtskompatibilität**: Bestehende ADRs in `platform` bleiben erhalten

---

## Considered Options

### Option 1 — Status Quo: Alles zentral in `platform`

**Pro:** Single Source of Truth, einfache Suche
**Contra:** Kontextverlust, KI-Agent-Ineffizienz, Skalierungsproblem

**Verworfen**: Skaliert nicht bei wachsender Projektanzahl und -komplexität.

### Option 2 — Vollständig dezentral: Jedes Repo eigene ADRs

**Pro:** Self-contained, kein zentrales Nadelöhr
**Contra:** Cross-cutting Entscheidungen müssen dupliziert oder referenziert
werden. Risiko widersprüchlicher Entscheidungen. Kein zentraler Überblick.

**Verworfen**: Governance-Verlust bei ökosystem-weiten Entscheidungen.

### Option 3 — Hybrid: Platform + Repo-lokal (gewählt)

**Pro:**
- Ökosystem-Regeln zentral, Repo-Entscheidungen lokal
- Jedes Repo ist self-contained für seinen Scope
- Cross-Referencing verbindet die Ebenen
- KI-Agents haben lokalen Kontext

**Contra:**
- Zwei Orte für ADRs (leicht höhere kognitive Last)
- Nummerierung muss koordiniert werden

---

## Decision Outcome

**Gewählt: Option 3 — Hybrid ADR Governance**

### Die zwei Ebenen

| Ebene | Ort | Scope | Präfix |
|-------|-----|-------|--------|
| **Ökosystem** | `platform/docs/adr/` | Cross-cutting, Infrastruktur, Standards | `ADR-NNN` (globale Nummer) |
| **Repo-lokal** | `<repo>/docs/adr/` | Repo-spezifische Entscheidungen | `<REPO>-NNN` (repo-lokale Nummer) |

### Repo-Präfixe

| Repo | Präfix | Beispiel |
|------|--------|---------|
| `platform` | `ADR` | `ADR-083-hybrid-adr-governance.md` |
| `137-hub` | `HUB` | `HUB-001-django-htmx-not-nextjs.md` |
| `bfagent` | `BFA` | `BFA-001-multi-agent-architecture.md` |
| `mcp-hub` | `MCP` | `MCP-001-fastmcp-pattern.md` |
| `travel-beat` | `TB` | `TB-001-trip-model-design.md` |
| `risk-hub` | `RISK` | `RISK-001-assessment-scoring.md` |
| `weltenhub` | `WH` | `WH-001-story-universe-model.md` |
| `pptx-hub` | `PPTX` | `PPTX-001-slide-generation.md` |

### Entscheidungsregel: Wo gehört eine ADR hin?

```
Betrifft die Entscheidung MEHR ALS EIN Repo?
  → JA  → platform/docs/adr/ADR-NNN-*.md (globale Nummer)
  → NEIN → <repo>/docs/adr/<PRÄFIX>-NNN-*.md (repo-lokale Nummer)

Unsicher?
  → Starte repo-lokal.
  → Promote zu platform, wenn die Entscheidung cross-cutting wird.
```

### Beispiele

| Entscheidung | Scope | Ort |
|---|---|---|
| Unified Deployment Pattern (Docker, GHCR) | Alle Repos | `platform` ADR-021 |
| Secrets Management Standard | Alle Repos | `platform` ADR-045 |
| Django+HTMX statt Next.js (nur 137-hub) | 137-hub | `137-hub` HUB-001 |
| LLM Provider Abstraction (nur 137-hub) | 137-hub | `137-hub` HUB-002 |
| Multi-Agent Architecture (nur bfagent) | bfagent | `bfagent` BFA-001 |
| Content-Sync API (137-hub ↔ bfagent) | Zwei Repos | `platform` ADR-NNN |

### Nummerierung

- **Platform ADRs**: Weiterhin `max(existing) + 1` (ADR-065 gilt)
- **Repo-lokale ADRs**: Eigene Sequenz pro Repo, startend bei 001
  - Nummerierung: `max(existing in <repo>/docs/adr/) + 1`
  - Format: `<PRÄFIX>-NNN-<slug>.md` (z.B. `HUB-001-django-htmx.md`)

### Cross-Referencing

Repo-lokale ADRs referenzieren Platform-ADRs im Frontmatter:

```yaml
---
status: "accepted"
date: 2026-02-25
platform-refs: ["ADR-021-unified-deployment-pattern.md"]
---
# HUB-001: Django Monolith + HTMX (nicht Next.js SPA)
```

Platform-ADRs können auf repo-lokale ADRs verweisen:

```yaml
related: ["137-hub:HUB-001", "bfagent:BFA-003"]
```

### Verzeichnisstruktur

```
platform/docs/adr/
├── INDEX.md                          # Globaler Index (nur platform ADRs)
├── ADR-083-hybrid-adr-governance.md  # Diese ADR
└── ...

137-hub/docs/adr/
├── INDEX.md                          # Lokaler Index (nur HUB-ADRs)
├── HUB-001-django-htmx.md
└── ...

bfagent/docs/adr/
├── INDEX.md
├── BFA-001-multi-agent-architecture.md
└── ...
```

### Repo-lokaler INDEX.md (Template)

```markdown
# ADR Index — <Repo-Name>

> Repo-spezifische Architecture Decision Records.
> Ökosystem-weite ADRs: siehe [platform/docs/adr/INDEX.md](https://github.com/achimdehnert/platform/blob/main/docs/adr/INDEX.md)

| Nr | Titel | Status | Datum | Platform-Ref |
|----|-------|--------|-------|-------------|
| HUB-001 | Django Monolith + HTMX | Accepted | 2026-02-25 | ADR-021 |
```

---

## Positive Consequences

- Jedes Repo ist architektonisch self-contained
- KI-Agents finden repo-spezifischen Kontext lokal
- Platform bleibt schlank (nur cross-cutting Entscheidungen)
- Klare Entscheidungsregel verhindert Duplikation
- Skaliert mit wachsender Projektanzahl

## Negative Consequences

- Zwei Orte für ADRs (aber klar abgegrenzt)
- Bestehende repo-spezifische ADRs in platform müssten langfristig migriert
  werden (kein sofortiger Handlungsbedarf)
- Repo-lokale Indices müssen gepflegt werden

---

## Migration (Optional, nicht sofort)

Bestehende ADRs in `platform`, die nur ein einzelnes Repo betreffen,
können bei Gelegenheit in das jeweilige Repo migriert werden:

1. Datei kopieren nach `<repo>/docs/adr/<PRÄFIX>-NNN-*.md`
2. Originaldatei in `platform` mit Status `Migrated` markieren und
   Verweis auf neuen Ort hinzufügen
3. Platform INDEX.md aktualisieren

**Regel**: Migration ist optional und erfolgt nur bei aktiver Bearbeitung
der betroffenen ADR. Kein Big-Bang-Migration.

---

## Confirmation

- [ ] Jedes Repo mit eigenen ADRs hat ein `docs/adr/INDEX.md`
- [ ] Repo-lokale ADRs verwenden den korrekten Präfix
- [ ] Cross-Referencing zwischen Ebenen funktioniert
- [ ] Platform INDEX.md referenziert diese ADR
