---
name: issues-offen
description: Offene GitHub-Issues EINES Repos ODER org-/cross-repo triagieren und gate-freie selbst abarbeiten (1 PR/Issue, Stopp bei Judgment/Infra)
metadata:
  mode: write
  migrated_from: .windsurf/workflows/issues-offen.md
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

**Argument dieses Aufrufs** (das, was nach dem Skill-Namen übergeben wurde — leer, wenn nichts übergeben):
- **kein `org:`-Präfix** → Single-Repo-Modus (Repo-Kurzname oder cwd). Verhalten unverändert.
- **`org:<org>`** → Cross-Repo-Modus (Step 0b). `<org>` ist die GitHub-Org.

## Step 0: Repo-Kontext (NICHT hardcoden)

1. Repo bestimmen: das übergebene Argument → `<repo>`; sonst Basename von `git rev-parse --show-toplevel`.
2. Owner/Org + Konventionen NICHT raten — **stabile Quelle zuerst, Live nur als Fallback:**
   - **Primär (kein API-Call):** `~/github/<repo>/project-facts.md` lesen. Owner/Repo
     steckt in der `GitHub:`-Zeile (`https://github.com/<owner>/<repo>`); Stack/Settings/
     Testpfad/Branch für Phase 3 kommen aus derselben Datei — *einmal* gelesen, nicht
     pro Lauf neu via API hergeleitet. Diese Daten sind stabil (auto-generiert von
     `platform/.github/scripts/push_project_facts.py`).
   - **Fallback (nur wenn `project-facts.md` fehlt):**
     `gh repo view --json nameWithOwner -q .nameWithOwner` im Zielrepo (`~/github/<repo>`).
   - Niemals `achimdehnert` o.ä. hardcoden.
   - ⚠️ NUR der **stabile** Kontext (Owner/Pfad/Konventionen) ist cachebar. Die
     **volatile** Issue-Liste (Phase 1) bleibt IMMER live aus `gh issue list` — ein
     Snapshot davon würde veralten (geschlossene Issues, neue P0, Re-Labels).
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
   mit Grund `kein lokaler Klon`. Nach dem Klon gilt der Repo-Kontext aus Step 0.2
   (stabile Quelle `project-facts.md` zuerst) auch hier — pro Repo einmal.

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

> **Strukturierte Tabelle** für Sofort-Überblick — eine Zeile pro Issue, keine
> rohen Befehls-/Log-Dumps. `Status` ∈ {DONE, STOP, SKIP}, `Risiko` als Ampel
> (🟢/🟡/🔴), `Inhalt` = Issue-Titel knapp, `Next` = Folgeaktion/Grund kurz.
> Details (falls nötig) als kurze Prosa **unter** der Tabelle, nicht in der Zelle.

**Single-Repo** — Kopfzeile `/issues-offen <owner>/<repo> — <datum> · Cap erreicht: <ja/nein>`:

| Issue | Status | PR | Risiko | Inhalt | Next |
|---|---|---|---|---|---|
| #\<n\> | DONE | #\<p\> | 🟢 | \<titel\> | — |
| #\<n\> | STOP | — | 🔴 | \<titel\> | \<grund: ADR/Infra/P1/Scope\> |
| #\<n\> | SKIP | — | — | \<titel\> | \<grund\> |

**Cross-Repo** (`org:<org>`) — Kopfzeile mit Summen (`Repos gescannt: R · Issues bearbeitet: X · Repo-Cap(8): <j/n> · Issue-Cap(5): <j/n>`); zusätzliche `Repo`-Spalte:

| Repo | Issue | Status | PR | Risiko | Inhalt | Next |
|---|---|---|---|---|---|---|
| \<repo-a\> | #12 | DONE | #34 | 🟢 | \<titel\> | — |
| \<repo-a\> | #13 | STOP | — | 🔴 | \<titel\> | Infra |
| ttz-lif/* | — | SOVEREIGN-SKIP | — | — | Souveränitäts-Gate | nur mit explizitem `org:`-Targeting |

Unter der Tabelle eine Zeile: `Noch offen (nächster Lauf): <was wegen Cap übrig blieb>`.

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
- 2026-06-02: Step 0.2 — stabilen Repo-Kontext (Owner/Pfad/Konventionen) **primär aus
  `project-facts.md`** lesen statt pro Lauf via `gh repo view` neu herleiten; API-Call
  nur noch Fallback. Spart den Kontext-Neuaufbau bei Multi-Repo-/Multi-Lauf-Nutzung.
  Volatile Issue-Liste (Phase 1) bleibt explizit live — kein Snapshot-Cache (Staleness).
- 2026-06-02: Phase-4-Report auf **strukturierte Tabelle** umgestellt (Issue/Status/PR/
  Risiko/Inhalt/Next; Cross-Repo mit Repo-Spalte) statt Plain-Text-Liste — Sofort-Überblick,
  keine rohen Bash-/Log-Dumps. Reine Darstellungsänderung; Verhalten/Caps/Gates unverändert.
