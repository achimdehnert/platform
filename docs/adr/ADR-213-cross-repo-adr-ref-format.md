---
id: ADR-213
title: Cross-Repo-ADR-Referenz-Format — `repo:ADR-NNN` (plattformweit)
status: proposed
date: 2026-05-20
deciders: [achim]
informed: [all-repos]
domains: [governance, documentation, drift-prevention]
supersedes: []
amends: []
depends_on: []
tags: [adr, cross-repo, namespace, lint, convention]
scope:
  include_paths:
    - "docs/adr/ADR-*.md"
    - "scripts/checks/adr_cross_repo_refs.sh"
---

# ADR-213: Cross-Repo-ADR-Referenz-Format — `repo:ADR-NNN` (plattformweit)

- **Status:** proposed
- **Datum:** 2026-05-20
- **Entscheider:** Achim Dehnert
- **Verwandt:** ADR-211 (klickdummy-skopierte Erstanwendung als I4), ADR-207 (Cross-Repo-Doku-Konvention, **anderes Thema** — Ingest/Doku-Wahrheit, nicht Namensraum)

## Kontext

ADR-Nummern und Konzept-Bezeichner kollidieren über Repos. Belegtes Beispiel
(Drift-Episode `2026-05-19-klickdummy-adr180-collision`, festgehalten als
`drift: true`-Memory):

- `ADR-180` bezeichnet in **platform** „package-consolidation-strategy",
  in **writing-hub** „lecture-outline-wizard". Ohne Repo-Qualifier ist eine
  zitierte „ADR-180"-Aufgabe **mehrdeutig** und hat in der laufenden Session
  konkret zu einer Fehlzuordnung geführt (Eingriff am falschen Repo geplant).
- „klickdummy" bedeutet je Repo strukturell etwas anderes (manifest-Mockup,
  Demo-Render, Spec-Driven). Ohne `repo:`-Qualifier ist Diskussion über
  Klickdummies cross-repo nicht eindeutig.

Diese Mehrdeutigkeit ist nicht hypothetisch — sie ist die Drift-Lehre, die
ADR-211 als I4 erstmals klickdummy-skopiert adressiert hat. Da das Problem
nicht klickdummy-spezifisch ist, sondern jede Cross-Repo-ADR-Referenz
betrifft, wird die Regel hier **plattformweit** verallgemeinert.

## Entscheidung

**Cross-Repo-Referenzen auf ADRs MÜSSEN das Format `repo:ADR-NNN` haben**
und der striktem Regex genügen:

```
^[a-z][a-z0-9-]+:ADR-[0-9]{3}$
```

Beispiele konform: `platform:ADR-211`, `risk-hub:ADR-046`,
`writing-hub:ADR-180`, `meiki-hub:ADR-020`.

**Same-Repo-Referenzen** (Bezug auf einen ADR im selben Repo) bleiben **bare
`ADR-NNN`** zulässig — der Kontext ist eindeutig, die Lesbarkeit profitiert.

**Geltungsbereich:** alle Repos mit `docs/adr/`-Verzeichnis, und für jedes
Frontmatter-Feld, das ADR-Referenzen aufnimmt (`conforms_to`, `amends`,
`supersedes`, `depends_on`, `related`, `superseded_by`, `consolidates`,
`conflicts_with`), sowie für Body-Text und Bezug-Listen.

## Enforcement

`platform/scripts/checks/adr_cross_repo_refs.sh` existiert bereits (im
klickdummy-Kontext für ADR-211 I4 / SF5 gebaut, bewusst generisch
implementiert):

- Vertrag: validiert qualifizierte Refs der Form `<wort>:ADR-<ziffern>`
  gegen den strikten Regex; FAIL bei Verstoß.
- Bewusste Scope-Grenze: erkennt **fehlformatierte qualifizierte** Refs
  zuverlässig (nahezu false-positive-frei); erkennt **unqualifizierte
  Cross-Repo-Refs** (bare `ADR-NNN` ohne Repo-Präfix, die eigentlich
  qualifiziert sein müssten) **nicht** — keine false-positive-freie
  Heuristik möglich (ADR-Nummern-Lücken, Vorwärts-/Supersede-Refs). Die
  letzte Sicherung bleibt **Review + I4-Kultur**, nicht der Lint.

**Adoptionspfad:**

1. Plattform-CI ruft das Skript auf `platform/docs/adr/` auf.
2. `onboard-repo`-Skill (Platform) integriert den Check ins Repo-CI eines
   jeden neuen Klickdummy-/Doku-Repos (Aufruf gegen lokales `docs/adr/`).
3. Bestehende Repos: Adoption per Bedarf (keine Big-Bang-Migration nötig —
   die Regel ist konstruktiv, nicht retroaktiv strafend).

## Konsequenzen

**Positiv**
- Cross-Repo-Referenzen sind eindeutig disambiguiert; die Drift-Episode
  vom 2026-05-19 wird strukturell verhindert, nicht kulturell.
- Das ADR-Vokabular ist über Repo-Grenzen hinweg konsistent — Reviews,
  Adversarial-Pässe und Cross-Repo-Konsolidierungen werden günstiger.
- Bestehende ADRs müssen nicht massenhaft umgeschrieben werden; die Regel
  greift bei neuen/geänderten Refs durch den Lint.

**Negativ**
- Geringfügige Schreibdisziplin im Frontmatter und im Body.
- Lokale Lesbarkeit von Same-Repo-Refs bleibt bewusst bare (kein Zwang zu
  `<self>:ADR-NNN`) — eine Inkonsistenz, die wir akzeptieren, weil
  Lesefluss höher wiegt als formale Uniformität.

**Neutral**
- Same-Repo-Konvention bleibt unverändert.

## Beziehung zu existierenden ADRs

- **ADR-211 I4** ist die klickdummy-skopierte Erstanwendung dieser Regel.
  Sie bleibt dort als klickdummy-spezifische Invariante; ADR-213 ist die
  generische Verallgemeinerung.
- **ADR-207** (Cross-Repo-Ingest- & Doku-Konvention) regelt
  **Doku-Strategie** (eine Doku-Wahrheit pro Repo, MD>PDF>docx,
  inbox-Trichter, Provenienz-Archiv) — **nicht** ADR-Namensraum. Eine
  frühere Auslagerung von I4 nach ADR-207 (ADR-211 Rev 9 / F5) war eine
  thematische Fehlzuordnung und wird in ADR-211 Rev 10 zurückgenommen.

## Confirmation

- `platform/scripts/checks/adr_cross_repo_refs.sh` läuft in Platform-CI
  gegen `platform/docs/adr/`: exit 0.
- Mindestens ein zusätzliches Klickdummy-/ADR-tragendes Repo (meiki-hub,
  risk-hub oder writing-hub) ruft den Check über `make adr-refs` oder
  CI-Workflow auf.
- Die Drift-Memory `2026-05-19-klickdummy-adr180-collision` referenziert
  diesen ADR als strukturelle Antwort.

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Cross-Repo-Ref** | Referenz auf einen ADR, der in einem *anderen* Repo lebt |
| **Same-Repo-Ref** | Referenz auf einen ADR im selben Repo (bare `ADR-NNN`) |
| **`repo`-Qualifier** | kleinbuchstabiger, Bindestrich-zulässiger Token, der das Repo benennt (`platform`, `meiki-hub`, `risk-hub`, `writing-hub`, `pptx-hub`, …) |

## Bezug

- ADR-211 — Klickdummy-Cross-Repo-Rahmen (I4 als klickdummy-skopierte Erstanwendung)
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (Auslöser-Episode, `drift: true`)
- Policy `adr-threshold.md` (Selbsttest: cross-cutting ≥ 3 Repos + nicht-trivialer Drift-Trade-off → ADR-pflichtig)
