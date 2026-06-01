---
status: proposed
implementation_status: none
date: 2026-06-01
decision-makers: Achim Dehnert
domains: [dx, git-workflow, drift-prevention, governance]
scope: platform
relates_to: [ADR-021, ADR-209, ADR-234]
tags: [git, worktree, parallel-sessions, branch-strategy, integration, claude-code, cross-repo]
---

# ADR-233: Parallel-Session-Worktree-Konvention — Isolation von Integration entkoppeln

| Attribut       | Wert                                                    |
|----------------|---------------------------------------------------------|
| **Status**     | Proposed                                                |
| **Scope**      | platform (org-weit, alle Repos & Coding-Sessions)       |
| **Repo**       | platform                                                |
| **Erstellt**   | 2026-06-01                                              |
| **Autor**      | Achim Dehnert                                           |
| **Reviewer**   | –                                                       |
| **Supersedes** | –                                                       |
| **Relates to** | ADR-021, ADR-209, ADR-234                               |

---

## 1. Kontext

### 1.1 Ausgangslage
Mehrere Coding-Sessions (Claude-Code, parallele Agenten, Hintergrund-Workflows) arbeiten gleichzeitig
auf **einem geteilten** Haupt-Working-Tree pro Repo (`~/github/<repo>`). Jede Session `switch`t dort
den Branch nach Bedarf.

### 1.2 Problem / Lücken (evidenzbasiert, 2026-06-01 verifiziert)
- **Geteilter HEAD-Flip:** Während der ADR-234-Arbeit sprang der Haupt-Tree `~/github/platform` unter
  der laufenden Session von `feat/repo-ready-skill` → `feat/konzept-skill` → `feat/repo-ready-skill`
  um — eine andere Session hatte den HEAD umgeschaltet. Editieren auf dem falschen Branch wäre die Folge
  (vermieden nur durch die House-Rule „Branch vor jedem Edit bestätigen").
- **Worktree-Friedhof:** `git worktree list` zeigte **11 Worktrees**, ältester **12 Tage**, die meisten
  **unmerged und nie aufgeräumt** — der empirische Beleg, dass „später zusammenbringen, wenn keine
  parallelen Tasks laufen" nie eintritt.
- **Branch-Sprawl:** 32 lokale Branches.
- **Verwandte Lehre:** F1-dev-hub-Kollision — ein `git rm --cached` im fremden aktiven Working-Tree
  staged 50 Löschungen in deren Branch (`feedback`-Memory).

### 1.3 Constraints
- Die Plattform mandatiert bereits **PR→`main`** mit „branch up to date with base" + required checks
  (ADR-021-Linie) — kontinuierliche Integration durch main ist der akzeptierte Pfad.
- Worktrees sind nicht gratis (Disk, ~200–500 ms Setup) → „immer Worktree" braucht eine GC-Disziplin.
- Deterministisch/strukturell, kein LLM für die Aufräum-Entscheidung (Repo-Health-Disziplin).

## 2. Entscheidung

**Isolation und Integration werden entkoppelt — der schlechte Zustand wird unerreichbar gemacht, nicht
überwacht** (gleiches Prinzip wie ADR-234):

1. **Main-Tree heilig:** der geteilte Repo-Checkout `~/github/<repo>` bleibt **dauerhaft auf `main`**
   (Referenz). **Keine** Session `switch`t den HEAD dieses Trees. Damit verschwindet die Klasse
   „HEAD-Flip unter fremder Session" by construction.
2. **Per-Session-Worktree:** jede Session, die editiert (auch top-level interaktiv), arbeitet auf einem
   **eigenen Branch in einem eigenen `git worktree`**. Sub-Agenten nutzen die Harness-Isolation
   (`isolation: "worktree"`) — nicht neu erfinden.
3. **Integration kontinuierlich durch `main`, nie „wenn ruhig":** kleiner Branch → PR → squash→`main`,
   sofort und asynchron. „Zusammenbringen" ist der normale, durch main rebasende PR-Merge — **kein**
   Warten auf einen quiescenten Moment (der nachweislich nie kommt).
4. **Deterministischer Worktree-Reaper (Pflicht):** `tools/worktree-reaper.py` GC't Worktrees, deren
   Branch **gemergt** ist (squash-aware via PR-`mergedAt`/`headRefOid`) oder **>N Tage unberührt** —
   mit Dirty-Guard (nie einen Tree mit uncommitted changes anfassen) und Restore-Manifest.

## 3. Betrachtete Alternativen

| # | Alternative | Verdikt |
|---|---|---|
| A | **Status quo** — geteilter Haupt-Tree, Sessions switchen HEAD | verworfen: erlebte HEAD-Flip-Kollision, F1-Lehre |
| B | **„Worktree, dann mergen wenn keine parallelen Tasks laufen"** (Ausgangsvorschlag) | verworfen: **empirisch falsifiziert** — kein quiescenter Moment (11 stale Worktrees); koppelt Isolation an Integration; unbeobachtbare Vorbedingung; verschlimmert Konflikte (langlebige Branches) |
| C | **Isolation ⟂ Integration entkoppelt (gewählt)** — Main-Tree heilig + per-Session-Worktree + kontinuierliche PR→main + Reaper | mehr Worktree-Disziplin, dafür Kollisions-Klasse eliminiert + bestehende PR→main-Konvention konsistent |
| D | **Nur Harness-Isolation** (`isolation: worktree` für Sub-Agenten) | unvollständig: deckt Sub-Agenten ab, **nicht** top-level interaktive Sessions, die heute den Haupt-Tree teilen |

## 4. Begründung im Detail
- **Kategorientrennung:** Isolation des Working-Tree (Worktree) und Integration der Änderungen (git via
  PR→main) sind orthogonal. Alternative B koppelt sie und erfindet eine Serialisierungs-Barriere, die git
  gerade abschafft.
- **Unerreichbar statt überwacht:** „Main-Tree heilig" macht den HEAD-Flip strukturell unmöglich, statt
  ihn per Disziplin abzufangen — derselbe Hebel wie die Invariante in ADR-234.
- **Reaper gegen Sprawl:** ohne deterministischen GC verlagert „immer Worktree" nur die 32-Branch-Schwemme
  auf die Platte (11 stale Worktrees sind der Backlog).

## 5. Implementation Plan
- `tools/worktree-reaper.py` (dry-run default; `--apply`; squash-aware merged-Erkennung via `gh pr`;
  Dirty-Guard; Stale-Schwelle; Restore-Manifest JSONL).
- Konvention in `CORE_CONTEXT.md`/Session-Start-Ritual verankern (Main-Tree heilig; Session = Worktree).
- Einmaliger Cleanup der 11 bestehenden stale Worktrees — **nur nach Einzel-Freigabe** (fremde/evtl.
  aktive Sessions; destruktive Shared-State-Aktion).

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Worktree-Sprawl ohne GC | Reaper-Pflicht; Stale-Report als Frühwarnung |
| R-2 | Reaper entfernt dirty/unmerged Tree (Datenverlust) | harter Dirty-Guard + nur PR-merged als Reap-Kriterium; Restore-Manifest |
| R-3 | Sessions ignorieren „Main-Tree heilig" | Session-Start-Ritual + ggf. Hook, der HEAD-Switch im Haupt-Tree warnt |
| R-4 | Disk-Druck durch viele Worktrees | Reaper-Stale-Schwelle; Worktrees unter `/tmp` für kurzlebige |

## 7. Konsequenzen
### 7.1 Positiv
- HEAD-Flip-Kollision strukturell eliminiert; konsistent mit bestehender PR→main-Integration.
- Stale-Worktree-Friedhof wird messbar + automatisch abbaubar.
### 7.2 Trade-offs
- Mehr Worktree-Handling pro Session; leichte Disk-/Setup-Kosten.
### 7.3 Nicht in Scope
- Heilung/Entfernung bestehender fremder Worktrees ohne Freigabe (destruktiv, Einzelfall).
- Andere Orgs (`ttz-lif`, `meiki-lra`) — Konvention gilt, aber kein org-übergreifender Enforcement-Mechanismus.

## 8. Validation Criteria
- `~/github/<repo>` bleibt nach einer Session auf `main` (kein fremder HEAD-Flip messbar).
- `worktree-reaper.py` (dry-run) listet gemergte Worktrees korrekt + lässt dirty/unmerged unangetastet.
- **Kill-/Review-Gate:** Wenn bis **2026-09-01** der Reaper nicht existiert *oder* der Haupt-Tree weiter
  routinemäßig HEAD-geflippt wird → Konvention gescheitert, zurück auf Status quo mit dokumentierter Warnung.

## 9. Glossar

| Begriff | Bedeutung |
|---|---|
| **ADR** | Architecture Decision Record. |
| **git worktree** | Mehrere Arbeitsverzeichnisse desselben Repos, je auf eigenem Branch, ein gemeinsames `.git`. |
| **HEAD** | Der aktuell ausgecheckte Branch/Commit eines Working-Tree. |
| **Squash-Merge** | PR-Merge, der alle Branch-Commits zu einem auf `main` zusammenfasst (Branch-Commits sind danach keine Ancestors von main). |
| **Reaper** | Aufräum-Werkzeug, das nicht mehr benötigte Worktrees/Branches entfernt. |
| **Dirty-Guard** | Schutz: ein Working-Tree mit uncommitted changes wird nie automatisch entfernt. |
| **Restore-Manifest** | Protokoll (Pfad/Branch/SHA) entfernter Worktrees zur Wiederherstellbarkeit. |

## 10. Referenzen
- **ADR-234** Clean-State-Invariante (gleiches „unerreichbar statt überwacht"-Prinzip).
- **ADR-021** Unified Deployment Pattern (PR→main-Linie).
- Memory `feedback_branch_cleanup_squash_worktree` (squash-aware, Worktree-Branches ausschließen,
  Restore-Manifest) · `project_f1_windsurf_untrack_rollout` (dev-hub-Shared-Tree-Kollision).

## 11. Changelog
- **2026-06-01:** Initial (Proposed). Aus der Advocatus-Diabolus-Review des Vorschlags „immer Worktree,
  dann mergen wenn ruhig" — zweite Hälfte empirisch falsifiziert (11 stale Worktrees), Synthese
  = Isolation ⟂ Integration entkoppeln.
