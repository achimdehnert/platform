---
id: ADR-232
title: "CC-Skill-Namens-Taxonomie: Präfix-Gruppen mit Alias-Migration"
status: proposed
date: 2026-06-01
deciders: [Achim Dehnert]
consulted: []
informed: [iilgmbh]
domains: [skills, cc-skill-dist, dx]
supersedes: []
amends: []
depends_on: [ADR-229, ADR-230]
related: [ADR-229, ADR-230]
tags: [skill, naming, taxonomy, cc-skill-dist, dx]
scope:
  include_paths:
    - "docs/adr/ADR-232-*"
---

# ADR-232 — CC-Skill-Namens-Taxonomie: Präfix-Gruppen mit Alias-Migration

| Attribut | Wert |
|---|---|
| **Status** | Proposed |
| **Scope** | platform (cross-cutting: alle CC-Skills) |
| **Relates to** | ADR-229 (Windsurf-Review-Subset), ADR-230 (CC-first-Distribution) |

## 1. Kontext

Es gibt ~70 CC-Skills in einem **flachen Namensraum** (`platform main
.windsurf/workflows/`, verteilt via `cc-skill-dist` nach `~/.claude/commands/`).
Probleme:

1. **Auffindbarkeit:** `/` listet 70 Einträge ohne Gruppierung; verwandte Skills
   (`adr`, `adr-review`, `adr-challenger`, `adr-curator`, `adr-health`,
   `adr-handoff-extern`) sind nur durch Konvention beieinander.
2. **Kollisionen / Verwechslung:** Beinahe-Homonyme (`teste-repo` vs. der heute
   vorgeschlagene `repo-testen`) sind ein realer Footgun.
3. **Inkonsistente Benennung:** mal Verb-zuerst (`teste-repo`), mal Nomen-zuerst
   (`repo-health-check`), mal Sprache gemischt (de/en).

## 2. Entscheidung

**Präfix-Gruppen-Taxonomie `<gruppe>-<verb/nomen>`**, durchgesetzt über
`cc-skill-dist`, eingeführt **mit Alias-Migration (kein Breaking-Rename)**.

### 2.1 Gruppen (Vorschlag, finalisierbar im Review)

| Präfix | Domäne | Beispiele (neu ← alt) |
|---|---|---|
| `adr-*` | ADR-Lifecycle | bereits konform (`adr`, `adr-review`, …) |
| `repo-*` | Repo-Level-Ops | `repo-ready` (neu), `repo-health` ← `repo-health-check`, `repo-onboard` ← `onboard-repo` |
| `kd-*` | Klickdummy | `kd-new` ← `klickdummy`, `kd-search` ← `klickdummy-search` |
| `test-*` | Test/QA | `test-repo` ← `teste-repo`, `test-frontend` ← `frontend-ui-test`, `test-prerelease` ← `pre-release-test` |
| `infra-*` | Infra/Drift | bereits tlw. konform; `infra-drift` ← `drift-check`, `infra-nginx` ← `nginx-check` |
| `deploy-*` | Deploy/Release | `deploy-prod` ← `run-prod`/`ship`, `deploy-staging` ← `run-staging`/`ship-staging`, `deploy-rollback` ← `rollback` |
| `session-*` | Session-Ritual | `session-start`, `session-end` ← `session-ende`, `session-knowledge` ← `knowledge-capture` |
| `docu-*` | Doku | bereits tlw. konform |

> Die exakte Map ist **Review-Gegenstand**; diese ADR legt das **Schema** +
> **Migrationsmechanismus** fest, nicht jede Einzelumbenennung als Fakt.

### 2.2 Konvention

- Schema `<gruppe>-<kurz>`, **lowercase-kebab**, Sprache **einheitlich** (Vorschlag:
  en für Gruppe+Verb; de-Begriffe nur wo fachlich zwingend).
- Genau **ein** Präfix je Skill; keine Mehrfach-Gruppen.
- Neue Skills tragen ab Annahme **direkt** den Gruppen-Präfix (z. B. `repo-ready`).

### 2.3 Migration — Alias-Fenster (kein Breaking)

1. `cc-skill-dist/generate.py` erhält **Alias-Support:** zu jedem umbenannten Skill
   wird zusätzlich ein **deprecated Alias-Stub** unter dem alten Namen generiert
   (Frontmatter `deprecated_alias_of: <neu>`, Body = Hinweis + Weiterleitung).
2. **Deprecation-Fenster** (Vorschlag: 1 Quartal). `doctor.py` meldet Alias-Nutzung;
   nach Frist werden Alias-Stubs entfernt.
3. **Repo-by-repo / gruppenweise** Rollout (nicht Big-Bang), je über das gegatete
   Live-Rollout (ADR-230 §8).
4. Referenzen in Doku/Memory/`workflow-index` werden mitgezogen (Teil der jeweiligen
   Gruppen-PR).

## 3. Konsequenzen

**Positiv:** Auffindbarkeit (Gruppen-Tab-Completion `repo-<tab>`), keine Homonym-
Kollisionen, konsistente Benennung, klare Heimat für neue Skills.

**Negativ / Risiko:** Muskelgedächtnis-Bruch (gemildert durch Alias-Fenster);
Einmal-Aufwand Alias-Mechanik in `cc-skill-dist`; Doku-Referenzen-Sweep.
**Mitigation:** Aliase + phasenweiser Rollout + `doctor.py`-Tracking.

## 4. Alternativen

1. **Status quo (flach):** null Aufwand, aber Auffindbarkeit/Kollisionen bleiben.
   *Verworfen* — der `teste-repo`/`repo-testen`-Footgun ist real.
2. **Big-Bang-Rename ohne Alias:** schnell, aber bricht jeden bestehenden Aufruf +
   Doku. *Verworfen* — inakzeptables Breaking.
3. **Nur neue Skills konform, alte unangetastet:** geringster Aufwand, aber
   dauerhafte Zwei-Welten-Inkonsistenz. *Teil-Fallback*, falls Alias-Mechanik zu teuer.

## 5. Offene Punkte (Review)

- Finale Gruppen-Liste + exakte Einzel-Map.
- Sprache (en vs. de) einheitlich?
- Deprecation-Fenster-Länge.
- Reihenfolge des gruppenweisen Rollouts.

## Provenance

- 2026-06-01: User-Frage „Renaming vorhandener Skills nach Gruppe (z. B. /kd-test,
  /repo-…)?" im Zuge des `/repo-ready`-Baus. Diese ADR legt Schema + Alias-Migration
  fest; `/repo-ready` ist bereits `repo-*`-konform.
