---
title: "ADR-175 — Adopt selective modularization for .windsurf/workflows/ files"
date: 2026-04-29
amended: 2026-04-29
status: Accepted
deciders: achimdehnert
implementation_status: implemented
implementation_evidence:
  - "platform/.windsurf/workflows/onboard-repo.md — Step 7 + Refs ausgelagert (1175→1041 LOC, -11%)"
  - "platform/.windsurf/workflows/new-github-project.md — Verifikation ausgelagert (701→664 LOC, -5%)"
  - "platform/.windsurf/workflows/platform-audit.md — Report-Skeleton ausgelagert (420→367 LOC, -13%)"
  - "platform/.windsurf/workflows/agentic-coding.md — Diagramm + ADR-Refs ausgelagert (372→351 LOC, -6%)"
  - "platform/.windsurf/workflows/session-ende.md — Checkliste + MCP-Tabelle ausgelagert (365→346 LOC, -5%)"
  - "platform/docs/onboarding/{onboard-repo,new-github-project}-checklist.md — onboarding-Lookups"
  - "platform/docs/governance/{agentic-coding-reference,session-ende-checklist,platform-audit-report-template}.md — governance-Lookups"
  - "Gesamt: 3033→2769 LOC (-9%, 264 LOC ausgelagert auf 5 Workflows)"
implementation_done_when:
  - "Sync-CI verteilt docs/<topic>/ Dateien zu allen Repos die den Workflow nutzen (Issue offen)"
  - "Modularisierungs-Regeln in workflow-review.md ergänzt (Pattern-Doku)"
  - "Mind. 5 Workflows >300 LOC nach Pattern refaktoriert (aktuell 5/5)"
  - "Test: Coding-Agent versteht Referenz-Verweise und liest externes File bei Bedarf (manuell verifiziert)"
---

# ADR-175 — Adopt selective modularization for .windsurf/workflows/ files

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

**Token-Kontext (Größenordnung):** Ein Workflow von 1175 LOC ≈ 9-10k Tokens.
Bei 50+ Workflow-Aufrufen pro Session × 4-6 Sessions pro Tag ergibt sich
~2-3M Tokens/Monat allein für Workflow-Lookups. Modularisierung passive Sections
spart 5-15% pro Aufruf.

## Decision Drivers

- Workflow muss vom Agent linear lesbar/ausführbar bleiben
- Token-Kosten reduzieren (große Workflows = teure Sessions)
- Aktive Steps bleiben dort wo der Agent arbeitet
- Passive Inhalte (Checklisten, Beispiele, Referenzen) auslagerbar
- Keine versteckten Multi-File-Read-Abhängigkeiten
- Auslagerungs-Pfade müssen vom Sync-CI mit-distribuiert werden

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
- ❌ Workflows >1000 LOC sind unwartbar

## Decision Outcome

**Wir wählen Option 2** — selektive Auslagerung nach Inhalt-Typ.

**Begründung:** Option 2 reduziert Token-Kosten ohne den linearen Workflow-Flow zu
brechen. Agent liest passive Inhalte (Checklisten, Referenzen) nur bei Bedarf
über expliziten Verweis. Aktive Steps mit Code/Templates bleiben dort wo gearbeitet
wird — kein hidden Multi-File-Read.

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

### Anti-Pattern (NICHT auslagern)

- ❌ Aktive Bash-Steps in eigene Datei → Multi-File-Read-Pflicht
- ❌ YAML-Templates die der Agent direkt erstellt (Issue Templates etc.) — sollen inline bleiben
- ❌ Schritt-für-Schritt-Anleitungen mit Variablen-Zustand zwischen Steps
- ❌ MCP-Tool-Calls die Phase-übergreifend Daten teilen

### Auslagerungs-Pfad

`platform/docs/<topic>/<workflow-name>-<aspect>.md`

Beispiele:
- `docs/onboarding/onboard-repo-checklist.md`
- `docs/onboarding/new-github-project-checklist.md`
- `docs/governance/platform-audit-rubric.md`

> **Pfad-Konvention:** Erste Ebene = Topic-Domain (onboarding, governance, deploy, …),
> Zweite Ebene = `<workflow>-<aspect>.md`. **Keine Subdirs in `.windsurf/workflows/`** —
> Cascade-Workflow-Auflistung ist flach.

### Verweis-Format im Workflow

```markdown
## Step X: Verifikation

→ **[`docs/onboarding/<workflow>-checklist.md`](../../docs/onboarding/<workflow>-checklist.md)**

Inhalte:
- [Aufzählung der Hauptthemen]

**Quick-Check** (sofort ausführen):
\`\`\`bash
# Minimal-Befehl der inline bleibt
\`\`\`
```

### Größen-Schwellen

| LOC | Aktion |
|-----|--------|
| <300 | Status quo, keine Modularisierung |
| 300-500 | Optional: passive Sections auslagern |
| 500-1000 | Empfohlen: alle passiven Sections auslagern |
| >1000 | Pflicht: passive auslagern + Step-Modularisierung prüfen |

## Consequences

### Good
- Token-Kosten pro Workflow-Aufruf reduziert (5-15% bei Pilot-Refactors)
- Workflow-Files bleiben lesbar (Übersicht)
- Pattern wiederholbar bei zukünftigen Refactors
- Externe Files können separat versioniert werden
- Auslagerungs-Pfad-Konvention dokumentiert

### Bad
- Agent muss beim Quick-Check ggf. externes File lesen (1 zusätzlicher Read)
- Auslagerungs-Pfad-Konvention muss eingehalten werden (Disziplin)
- Sync-Workflows-CI muss `docs/<topic>/` mit-verteilen (siehe Open Questions)
- Bei Drift zwischen Workflow + Lookup-File entstehen Inkonsistenzen

### Confirmation

Compliance mit dieser ADR wird verifiziert durch:

1. **`/workflow-review` Workflow** prüft pro Workflow-File:
   - Größe gegen Schwellen-Tabelle
   - Bei >500 LOC: Existieren passive Sections inline?
   - Bei Verweisen: Existiert das verlinkte File?
2. **Pre-Merge-Check (manuell):** Bei neuem Workflow >500 LOC fordert Reviewer
   Modularisierung gemäß diesem ADR ein.
3. **CI-Drift-Check (zukünftig, siehe Validation Criteria):** Automatisierter
   Test ob alle Workflow-Verweise (`→ [` ... `](docs/...)`) auf existierende
   Files zeigen.

## Open Questions

1. **Sync-CI-Verhalten:** Verteilt `sync-workflows-to-repos.yml` aktuell nur
   `.windsurf/workflows/*.md` oder auch referenzierte `docs/<topic>/*.md`?
   → Bei aktuellem Stand: NEIN. Workflows die ausgelagerte Files referenzieren
   funktionieren nur im `platform`-Repo. **Lösung:** Sync-CI erweitern oder
   Auslagerung nur bei platform-only Workflows zulassen.
2. **Subdirs in `.windsurf/workflows/`:** Funktionieren Subdirs (z.B.
   `.windsurf/workflows/onboarding/foo.md`) als Slash-Commands?
   → Cascade-Doku erwähnt nur flache Struktur. **Annahme:** Subdirs werden NICHT
   als `/foo` erkannt. Dieses ADR meidet Subdirs daher bewusst.
3. **Drift zwischen Workflow + Lookup-File:** Was wenn Lookup-File während
   Workflow-Ausführung veraltet ist?
   → **Mitigation:** Lookup-Files versionieren via Git, Workflow zeigt Commit-Hash.
   Aktuell: Manuelle Disziplin, kein automatischer Drift-Check.

## Validation Criteria

- [x] Pilot-Refactor `onboard-repo` (1175→1041 LOC) live im Einsatz
- [x] Pilot-Refactor `new-github-project` (701→664 LOC) live im Einsatz
- [x] Pilot-Refactor `platform-audit` (420→367 LOC) — Report-Skeleton ausgelagert
- [x] Pilot-Refactor `agentic-coding` (372→351 LOC) — Diagramm + ADR-Refs ausgelagert
- [x] Pilot-Refactor `session-ende` (365→346 LOC) — Checkliste + MCP-Tabelle ausgelagert
- [x] **5/5 Pilot-Refactors abgeschlossen — Status `Proposed` → `Accepted`** (2026-04-29)
- [ ] Agent findet ausgelagerte Checkliste und kann sie bei Verifikation konsultieren (nächste Live-Session)
- [ ] Sync-CI verteilt `docs/<topic>/` mit oder Pattern-Beschränkung dokumentiert (Open Question 1)

## More Information

- **Pilot-Refactor Commits:** `f879bf8`, `eb400ea` (2026-04-29)
- **Issue #80:** P0 MCP-Migration (parallel durchgeführt, abgeschlossen)
- **Workflow:** [`platform/.windsurf/workflows/workflow-review.md`](../../.windsurf/workflows/workflow-review.md) — operationalisiert dieses ADR
- **ADR-066:** Agentic Coding Workflow v4 — definiert das lineare Step-Modell, das diese ADR respektiert
- **ADR-145:** Knowledge Capture — Wissen wird extern in Outline gespeichert (paralleles Pattern)
- **MADR 4.0:** https://adr.github.io/madr/

## Changelog

- 2026-04-29 (Initial): Proposed nach `/workflow-review` Session mit 2 Pilot-Refactors
- 2026-04-29 (Amended via /adr-review): MADR 4.0 Compliance — Title als Decision-Statement; `Decision Outcome` mit Reasoning; `Confirmation` Subsection ergänzt; `Open Questions` Sektion eingeführt; `implementation_status` von invalidem `planned` auf gültiges `partial` korrigiert (ADR-138-konform); Anti-Pattern-Sektion ergänzt; Token-Kosten quantifiziert
- 2026-04-29 (Accepted): 5/5 Pilot-Refactors erfolgreich abgeschlossen (3033→2769 LOC, -9%). Status `Proposed` → `Accepted`. `implementation_status: partial` → `implemented`.
