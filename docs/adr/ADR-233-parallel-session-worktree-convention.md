---
status: proposed
implementation_status: partial  # 2026-06-04: pre-commit-Backstop (main-tree-protect) verdrahtet; Snap-back-Hook-Aktivierung via 'tools/main-tree-guard.sh install .' je Checkout
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
überwacht** (gleiches Prinzip wie ADR-234). **Ehrlichkeit nach externer Runde 2:** „unerreichbar" gilt
*nur*, wenn der Guard (Punkt 1) tatsächlich erzwingt; eine bloße Konvention wäre *sozial*, nicht
strukturell. Darum ist der Guard Teil der **Entscheidung**, nicht der Risiko-Mitigation.

1. **Main-Tree heilig — durch harten Guard, nicht durch Ritual (REC-1/AD-1/AD-11):** der geteilte
   Checkout `~/github/<repo>` bleibt dauerhaft auf `main`. Ein **verpflichtender `main-tree-guard`**
   (pre-`checkout`/`switch`-Hook + Sentinel `.git/iil-main-tree-protected`) **blockt** jede
   branch-ändernde Operation im Haupt-Tree und schreibt ein **Guard-Event** ins Audit-Log. Ohne diesen
   Guard ist die Invariante nicht erreicht (siehe Kill-Gate §8).
2. **Per-Session-Worktree via offiziellem Entry Point (REC-2/REC-3/REC-5/REC-8):** jede **editierende
   oder branch-ändernde** Session läuft über **einen** verbindlichen Wrapper
   `repo-session start <repo> --task <slug>`, der: (a) prüft, dass der Haupt-Tree auf `main` ist,
   (b) `git fetch --prune origin main` ausführt, (c) einen Worktree **von `origin/main`** (oder explizitem
   `base_ref`) mit Branch-Schema `session/<YYYY-MM-DD>/<agent-or-user>/<task-slug>` anlegt,
   (d) eine **Lease** schreibt (§2.4), (e) am Ende Reaper-Dry-Run + Summary ausgibt. **Reine Read-only-
   Analyse** darf im Haupt-Tree bleiben (REC-3). Sub-Agenten nutzen die Harness-Isolation
   (`isolation: "worktree"`) — nicht neu erfinden.
   **Isolations-Grenze (REC-4/AD-4):** ein Worktree isoliert Working-Tree/Index/HEAD, **nicht**
   Branch-Namespace, Stash, lokale `git config`, Hooks und Remote-Tracking-Refs. Daher: keine globalen
   `git config`-Änderungen aus Sessions, kein geteilter `git stash`, keine Wiederverwendung aktiver
   Session-Branches.
3. **Integration kontinuierlich durch `main`, nie „wenn ruhig":** kleiner Branch → PR → squash→`main`,
   sofort und asynchron. „Zusammenbringen" ist der normale, durch main rebasende PR-Merge — **kein**
   Warten auf einen quiescenten Moment (der nachweislich nie kommt).
4. **Deterministischer Worktree-Reaper (Pflicht) + Lease-Ledger (REC-6/REC-7):** `tools/worktree-reaper.py`
   entfernt **nur das Worktree-Verzeichnis, nie den Branch** (committed-but-unmerged Arbeit überlebt;
   Restore via `git worktree add <path> <branch>`). Reap-Klassen: **gemergt** (squash-aware via
   `gh pr --state merged`) → Worktree entfernbar; **unmerged + clean + stale** → **nur archivieren/als
   `needs-owner-action` markieren, nie auto-entfernen** (REC-6). **Dirty-Guard** schützt uncommitted
   changes absolut. Die Stale-Entscheidung läuft über eine **maschinenlesbare Lease**
   (`session_id, owner, created_at, last_touch, branch, base_sha, intended_pr, expires_at, ephemeral`)
   statt roher mtime (REC-7/AD-8). Jede Entfernung ins Restore-Manifest (JSONL).

## 3. Betrachtete Alternativen

| # | Alternative | Verdikt |
|---|---|---|
| A | **Status quo** — geteilter Haupt-Tree, Sessions switchen HEAD | verworfen: erlebte HEAD-Flip-Kollision, F1-Lehre |
| B | **„Worktree, dann mergen wenn keine parallelen Tasks laufen"** (Ausgangsvorschlag) | verworfen: **empirisch falsifiziert** — kein quiescenter Moment (11 stale Worktrees); koppelt Isolation an Integration; unbeobachtbare Vorbedingung; verschlimmert Konflikte (langlebige Branches) |
| C | **Isolation ⟂ Integration entkoppelt (gewählt)** — Main-Tree heilig + per-Session-Worktree + kontinuierliche PR→main + Reaper | mehr Worktree-Disziplin, dafür Kollisions-Klasse eliminiert + bestehende PR→main-Konvention konsistent |
| D | **Nur Harness-Isolation** (`isolation: worktree` für Sub-Agenten) | unvollständig: deckt Sub-Agenten ab, **nicht** top-level interaktive Sessions, die heute den Haupt-Tree teilen |
| E | **Full-Clone pro Session** (REC-12/AD-15) | verworfen: isoliert zwar auch lokale config/stash/refs, kostet aber Disk/Netzwerk/Setup und erzeugt Credential-/Remote-Drift; nur Sonderfall (gefährliche lokale Git-Config / große Experimente) |
| F | **Ephemerer Wrapper mit Auto-Create/Auto-Reap** (REC-12/AD-16) | **gewählte Härtung von C** — der Wrapper aus §2.2 *ist* dieser Mechanismus; macht die Konvention praktisch erzwingbar statt freiwillig |
| G (2028-Zielbild) | **Bare/Mirror-Objektanker** statt editierbarem Main-Tree; alle Checkouts sind Worktrees unter `_worktrees/<repo>/<session>` (OOTB-C) | für v1 zu hart (Bruch mit IDE-Pfaden/Gewohnheiten); prüfen, falls Guard/Wrapper nicht zuverlässig wirken |

## 4. Begründung im Detail
- **Kategorientrennung:** Isolation des Working-Tree (Worktree) und Integration der Änderungen (git via
  PR→main) sind orthogonal. Alternative B koppelt sie und erfindet eine Serialisierungs-Barriere, die git
  gerade abschafft.
- **Unerreichbar statt überwacht:** „Main-Tree heilig" macht den HEAD-Flip strukturell unmöglich, statt
  ihn per Disziplin abzufangen — derselbe Hebel wie die Invariante in ADR-234.
- **Reaper gegen Sprawl:** ohne deterministischen GC verlagert „immer Worktree" nur die 32-Branch-Schwemme
  auf die Platte (11 stale Worktrees sind der Backlog).

## 5. Implementation Plan
- `tools/worktree-reaper.py` ✅ gebaut + dry-run-validiert (7 merged erkannt, 2 dirty geschützt) — als
  **versioniertes Plattformtool** (Changelog, Test-Fixtures für squash-merged-PR-Erkennung, fester
  `--dry-run`/`--apply`-Contract; REC-13/M28-8) weiterführen.
- **`tools/main-tree-guard.sh`** (REC-1) ✅ gebaut + getestet: post-checkout-Hook → Snap-back auf `main`
  + Guard-Event-Log; `report` liefert `unauthorized_head_flips/30d` (Kill-Gate-Metrik §8). Ehrliche
  Grenze: git hat keinen Pre-switch-Block → Hook ist Sicherheitsnetz + Messung, der **Wrapper ist der
  eigentliche Enforcer**.
- **`tools/repo-session.sh`** (REC-2) ✅ gebaut + getestet: `start`/`list`/`end`; legt Worktree **von
  `origin/main`** an, Branch-Schema `session/<date>/<owner>/<slug>`, schreibt Lease (REC-7), Dirty-Guard
  bei `end`.
- **Lease-Ledger** (REC-7) ✅ vom Wrapper geschrieben; Reaper-Stale-Logik ✅ auf Lease umgestellt
  (`expires_at` primär, mtime nur Fallback — `worktree-reaper.py:classify`).
- **Geplante Reaper-Invocation** ✅ `infra/host-maintenance/worktree-reaper-all.sh` +
  `worktree-reaper.{service,timer}` (systemd --user, täglich, merged-only `--apply`). Schließt die
  Akkumulations-Wurzel: der Reaper lief bisher nur als Dry-Run am `repo-session end` (nur der eine
  übergebene Tree, nur bei manueller Invocation) → Orphans aus `gh pr merge` ohne `end` blieben liegen.
  Anker für den Längsschnitt-Slug `worktree-orphan-accumulation` (≥2× in session-retros). Host-`enable`
  bleibt expliziter Menschen-Schritt (README); der Merge ändert nichts am Host.
- Konvention + Entry Point in `CORE_CONTEXT.md`/Session-Start-Ritual verankern (ein offizieller Einstieg).
- Einmaliger Cleanup bestehender stale Worktrees — **nur nach Einzel-Freigabe** (fremde/evtl. aktive
  Sessions; destruktive Shared-State-Aktion). *(In dieser Session bereits durchgeführt: 7 gemergte gereapt.)*

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Worktree-Sprawl ohne GC | Reaper-Pflicht; Branch-/Worktree-Namensschema (§2.2); Stale-Report als Frühwarnung |
| R-2 | Reaper entfernt clean-but-unmerged Tree (Verlust nicht-integrierter Arbeit) | Reaper entfernt **nur Worktree-Dir, nie Branch**; unmerged+clean → nur markieren, nie auto-remove (REC-6); Restore-Manifest |
| R-3 | Sessions ignorieren „Main-Tree heilig" | **harter `main-tree-guard` ist jetzt Teil der Entscheidung (§2.1)**, nicht nur Mitigation — branch-ändernde Ops im Haupt-Tree werden geblockt + als Guard-Event gezählt (REC-1/REC-9) |
| R-4 | Disk-Druck — kippt real durch per-Worktree-Artefakte (`.venv`, `node_modules`, Builds, Logs), nicht durch geteilte Git-Objekte (M28-5) | **Disk-/Artefakt-Budget (REC-10):** Standardpfade, Max-Anzahl/Repo, Max-Alter, `reaper --disk-report`; geteilte Caches wo möglich |
| R-5 | Ephemere Experimente vs. PR-fähige Arbeit vermischt (REC-11/AD-13) | Lease-Feld `ephemeral: true|false`; **`/tmp` nur für `ephemeral: true`**, nie für PR-/Übergabe-Arbeit |
| R-6 | **Zwei parallele Sessions arbeiten unbemerkt am selben Thema → Duplikat-/dangling-PRs** (Retro-Gate `parallel-session-pr-collision`, ≥2× über Retros → gate-pflichtig) | **PR-Kollisionscheck in `repo-session.sh start`** (`check_pr_collision`, §5): vor dem Abzweigen `gh pr list` — offener PR mit demselben `--task`-Slug im head-branch = **harter Block**; sonstige offene PRs werden zur Awareness gelistet. Fail-open nur bei fehlendem `gh`/Auth (mit sichtbarem Hinweis, nie still). Bewusste Parallelarbeit: `REPO_SESSION_SKIP_PR_CHECK=1` |

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
- `~/github/<repo>` bleibt nach einer Session auf `main`.
- `worktree-reaper.py` (dry-run) listet gemergte Worktrees korrekt + lässt dirty/unmerged unangetastet
  (entfernt nie einen Branch).
- **Guard wirkt messbar (REC-9/REC-14):** ein absichtlicher `git switch`/`checkout` im Haupt-Tree wird
  **geblockt** und/oder erzeugt ein **Guard-Event** im Audit-Log. Metrik: **`unauthorized_head_flips / 30 Tage`**.
- **Kill-Gate (messbar, datiert):** Wenn bis **2026-09-01** (a) `main-tree-guard` + `repo-session`-Wrapper
  nicht existieren **oder** (b) `unauthorized_head_flips > 0 / 30 Tage` (Guard greift nicht / wird umgangen),
  gilt die Konvention als **nicht erzwingbar** → Status `Deprecated`, zurück auf Status quo mit dokumentierter
  Warnung. „Routinemäßig" ist damit durch eine Zahl ersetzt (M28-6).

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

## 11. Rückfluss externe Review-Runde (Step-5-Tagging)

Externe ADR-Review-Runde (Briefing `~/shared/adr-handoff-ADR-233-2026-06-01.md`): 14 RECs, **alle
`[valid]`**, kein Dissens. Zentraler Treffer: der Leitsatz „unerreichbar by construction" stand im
Widerspruch zu „Main-Tree heilig = Ritual + ggf. Hook" — der Guard ist jetzt **Teil der Entscheidung**.

| REC | Verdikt | Aktion im ADR |
|---|---|---|
| REC-1 (harter Guard statt Ritual) | [valid] | §2.1 `main-tree-guard` verpflichtend; §6 R-3 von Mitigation → Entscheidung |
| REC-2 (offizieller Session-Wrapper) | [valid] | §2.2 `repo-session start` als verbindlicher Entry Point |
| REC-3 (Read-only im Main-Tree erlaubt) | [valid] | §2.2 Scope-Präzisierung |
| REC-4 (Isolations-Grenze) | [valid] | §2.2 Caveat (stash/config/refs nicht isoliert) + Regeln |
| REC-5 (Branch-Namensschema) | [valid] | §2.2 `session/<date>/<agent>/<slug>` |
| REC-6 (unmerged-clean nie auto-remove) | [valid] | §2.4 + §6 R-2: nur Worktree-Dir, nie Branch; markieren statt entfernen |
| REC-7 (Lease-Ledger statt mtime) | [valid] | §2.4 Lease-Felder; §5 Reaper-Umstellung |
| REC-8 (Worktree von origin/main) | [valid] | §2.2 (d); diese Session bereits so praktiziert |
| REC-9 (messbares Kill-Gate) | [valid] | §8 `unauthorized_head_flips / 30 Tage` |
| REC-10 (Disk-/Artefakt-Budget) | [valid] | §6 R-4 (Artefakte, nicht Git-Objekte) |
| REC-11 (ephemer vs persistent) | [valid] | §6 R-5; `/tmp` nur `ephemeral: true` |
| REC-12 (Alternativen E/F) | [valid] | §3 E (Full-Clone, verworfen), F (Wrapper, gewählte Härtung), G (Bare-Anker, 2028) |
| REC-13 (Reaper versionieren) | [valid] | §5 Folge-Item (Changelog, Test-Fixtures, Contract) |
| REC-14 (Validation: switch-block prüfen) | [valid] | §8 Guard-Wirkungs-Kriterium |

## 12. Changelog
- **2026-06-01:** Initial (Proposed). Aus der Advocatus-Diabolus-Review des Vorschlags „immer Worktree,
  dann mergen wenn ruhig" — zweite Hälfte empirisch falsifiziert (11 stale Worktrees), Synthese
  = Isolation ⟂ Integration entkoppeln.
- **2026-06-01:** Externe Review-Runde (14/14 RECs valid) eingearbeitet: harter `main-tree-guard` +
  `repo-session`-Wrapper als Entscheidung (nicht Ritual), Lease-Ledger, geschärfte Reaper-Semantik
  (nie Branch löschen / unmerged-clean nur markieren), messbares Kill-Gate, Disk-Budget, Alternativen
  E/F/G. Tag-Tabelle §11.
- **2026-07-04:** `repo-session.sh reap [<repo>]` + Auto-Reap bei `start` (Retro f5e1d F-P4,
  Gate `worktree-midsession-accumulation` ×2 → Gate-Pflicht, #913): jede neue Session räumt
  zuerst gemergte+cleane Orphan-Worktrees des Ziel-Repos via `worktree-reaper.py --apply` ab
  (self-healing statt neuer Pflicht-Doku; der Pflicht-Reaper lief bisher nur bei /session-ende,
  nicht beim Merger). Best-effort: Reap-Fehler blockieren `start` nie; dirty/un-gemergte
  Worktrees bleiben durch die Reaper-Guards unangetastet.
