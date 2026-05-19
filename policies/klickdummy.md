# Policy: Klickdummy

**Trigger words:** klickdummy, mockup, prototyp, parity-test, demo-render, `?demo=`

## Rule

Ein Klickdummy ist ein **Renderer einer maschinenlesbaren Anforderungs-Spec**
zur frühen Validierung — nicht selbst die Quelle und kein Produktionscode.
Volle Begründung + Acceptance-Gate: `platform/docs/adr/ADR-211`.

## Vier Invarianten (jeder Klickdummy, jedes Repo, ansatz-offen)

- **I1 Spec-first** — versioniertes, maschinenlesbares Spec-Artefakt
  (YAML/JSON/strukturiertes Frontmatter); Markdown-Bullets zählen nicht.
  Konformität via `make -C <repo> klickdummy-i1` (Exit-Code), CI-verifiziert.
- **I2 Prod-Sicherheit** — genau **eine** Klasse explizit deklarieren:
  *Mock-Prototyp* (kein Backend, Systemgrenzen als Target-Mock) ODER
  *Demo-Render* (env-gegated, in Prod nicht erreichbar). Keine Klasse
  deklariert = Verstoß (kein vacuous pass). Check ist **repo-definiert**
  (`make klickdummy-i2`), kein plattformweiter String-Grep.
- **I3 Off-Ramp** — Parity-grün pro Screen ⇒ statische Quelle entfernt.
  Verbotene Doppelquell-Grenze = **prod-Release**; Staging ist erlaubter
  Doppelquell-Raum (dort läuft der Parity-Vergleich).
- **I4 Namensraum** — Cross-Repo-Referenzen **nur** als `repo:ADR-NNN`.
  Unqualifiziertes „ADR-NNN"/„klickdummy" ist repo-mehrdeutig → erst Repo
  verifizieren (Drift-Lehre 2026-05-19).

## Wann gilt das

Sobald ein Repo einen `klickdummy/`-Pfad oder einen `?demo=`-Render hat. Das
Repo braucht ein lokales Klickdummy-ADR mit `conforms_to: ADR-211` und
`make klickdummy-{i1,i2,i3,i4}`-Targets. Kein ADR/Target ⇒ Plattform-CI rot
(`platform/scripts/checks/klickdummy_registry.sh`).

## Wann NICHT

- Wegwerf-Skizze ohne `klickdummy/`-Pfad, ohne Zielsystem, einmalig im Workshop
  gezeigt und sofort verworfen → keine I1–I4-Pflicht.
- Echte App-UI ohne `?demo=`-Sonderzustand → normaler Code, kein Klickdummy.

## Mechanik (SSoT)

Diese Datei ist die versionierte SSoT. `~/.claude/policies/klickdummy.md` ist
ein **Symlink** in einen gepinnten platform-Worktree (kein Kopier-Sync) —
`inject_policies.py`/`claude-policy` lesen den Symlink unverändert. Änderung
nur per **platform-PR + Changelog-Bump**; der gepinnte Worktree zieht beim
nächsten Refresh nach.

## Changelog

- 2026-05-19: Initial. Aus ADR-211 (Rev 4, drei Adversarial-Pässe) abgeleitet.
  Folge-Artefakte SF1–SF6 (`adr-211-followup`) noch offen — bis dahin ist
  ADR-211 `proposed`, Confirmation 0/6.
