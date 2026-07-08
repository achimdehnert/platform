---
id: ADR-211
title: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)
status: accepted
date: 2026-05-19
deciders: [achim]
informed: [all-repos]
domains: [ux, requirements, process, security, drift-prevention]
supersedes: []
amends: []
depends_on: []
tags: [klickdummy, mockup, requirements-spec, parity-test, prod-guard, convention]
scope:
  include_paths:
    - "policies/klickdummy.md"
    - "scripts/checks/klickdummy_*.sh"
    - "**/klickdummy/**"
---

# ADR-211: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)

- **Status:** accepted *(2026-05-19, Decider-Ratifizierung des Entscheids I1–I4 + Enforcement-Pfad; Adoption-Scoreboard SF1–SF6 läuft separat und gatet den Status NICHT — siehe Acceptance-Trigger)*
- **Datum:** 2026-05-19
- **Entscheider:** Achim Dehnert
- **Verwandt:** risk-hub:ADR-046, writing-hub:ADR-180, meiki-hub:ADR-020, meiki-hub:ADR-026 (Rev 12)
- **Adversarial reviews:** sechs Cascade-Pässe (Rev 2/3/4/9 + Rev 10 F5-Rollback + Rev 11 #228/#229) + Rev-12-Empiriebasis (meiki-hub PR #23, 7 Iterationen 2026-05-20) + Rev-13-Decider-Pivot (ADR-214-Draft als advocatus diabolus zurückgezogen, 4 🔴-Findings) + Rev-14-Browser (Stakeholder-Feedback 2026-05-21), siehe Revisionshistorie

## Zusammenfassung

Mehrere Repos bauen „Klickdummies". Der naheliegende Rahmen — „jeder macht
sein Ding, wir teilen Vokabular" — wäre **keine Entscheidung** (per
`adr-threshold.md` reichte eine Konvention). Dieses ADR trifft drei harte,
erzwingbare Entscheidungen, weil jede einen realen Schaden verhindert:

1. **Spec-zentriert statt Renderer-zentriert.** Dauerhaftes Artefakt ist die
   **maschinenlesbare Anforderungs-Spec**, nicht ihre Darstellung. Ein
   Klickdummy *rendert* sie; ein Parity-Test ist das Konformitäts-Gate.
2. **Vier scharf abgegrenzte Patterns, drei brauchen externen Prod-Guard
   (Rev 11).** Klickdummies kommen in vier Patterns (`mock` / `stub-demo` /
   `story` / `spec-demo`) entlang *Datenquelle × Code-Pfad-Identität*. Jedes
   nicht-`mock`-Pattern erfordert eine **distinkte** externe Prod-Probe.
3. **Parity-grün ist die Off-Ramp, mit TTL — *und* Phase-A bekommt einen
   harten Termin (Rev 11).** Parity-grün pro Screen ⇒ statische Quelle
   mechanisch entfernt; **Phase-A ohne Zielsystem** wird zusätzlich durch
   `sunset_after`-Pflicht-Frontmatter terminiert — beendet das „Static-
   Leichen"-Muster strukturell, unabhängig davon ob Parity je grün wird.

Die drei *Schaden-Entscheidungen* entsprechen den Invarianten I1–I3; **I4
(Namensraum)** ergänzt sie als Drift-Schutz für Cross-Repo-Refs.
Implementierungs-Stack bleibt repo-lokal; alle vier Invarianten sind
ansatz-offen.

## Kontext

Ist-Lage (2026-05-19): meiki-hub (Manifest-Single-File-Mock, CI-Invariante),
writing-hub (`?demo=`-Render echter Templates + Parity, ADR-180), risk-hub
(Spec-Driven UI Convention, repo-lokal, ADR-046 Rev 2). Drei Formen, kein
gemeinsamer „fertig"-Begriff. Die Mehrdeutigkeit „klickdummy"/„ADR-180" über
Repo-Grenzen verursachte in dieser Session eine konkrete Fehlzuordnung —
Drift-Episode `2026-05-19-klickdummy-adr180-collision`, **belegt** als
Drift-Memory (meiki-hub-Auto-Memory, `drift: true`) **und** Followup-Issue
`adr-211-followup/SF5`, nicht nur hier erzählt (R5).

> **Selbsttest gegen `adr-threshold.md`:** kehrt den Status quo repo-autonomer
> Klickdummy-Proliferation um, adressiert eine **Sicherheitsfläche**
> (Demo-Render in Prod), cross-cutting über ≥ 3 Repos → Pflicht-Kriterien
> erfüllt, echte Entscheidung.

## Entscheidung — vier Invarianten (ansatz-offen)

| # | Invariante | Erzwingung |
|---|---|---|
| **I1 Spec-first** | Maschinenlesbares, versioniertes Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter); Markdown-Bullets zählen nicht. Klickdummy rendert es, ist nicht die Quelle. **Bidirektionale Coverage:** jede Impl-Route hat einen Spec-Eintrag *und* jeder Spec-Eintrag eine Route/Screen — kein einseitiges „Datei existiert & rendert". *Rev 12:* die Spec ist auch der **Eingang für Anforderungs-Updates** — optional über Co-Creation-Loop (§Co-Creation, opt-in) und **Ausgang** für abgeleitete Requirements (§Requirements-Bridge, opt-in). *Rev 17 — Daten-Treue der Anzeige (Klarstellung, kein neues Gate):* ausgegebene Zahlen/Aggregate (Counts, Summen, KPIs) sind aus den im Klickdummy vorhandenen Daten **berechnet**, nicht als Literal geschrieben — auch in `class: mock` (Daten dürfen synthetisch sein, die **Berechnung** muss echt sein). Cross-Screen-Aggregate (Eltern-Kachel = Summe der Kind-Liste) aus **einer** Quelle rechnen. *Rev 18 — Ausführbare Parity-Ableitung (Klarstellung, kein neues Gate):* `parity_acceptance`-Einträge dürfen einen optionalen ausführbaren `assert`-Block tragen; ein forward-only deterministischer Generator (`klickdummy-gen-e2e`, §Executable-Parity-Bridge) erzeugt daraus eine Suite, die per `SPEC_RENDERER_BASE_URL` Renderer #1 (Klickdummy) **und** #2 (echte App) gegen dieselbe Assertion prüft (parity-grün gegen #2 = I3-Off-Ramp-Gate). Die Tests sind **abgeleitetes, regenerierbares** Artefakt — die Spec bleibt normativer Acceptance-Record, **weder Produktionscode noch Test-Harness-Quelle**; Prosa-`check` bleibt normativ und gewinnt bei Konflikt mit `assert`. *Rev 19 — Konzept-Doc als idea-Vorstufe (Klarstellung, kein neues Gate):* die Lifecycle-Stufe `pipeline_status: idea` darf ein **Konzept-Doc** (`KONZ-<repo>-NNN`) tragen — Rationale-/Entscheidungs-Artefakt, **kein System-of-Record und keine Anforderungsquelle**. Ab Spec-Existenz ist allein die Spec normativ; das Konzept-Doc trägt danach nur Rationale (read-only, analog I3-Archivregel Rev 18). Für T1/T2 persistiert es als **Annahmen-Ledger ohne Anforderungs-Freitext** — die zweite-Wahrheit-Fläche ist strukturell verkleinert, nicht nur verboten. | `make -C <repo> klickdummy-i1` (Exit-Code), CI-verifiziert — prüft Spec↔Route-Coverage, nicht nur Spec==Render · *Rev 17:* Daten-Treue = **Review-Gate** (kein sauberer Exit-Code; optional heuristischer Lint, der Zahl-Literale in Anzeige-Elementen ohne Datenbindung flaggt) · *Rev 18:* Determinismus + Drift-Gate `klickdummy-parity-drift` (Exit-Code, Reuse S10-Muster); Prosa↔`assert`-Konflikt = Review-Gate; Coverage/Skip-Debt im Manifest |
| **I2 Prod-Sicherheit (4-Pattern, Rev 11)** | Genau **ein** Pattern je Klickdummy, **explizit deklariert**: `mock` / `stub-demo` / `story` / `spec-demo` (Achsen: *Datenquelle × Code-Pfad-Identität*; vollständige Definition siehe Glossar). „Kein Pattern deklariert" = I2-Verstoß (kein vacuous pass). Die Vereinfachung *Mock-Prototyp/Demo-Render* (Rev ≤10) wird hier verfeinert, weil die drei Nicht-`mock`-Patterns *distinkte* Prod-Probes erfordern. | **Zwei Schichten:** (a) repo-definierter `make -C <repo> klickdummy-i2` (Selbstaussage des Patterns); (b) **plattform-externer Prod-Probe** `klickdummy_prod_guard.sh` mit pattern-spezifischem Verhalten: `mock` ⇒ N/A (Pfad nicht in Prod-Deploy); `stub-demo` ⇒ deklarierte Demo-Route 404; `story` ⇒ Catalog-Route (z. B. `/storybook/`) 404; `spec-demo` ⇒ `?demo=<state>` 404/disabled. `klickdummy_prod_guard.sh` (F11) ist derzeit **unimplementiert/dormant** (ADR-211 Rev 20, #255 geparkt); bis zu seiner Implementierung ist ausschließlich die repo-lokale Pattern-Deklaration (a) aktiv und es existiert **kein bindendes Cross-Repo-Prod-Probe-Signal**. **Risiko-Hinweis (Übergang, REC-4):** bis F11 gebaut ist, fehlt die *externe* Falsifikation (Demo-/Catalog-/`?demo=`-Route ⇒ Prod-404) für die Nicht-`mock`-Patterns — I2 ist solange **schwächer als ursprünglich dokumentiert**, weil auf Selbstdeklaration statt externem Prod-Probing gestützt |
| **I3 Lebenszyklus + TTL + Sunset (Rev 11)** | **A ohne Zielsystem:** Pflicht-Frontmatter `sunset_after: <ISO-Datum>` in der Repo-Klickdummy-ADR (Default ADR-Datum + 12 Monate); nach Fristablauf ohne PR-Extension ⇒ ADR auto-`deprecated`, Pfad `klickdummy/archive/` (siehe §Frontmatter-Konvention). **B Transition:** ab erstem Screen mit Impl-Route greift I3 je Screen. **C mit Zielsystem:** Doppelquelle endet bei **`min(prod-Release, Parity-grün + N Tagen)`** (N Default **30 d**, repo-tunbar) — schließt das „ewig auf Staging"-Leck (F4). Staging ist erlaubter Doppelquell-Raum *innerhalb* der TTL. *Rev 18 — Off-Ramp-Beweis statt -Behauptung:* Parity-grün erfüllt den Off-Ramp eines Screens nur mit (1) Renderer-#1-Entfernung (`off_ramp_status: removed`, Pfad `klickdummy/archive/`) **und** (2) negativem Reachability-Beleg (alte statische Route ⇒ Prod-404). **Max. eine lebende UI-Impl pro Spec-Screen**; Archiv = read-only (Reaktivierung re-triggert I3). **F4 nur für inventarisierte Routen geschlossen** — Alias-/Preview-Restrisiko offen (F20). *Rev 19 — Konzept-Doc TTL (idea-Stufe):* das `KONZ-`-Doc trägt `review_by` (Default created + 90 d; Frist ohne Extension ⇒ `sunset`) und `kill_criteria`; sobald eine Spec existiert, setzt `superseded_by_spec` das Doc read-only — ein CI-Gate blockt inhaltliche Edits ohne `reactivation_reason` + `I1-review`-Label (hebt F21 von „dokumentiert" auf „kontrolliert"). | `make -C <repo> klickdummy-i3` (Phase B/C); `platform/scripts/checks/adr_sunset.sh` (Phase A, nightly — öffnet Issue bei passierter Frist) · *Rev 18:* Reachability-Beleg über F11-Prod-Guard (Doppel-Geltung I2+I3); bis Bau manueller, im PR dokumentierter Ersatzbeleg |
| **I4 Namensraum** | Klickdummy-ADRs tragen reserviertes Titel-Präfix; Cross-Repo-Refs **nur** `repo:ADR-NNN` (inkl. `conforms_to: platform:ADR-211`). Drift-Schutz (vgl. Drift-Memory `klickdummy-adr180-collision`). *Rev 19:* neuer Namensraum `KONZ-<repo>-NNN` (pro Repo unter `docs/konzepte/`, parallel zu `ADR-NNN`); Cross-Repo-Ref `repo:KONZ-NNN`; `owner` Pflicht (kein `TBD`). | `platform/scripts/checks/adr_cross_repo_refs.sh` (plattformseitig, kein repo-Make-Target — generischer ADR-Lint) |

**Auswahlhilfe Rev 11 (illustrativ; Mapping bekannter Implementierungen auf
die 4 Patterns aus I2):**

| Pattern | Beispiel | Datenquelle | Code-Pfad | I2-Externprobe |
|---|---|---|---|---|
| `mock` | meiki-hub:ADR-020 | leere/feste Stubs | **separater** Wegwerf-Pfad | N/A |
| `stub-demo` | (potenziell risk-hub:ADR-046) | synth. im Code | **real**, fester Demo-Pfad | Demo-Route 404 |
| `story` | (Storybook-Stil — kein Beispiel-Repo) | synth. pro Story | **real**, isolierte Catalog-Route | Catalog-Route 404 |
| `spec-demo` | writing-hub:ADR-180 | synth. via Flag | **real**, env-gegated | `?demo=` 404 |

KI-generiert/Figma-as-Spec zulässig, sofern I1–I4 erfüllt. Repos mit
bestehendem `class: Mock-Prototyp` (Rev ≤10) ⇒ `mock`. Repos mit
`Demo-Render` (Rev ≤10) müssen in der nächsten Conformance-Iteration zu
einem der drei Nicht-`mock`-Patterns präzisiert werden. **Migrations-
Cookbook siehe §Migration Rev-≤10 → Rev-11 (Rev 12, schließt F12).**

### Was repo-lokal bleibt
Tech-Stack, Schema, UI-Bausteine, Teststack. risk-hub:ADR-046 behält seine
Repo-Lokalität; dieses ADR ersetzt keine Implementierungs-ADR.

## Frontmatter-Konvention für repo-lokale Klickdummy-ADRs (Rev 11, schließt #228)

Repo-lokale ADRs mit `tags: [klickdummy]` MÜSSEN folgende Frontmatter
führen:

```yaml
class: mock | stub-demo | story | spec-demo   # Rev-11 I2 (Pflicht)
sunset_after: 2026-12-31                       # ISO-Datum (Pflicht; Default ADR-Datum + 12 Monate)
extension_review_required: true                # Optional (Default true für mock, false sonst)
```

**Geltungsbereich:** ausschließlich **repo-lokale** Klickdummy-ADRs.
**ADR-211 selbst** (Platform-Policy-ADR mit `tags: [klickdummy, ...]`) ist
**explizit ausgenommen** — eine Policy-ADR hat keinen Sunset, ihre
Geltung wird durch `supersedes`/`amends` geregelt.

**Auto-Deprecation:** Nach Ablauf von `sunset_after` ohne PR-Extension:
- ADR-Status wechselt zu `deprecated` (Validator-erzwungen)
- Klickdummy-Pfad wandert nach `klickdummy/archive/`
- Owner-Review nötig für Extension (neuer PR mit neuem `sunset_after`)

**Enforcement:** `platform/scripts/checks/adr_sunset.sh` (nightly CI;
öffnet GitHub-Issue bei passierter Frist). Adoption-Scoreboard-Item S7.

### Hinweis zu I4-Scope (Rev 10)
I4 ist hier *klickdummy-skopiert* (Refs in den Klickdummy-ADRs und
`conforms_to`-Felder). Eine plattformweite Verallgemeinerung des
Cross-Repo-Ref-Formats wäre ein **eigener** ADR — sie gehört **nicht** in
ADR-207 (Doku-Strategie/Ingest), wie Rev 9/F5 fälschlich annahm.

## Enforcement-Pfad

Mechanik exakt wie `policies/README.md` (Rev 5 — keine Erfindung eines
Parallelpfads):

1. **Rationale:** dieses ADR.
2. **SSoT (versioniert):** `platform/policies/klickdummy.md` — im Plattform-Repo,
   reviewbar; Änderung **nur per platform-PR + Changelog-Bump**.
3. **Injektion (operativ):** `~/.claude/policies/klickdummy.md` ist ein
   **Symlink** in einen gepinnten platform-Worktree (`~/github/platform-pinned/policies/`),
   denselben Mechanismus wie `adr-threshold.md`/`llm-routing.md`;
   `inject_policies.py`/`claude-policy` lesen den Symlink unverändert. **Kein
   Kopier-Sync.** Der gepinnte Worktree zieht beim nächsten Refresh nach; das
   Scoreboard-Item S6 erkennt einen *stale gepinnten Worktree*.
4. **Adoption:** `onboard-repo`-Skill prüft I1–I4 + ADR-Header + `make klickdummy-{i1,i2,i3}` (I4 plattformseitig via Lint, siehe S5).
5. **Verifikation:** `platform/scripts/checks/klickdummy_registry.sh` über `registry/repos.yaml`.

## Acceptance-Trigger (F1/F2 — Entscheidung ≠ Rollout)

**Kategorienkorrektur (Rev 9):** Frühere Revisionen verwechselten
„Entscheidung getroffen" mit „flottenweit ausgerollt & grün". Das erzeugte
einen **Deadlock** (das Acceptance-Gate verlangte die gemergte Policy, deren
Merge an der Acceptance hing) und einen **mit der Flotte oszillierenden
Status**. Korrektur:

- **`status: accepted`** ⇔ der *Entscheid* (I1–I4 + Enforcement-Pfad) ist von
  den Decidern ratifiziert (Review dieses ADR). Das Mergen von
  `policies/klickdummy.md` ist **Teil des Acceptance-Akts**, keine
  Vorbedingung. Kein zirkulärer Fixpunkt.
- **C1–S6** (vormals „Confirmation C1–C6") sind ein **separates, lebendes
  Adoption-Scoreboard** in `adr-211-followup` (SF1–SF6). Es trackt den
  Rollout-Fortschritt und **gatet `status` nicht** — eine akzeptierte
  Architekturentscheidung ist stabil, nicht eine Funktion fortlaufender
  Flotten-Drift.

## Adoption-Scoreboard (lebend, nicht status-gatend)

> Baseline 2026-05-19: 0/6. Fortschritt in `adr-211-followup` SF1–SF6.
> Reihenfolge frei; keiner blockt die Acceptance des Entscheids.

```bash
# S1 Registry-Konformität (SF1)
platform/scripts/checks/klickdummy_registry.sh
#   GELTUNGSBEREICH: nur in registry/repos.yaml gelistete (achimdehnert-)Repos.
#   Andere Orgs (z. B. meiki-lra:meiki-hub) NICHT abgedeckt — Repo-CI verantwortet.
#   Konformität = Repo-ADR-Frontmatter `conforms_to: platform:ADR-211`.

# S2 I1 Spec↔Route-Coverage je Repo (SF2)
make -C <repo> klickdummy-i1

# S3 I2 Prod-Guard — ZWEISCHICHTIG (SF3)
make -C <repo> klickdummy-i2                              # (a) Repo-Selbstaussage
platform/scripts/checks/klickdummy_prod_guard.sh <repo>  # (b) externer Prod-Probe,
#   registry-URL + '?demo=' ⇒ erwartet 404/disabled. (b) ist bindend, repo-unabhängig.

# S4 I3 Off-Ramp mit TTL, Grenze = min(prod-Release, Parity-grün + N d) (SF4)
make -C <repo> klickdummy-i3

# S5 I4 Cross-Repo-Ref-Format (Rev 10: zurück in ADR-211; F5 zurückgenommen)
platform/scripts/checks/adr_cross_repo_refs.sh
#   Validiert qualifizierte Cross-Repo-Refs (^[a-z][a-z0-9-]+:ADR-[0-9]{3}$).
#   Klickdummy-skopiert; plattformweite Verallgemeinerung wäre eigener ADR.

# S6 Policy-SSoT existiert UND gepinnter Worktree nicht stale (SF6)
platform/scripts/checks/klickdummy_policy_sync.sh
#   FAIL wenn SSoT fehlt ODER Injektions-Ziel fehlt/weicht ab (staler Pinned).
#   SKIP (exit 0) ohne ~/.claude/policies (off-machine CI); --strict ⇒ FAIL.
#   Doppel-Stale-Check (vs origin/main) seit PR #254.

# S7 sunset_after-Enforcement für Phase-A Klickdummy-ADRs (Rev 11, #228)
platform/scripts/checks/adr_sunset.sh
#   Nightly. Scant alle ADRs mit tags: [klickdummy] (außer ADR-211 selbst).
#   FAIL wenn sunset_after fehlt ODER Frist passiert ohne PR-Extension.

# S8 4-Pattern-Konformität (Rev 11, #229)
#   Repo-lokale Klickdummy-ADRs MÜSSEN class ∈ {mock,stub-demo,story,spec-demo}
#   führen (geprüft via klickdummy_registry.sh + Frontmatter-Lint).

# S9  Co-Creation-Loop-Adoption (Rev 12, optional)
#     Pro Repo: ja/nein/n-a. Mindestens 1 Iterations-Eintrag in feedback-log.md
#     wenn aktiviert. Misst Velocity-Vorteil; gatet NICHT.

# S10 Requirements-Bridge-Adoption (Rev 12, optional)
#     Pro Repo: ja/nein. Wenn ja, muss `make klickdummy-requirements-drift`
#     in CI laufen (re-extract + git diff --exit-code).

# S11 Soft-Migrate → Strict-Mode-Trigger (Rev 12)
#     Plattform-Cross-Repo-Inventur (Skript siehe §Migration). Sobald 0 Repos
#     'mock-prototyp'/'demo-render' verwenden ODER Hard-Deadline 2026-08-20
#     erreicht: Strict-Mode in check_i2.py überall aktivieren (LEGACY={}).
#     S11-Erfüllung schließt F12.
#
# S12 KD-first-Gate-Adoption (Rev 16, optional, nicht status-gatend)
#     Pro Repo: ja/nein. Wenn ja: NEUE Features mit User-facing Surface
#     durchlaufen das KD-first-Gate (Spec + KD + Signoff VOR Impl, §KD-first-Gate).
#     Misst Velocity-Vorteil; gatet plattformweit NICHT.
#
# S13 Executable-Parity-Bridge-Adoption (Rev 18, optional, nicht status-gatend)
#     Pro Repo: ja/nein. Wenn ja: `klickdummy-parity-drift` läuft in CI
#     (re-generieren + git diff --exit-code, analog S10); Manifest als Artefakt;
#     org-weiter Mindestdatensatz (spec_id, executable/skipped, Skip-Owner/-Grund,
#     fragile-count, letztes-Grün, off_ramp_status). Misst Operationalisierung; gatet NICHT.
#     STATUS (2026-06-13, Rev 21): REAKTIVIERT — Wertthese erstmals empirisch eingelöst.
#     Die VIER REC-1-Reaktivierungsbedingungen sind ALLE belegt (verifiziert durch Ausführung
#     gegen die echte App, nicht durch Behauptung):
#       (1) echter Renderer #2 = risk-hub `/sds/review/` (live, login-gegatete Django-App);
#       (2) ≥1 fachlicher `assert`-Block = `sds-verwalten`-Spec (3 ausführbare Asserts);
#       (3) Selektor-/Testkontrakt = `data-testid` (sds-review-queue/-row/-verify-btn) in der
#           App `review_queue.html`;
#       (4) Auth-/Session-Modell = `storage_state` via `browser_context_args` (F22 GESCHLOSSEN).
#     BEWEIS: dieselbe generierte Suite läuft 3/3 grün gegen Renderer #2 UND wird rot, sobald ein
#     App-`data-testid` vom Spec-Kontrakt abweicht (Divergenz injiziert, ausgelieferter HTML
#     verifiziert) → diskriminiert App↔Spec-Drift, nicht nur Mockup-gegen-sich-selbst.
#     Dabei zwei „gebaut, nie ausgeführt"-Bugs im Generator gefunden+gefixt (auth-API + Strict-
#     Mode/.first; iilgmbh/iil-klickdummy #67) — bestätigt Rev-20-Lesson REC-5.
#     `review_by 2026-12-04` entfällt als Lösch-Trigger; S13 misst ab jetzt Operationalisierung
#     (nicht-gatend bleibt nicht-gatend). Verbliebene Folge-Arbeit (kein Blocker der These):
#     CI-fähige risk-hub-Suite braucht deterministischen Seed + Auth-Automation (F22 ist als
#     Generator-Mechanismus geschlossen; Adopter-seitige Einbettung = Operationalisierung).

# S14 Sitemap-Freshness-Adoption (Rev 24, optional, nicht status-gatend)
#     Pro Repo: ja/nein/n-a (n-a = kein klickdummy/sitemap/ geführt). Wenn ja:
#     `klickdummy-sitemap-drift` (oder repo-äquivalentes Target) läuft in CI
#     (re-generieren via klickdummy-gen-sitemap + git diff --exit-code, analog
#     S10/S13). Erst-Adopter: risk-hub (Auslöser dieses Amendments, PR folgt).
```

## §Co-Creation-Loop (optional, Rev 12)

**Was es ist.** Eine *opt-in*-Erweiterung des Klickdummy-Anwendungsmodells:
neben dem klassischen Stakeholder-Pfad „Workshop → Mensch übersetzt → Spec"
existiert ein **direkter Eingangskanal aus dem Klickdummy in die Spec**.
Stakeholder geben Feedback *im Klickdummy*; das Feedback ist strukturiert
(Screen, Persona, Kategorie, optional Action-Bezug + DOM-Snapshot +
Anhänge) und durchläuft denselben Spec → Render → Commit-Pfad wie jede
andere Anforderung.

**Was es NICHT ist.** Keine neue Invariante. Keine Aufweichung von I2 (das
Widget bleibt unter `class: mock` ein Mock-Pfad ohne Backend; bei
`spec-demo` o. ä. greift weiterhin der Prod-Guard). Kein Pflicht-Pattern —
Repos, die ohne Co-Creation auskommen, müssen nichts implementieren.

**Erlaubte Pfade entlang Vertrauens-Perimeter** (Rev 13 neu strukturiert
nach Decider-Pivot 2026-05-20: zentraler Endpoint zurückgezogen, da
0 produktive Iterationen in 7 meiki-Iter. + Coding-Agent existiert nicht):

| Pfad | Was | Status in Rev 13 |
|---|---|---|
| **A-light** | Widget → Submit-Mode `download` oder `clipboard` → Issue manuell anlegen | **Default.** Offline-fähig, kein GitHub-Token nötig, kein Service-Abhängigkeit. Empirisch validiert durch meiki-Iter. 1-7. |
| **A-User-Direct** | Widget → Submit-Mode `github` → `POST api.github.com/repos/.../issues` mit **User-PAT** (im `localStorage.klickdummy_github_token`) | **Erlaubt + Default für GitHub-User-Workflows.** Issue-Author = realer User; Rate-Limit/Audit/CSRF GitHub-native (5000 req/h pro Token); kein Service zu betreiben; kein PII-Filter-Risiko (User entscheidet selbst, was committet wird — analog zum normalen Issue-Anlegen). |
| **A-Agent** *(noch nicht aktiviert)* | Issue mit Label `klickdummy-feedback` → automatischer Coding-Agent → Diff-PR | **Voraussetzung:** GitHub-Action wie `anthropics/claude-code-action` o. ä. **im Ziel-Repo eingerichtet.** Aktuell in **keinem** Repo aktiv. „A-Agent aktiviert" = nachzuweisen per Workflow-Existenz, nicht per Behauptung. |
| **B · Direkt-LLM** | Widget → LLM direkt | **Verboten** in dieser Rev. Aktivierung erfordert neuen ADR (Audit-/Threat-Model, Cost-Cap). Wäre nicht „Browser → LLM mit Code-Rechten" (das war C in Rev 12), sondern „Browser → Backend → LLM" — also auch ein Service. Wenn Service-Bedarf empirisch belegt ist (S9 zeigt skaliertes Co-Creation), neu evaluieren. |
| **C · Browser-LLM** | Widget → LLM mit Code-Schreib-Rechten aus Browser | **Verboten.** Wie Rev 12. |

**Pivot-Begründung (Rev 13):** Rev 12 hatte „A · Bridge" als Pfad-A-Default
mit zentralem Endpoint `feedback.iil.pet` vorgesehen. Decider-Review
2026-05-20 (4 K-Findings 🔴) verwarf das:

- **K1**: 0 produktive Endpoint-Iterationen — Hypothese, nicht Empirie
- **K3**: Coding-Agent existiert nicht — Service ohne Konsument
- **K6/K12**: Service-Wartung amortisiert sich nicht
- **K10**: Datenschutz-Default falsch herum (4/6 Repos sind sensibel)

**GitHub-Direkt-API ist 2026-Standard** für solche Mini-Tools — Audit/
Rate-Limit/Auth-Modell sind native. Wenn Skalierung später Service
erfordert, kann „A-Bridge" als neuer Pfad in Rev 14 mit Empirie ergänzt
werden — bis dahin nicht gebaut.

**Aktivierungs-Definition** (eindeutig, prüfbar):

Ein Repo gilt als „Co-Creation-Loop aktiviert" **genau dann, wenn alle drei
Bedingungen erfüllt sind:**

1. Spec enthält Block `feedback_loop:` mit deklariertem Payload-Schema und
   mindestens einem aktivierten Submit-Mode.
2. Widget ist in der Klickdummy-Render-Quelle vorhanden UND opt-in
   (Default: aus; z. B. `?feedback=on` oder Build-Flag).
3. Provenance-Log `feedback-log.md` existiert neben der Spec.
4. **Pfad-Deklaration**: `feedback_loop.path: A-light | A-User-Direct | A-Agent`
   (Rev 13 — Pfade B/C bleiben verboten). Verhindert Vacuous-Pass „aktiviert
   ohne Pfad". `A-Agent` setzt nachgewiesene Coding-Agent-Workflow-Existenz
   im Repo voraus.
5. Repo-lokales Klickdummy-ADR referenziert die Aktivierung — bevorzugt
   `tags: [klickdummy, co-creation]` (analog Requirements-Bridge); Fallback
   Body-Section `## Co-Creation-Loop aktiv (Pfad <A|B>)`.

Bei Erfüllung ⇒ Scoreboard S9 = ja. Bei nur 1–4 erfüllt = „in Arbeit",
nicht aktiviert.

**Pflichten bei Aktivierung:**

1. **Spec-Block `feedback_loop:`** dokumentiert Capability, Payload-Schema,
   aktivierte Submit-Modi, Endpoint-Contract (per Aktivierungs-Bedingung 1).
2. **Provenance-Log** (`feedback-log.md` neben der Spec, per Bedingung 3) —
   jeder umgesetzte Vorschlag mit Quellverweis ins Archiv. Macht Auto-
   Iterationen nachvollziehbar.
3. **Issue-Template** mit Label `klickdummy-feedback` (Pfad A).
4. **Inbox-Konvention** falls Download-Submit verwendet wird: das Repo
   **deklariert** in seinem lokalen Klickdummy-ADR oder im Provenance-Log,
   wo die Inbox liegt UND wann sie geleert wird. Default: Session-Ende.
   Generisch, repo-spezifisch konkretisierbar (kein Hard-Coding auf
   meiki-Doku-Strategie).
5. **Klassen-Erhalt** — die Aktivierung darf die `class`-Deklaration nicht
   verändern. Konkret je Pattern:
   - **`mock`:** Klickdummy-Codebasis (incl. Widget) ist nicht in
     Prod-Deploy. Der Feedback-Endpoint ist ein **separater Dienst** (nicht
     Teil des Klickdummy-Code-Pfads); seine Existenz in Prod ist erlaubt,
     solange er keinen Code-Pfad zurück in den Klickdummy schafft.
     `class_evidence.no_backend: true` bleibt gültig (gemeint ist das
     Klickdummy-Backend, nicht der externe Endpoint).
   - **`stub-demo`:** Widget liegt **hinter** der Demo-Route; I2-Externprobe
     `Demo-Route 404` bleibt gültig (Widget ist nicht über andere Route
     erreichbar).
   - **`story`:** Widget liegt **innerhalb** der Catalog-Route (z. B.
     Storybook-Addon); I2-Externprobe `Catalog-Route 404` bleibt gültig.
   - **`spec-demo`:** Widget ist hinter `?feedback=on`-Sub-Flag, das
     **selbst hinter** dem `?demo=`-Guard liegt; I2-Externprobe
     `?demo= 404/disabled` impliziert `?feedback= 404/disabled`.
6. **Feedback-Scope-Trennung** (aus Reflexivität abgeleitet, normativ):
   wenn das Widget für Feedback **über sich selbst** genutzt werden soll,
   MUSS das Payload-Schema ein Feld `feedback_scope: app | klickdummy-tool`
   führen — sonst kreuzt sich Tool-Drift mit App-Drift im selben
   Provenance-Log.
7. **Self-Trigger-Review-Pflicht:** *compliance-getriggerte* Iterationen
   (Spec-Update aus Policy-Hook oder Coding-Agent-Drift-Erkennung, ohne
   menschlichen Stakeholder als Quelle) MÜSSEN einen PR mit **mindestens
   einem menschlichen Approver** durchlaufen — kein Auto-Merge, auch nicht
   wenn CI grün ist. Schutz vor Cascading-Failures bei fehlerhaften
   Policies oder fehl-erkennenden Agents.
   *Empirie-Hinweis:* meiki Iter. 7 (compliance-getriggerte Migration)
   erfolgte ad-hoc auf explizite User-Autorisierung („autonom bis
   fehlerfrei") — dies entspricht der Pflicht 7 (menschlicher Approver
   per Autorisierung). Ab Rev 12 ist die Autorisierung pro PR explizit
   einzuholen, nicht implizit-rollierend.

**Beobachtungen aus meiki-Empirie (PR #23, 7 Iterationen in 1 h 2026-05-20 —
single-case, Generalisierung steht aus):**

- **Velocity-Indikator (single-case)**: 6 stakeholder-getriggerte
  Iterationen in 46 Min — verkürzt die Erfassungsschleife dramatisch.
  **Belegbarkeit erst nach 2–3 weiteren Cross-Repo-Aktivierungen** (S9-
  Tracking macht das messbar).
- **Single-Threading-Risiko**: ohne Endpoint+Agent (Pfad A vollständig) ist
  die Verarbeitungsschleife (Spec → Render → Commit) Flaschenhals. Pfad A
  ist dann nur *light* (Download → Inbox → Mensch). **Konsequenz für die
  Adoption**: Pfad A erst dann „aktiviert" laut S9, wenn Endpoint+Agent
  laufen — nicht schon bei Widget+Download.
- **Iteration-Typologie**: neben *stakeholder-getriggert* gibt es
  *compliance-getriggert* (Policy-Hook erkennt Drift → Spec-Update läuft
  durch dieselbe Pipe). Beide MÜSSEN ein Provenance-Log-Eintrag erzeugen,
  Letztere zusätzlich PR-Review (Pflicht 7).
- **Reflexivität** (meiki Iter. 6: „Widget verbessert sich selbst über
  Feedback aus sich selbst"): normative Konsequenz in Pflicht 6
  (`feedback_scope`-Trennung), nicht nur Erzählung.

**Referenz-Implementierung:** `meiki-hub:ADR-026` (proposed) +
`docs/01-architektur/mockups/fristenmanagement-klickdummy/` (Widget-Code,
Spec-Block, Issue-Template, Provenance-Log).

**Plattform-Heimat** (Best-Effort, kein Termin in diesem ADR — Repos dürfen
*sofort* anfangen):

- `platform/snippets/klickdummy-feedback-widget.html` (CSS+HTML+JS-Snippet)
- `platform/schemas/feedback-payload.schema.json`
- `platform/scripts/feedback-bridge.py` (Endpoint, Pfad A)

**Bis diese Plattform-Heimat existiert** gilt die *erstbauende
Implementierung* (meiki-hub) als Referenz; andere Repos dürfen
copy-paste-adoptieren. Sobald Plattform-Heimat steht, wandern alle Kopien
binnen 30 Tagen dorthin (Symlink/Submodule). **Verbindlich wird die
Plattform-Heimat erst durch ein separates Adoption-ADR** — diese Rev 12
schafft die *Konvention*, nicht das *Werkzeug*.

## §Requirements-Bridge (optional, Rev 12)

**Was es ist.** Deterministische Forward-Generierung aus der Spec:
`screens-spec.yaml` (oder Äquivalent) → `requirements/use-cases/UC-*.md`,
`requirements/fr.md`, `requirements/nfr.md`, `requirements/schnittstellen.md`,
`requirements/lastenheft-skeleton.md`, `requirements/pflichtenheft-skeleton.md`.
Jede `parity_acceptance` wird zu einer FR; jeder Screen wird zu einem UC;
`class`, `class_evidence`, `off_ramp` werden zu NFRs.

**Asymmetrie ist Absicht.** *Forward* (Spec → Requirements) ist
deterministisch und re-runnable; *Reverse* (Requirements → Spec/Klickdummy)
ist menschlich + Coding-Agent — **keine** automatische Regeneration. Ein
Lastenheft kann Anforderungen enthalten, die der Klickdummy nicht abbildet
(Performance, SLA, Audit-Retention, Barrierefreiheit) — die Brücke
behauptet das nicht.

**Drift-Schutz.** Re-Extract gegen committeten Stand + `git diff --exit-code`
als Make-Target `klickdummy-requirements-drift`. CI rot bei stiller
Divergenz.

**Aktivierungs-Definition** (eindeutig, prüfbar):

Ein Repo gilt als „Requirements-Bridge aktiviert" **genau dann, wenn alle
drei Bedingungen erfüllt sind:**

1. Generierte Artefakte unter `requirements/` sind committed UND tragen
   `source_spec`-Frontmatter (Rückverweis auf die Spec).
2. `make klickdummy-requirements-drift` existiert UND ist Teil des
   Repo-CI-Workflows (z. B. unter `klickdummy: …`-Aggregat-Target).
3. Repo-lokales Klickdummy-ADR referenziert die Aktivierung. Bevorzugt:
   `tags: [klickdummy, requirements-bridge]` in der Frontmatter (maschinen-
   lesbar für Cross-Repo-Inventur). Fallback: Body-Section mit Header
   `## Requirements-Bridge aktiv` (für ADR-Formate ohne Tags-Konvention).

Bei Erfüllung ⇒ Scoreboard S10 = ja. Bei nur 1–2 erfüllt = „in Arbeit",
nicht aktiviert.

**Pflichten bei Aktivierung:**

1. CI-Drift-Gate aktiv (per Aktivierungs-Bedingung 2): re-extract +
   `git diff --exit-code` auf jedem PR. Verhindert stille Divergenz.
2. Alle generierten Artefakte tragen `status: draft|skeleton` im
   Frontmatter — sie sind **Skelette, keine fertigen Dokumente**.
3. Manuell zu ergänzende NFR-Klassen werden explizit als Block in `nfr.md`
   stehen gelassen (Performance / Verfügbarkeit / Datenschutz / Audit /
   Barrierefreiheit / I18n) — die Brücke generiert nur, was die Spec
   hergibt.

*Hinweis:* Pflicht 1 deckt die „Re-Extract bei jedem Spec-PR"-Sorge
implizit ab — bei Spec-Änderung ohne Re-Extract wird das Drift-Gate rot.
Eine separate Pflicht wäre Doppel-Mandat.

**Skript-Cleanup-Konvention (aus meiki-Erfahrung):** Vor dem Schreiben
werden veraltete `UC-*.md` im Zielordner gelöscht. Sonst lässt eine
Screen-Reihenfolge- oder Namensänderung zwei parallele UC-Sets stehen
(echter Drift-Fall, in meiki Iter. 1 entdeckt + per Skript-Erweiterung
behoben).

**Referenz-Implementierung:** `meiki-hub:scripts/klickdummy/extract_requirements.py`
(~280 LOC, eine Quelle wahr, deterministisch, drift-aware).

**Plattform-Heimat** (Best-Effort, kein Termin):
`platform/scripts/klickdummy/extract_requirements.py` als shared Tool mit
CLI-Flags (`--out-dir`, `--no-cleanup`, `--strict-class`). Bis dahin gilt
die meiki-hub-Implementierung als Referenz; copy-paste-Adoption erlaubt;
Migration auf Plattform-Heimat innerhalb 30 Tagen nach Bereitstellung.

## §Executable-Parity-Bridge (optional, Rev 18)

**Opt-in-Capability** (additiv, nicht status-gatend — wie §Co-Creation/§Requirements-Bridge). Spec → ausführbare Parity-/Acceptance-Suite, **forward-only, deterministisch, drift-aware**. Schwester der §Requirements-Bridge (dort Spec → Markdown; hier Spec → *ausführbare* Tests). Empirie: `iil-klickdummy` v1.6.0 (`klickdummy-gen-e2e`), zwei externe Review-Runden (R1 Richtung, R2 Amendment-Text).

**Mechanik.** `parity_acceptance[]` trägt optional `assert: {action, selector, expect}` (`action ∈ {visible, text, clickable, url, count}`); Prosa-`check` bleibt Pflicht ⇒ rückwärtskompatibel. Der Generator emittiert eine pytest/Playwright-Suite, die per `SPEC_RENDERER_BASE_URL` Renderer #1 (Klickdummy) und #2 (echte App) gegen *dieselbe* Assertion fährt. **Parity-grün gegen #2 = I3-Off-Ramp-Gate** (siehe I3 Rev 18). Die Tests überleben den Off-Ramp — die Kontinuität liegt in Spec + Tests, nicht im Wegwerf-Renderer.

**Determinismus + Anti-Drift (operatives Gate).** Generierte Dateien tragen `AUTO-GENERATED` + `Spec-SHA256` und **keinen Zeitstempel**; ein Repo mit aktiver Bridge fährt `make klickdummy-parity-drift` in CI (re-generieren + `git diff --exit-code`, exakt analog `klickdummy-requirements-drift`, S10). Manuelle Edits / veraltete Generate ⇒ CI rot.

**Grenzen (bewusst, gegen Über-Claim).**
- Tests sind regenerierbares Derivat — Spec ≠ Produktionscode, ≠ Test-Harness-Quelle. Bei Prosa↔`assert`-Widerspruch gewinnt die Prosa (Review-Gate; der Generator erkennt Freitext-Konflikte nicht maschinell).
- `parity_acceptance` prüft **Acceptance/Parity**, nicht tiefe Produkt-E2E; handgeschriebene E2E, die eine *bestehende* Spec-Acceptance prüfen, **müssen** deren Spec-ID referenzieren.
- **NFR/Security/A11y/Performance/Audit** sind nicht aus `assert` ableitbar (Requirements-Bridge-Asymmetrie); das Manifest weist das als `uncovered_note` aus.
- Kommunikation: „idee→E2E-**fähig**, mit sichtbarer Operationalisierungsquote" — nicht „geschlossen". `assert`-lose Einträge bleiben sichtbarer `skip` (Skip-Debt), nie stilles Weglassen.

**Manifest.** Je Lauf `*.manifest.json`: `spec_id`, `spec_sha256`, `spec_schema_version`, `generator_version`, `base_url_env`, Coverage (`executable`/`skipped`), `skipped_detail`, `fragile_selectors`, `uncovered_note`.

**Selector-Konvention (Rev 22 — F23 GESCHLOSSEN).** Primärer stabiler Anker: `data-testid`/`data-acceptance-id`, erreichbar als bare CSS **oder** via `testid=`-Präfix (kanonisch ab Rev 22; bare `[data-testid=foo]`-CSS bleibt gültig, ist aber **deprecated** — Manifest-Warnung). Semantisches Fallback-Vokabular (D2): `testid=…`→`get_by_test_id`, `role=…[name=…]`→`get_by_role`, `label=…`→`get_by_label` (stabile Anker, Accessibility-Tree-gebunden); `text=…`→`get_by_text` (fragil, i18n-unstabil — markiert, nicht verboten). Ohne Präfix: bare CSS (`page.locator`), fragil. Off-Ramp-Gate D1: `--strict-selectors` macht fragile Selektoren (bare CSS ohne `data-*`-Anker, `text=`) zu Exit-Code-3-Fehler statt Manifest-Warnung; reine Mockup-Läufe ohne das Flag unverändert. **Externe Zweitmeinung (5 RECs, 2026-06-30):** REC-1 (spec-Attribut `strict_selectors: true` zusätzlich zu CLI-Flag) + REC-2 (Parser-Grenzfälle `role=`-Syntax formal dokumentiert + Roundtrip-Tests für Sonderzeichen/Whitespace) als offene Follow-up-Tickets. Locator-Registry zurückgestellt (Doppelquell-Risiko, F18 — Trigger jetzt geschärft, s. §Offene F-Items).

**Ownership nach Prod.** Org-weites Minimum (wer darf Spec / `check` / `assert` / Skip-Debt / `off_ramp_status` ändern); lokale Klickdummy-ADRs **konkretisieren** nur, divergieren nicht. Anti-Abschwächung: eine Änderung, die `check`/`assert` entfernt/abschwächt oder einen Selektor verfragilisiert, braucht PR-Label `parity-weakening` + fachliche Begründung (fachlicher Reviewer Soll).

**F11-Doppel-Geltung.** Wird `klickdummy_prod_guard.sh` gebaut (F11, **dormant** — #255 geparkt 2026-06-04, siehe Rev 20), erhält es zwei Geltungsgründe statt eines zweiten Checkers (SSoT): **I2** (Demo-/Catalog-/`?demo=`-Route ⇒ Prod-404) **und** **I3** (archivierte Klickdummy-Route nach Off-Ramp ⇒ 404). Bis dahin: manueller, im PR dokumentierter Ersatzbeleg.

Scoreboard **+S13**.

## §Sitemap-Freshness (optional, Rev 24)

**Opt-in-Capability** (additiv, nicht status-gatend — wie §Co-Creation/§Requirements-Bridge/§Executable-Parity-Bridge). Adressiert eine reale Empirie-Lücke: risk-hubs Klickdummy-Sitemap (`klickdummy/sitemap/`, ein KD-Baum-Übersichts-Renderer nach I4) war beim Auffinden **6 Wochen** alt und fehlte eine komplette KD-Welle (5 neue Sub-KDs + mehrere weitere Module) — nicht weil das Regenerierungs-Skript fehlte, sondern weil es nur repo-lokal existierte (`scripts/gen_kd_sitemap.py`) und niemand strukturell daran erinnert wurde, es nach jedem KD-Build neu laufen zu lassen.

**Distribution (Voraussetzung).** Der Generator wurde nach `iil-klickdummy` extrahiert (`klickdummy-gen-sitemap <repo_root> <adr_local> [repo_name]`, folgt der Rev-15-Extraktionskonvention) — Cross-Repo-Verfügbarkeit ist Bedingung, nicht Ergebnis dieses Amendments.

**Mechanik.** Repos, die eine KD-Sitemap führen (`klickdummy/sitemap/screens-spec.yaml` vorhanden), regenerieren sie via `klickdummy-gen-sitemap` und committen das Ergebnis. **Freshness-Gate (exakt analog `klickdummy-requirements-drift`/S10 und `klickdummy-parity-drift`/S13):** ein Make-Target (repo-lokale Konvention: `klickdummy-sitemap-drift`) regeneriert in ein Temp-Verzeichnis und diff'ed gegen den committeten Stand (`git diff --exit-code` oder Byte-Vergleich); Divergenz ⇒ CI rot. Kein plattform-externer Prober (anders als I2(b)) — die Sitemap hat keine Prod-Sicherheitsdimension, nur eine Vollständigkeits-/Aktualitäts-Dimension.

**Grenzen (bewusst, gegen Über-Claim).**
- Das Gate erzwingt *Konsistenz* (committete Sitemap == frischer Regen), nicht *Vollständigkeit* jenseits dessen, was der Generator aus `screens-spec.yaml`-Dateien lesen kann — ein KD ohne Spec-Datei bleibt unsichtbar (kein neuer Mechanismus, gleiche Grenze wie I1).
- Opt-in: Repos ohne Sitemap-Adoption sind nicht betroffen; kein neues Pflichtartefakt für alle Klickdummy-Repos.
- Ersetzt nicht `/kd-scout`-artige Brownfield-Erkennung (Code-vs-KD-Abgleich) — reine KD-Baum-interne Konsistenz.

Scoreboard **+S14**.

## §Distribution — Plattform-Heimat (Rev 13)

**Was Rev 12 als „Best-Effort, kein Termin" markierte, ist jetzt konkret.**
Auslöser: ttz-hub als 6. Klickdummy-Repo + Anspruch *„permanente
Weiterentwicklung wirkt cross-repo"*.

### Drei Bausteine

| Material | Wo | Wie |
|---|---|---|
| **Python-Code** (`check_i1..i4`, `extract_requirements`, `inventory`, `install_snippets`, `registry`) | **`iilgmbh/iil-klickdummy`** (ab Rev 15, extrahiert 2026-05-21 aus platform-monorepo) | **pip-Paket via public PyPI**: `pip install "iil-klickdummy>=1.1,<2.0"`. Fallback Git-URL: `pip install "iil-klickdummy @ git+https://github.com/iilgmbh/iil-klickdummy.git@v1.1.1"`. Implementations-ADR: `iilgmbh:iil-klickdummy:ADR-001`. |
| **JSON-Schemas** + **HTML-Snippets** (Widget v0.5, Issue-Template, Spec-Template, Shell-Bootstrap) | `iil_klickdummy/{schemas,snippets}/` als `package_data` | Mitversendet im pip-Paket. Snippet-Installation pro Repo via Console-Script `klickdummy-install-snippets [--symlink]` nach `<repo>/platform-snippets/klickdummy/`. |
| **Convention-Pfade** (z. B. `~/.claude/policies/klickdummy.md`) | platform-Worktree | **Symlink** (Bestand aus Rev 5, unverändert). |

**Distributions-Wahl-Begründung (Decider-Pivot 2026-05-20):** Initial-Vorschlag
„pip + Git-Submodul" wurde verworfen — Submodul auf platform/ würde das
ganze Repo (hunderte MB) in jeden Klickdummy-Repo ziehen. Sparse-Checkout
ist fragil. **Reine pip-Lösung mit `package_data` für HTML** ist
idiomatisches Python (django/flask/pip-tools machen es so).

### Versionierung

semver. Git-Tag `v{X.Y.Z}` auf platform-main. Repos pinnen
`@vX.Y.Z#subdirectory=...` für reproduzierbare Builds; Major-Bump = ADR-
Update mit Migrations-Cookbook (analog F12-Soft-Migrate). v1.0.0 enthält
den Strict-Mode-Stand (Rev 12 + Pfad-A-Pivot 2026-05-20).

### Widget v0.5 — Plugin-Architektur (Rev 13)

Widget verlangt Konfiguration über `window.KLICKDUMMY_*`-Globals:

```js
window.KLICKDUMMY_SPEC = { id, version, klickdummy_class };
window.KLICKDUMMY_FEEDBACK_REPO = "owner/repo";
// optional:
window.KLICKDUMMY_CATEGORIES = [{value,label}, ...];     // override default 5
window.KLICKDUMMY_PERSONA_HOOK = () => '<persona>';
window.KLICKDUMMY_VERFAHREN_HOOK = () => '<verfahren>';
```

**Plugin-Hooks** machen Repo-Customization möglich ohne Fork — z. B.
ttz-hub-Categories (`datenschutz-bedenken`), risk-hub-Categories
(`compliance`), oder repo-spezifische Persona-Auflösung.

### Coding-Agent (Pfad A-Agent, Vorausschau)

Statt zentralem Service: **GitHub-Action pro Repo**, getriggert auf Label
`klickdummy-feedback`. Workflow-Skelett unter `iil_klickdummy/snippets/`
(als Rev-13-Folge-PR; v1.0 liefert nur das Issue-Template). Existenz der
Action ist die Voraussetzung für Pfad-A-Agent-Aktivierung (siehe
§Co-Creation Aktivierungs-Bedingung 4).

### Eigenständiges ADR — bewusst NICHT

Rev 12 hatte „Plattform-Heimat" als „Best-Effort". Rev 13 macht sie konkret,
**bleibt aber in ADR-211**, weil Distribution-Mechanik ohne Service-Boundary
keine neue Architektur-Entscheidung mehr ist (`adr-threshold.md`: „following
an existing pattern" → kein eigener ADR). Decider-Review 2026-05-20 verwarf
ADR-214-Draft mit dieser Begründung.

## §Multi-Klickdummy-Browser (Rev 14, optional)

**Auslöser:** Stakeholder-Feedback 2026-05-21 (meiki:klickdummy-feedback,
`feedback_scope: klickdummy-tool`, Pfad-A-light): *„erweitere den klickdummy
so, dass er mehrere versionen und verschiedene klickdummies aufrufen kann.
als listbox im linken menu möglich?"*

Erste Empirie durch User-Direct-API-Bridge **außerhalb** der zentral-
Service-Hypothese — bestätigt Rev-13-Pivot-B-Entscheidung.

**Mechanik (in iil-klickdummy v1.1.0):**

- **`iil_klickdummy.registry`** — Python-Modul:
  - `discover_klickdummies(repo_root)` — sucht `klickdummy/<name>/screens-spec.yaml`
    + `docs/01-architektur/mockups/<name>/screens-spec.yaml` (meiki-Fallback)
  - `discover_versions(spec_path, repo_root)` — extrahiert `spec_version`-
    Werte aus Git-History je Spec-File
  - `render_browser_html(klickdummies, output)` — statische HTML mit
    eingebetteten Metadaten (kein externer fetch zur Laufzeit)
- **Console-Script `klickdummy-browser`** — `[--repo .] [--output X.html] [--json] [--cross-repo (v1.2)]`
- **Snippet `browser/browser.html.tmpl`** — Sidebar mit Listbox „Klickdummy"
  + „Version" + Detail-Card (Klasse-Badge, ADR-Ref, Schwester-Klickdummies)
  + iframe lädt aktive `shell.html?feedback=on`

**Stufen-Plan:**

| Stufe | Was | Release |
|---|---|---|
| 1 — Versions-Switcher im selben Klickdummy | Listbox aus Git-Tags / `spec_version`-History | v1.1.0 |
| 2 — Repo-Browser (mehrere Klickdummies im selben Repo) | Listbox aus `discover_klickdummies(repo_root)` | v1.1.0 |
| 3 — Cross-Repo-Browser | `--cross-repo --base ~/github` aggregiert über alle Repos | v1.2.0 (Roadmap) |
| 4 — Live-Web-Service | Hosted Index unter `klickdummies.iil.pet` | Best-Effort, Bedarf-getrieben |

**Aktivierungs-Definition** (analog Co-Creation):

Ein Repo gilt als „Klickdummy-Browser aktiviert" wenn:
1. `klickdummy-browser`-Output (`klickdummy-browser.html`) im Repo committed ist
   ODER in CI/GitHub-Pages generiert wird
2. Repo-lokales Klickdummy-ADR referenziert den Browser-Pfad (optional)

**Was der Browser NICHT macht** (Anti-Patterns):

- ❌ kein Live-Daten-Sammeln (statisches HTML, keine API-Calls zur Laufzeit
  außer optional zu GitHub für Issue-Bridge — separat per Widget)
- ❌ kein Render-Eingriff in den Klickdummy selbst — Browser ist
  *Container*, nicht Modifikator
- ❌ keine Class-Erhaltung-Verletzung — bei `class: mock` ist `browser.html`
  Teil des Wegwerf-Pfads (nicht in Prod-Deploy)

**Empirie-Quelle:** Dieses §-Update entstand durch das **zweite** real
beobachtbare Stakeholder-Feedback durch die A-User-Direct-Bridge
(post Smoke-Test #27); die Idee landet im Provenance-Log und führt direkt
zu v1.1-Code in derselben Session — Iterations-Reflexivität funktioniert
wie in Rev 13 beschrieben.

## §Acceptance-Marker (Rev 16, optional)

**Problem (aus meiki-hub Iter 9, 2026-05-25):** Stakeholder fordern Sichtbarkeit
des Reifegrads je Klickdummy/Screen — *„accepted, getestet, abgenommen"*. Naive
Lösung (Status-Feld pro Screen) hat 7 dokumentierte Schwächen (Status-Drift,
fehlende Evidence, 3-Domänen-im-1-Eimer, Granularitäts-Falle, kein Decay etc.;
siehe Empirie-Quelle unten). **Erweiterung von I1, keine neue Invariante.**

**Schema** (im Klickdummy-Spec, KD- oder Screen-Level, append-only):

```yaml
acceptance:
  spec_signed:                              # PO/PM-Sign-Off (Anforderungs-Akzeptanz)
    - { by: po.dehnert, date: 2026-05-25, ref: workshop-WS-042 }
  ui_walked:                                # End-User-Workshop-Walk (Bedienbarkeit)
    - { by: sb.jugendamt-3, date: 2026-05-23, ref: workshop-WS-044, n_screens: 6 }
```

**Pflichtfelder:** `by`, `date`, `ref`. **Status derivativ** (nie manuell):

| Status | Bedingung |
|---|---|
| `signed` | jüngster Eintrag ≤ 60 Tage alt |
| `stale`  | jüngster Eintrag > 60 Tage alt (Spec-Drift-Verdacht, Re-Walk empfohlen) |
| `missing`| keine Einträge — Rendering unterdrückt (kein Rauschen) |

**Warum genau 2 Achsen (nicht 4):** Smallest-viable. Spec-Sign-Off und User-Walk
sind die zwei *meistgenutzten* Sign-Off-Events im Workshop-Workflow. Weitere
Achsen (validated, impl_parity) sind nicht ausgeschlossen — werden aber erst
mit Empirie aus zweitem Repo nachgezogen (Pre-Check `adr-threshold.md`).

**Trennung gegenüber I3 (Sunset):** Acceptance-Marker sagen *„dieser Walk ist
passiert"*. Sunset sagt *„dieser KD verfällt am Tag X"*. Beide unabhängig.
Ein `stale` Acceptance-Marker ist *kein* automatischer Sunset-Auslöser.

**Trennung gegenüber Impl-Abnahme:** Klickdummy-Acceptance ≠ Vertrags-Abnahme
der späteren Implementierung. Vertragliche Abnahme bleibt I3 Phase-C-Parity.

**Render-Konvention:** Status-Bar je Screen-Render zeigt Chip pro Achse
(`✓ spec_signed` grün, `⚠ ui_walked` gelb bei `stale`, missing nicht
gerendert). Genesor-Übersicht spiegelt Achsen-Status pro KD wieder.

## §UC-Coverage (Rev 16, optional)

**Problem:** Use-Case-Listen leben heute als Markdown-Files (4 Repos im Pilot,
zwei verschiedene Frontmatter-Stile in ausschreibungs-hub + meiki-hub).
Bidirektionale Coverage zwischen UC und Klickdummy-Screen war Ad-hoc-Lookup.

**Konvention** (kompatibel mit bestehendem ausschreibungs-hub-Stil):

```yaml
---                                          # UC-Markdown-Frontmatter
uc_id: UC-WG-001                             # Pflicht — intra-repo eindeutig
name: "Wohngeld-Antrag stellen"              # Pflicht
primaer_akteur: buerger                      # empfohlen
sekundaer_akteure: [bevollmaechtigte]        # optional
realisiert_von_klickdummy: meiki-hub:ADR-032 # empfohlen — Aggregat-Backref
related_screens:                             # bidirektional gelintet
  - meiki-hub:ADR-032#antragsdaten
  - meiki-hub:ADR-032#einkommens_plausi
fv_bezug: FV-OKWOBIS-WOHNGELD                # optional (Konkurrenz-FV)
prio: hoch | mittel | niedrig                # optional
status: draft | reviewed | approved          # optional
---
```

**Cross-Repo-Namespace** `<repo>:UC-NNN` analog I4 — vollqualifiziert
(z. B. `meiki-hub:UC-WG-001`, **nicht** `meiki:UC-WG-001`). Konsistent zu I4
Cross-Repo-ADR-Refs im gesamten ADR-Korpus.

Refs in `related_screens` nutzen das Format `<repo>:ADR-NNN#screen-id`.
Beim Bestand (Iter ≤11) existieren Legacy-Kurzform-Refs (`meiki:ADR-032`);
``klickdummy_lineage.py`` löst diese via Heuristik auf (Prefix +
`-hub`-Suffix). **Neu erstellte UCs** sollen ausschließlich die
vollqualifizierte Form nutzen; die Heuristik bleibt für Migrations-Übergang
bestehen (analog Rev-12-Soft-Migrate) und entfällt nach Cross-Repo-Inventur
ohne Kurzform-Treffer.

**Bidirektionaler Lint** (Erweiterung von I1):

- Jede `related_screens`-Ref muss zu einem existierenden Screen auflösen
  (sonst Coverage-Warning).
- Optional: Screen kann `realizes_use_cases: [<repo>:UC-NNN]` als Rückrichtung
  haben — `klickdummy_lineage.py` linted die Symmetrie.

**Coverage-Output:** Cross-Repo-Heatmap `UCs × KDs` mit Cell-Zähler (Anzahl
realized Screens pro Tupel). Footer listet UCs ohne Realisierung + UCs mit
nicht-auflösbaren Refs. Generator: `klickdummy_lineage.py --genesor`
schreibt `genesor/coverage.html` (no Service-Boundary, statisch).

**SSoT bleibt YAML im git.** Externe UC-Quellen (JIRA, Linear, Excel) sind als
*Read-Only-Import-Adapter* erlaubt — sie schreiben YAML im Repo, niemals
umgekehrt. (Pre-Check `adr-threshold.md`: kein Service, keine Boundary.)

**Markdown-only-UCs ohne Frontmatter** (siehe ausschreibungs-hub `UC-001..003`)
werden im Discovery übersprungen — keine Coverage, kein FAIL. Konvertierung
zu Frontmatter-Stil per repo-lokaler PR, nicht plattform-erzwungen.

### `by`-Konvention (Audit-Trail, pro Achse differenziert)

Achsen haben unterschiedliche Stakeholder-Populationen — eine einheitliche
Login-Pflicht funktioniert nicht (siehe Adversarial-Pass-Finding zu Rev 16:
End-User-Sachbearbeiter:innen haben keinen GitHub-Account, können also
weder PR-Author noch -Approver sein).

| Achse | `by`-Wert | Beglaubigung | Validator-Layer-B-Pfad |
|---|---|---|---|
| **`spec_signed`** | GitHub-Login (Pflicht) | `by` MUSS PR-Author ODER Approver-Login matchen | `gh api repos/<o>/<r>/pulls/<N>/reviews` (Approver) UNION Commit-Author-Liste |
| **`ui_walked`** | Freier Identifier (Persona/Rolle erlaubt, z. B. `sb.jugendamt-3`) | Sponsor-Statement im PR-Body durch Author/Approver: `vouch: ui_walked sb.jugendamt-3 ref: workshop-WS-044` | Parser im PR-Body sucht `vouch:`-Zeilen; Sponsor muss seinerseits GitHub-Login mit Write-Access sein |

**Mechanik gemeinsam:** Audit-Trail lebt im git-PR-Log, nicht im YAML-Text.
`by` allein ist Behauptung; die Beglaubigung ist die git-PR-seitige
Verknüpfung (direkt für `spec_signed`, sponsor-vermittelt für `ui_walked`).

**Beispiel-Werte gehören keine GitHub-Login-Syntax aufzwingen** — die
Beispiele in §Acceptance-Marker (`po.dehnert`, `sb.jugendamt-3`) sind
Rollen-Identifier und gelten dort als zulässige `ui_walked`-Form (oder als
Persona-Slugs in der Übergangsphase, bis Repos eigene Login-Mappings haben).

**F16 (offen):** End-User-Walks ohne GitHub-Identität strukturell sauber
absichern — Sponsor-Pattern ist Provisorium. Schließung-Pfad: nach erster
echter Workshop-Empirie mit mehr als 5 Sign-Off-Akten (siehe §Offene F-Items).

## §Threshold-Reality-Check (Rev 16, sichtbarer Self-Check)

Per `~/.claude/policies/adr-threshold.md` vor Promotion auf `accepted`-Status —
als auditierbarer Block, nicht nur Floskel im Changelog:

| Kriterium | Trifft zu? | Beleg |
|---|---|---|
| Cross-Cutting-Impact >1 Repo | **Ja** | meiki-hub + ausschreibungs-hub Pilot (47 UCs cross-repo: 4 ausschreibungs-hub + 43 meiki-hub) |
| Reversibel? | **Ja** (opt-in pro Repo) | ohne `acceptance:`-Block / UC-Files keine Wirkung |
| Service-Boundary neu? | Nein | `klickdummy_lineage.py` bleibt SSoT (no daemon/API) |
| Data-Sovereignty / Security? | Nein | YAML-im-git, kein remote-state |
| Trade-Off worth recording? | **Ja** | 7-Findings-Adversarial gegen naive Status-Felder |

**Verdict:** ADR-Erweiterung gerechtfertigt. Eigener ADR-21X wurde erwogen
und verworfen (siehe Adversarial-Pass Rev 16 unten). **Risiko-Flag:**
§UC-Coverage führt einen dritten first-class-Knoten (Use Case) ein —
Steel-Man-Argument für eigene Invariante I5. Bewusst als §-Erweiterung
gehalten, bis Cross-Repo-Adoption diese Promotion empirisch rechtfertigt
(siehe F-Items F13/F14/F15 unten).
## §KD-first-Gate (optional, Rev 16)

**Opt-in-Capability** (additiv, nicht status-gatend — wie §Co-Creation/§Requirements-Bridge). Bewusst **zwei Ebenen**, getrennt nach *mechanisch erzwingbar* vs. *Prozess-Empfehlung* (adr-challenger 2026-05-28, gegen das Vacuous-Pass-Risiko C1/C2):

**(1) Coverage-Invariante (mechanisch erzwingbar) — die eigentliche Substanz:** Bei aktiviertem Gate MUSS jeder Spec-Eintrag mit `surface: ui` einen gerenderten Klickdummy-Screen haben (I1/I2). Das ist ein Exit-Code-Check (`klickdummy-i1`-Erweiterung), **kein Selbstauskunfts-S-Item** — die KD-*Existenz* je UI-Spec ist prüfbar, anders als ein zeitliches „vor Impl". Damit wird „KD-first" zur **Coverage-Invariante** (vacuous-pass-sicher), nicht zum unprüfbaren Versprechen.

> **`surface: ui` ist NICHT frei opt-out-bar (schließt den „leere-Menge"-Vacuous-Pass, adr-challenger Re-Pass C1'):** `klickdummy-i1` leitet das Flag aus dem bereits geprüften I1-Coverage-Signal ab — ein Spec-Eintrag, dessen Impl-Route eine UI rendert (Template / HTTP-200-View), **MUSS** `surface: ui` tragen; Weglassen bei vorhandener UI-Route ⇒ FAIL. So erzwingt der Check die Klassifikation, statt sie zu glauben — die Invariante kann nicht durch Weglassen des Felds auf die leere Menge reduziert werden.

**(2) Prozess-Empfehlung (SOLLTE, nicht erzwungen):** Das Stakeholder-Feedback am Klickdummy SOLLTE *vor* der Impl der Surface eingeholt werden — Feedback am klickbaren Prototyp ist schneller/präziser als an laufendem Code/PRs (der Engpass ist die Abstimmung über Layout/Flow/Scope, nicht das Tippen). Auditierbar nur, wenn die Spec einen `signoff:`-Block trägt (`approver` · `date` · `kd_version`); ohne diesen ist es Empfehlung, kein Gate. **Vorwärtsgerichtet:** bestehende Impl bleibt I3-Transition (nicht retroaktiv gegated — impl-first ist Transitions-Zustand bereits existierender Repos, keine Design-Präferenz).

**Ausnahmen:** Backend-only/ohne UI, `bugfix`/`refactor`/`infra`/`docs`/trivial. Maßgeblich ist das aus dem I1-Signal abgeleitete `surface: ui` (s. o.) — eine Surface mit UI-Route lässt sich nicht durch Task-Typ-Selbstdeklaration am Gate vorbeiführen.

**KI-/Daten-Qualität als eigenes Spec-Feld `backend_quality_check:` (A2), nicht als Fußnote:** Ein KD validiert per Definition nur Layout/Flow — Backend-/KI-Output-Qualität (z. B. LLM-Extraktion) ist mit synthetischen Demo-Daten **nicht** prüfbar. Specs mit Pattern `spec-demo` und KI-Wertschöpfung SOLLTEN ein Feld `backend_quality_check:` führen, das eine separate parity-artige Probe gegen das *echte* Backend referenziert (kein Mensch-Signoff, kein synthetischer Demo-Pfad). Empirie: ausschreibungs-hub `document-intelligence-vergabe-analyse` — 3-Tab-Layout per spec-demo-KD (`?demo=`) früh geklärt, die Extraktionsqualität nur per echtem LLM-Lauf (Groq) sichtbar.

**Operationalisierung:** agentic-coding-Workflow, optionaler **Step 2.7 (KD-Gate)** vor Step 3; bei KI-Features `backend_quality_check`-Kriterium in Step 5/6.

**Empirie-Stand:** 1 Feature (2026-05-28). Verbindlichkeit (Coverage-Invariante plattformweit erzwungen) erst nach **3+ Piloten** mit belegtem Velocity-Vorteil — bis dahin opt-in + Scoreboard S12. adr-challenger-Findings adressiert: C1 (Vacuous-Pass → Ebene 1 mechanisch), C2 („Pflicht" in opt-in = Kategorienfehler → SOLLTE), A1 (Coverage-Invariante statt zeitliches Gate), A2 (`backend_quality_check`-Feld).

## §Migration Rev-≤10 → Rev-11 (Rev 12, F12 in Schließung)

**Problem (F12 aus Rev 11):** Repos mit `class: mock-prototyp` (Rev ≤10)
müssen auf Rev-11 4-Pattern (`mock`) umstellen. Ein Hard-Cutover bricht
alle Schwester-Repos gleichzeitig.

**Pattern (aus meiki-hub Iter. 7, 2026-05-20):** *Soft-Migrate mit
Hard-Deadline* — plattformseitig und repo-seitig zweistufig, aber **mit
verbindlicher Frist**:

```python
# scripts/klickdummy/check_i2.py — übergangsweise:
ALLOWED  = {"mock", "stub-demo", "story", "spec-demo"}
LEGACY   = {
    "mock-prototyp": "mock",          # eindeutig, sicheres Auto-Mapping
    "demo-render":   "spec-demo",     # Default-Hinweis im Warning, NICHT
                                      # verbindliche Migration — Repo wählt
                                      # per Rev-11-Auswahlhilfe zwischen
                                      # stub-demo | story | spec-demo.
}
DEADLINE = "2026-08-20"   # = Rev-11-Datum + 3 Monate (Rev-12-Entscheid)
# Vor DEADLINE: bei Match in LEGACY ⇒ ⚠-Warning + Mapping-Hinweis, KEIN FAIL.
# Ab  DEADLINE: bei Match in LEGACY ⇒ FAIL (CI rot), unabhängig von S11.
# Strict-Mode (LEGACY = {}) wird durch S11-Inventur-Skript früher aktiviert,
# sobald Cross-Repo-Inventur 0 Treffer zeigt. Deadline ist die obere Grenze.
```

**Warum Hard-Deadline:** Ohne sie ist Soft-Migrate eine F4-Klasse-Schwäche
(„ewig auf Staging"-Äquivalent für Class-Migration). Ein einzelnes
nicht-migriertes Repo könnte den Trigger ewig blockieren. Die Deadline
zwingt zur Migration unabhängig von Cross-Repo-Adoption.

**Migrations-Schritte je Repo** (~15 Min, mechanisch):

1. `screens-spec.yaml` (oder Äquivalent): `class: mock-prototyp` → `class: mock`
   (Rev-10-Begriff `Mock-Prototyp` mappt eindeutig auf `mock`).
   `demo-render` ist **kein** Auto-Mapping — Repo entscheidet per
   §Auswahlhilfe Rev 11 (Datenquelle × Code-Pfad-Identität), ob das
   bisherige Demo-Render-Pattern `stub-demo`, `story` oder `spec-demo`
   ist. Soft-Migrate-`LEGACY`-Map enthält `demo-render → spec-demo` nur
   als Default-Hinweis im Warning-Output, **nicht** als verbindliche
   Migration.
2. `module-manifest.json` (falls vorhanden): `klickdummy_class:` analog.
3. JSON-Schemata: `enum`-Listen auf 4-Pattern.
4. Frontend-Payloads (z. B. Widget): `klickdummy_class: 'mock'`.
5. ADR-Frontmatter:
   - `tags: [klickdummy]`
   - `class: mock` (oder Rev-11-Wert)
   - `sunset_after: <ADR-Datum + 12 Monate>`
   - `extension_review_required: true`
6. `make klickdummy-i1 klickdummy-i2 klickdummy-i3 klickdummy-i4` → alles PASS.
7. Provenance-Eintrag (falls feedback-log.md geführt wird): „Compliance-
   getriggerte Iteration" dokumentieren.

**Strict-Mode-Trigger (Scoreboard-Item S11)** — Bootstrap-Implementation
(als Teil dieses ADR-Rev mitgeliefert, nicht zirkulär referenziert):

```bash
#!/usr/bin/env bash
# platform/scripts/checks/klickdummy_legacy_class_inventory.sh
# Cross-Repo-Inventur: meldet 'mock-prototyp' / 'demo-render' in
# screens-spec.yaml, module-manifest.json, ADR-Frontmatter, Widget-Code.
# Exit 0 wenn 0 Treffer; Exit 1 sonst (+ Liste Repos+Pfade auf stdout).
set -euo pipefail
REPOS_BASE="${REPOS_BASE:-$HOME/github}"
PATTERNS='mock-prototyp|demo-render'
FOUND=0
for repo in meiki-hub writing-hub risk-hub pptx-hub dev-hub; do
  d="$REPOS_BASE/$repo"
  [[ -d "$d" ]] || continue
  matches=$(grep -rEn --include='*.yaml' --include='*.yml' --include='*.json' \
            --include='*.md' --include='*.html' "$PATTERNS" "$d" 2>/dev/null || true)
  if [[ -n "$matches" ]]; then
    echo "=== $repo ==="; echo "$matches"; FOUND=1
  fi
done
exit $FOUND
```

Sobald Exit 0: separater PR setzt `LEGACY = {}` in `check_i2.py` jedes
Repos (oder zentral, falls Skript-Heimat plattformseitig migriert).
**Spätestens am `DEADLINE` (2026-08-20) wird `LEGACY = {}` unabhängig vom
Skript-Output erzwungen** — Inventur ist die freundliche Variante.

**Migrations-Status — final post-Rev-13 (2026-05-20). Live-Quelle:
S11-Inventur-Skript-Output (siehe Code oben):**

| Repo | Class-Migration | Plattform-Heimat-Adoption (Rev 13) | PRs |
|---|---|---|---|
| meiki-hub | ✅ migriert | ✅ adoptiert | #21, #23, #24, #25 |
| writing-hub | ✅ migriert (`demo-render` → `spec-demo`) | ✅ adoptiert | #21, #23, #24 |
| risk-hub | ✅ migriert (HTML-Files `mock-prototyp` → `mock` in Rev-13-Adoption) | ✅ adoptiert | #125, #126 |
| ttz-hub | — (Erst-Adoption, kein Legacy) | ✅ adoptiert (Erst-Repo) | #5, #6 |
| pptx-hub | ✓ N/A (kein `klickdummy/`-Pfad, §Wann-NICHT) | — | — |
| dev-hub | ✓ N/A (selber Befund) | — | — |

**S11-Inventur (final, 2026-05-20):** 0 echte Drift-Treffer cross-repo;
verbleibende Refs sind LEGACY-Map, History-Kommentare und Compat-Code —
alle beabsichtigt. **Strict-Mode (`LEGACY={}`) aktiviert** in meiki-hub
(#24) und writing-hub (#23). Hard-Deadline 2026-08-20 wurde damit lange
unterschritten — **F12 endgültig geschlossen** bereits zum 2026-05-20.

**Empirie-Validierung Rev 13 (Acceptance-Trigger erfüllt):**

1. ✅ Decider ratifiziert (PR #274 merged)
2. ✅ Pilot-Migration meiki-hub erfolgreich (PR #25, ~10 Min) — Mechanik bewährt
3. ✅ 3 weitere Adoptionen ohne Architektur-Anpassung (writing-hub#24, risk-hub#126, ttz-hub#5)
4. ⏳ Produktive Stakeholder-Iteration durch A-User-Direct-API — wartet auf ersten realen Submit nach A-Agent-Workflow-Aktivierung

Diese Tabelle kann veralten — bei Diskrepanz mit S11-Skript-Output gilt
das Skript. Tabelle wird im **nächsten ADR-Rev** auf Live-Quelle umgestellt
(z. B. GitHub-Project oder generierter Block aus Skript).

## Konsequenzen

**Positiv:** Spec-first beendet Renderer-Wildwuchs; Off-Ramp+TTL verhindert
Static-Leichen auch im Dauer-Staging; der **extern geprüfte** Demo-Render-
Prod-Guard schließt die Sicherheitslücke *cross-repo verifizierbar* (nicht
nur per Repo-Selbstaussage); Entscheid/Scoreboard-Trennung macht den Status
stabil und löst den Acceptance-Deadlock; Enforcement nutzt den bestehenden
Pinned-Worktree-Symlink (policies/README.md), kein Parallelpfad.
**Negativ:** je Repo einmaliger Aufwand `make klickdummy-{i1..i3}`; der
plattform-externe Prod-Probe (S3b) braucht eine erreichbare Registry-Prod-URL
je Demo-Render-Repo; 6 SF-Followups sind Rollout-Aufwand (aber **nicht**
Acceptance-blockierend).
**Governance-Risiko (F8, offen):** security-perimeter + org-bindend, aber
`deciders:[achim]`, `consulted:[]`. Eine per-Vertrauen nicht erzwingbare
Sicherheitsregel (Grund für den externen S3b-Probe) mit Bus-Faktor 1 ist
fragil — **mind. ein `consulted` empfohlen** vor `accepted`.
**Abhängigkeit (F7, Rev 10 angepasst):** `depends_on: []` — die in Rev 9
behauptete Abhängigkeit zu ADR-207 war Konsequenz der Fehl-Auslagerung F5
(siehe Rev 10). ADR-207 ist Doku-Strategie/Ingest, kein Namensraum-Heim.

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Anforderungs-Spec** | Versioniertes, maschinenlesbares Quell-Artefakt (YAML/JSON/Frontmatter); Markdown-Bullets zählen nicht |
| **Klickdummy** | Oberbegriff: *Renderer* der Spec zur frühen Validierung |
| **`mock` (Pattern, Rev 11)** | Wegwerf-Renderer, **separater Code-Pfad**, leere/feste Stubs. Beispiel: meiki-hub. I2-Externprobe N/A |
| **`stub-demo` (Pattern, Rev 11)** | **Realer** Code-Pfad mit synthetischen Daten an dedizierter Demo-Route. I2-Externprobe: Route ⇒ 404 |
| **`story` (Pattern, Rev 11)** | **Realer** Code-Pfad, isolierter Component-Catalog (z. B. Storybook). I2-Externprobe: Catalog-Route ⇒ 404 |
| **`spec-demo` (Pattern, Rev 11)** | **Realer** Code-Pfad, env-gegateter Zustand via Flag. Beispiel: writing-hub. I2-Externprobe: `?demo=` ⇒ 404/disabled |
| **`sunset_after` (Rev 11)** | Pflicht-Frontmatter-Datum für repo-lokale Klickdummy-ADRs; nach Frist ohne Extension ⇒ ADR auto-`deprecated`, Pfad archiviert |
| **Parity-Test** | Renderer↔Implementierung-Äquivalenztest — Gate **und** Off-Ramp |
| **Off-Ramp** | Parity-grün ⇒ mechanische Entfernung der statischen Quelle (Grenze: `min(prod-Release, Parity-grün + N d)`) |
| **Adoption-Scoreboard** | Lebende SF1–SF6-Rollout-Metrik; **gatet `status` nicht** (Rev 9) |
| **`acceptance.spec_signed` (Rev 16)** | Append-only Sign-Off-Liste durch PO/PM; Status derivativ (≤60d=`signed`, >60d=`stale`, leer=`missing`) |
| **`acceptance.ui_walked` (Rev 16)** | Append-only Workshop-Walk-Liste durch End-User; selbe Status-Logik wie `spec_signed`; Beglaubigung via Sponsor-`vouch:`-Statement im PR-Body durch Author/Approver mit Write-Access (siehe §by-Konvention + F16) |
| **Sponsor-`vouch:`-Pattern (Rev 16)** | PR-Body-Zeile `vouch: <axis> <by-value> ref: <ref>` durch Stakeholder mit GitHub-Write-Access; bürgt für Akzeptanz-Eintrag dessen `by`-Wert keine GitHub-Identität ist (typisch `ui_walked` mit End-User-Persona) |
| **`<repo>:UC-NNN` (Rev 16)** | Cross-Repo-Namespace für Use Cases analog I4-Klickdummy-Namespace |
| **`related_screens` (Rev 16)** | UC-Frontmatter-Feld; Refs werden bidirektional gegen Klickdummy-Screens gelintet |
| **UC-Coverage-Heatmap (Rev 16)** | `genesor/coverage.html` — Cross-Repo `UCs × KDs`-Matrix, Cell = realized Screen-Count |

## Acceptance-Trigger

`status` → `accepted`, sobald die Decider den **Entscheid** (I1–I4 +
Enforcement-Pfad) im Review ratifizieren; das Mergen von
`policies/klickdummy.md` ist Teil dieses Akts. Das Adoption-Scoreboard
(SF1–SF6) ist **kein** Acceptance-Vorbehalt (Rev-9-Korrektur von F1/F2).
(Im Frontmatter bewusst kein Custom-Feld — Schema lässt nur Standard-
Properties zu; Acceptance-Logik im Body.)

## Revisionshistorie

Sechs Cascade-Adversarial-Pässe + Schema-/YAML-Härtung:

- **Rev 1** — initial proposal
- **Rev 2** (bf7c4d6) — Spec-first, Prod-Guard, Parity-Off-Ramp
- **Rev 3** (47ff4f9) — Enforcement in-repo, I1/Confirmation executable
- **Rev 4** — R4 prod-Grenze, R3 repo-definierte Checks, R2 Baseline 0/N, R5 Drift belegt, R6 Acceptance-Trigger
- **Rev 5** — Mechanik: `~/.claude/policies` Symlink in gepinnten platform-Worktree (kein Kopier-Sync)
- **Rev 6** — C1-Geltungsbereich (nur registry-Repos); `conforms_to` I4-qualifiziert; SF1-Regex + SF5
- **Rev 7** — C6 auf Script `klickdummy_policy_sync.sh`; SF6
- **Rev 8** — Frontmatter schema-konform (`review_history`/`acceptance_trigger` in Body; YAML-`date:`-Fix)
- **Rev 9 (tiefer Adversarial-Pass)** — **F1/F2:** Entscheid ↔ Rollout entkoppelt (löst Acceptance-Deadlock + oszillierenden Status; C1–C6 → status-neutrales Adoption-Scoreboard). **F3:** I2 um plattform-externen, repo-unabhängigen Prod-Probe erweitert (Sicherheitsinvariante cross-repo verifizierbar statt per-Vertrauen). **F4:** I3 Off-Ramp-TTL `min(prod-Release, Parity-grün+N d)` (Dauer-Staging-Leck). **F5:** I4 → ADR-207 ausgelagert, `scope` entschlackt, „vier"→„drei Invarianten". **F6:** I1 bidirektionale Spec↔Route-Coverage statt Format-Existenz. **F7/F8** als offene Punkte dokumentiert.
- **Rev 10** — **F5 zurückgenommen:** ADR-207 ist Doku-Strategie/Ingest-Trichter (eine Doku-Wahrheit pro Repo, MD>PDF>docx, inbox-Trichter) — **nicht** Cross-Repo-ADR-Namensraum. Die I4-Auslagerung war thematische Fehl-Zuordnung. **I4 zurück in ADR-211** (klickdummy-skopiert; eine plattformweite Verallgemeinerung wäre ein eigener ADR, nicht ADR-207). `depends_on: []`, „drei"→„vier Invarianten" zurück, ADR-207 aus Verwandt/Bezug entfernt (war nur wegen F5 drin).
- **Rev 11 (Bundle #228/#229; orthogonal zu Rev 10)** — **F9 (#229):** I2 von 2 → **4 scharf abgegrenzte Patterns** (`mock`/`stub-demo`/`story`/`spec-demo`) entlang *Datenquelle × Code-Pfad-Identität*. Jedes Pattern erhält eine **distinkte** I2-Externprobe (mock = N/A; sonst je eigene Route/Query). Vermeidet das Theater-Risiko des 4-Pattern-Splits, weil die *Enforcement* je Pattern wirklich anders ist (siehe Glossar/Auswahlhilfe). **F10 (#228):** `sunset_after`-Pflicht-Frontmatter für repo-lokale Klickdummy-ADRs (nicht ADR-211 selbst); Phase-A bekommt damit einen *harten* Termin unabhängig von Parity. Auto-`deprecated` nach Frist, Extension via PR-Review. Enforcement-Script `adr_sunset.sh` als Scoreboard-Item S7; S8 = 4-Pattern-Konformität. I4 bleibt bestehen (Rev 10). **Offene Folge-Punkte:** (F11) `klickdummy_prod_guard.sh` muss pattern-spezifisch verzweigen (Issue #255 SF3-AC vor Bau anpassen); (F12) Migrations-Mapping bestehender Rev-≤10 `Demo-Render`-Repos auf eines der drei Nicht-`mock`-Patterns.
- **Rev 12 (Empirie-getrieben aus meiki-hub PR #23, 7 Iterationen 2026-05-20)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: keine neue Boundary, kein 5. Invariant, kein eigener ADR-21X. **F12 in Schließung** (§Migration Rev-≤10 → Rev-11) — Soft-Migrate-Pattern mit **Hard-Deadline 2026-08-20** (Rev-11-Datum + 3 Monate) etabliert; vor Deadline ⚠-Warning, ab Deadline FAIL; Strict-Mode-Trigger als Scoreboard-Item S11 (Inventur-Skript ODER Deadline schließt F12). **Zwei optionale Capabilities** als Erweiterung von I1: **§Co-Creation-Loop** (Stakeholder-Feedback aus Klickdummy → Spec, 3 Vertrauens-Pfade A/B/C — meiki-hub:ADR-026 als Referenz) und **§Requirements-Bridge** (Spec → UC/FR/NFR/Lasten/Pflicht, deterministisch + drift-aware, asymmetrisch — Forward auto, Reverse menschlich). Scoreboard erweitert um S9 (Co-Creation-Adoption), S10 (Requirements-Bridge-Adoption), S11 (Strict-Mode-Trigger). **Iteration-Typologie:** *stakeholder-getriggert* (klassisch) + *compliance-getriggert* (Policy-Hook erkennt Drift → dieselbe Pipe — meiki Iter. 7 als Erstanwendung). **Reflexivität dokumentiert** (Widget kann sich über sich selbst weiterentwickeln, meiki Iter. 6). **F11 weiterhin offen** (pattern-spezifischer Prod-Guard — gehört in Issue #255-Umsetzung, nicht ADR-Text).
- **Rev 13 (Decider-Pivot 2026-05-20 — Plattform-Heimat konkret + Co-Creation-Pfade neu)** — Auslöser: ttz-hub als 6. Klickdummy-Repo + Anspruch *„permanente Weiterentwicklung wirkt cross-repo"*. **Initial ADR-214-Draft (Distribution + Service-Endpoint) wurde nach Decider-Review als advocatus diabolus zurückgezogen** (4 🔴-Findings: K1 0% Empirie für Endpoint, K3 Coding-Agent existiert nicht, K6/K12 Service-Wartung ohne ROI, K10 Datenschutz-Default falsch herum). **Konsequenzen in Rev 13:** (a) **§Distribution** als ADR-211-§ statt ADR-214 (`adr-threshold.md`: ohne Service-Boundary keine neue Architektur-Entscheidung). pip-Paket `iil-klickdummy` v1.0.0 mit Schemas + Skripten + Widget v0.5 als `package_data`; via Git-URL bis privates PyPI aufgesetzt ist. (b) **§Co-Creation Pfade A neu strukturiert:** `A-light` (download/clipboard, empirisch validiert) + `A-User-Direct` (Widget POSTet direkt an `api.github.com` mit User-PAT in localStorage — GitHub-native Audit/Rate-Limit/Auth) + `A-Agent` (GitHub-Action pro Repo, Voraussetzung nachweisbar). „A-Bridge" mit zentralem Endpoint **gestrichen** — wenn Skalierung Service erfordert, neu evaluieren in Rev 14. (c) **Plugin-Architektur im Widget** (`KLICKDUMMY_CATEGORIES`/`PERSONA_HOOK`/`VERFAHREN_HOOK`) — Repo-Customization ohne Fork. (d) **Widget v0.5 = voller meiki-v0.4-Stand** (Action-Liste, DOM-Snapshot, File-Upload, Scope-Selector, Verfahrens-Kontext) — Iterations-Rückschritt bei Adoption vermieden.
- **Rev 14 (2026-05-21 — Multi-Klickdummy-Browser + public PyPI)** — Empirie-getrieben durch erstes „echtes" Stakeholder-Feedback nach Smoke-Test #27 (Pfad A-light, `feedback_scope: klickdummy-tool`): *„erweitere den klickdummy so, dass er mehrere versionen und verschiedene klickdummies aufrufen kann. als listbox im linken menu möglich?"* **Konsequenzen:** (a) **`iil-klickdummy` v1.1.0** mit neuem Modul `registry.py` + Snippet `browser/browser.html.tmpl` + Console-Script `klickdummy-browser` — Stufe 1 (Versions-Switcher aus Git-History) + Stufe 2 (Repo-Browser mit Listbox + iframe). Stufe 3 (Cross-Repo) als v1.2-Roadmap, Stufe 4 (Live-Service) Best-Effort. (b) **Distribution-Update:** public PyPI (`pip install iil-klickdummy>=1.1,<2.0`) wird Default; Git-URL bleibt Fallback. Privates PyPI nicht weiterverfolgt — public ist niedrigste Reibung und gibt Open-Source-Signal ohne Wartungs-Service-Boundary (analog Rev-13-Pivot-Logik). PyPI-Publish via Trusted Publishing (OIDC), kein API-Token in Secrets. (c) **§Multi-Klickdummy-Browser** dokumentiert Aktivierungs-Definition + 3 Anti-Patterns + 4-Stufen-Roadmap. (d) **Reflexivität gestärkt:** Iter. 8 (Stakeholder-Feedback per A-light) führt direkt zu v1.1-Code in derselben Session — empirischer Beleg, dass Co-Creation-Loop wie in Rev 13 designed funktioniert.
- **Rev 16 (2026-05-25/26 — Empirie aus meiki-hub Iter 9-11: Acceptance + UC-Coverage + Adversarial-Pass)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md` **als sichtbarer §Threshold-Reality-Check im Body dokumentiert** (nicht nur Floskel). **Zwei optionale §-Erweiterungen** von I1: (a) **§Acceptance-Marker** mit zwei orthogonalen Achsen (`spec_signed` für PO/PM-Sign-Off, `ui_walked` für End-User-Workshop-Walk), append-only Listen mit Evidence-Pflicht (`by`+`date`+`ref`), Status derivativ aus jüngstem Eintrag (`signed` ≤60d, `stale` >60d, `missing`); adressiert den 7-Findings-Adversarial-Review gegen naives Status-Feld-Design. (b) **§UC-Coverage** standardisiert UC-Markdown-Frontmatter kompatibel mit Bestand (ausschreibungs-hub + meiki-hub); Cross-Repo-Namespace `<repo>:UC-NNN`; bidirektionaler Lint UC→Screen; Coverage-Heatmap als `genesor/coverage.html`. **`by`-Audit-Trail-Konvention** ergänzt: `acceptance.<axis>[*].by` muss PR-Author/Approver-Login matchen — sonst unbeglaubigte Behauptung. **Adversarial-Pass (2026-05-26)** identifizierte 5 Steel-Mans; 3 davon als F-Items F13/F14/F15 unter §Offene F-Items dokumentiert (Content-Hash, Reverse-Lint, Auto-Skelett-Verzerrung). Stärkster Counter (Steel-Man #1: „§UC-Coverage führt dritten first-class-Knoten ein, Invariante I5 unter Tarnnamen") wurde **bewusst nicht umgesetzt** — bleibt als §-Erweiterung bis Cross-Repo-Adoption I5-Promotion empirisch rechtfertigt. **Pilot meiki-hub** (Iter 9-11, 2026-05-25/26): 47 UCs cross-repo nach Generator-Run (4 ausschreibungs-hub + 43 meiki-hub), 45 realized · davon 28 `auto_generated: true` (Stub) und 17 manuell-validiert · 21 → 50 Coverage-Zellen · Validator-Layer-A 36/47 clean. Beide §-Erweiterungen sind **opt-in pro Repo**. **Cloud-Ultrareview (2026-05-26, PR #297)** identifizierte 4 Findings (1 normal + 3 nits); alle in zweitem Amend gefixt: `by`-Konvention pro Achse differenziert (Login-Pflicht nur `spec_signed`, freier Identifier + Sponsor-Pattern für `ui_walked`), `<spec-id>`-OR-Form aus Ref-Konvention entfernt, vollqualifizierte `<repo>:`-Form als Soll mit Legacy-Heuristik (Soft-Migrate-Pattern Rev 12), Threshold-Check-Empirie-Zahl auf aktuellen Stand korrigiert (18→47), Cross-Ref-Tippfehler §Bezug→§Offene F-Items. Neues F-Item **F16** (`ui_walked`-Beglaubigung ohne GitHub-Identität) als offen dokumentiert.
- **Rev 15 (2026-05-21 — Repo-Extraktion zu iilgmbh/iil-klickdummy)** — Auslöser: 59 offene platform-Issues + PyPI-Publish macht platform-Repo public-sichtbar → Klickdummy-Konsumenten sehen verwirrenden Org-internen Issue-Mix. Plus: iilgmbh-Org als künftige Heimat für `iil-*`-Familie + `risk-hub` (Move-Roadmap). **Aktion:** `packages/iil-klickdummy/` per `git filter-repo --path` extrahiert nach `iilgmbh/iil-klickdummy` (Historie erhalten, 3 sichtbare Commits seit Trennung + Subtree-Detail). v1.1.1 als Patch-Release im neuen Repo (Repo-Move-only, kein Code-Change). PyPI-Trusted-Publisher umkonfiguriert: Owner `iilgmbh`, Repo `iil-klickdummy`, Workflow `publish-pypi.yml`. **Trennung Konvention ↔ Implementation festgeklopft:** ADR-211 (Konvention) bleibt achimdehnert/platform; `iilgmbh:iil-klickdummy:ADR-001` ist Implementations-ADR. Schwester-Implementations (`meiki-hub:ADR-021`, `writing-hub:ADR-180`, `risk-hub:ADR-046`, `ttz-hub:ADR-100`) per `sister_of` cross-verlinkt. **Nebeneffekt:** platform-Issues fokussieren wieder auf platform-weite Themen; iil-klickdummy-spezifische Issues entstehen im neuen Repo (Stale-Bot + Issue-Templates dort aktiv). **Keine Änderung für Konsumenten:** `pip install iil-klickdummy>=1.1,<2.0` funktioniert unverändert (PyPI-Project-Name stabil; nur das Backing-Repo wechselt).
- **Rev 16 (2026-05-28 — KD-first-Gate als opt-in-Capability)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: keine neue Invariante (lebt als opt-in I1/I2-Extension wie Rev-12-§Co-Creation), kein 5. I5, kein eigener ADR-21X. Auslöser: Decider-Wunsch „KD-first für schnelleres/präziseres Feedback; alles erst als KD, dann Implementierung". **adr-challenger-Pass** stellte fest: ein *verbindliches* plattformweites Gate aus **1 Feature** (ausschreibungs-hub `document-intelligence-vergabe-analyse`) widerspräche der Methodik-Lehre Rev 14 („erst Empirie, dann Vertrag") und der `ansatz-offen`-Haltung (retroaktive Non-Konformanz existierender impl-first-Repos = Kategorienfehler wie Rev 9; impl-first ist Transitions-Zustand, keine Präferenz). **Konsequenz:** right-sized auf **opt-in** (§KD-first-Gate) + **vorwärtsgerichtet** (bestehende Impl bleibt I3-Transition, nicht gegated). **KI-/Daten-Qualitäts-Zusatz** (KD validiert Layout/Flow, nicht Output-Qualität — separater Backend-Check Pflicht) als allgemeingültige Klarstellung. Scoreboard +S12 (KD-first-Gate-Adoption, optional, nicht status-gatend). Operationalisierung: agentic-coding **Step 2.7**.

- **Rev 17 (2026-05-29 — Daten-Treue der Anzeige)** — **Klarstellung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: **kein 5. Invariant (I5), kein eigener ADR** — als Klarstellung an I1 angehängt (analog Rev-16 „KI-/Daten-Qualitäts-Zusatz“). Regel: im Klickdummy ausgegebene Zahlen sind **berechnet, nicht literal** (Mock-Daten synthetisch, Berechnung echt); Cross-Screen-Aggregate aus **einer** Quelle. Enforcement = **Review-Gate** (nicht exit-code-prüfbar). **Empirie bewusst dünn benannt: 1 Instanz** (design-hub `tenant-angebote`, hartkodierte „4“ doppelt in Liste + Dashboard-Kachel) — daher als Klarstellung statt Gate **right-sized**; Promotion zu I-Status erst bei Cross-Repo-Evidenz (vgl. Rev-16-Logik + Steel-Man #1 „I5 unter Tarnnamen“, bewusst nicht umgesetzt).

- **Rev 18 (2026-05-31 — Executable-Parity-Bridge)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: keine Boundary, **kein 5. Invariant (I5)**, kein eigener ADR-21X — opt-in-§-Erweiterung von I1 (Muster Rev 12/16), die die **bestehende** These „Parity-Test ist das Konformitäts-Gate" *ausführbar* macht (kristallisiert, kehrt nicht). **I1-Klarstellung:** ausführbare Parity-Tests sind regenerierbares Derivat (Spec ≠ Prod-Code/Test-Harness); Determinismus (kein Zeitstempel im File) + Drift-Gate `klickdummy-parity-drift` (Reuse S10); Prosa↔`assert`-Konflikt = Review-Gate. **I3-Härtung:** Off-Ramp nur mit Renderer-#1-Entfernung (`off_ramp_status: removed`) **und** negativem Reachability-Beleg; „max. eine lebende UI-Impl/Screen"; Archiv read-only (Reaktivierung re-triggert I3). **Ehrliche Reichweite (zentrale Runde-2-Korrektur):** F4 **nur für inventarisierte Routen** geschlossen — Alias-/Preview-Risiko offen (F20). **Neue §Executable-Parity-Bridge** (opt-in): `assert`-Vokabular, Selector-Konvention, Reproduzierbarkeits-Manifest mit Coverage-/Skip-Transparenz, Parity≠Deep-E2E (Deep-E2E *muss* Spec-IDs referenzieren), org-weites Ownership-Minimum. Scoreboard **+S13**. **F11** Doppel-Geltung (I2+I3, ein Checker) — bis Bau provisorischer manueller Ersatzbeleg. Neue offene **F17** (`assert`-DSL-Lebenszyklus), **F18** (Selector-Fragilität / Locator-Registry zurückgestellt), **F19** (Operationalisierung cross-repo via Genesor), **F20** (Spec-ID-Route-Inventar gegen Alias-/Preview-Leck). **Empirie:** Keystone `iil-klickdummy` v1.6.0 (`klickdummy-gen-e2e`, 34 Tests grün, inkl. Determinismus-Fix aus Runde 2) + **zwei** externe LLM-Zweitmeinungen (R1 25 RECs, R2 15 RECs), Step-5-getaggt. **Implementations-PRs:** iilgmbh/iil-klickdummy #9 (Keystone, gemergt), #10 (CI-Node24, gemergt).

- **Rev 19 (2026-06-01 — Konzept-Doc als idea-Vorstufe)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md` (**bewusst grenzwertig**): ein neues CC-Skill (`/konzept`), das eine Datei schreibt, ist „Feature nach Muster" (wie `idea-intake`/`use-case`, ohne eigenes ADR) → für sich CHANGELOG+PR. **Verankert wird daher nur** die echte Architektur-Klarstellung: *vor der Spec darf ein persistent referenzierbares Artefakt existieren, ohne I1 zu verletzen* — **kein 5. Invariant (I5)**, keine Boundary, kein eigener ADR-21X; Methodik/Tiers/Agentenrollen des Skills werden **nicht** kanonisiert (sonst Rückfall auf CHANGELOG+PR). **I1-Klarstellung:** `KONZ-<repo>-NNN` (Stufe `idea`) ist Rationale-Artefakt, **kein SoR/Anforderungsquelle**; ab Spec-Existenz nur Spec normativ; T1/T2 persistieren als Annahmen-Ledger ohne Anforderungs-Freitext (Form-Härtung gegen „wird-als-Vor-Anforderung-gelesen"). **I3:** `review_by`-TTL + `superseded_by_spec`-CI-Gate (Edit-Block ohne `reactivation_reason`+`I1-review`). **I4:** Namensraum `repo:KONZ-NNN`. Neue offene **F21** (Konzept-Doc-vs-Spec-Upstream-Drift; Gate hebt von „dokumentiert" auf „kontrolliert", Sekundärlücke F21b: Spec ohne gesetztes `superseded_by_spec`). **Empirie:** Skill aus Maximal-Monolith destilliert, gehärtet durch T1-Dogfood + **eine externe LLM-Zweitmeinung** (16 AD- + 6 THR- + 6 OOTB-Befunde eingearbeitet); erster Produktivlauf `iilgmbh/iil-klickdummy:KONZ-001` (T2). **PRs:** achimdehnert/platform #370 (Skill+Template, gemergt), iilgmbh/iil-klickdummy #16 (KONZ-001+Teil-A, gemergt).

- **Rev 20 (2026-06-04 — Parity-Schicht dormant + I2(b)-Ehrlichkeit)** — **Erweiterung, kein Entscheid-Widerruf**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: die Executable-Parity-Bridge ist opt-in/nicht-status-gatend → Dormancy lebt im **Scoreboard (S13→`dormant`, `dormancy_review_by: 2026-12-04`)**, nicht als Invarianten-Änderung. **Empirie (verifiziert durch Ausführung + plattformweiten Sweep, 2026-06-04):** Mechanismus belegt (A1 — *eine* generierte Suite gegen zwei unabhängige Renderer: #1 grün, #2 rot auf injizierten Divergenzen), aber **0 reale Renderer #2** plattformweit — drei Lücken: keine ausführbaren `assert` außer dem `risk-hub:avv-pflege`-Stub (dessen Asserts das KD-Gerüst prüfen, keine App-UI), **0 `data-testid`** in den Apps (`ausschreibungs-hub`/`nl2iot-hub`), und `gen_e2e` ohne **Auth-Modell** (login-gegatete Routen wie `bieterpilot.de/angebote/` → 302 → /login/ sind nicht testbar). **I2(b)-Korrektur (accepted Body):** `klickdummy_prod_guard.sh` (F11) ist **unimplementiert/dormant** (#255 geparkt) — bis Bau bindet faktisch nur die Selbst-Deklaration (a); ADR-216 §I2-Probe ebenso dormant. **Neue offene F22** (Generator-Auth-Modell, Voraussetzung jeder echten Bridge) und **F23** (REC-7: soll Renderer #2 künftig einen stabilen UI-Testkontrakt via `data-testid`/Manifest liefern, oder die Bridge auf semantischere Selektoren umstellen?). **Reaktivierungs-Trigger (REC-1, messbar statt vage):** ALLE VIER Bedingungen — (1) echter Renderer #2, (2) ≥1 fachlicher `assert`-Block, (3) Selektor-/Testkontrakt für die echte App, (4) Auth-/Session-Modell der Suite; ein einzelner nomineller Renderer #2 reaktiviert NICHT. **`review_by: 2026-12-04` erzwingt (REC-2) eine harte Entscheidung** reactivate|delete|re-charter — Default ohne erfüllte Bedingungen = delete/re-charter, kein stilles Verlängern. **Naming-Korrektur:** `klickdummy-parity-drift` prüft Spec↔Datei-Drift, **nicht** Parität — im Generator-Header klargestellt (iil-klickdummy v1.22.2, PR #54). **I3-Phase-A (`sunset_after`-TTL) bleibt hart aktiv** (gegen „Mock lebt ewig", adr-challenger #2). **Was aktiv bleibt:** I1, I2-Pattern-*Deklaration*, I4, Co-Creation, Requirements-Bridge, Discovery — für das Mockup-Stadium. **Lessons-Learned (REC-5):** opt-in-Bridges erst dann `accepted`-nah dokumentieren, wenn ≥1 realer End-to-End-Pfad gegen die Zielklasse der Systeme gelaufen ist — synthetische Diskriminierungsfähigkeit (A1) belegt den *Mechanismus*, nicht die *Plattformreife*. **Follow-up (REC-10, separat & kleiner):** „Negative Off-Ramp Witness" als pragmatische Alternative zur vollen Parity-Bridge prüfen — Off-Ramp verlangt zunächst nur maschinenlesbaren Beleg (alte KD-Route ⇒ Prod-404; Zielroute nach Login erreichbar; minimaler Smoke-Check auf erwarteten Titel/Landmark), damit echte Off-Ramps nicht auf die Reaktivierung der großen Generator-Schicht warten.

- **Rev 22 (2026-06-30 — F23 GESCHLOSSEN: Selektor-Kontrakt gehärtet, Hybrid D1+D2+D3)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: keine neue Invariante, keine neue Boundary, kein eigener ADR — härtet die bestehende Selector-Konvention (Rev 18/21) durch ein opt-in-Gate und ein dokumentiertes Fallback-Vokabular; das ist Erweiterung nach bestehendem Muster. **F23 geschlossen via KONZ-iil-klickdummy-007 (T2, Hybrid-Empfehlung, 2026-06-30).** Drei Teile: **(D1)** `--strict-selectors`-Flag (opt-in, Off-Ramp-Pfad setzt es): fragile Selektoren → Exit-Code 3 statt nur Manifest-Warnung; reine Mockup-Läufe unverändert. **(D2)** Präfix-Dispatch im `selector`-String: `testid=`→`get_by_test_id`, `role=…[name=…]`→`get_by_role`, `label=`→`get_by_label` (stabile Anker, zählen nicht als fragil); `text=`→`get_by_text` (fragil, i18n-unstabil, markiert); bare CSS ohne `data-*` weiterhin fragil. `selector` bleibt `string` — **kein Schema-Bruch**, Bestands-Specs bit-identisch gültig. Bare `[data-testid=foo]`-CSS **deprecated** (Manifest-Warnung; `testid=foo` wird kanonischer Weg); kein Exit-Code bis zur nächsten Major-Version. **(D3)** Locator-Registry (F18) unverändert zurückgestellt; Trigger geschärft (REC-5): „≥2 Consumer-Specs müssen Selektor wegen App-Implementierungsänderung ändern" — zählbar, nicht interpretierbar. **Warum kein „B statt A":** semantische Selektoren werden als Fallback *eingegliedert*, nicht als Ersatz — der einzige real grüne E2E-Pfad (Rev 21, 3/3 via `data-testid`) bleibt primär. **Empirie:** `iil-klickdummy` v1.29.0 — D1+D2 implementiert; 4 neue Tests (Präfix-Dispatch, Routing, Fragilität, Off-Ramp-Gate inkl. Exit-3 + Default-0 + stabiler-Anker-grün), 151 Tests grün, Linter clean. **Externe Zweitmeinung (5 RECs, 211-response.md):** Empfehlung „Überarbeiten" (nicht Ablehnen). AD-1/REC-1 (spec-Attribut `strict_selectors`) + AD-2/REC-2 (Parser-Grenzfälle `role=`-Syntax) als offene Follow-up-Tickets; AD-3/REC-3 (`[data-testid=foo]` deprecated) direkt adressiert; AD-4 (`text=`-Widerspruch) **widerlegt** — `text=` dispatcht auf `get_by_text` (valider Fallback) und ist fragil (bei `--strict-selectors` geblockt), kein Widerspruch da Off-Ramp Stabilität verlangt; AD-5/REC-5 (F18-Trigger) direkt adressiert (D3). **Ehrliche Reichweite:** Präfix-Vokabular wirkt in Konsumenten-Repos erst nach `pip install iil-klickdummy>=1.29`; bis dahin nur im Generator-Repo aktiv. **PRs:** iilgmbh/iil-klickdummy #89 (KONZ-007), #90 (D1+D2 Implementierung, gemergt).

- **Rev 21 (2026-06-13 — Parity-Bridge REAKTIVIERT: Wertthese erstmals eingelöst)** — **Erweiterung, kein Entscheid-Widerruf**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: nicht-status-gatend → der Statuswechsel lebt im **Scoreboard (S13 `dormant`→`reaktiviert`)**, nicht als Invarianten-Änderung. **Auslöser ist der in Rev 20 messbar definierte Reaktivierungs-Trigger (REC-1) — keine freie Entscheidung, sondern Bedingungseintritt:** ALLE VIER Bedingungen erstmals erfüllt und **durch Ausführung gegen die echte App verifiziert** (nicht behauptet): (1) echter Renderer #2 = `risk-hub` `/sds/review/` (live, login-gegatete Django-App); (2) ≥1 fachlicher `assert`-Block = `risk-hub:klickdummy-spec-sds-verwalten` (3 ausführbare Asserts); (3) Selektor-/Testkontrakt = `data-testid` (`sds-review-queue`/`-row`/`-verify-btn`) in `templates/global_sds/review_queue.html`; (4) Auth-/Session-Modell = `storage_state` via `browser_context_args`. **F22 (Generator-Auth-Modell) GESCHLOSSEN.** **Beweis (empirisch, lokal gefahren):** dieselbe generierte Suite läuft 3/3 grün gegen Renderer #2 **und** wird rot, sobald ein App-`data-testid` vom Spec-Kontrakt abweicht (Divergenz injiziert, *ausgelieferter* HTML verifiziert — gunicorn-Template-Cache erzwang Restart, sonst falsch-positiv) → die Suite diskriminiert **App↔Spec-Drift**, nicht nur Mockup-gegen-sich-selbst (A1→A2). **Zwei „gebaut, nie ausgeführt"-Generator-Bugs gefunden+gefixt** (beide bestanden Unit-Tests, weil die nur Text-Marker prüften): (a) `auth.storage_state` emittierte die nicht-existente API `page.context.set_storage_state(path=…)` → `TypeError` gegen jeden login_required-Renderer; (b) `visible`/`text`/`clickable` brachen an Playwright-Strict-Mode bei mehrfach matchenden Kontrakt-Selektoren → `.first`. **Lesson-Learned (verstärkt Rev-20-REC-5):** „gemergt ≠ ausgeführt ≠ belegt" — der billigste Check (Suite *einmal* gegen die Zielklasse laufen lassen) kippte sowohl die Descope-Hypothese als auch zwei latente Feature-Bugs; opt-in-Bridges erst nach realem E2E-Pfad als reif führen. **Verbleibende Folge-Arbeit (kein Blocker der These):** CI-fähige risk-hub-Suite braucht deterministischen Seed (count-Asserts sind dateninduziert) + Auth-Automation; F11/`klickdummy_prod_guard.sh` bleibt **dormant** (#255, unberührt von dieser Rev); F23 (stabiler UI-Testkontrakt als Konvention) offen. **PRs:** iilgmbh/iil-klickdummy #67 (Generator-Fixes + Regressionstest, 141 Tests grün).

- **Rev 23 (2026-07-05 — Content-Screen-Typ: route-lose Marketing/Onboarding-Screens)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: **keine neue Invariante (kein I5), keine neue Boundary, kein eigener ADR** — additive, opt-in-§-Erweiterung des Renderers nach bestehendem Muster (Rev 12/16/18), die den bereits vorhandenen Leerzustands-Zweig füllt. **Motivation (geerdet, nicht spekulativ):** ein KD soll die gesamte Eintritts-Journey abbilden (kalter Besucher → Value), damit Stakeholder von Anfang an Feedback geben; der Daten-Screen-Renderer konnte bisher nur `datafields`/`local_entities` darstellen → Marketing/Landing-Screens (Hero/Value-Prop/CTA, keine Daten-Entities) rendern leer. **Neu:** optionales Screen-Feld `content: [{type: hero|prose|cta|media|plan_table}]` + `off_route: bool`; Renderer-Branch `_render_content_blocks()` am bestehenden Leer-Fallback-Hook, alle Spec-Strings `html.escape` (S-02/S-03-Härtung). **Additiv, kein Schema-Bruch:** Bestands-Specs ohne `content:` rendern bit-identisch; ein Content-Screen ist **additiv zu einer bestehenden Screen-Klasse** (Flow-Knoten via `next_screens`/`back_screen` oder Assertions-Screen), kein neuer Screen-Typ im anyOf. **Block-Typen bewusst auf 5 begrenzt** (kein Marketing-Builder). **I1-Klarstellung:** `content:` ist Render-Hilfe für route-lose Screens, kein Anforderungs-SoR; `off_route: true` ist **Vorwärts-Marker** — verifiziert (`check_i1.py` ist schema-only), es existiert **kein** Route↔Screen-Coverage-Gate im Code, das ihn heute konsumiert; ein künftiges Coverage-Gate muss ihn honorieren. **Reifegrad ehrlich:** das Feld ist im Schema **`experimental`** markiert bis zu dieser Ratifizierung; nach Merge dieser Rev gilt es als akzeptierte opt-in-Konvention. **Empirie (durch Ausführung belegt):** iil-klickdummy **v1.31.0** (PyPI, Wheel+sdist verifiziert), 4 neue Tests inkl. XSS-Escape, 201 Tests grün; Dogfood `travel-beat` Onboarding-Journey-KD (#59) — `landing` rendert nach Umstellung Hero/Prose/CTA (`<h1>Deine Reise wird zur Geschichte.</h1>`) statt Leerfläche, `klickdummy-genesor` Smoke 1/0. **Konzept:** `KONZ-iil-klickdummy-009` (T2). **PRs:** iilgmbh/iil-klickdummy #130 (KONZ-009), #132 (Impl, gemergt), #133 (Release v1.31.0, gemergt). **Ehrliche Reichweite:** wirkt in Konsumenten-Repos erst nach `pip install iil-klickdummy>=1.31`; `content:` rendert nur für Screens ohne Daten-Entities.

- **Rev 24 (2026-07-07 — §Sitemap-Freshness: KD-Übersichts-Drift-Gate)** — **Erweiterung, kein neuer Entscheid**; `status` bleibt `accepted`. Pre-Check per `adr-threshold.md`: **keine neue Invariante, keine neue Boundary, kein eigener ADR** — additive opt-in-§-Erweiterung von I1 nach bestehendem Muster (Rev 12 §Requirements-Bridge/Rev 18 §Executable-Parity-Bridge: Spec → regenerierbares Derivat + Drift-Gate). **Auslöser (geerdet, nicht spekulativ):** risk-hubs KD-Sitemap (`klickdummy/sitemap/`) war beim Auffinden 6 Wochen alt und fehlte eine komplette DSB-KD-Welle (5 neue Sub-KDs, #394-#399) + mehrere weitere Module (verifiziert: 11 Wurzeln/20 Knoten committet vs. 19 Wurzeln/46 Knoten nach Regen) — das Generator-Skript (`scripts/gen_kd_sitemap.py`) existierte nur repo-lokal, kein struktureller Zwang zur Neugenerierung. **Voraussetzung geschaffen:** Generator nach `iil-klickdummy` extrahiert als `klickdummy-gen-sitemap <repo_root> <adr_local> [repo_name]` (Rev-15-Extraktionskonvention, repo_root/adr_local/repo_name jetzt Parameter statt hartkodiert). **Neu:** §Sitemap-Freshness — Repos mit `klickdummy/sitemap/screens-spec.yaml` SOLLEN ein Drift-Gate (`klickdummy-sitemap-drift`, exakt analog `klickdummy-requirements-drift`/S10 und `klickdummy-parity-drift`/S13: re-generieren + `git diff --exit-code`) in CI führen. Opt-in, nicht status-gatend, kein neues Pflichtartefakt für Repos ohne Sitemap-Adoption. **Grenzen:** erzwingt Konsistenz (committet == frisch generiert), nicht Vollständigkeit jenseits vorhandener `screens-spec.yaml`-Dateien; kein Ersatz für Brownfield-Erkennung (`/kd-scout`). Scoreboard **+S14**. **PRs:** iilgmbh/iil-klickdummy #143 (Extraktion, gemergt); risk-hub-Adoption folgt separat.

## Bezug

- **Playbook:** `docs/concepts/CONCEPT-003-klickdummy-playbook.md` — Begleit-Dokument zu diesem ADR (wie konkret implementieren, Stack-Patterns, Lessons Learned, Repo-Adoptions-Status)
- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 · meiki-hub:ADR-026 (Co-Creation-Loop + Requirements-Bridge — Rev-12-Empiriebasis) — Mapping auf Rev-11-Patterns in §Auswahlhilfe
- Followups `adr-211-followup` SF1–SF11 (Adoption-Scoreboard, **nicht status-gatend**) — S7/S8 durch Rev 11, S9/S10/S11 durch Rev 12
- Closes-on-acceptance: **#228** (sunset_after-Frontmatter, F10) und **#229** (4-Pattern-Taxonomie, F9). #255 SF3-AC muss vor Bau an pattern-spezifischen Prod-Guard angepasst werden (F11, **dormant** — Rev 20). **F12 geschlossen durch Rev 12** (§Migration).
- meiki-hub PR #23 (`feat/klickdummy-feedback-loop-poc`, 7 Iterationen) — Empiriequelle für Rev 12; insbesondere `docs/01-architektur/mockups/fristenmanagement-klickdummy/feedback-log.md` (Provenance + Iteration-Typologie).
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (meiki-hub-Auto-Memory, `drift: true`)
- Policy `adr-threshold.md` (Selbsttest — Rev 12 begründet Erweiterung statt neuem ADR; Rev 16 dokumentiert den Self-Check sichtbar als §Threshold-Reality-Check)

## Offene F-Items (durch Rev 16 dokumentiert, nicht geschlossen)

- **F13 (Layer-C-Content-Hash)**: `acceptance.<axis>[*]` speichert kein Content-
  Hash des UC/Spec-Standes bei Sign-Off. Stale-Decay greift erst nach 60d —
  Spec-Drift bleibt bis dahin unsichtbar. Schließung-Pfad: bei erstem realem
  „ich habe was anderes signiert"-Konflikt-Bericht (Rev 17).
- **F14 (Reverse-Lint Screen→UC)**: §UC-Coverage linted UC→Screen, aber nicht
  Screen→UC. Klickdummy-Spec mit Orphan-Screens (kein UC referenziert sie)
  wird nicht gefunden. Schließung-Pfad: Validator-Erweiterung + `uc-coverage-
  exempt: <reason>`-Opt-out im Spec.
- **F15 (Coverage-Verzerrung durch Auto-Skelette)**: `auto_generated: true`-UCs
  werden in Coverage-Metrik voll mitgezählt; Pilot meiki-hub zeigt 96%
  „realized", davon 60% Auto-Skelette ohne Stakeholder-Walk. Schließung-Pfad:
  Coverage-Split „echt vs. auto" in Heatmap + UC-Index.
- **F16 (`ui_walked`-Beglaubigung ohne GitHub-Identität)**: End-User wie
  Sachbearbeiter:innen im Workshop haben strukturell keinen GitHub-Account.
  Rev 16 nutzt **Sponsor-Statement** (`vouch:` im PR-Body durch
  Author/Approver mit Write-Access) als Provisorium; das ist bisher nicht
  empirisch validiert. Schließung-Pfad: nach 5+ realen Workshop-Sign-Offs
  prüfen ob das Pattern trägt oder eine alternative Mechanik nötig ist
  (z. B. separates Sign-Off-Repo, signed digital token, OAuth-Flow für
  Workshop-Teilnehmer).

- **F17 (`assert`-DSL-Lebenszyklus, Rev 18)**: Erweiterungsregel für `action`-
  Typen (Semantik + Negativbeispiel + Generator-Fixture + Kompat-Notiz) **und**
  Schema-Versions-Deprecation/Migration (`spec_schema_version`). Ohne das:
  DSL-Drift + Legacy-Generator-Matrix bis 2028. Schließung-Pfad: erster RFC für
  eine neue Action erzwingt die Regel.
- **F18 (Selector-Fragilität / Locator-Registry zurückgestellt, Rev 18)**: die
  `data-*`-Konvention + Rev-22-Härtung (D1+D2) *mildern* das UI-Refactor-Risiko,
  lösen es strukturell nicht. Eine Locator-Registry (Spec nennt fachliche ID, App
  mappt Selektor) ist bewusst zurückgestellt (Risiko, selbst Doppelquelle zu werden).
  **Schließung-Pfad (Rev 22 — konkretisiert, REC-5):** messbarer Trigger =
  „Selektor-String in ≥2 Consumer-Specs muss *wegen einer App-Implementierungs-
  änderung* geändert werden" — zählbar (Issue-Spur je betroffener Spec), nicht
  interpretierbar als „irgendein Refactor". Bis dahin: Konvention + D1+D2 aktiv.
- **F19 (Operationalisierungsquote cross-repo, Rev 18)**: Skip-Debt/fragile-count
  sind pro Lauf im Manifest sichtbar, aber nicht org-weit aggregiert.
  Schließung-Pfad: Genesor zeigt `pipeline_status` + Parity-Status + Skip-Quote
  in **einem** Statusmodell (S13-Mindestdatensatz).
- **F20 (Spec-ID-Route-Inventar — Anti-F4-Restlücke, Rev 18)**: der I3-
  Reachability-Beleg schließt F4 nur für **bekannte/inventarisierte** Routen;
  Alias-, CDN-, Preview-, Storybook- und neu entstandene Einstiegspfade bleiben
  Restrisiko. Schließung-Pfad: maschinenlesbares Inventar erlaubter lebender
  Routen je Spec-Screen-ID — minimal als CI-Artefakt startend, später Scanner
  über Build-/Deploy-Metadaten (F11-Erweiterung).
- **F21 (Konzept-Doc-vs-Spec-Upstream-Drift, Rev 19)**: ein `KONZ-`-Doc, das
  *nach* Entstehen seiner Spec inhaltlich weitergepflegt wird, wird zur zweiten
  Anforderungs-Wahrheit. **Mitigation:** I1-Archivregel + `superseded_by_spec`-
  CI-Gate (Edit-Block ohne `reactivation_reason`+`I1-review`) + `review_by`-TTL +
  Ledger-Form für T1/T2 (kein Anforderungs-Freitext). **Reichweite:** das Gate
  *kontrolliert* den Edit-nach-Spec-Pfad, sobald gebaut. **Sekundärlücke F21b:**
  eine Spec, die entsteht *ohne* `superseded_by_spec` zu setzen, bleibt unerfasst
  — Schließung-Pfad: `klickdummy-sync`-analoger Cross-Check Spec-Existenz ↔ Feld.
