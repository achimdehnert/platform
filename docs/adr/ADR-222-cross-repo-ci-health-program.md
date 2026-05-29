---
status: proposed
date: 2026-05-18
revision: 4
decision-makers: [Achim Dehnert]
scope: platform
implementation_status: none
related: [ADR-111, ADR-196, platform#191, platform#194]
supersedes: []
---

# ADR-222 (v4, amendiert): Zwei SHA-gepinnte CI-Familien für 48 Repos

> **Kurz:** Geteilte CI ja. *Eine* Familie für 48 heterogene Repos nein.
> Zwei Familien (PyPI-Library / Django-Hub), Pin per **SHA**, ein
> **dynamischer read-only `platform-doctor`** als Wahrheits-Check.
> Library-Kompatibilität via **api-diff + Consumer-Pinning + Dependabot**
> — *nicht* via Reverse-Smoke (per Red-Team V4.3 exzidiert).

## Status

`proposed` — **eingefroren bis `platform-doctor`-Daten vorliegen**. Keine
weitere ADR-Iteration ohne neue Empirie (Lehre aus 4 Iterationen v1→v4;
vgl. Rationale §8/§9). Begründung: `reviews/ADR-222-v4-rationale.md`.

## Kontext

48 Repos. Empirie `platform#191` (gitleaks in `_ci-python.yml`): ein Fix
entsperrte alle Consumer und hätte bei einem Bug alle gebrochen.

**Repo-Triage 2026-05-18 — vom Entscheider verifiziert, als Faktum behandelt:**
46/49 aktiv, 3 raus (`iil-adrfw-repo` Dup-Klon, `iil-codeguard`, `lastwar-bot`
— keiner tragend). **Folge: keine Scope-Reduktion. Dies ist eine
46-Repo-Vollflotten-Konvergenz ohne Rabatt** — bewusst akzeptiert, kein
offener Punkt. Die verifizierte `bemerkung`-Spalte belegt zugleich die
Zwei-Kategorien-Struktur (deployed-Hub vs. Library-mit-Consumern):

| Kategorie | ~Anzahl | CI-Charakter | Top-Risiko |
|---|---|---|---|
| PyPI-Library | ~14 | build → test-Matrix → api-diff → twine | schlechte Release bricht bis zu 21 Consumer |
| Django-Hub | ~34 | docker build → test → GHCR → compose up | ein Hub down = 1 Service (lokaler Blast-Radius) |

Top-Libraries nach Consumern: `aifw` (13), `promptfw` (12), `testkit` (11),
`authoringfw` (9). `platform` selbst: 21 Consumer.

## Entscheidung

### D1 — Zwei Workflow-Familien, nicht eine
`achimdehnert/.github/.github/workflows/`: `_ci-pylib.yml` (PyPI-Libs) und
`_ci-djangohub.yml` (Django-Hubs). Repos konsumieren eine oder keine. Dritte
Familie nur per neuer ADR.

### D2 — SHA-Pin statt Tag-Pin
Konsumenten pinnen Commit-SHA (`uses: …/_ci-pylib.yml@a3f9e21…`), nie `@vN`.
Tag-Mutation durch Maintainer-Compromise verteilt sonst beliebigen Code an
48 Repos. GitHub-Industriestandard.

### D3 — Updates über Dependabot, kein Magic-Number-Canary
Dependabot schlägt SHA-Bumps als PR pro Repo vor; die Merge-Reihenfolge ist
die faktische Canary-Kohorte. Kein separater `N=3`-Mechanismus.

### D4 — Library-Kompatibilität via api-diff + Consumer-Pinning (ersetzt Reverse-Smoke)
**Reverse-Smoke wurde per Red-Team V4.3 verworfen** (invertierter SPOF:
kaputter Consumer-Test blockiert Lib-Release für alle anderen; falsches
Artefakt: testet Source statt Wheel — die mcp-hub-hatchling-Klasse;
willkürliches N gegen den Long-Tail). Stattdessen — konsistent damit, dass
Dependabot bereits für SHA-Bumps vertraut wird:

1. `_ci-pylib.yml` hat einen **`api-diff`**-Job: bricht die *öffentliche*
   API vs. letzter PyPI-Release ohne Major-Bump → Release rot. Library-
   seitiger Vertrag (Semver, hartes Gate).
2. Consumer pinnen **exakte** Version (`aifw==X.Y`, nicht `>=`).
3. **Dependabot** öffnet den Bump-PR im Consumer; die **Consumer-eigene CI**
   ist das Integrations-Gate — dort wo Kontext + echtes Wheel sind.

Kein `consumers.yaml`, kein library-seitiges Cross-Repo-Klonen, keine
release-blockierende Fremd-Testsuite.

### D5 — `platform-doctor`: dynamischer, read-only Conformance-Check
Eine Datei (`scripts/platform_doctor.py`, < 300 Z., **keine** Schreib-Ops).

**Dynamische Repo-Discovery — keine hartkodierte Liste** (Repo-Zahl/-Set
ändert sich; eine fixe Liste wäre selbst Drift/Rot-Fläche): doctor
enumeriert Repos zur Laufzeit (Scan `$GITHUB_DIR` nach `.git` → `origin`;
Aktualität via `gh repo view --json pushedAt`, NICHT via
Shallow-Clone-`git log` — das war ein realer Mess-Fehler in Phase 0).
Kategorie (pylib/hub/other) wird **inferiert**, nicht gepflegt.

Checks/Repo: SHA-Pin statt `@main`/`@vN` · `requires-python` ↔ CI/Container ·
keine `git+…#subdirectory`-Deps · (pylib) letzte Release < 180 d ODER
`.ci-frozen` · (hub) `/livez`+`/healthz`. Output:
`reports/platform-doctor-<datum>.md`, Status `green|yellow|red` pro Repo.
Ad hoc oder als Step in `_ci-djangohub.yml` von `platform`.

### D6 — Maintenance-Pinning
Niedrig-aktive Repos dürfen Frozen-SHA via `.ci-frozen` (Grund +
`re-review-date`). `platform-doctor` toleriert, alarmiert bei Überschreitung.

### D7 — Waiver mit Hard-Limits
`docs/ci-waivers.yaml`: `expires` Pflicht (abgelaufen = rot); `renewed >= 2`
→ Eskalations-Issue; max **5 aktive Waiver/Repo** (hart, sonst rot).

## Explizit ausgeschlossen (eigene spätere ADRs)
Org-weiter Auto-Fix-Bot (Threat-Model-ADR) · dritte Familie (ADR-222a falls
empirisch nötig) · Monorepo · Programm-Selbstabschaltung (ersetzt durch
`platform-doctor`-Trends). **Reverse-Smoke**: verworfen, nicht „später".

## Konsequenzen
**+** Heterogenität anerkannt (kein God-Workflow); SHA-Pin = Standard;
Library-Vertrag (api-diff) ohne invertierten SPOF; doctor dynamisch →
selbst-aktualisierend, kein Listen-Rot; Prozess bleibt im Skill, nicht in
Governance. **−** Vollflotten-Invest real (~46 Repos, kein Triage-Rabatt;
Schätzung Rationale §6 **ohne** Reverse-Smoke-Posten); zwei Familien können
driften → geteilte Schritte als Composite Action `ci-common@<sha>`.
**Reversibel:** SHA-Pins/Doctor pro Repo rücknehmbar, kein Fleet-Lock-in.

## Implementation-Reihenfolge (Code zuerst — Lehre aus v1→v4)
1. **`platform-doctor` v0.1** (dynamisch, read-only) — erzeugt die Empirie.
2. Doctor-Output reviewen. Trägt das Bild nicht → ADR pausiert lassen,
   *kein* v5.
3. `_ci-pylib.yml` (+ api-diff) zuerst `aifw` (13 Consumer = größter Hebel).
4. `_ci-djangohub.yml` zuerst `platform`.
5. Dependabot in Top-16; `.ci-frozen` für Maintenance; Rest über Wochen.
`platform-doctor` grün auf Top-16 = „fertig" für die Konvergenzphase.

## Offen für externen Review
1. api-diff-Tooling: `griffe`/eigener AST-Diff?
2. Composite-Action `ci-common@<sha>` jetzt oder Duplikation tolerieren?
3. `platform-doctor` strikt read-only (kein Auto-PR)?
4. MCP/Odoo/Bots → `_ci-djangohub.yml` oder ADR-222a?
