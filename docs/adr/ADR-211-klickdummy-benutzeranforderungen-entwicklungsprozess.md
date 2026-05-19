---
id: ADR-211
title: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)
status: proposed
date: 2026-05-19
deciders: [achim]
informed: [all-repos]
domains: [ux, requirements, process, security, drift-prevention]
supersedes: []
amends: []
depends_on: [ADR-207]
tags: [klickdummy, mockup, requirements-spec, parity-test, prod-guard, convention]
scope:
  include_paths:
    - "policies/klickdummy.md"
    - "scripts/checks/klickdummy_*.sh"
    - "**/klickdummy/**"
    - "**/docs/adr/ADR-*.md"
---

# ADR-211: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)

- **Status:** proposed *(→ accepted erst wenn Confirmation C1–C6 grün; aktuell 0/6, siehe Baseline)*
- **Datum:** 2026-05-19
- **Entscheider:** Achim Dehnert
- **Verwandt:** ADR-207, risk-hub:ADR-046, writing-hub:ADR-180, meiki-hub:ADR-020
- **Adversarial reviews:** drei Cascade-Pässe (Rev 2/3/4), siehe Frontmatter `review_history`

## Zusammenfassung

Mehrere Repos bauen „Klickdummies". Der naheliegende Rahmen — „jeder macht
sein Ding, wir teilen Vokabular" — wäre **keine Entscheidung** (per
`adr-threshold.md` reichte eine Konvention). Dieses ADR trifft drei harte,
erzwingbare Entscheidungen, weil jede einen realen Schaden verhindert:

1. **Spec-zentriert statt Renderer-zentriert.** Dauerhaftes Artefakt ist die
   **maschinenlesbare Anforderungs-Spec**, nicht ihre Darstellung. Ein
   Klickdummy *rendert* sie; ein Parity-Test ist das Konformitäts-Gate.
2. **Mock-Prototyp ≠ Demo-Render — harter Prod-Guard.** Ein Demo-Render der
   *echten* App (`?demo=<state>`) ist eine **Prod-Sicherheitsfläche**.
3. **Parity-grün ist die Off-Ramp.** Parity-grün pro Screen ⇒ statische Quelle
   mechanisch entfernt — beendet das „Static-Leichen"-Muster.

Implementierungs-Stack bleibt repo-lokal; die Invarianten sind ansatz-offen.

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
| **I1 Spec-first** | Maschinenlesbares, versioniertes Spec-Artefakt (YAML/JSON/strukturiertes Frontmatter); Markdown-Bullets zählen nicht. Klickdummy rendert es, ist nicht die Quelle. | `make -C <repo> klickdummy-i1` (Exit-Code), CI-verifiziert — keine Frontmatter-Behauptung |
| **I2 Prod-Sicherheit** | Genau eine Klasse je Klickdummy, **explizit deklariert**: **Mock-Prototyp** (kein Backend; Systemgrenzen als Target-Mock) ODER **Demo-Render** (env-gegated; in Prod nicht erreichbar). „Keine Klasse deklariert" ist I2-Verstoß (kein vacuous pass). | repo-definierter Check `make -C <repo> klickdummy-i2`; Plattform prüft nur, **dass** er existiert und Exit 0 liefert (R3 — kein plattformweiter String-Grep) |
| **I3 Lebenszyklus** | **A ohne Zielsystem:** endet bei dok. Fachabteilungs-Review → ADR `accepted-frozen`/`superseded`, Spec eingefroren, Pfad `klickdummy/archive/`. **B Transition:** ab erstem Screen mit Impl-Route greift I3 je Screen. **C mit Zielsystem:** Parity-grün/Screen ⇒ statische Quelle weg. **Staging ist ausdrücklich erlaubter Doppelquell-Raum** (dort läuft der Parity-Vergleich); verbotene Grenze = **prod-Deploy** (Tag/Container-Push nach prod), nicht staging (R4). | `make -C <repo> klickdummy-i3`: assert für jeden Screen mit Impl-Route + grünem Parity + **prod-Release** ⇒ statische Quelle abwesend |
| **I4 Namensraum** | Repo-Klickdummy-ADR mit reserviertem Titel-Präfix; Cross-Repo-Refs **nur** `repo:ADR-NNN` (inkl. des `conforms_to:`-Feldes → `conforms_to: platform:ADR-211`). | `platform/scripts/checks/adr_cross_repo_refs.sh` |

**Auswahlhilfe (illustrativ):** Konzeptphase ohne Backend → Mock-Prototyp
(meiki-hub:ADR-020). App-Repo mit Zielsystem → Demo-Render + Parity
(writing-hub:ADR-180). UI-Spec primär → Spec-Driven (risk-hub:ADR-046).
KI-generiert/Figma-as-Spec zulässig, sofern I1–I4 erfüllt.

### Was repo-lokal bleibt
Tech-Stack, Schema, UI-Bausteine, Teststack. risk-hub:ADR-046 behält seine
Repo-Lokalität; dieses ADR ersetzt keine Implementierungs-ADR.

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
   Kopier-Sync.** Der gepinnte Worktree zieht beim nächsten Refresh nach; C6
   erkennt einen *stale gepinnten Worktree* (Policy in der Quelle, aber
   Pinned-Stand veraltet).
4. **Adoption:** `onboard-repo`-Skill prüft I1–I4 + ADR-Header + `make klickdummy-{i1,i2,i3,i4}`.
5. **Verifikation:** `platform/scripts/checks/klickdummy_registry.sh` über `registry/repos.yaml`.

## Confirmation (executable Acceptance-Gate)

> **Baseline 2026-05-19: 0/6 grün** — keiner der Checks/Targets/Policies
> existiert noch (R2). Confirmation ist das **Acceptance-Gate**: `status`
> bleibt `proposed`, bis C1–C6 grün sind (R6). Jeder offene Punkt ist ein
> `adr-211-followup`-Issue (SF1–SF6).

```bash
# C1 Registry-Konformität (SF1)
platform/scripts/checks/klickdummy_registry.sh
#   GELTUNGSBEREICH: nur in registry/repos.yaml gelistete Repos (= achimdehnert-
#   Plattform-Repos). Repos anderer Orgs (z. B. meiki-lra:meiki-hub) sind NICHT
#   im Registry und werden von C1 bewusst NICHT abgedeckt — ihre Konformität
#   verantwortet die jeweilige Repo-CI + die Implementierungsliste in diesem ADR.
#   Konformität = Repo-ADR-Frontmatter `conforms_to: platform:ADR-211`
#   (I4-qualifiziert; bare `ADR-211` wird übergangsweise akzeptiert).

# C2 I1 Spec==Render je Repo (SF2)
make -C <repo> klickdummy-i1

# C3 I2 Prod-Guard — REPO-definiert, nicht plattform-Grep (SF3)
make -C <repo> klickdummy-i2
#   Mock-Prototyp-Repo: assert kein ?demo=-Pfad existiert
#   Demo-Render-Repo:   Prod-Smoke + Middleware-Unit-Test, ?demo in PROD → 404/disabled

# C4 I3 Off-Ramp, Grenze = prod-Release (SF4)
make -C <repo> klickdummy-i3

# C5 I4 Cross-Repo-Ref-Format (SF5)
platform/scripts/checks/adr_cross_repo_refs.sh   # regex ^[a-z][a-z0-9-]+:ADR-\d{3}$

# C6 Policy-SSoT existiert UND gepinnter Worktree nicht stale (SF6)
platform/scripts/checks/klickdummy_policy_sync.sh
#   FAIL wenn SSoT fehlt ODER Injektions-Ziel fehlt/weicht ab (staler Pinned).
#   SKIP (exit 0) ohne ~/.claude/policies (off-machine CI); --strict ⇒ FAIL.
#   Erkennt 'Policy gemerged/geändert, Pinned-Refresh fehlt'.
```

## Konsequenzen

**Positiv:** Spec-first beendet Renderer-Wildwuchs; Off-Ramp verhindert
Static-Leichen; Demo-Render-Prod-Guard schließt eine Sicherheitslücke;
Enforcement nutzt den bestehenden, dokumentierten Pinned-Worktree-Symlink
(policies/README.md) statt einen Parallelpfad zu erfinden.
**Negativ:** je Repo einmaliger Aufwand für `make klickdummy-{i1..i4}`;
6 Followup-Artefakte (SF1–SF6) sind Voraussetzung für Acceptance.
**Neutral:** bestehende Klickdummies funktional unverändert.

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Anforderungs-Spec** | Versioniertes, maschinenlesbares Quell-Artefakt (YAML/JSON/Frontmatter); Markdown-Bullets zählen nicht |
| **Klickdummy** | Oberbegriff: *Renderer* der Spec zur frühen Validierung |
| **Mock-Prototyp** | Wegwerf-Renderer ohne Backend (Target-Mock-Systemgrenzen) |
| **Demo-Render** | Env-gegateter Zustand der echten App (`?demo=`) — Prod-Sicherheitsfläche |
| **Parity-Test** | Renderer↔Implementierung-Äquivalenztest — Gate **und** Off-Ramp |
| **Off-Ramp** | Parity-grün ⇒ mechanische Entfernung der statischen Quelle (Grenze: prod-Release) |

## Acceptance-Trigger

`status` bleibt **proposed**, bis Confirmation **C1–C6 grün** sind (siehe
Abschnitt Confirmation, aktuell Baseline). Erst dann → `accepted`. (Im
Frontmatter bewusst kein Custom-Feld — das ADR-Schema lässt nur die
Standard-Properties zu; Acceptance-Logik gehört in den Body.)

## Revisionshistorie

Drei Cascade-Adversarial-Pässe + Schema-/YAML-Härtung:

- **Rev 1** — initial proposal
- **Rev 2** (bf7c4d6) — Spec-first, Prod-Guard, Parity-Off-Ramp
- **Rev 3** (47ff4f9) — Enforcement in-repo, I1/Confirmation executable
- **Rev 4** — R4 prod-Grenze, R3 repo-definierte Checks, R2 Baseline 0/N, R5 Drift belegt, R6 Acceptance-Trigger
- **Rev 5** — Mechanik-Korrektur: `~/.claude/policies` ist Symlink in gepinnten platform-Worktree (kein Kopier-Sync)
- **Rev 6** — C1-Geltungsbereich präzisiert (nur registry-Repos); `conforms_to` I4-qualifiziert; SF1-Regex + SF5
- **Rev 7** — C6 auf Script `klickdummy_policy_sync.sh` umgestellt; SF6
- **Rev 8** — Frontmatter schema-konform: `review_history`/`acceptance_trigger` aus Frontmatter in den Body verschoben (iil-adrfw `validate` lehnt Additional Properties ab; vorher zudem YAML-ScannerError durch `date:`-Mapping-Fehlinterpretation)

## Bezug

- ADR-207 — Cross-Repo-Ingest-/Doku-Konvention
- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 (Implementierungen)
- Followups `adr-211-followup` SF1–SF6 (Confirmation-Baseline 0/6)
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (meiki-hub-Auto-Memory, `drift: true`)
- Policy `adr-threshold.md` (Selbsttest)
