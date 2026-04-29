---
title: "ADR-175 — Workflow Modularization Pattern: Inline vs External References"
date: 2026-04-29
status: Proposed
deciders: achimdehnert
implementation_status: planned
implementation_evidence:
  - "platform/.windsurf/workflows/onboard-repo.md — Step 7 + Refs ausgelagert (Pilot, 1175→1041 LOC)"
  - "platform/.windsurf/workflows/new-github-project.md — Verifikation ausgelagert (Pilot, 701→664 LOC)"
  - "platform/docs/onboarding/onboard-repo-checklist.md — neuer Auslagerungs-Pfad etabliert"
implementation_done_when:
  - "Modularisierungs-Regeln in workflow-index.md dokumentiert"
  - "Mind. 5 Workflows >300 LOC nach Pattern refaktoriert"
  - "Test: Coding-Agent versteht Referenz-Verweise und liest externes File bei Bedarf"
---

# ADR-175 — Workflow Modularization Pattern: Inline vs External References

## Context and Problem Statement

Mehrere `.windsurf/workflows/*.md` Dateien sind über 300-1175 Zeilen groß
(`onboard-repo`, `new-github-project`, `platform-audit`, `agentic-coding`,
`session-ende`, `session-start`). Beim Workflow-Aufruf lädt Cascade die gesamte
Datei → Token-Kosten + langsamere Reaktion + schlechtere Übersicht.

Naive Modularisierung ("alles aufteilen") ist gefährlich: Agentic Workflows
folgen einem linearen Step-by-Step-Modell. Das Verteilen aktiver Steps auf
mehrere Files erfordert Multi-File-Reads und ändert die Workflow-Mechanik.

**Problem:** Wir brauchen klare Regeln, **was** ausgelagert werden darf
und **was** inline bleiben muss.

## Decision Drivers

- Workflow muss vom Agent linear lesbar/ausführbar bleiben
- Token-Kosten reduzieren (große Workflows = teure Sessions)
- Aktive Steps bleiben dort wo der Agent arbeitet
- Passive Inhalte (Checklisten, Beispiele, Referenzen) auslagerbar
- Keine versteckten Multi-File-Read-Abhängigkeiten

## Considered Options

### Option 1: Alles aufteilen (Multi-File Workflows)
- Jede Phase in eigenes File, Workflow als Index
- ❌ Zerstört linearen Step-Flow
- ❌ Agent muss bei jedem Step neue Datei lesen
- ❌ Nicht mit Cascade-Workflow-Modell kompatibel

### Option 2: Selektive Auslagerung nach Inhalt-Typ ✅ (gewählt)
- **Inline bleibt:** Aktive Steps, Code-Snippets, YAML/JSON Templates die direkt erstellt werden
- **Ausgelagert:** Verifikations-Checklisten, Beispiel-Repo-Referenzen, optionale Tiefenerklärungen
- ✅ Workflow-Ablauf bleibt linear
- ✅ Agent liest nur was er aktiv braucht
- ✅ Externe Files sind Lookups (Agent findet sie über Verweis)

### Option 3: Status quo (alle Workflows inline)
- ❌ Token-Verschwendung bei jedem Aufruf
- ❌ Onboard-repo (1175 LOC) bei jeder Session-Schleife geladen

## Decision

**Wir wählen Option 2** — selektive Auslagerung nach Inhalt-Typ:

### Auslagerungs-Regeln

| Kategorie | Aktion | Begründung |
|-----------|--------|------------|
| **Aktive Steps** (Step N) | INLINE | Linearer Workflow-Ablauf |
| **Inline-Code** (Bash, Python, YAML) | INLINE | Agent muss direkt sehen |
| **Konfig-Templates** (Dockerfile, compose) | INLINE | Werden im Step erstellt |
| **Verifikations-Checklisten** | AUSGELAGERT | Lookup am Ende, optional |
| **Beispiel-Repo-Referenzen** ("137-hub als Vorbild") | AUSGELAGERT | Lookup-only |
| **Compliance-/Migration-Anleitungen** | AUSGELAGERT | Selten gebraucht |
| **Glossare / FAQ** | AUSGELAGERT | Lookup-only |

### Auslagerungs-Pfad

`platform/docs/<topic>/<workflow-name>-<aspect>.md`

Beispiele:
- `docs/onboarding/onboard-repo-checklist.md`
- `docs/onboarding/new-github-project-checklist.md`
- `docs/governance/platform-audit-rubric.md`

### Verweis-Format im Workflow

```markdown
## Step X: Verifikation

→ **[`docs/onboarding/<workflow>-checklist.md`](../../docs/onboarding/<workflow>-checklist.md)**

Inhalte:
- [Aufzählung der Hauptthemen]

**Quick-Check** (sofort ausführen):
```bash
# Minimal-Befehl der inline bleibt
```
```

### Größen-Schwellen

| LOC | Aktion |
|-----|--------|
| <300 | Status quo, keine Modularisierung |
| 300-500 | Optional: passive Sections auslagern |
| 500-1000 | Empfohlen: alle passiven Sections auslagern |
| >1000 | Pflicht: passive auslagern + Step-Modularisierung prüfen |

## Consequences

### Positiv
- Token-Kosten pro Workflow-Aufruf reduziert
- Workflow-Files bleiben lesbar (Übersicht)
- Pattern wiederholbar bei zukünftigen Refactors
- Externe Files können separat versioniert werden

### Negativ
- Agent muss beim Quick-Check ggf. externes File lesen (1 zusätzlicher Read)
- Auslagerungs-Pfad-Konvention muss eingehalten werden
- Sync-workflows-CI muss `docs/<topic>/` mitschleppen wenn nötig

## Validation Criteria

- [ ] Pilot-Refactor `onboard-repo` (1175→1041) und `new-github-project` (701→664) im Live-Einsatz getestet
- [ ] Agent findet ausgelagerte Checkliste und kann sie bei Verifikation konsultieren
- [ ] Workflow-Pattern in `workflow-review.md` dokumentiert (ergänzt um diese Regeln)
- [ ] 3 weitere Workflows nach Pattern refaktoriert: `platform-audit`, `agentic-coding`, `session-ende`

## Referenzen

- Pilot-Refactor Commits: `f879bf8`, `eb400ea` (2026-04-29)
- Issue #80: P0 MCP-Migration (parallel durchgeführt)
- ADR-066: Agentic Coding Workflow v4 (lineares Step-Modell)
- ADR-145: Knowledge Capture (legt fest dass Wissen extern gespeichert wird)

## Changelog

- 2026-04-29: Initial Proposed nach `/workflow-review` Session mit 2 Pilot-Refactors
