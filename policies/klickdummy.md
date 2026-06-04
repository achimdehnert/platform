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
  **(b) ist das *vorgesehene* bindende Cross-Repo-Signal** — Behauptung wird
  adversarial extern getestet, nicht dem Repo-Selbstcheck geglaubt.
  **Status 2026-06-04 (wortgleich zu ADR-211 I2(b)/Rev 20 — SSoT):**
  `klickdummy_prod_guard.sh` (F11) ist derzeit **unimplementiert/dormant**
  (ADR-211 Rev 20, #255 geparkt); bis zu seiner Implementierung ist
  ausschließlich die repo-lokale Pattern-Deklaration (a) aktiv und es existiert
  **kein bindendes Cross-Repo-Prod-Probe-Signal**. Übergangs-Risiko: die externe
  Falsifikation fehlt für die Nicht-`mock`-Patterns bis F11 gebaut ist — I2
  stützt sich solange auf Selbstdeklaration.

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
- 2026-05-20: Rev-12-Angleichung (Empirie meiki-hub PR #23). **Erweiterung, kein
  neuer Entscheid.** I1 erhält zwei *optionale* Erweiterungen (siehe ADR-211
  §Co-Creation-Loop, §Requirements-Bridge). **F12 geschlossen** via
  **Soft-Migrate**: `check_i2.py` akzeptiert Rev-≤10-Werte
  (`mock-prototyp`/`demo-render`) übergangsweise mit ⚠-Warning + Mapping
  (`{mock-prototyp→mock, demo-render→spec-demo}`); Strict-Mode wird via
  Scoreboard-Item S11 nach Cross-Repo-Migration aktiviert. Iteration-
  Typologie erweitert (stakeholder- + compliance-getriggert).
- 2026-05-20: Rev-13-Angleichung (Decider-Pivot). **Erweiterung.** Initialer
  ADR-214-Draft (Distribution-Service) als advocatus diabolus zurückgezogen;
  §Distribution wird ADR-211-§ (pip-Paket `iil-klickdummy` mit Schemas/Skripten/
  Widget). §Co-Creation Pfade A neu (A-light / A-User-Direct via GitHub-API /
  A-Agent); zentraler Endpoint gestrichen. Plugin-Hooks im Widget.
- 2026-05-21: Rev-14-Angleichung (Multi-Klickdummy-Browser + public PyPI).
  **Erweiterung.** `iil-klickdummy` v1.1 mit `registry.py` + `klickdummy-browser`
  (Versions-/Repo-Browser). public PyPI (`pip install iil-klickdummy`) wird
  Default, Git-URL Fallback; Trusted Publishing (OIDC).
- 2026-05-21: Rev-15-Angleichung (Repo-Extraktion). **Kein Invarianten-Change.**
  `packages/iil-klickdummy` → `iilgmbh/iil-klickdummy` extrahiert (Historie
  erhalten). Trennung festgeklopft: ADR-211 (Konvention) bleibt
  achimdehnert/platform; `iilgmbh:iil-klickdummy:ADR-001` ist Implementations-ADR;
  Schwester-Impls via `sister_of`.
- 2026-05-25/28: Rev-16-Angleichung (zwei Amends). **Erweiterung.** Optionale §-
  Erweiterungen von I1: **§Acceptance-Marker** (`spec_signed`/`ui_walked`, append-
  only mit Evidence `by`+`date`+`ref`) und **§UC-Coverage** (UC↔Screen-Lint,
  Cross-Repo-Namespace `<repo>:UC-NNN`); offene F13–F16. Dazu **§KD-first-Gate**
  (opt-in; NEUE User-facing Features erst als KD), Scoreboard +S12.
- 2026-05-29: Rev-17-Angleichung (Daten-Treue der Anzeige). **Klarstellung.**
  Im Klickdummy ausgegebene Zahlen sind **berechnet, nicht literal** (Mock-Daten
  synthetisch, Berechnung echt); Cross-Screen-Aggregate aus **einer** Quelle.
  Enforcement = Review-Gate. An I1 angehängt; kein I5.
- 2026-05-31: Rev-18-Angleichung (Executable-Parity-Bridge). **Erweiterung, kein
  neuer Entscheid.** Optionale §-Erweiterung von I1: `parity_acceptance.assert`
  → forward-only deterministischer Generator (`klickdummy-gen-e2e`) erzeugt eine
  Playwright/pytest-Suite, die Renderer #1 (Klickdummy) und #2 (echte App) per
  `SPEC_RENDERER_BASE_URL` gegen dieselbe Assertion prüft — parity-grün gegen #2
  = I3-Off-Ramp-Gate. **I3 gehärtet:** Off-Ramp nur mit Renderer-#1-Entfernung
  (`off_ramp_status: removed`) + negativem Reachability-Beleg; „max. eine lebende
  UI-Impl pro Spec-Screen"; F4 nur für inventarisierte Routen geschlossen (F20
  offen). Drift-Gate `klickdummy-parity-drift` (Reuse S10). Scoreboard +S13.
  Empirie: iil-klickdummy v1.6.0 + zwei externe Review-Runden. (Hinweis: dieser
  Changelog lag bei Rev-12 — Rev 13–17 betrafen die Kern-Invarianten nicht.)
- 2026-06-04: Rev-20-Angleichung (I2(b)-Ehrlichkeit). **Erweiterung, kein
  Entscheid-Widerruf.** `klickdummy_prod_guard.sh` (F11) ist als
  **unimplementiert/dormant** markiert (ADR-211 Rev 20, #255 geparkt) — bis Bau
  bindet faktisch nur die repo-lokale Pattern-Deklaration (a); kein bindendes
  Cross-Repo-Prod-Probe-Signal. Empirie 2026-06-04: Parity-Mechanismus belegt
  (A1), aber 0 reale Renderer #2 plattformweit. Hält die Policy wortgleich zu
  ADR-211 I2(b)/ADR-216 (SSoT). Die opt-in-Executable-Parity-Bridge ist im
  Scoreboard S13 `dormant` (review_by 2026-12-04).
