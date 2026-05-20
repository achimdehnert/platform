# Policy: Klickdummy

**Trigger words:** klickdummy, mockup, prototyp, mock-prototyp, stub-demo, story, spec-demo, parity-test, demo-render, `?demo=`, sunset_after

## Rule

Ein Klickdummy ist ein **Renderer einer maschinenlesbaren Anforderungs-Spec**
zur frühen Validierung — nicht selbst die Quelle und kein Produktionscode.
Volle Begründung: `platform/docs/adr/ADR-211` (Rev 11, `status: accepted`).

## Vier Invarianten (jeder Klickdummy, jedes Repo, ansatz-offen)

- **I1 Spec-first (bidirektionale Coverage)** — versioniertes,
  maschinenlesbares Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter);
  Markdown-Bullets zählen nicht. `klickdummy-i1` asserts **Spec ↔ Route
  Coverage**: jede Impl-Route hat einen Spec-Eintrag *und* jeder Spec-Eintrag
  eine Route/Screen — kein „Datei existiert & rendert".

- **I2 Prod-Sicherheit (4-Pattern, plattform-extern bindend)** — genau
  **ein** Pattern explizit deklarieren entlang *Datenquelle × Code-Pfad-
  Identität*:
  - **`mock`** — separater Wegwerf-Code-Pfad, leere/feste Stubs. Nicht in
    Prod-Deploy. I2-Externprobe **N/A**.
  - **`stub-demo`** — realer Code-Pfad, synthetische Daten an dedizierter
    Demo-Route. I2-Externprobe: deklarierte Demo-Route ⇒ **404**.
  - **`story`** — realer Code-Pfad, isolierter Component-Catalog
    (z. B. Storybook). I2-Externprobe: Catalog-Route ⇒ **404**.
  - **`spec-demo`** — realer Code-Pfad, env-gegateter Zustand via Flag
    (`?demo=<state>`). I2-Externprobe: `?demo=` ⇒ **404/disabled**.

  „Kein Pattern deklariert" ist Verstoß (kein vacuous pass). Verifikation:
  (a) repo-definierter `make -C <repo> klickdummy-i2` (Selbstaussage);
  (b) **plattform-externer Prod-Probe** `klickdummy_prod_guard.sh` mit
  *pattern-spezifischem* Verhalten (siehe obige Probe-Definitionen).
  **(b) ist das bindende Cross-Repo-Signal** — Behauptung wird adversarial
  extern getestet, nicht dem Repo-Selbstcheck geglaubt.

- **I3 Off-Ramp mit TTL + Sunset (Rev 11)** —
  - **Phase A (ohne Zielsystem):** Pflicht-Frontmatter `sunset_after`-Datum
    in der Repo-Klickdummy-ADR (siehe §Frontmatter-Konvention unten).
    Auto-`deprecated` nach Frist ohne PR-Extension.
  - **Phase B (Transition):** ab erstem Screen mit Impl-Route greift I3 je
    Screen.
  - **Phase C (mit Zielsystem):** Doppelquelle endet bei
    **`min(prod-Release, Parity-grün + N Tagen)`** (N Default **30 d**,
    repo-tunbar). Staging ist erlaubter Doppelquell-Raum *innerhalb* der TTL.

- **I4 Namensraum** — Klickdummy-ADRs tragen reserviertes Titel-Präfix;
  Cross-Repo-Refs **nur** `repo:ADR-NNN` (inkl. `conforms_to: platform:ADR-211`).
  Drift-Schutz (Drift-Memory `klickdummy-adr180-collision`). Plattformseitiger
  Lint via `adr_cross_repo_refs.sh`, kein repo-Make-Target.

## Frontmatter-Konvention (Rev 11)

Repo-lokale ADRs mit `tags: [klickdummy]` MÜSSEN folgende Frontmatter:

```yaml
class: mock | stub-demo | story | spec-demo
sunset_after: 2026-12-31                       # ISO-Datum; Default ADR-Datum + 12 Monate
extension_review_required: true                # Optional (Default: true für mock, false sonst)
```

**Ausgenommen:** ADR-211 selbst (Platform-Policy-ADR, kein Sunset; Geltung
via `supersedes`/`amends`). Nach `sunset_after` ohne Extension: ADR-Status
auto-`deprecated`, Klickdummy-Pfad → `klickdummy/archive/`. Enforcement:
`adr_sunset.sh` (nightly).

## Wann gilt das

Sobald ein Repo einen `klickdummy/`-Pfad oder einen `?demo=`-Render hat. Das
Repo braucht ein lokales Klickdummy-ADR mit `conforms_to: platform:ADR-211`
und `make klickdummy-{i1,i2,i3}`-Targets. Kein ADR/Target ⇒ Plattform-CI rot
(`platform/scripts/checks/klickdummy_registry.sh`).

## Wann NICHT

- Wegwerf-Skizze ohne `klickdummy/`-Pfad, ohne Zielsystem, einmalig im Workshop
  gezeigt und sofort verworfen → keine I1–I4-Pflicht.
- Echte App-UI ohne `?demo=`-Sonderzustand → normaler Code, kein Klickdummy.

## Entscheidung ≠ Rollout (Rev 9, unverändert)

ADR-211 ist **`accepted`**. Der Rollout-Fortschritt lebt als
**Adoption-Scoreboard** in `adr-211-followup` (SF1–SF8 seit Rev 11) — er
**gatet den ADR-Status nicht** und ist kein Aktivierungs-Vorbehalt dieser
Policy.

## Mechanik (SSoT)

Diese Datei ist die versionierte SSoT. `~/.claude/policies/klickdummy.md` ist
ein **Symlink** in einen gepinnten platform-Worktree (kein Kopier-Sync) —
`inject_policies.py`/`claude-policy` lesen den Symlink unverändert. Änderung
nur per **platform-PR + Changelog-Bump**; der gepinnte Worktree zieht beim
nächsten Refresh nach. Doppel-Stale-Check (Rev 11/#254): das Sync-Script
prüft zusätzlich gegen `origin/main`.

## Changelog

- 2026-05-19: Initial. Aus ADR-211 (Rev 4, drei Adversarial-Pässe) abgeleitet.
- 2026-05-20: Rev-9-Angleichung. „Drei Invarianten" — I4 nach ADR-207
  ausgelagert. I1 bidirektional. I2 + plattform-externer Prod-Probe.
  I3 Off-Ramp-TTL. „Entscheidung ≠ Rollout".
- 2026-05-20: Rev-10-Angleichung (F5-Rollback). I4 zurück in ADR-211
  (klickdummy-skopiert; ADR-207 ist Doku-Strategie, nicht Cross-Repo-ADR-
  Namensraum). „Vier Invarianten" zurück.
- 2026-05-20: Rev-11-Angleichung. I2 von 2 → **4 Patterns**
  (`mock`/`stub-demo`/`story`/`spec-demo`) entlang Datenquelle × Code-Pfad-
  Identität, distinkte Externprobe je Pattern. I3 Phase-A mit Pflicht-
  `sunset_after`-Frontmatter und Auto-`deprecated`. Neue Frontmatter-Konvention.
