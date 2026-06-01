---
status: proposed
date: 2026-06-01
decision-makers: Achim Dehnert
domains: [ci-cd, deployment, governance, drift-prevention, dependency-management]
scope: platform
relates_to: [ADR-021, ADR-120, ADR-157, ADR-058, ADR-209, ADR-226]
tags: [ci-health, invariant, branch-protection, provenance, promote-gate, dependency-cohort, staging, cross-repo]
---

# ADR-232: Sauberer Repo-Zustand (Staging & Prod) als erzwungene Invariante statt laufendem Reparatur-Task

| Attribut       | Wert                                                    |
|----------------|---------------------------------------------------------|
| **Status**     | Proposed                                                |
| **Scope**      | platform (org-weit, alle Repos `achimdehnert`)          |
| **Repo**       | platform                                                |
| **Erstellt**   | 2026-06-01                                              |
| **Autor**      | Achim Dehnert                                           |
| **Reviewer**   | –                                                       |
| **Supersedes** | –                                                       |
| **Relates to** | ADR-021, ADR-120, ADR-157, ADR-058, ADR-209, ADR-226   |
| **Quelle**     | KONZ-platform-001 (PR #376) — intern + extern adversarial reviewt |

---

## 1. Kontext

### 1.1 Ausgangslage

Das Ziel war ursprünglich ein **laufender Task**, der alle ~41 Repos in Staging **und** Prod
CI-grün/deployfähig hält. Die Erdung (verifiziert in dieser Session) zeigte: fast alle Bausteine
existieren bereits — aber als **Detektoren, nicht Enforcer**:

- `megatest.yml:60` und `platform-audit.yml:87` fangen ihren Exit-Code ein und setzen direkt
  `continue-on-error: true` → der Job meldet grün trotz rotem Befund.
- Reusable-CI (`_ci-python.yml`, `_ci-pypi.yml`, `_ci-odoo.yml`) existiert, wird aber per-Repo nur
  *freiwillig* via `uses:` konsumiert.
- `ship.sh promote` retaggt ein `:staging`-Image nach Prod und prüft dabei **nur dessen Existenz**,
  nie ob es je grün/gesund war.
- Es existieren **zwei** Registries, die *beide* „Single Source of Truth" beanspruchen
  (`scripts/repo-registry.yaml`, `registry/repos.yaml`).
- Staging existiert real nur für ~4 von 22 Hubs (ADR-157).

### 1.2 Problem / Lücken

1. **Detect-Posture statt Prevention:** Ein Reparatur-Task verwaltet Rot-Zustände, statt sie
   unerreichbar zu machen — ein offener Regelkreis ohne Aktor (Sisyphos).
2. **Keine beweisbare Deploy-Kette:** Selbst mit „Staging grün" ist nicht bewiesen, dass *genau
   derselbe* Artefakt-Digest aus *genau demselben* Commit in Prod landet (Tags sind überschreibbar).
3. **Rote Mehrheit ist Engineering, nicht Regel-Defizit:** ~34/57 Repos rot wegen iil-*-Dependency/
   Version-Drift + echten Testfehlern. Regeln *verhindern künftige* Drift, *heilen aber kein*
   bestehendes rotes Repo.
4. **Mehrdeutige SSoT:** Adoptions-/Live-Repo-Messung erbt die Doppelquelle.

### 1.3 Constraints

- Kein Flotten-Merge-Freeze: rote Checks *jetzt* merge-blockend zu schalten friert ~34 Repos ein und
  erzeugt Goodhart-Druck (Gate-Senkung).
- Andere Orgs (`ttz-lif`, `meiki-lra`) sind von hier nicht per Settings erreichbar → nur defensiv.
- Neue Regeln deterministisch/strukturell, kein LLM (Repo-Health-Disziplin).

---

## 2. Entscheidung

**Der saubere Zustand wird eine erzwungene Invariante, nicht ein laufender Reparatur-Task.**
Leitsatz: *Green by construction — Enforcement folgt dem **frischen** Grün-Zustand pro Repo, erzwingt
ihn nie voraus.* Die Invariante liegt **nicht** auf „Repo ist grün", sondern auf der **beweisbaren
Kette** `repo@sha → artifact@digest → staging-health → prod`.

Sechs Bausteine in zwingender Reihenfolge:

- **P0 — Registry-SSoT-Konsolidierung:** zwei Registries → eine; Live-Repo-Liste abgeleitet aus
  `gh repo list` (nicht Hand-Liste). Felder u. a. `lifecycle: live|maintenance|dead`, `staging`,
  `waiver:[{gate, reason, expires}]`.
- **P0.5 — Cleanliness-Ledger + iil-Dependency-Cohort (Primär-Hebel):** ein abgeleitetes,
  maschinenlesbares `clean_state`-Ledger pro Repo (bindet `default_branch_sha`, `constraints_sha256`,
  `green_runs_30d`, `artifact_digest`, `staging_health_digest`, `prod_promotable`) + ein zentral
  erzeugter `constraints/iil-cohort-<YYYY.MM>.txt`. **Dependency-Kohärenz vor Enforcement** — sonst
  härtet die Invariante nur die ohnehin gesunden Repos.
- **R1 — `uses:`-Konvergenz** auf die shared reusable Workflows, gepinnt via gerolltem **`@v1`**
  (nicht `@main`), verteilt über **Canary-Ringe + Consumer-Contract-Test** (nicht 40 blinde Bump-PRs).
- **R2 — Branch-Protection-as-Code-Reconciler:** setzt den shared-CI-Check pro Repo **erst dann** als
  `required`, wenn ein **Frische-Quorum** erfüllt ist (≥4 erfolgreiche Default-Branch-Läufe/30 Tage,
  letzter <7 Tage alt, aktueller SHA + iil-Constraint-Snapshot, keine aktiven Waiver, nicht `sunset`,
  Owner gesetzt). Bewusst **kein** „≥N Merges"-Kriterium (Anti-Theater).
- **R3 — Digest-gebundenes Promote-Gate:** `ship.sh promote` promotet **exakt den `artifact_digest`**,
  für den das Ledger CI-green **und** staging-health-green belegt — kein Retag eines `:staging`-Tags.
  Hotfix *beschleunigt den Pfad* (ephemere Emergency-Staging, derselbe Digest), umgeht das Gate nicht;
  Break-Glass → automatischer Incident-Freeze bis nachträgliche Staging-Validierung oder Rollback.
- **R4/R5 — Ausnahmen + dünner Rest:** Waiver als Registry-Feld (kein drittes File); ein dünner
  Event-Handler für UNKNOWN-Fehler + ein abgeleiteter Adoption-/Red-Rate-Meter (Nenner = `gh repo list`),
  selbst-abschaltend (≥90 % Adoption ∧ <10 % Red-Rate/30 d) — Governance unter `/ci-green-program`.

---

## 3. Betrachtete Alternativen

| # | Alternative | Verworfen, weil |
|---|---|---|
| A | **Status quo** — Detektoren + manuelle `/ci-green-program`-Wellen | offener Regelkreis; Drift kehrt zurück (Sisyphos) — genau das, was der Auftrag ersetzen will |
| B | **Naive Invariante** — alle Checks sofort merge-blockend, promote-only by Konvention | Petitio principii (friert ~34 rote Repos ein → Goodhart); kein Enforcement-Mechanismus (Branch-Protection ist Setting, kein Code); `ship.sh` prüft nur Image-Existenz |
| C | **Synthese (gewählt)** — Enforcement folgt frischem Grün, P0/P0.5 zuerst, Gates als Code, digest-gebunden | mehr Vorarbeit (Registry-Konsolidierung + Reconciler + Cohort), dafür kein Freeze, beweisbar, graduell |
| D | **Nur P0+R1+R5** (Konvergenz + Meter, kein Enforcement) | „bleibt grün" nur gemessen, nicht garantiert — Fallback, falls Reconciler scheitert (= Kill-Gate-Ausgang) |

---

## 4. Begründung im Detail

- **Regel statt Abfolge:** Die heutige Abfolge (cron-Detektion → `continue-on-error` → Issue → Mensch
  fixt → nächster Drift) ist ein Regelkreis ohne Aktor. Sobald ein Repo verdientes frisches Grün
  erreicht, ist sein Check `required` → Drift kann nicht mehr mergen → die Abfolge entfällt für dieses
  Repo. Graduell, nicht per Dekret.
- **Gate unmittelbar vor der irreversiblen Aktion** (Lehre aus ADR-210): R3 sitzt genau dort — „Prod
  empfängt nur den belegten Staging-Digest", nicht „CI irgendwo grün".
- **Dependency-Kohärenz als Primär-Hebel** (externe Zweitmeinung): ohne iil-Cohort-Constraints
  adressiert die Invariante nicht die rote Mehrheit (Problem 1.2.3).
- **Provenance statt Tag** (externer harter Prüfpunkt AD-E1): ein überschreibbares `:staging`-Tag kann
  ein anderes Image als das geprüfte sein → Digest-Bindung schließt die Lücke.

---

## 5. Implementation Plan (30/60/90)

- **30 Tage:** P0 (eine Registry) + `continue-on-error` aus den Detektoren entfernen +
  `registry_coverage_drift`-Frühwarn-Job; P0.5-Start (erster iil-Cohort-Snapshot + read-only
  Ledger-Generator).
- **60 Tage:** `iil-distribution`-Pilot mit 3 Hubs; `tools/branch-protection-reconciler.py` im
  Dry-Run mit Frische-Quorum über alle live-Repos; erste 5 Repos „required nach verdientem frischem Grün".
- **90 Tage:** R3 digest-gebundenes Promote-Gate für die 3–4 Repos *mit* Staging; Kill-Gate-Check.

---

## 6. Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R-1 | Merge-Freeze roter Repos (Goodhart) | „required folgt frischem Grün-Quorum", nie Flotten-Schalter |
| R-2 | Branch-Protection driftet (kein Reconciler) | Reconciler als Pflicht-Baustein; Kill-Gate koppelt daran |
| R-3 | `@main`-Bruch trifft Flotte unsichtbar | `@v1`-Tag + Canary-Ringe + Consumer-Contract-Test |
| R-4 | Waiver werden de-facto permanent | `expires` maschinell vom Meter gelesen; `budget_sum_trend`-Alarm |
| R-5 | Meter wird blind (Hand-Listen-Nenner) | Nenner = `gh repo list`; `registry_coverage_drift` |
| R-6 | Überschriebenes `:staging`-Tag fälschlich promotet | R3 digest-gebunden; Ledger erzwingt `artifact_digest == staging_health_digest` |

---

## 7. Konsequenzen

### 7.1 Positiv
- „Staging + Prod sauber" wird eine *Konstruktions*-Eigenschaft (beweisbare Kette), kein Prüfziel.
- Der Reparatur-Loop wird abgeschafft, nicht perfektioniert; der Rest-Task schaltet sich selbst ab.
- Eine einzige Registry-SSoT; Dependency-Drift an der Quelle kontrolliert.

### 7.2 Trade-offs
- Erhebliche Vorarbeit (Registry-Konsolidierung, Reconciler, iil-Cohort) vor erstem Enforcement-Effekt.
- `iil-distribution` erfordert Release-Disziplin; eine kaputte zentrale Distribution kann mehrere Repos
  blocken → bewusst nur 3-Hub-Pilot.

### 7.3 Nicht in Scope
- Andere Orgs (`ttz-lif`, `meiki-lra`) — nur defensiv.
- Heilung bestehender roter Repos (echtes per-Repo-Engineering, F4-Programm) — dieser ADR *verhindert*
  künftige Drift und sperrt gewonnenen Boden, *fixt* aber kein rotes Repo.
- ADR-209 (policy-auto-sync) ist **nicht** betroffen (verbreitetes Fehl-Label „ADR-209 = CI-Health").

---

## 8. Validation Criteria

- Nach P0 existiert **genau eine** Datei mit `# Single Source of Truth`; Live-Liste = `gh repo list`.
- Ledger enthält pro Repo `artifact_digest == staging_health_digest` **oder** `prod_promotable: false`.
- `tools/branch-protection-reconciler.py` setzt `required` ausschließlich bei erfülltem Frische-Quorum
  (auditierbar via `gh api …/branches/main/protection`).
- `ship.sh promote` schlägt fehl, wenn der zu promotende Digest kein belegtes staging-health-green hat.
- **Kill-Gate (messbar, datiert):** Wenn bis **2026-09-01** weder die Registry konsolidiert noch der
  Reconciler existiert → ADR auf `Deprecated`, Rückfall auf Alternative D (reines `/ci-green-program`).
  Exception-Budget: max. 2 aktive Registry-Waiver/Repo, je `expires` ≤ 90 Tage; abgelaufen = CI-Fail.

---

## 9. Glossar

| Abkürzung / Begriff | Bedeutung |
|---|---|
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung. |
| **CI/CD** | Continuous Integration / Continuous Deployment — automatisierte Test-/Auslieferungspipeline. |
| **Invariante** | Eine Bedingung, die per Konstruktion immer wahr ist (kein Pfad in den verletzenden Zustand). |
| **Branch-Protection** | GitHub-Regel, die Merges auf einen Branch an Bedingungen (z. B. grüne Checks) bindet. |
| **Required Status Check** | Ein CI-Check, der grün sein *muss*, bevor gemergt werden darf. |
| **Reusable Workflow** | Zentral gepflegter GitHub-Actions-Workflow, den andere Repos via `uses:` einbinden. |
| **Artifact Digest** | Unveränderlicher Inhalts-Hash (`sha256:…`) eines Container-Images — im Gegensatz zum überschreibbaren Tag. |
| **Provenance-Kette** | Lückenlose Herkunftskette: welcher Commit → welches Artefakt → welche Validierung → Prod. |
| **Promote-Gate** | Prüfschritt unmittelbar vor der Prod-Auslieferung. |
| **Frische-Quorum** | Mindestmenge *aktueller* erfolgreicher CI-Läufe als Beleg für „echtes" (nicht passives) Grün. |
| **iil-Cohort / Distribution** | Zentral getesteter, versions-kohärenter Satz interner `iil-*`-Libraries als ein pinbares Paket. |
| **Waiver** | Dokumentierte, ablaufende Ausnahme von einer Regel. |
| **Goodhart** | „Wird eine Metrik zum Ziel, taugt sie nicht mehr als Metrik" — Anreiz zur Umgehung. |
| **SSoT** | Single Source of Truth — die eine maßgebliche Datenquelle. |

---

## 10. Referenzen

- **KONZ-platform-001** (`docs/konzepte/KONZ-platform-001-clean-state-invariant.md`, PR #376) — volle
  Analyse inkl. internem Dreifach-Adversariat + externer Zweitmeinung.
- Externes Briefing: `~/shared/konzept-clean-state-invariant-2026-06-01.md`.
- **ADR-021** Unified Deployment Pattern · **ADR-120** Unified Multi-Repo Deployment Pipeline mit
  Staging · **ADR-157** Staging-Production-Split & Port-Governance · **ADR-058** Platform Test-Taxonomy
  · **ADR-226** `_ci-pypi.yml`-Adoption-Gate (Meter-Muster) · **ADR-210** Gate vor irreversibler Aktion.
- `/ci-green-program` (Governance + Self-Exit-Kriterium).

---

## 11. Changelog

- **2026-06-01:** Initial (Proposed). Abgeleitet aus KONZ-platform-001 nach internem + externem
  Adversarial-Review; Provenance-Kette + Frische-Quorum + iil-Cohort als Primär-Hebel integriert.
