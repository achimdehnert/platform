# ADR Migration Concept: platform → repo-spezifische Repos

**Stand:** 2026-02-26  
**Autor:** Achim Dehnert  
**Zweck:** ADRs aus `platform/docs/adr/` in die jeweiligen Ziel-Repos migrieren, die sich ausschließlich auf ein einzelnes Projekt beziehen.

---

## Hintergrund

Das `platform`-Repo dient als zentrales Archiv für plattformweite Entscheidungen.
Einige ADRs wurden dort abgelegt, obwohl sie nur ein einzelnes Projekt betreffen.
Diese sollen in das jeweilige Ziel-Repo verschoben werden — das `platform`-Exemplar
bekommt einen Redirect-Stub.

---

## Migrationsstrategie

```
platform/docs/adr/ADR-XXX-name.md
  → [target-repo]/docs/adr/ADR-XXX-name.md   (vollständige Kopie)
  → platform/docs/adr/ADR-XXX-name.md        (Redirect-Stub, bleibt erhalten)
```

Der Redirect-Stub verhindert, dass bestehende Links ins Leere laufen.

---

## Repo-Zuordnung

### travel-beat (DriftTales)

| ADR | Titel | Ziel |
|-----|-------|------|
| ADR-016 | Import von Reiseplänen als Trip-Stops | `travel-beat/docs/adr/` |

### weltenhub (Weltenforger)

| ADR | Titel | Ziel |
|-----|-------|------|
| ADR-018 | Weltenhub — Zentrale Story-Universe Plattform | `weltenhub/docs/adr/` |
| ADR-019 | Weltenhub UI, Templates, Views & APIs | `weltenhub/docs/adr/` |
| ADR-024 | Location-Recherche als Weltenhub-Modul | `weltenhub/docs/adr/` |

### bfagent (Book Factory Agent)

| ADR | Titel | Ziel |
|-----|-------|------|
| ADR-047 | Sphinx Documentation Hub | `bfagent/docs/adr/` (status: superseded — trotzdem migrieren) |
| ADR-076 | bfagent CI Test Strategy | `bfagent/docs/adr/` |

### trading-hub

| ADR | Titel | Ziel |
|-----|-------|------|
| ADR-052 | Trading Hub — Broker-Adapter-Architektur | `trading-hub/docs/adr/` |
| ADR-400 | Market Scanner Hybrid Architecture | `trading-hub/docs/adr/` |
| ADR-401 | Autonomous Trading Bot | `trading-hub/docs/adr/` |

### risk-hub (Schutztat)

| ADR | Titel | Ziel |
|-----|-------|------|
| ADR-038 | DSB Datenschutzbeauftragter Module | `risk-hub/docs/adr/` |

### Nicht migrieren (plattformweit)

ADR-029 (CAD Hub Extraction), ADR-034 (CAD ETL Chat-Agent), ADR-039 (Seating),
ADR-064 (coach-hub) — Ziel-Repos existieren noch nicht im Workspace.
Diese verbleiben in `platform/docs/adr/` bis die Repos ongeboardet sind.

---

## Redirect-Stub Format

```markdown
---
status: moved
date: YYYY-MM-DD
---

# ADR-XXX: [Titel]

> **Moved** → [`[repo]/docs/adr/ADR-XXX-name.md`](https://github.com/achimdehnert/[repo]/blob/main/docs/adr/ADR-XXX-name.md)

Dieser ADR wurde in das Ziel-Repo verschoben, da er ausschließlich `[repo]` betrifft.
```

---

## Ausführungsschritte

1. `docs/adr/` im Ziel-Repo anlegen (falls nicht vorhanden)
2. ADR-Datei kopieren (unverändert, vollständiger Inhalt)
3. Redirect-Stub in `platform/docs/adr/` ersetzen
4. `platform/docs/adr/INDEX.md` aktualisieren (moved-Einträge markieren)
5. GitHub Issue im Ziel-Repo erstellen: `[ADR] ADR-XXX migriert von platform`

---

## Priorisierung

| Priorität | ADRs | Begründung |
|-----------|------|------------|
| Sofort | ADR-016, ADR-018, ADR-019, ADR-024 | Aktiv genutzte Repos, Status: accepted |
| Nächste Woche | ADR-052, ADR-076, ADR-400, ADR-401 | trading-hub + bfagent aktiv |
| Niedrig | ADR-038, ADR-047 | risk-hub + superseded |

