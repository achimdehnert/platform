---
description: Offene GitHub-Issues EINES Repos triagieren und gate-freie selbst abarbeiten (1 PR/Issue, Stopp bei Judgment/Infra)
mode: write
---

# /issues-offen — Open-Issue Worker (single repo, gated)

> **Zweck:** Live die offenen Issues eines Repos von GitHub holen, triagieren
> und die *gate-freien* selbst erledigen — ein PR pro Issue, harter Stopp bei
> Judgment/Infra. Frischer, idempotenter Lauf → schedule-tauglich
> (`/schedule /issues-offen <repo>`), KEINE Endlos-Session.
>
> **Wann:** "Erledige, was in `<repo>` offen ist", ohne vorab geplanten Handoff.
> **Wann NICHT:** Es gibt einen dokumentierten Handoff/NÄCHSTE-AKTIONEN →
> `/issues-abarbeiten`. Multi-Repo `auto`-Queue über Nacht → `/process-agent-queue`.
> **Abgrenzung:** `/issues-abarbeiten` setzt einen *geplanten* Stand fort (Quelle =
> Memory-Handoff). `/issues-offen` startet *frisch aus `gh issue list`* (Quelle =
> GitHub) und triagiert selbst.

## Verwendung

```
/issues-offen <repo>          # z.B. /issues-offen risk-hub
/issues-offen                 # ohne Arg: aktuelles Repo aus cwd
```

`$ARGUMENTS` = Repo-Kurzname. Default: aktuelles Repo.

## Step 0: Repo-Kontext (NICHT hardcoden)

1. Repo bestimmen: `$ARGUMENTS` → `<repo>`; sonst Basename von `git rev-parse --show-toplevel`.
2. Owner/Org NICHT raten — aus dem Repo lesen:
   `gh repo view --json nameWithOwner -q .nameWithOwner` im Zielrepo
   (`~/github/<repo>`), bzw. `project-facts.md`. Niemals `achimdehnert` o.ä. hardcoden.
3. pgvector-Tunnel optional; dieser Workflow braucht ihn nicht.

## Phase 1: Holen + Triage (read-only)

1. `gh issue list --repo <owner>/<repo> --state open --limit 50 --json number,title,labels,milestone`
2. Jedes Issue in genau einen Eimer einsortieren:

   **DO-NOW (gate-frei, selbst erledigen)** — wenn ALLE zutreffen:
   - Label `ai-assignable` ODER `automated` ODER (`type:bug` + `complexity:simple`)
     ODER `documentation`/`docu-update`
   - KEIN `P1`/`P0`/`blocked`/`needs-discussion`/`security`
   - Titel/Body enthält KEINE Judgment-/Infra-Marker (siehe STOP)

   **STOP (nur listen, NICHT anfassen)** — sobald EINES zutrifft:
   - ADR-Bezug, Migration, Deploy/Infra, Secrets/Security, DSGVO-Wertung
   - "architektur", "cross-repo", Schema-/Datenmodell-Entscheidung
   - `P1`/`P0`, oder Label `needs-discussion`/`blocked`
   - Issue ohne klaren, umrissenen Scope (Diskussion/Konzept)

   **SKIP** — kein actionable Code (Frage, Duplikat, `wontfix`, fremd-assigned).
3. DO-NOW nach Priorität ordnen (P2 > P3 > unlabelled), Cap: **max 5 Issues/Lauf**.
4. Plan als Tasks materialisieren (`TaskCreate`), ein Task pro DO-NOW-Issue.

## Phase 2: Guardrails (vor JEDER Aktion)

1. **Kein Duplikat:** `gh pr list --repo <owner>/<repo> --search "<#issue>"` —
   existiert schon ein PR/Branch zum Issue → nur fortführen, NIE neu anlegen.
2. **Branch:** `fix/<issue>-<slug>` bzw. `feat/<issue>-<slug>` aus aktuellem `main`.
3. **ScopeLock:** nur Dateien anfassen, die das Issue benennt/impliziert. Bei
   Ausweitung auf fremde Bereiche → STOP, Issue als STOP umklassifizieren.

## Phase 3: Pro DO-NOW-Issue

1. Minimal umsetzen (kein Refactor drumherum), Konventionen aus `project-facts.md`.
2. Tests für neue Funktion mitliefern; vorhandene Tests/Lint laufen lassen.
3. **Genau ein PR pro Issue**, Body endet mit `Closes #<n>`. Kein Merge, kein
   Force-Push.
4. Erste fehlschlagende Aktion (Test/Lint/Build rot, das du nicht trivial fixt)
   → STOP für dieses Issue, als Kommentar am Issue vermerken, nächstes Issue.

## Phase 4: Report (immer, am Ende)

```
/issues-offen <owner>/<repo> — <datum>
DONE:    #<n> <titel> → PR #<p>   (xN)
STOP:    #<n> <titel> — <grund: ADR/Infra/P1/Scope>   (xM)
SKIP:    #<n> <titel> — <grund>   (xK)
Cap erreicht: <ja/nein>  | Nächster Lauf nimmt den Rest.
```

## Anti-Patterns

- ❌ Mehr als 1 PR pro Issue, oder PR ohne `Closes #n`.
- ❌ Ein STOP-Issue trotzdem anfassen (ADR/Migration/Infra/Security/P1).
- ❌ ScopeLock verletzen (fremde Dateien "gleich mit" ändern).
- ❌ Mergen, Force-Push, Branch löschen, oder rote CI ignorieren.
- ❌ Owner/Org/Pfade hardcoden statt aus dem Repo lesen.
- ❌ Endlos-Loop in einer Session — Lauf endet nach Cap; Wiederholung via `/schedule`.

## Changelog

- 2026-05-28: Initial. Geschwister von `/issues-abarbeiten` ohne Handoff-Pflicht;
  Quelle = `gh issue list`. Gate-Signale an risk-hub-Labels orientiert
  (`ai-assignable`, `complexity:simple`). Schedule-tauglich (frische Läufe).
