---
description: Offene GitHub-Issues EINES Repos ODER org-/cross-repo triagieren und gate-freie selbst abarbeiten (1 PR/Issue, Stopp bei Judgment/Infra)
mode: write
---

# /issues-offen — Open-Issue Worker (single repo ODER org-weit, gated)

> **Zweck:** Live die offenen Issues holen — eines Repos *oder* einer ganzen Org
> (cross-repo) — triagieren und die *gate-freien* selbst erledigen: ein PR pro
> Issue, harter Stopp bei Judgment/Infra. Frischer, idempotenter Lauf →
> schedule-tauglich (`/schedule /issues-offen <repo|org:…>`), KEINE Endlos-Session.
>
> **Wann:** "Erledige, was in `<repo>` offen ist", ohne vorab geplanten Handoff.
> **Wann NICHT:** Es gibt einen dokumentierten Handoff/NÄCHSTE-AKTIONEN →
> `/issues-abarbeiten`. Multi-Repo `auto`-Queue über Nacht → `/process-agent-queue`.
> **Abgrenzung:** `/issues-abarbeiten` setzt einen *geplanten* Stand fort (Quelle =
> Memory-Handoff). `/issues-offen` startet *frisch aus `gh issue list`* (Quelle =
> GitHub) und triagiert selbst.

## Verwendung

```
/issues-offen <repo>          # Single-Repo, z.B. /issues-offen risk-hub
/issues-offen                 # ohne Arg: aktuelles Repo aus cwd
/issues-offen org:<org>       # Cross-Repo: alle (nicht-archivierten) Repos der Org
/issues-offen org:<org> repo:<r1>,<r2>   # Cross-Repo, aber nur diese Repos
```

`$ARGUMENTS`:
- **kein `org:`-Präfix** → Single-Repo-Modus (Repo-Kurzname oder cwd). Verhalten unverändert.
- **`org:<org>`** → Cross-Repo-Modus (Step 0b). `<org>` ist die GitHub-Org.

## Step 0: Repo-Kontext (NICHT hardcoden)

1. Repo bestimmen: `$ARGUMENTS` → `<repo>`; sonst Basename von `git rev-parse --show-toplevel`.
2. Owner/Org NICHT raten — aus dem Repo lesen:
   `gh repo view --json nameWithOwner -q .nameWithOwner` im Zielrepo
   (`~/github/<repo>`), bzw. `project-facts.md`. Niemals `achimdehnert` o.ä. hardcoden.
3. pgvector-Tunnel optional; dieser Workflow braucht ihn nicht.

## Step 0b: Repo-Discovery (NUR Cross-Repo-Modus `org:<org>`)

> Ziel: die Repo-Liste **aus stabiler Quelle** holen (nicht hardcoden), Souveränität
> wahren, dann Phase 1 pro Repo laufen lassen und Treffer **global** sammeln.

1. **Repos entdecken (live, authoritativ):**
   `gh repo list <org> --no-archived --source --json name,isArchived,isPrivate --limit 200`
   → deterministisch alphabetisch ordnen (damit aufeinanderfolgende `/schedule`-Läufe
   planbar weiterkommen). Optional gegen `platform/infra/repos.yaml` gegenprüfen,
   falls vorhanden. **Keine** Repo-Namen hartkodieren.
2. **🔒 Souveränitäts-Gate (HART):** Repos der Orgs **`ttz-lif`** und **`meiki-lra`**
   (Public-Sector / Citizen-/Mandantendaten) werden im Cross-Repo-Modus
   **übersprungen**, AUSSER `<org>` benennt sie ausdrücklich (`org:ttz-lif`). Auch
   dann gilt das per-Issue-STOP-Gate (DSGVO/Security) unverändert. Im Report als
   `SOVEREIGN-SKIP` ausweisen. (Begründung: `~/.claude/CLAUDE.md` Daten-Souveränität.)
3. **`repo:<…>`-Filter** (optional): wenn angegeben, nur diese Repos aus der Liste.
4. **Repo-Cap:** max **8 Repos/Lauf** scannen (Rest nächster Lauf). Bei mehr:
   alphabetisch die ersten 8 noch nicht in diesem Lauf behandelten.
5. **Lokaler Klon für DO-NOW:** Triage (Phase 1) braucht nur `gh` (kein Klon). Für
   die Umsetzung (Phase 3) muss das Repo unter `~/github/<name>` liegen — fehlt es,
   `gh repo clone <org>/<name> ~/github/<name>` (flach genügt), sonst Issue → STOP
   mit Grund `kein lokaler Klon`.

## Phase 1: Holen + Triage (read-only)

> Single-Repo: einmal für `<owner>/<repo>`. Cross-Repo: **pro entdecktem Repo**
> (Step 0b) ausführen und Treffer in eine **globale** DO-NOW-Liste sammeln
> (jedes Issue mit seinem `<owner>/<repo>` markiert).

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
3. DO-NOW nach Priorität ordnen (P2 > P3 > unlabelled). **Caps:**
   - Single-Repo: **max 5 Issues/Lauf**.
   - Cross-Repo: **global max 5 Issues/Lauf** UND **max 2 Issues/Repo** (Coverage
     über Repos streuen statt ein Repo leerräumen). Rest → nächster Lauf.
4. Plan als Tasks materialisieren (`TaskCreate`), ein Task pro DO-NOW-Issue
   (Cross-Repo: Task-Titel mit `<repo>#<n>` präfixen).

## Phase 2: Guardrails (vor JEDER Aktion)

0. **Cross-Repo: ins richtige Repo wechseln.** Vor jeder Git-Aktion ins Ziel-Repo
   des Issues (`~/github/<repo>`) wechseln und **`git branch --show-current`
   bestätigen** (kein Edit/Commit auf einem fremden/falschen Branch — House-Rule).
   Jedes Issue wird vollständig in seinem eigenen Repo abgeschlossen, bevor das
   nächste beginnt (keine vermischten Working-Trees).
1. **Kein Duplikat:** `gh pr list --repo <owner>/<repo> --search "<#issue>"` —
   existiert schon ein PR/Branch zum Issue → nur fortführen, NIE neu anlegen.
2. **Branch:** `fix/<issue>-<slug>` bzw. `feat/<issue>-<slug>` aus dem `main` des
   **jeweiligen** Repos.
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

Single-Repo:
```
/issues-offen <owner>/<repo> — <datum>
DONE:    #<n> <titel> → PR #<p>   (xN)
STOP:    #<n> <titel> — <grund: ADR/Infra/P1/Scope>   (xM)
SKIP:    #<n> <titel> — <grund>   (xK)
Cap erreicht: <ja/nein>  | Nächster Lauf nimmt den Rest.
```

Cross-Repo (`org:<org>`): pro Repo gruppiert + Summenzeile:
```
/issues-offen org:<org> — <datum>  (Repos gescannt: R/總, Issues bearbeitet: X)
<repo-a>:  DONE #12 → PR #34 · STOP #13 (Infra)
<repo-b>:  DONE #4  → PR #5
SOVEREIGN-SKIP: ttz-lif/* , meiki-lra/*   (nicht ohne explizites org:-Targeting)
Repo-Cap (8) erreicht: <ja/nein> · Issue-Cap (5) erreicht: <ja/nein>
Noch offen (nächster Lauf): <repos/issues, die wegen Cap übrig blieben>
```

## Anti-Patterns

- ❌ Mehr als 1 PR pro Issue, oder PR ohne `Closes #n`.
- ❌ Ein STOP-Issue trotzdem anfassen (ADR/Migration/Infra/Security/P1).
- ❌ ScopeLock verletzen (fremde Dateien "gleich mit" ändern).
- ❌ Mergen, Force-Push, Branch löschen, oder rote CI ignorieren.
- ❌ Owner/Org/Pfade hardcoden statt aus dem Repo lesen (auch die Repo-Liste:
  immer `gh repo list`, nie eine fixe Liste im Skill).
- ❌ Endlos-Loop in einer Session — Lauf endet nach Cap; Wiederholung via `/schedule`.
- ❌ Cross-Repo: `ttz-lif`/`meiki-lra` ohne explizites `org:`-Targeting anfassen
  (Souveränitäts-Gate), oder archivierte/fremd-owned Repos mit-iterieren.
- ❌ Cross-Repo: Issue in Repo A committen, während der Working-Tree auf Repo B
  steht — pro Issue ins eigene Repo wechseln + Branch verifizieren.

## Changelog

- 2026-05-28: Initial. Geschwister von `/issues-abarbeiten` ohne Handoff-Pflicht;
  Quelle = `gh issue list`. Gate-Signale an risk-hub-Labels orientiert
  (`ai-assignable`, `complexity:simple`). Schedule-tauglich (frische Läufe).
- 2026-06-01: Cross-Repo-Modus `org:<org>` (Step 0b): Repo-Discovery via
  `gh repo list` (nie hardcoden), **Souveränitäts-Gate** (ttz-lif/meiki-lra nur
  bei explizitem Targeting), Repo-Cap (8) + globaler Issue-Cap (5) + max 2/Repo,
  pro-Repo-Branch-Verifikation, aggregierter Report. Single-Repo-Verhalten unverändert.
