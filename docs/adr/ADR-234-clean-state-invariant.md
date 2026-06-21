---
status: accepted
implementation_status: in_progress
date: 2026-06-01
decision-makers: Achim Dehnert
domains: [ci-cd, deployment, governance, drift-prevention, dependency-management]
scope: platform
relates_to: [ADR-021, ADR-120, ADR-157, ADR-058, ADR-209, ADR-226]
tags: [ci-health, invariant, branch-protection, provenance, promote-gate, dependency-cohort, staging, cross-repo]
---

# ADR-234: Sauberer Repo-Zustand (Staging & Prod) als erzwungene Invariante statt laufendem Reparatur-Task

| Attribut       | Wert                                                    |
|----------------|---------------------------------------------------------|
| **Status**     | Accepted (2026-06-06) — Kern-Invariante + P0; R2/R3-full/R5 gated Roadmap (s. §2.1) |
| **Scope**      | platform (org-weit, alle Repos `achimdehnert`)          |
| **Repo**       | platform                                                |
| **Erstellt**   | 2026-06-01                                              |
| **Autor**      | Achim Dehnert                                           |
| **Reviewer**   | intern (3×) + extern (Review-Runde 2 + 3, adversarial)  |
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

Bausteine in der Reihenfolge **P0 → P0.5a → R1 → P0.5b → R3-minimal → R2 → R3-full → R5** (nach externer
Review-Runde 2 neu geschnitten — R3 sitzt am irreversibelsten Pfad und darf nicht hinter voller R2
warten; AD-4/M28-5):

- **P0 — Registry-SSoT-Konsolidierung via Union-Canonical (korrigiert 2026-06-01, Befund unten):**
  **Wichtig — kein „eine zur View der anderen":** Die zwei heutigen Registries sind **kein Superset**,
  sondern unterschiedlicher *Scope*: `scripts/repo-registry.yaml` = flaches Flotten-Inventar (**42 Repos**,
  operativ: type/prod_url/port/health), `registry/repos.yaml` = kuratiertes deployed-Subset (**18 Systeme**,
  Deploy/Lifecycle/Tenancy/Coverage). Schnittmenge nur 16; **26 Repos nur flach, 2 nur reich.** Ein
  Generator „reich → flach" würde 26 Repos verlieren (verifiziert via `tools/registry-consistency-check.py`).
  → Der einzige verlustfreie Weg: eine **neue kanonische Union-Registry aller ~44 Repos** mit
  **geschichtetem Schema** (operative Felder für *alle* + Deploy/Governance-Felder für das deployed-Subset);
  **beide Altdateien werden daraus als Views generiert** (dann wirklich verlustfrei), Konsumenten danach
  inkrementell migriert, Views retired. Live-Repo-Liste abgeleitet aus `gh repo list` mit **deterministischen
  Include/Exclude-Filtern** (archived, fork, template, private/internal, infra-only, repo-type, Fremd-Org —
  AD-9/AD-21). Union-Schema mit **einem kanonischen Lifecycle-Feld** (`pipeline_status ∈ {live, maintenance,
  dead, archived}` — kein zweites `sunset`-Vokabular; AD-1/M28-2) + Pflichtfeldern `owner_team`, `repo_type`,
  `staging_profile`, `artifact_kind` und der **vollständigen Waiver-Semantik** (`waiver:[{gate, reason,
  expires}]`, Max-Budget, Gate-Bezug — aus R4 vorgezogen, AD-2).
  **Erststep (nicht-brechend, bereits gebaut):** `tools/registry-consistency-check.py` + informational
  CI-Job machen die Dual-SSoT-Divergenz sichtbar/nicht-driftend, bevor die Union-Migration startet.
- **P0.5a — iil-Dependency-Cohort + Ledger-*Schema* (Primär-Hebel):** zentral erzeugter
  `constraints/iil-cohort-<YYYY.MM>.txt` (mit Supportfenster/Deprecation-Datum, M28-8) + die *Definition*
  des `clean_state`-Ledger-Schemas, **repo-typisiert** (Hub = Docker-`artifact_digest`; Library =
  Package-Artefakt; Infra = eigenes Gate-Profil oder `prod_promotable: N/A`; AD-12/M28-4). Dependency-
  Kohärenz **vor** Enforcement — sonst härtet die Invariante nur die ohnehin gesunden Repos.
- **R1 — `uses:`-Konvergenz + Metadaten-Contract:** jedes live-Repo konsumiert die shared reusable
  Workflows via `uses:`, gepinnt via gerolltem **`@v1`** (nicht `@main`), verteilt über **Canary-Ringe +
  Consumer-Contract-Test** (nicht 40 blinde Bump-PRs). Die Workflows **emittieren** die Ledger-Metadaten
  (sha, `constraints_sha256`, run-provenance, digest) — Voraussetzung, dass P0.5b ein echtes Ledger
  aggregieren kann (AD-3/AD-14).
- **P0.5b — `clean_state`-Ledger (abgeleiteter Cache, KEINE dritte Wahrheit):** aggregiert + validiert aus
  GitHub-Actions + Registry + Deploy-Artefakten; ausdrücklich als *derived cache* markiert, nie eigene
  Quelle (AD-11). Bindet `default_branch_sha`, `constraints_sha256`, `green_runs_30d`, `artifact_digest`,
  `staging_health_digest`, `prod_promotable`.
- **R3-minimal (fail-closed, staging-fähige Hubs zuerst):** das Promote-Gate wird **früh** als schmaler
  Fail-Closed-Ring auf den 3–4 staging-fähigen Hubs scharf — `ship.sh promote` promotet **exakt den
  `artifact_digest`**, für den das Ledger CI-green **und** staging-health-green belegt (kein Retag eines
  beweglichen `:staging`-Tags). Schließt den gefährlichsten irreversiblen Pfad, ohne die rote Flotte zu
  blockieren.
- **R2 — Branch-Protection-as-Code-Reconciler (mit Mindestvertrag):** setzt den shared-CI-Check pro Repo
  **erst** als `required`, wenn ein **Frische-Quorum** erfüllt ist (≥4 erfolgreiche Default-Branch-Läufe/30 d,
  letzter <7 d, aktueller SHA + iil-Constraint-Snapshot, keine aktiven Waiver, `pipeline_status: live`,
  `owner_team` gesetzt; Run-Provenance zählt nur zulässige Quellen — `run_source ∈ {scheduled, push}`,
  kein blindes rerun/manual; AD-19). Bewusst **kein** „≥N Merges"-Kriterium (Anti-Theater). **Mindestvertrag**
  des Reconcilers: `plan/apply/rollback`, idempotenter Diff, Audit-Log pro Repo, minimaler Token-Scope,
  Rate-Limit-/Partial-Failure-Verhalten, Schutz gegen ungeprüfte Massenänderung an 41 Repos (AD-10/M28-1).
  Rote/unklassifizierte Repos → explizite **`quarantine`-Lane** (kein Required, kein Prod-Promote ohne
  Break-Glass, aber Pflicht-Ledger + Owner) statt Flotten-Freeze.
- **R3-full:** Promote-Gate auf alle staging-fähigen + ledger-belegten Repos ausgerollt. Hotfix
  *beschleunigt den Pfad* (ephemere Emergency-Staging, derselbe Digest), umgeht das Gate nicht; Break-Glass
  → automatischer Incident-Freeze bis nachträgliche Staging-Validierung oder Rollback.
- **R4/R5 — Ausnahmen + dünner Rest:** R4 ist nur noch die **Enforcement-/Reporting-Regel** über die in
  P0 definierte Waiver-Semantik (kein drittes File, kein eigenes Schema). R5 = dünner Event-Handler für
  UNKNOWN-Fehler + abgeleiteter Meter (Nenner = gefilterte `gh repo list`); **Selbstabschaltung an
  Enforcement-Abdeckung gekoppelt** (R2-required + R3-Promote + Waiver-Expiry + UNKNOWN-Handling ≥30 d ohne
  kritische Lücke), nicht allein an Adoption/Red-Rate (AD-17/AD-18). Governance unter `/ci-green-program`.

### 2.1 Was Acceptance bedeutet — und was nicht (externe Review-Runde 3, REC-20)

Dieser ADR ist `accepted`, aber **phasenscharf**. Acceptance ist kein Liefer-Commitment für das
gesamte 8-Schritt-Programm; sie fixiert die Richtung und den bereits gelieferten Fundament-Slice.

**Entschieden (akzeptiert, nicht mehr neu aufzurollen):**
- Eine **kanonische SSoT** (`registry/canonical.yaml`); die Altdateien sind **generierte Views**, durch
  ein hartes Drift-Gate gegen Divergenz gesichert; neuer Code liest über `tools/registry_api.py`.
- **Digest-gebundene Provenance** `repo@sha → artifact@digest → staging-health → prod` (kein Tag-Retag).
- **Enforcement folgt frischem Grün** pro Repo (Frische-Quorum), erzwingt es nie voraus.
- **Quarantine-Lane statt Flotten-Freeze** für rote/unklassifizierte Repos.
- **Gate unmittelbar vor Prod-Promote** (R3 am irreversiblen Pfad).

**Noch nicht final akzeptiert (gated Roadmap — erwartbare ADR-Amendments, AD-13/M28-2):**
- Das konkrete **R2-Backend**: native GitHub-Rulesets (Alt E) vs. imperativer Reconciler-Bot — bis zur
  Entscheidung wird R2 **nur als Dry-Run/Plan-Generator** akzeptiert, nicht als schreibender Aktor.
- **R3-full**-Abdeckungsbreite über Repo-Typen/Artefaktarten/Staging-Profile hinaus.
- **R5**-Selbstabschaltung; **Alt F** (signiertes Clean-State-Certificate als bindender R3-Beleg) bleibt
  „nicht verworfen", Entscheidung bei R3-full.

Der nächste harte Acceptance-Slice ist **R3-minimal fail-closed** auf mind. einem staging-fähigen Hub;
weitere Phasen werden erst voll akzeptiert, wenn ein echtes fail-closed Promote-Gate + Break-Glass/
Rollback dokumentiert sind. Falsifizierbarkeit liegt im gestuften **Kill-Gate §8** (2026-09-01) — eine
Verlängerung darf nur per ausdrücklichem ADR-Amendment erfolgen, sonst automatischer Rückfall auf
`Detect-only` (Alt D).

---

## 3. Betrachtete Alternativen

| # | Alternative | Verworfen, weil |
|---|---|---|
| A | **Status quo** — Detektoren + manuelle `/ci-green-program`-Wellen | offener Regelkreis; Drift kehrt zurück (Sisyphos) — genau das, was der Auftrag ersetzen will |
| B | **Naive Invariante** — alle Checks sofort merge-blockend, promote-only by Konvention | Petitio principii (friert ~34 rote Repos ein → Goodhart); kein Enforcement-Mechanismus (Branch-Protection ist Setting, kein Code); `ship.sh` prüft nur Image-Existenz |
| C | **Synthese (gewählt)** — Enforcement folgt frischem Grün, P0/P0.5 zuerst, Gates als Code, digest-gebunden | mehr Vorarbeit (Registry-Konsolidierung + Reconciler + Cohort), dafür kein Freeze, beweisbar, graduell |
| D | **Detect-only fallback** — `P0-minimal + R1-Adoption-Meter + R5-Report`, **ohne** Anspruch auf erzwungene Invariante | „bleibt grün" nur gemessen, nicht garantiert — expliziter Kill-Gate-Rückfall (AD-7/M28-6). Fehlt sogar P0, ist D nicht erreichbar → Rückfall = „Status quo mit Warnung" |
| E | **Native GitHub-Rulesets als deklaratives Policy-as-Code-Backend** für R2 (statt imperativer Reconciler-Bot) | **nicht verworfen** — wahrscheinlich die robustere R2-Form (auditierbar, Dry-Run/Diff/Rollback); im Implementation Plan zu entscheiden, ob der Reconciler Settings *schreibt* oder nur Policy *generiert/validiert* (AD-15/M28-1) |
| F | **`clean-state certificate` / Build-+Staging-Attestation** als direkt prüfbares R3-Gate-Artefakt | **nicht verworfen** — als R3-Härtung: das bindende Gate hängt an einem unveränderlichen, signierten Zertifikat statt primär am mutable zentralen Ledger; Ledger bleibt Meter/Index (AD-16) |

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

## 5. Implementation Plan (30/60/90 — Sequenz P0 → P0.5a → R1 → P0.5b → R3-minimal → R2 → R3-full → R5)

- **30 Tage:** P0 (eine Registry + vollständiges Schema inkl. Waiver-Semantik + gefilterter
  `gh repo list`-Nenner) + `continue-on-error` aus den Detektoren entfernen +
  `registry_coverage_drift`-Frühwarn-Job; **P0.5a** (erster iil-Cohort-Snapshot + repo-typisiertes
  Ledger-*Schema*).
- **60 Tage:** R1 (Workflows emittieren Ledger-Metadaten, `@v1` + Canary-Ringe) → **P0.5b**
  (Ledger als derived cache); `iil-distribution`-Pilot mit 3 Hubs; **R3-minimal** fail-closed für
  mind. 1 staging-fähigen Hub; `tools/branch-protection-reconciler.py` im **Dry-Run** (Mindestvertrag)
  mit Frische-Quorum über alle live-Repos.
- **90 Tage:** R2 erste „required nach verdientem frischem Grün" + `quarantine`-Lane; R3-full für die
  staging-fähigen Hubs; Kill-Gate-Check (gestuft, s. §8).

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
- **Kill-Gate (messbar, datiert, GESTUFT — prüft die Kern-Invariante, nicht nur Vorarbeit; AD-5/AD-6):**
  Bis **2026-09-01** müssen **alle** folgenden existieren — sonst Status `Deprecated` bzw. `Detect-only`:
  (1) P0 konsolidiert (eine SSoT-Datei); (2) P0.5a — iil-Cohort-Snapshot + repo-typisiertes Ledger-Schema;
  (3) R2-Reconciler **mindestens im Dry-Run** (eine bloß konsolidierte Registry *ohne* Enforcement-Pfad
  hält den ADR **nicht** am Leben); (4) **R3-minimal fail-closed** für mind. **einen** staging-fähigen Hub.
  Rückfall = Alternative D (Detect-only); fehlt sogar (1), Rückfall = „Status quo mit Warnung" (AD-7).
- **Exception-Budget:** max. 2 aktive Waiver/Repo, je `expires` ≤ 90 Tage. **„Abgelaufen = Fail" präzise**
  (AD-8): ein abgelaufener Waiver lässt den zentralen Policy-Check **und** die gate-spezifische
  Promote-/Required-Eligibility-Prüfung des betroffenen Repos fehlschlagen — **nicht** einen
  unkontrollierten Flotten-Freeze noch-nicht-eligibler roter Repos.

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
- Externes Briefing (ADR-Runde): `~/shared/adr-handoff-ADR-234-2026-06-01.md`.
- Externes Briefing (Konzept-Runde): `~/shared/konzept-clean-state-invariant-2026-06-01.md`.
- **ADR-021** Unified Deployment Pattern · **ADR-120** Unified Multi-Repo Deployment Pipeline mit
  Staging · **ADR-157** Staging-Production-Split & Port-Governance · **ADR-058** Platform Test-Taxonomy
  · **ADR-226** `_ci-pypi.yml`-Adoption-Gate (Meter-Muster) · **ADR-210** Gate vor irreversibler Aktion.
- `/ci-green-program` (Governance + Self-Exit-Kriterium).

---

## 11. Rückfluss externe Review-Runde 2 (Step-5-Tagging)

Die externe ADR-Review-Runde lieferte 15 RECs. Tagging-Disziplin: nur `[valid]` floss als *eigene*
Änderung ein, nicht als wörtliche Übernahme. Verdikt-Tabelle (REC → Verdikt → Aktion):

| REC | Verdikt | Aktion im ADR |
|---|---|---|
| REC-1 (Schema/Lifecycle/Owner) | [valid] | P0 um kanonisches `pipeline_status` + Pflichtfelder erweitert |
| REC-2 (Waiver in P0) | [valid] | Waiver-Semantik nach P0 vorgezogen; R4 = nur Enforcement/Reporting |
| REC-3 (P0.5-Split) | [valid] | P0.5a (Cohort+Schema) / R1 (Metadaten-Emission) / P0.5b (Ledger) |
| REC-4 (Sequenz, R3 früher) | [valid] | Sequenz P0→P0.5a→R1→P0.5b→R3-min→R2→R3-full→R5 |
| REC-5 (Kill-Gate gestuft) | [valid] | §8: 4 gestufte Muss-Kriterien bis 2026-09-01 |
| REC-6 (Alt D = Detect-only) | [valid] | Alternative D neu definiert; Sub-Fallback „Status quo mit Warnung" |
| REC-7 („abgelaufen=Fail" präzise) | [valid] | §8 Exception-Budget präzisiert (kein Flotten-Freeze) |
| REC-8 (`gh repo list`-Filter) | [valid] | P0 deterministische Include/Exclude-Filter |
| REC-9 (R2-Mindestvertrag) | [valid] | R2 um plan/apply/rollback/audit/token-scope erweitert |
| REC-10 (Ledger=derived cache, typisiert) | [valid] | P0.5a/P0.5b: repo-typisierte Profile, „derived cache" explizit |
| REC-11 (Alt E: GitHub Rulesets) | [valid] | Alternative E ergänzt |
| REC-12 (Alt F: Attestation) | [valid] | Alternative F ergänzt |
| REC-13 (R5 enforcement-coverage) | [valid] | R5-Selbstabschaltung an Enforcement-Abdeckung gekoppelt |
| REC-14 (Run-Provenance im Quorum) | [valid] | R2 `run_source ∈ {scheduled, push}` |
| REC-15 (@v1/Cohort Audit-Log) | [valid] | Cohort-Supportfenster (P0.5a); Audit im R2-Vertrag |

Quarantine-Lane (OOTB-Ansatz D der Review) als R2-Ergänzung übernommen. Kein REC als
`[missversteht-Kontext]`/`[out-of-scope]` verworfen — die Runde war durchweg additiv und
respektierte die „nicht neu aufrollen"-Liste.

### 11.1 Rückfluss externe Review-Runde 3 (Post-P0, Empfehlung „überarbeiten")

Die dritte Runde (gegen die Live-Implementierung verifiziert) empfahl statt Full-Acceptance einen
begrenzten Acceptance-Slice. Verdikte (intern gegen ADR + Code falsifiziert):

| REC | Verdikt | Aktion |
|---|---|---|
| REC-2 (stale Frontmatter) | [valid] | `implementation_status: none → in_progress`; Status-Tabelle phasenscharf |
| REC-1/20 (Acceptance-Grenze) | [valid] | §2.1 „Was Acceptance bedeutet / nicht" — Invariante+P0 entschieden, R2/R3-full/R5 gated |
| REC-3 (P0-End-Zustand fixieren) | [valid] | §2.1 + bestehender Changelog (Views = legitimer Endzustand, Read-API) |
| REC-8 (R2-Backend-Entscheidung erzwingen) | [valid] | §2.1: R2 bis Backend-Entscheidung nur Dry-Run/Plan |
| REC-5 (Kill-Gate nur per Amendment verlängerbar) | [valid] | §2.1 + §8-Verweis |
| REC-11/12/13 (Owner/Scope aus Generator-Code in Datenmodell) | [valid] | **Code-TODO** (separat): `enterprise_owners`/`repo_owner`-Literal in `tools/registry-canonical.py:82` → kanonisches `owner_team` bzw. Transition-Feld mit `expires_when` |
| REC-4 (CI-Guard gegen neue View-Direct-Reads) | [valid] | **Code-TODO** (separat) — Lint-Step |
| REC-9/REC-10 (Reconciler-Vertrag, Token-Scope) | [bereits vorhanden] | R2 „Mindestvertrag" (§2) deckt plan/apply/rollback/Audit/Token-Scope/Partial-Failure ab — nur präzisieren, kein Neu-Bau |
| REC-17/18 (Solo-Maintainer WIP-Limit) | [valid, Roadmap] | als Implementation-Plan-Disziplin, nicht ADR-bindend |
| REC-19 (Alt F bindendes R3-Cert) | [deferred] | bleibt „nicht verworfen", Entscheidung bei R3-full — kein Scope für Accept-now |

---

### 11.2 Amendment 2026-06-12 — P0-Restschuld: Neben-Wahrheiten der Verteilungs-Schicht

**Befund (Codebase-Analyse 2026-06-12, alle Pfade verifiziert):** P0 hat die *Registry*-Dual-SSoT
aufgelöst, aber die **Verteilungs-Schicht** hält drei weitere, hand-gepflegte Wahrheiten über die
Flotte, die nicht aus `canonical.yaml` gespeist werden:

1. **`registry/github_repos.yaml`** — von `scripts/sync-workflows.sh:95-97` ausdrücklich als
   „SSoT" für Repo-Typ-Kategorien (UNIVERSAL/DJANGO_HUB/PACKAGE) deklariert → vierte Quelle mit
   eigenem Typ-Vokabular neben `repo_type` in canonical.
2. **Hand-Arrays in `scripts/sync-repo.sh:75-97`** — `WSL_REPOS` (24 Repos) + `SERVER_APP_PATHS`
   (Kommentar: „Verified against live server **2026-03-05**" — 3 Monate stale). Neue Repos nehmen
   am 3-Node-Sync schlicht nicht teil; niemand merkt es (silent skip by design).
3. **Dual-Generator** `scripts/gen_project_facts.py` (11 KB, liest flat-View) vs.
   `scripts/generate_project_facts.py` (18 KB, GitHub-API + rich-View) — zwei Implementierungen
   erzeugen `project-facts` mit unterschiedlichen Input-Quellen und Defaults.

**Amendment-Entscheidung (P0-Schlussstein, gleiche Logik wie der Registry-Flip):**

- **A1 — canonical.yaml wird um Distributions-Felder erweitert** (`workflow_category`,
  `wsl_checkout: bool`, `server_compose_path`), `github_repos.yaml` wird **generierte View**
  (gleicher Mechanismus wie die beiden Alt-Registries: GENERATED-Header + Drift-Gate) oder retired,
  falls `repo_type` die Kategorien bereits deterministisch ableiten kann.
- **A2 — Shell-Verteiler lesen generierte Includes statt Hand-Arrays:** `registry_api.py` bekommt
  einen `emit --format bash`-Subcommand; `sync-repo.sh`/`sync-workflows.sh` sourcen das Artefakt.
  Hand-Edit am Array = CI-Fail (View-Reader-Guard-Erweiterung, REC-4-Muster).
- **A3 — genau ein project-facts-Generator:** `generate_project_facts.py` (API-vollständig) wird
  kanonisch, `gen_project_facts.py` → deprecation-Stub mit Forward-Call + Warnung, Entfernung nach
  30 Tagen. Aufrufer (session-start Phase 0.2, Workflows) werden im selben PR umgestellt.

**Nicht in Scope dieses Amendments:** Inhaltliche project-facts-Schema-Änderungen; die in §11.1
bereits getrackten Code-TODOs (REC-11/12/13) bleiben eigenständig.

**Validation:** Nach Umsetzung liefert
`grep -rn "WSL_REPOS=\|SERVER_APP_PATHS=" scripts/ --include="*.sh"` nur noch generierte
Include-Dateien; `github_repos.yaml` trägt GENERATED-Header; es existiert genau ein
project-facts-Generator-Entry-Point.

---

## 12. Changelog

- **2026-06-12:** **Amendment §11.2 — P0-Restschuld Verteilungs-Schicht** (Codebase-Analyse
  2026-06-12): `github_repos.yaml` als vierte Quelle, stale Hand-Arrays in `sync-repo.sh`
  (Stand 2026-03-05), Dual-Generator project-facts. Entscheidung A1–A3: Distributions-Felder in
  canonical, Shell-Verteiler lesen generierte Includes, ein kanonischer Generator. Status proposed
  bis PR-Merge.
- **2026-06-06:** **Accepted (phasenscharf).** Status `proposed → accepted`, `implementation_status
  none → in_progress`. §2.1 „Was Acceptance bedeutet / nicht" ergänzt (externe Review-Runde 3, REC-20):
  Invariante + SSoT + Digest-Provenance + frisches-Grün-Enforcement + Promote-Gate sind entschieden;
  R2-Backend (Alt E vs. Bot), R3-full-Breite, R5/Alt-F bleiben gated Roadmap. Falsifizierbarkeit über
  Kill-Gate §8 (nur per Amendment verlängerbar). Offene Code-TODOs aus Runde 3 (§11.1): Owner/Scope aus
  Generator-Literal ins Datenmodell (REC-11/12/13), CI-Guard gegen neue View-Direct-Reads (REC-4).
- **2026-06-01:** Initial (Proposed). Abgeleitet aus KONZ-platform-001 nach internem + externem
  Adversarial-Review; Provenance-Kette + Frische-Quorum + iil-Cohort als Primär-Hebel integriert.
- **2026-06-01:** Externe ADR-Review-Runde 2 eingearbeitet (15/15 RECs `[valid]`): Sequenz neu
  geschnitten (R3 früher, P0.5-Split), Schema/Waiver in P0 vorgezogen, Kill-Gate gestuft, Ledger als
  derived cache + repo-typisiert, R2-Mindestvertrag + quarantine-Lane, Alternativen E/F, R5 an
  Enforcement-Abdeckung gekoppelt. Step-5-Tag-Tabelle in §11.
- **2026-06-01:** P0 korrigiert nach Verlustfrei-Check (`tools/registry-consistency-check.py`): die zwei
  Registries sind **kein Superset** (flach 42 / reich 18, Schnitt 16, 26 nur-flach). „eine zur View der
  anderen" verworfen → **Union-Canonical** ist der einzige verlustfreie Weg. Nicht-brechender Erststep
  (Consistency-Check + informational CI) gebaut; Union-Migration bleibt das P0-Programm.
- **2026-06-01:** Union-Canonical **Schritt 1 bewiesen** (`tools/registry-canonical.py` + `registry/canonical.yaml`):
  Union aus beiden Altdateien (44 Repos, flat=42/rich=18); `verify` zeigt **beide Views regenerieren
  semantisch identisch** zu den Altdateien (round-trip exit 0) → Strategie verlustfrei belegt. **Noch
  nicht kanonisch geschaltet** — Altdateien + ~45 Konsumenten unverändert; flip-auf-generiert +
  Konsumenten-Migration sind die nächsten gegateten Schritte.
- **2026-06-01:** **Flip vollzogen** (`registry-canonical.py flip`): `registry/canonical.yaml` ist jetzt
  die **kanonische SSoT**; beide Altdateien sind **generierte Views** (GENERATED-Header; reicher
  Schema-Doc-Header verbatim erhalten). **Drift-Gate** (`registry-consistency.yml` → `verify`, hartes
  Fail) verhindert Divergenz. Sicherheits-Vorabcheck: **0 Text-grep-Konsumenten** (alle 25 yaml-parsen;
  klickdummy-host-`repos.yaml` ist ein anderes File) → semantisch verlustfrei. **Offen:** Konsumenten
  schrittweise auf `canonical.yaml` umziehen, dann Views retiren.
- **2026-06-01:** **P0 effektiv abgeschlossen.** Befund: **kein** Konsument liest beide Registries
  (8 nur flach, 10 nur reich) → eine Migration auf canonicals verschachteltes Schema wäre rein
  kosmetisch + netto-negativ (Mehr-Komplexität, kein funktionaler Gewinn). **Entscheidung: die
  generierten Views sind der legitime, divergenzsichere End-Zustand** (Read-API); bestehende Konsumenten
  bleiben unverändert. Für *neuen* Code: `tools/registry_api.py` (`flat()`/`rich()`/`repos()`/`repo()`,
  liest canonical; die Projektion-Logik `gen_flat`/`gen_rich` lebt dort und wird von der CLI/dem
  Drift-Gate importiert → eine Implementierung). View-Retire ist damit **nicht** erforderlich. Die
  Dual-SSoT (P0-Kernproblem) ist aufgelöst.
