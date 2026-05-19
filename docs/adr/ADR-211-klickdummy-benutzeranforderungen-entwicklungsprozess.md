---
id: ADR-211
title: Spec-zentrierte Klickdummies — Anforderungsartefakt, Prod-Sicherheit und Parity-Off-Ramp (Cross-Repo)
status: proposed
date: 2026-05-19
deciders: [achim]
informed: [all-repos]
review_history:
  - 2026-05-19: Rev 1 — initial proposal
  - 2026-05-19: Rev 2 — adversarial review (commit bf7c4d6) — Spec-first, Prod-Guard, Parity-Off-Ramp
  - 2026-05-19: Rev 3 — second adversarial pass (commit 47ff4f9) — enforcement in-repo, I1/Confirmation executable
  - 2026-05-19: Rev 4 — third adversarial pass — R4 prod-Grenze, R3 repo-definierte Checks, R2 Baseline 0/N, R5 Drift belegt, R6 ADR-Acceptance-Trigger
  - 2026-05-19: Rev 5 — Mechanik-Korrektur: ~/.claude/policies ist SYMLINK in gepinnten platform-Worktree (kein Kopier-Sync); Update nur via platform-PR + Changelog (Quelle: policies/README.md)
acceptance_trigger: "status → accepted erst wenn C1–C6 grün (siehe Confirmation); bis dahin proposed"
domains: [ux, requirements, process, security, drift-prevention]
supersedes: []
amends: []
depends_on: [ADR-207]
tags: [klickdummy, mockup, requirements-spec, parity-test, prod-guard, convention]
scope:
  governed_artifacts:
    - "platform/policies/klickdummy.md (versionierte QUELLE der operativen Regel)"
    - "~/.claude/policies/klickdummy.md (Symlink in gepinnten platform-Worktree; liest die Quelle, kein Kopier-Sync)"
    - "meiki-hub:ADR-020 / risk-hub:ADR-046 / writing-hub:ADR-180 (Implementierungen)"
    - "onboard-repo Skill — Adoptionspunkt"
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
| **I4 Namensraum** | Repo-Klickdummy-ADR mit reserviertem Titel-Präfix; Cross-Repo-Refs nur `repo:ADR-NNN`. | `platform/scripts/checks/adr_cross_repo_refs.sh` |

**Auswahlhilfe (illustrativ):** Konzeptphase ohne Backend → Mock-Prototyp
(meiki-hub ADR-020). App-Repo mit Zielsystem → Demo-Render + Parity
(writing-hub ADR-180). UI-Spec primär → Spec-Driven (risk-hub ADR-046).
KI-generiert/Figma-as-Spec zulässig, sofern I1–I4 erfüllt.

### Was repo-lokal bleibt
Tech-Stack, Schema, UI-Bausteine, Teststack. risk-hub ADR-046 behält seine
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
#   alle Repos mit klickdummy/-Pfad in registry/repos.yaml haben ADR conforms_to: ADR-211

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

# C6 Policy-Quelle existiert UND gepinnter Worktree nicht stale (SF6)
test -f platform/policies/klickdummy.md \
  && diff -q platform/policies/klickdummy.md ~/.claude/policies/klickdummy.md
#   exit 0 nur wenn Quelle vorhanden UND der gepinnte Worktree (Symlink-Ziel)
#   den aktuellen Stand zeigt — erkennt 'Policy gemerged, Pinned-Refresh fehlt'
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

## Bezug

- ADR-207 — Cross-Repo-Ingest-/Doku-Konvention
- risk-hub:ADR-046 · writing-hub:ADR-180 · meiki-hub:ADR-020 (Implementierungen)
- Followups `adr-211-followup` SF1–SF6 (Confirmation-Baseline 0/6)
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (meiki-hub-Auto-Memory, `drift: true`)
- Policy `adr-threshold.md` (Selbsttest)
