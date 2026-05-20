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
- **Adversarial reviews:** sechs Cascade-Pässe (Rev 2/3/4/9 + Rev 10 F5-Rollback + Rev 11 #228/#229) + Rev-12-Empiriebasis (meiki-hub PR #23, 7 Iterationen 2026-05-20), siehe Revisionshistorie

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
| **I1 Spec-first** | Maschinenlesbares, versioniertes Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter); Markdown-Bullets zählen nicht. Klickdummy rendert es, ist nicht die Quelle. **Bidirektionale Coverage:** jede Impl-Route hat einen Spec-Eintrag *und* jeder Spec-Eintrag eine Route/Screen — kein einseitiges „Datei existiert & rendert". *Rev 12:* die Spec ist auch der **Eingang für Anforderungs-Updates** — optional über Co-Creation-Loop (§Co-Creation, opt-in) und **Ausgang** für abgeleitete Requirements (§Requirements-Bridge, opt-in). | `make -C <repo> klickdummy-i1` (Exit-Code), CI-verifiziert — prüft Spec↔Route-Coverage, nicht nur Spec==Render |
| **I2 Prod-Sicherheit (4-Pattern, Rev 11)** | Genau **ein** Pattern je Klickdummy, **explizit deklariert**: `mock` / `stub-demo` / `story` / `spec-demo` (Achsen: *Datenquelle × Code-Pfad-Identität*; vollständige Definition siehe Glossar). „Kein Pattern deklariert" = I2-Verstoß (kein vacuous pass). Die Vereinfachung *Mock-Prototyp/Demo-Render* (Rev ≤10) wird hier verfeinert, weil die drei Nicht-`mock`-Patterns *distinkte* Prod-Probes erfordern. | **Zwei Schichten:** (a) repo-definierter `make -C <repo> klickdummy-i2` (Selbstaussage des Patterns); (b) **plattform-externer Prod-Probe** `klickdummy_prod_guard.sh` mit pattern-spezifischem Verhalten: `mock` ⇒ N/A (Pfad nicht in Prod-Deploy); `stub-demo` ⇒ deklarierte Demo-Route 404; `story` ⇒ Catalog-Route (z. B. `/storybook/`) 404; `spec-demo` ⇒ `?demo=<state>` 404/disabled. (b) bleibt das **bindende Cross-Repo-Signal** (F3) |
| **I3 Lebenszyklus + TTL + Sunset (Rev 11)** | **A ohne Zielsystem:** Pflicht-Frontmatter `sunset_after: <ISO-Datum>` in der Repo-Klickdummy-ADR (Default ADR-Datum + 12 Monate); nach Fristablauf ohne PR-Extension ⇒ ADR auto-`deprecated`, Pfad `klickdummy/archive/` (siehe §Frontmatter-Konvention). **B Transition:** ab erstem Screen mit Impl-Route greift I3 je Screen. **C mit Zielsystem:** Doppelquelle endet bei **`min(prod-Release, Parity-grün + N Tagen)`** (N Default **30 d**, repo-tunbar) — schließt das „ewig auf Staging"-Leck (F4). Staging ist erlaubter Doppelquell-Raum *innerhalb* der TTL. | `make -C <repo> klickdummy-i3` (Phase B/C); `platform/scripts/checks/adr_sunset.sh` (Phase A, nightly — öffnet Issue bei passierter Frist) |
| **I4 Namensraum** | Klickdummy-ADRs tragen reserviertes Titel-Präfix; Cross-Repo-Refs **nur** `repo:ADR-NNN` (inkl. `conforms_to: platform:ADR-211`). Drift-Schutz (vgl. Drift-Memory `klickdummy-adr180-collision`). | `platform/scripts/checks/adr_cross_repo_refs.sh` (plattformseitig, kein repo-Make-Target — generischer ADR-Lint) |

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

**Erlaubte Pfade entlang Vertrauens-Perimeter:**

| Pfad | Was | Status in Rev 12 |
|---|---|---|
| **A · Bridge** | Widget → Endpoint → Issue → Coding-Agent → Diff-PR | **Erlaubt + Default.** Auditierbar, kein LLM-Call aus Browser. |
| **B · Direkt-LLM** | Widget → Endpoint → LLM → Diff-PR | **Erlaubt nach plattformweiter A-Adoption** (mindestens 2 Repos mit Pfad A produktiv) **und** Existenz eines plattformseitigen LLM-Audit-Frameworks (Logging, Rate-Limit, CSRF, Spam-Schutz, Cost-Cap). „Repo-lokale A-Erfahrung" reicht nicht — B ist plattformweite Reife-Stufe. |
| **C · Browser-LLM** | Widget → LLM mit Code-Schreib-Rechten aus Browser | **Verboten.** Außerhalb des Rahmens dieses ADR. Aktivierung erfordert **neuen ADR** (mit Audit-/Threat-Model). „Nicht umgesetzt" ist ungenügend — der Pfad ist nicht prospektiv-erlaubt. |

**Aktivierungs-Definition** (eindeutig, prüfbar):

Ein Repo gilt als „Co-Creation-Loop aktiviert" **genau dann, wenn alle drei
Bedingungen erfüllt sind:**

1. Spec enthält Block `feedback_loop:` mit deklariertem Payload-Schema und
   mindestens einem aktivierten Submit-Mode.
2. Widget ist in der Klickdummy-Render-Quelle vorhanden UND opt-in
   (Default: aus; z. B. `?feedback=on` oder Build-Flag).
3. Provenance-Log `feedback-log.md` existiert neben der Spec.
4. **Pfad-Deklaration**: `feedback_loop.path: A | B` (Pfad C ist verboten,
   siehe Pfade-Tabelle). Verhindert Vacuous-Pass „aktiviert ohne Pfad".
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

**Migrations-Status — Snapshot beim Schreiben dieses Rev (2026-05-20).
Live-Quelle: S11-Inventur-Skript-Output (siehe Code oben):**

- meiki-hub:ADR-020 / ADR-021 / ADR-026 — ✅ migriert (meiki-hub#23)
- writing-hub:ADR-180 — ⏳ noch zu migrieren
- risk-hub:ADR-046 — ⏳ noch zu migrieren
- pptx-hub / dev-hub — ⏳ noch zu migrieren

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

## Bezug

- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 · meiki-hub:ADR-026 (Co-Creation-Loop + Requirements-Bridge — Rev-12-Empiriebasis) — Mapping auf Rev-11-Patterns in §Auswahlhilfe
- Followups `adr-211-followup` SF1–SF11 (Adoption-Scoreboard, **nicht status-gatend**) — S7/S8 durch Rev 11, S9/S10/S11 durch Rev 12
- Closes-on-acceptance: **#228** (sunset_after-Frontmatter, F10) und **#229** (4-Pattern-Taxonomie, F9). #255 SF3-AC muss vor Bau an pattern-spezifischen Prod-Guard angepasst werden (F11, offen). **F12 geschlossen durch Rev 12** (§Migration).
- meiki-hub PR #23 (`feat/klickdummy-feedback-loop-poc`, 7 Iterationen) — Empiriequelle für Rev 12; insbesondere `docs/01-architektur/mockups/fristenmanagement-klickdummy/feedback-log.md` (Provenance + Iteration-Typologie).
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (meiki-hub-Auto-Memory, `drift: true`)
- Policy `adr-threshold.md` (Selbsttest — Rev 12 begründet Erweiterung statt neuem ADR)
