---
status: "accepted"
date: 2026-02-23
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related: ["ADR-046-docs-hygiene.md", "ADR-057-platform-test-strategy.md", "ADR-066-ai-engineering-team.md"]
implementation_status: implemented
---

# Adopt GitHub Issues + Projects as the single source of truth for work management across human and AI team members

| Attribut       | Wert                                                                                      |
|----------------|-------------------------------------------------------------------------------------------|
| **Status**     | Proposed                                                                                  |
| **Scope**      | Platform-wide                                                                             |
| **Repo**       | platform                                                                                  |
| **Erstellt**   | 2026-02-23                                                                                |
| **Autor**      | Achim Dehnert                                                                             |
| **Relates to** | ADR-046 (Docs Hygiene), ADR-057 (Test Strategy), ADR-066 (AI Engineering Team)           |

---

## Context and Problem Statement

Die Plattform wächst von Solo-Entwicklung zu einem gemischten Team aus menschlichen Entwicklern und AI-Agenten (Windsurf Cascade, zukünftig weitere MCP-basierte Agenten). Apps sollen produktiv und langfristig betrieben werden.

Ohne standardisiertes Work Management entstehen folgende Probleme:

1. **AI-Agenten haben keinen Kontext** — Agenten sehen technische Schuld im Code, wissen aber nicht ob sie bereits getrackt, priorisiert oder bewusst zurückgestellt ist.
2. **Deferred Decisions verschwinden** — ADR-Einträge ohne Issue-Verlinkung werden nicht umgesetzt (kein Ownership, kein Zieldatum-Tracking).
3. **Parallele Arbeit ohne Koordination** — mehrere Agenten oder Entwickler arbeiten an denselben Dateien ohne Sichtbarkeit.
4. **Kein Definition of Done** — PRs werden gemergt ohne klare Akzeptanzkriterien, Regressions entstehen.
5. **Fehlende Roadmap** — langfristige Produktentscheidungen sind nur in ADRs dokumentiert, nicht als priorisierter Backlog sichtbar.

---

## Decision Drivers

- **AI-Agenten-Kompatibilität**: Maschinenlesbare Strukturen — Label-Schema, Linking-Konventionen, automatisch prüfbare Regeln
- **Single Source of Truth**: Ein Tool für alle Repos, kein Wechsel zwischen Jira/Linear/Notion/GitHub
- **Minimalinvasivität**: Kein neues externes Tool — GitHub ist bereits vorhanden und in CI/CD integriert
- **Skalierbarkeit**: Funktioniert für 1 Person heute und für 10+ Personen + Agenten morgen
- **Nachvollziehbarkeit**: ADR ↔ Issue ↔ PR ↔ Deploy — lückenlose Traceability für Audits und Agenten
- **Langzeitbetrieb**: Produktive Apps brauchen kontrollierte Change-Prozesse, nicht Ad-hoc-Fixes

---

## Considered Options

1. **Kein formales Issue Management** — weiter wie bisher: TODO-Kommentare im Code, ADR-Einträge
2. **GitHub Issues only** — Issues pro Repo, Labels, Milestones, kein übergreifendes Backlog
3. **GitHub Issues + Projects (gewählt)** — Issues pro Repo + GitHub Projects als plattformweites Backlog + AI-Agent-Protokoll
4. **Externes Tool (Linear/Jira)** — dediziertes PM-Tool mit GitHub-Integration

---

## Decision Outcome

**Gewählt: Option 3 — GitHub Issues + Projects + AI-Agent-Protokoll**, weil:

- Option 1 skaliert nicht auf Team + AI-Agenten — Agenten haben keinen strukturierten Kontext.
- Option 2 fehlt die plattformweite Übersicht — bei 8+ Repos ist ein übergreifendes Backlog notwendig.
- Option 4 führt ein externes Tool ein, das synchronisiert werden muss — erhöht Komplexität ohne Mehrwert bei aktuellem Teamgröße.
- Option 3 nutzt GitHub nativ, ist für AI-Agenten über die GitHub API vollständig maschinenlesbar, und skaliert von Solo bis Team.

### Consistency Check mit bestehenden ADRs

| ADR | Relevanz | Konsistenz |
|-----|----------|------------|
| ADR-046 (Docs Hygiene) | Dokumentationsstandards | ✅ Issues ergänzen ADRs, ersetzen sie nicht |
| ADR-057 (Test Strategy) | Deferred Decisions in Tests | ✅ Alle Deferred Decisions erhalten Issue-Links |
| ADR-066 (AI Engineering Team) | AI-Agenten als Team-Mitglieder | ⚠️ ADR-066 ist `Proposed`, noch nicht implementiert — AI-Agent-Protokoll in ADR-067 ist Vorarbeit dafür |

### Confirmation

Compliance wird auf zwei Wegen verifiziert:

1. **CI-Check** (GitHub Actions): PR ohne verlinktes Issue wird mit Warning markiert (nicht blockiert — Ausnahme: `hotfix`-Label).
2. **Guardian-Audit** (monatlich):

```bash
# Issues ohne Milestone (sollten < 20% sein)
gh issue list --repo achimdehnert/bfagent --state open --json number,milestone \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for i in d if not i['milestone']), 'ohne Milestone von', len(d))"

# PRs ohne Issue-Referenz (Ziel: 0 außer hotfix)
gh pr list --repo achimdehnert/bfagent --state merged --json number,body \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for p in d if 'closes #' not in p['body'].lower() and 'fixes #' not in p['body'].lower()), 'PRs ohne Issue-Link')"
```

---

## Pros and Cons of the Options

### Option 1 — Kein formales Issue Management

* Good, because kein Overhead — direkt coden.
* Bad, because AI-Agenten haben keinen strukturierten Arbeitskontext.
* Bad, because technische Schuld ist unsichtbar und wird nicht umgesetzt.
* Bad, because bei Team-Wachstum sofort unlösbar.
* **Abgelehnt.**

### Option 2 — GitHub Issues only

* Good, because einfach, kein zusätzliches Tool.
* Good, because GitHub API ist für AI-Agenten zugänglich.
* Bad, because kein plattformweites Backlog über alle 8+ Repos.
* Bad, because keine Roadmap-Sicht für langfristige Planung.

### Option 3 — GitHub Issues + Projects + AI-Agent-Protokoll (gewählt)

* Good, because Single Source of Truth — alles in GitHub.
* Good, because GitHub Projects gibt plattformweite Roadmap-Sicht.
* Good, because vollständig maschinenlesbar via GitHub API für AI-Agenten.
* Good, because skaliert von 1 Person zu 10+ Personen + Agenten ohne Tool-Wechsel.
* Good, because ADR ↔ Issue ↔ PR ↔ Deploy Traceability ist vollständig.
* Bad, because GitHub Projects ist weniger mächtig als Linear/Jira (kein Time-Tracking, kein Gantt).
* Bad, because initiale Label-Taxonomie und Project-Struktur muss einmalig aufgebaut werden.

### Option 4 — Externes Tool (Linear/Jira)

* Good, because mächtigere PM-Features (Sprints, Gantt, Time-Tracking).
* Bad, because zusätzliches Tool das synchronisiert werden muss.
* Bad, because AI-Agenten brauchen separate Integration.
* Bad, because Kosten bei Team-Wachstum.
* **Abgelehnt.**

---

## Consequences

* Good, because AI-Agenten können Issues lesen, kommentieren und schließen — vollständiger Arbeitskontext.
* Good, because technische Schuld aus ADR Deferred Decisions ist immer als Issue trackbar.
* Good, because plattformweite Roadmap in GitHub Projects sichtbar für alle Team-Mitglieder.
* Good, because PR ↔ Issue ↔ ADR Traceability ermöglicht lückenlose Nachvollziehbarkeit.
* Bad, because Label-Taxonomie muss initial aufgebaut und diszipliniert gepflegt werden.
* Bad, because GitHub Projects ist kein vollwertiges PM-Tool — komplexe Abhängigkeiten bleiben in ADRs.

---

## Implementation Details

### 1. Label-Taxonomie (plattformweit, alle Repos)

| Kategorie | Labels | Farbe |
|-----------|--------|-------|
| **Typ** | `bug`, `enhancement`, `task`, `use-case`, `adr`, `hotfix`, `tech-debt`, `ci-cd` | Blau-Töne |
| **Severity** | `severity:critical`, `severity:high`, `severity:medium`, `severity:low` | Rot → Grün |
| **Status** | `triage`, `blocked`, `wontfix` | Gelb-Töne |
| **Meta** | `documentation`, `security`, `performance`, `dependencies`, `good first issue` | Grau |
| **AI-Agent** | `ai-assignable`, `ai-in-progress`, `ai-review-needed` | Lila |

> **Amendment 2026-02-26**: `P0/P1/P2/P3`-Labels durch `severity:*`-Labels ersetzt.
> Begründung: Severity beschreibt das *Problem* (technische Schwere), Priority ist ein *Workflow-Attribut*
> das im GitHub Project Field `Priority` abgebildet wird — automatisch gesetzt durch `issue-triage.yml`
> via `severity:*` → `Critical/High/Medium/Low`. Keine redundante Label-Ebene nötig.
> Bootstrap-Script: `.github/scripts/bootstrap_labels.py` (idempotent, alle 10 Repos).

**Regel**: Jedes Issue hat mindestens einen Typ-Label. Bug-Issues zusätzlich einen Severity-Label.

### 2. Issue-Template (Standard)

```markdown
## Kontext
[Warum existiert dieses Issue? Welches Problem löst es?]

## Aufgaben
- [ ] [Konkrete Aufgabe 1]
- [ ] [Konkrete Aufgabe 2]

## Akzeptanzkriterien
- [Messbares Kriterium 1]
- [Messbares Kriterium 2]

## Referenzen
- ADR: [Link falls relevant]
- PR: [wird beim Schließen ergänzt]
```

### 3. AI-Agent-Protokoll

AI-Agenten (Windsurf Cascade und zukünftige MCP-Agenten) folgen diesen Regeln:

**Beim Starten einer Aufgabe:**
```
1. Issue suchen: gh issue list --label "ai-assignable" --assignee ""
2. Issue assignen: gh issue edit <N> --add-assignee "@me"
3. Label setzen: gh issue edit <N> --add-label "ai-in-progress"
4. Branch erstellen: git checkout -b "ai/<issue-N>-<slug>"
```

**Beim Abschließen:**
```
1. PR erstellen mit "Closes #<N>" im Body
2. Label: gh issue edit <N> --add-label "ai-review-needed" --remove-label "ai-in-progress"
3. ADR aktualisieren falls Deferred Decision geschlossen wird
```

**Beim Entdecken von technischer Schuld (ohne bestehendes Issue):**
```
1. Prüfen ob Issue existiert: gh issue list --search "<Stichwort>"
2. Falls nicht: Issue erstellen mit Label "tech-debt", "needs-triage", "ai-assignable"
3. Code-Kommentar: # TODO: tracked in github.com/achimdehnert/<repo>/issues/<N>
```

### 4. GitHub Projects Struktur

**Projekt**: `Platform Roadmap` (org-level, alle Repos)

| View | Zweck |
|------|-------|
| **Backlog** | Alle offenen Issues, nach Priorität sortiert |
| **Sprint** (2-Wochen) | Aktive Issues — human + AI assigniert |
| **Roadmap** | Milestones als Zeitachse (Q1/Q2/Q3/Q4) |
| **Tech Debt** | Gefiltert auf Label `tech-debt` — Zieldaten sichtbar |

### 5. Milestone-Struktur

| Milestone | Zeitraum | Inhalt |
|-----------|----------|--------|
| `2026-Q1` | Jan–Mär 2026 | CI-Stabilisierung, ADR-Backlog |
| `2026-Q2` | Apr–Jun 2026 | Factory Boy, View-Test-Reparatur, AI-Team-Aufbau |
| `2026-Q3` | Jul–Sep 2026 | E2E-Tests, Playwright, Skalierung |
| `2026-Q4` | Okt–Dez 2026 | Produktionsreife, Monitoring, SLOs |

### 6. Linking-Konvention (ADR ↔ Issue ↔ PR)

```
ADR-065 Deferred Decision
    └── bfagent#10 (Issue: View-Tests reparieren)
            └── PR #15: "fix(tests): repair view tests — Closes #10"
                    └── ADR-065 Deferred Decisions Tabelle: Issue-Link + "Resolved"
```

**Pflicht**: Jeder PR der eine Deferred Decision schließt, aktualisiert die ADR-Tabelle.

---

## Risks

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|--------------------|--------|------------|
| Label-Taxonomie wird nicht gepflegt | Mittel | Mittel | Guardian-Audit monatlich; CI-Warning bei Issues ohne Pflicht-Labels |
| AI-Agenten erstellen Duplikat-Issues | Mittel | Niedrig | Suchpflicht vor Issue-Erstellung (Schritt 1 im AI-Protokoll) |
| GitHub Projects wird nicht genutzt | Mittel | Mittel | Wöchentlicher Backlog-Review als Team-Ritual |
| Issue-Backlog wächst unkontrolliert | Niedrig | Hoch | Monatlicher Triage-Termin; Issues ohne Aktivität nach 90 Tagen → `P3-low` oder schließen |
| GitHub API Rate Limits bei vielen Agenten | Niedrig | Niedrig | Caching in MCP-Hub; max. 1 API-Call pro Agenten-Schritt |

---

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum | Referenz |
|--------------|------------|-----------|----------|
| GitHub Actions CI-Check für PR-Issue-Linking | Technische Implementierung nach Team-Aufbau | 2026-Q2 | ADR-066 (Proposed) |
| Automatische Issue-Erstellung aus ADR Deferred Decisions | MCP-Tool `create_issue_from_adr` | 2026-Q3 | ADR-044 (MCP-Hub) |
| SLA-Definition für AI-assignable Issues | Wenn Team > 3 AI-Agenten aktiv | 2026-Q3 | ADR-066 (Proposed) |
| AI Engineering Team implementieren (ADR-066 → Accepted) | Voraussetzung für volles AI-Agent-Protokoll | 2026-Q2 | ADR-066 |

---

## More Information

- GitHub Issues API: https://docs.github.com/en/rest/issues
- GitHub Projects API: https://docs.github.com/en/issues/planning-and-tracking-with-projects
- ADR-066: AI Engineering Team — Rollen und Gate-Workflows (`Proposed`, noch nicht implementiert)
- ADR-046: Docs Hygiene — Dokumentationsstandards
- Bestehende Issues als Referenz: [bfagent#10](https://github.com/achimdehnert/bfagent/issues/10), [bfagent#12](https://github.com/achimdehnert/bfagent/issues/12)

---

## Changelog

| Datum      | Autor         | Änderung              |
|------------|---------------|-----------------------|
| 2026-02-23 | Achim Dehnert | Initial — Status: Proposed |
| 2026-02-23 | Achim Dehnert | Fix: ADR-066 als `Proposed` (nicht implementiert) korrekt referenziert |
| 2026-02-26 | Achim Dehnert | Amendment: `P0/P1/P2/P3` → `severity:*` Labels; `issue-triage.yml` + `bootstrap_labels.py` auf alle 10 Repos ausgerollt |
