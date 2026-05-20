# Policy: Klickdummy

**Trigger words:** klickdummy, mockup, prototyp, parity-test, demo-render, `?demo=`

## Rule

Ein Klickdummy ist ein **Renderer einer maschinenlesbaren Anforderungs-Spec**
zur frühen Validierung — nicht selbst die Quelle und kein Produktionscode.
Volle Begründung: `platform/docs/adr/ADR-211` (Rev 9, `status: accepted`).

## Drei Invarianten (jeder Klickdummy, jedes Repo, ansatz-offen)

- **I1 Spec-first (bidirektionale Coverage)** — versioniertes,
  maschinenlesbares Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter);
  Markdown-Bullets zählen nicht. `klickdummy-i1` asserts **Spec ↔ Route
  Coverage**: jede Impl-Route hat einen Spec-Eintrag *und* jeder Spec-Eintrag
  eine Route/Screen — kein „Datei existiert & rendert".
- **I2 Prod-Sicherheit (zwei Schichten, plattform-extern bindend)** — genau
  **eine** Klasse explizit deklarieren: *Mock-Prototyp* (kein Backend,
  Systemgrenzen als Target-Mock) ODER *Demo-Render* (env-gegated, in Prod
  nicht erreichbar). „Keine Klasse deklariert" ist Verstoß (kein vacuous
  pass). Verifikation:
  (a) repo-definierter `make -C <repo> klickdummy-i2` (Selbstaussage);
  (b) **plattform-externer Prod-Probe** `klickdummy_prod_guard.sh` gegen die
  Registry-Prod-URL: `?demo=<state>` live ⇒ **404/disabled erwartet**.
  **(b) ist das bindende Cross-Repo-Signal** — Behauptung wird adversarial
  extern getestet, nicht dem Repo-Selbstcheck geglaubt.
- **I3 Off-Ramp mit TTL** — Parity-grün pro Screen ⇒ statische Quelle
  entfernt, sobald **`min(prod-Release, Parity-grün + N Tagen)`** eintritt
  (N Default **30 d**, repo-tunbar). Staging ist erlaubter Doppelquell-Raum
  *innerhalb* der TTL — verhindert das „Static-Leichen im Dauer-Staging"-Leck.

> **Verschoben (nicht mehr hier):** das Cross-Repo-Ref-Format
> `repo:ADR-NNN` (vormals „I4") gehört in **`ADR-207`**
> (Cross-Repo-Ingest-/Doku-Konvention) — generische ADR-Hygiene, kein
> klickdummy-spezifischer Belang.

## Wann gilt das

Sobald ein Repo einen `klickdummy/`-Pfad oder einen `?demo=`-Render hat. Das
Repo braucht ein lokales Klickdummy-ADR mit `conforms_to: platform:ADR-211`
und `make klickdummy-{i1,i2,i3}`-Targets. Kein ADR/Target ⇒ Plattform-CI rot
(`platform/scripts/checks/klickdummy_registry.sh`).

## Wann NICHT

- Wegwerf-Skizze ohne `klickdummy/`-Pfad, ohne Zielsystem, einmalig im Workshop
  gezeigt und sofort verworfen → keine I1–I3-Pflicht.
- Echte App-UI ohne `?demo=`-Sonderzustand → normaler Code, kein Klickdummy.

## Entscheidung ≠ Rollout (Rev-9-Korrektur)

ADR-211 ist **`accepted`** (Decider-Ratifizierung des Entscheids I1–I3 +
Enforcement-Pfad). Der Rollout-Fortschritt lebt als **Adoption-Scoreboard**
in `adr-211-followup` (SF1–SF6) — er **gatet den ADR-Status nicht** und ist
kein Aktivierungs-Vorbehalt dieser Policy. Eine akzeptierte Entscheidung ist
stabil, nicht eine Funktion fortlaufender Flotten-Drift.

## Mechanik (SSoT)

Diese Datei ist die versionierte SSoT. `~/.claude/policies/klickdummy.md` ist
ein **Symlink** in einen gepinnten platform-Worktree (kein Kopier-Sync) —
`inject_policies.py`/`claude-policy` lesen den Symlink unverändert. Änderung
nur per **platform-PR + Changelog-Bump**; der gepinnte Worktree zieht beim
nächsten Refresh nach.

## Changelog

- 2026-05-19: Initial. Aus ADR-211 (Rev 4, drei Adversarial-Pässe) abgeleitet.
- 2026-05-20: Rev-9-Angleichung. **Drei** (nicht vier) Invarianten — I4
  (Cross-Repo-Ref-Format) nach ADR-207 ausgelagert. I1 bidirektionale
  Spec↔Route-Coverage. I2 erweitert um plattform-externen `klickdummy_prod_guard.sh`
  als bindendes Cross-Repo-Signal (Sicherheitsinvariante adversarial
  verifizierbar). I3 Off-Ramp-TTL `min(prod-Release, Parity-grün+N d)`,
  Default 30 d. „Entscheidung ≠ Rollout"-Klarstellung; ADR-211 ist accepted,
  Scoreboard läuft separat.
