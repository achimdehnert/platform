---
concept_id: KONZ-platform-001
title: Sauberer Repo-Zustand (CI-grün + deployfähig, Staging & Prod) als erzwungene Invariante statt laufendem Reparatur-Task
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []          # keine ADR-211-Spec; Bezug sind ADR-021/157/209/229/230 + /ci-green-program
adr_threshold: org-weiter ADR   # Cross-Repo, Reversal der Detect-Posture, neue Enforcement-Boundary, Reusable-Versionierungsstrategie
review_by: 2026-07-01
kill_criteria: "Wenn bis 2026-09-01 (a) die zwei Registries nicht zu EINER SSoT konsolidiert sind ODER (b) kein Branch-Protection-as-Code-Reconciler existiert, ist die 'Invariante' Theater → Konzept sunset, zurück auf reines /ci-green-program."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: .github/workflows/megatest.yml, commit_or_pr: "line 60", opened_in_session: true}
  - {claim_id: C2, source_path: .github/workflows/platform-audit.yml, commit_or_pr: "line 87", opened_in_session: true}
  - {claim_id: C3, source_path: .github/workflows/_ci-python.yml, commit_or_pr: "workflow_call line 11", opened_in_session: true}
  - {claim_id: C4, source_path: .github/workflows/pypi-ci-adoption-gate.yml, commit_or_pr: "lines 86-161", opened_in_session: true}
  - {claim_id: C5, source_path: scripts/ship.sh, commit_or_pr: "promote lines 119-124", opened_in_session: true}
  - {claim_id: C6, source_path: scripts/repo-registry.yaml, commit_or_pr: "line 2-3 'Single source of truth'", opened_in_session: true}
  - {claim_id: C7, source_path: registry/repos.yaml, commit_or_pr: "line 1 'Single Source of Truth'", opened_in_session: true}
  - {claim_id: C8, source_path: docs/adr/ADR-157-staging-production-split-and-port-governance.md, commit_or_pr: "lines 47/55 (4 von 22 Staging)", opened_in_session: true}
  - {claim_id: C9, source_path: docs/adr/ADR-209-policy-auto-sync-on-merge.md, commit_or_pr: "scope = policy-sync, NICHT CI-Health", opened_in_session: true}
  - {claim_id: C10, source_path: tests/megatest/budgets.toml, commit_or_pr: "Ratchet-Header + Nicht-Null-Budgets", opened_in_session: true}
  - {claim_id: C11, source_path: .github/workflows/sync-workflows-to-repos.yml, commit_or_pr: "PR #374 (in dieser Session entfernt)", opened_in_session: true}
  - {claim_id: E-ext1, source_path: ~/shared/konzept-clean-state-invariant-2026-06-01.md, commit_or_pr: "externe Zweitmeinung Runde 1 (E4) — additiv, kein Dissens", opened_in_session: true}
  # --- Amendment 2026-06-06 (agent-readiness-Session): R6/R7 + P0-Neuerdung ---
  - {claim_id: C12, source_path: registry/canonical.yaml, commit_or_pr: "0 liveness/owner-Felder; lifecycle/deployed vorhanden (ADR-234-SSoT)", opened_in_session: true}
  - {claim_id: C13, source_path: scripts/drift_check.py, commit_or_pr: "line 42 REGISTRY_FILE=scripts/repo-registry.yaml — NICHT canonical.yaml", opened_in_session: true}
  - {claim_id: C14, source_path: .github/workflows/runner-health.yml, commit_or_pr: "lines 160-173 Org-API ↔ github_repos.yaml, WARN-only, nur Runner-Repos", opened_in_session: true}
  - {claim_id: C15, source_path: tools/registry-consistency-check.py, commit_or_pr: "reconcilet flat↔rich INTERN, nicht gegen Org-Ground-Truth", opened_in_session: true}
  - {claim_id: C16, source_path: tools/cc-skill-dist/doctor.py, commit_or_pr: "PR #480 — F-A grüner Gate/0 Lane-Coverage; doctor-Tamper-Test = Injection-Muster", opened_in_session: true}
  - {claim_id: C17, source_path: "gh repo list (3 Orgs) + ls ~/github", commit_or_pr: "53 Org / 63 lokal / 77 project-facts / 3-4 Inventare — nicht reconciled", opened_in_session: true}
created: 2026-06-01
amended: 2026-06-06   # R6 Runtime-Reality-Probe + R7 Fault-Injection + P0-Neuerdung (canonical.yaml/ADR-234)
---

# KONZ-platform-001 — Sauberer Repo-Zustand als erzwungene Invariante

> **Tier T3.** Begründung (erster Satz, harte Auto-Eskalations-Trigger): org-weit über ~41 Repos,
> kehrt die heutige *Detect-and-file-issue*-Posture um, führt eine **neue Enforcement-Boundary**
> (Branch-Protection-as-Code) und eine **Reusable-Versionierungsstrategie** ein, verschiebt **SSoT**
> (zwei Registries → eine). Jeder einzelne dieser Trigger erzwingt mind. T2; die Summe ist T3.

---

## 1. Executive Summary

> **Amendment 2026-06-06 (agent-readiness-Session).** Drei native Ergänzungen, je belegt:
> **R6 Runtime-Reality-Probe** (deklariert `lifecycle` ↔ live geprobte Prod-Realität — der discord-Quadrant,
> heute ungeschlossen, da P0 nur `gh repo list`-*Existenz* ableitet, keine Laufzeit) · **R7 beweisbar-echte
> Gates** (Fault-Injection; Live-Beleg F-A/PR #480: grüner Gate mit 0 Lane-Coverage) · **P0-Neuerdung**
> (post-ADR-234 sind es 3–4 Inventare, nicht 2; Ziel-SSoT = `canonical.yaml`). Telos „stärkeres Modell
> in ~2 Mon." ist **Dringlichkeits-**, kein **Design-Treiber** — es erhöht *nur* die Priorität von R6
> (Modell hat kein Out-of-Band-Gedächtnis). Kill-Gate um (c)/(d)/(e) erweitert; Risiken R-7/R-8/R-9.
> *Diff zum 2026-06-01-Stand: §5 R6/R7 + P0-Absatz, §11 R-7..R-9, §13 Kill-Gate c–e + Teil-Sunset.*

**Ziel (vom Auftraggeber):** ein *laufender Task*, der sicherstellt, dass alle Repos in Staging
**und** Prod CI-grün/deployfähig werden und es **bleiben** — evidenzbasiert, auf festen Regeln,
Ausnahmen minimal; wo eine wiederkehrende **Abfolge** durch eine **Regel** ersetzt werden kann,
priorisiert.

**Kernbefund nach Erdung + adversarialem Dreifach-Review:** Die richtige Antwort ist **kein
laufender Reparatur-Task**. Die `/ci-green-program`-Skill formuliert es selbst: „Jede manuelle
Per-Repo-Reparatur ist ein Eingeständnis, dass die geteilte Quelle eine Klasse nicht verhindert.
Ziel ist, den Loop **abzuschaffen**." Das deckt sich exakt mit der Auftrags-Anweisung
„Abfolge → durch Regel ersetzen". Ein Task, der wiederholt fragt „ist es noch sauber?", behandelt
Sauberkeit als *Bestand*; eine Invariante macht den unsauberen Zustand zu einem *nicht erreichbaren*.

**Aber:** Die naive Invarianten-These („mach alle Checks merge-blockend, deploye promote-only")
ist im Adversariat **an drei Stellen tödlich gescheitert** und musste umgebaut werden:

1. **Petitio principii (R2):** ~34/57 Repos sind heute rot — und zwar wegen *echten*
   Engineering-Schulden (iil-*-Dependency/Version-Drift + reale Testfehler), nicht wegen fehlender
   Regeln (`project_f4_ci_green_program`). Rote Checks *jetzt* merge-blockend zu schalten friert
   die Flotte ein und erzeugt Druck, Gates zu senken (Goodhart).
2. **Enforcement-Fiktion (R2/R3):** Für die beiden „Erzwingungs"-Regeln existiert **kein
   Erzwingungs-Mechanismus** — Branch-Protection ist ein per-Repo-GitHub-Setting (kein Code, kein
   Reconciler, andere Orgs unerreichbar); `ship.sh promote` prüft nur *Existenz* eines
   `:staging`-Images, **nie ob es grün war** (C5).
3. **Versteckte Doppelquelle:** Es gibt **zwei** Dateien, die *beide* „Single Source of Truth"
   beanspruchen (C6, C7). Jede Adoptions-/Live-Repo-Messung erbt diese Ambiguität.

**Empfohlene Synthese:** *Green by construction — aber Enforcement **folgt** dem Grün-Zustand pro
Repo, erzwingt ihn nie voraus.* Sechs Bausteine in **zwingender Reihenfolge** (P0 zuerst), von
denen ~80 % bereits als optionale/informationelle Infrastruktur existieren und nur **verbindlich +
verhindernd** gemacht werden müssen.

**Nachschärfung durch externe Zweitmeinung (Runde 1, 2026-06-01 — §6b):** Die Richtung wurde
bestätigt, aber an zwei Stellen als *zu repo-zentriert* korrigiert. (i) **Die kleinste Einheit der
Invariante ist falsch:** nicht „Repo ist grün", sondern eine **beweisbare Kette**
`repo@sha → artifact@digest → staging-health → prod`. Ein `:staging`-*Tag* ist überschreibbar — ohne
Digest-/Commit-Bindung kann ein später überschriebenes Image fälschlich als „grün" promotet werden
(verschärft E3). (ii) **„grün-30d" muss Frische-Evidenz sein, nicht passive Zeit:** ein Repo kann
30 Tage grün *aussehen*, ohne dass je ein frischer CI-Lauf gegen die *aktuelle* Dependency-Auflösung
lief. Daraus folgt der neue Baustein **P0.5 (Cleanliness Ledger + iil-Dependency-Cohort)** und die
Erkenntnis, dass **Dependency-Kohärenz** (E6) der eigentliche Primär-Hebel ist — sonst härtet die
Invariante nur die ohnehin gesunden Repos und lässt die rote Mehrheit außerhalb.

---

## 2. Scope & Evidenzbasis

**In Scope:** alle Repos der Org `achimdehnert` mit echtem origin; explizit *nur defensiv* für
`ttz-lif`/`meiki-lra` (andere Orgs — Settings von hier nicht erreichbar, Daten-Sovereignty).

**Evidenz-Ehrlichkeit:** Belege C1–C11 wurden in dieser Session geöffnet (selbst oder durch
delegierte Lese-Agenten; Provenienz im Manifest). Zeilennummern aus delegiertem Read sind als
solche gekennzeichnet. Alles ohne Beleg ist als **Hypothese (H)** markiert.

**Verifizierte Grundlage (E2/E3):**
- Detektoren werfen ihren eigenen Befund weg: `megatest.yml:60` und `platform-audit.yml:87`
  fangen den Exit-Code ein und setzen `continue-on-error: true` (C1, C2).
- Reusable-CI existiert (`_ci-python.yml` `workflow_call`, C3) und der **abgeleitete-Meter-
  Präzedenzfall** ist real und schließt sein eigenes Tracking-Issue bei Vollabdeckung
  (`pypi-ci-adoption-gate.yml:86-161`, C4).
- `ship.sh` hat einen `promote`-Modus, der `:staging` → `:latest` retaggt — Vorbedingung ist nur
  *Existenz*, kein Grün-Status (C5).
- Doppel-SSoT: `scripts/repo-registry.yaml` (C6) und `registry/repos.yaml` (C7).
- ADR-157: nur **4 von 22** Hubs hatten Staging-Ports (C8) → R3 betrifft heute eine Minderheit.
- ADR-209 ist **policy-auto-sync**, *nicht* CI-Health-Governance (C9) — verbreitetes Fehl-Label.

**Hypothesen (H), billigster Check benannt:**
- (H1) Branch-Protection-Status der 41 Default-Branches — Check: `gh api repos/{o}/{r}/branches/main/protection`.
- (H2) R5-Exit-Kriterium braucht eine Red-Rate-Zeitreihe, die heute nirgends erhoben wird —
  der Adoption-Gate misst nur Adoptions-%, nicht Röte über 30 Tage.

---

## 3. Infrastruktur-Fit (ADR-konform)

| Baustein | Existierende ADR/Infra | Fit |
|---|---|---|
| R1 Reusable-Konvergenz | ADR-021 (unified deployment, `_ci-*.yml`), ADR-058 (Test-Taxonomie) | direkt; ist bereits die ADR-021-Soll-Architektur |
| R2 Enforcement | — (Lücke: kein Branch-Protection-as-Code) | **neue Boundary → ADR-pflichtig** |
| R3 Promote-Gate | ADR-021 Deploy-Pattern, ADR-157 Staging-Split, Memory `ADR-210` (Gate unmittelbar vor irreversibler Aktion) | Idee ADR-gedeckt; Implementierung fehlt im Code |
| R4 Waiver | `/ci-green-program` Phase 4 (`docs/ci-waivers.md`) | Konzept existiert, Datei nicht |
| R5 Meter | `pypi-ci-adoption-gate.yml` (Muster), ADR-226 Adoption-Gate | direkt ableitbar |
| P0 Registry-Konsolidierung | ADR-022 (repo_checker liest `registry/repos.yaml`) | Reversal/Merge → ADR-pflichtig |

**Governance:** Das Programm läuft unter `/ci-green-program` (Selbst-Exit-Kriterium dort bereits
definiert). Die *neuen Entscheidungen* (Enforcement-Boundary, Reusable-Versionierung,
Registry-SSoT) brauchen einen **org-weiten ADR** bzw. Amendments an ADR-021/157 — **nicht** ADR-209
(das ist policy-sync, C9).

---

## 4. Steelman (stärkste Form der These)

Die Regeln erfinden nichts — sie schließen Lücken an bereits gebauten Stümpfen. Der Implementierungs-
Delta ist klein, das Verhaltens-Delta total. **„Regel statt Abfolge" ist strukturell überlegen, weil
die heutigen Detektoren ihren eigenen Befund wegwerfen** (`continue-on-error`, C1/C2): ein offener
Regelkreis ohne Aktor. Eine Invariante hat keinen „Stand", den ein Task pflegen müsste — sie ist
wahr, oder der Merge/Promote passiert nicht. Der **abgeleitete Meter** (C4) kann nicht stale werden,
weil er GitHubs Wahrheit liest statt eigenen State zu halten — und schließt sich selbst (echte
Selbstabschaltung, kein Zombie). Der entscheidende Einzelhebel im Steelman: das Gate **unmittelbar
vor die irreversible Aktion** setzen (Memory `ADR-210`-Lehre) — bei R3 also „Prod kann nur
Staging-Bytes empfangen", nicht „CI irgendwo grün".

**Was davon überlebt:** R1 (deterministische Prävention) und R5 (abgeleiteter Meter) sind im Kern
gesund. Die Promote-*Idee* ist richtig verortet. Das Steelman irrt nur in einem Punkt — es liest
in `ship.sh:124` ein Grün-Gate hinein, das dort nicht steht (siehe §6).

---

## 5. Konzeptdefinition — die Bausteine (revidiert, in zwingender Reihenfolge; R6/R7 = Amendment 2026-06-06)

> **Leitsatz:** *Green by construction; Enforcement folgt dem Grün-Zustand pro Repo, erzwingt ihn nie voraus.*

**P0 — Registry-Konsolidierung (versteckte Vorbedingung, zuerst).**
Zwei „SSoT"-Registries (C6/C7) → **eine**. Felder mind.: `type`, `lifecycle: live|maintenance|dead`,
`staging:{…}|null`, `deploy:{…}`, `waiver:[{gate, reason, expires}]`. Die **Live-Repo-Liste wird
NICHT aus der Hand-Liste**, sondern aus `gh repo list` abgeleitet und gegen die Registry abgeglichen
(schließt das „Meter wird blind"-Loch, §6/Maintainer-Pfad 2). Ohne P0 erben R1/R2/R5 die Ambiguität.
*P0-Neuerdung (Amendment 2026-06-06):* Seit **ADR-234** (gemergt 2026-06-05) existiert `registry/canonical.yaml`
als *generierte* SSoT (`tools/registry-canonical.py flip` → `scripts/repo-registry.yaml`). Aus „zwei
Registries (C6/C7)" sind damit **drei–vier** geworden: `canonical.yaml` (neu) · `scripts/repo-registry.yaml`
(generiert) · `registry/repos.yaml` · `registry/github_repos.yaml` (manuell, von `runner-health.yml` als
Org-Abgleich genutzt). Verschärfung statt Entlastung — verifiziert: `drift_check.py` liest
`repo-registry.yaml`, `runner-health.yml` liest `github_repos.yaml`: **zwei Reconciler gegen zwei
verschiedene Inventare**. P0-Ziel neu geerdet → Konsolidierungs-**Ziel-SSoT = `canonical.yaml`**;
`github_repos.yaml`+`repos.yaml` falten hinein; `registry_coverage_drift` (R5) und der R2b-Reconciler lesen
**ausschließlich** `canonical.yaml`.

**P0.5 — Cleanliness Ledger + iil-Dependency-Cohort (neu, externe Runde 1; vor R1).**
Ohne ein maschinenlesbares, *abgeleitetes* Ledger prüfen R2 und R3 **verschiedene Wahrheiten**. Das
Ledger bindet pro Repo die ganze Beweis-Kette zusammen (nicht persistierter State — aus GitHub +
Registry abgeleitet):
```yaml
clean_state:
  repo: achimdehnert/<name>
  default_branch_sha: "<sha>"
  workflow_ref: "platform/.github/workflows/_ci-python.yml@v1.2.3"
  constraints_sha256: "<sha>"          # welcher iil-*-Cohort wurde aufgelöst
  last_default_branch_green_at: "..."
  green_runs_30d: 4                    # Frische-Quorum, nicht passive Zeit
  required_eligible_since: "..."
  artifact_digest: "sha256:..."        # NICHT das :staging-Tag — der Digest
  staging_health_run_id: "..."
  staging_health_digest: "sha256:..."  # muss == artifact_digest sein
  prod_promotable: true
  active_waivers: []
```
Dazu ein **SSoT für interne Dependencies** — `constraints/iil-cohort-<YYYY.MM>.txt` (zentral
erzeugt/owned). Begründung: E6 sagt, die rote Mehrheit hängt an iil-*-Dependency-Drift, **nicht** an
fehlenden Regeln. Ohne Cohort-Constraints härtet R2 nur die ohnehin gesunden Repos. Dependency-
Kohärenz ist damit **Primär-Hebel**, nicht späteres Nice-to-have.

**R1 — Konvergenz auf shared reusable Workflows (deterministisch).**
Jedes `live`-Repo konsumiert `_ci-python.yml`/`_ci-pypi.yml`/`_ci-odoo.yml` via `uses:`. **Pin via
gerolltem `@v1`-Major-Tag**, **nicht `@main`** (sonst async-unsichtbarer Flottenbruch — Maintainer-
Pfad 1; heute durchweg `@main`). **Verteilung NICHT per 40 blinden Bump-PRs** (externe Runde),
sondern **Canary-Ringe + Consumer-Contract-Test** (§6b/AD-E3): `@v1-candidate` läuft gegen eine
Consumer-Matrix → Ring 0 (3 Repos) → Ring 1 (10) → Flotte; erst nach grünem Ring wird `@v1` bewegt.
Menschliches Review nur bei Contract-Bruch. Reusable-Workflows müssen den **aktuellen Cohort-
Constraint** (P0.5) nutzen oder im Ledger als abweichend markiert sein. Versionierungsstrategie
ADR-pflichtig.

**R2 — Enforcement folgt *frischem* Grün, pro Repo (umgebaut; NICHT Flotten-Schalter, NICHT passive Zeit).**
(a) `continue-on-error` aus den Detektoren entfernen (billig, sofort) — macht Röte *sichtbar*. (b) Ein
**Branch-Protection-as-Code-Reconciler** (neu — existiert nicht) setzt den shared-CI-Check pro Repo
**erst dann** als `required`, wenn ein **Frische-Quorum** erfüllt ist (externe Runde, AD-E2):
≥4 erfolgreiche Default-Branch-Läufe/30 Tage, **letzter <7 Tage alt**, auf aktuellem Default-Branch-
SHA **und aktuellem iil-*-Constraint-Snapshot**, keine aktiven Waiver, Repo nicht `sunset`, Owner
gesetzt. **Bewusst KEIN „≥N Merges"-Kriterium** — das erzeugt Dummy-Merge-/Activity-Theater. *Required
folgt verdientem, frischem Grün, statt es zu erzwingen.* Kein rotes Repo wird eingefroren.

**R3 — Promote-Gate als Code, DIGEST-gebunden (umgebaut; harter Prüfpunkt externe Runde).**
`ship.sh promote` darf **nicht** abstrakt „Staging grün" prüfen und **nicht** ein `:staging`-*Tag*
retaggen (Tags sind überschreibbar → ein später überschriebenes Image gilt fälschlich als grün,
verschärft C5/E3). Statt dessen: promote **exakt denselben `artifact_digest`**, für den im Ledger
(P0.5) CI-green **und** staging-health-green mit *demselben* Digest belegt sind. Damit ist
`Prod ⊆ grün-Staging` eine **beweisbare** Provenance-Kette, nicht eine Tag-Konvention. Gilt nur für
Repos mit gebautem Staging (heute 3–4, C8) → Staging-Rollout = explizite Vorbedingung.
**Hotfix (externe Runde):** der Waiver *umgeht das Gate nicht*, er *beschleunigt den Pfad* — Hotfix
baut einen unveränderlichen Digest → ephemere Emergency-Staging → reduziertes P0/P1-Health-Gate →
promotet **denselben** Digest. Nur Break-Glass darf Prod vorziehen; dann greift ein **automatischer
Incident-Freeze** (keine weiteren Promotes), bis derselbe Digest nachträglich in Staging validiert
*oder* zurückgerollt ist.

**R4 — Ausnahmen als Registry-Feld (kein drittes File).**
Waiver leben als `waiver:[{gate, reason, expires}]` **in der konsolidierten Registry** (P0), nicht in
einer separaten `docs/ci-waivers.md` (existiert nicht; wäre nur `continue-on-error` umbenannt).
Meter (R5) und Required-Logik (R2) lesen **dieselbe** Quelle; Ablauf maschinell.

**R5 — dünner Rest-Task: Event-Handler + abgeleiteter Meter (ehrlicher Nenner).**
Einziger verbleibender *laufender* Anteil. Event-Handler für `UNKNOWN`/neuartige Fehler
(`/ci-green-program` Phase 3); Adoption-Meter abgeleitet aus GitHub (Muster C4), **Nenner =
`gh repo list` live**, nicht Hand-Liste. Plus zwei Frühwarn-Metriken (§11). Selbst-abschaltend per
`/ci-green-program`-Exit (≥90 % Adoption ∧ <10 % Red-Rate/30d) — *nur ehrlich mit echtem Nenner*.

**R6 — Runtime-Reality-Probe (deklariert ≠ läuft; der discord-Quadrant). [Amendment 2026-06-06]**
P0 leitet die *Existenz*-Liste aus `gh repo list` ab (schließt Enrollment) — aber **nichts probt die
Prod-Laufzeit gegen die `lifecycle`-Deklaration**. Lücke: ein `lifecycle: dead|maintenance`-Repo, dessen
Container auf Prod weiterläuft (Präzedenz: der discord-bot crash-loopte wochenlang, Repo war clean —
Drift-Memory `repo-clean ≠ prod-clean`), oder ein `lifecycle: live`, dessen Prod-Endpoint still tot ist.
R6 fügt dem P0.5-Ledger eine **beobachtete** (nicht deklarierte) Dimension hinzu: täglicher Probe-Job
liest `deploy:{prod_url, health}` der konsolidierten Registry, macht HTTP-GET (`/livez/`) **und**
Container-Presence (`docker ps` über den deploy-Pfad), schreibt `prod_runtime_observed` ins Ledger und
**flaggt jeden Widerspruch** `lifecycle` ↔ `prod_runtime_observed` als blockierenden Issue. **Bewusst KEIN
neues Deklarativ-Feld** — das wäre eine dritte Wahrheit neben `lifecycle`/`deploy` und verrottet genau wie
sie es beim discord-Bot tat; `prod_runtime_observed` ist *gemessen* und nur *gegen* die Deklaration wertvoll.
Eskalation über R5. *Modell-Relevanz:* ein übernehmendes Modell hat **kein Out-of-Band-Gedächtnis**
(„ich weiß, dass wir das abschalteten") → R6 ist der einzige Baustein, dessen Priorität sich aus dem
Agent-Readiness-Telos *erhöht*; die übrigen gälten für einen Menschen identisch.

**R7 — Beweisbar-echte Gates (Fault-Injection; kein No-Op-Gate). [Amendment 2026-06-06]**
Jedes *erzwingende* Gate dieser Kette (R2b-Reconciler, R3-Promote-Gate, R6-Probe, `registry_coverage_drift`,
Cohort-Constraint-Gate) trägt einen **Fault-Injection-Test**: injiziere den bekannten Defekt → das Gate
**muss** failen. Ein Gate, das für seine Defektklasse noch nie rot war, ist No-Op-verdächtig. **Live-Beleg
(2026-06-05):** der `cc-skill-dist-doctor`-Gate war grün und testete eine ganze Lane mit **0 Coverage**
(PR #480, Befund F-A) — ein grüner Gate-*Name* ohne Garantie. Das Muster existiert bereits produktiv: der
`doctor.py`-Tamper-Test (PR #480) injiziert eine manipulierte Kopie und erzwingt Drift>0. R7 generalisiert
es: **kein Gate wird `required` (R2b/R3), bevor sein Fault-Injection-Test grün ist** — sonst verlagert die
„Invariante" das Vertrauen nur auf einen ungeprüften Prüfer (R-2 auf der Meta-Ebene). R7 ist die
Vorbedingung, die R2/R3 überhaupt *vertrauenswürdig* macht.

---

## 6. Adversariale Analyse (die drei tödlichen Treffer + Auflösung)

**AD-1 (KRITISCH) — R2 als Sofort-Schalter ist Petitio principii + Goodhart-Generator.**
Beleg: `project_f4_ci_green_program` (verifiziert) — „CI grün flottenweit ist KEIN mechanisches
Sweep-Problem". Rote Checks jetzt merge-blockend = ~34 Repos eingefroren an echten Engineering-
Fehlern → Umgehungsdruck (Gate senken, Check umbenennen, Admin-Merge).
**Auflösung:** R2 umgebaut zu „required folgt Grün-30d pro Repo" (§5). Eine Invariante auf einem
Zustand zu *erzwingen*, der sie massenhaft verletzt, ist kein Enforcement, sondern ein Freeze.

**AD-2 (KRITISCH) — R2/R3 haben heute NULL Enforcement-Maschinerie.**
Beleg: Repo-weite Suche nach `required_status_checks`/`branch.protection` → kein Reconciler/Audit.
Branch-Protection ist per-Repo-Setting, Admin-bypassbar, andere Orgs unerreichbar.
**Auflösung:** Branch-Protection-as-Code-Reconciler ist ein **explizites P-Item vor R2** (und Teil
des Kill-Gates). Ohne ihn ist R2 ersatzlos zu streichen, weil nicht erzwingbar/auditierbar.

**AD-3 (HOCH) — R3 ist Namens-Konvention, kein Gate; für 85 % nicht anwendbar.**
Beleg: `ship.sh:119-124` prüft nur Image-*Existenz* (C5); ADR-157: 18/22 ohne Staging (C8).
**Auflösung:** Promote-Gate als Code + Staging-Rollout als Vorbedingung (§5, R3).

**AD-4 (Scheinkonkretheit) — `docs/ci-waivers.md` existiert nicht; ablaufender Waiver =
`continue-on-error` umbenannt.** **Auflösung:** Waiver als Registry-Feld (R4).

**AD-5 (Doppelquelle) — die These baut auf zwei „SSoT"-Registries auf.** **Auflösung:** P0 zuerst.

**Maintainer-2028-Verrottungspfade (Prognose, belegt):**
(P1) `@main`-Pin überall → async-unsichtbarer Flottenbruch → Reusables werden „darf-man-nicht-
anfassen"-Zone. (P2) `budgets.toml`-Ratchet (C10) wird per `--update-budgets` hochgesetzt =
permanenter Waiver ohne `expires`; Meter scannt nur die Schnittmenge dreier Hand-Listen → wird
blind für neue Repos. (P3) „selbst-abschaltender" Meter wird Zombie wie `sync-workflows-to-repos.yml`
(„retire pending", war nie gelöscht — bis **PR #374 in dieser Session**, C11: der Mechanismus ist
real, aber adressierbar).

---

## 6b. Externe Zweitmeinung (Runde 1, 2026-06-01) — neue blinde Flecken

Briefing: `~/shared/konzept-clean-state-invariant-2026-06-01.md`. Auftrag war explizit „neue blinde
Flecken statt Wiederholung interner Treffer". Zwei Einwände, die das interne Adversariat **übersah**:

**AD-E1 (KRITISCH) — „Clean repo state" ist die falsche kleinste Einheit.**
R2 macht Branch-Protection grün, R3 macht das Promote-Gate grün — aber das Konzept *verband diese
Zustände nicht zu einer beweisbaren Kette*. Schadensszenario: main grün bei Commit A, Staging zeigt
Digest B, ein Hotfix baut Digest C, Prod bekommt per Retag *irgendeinen* davon — alle Einzelregeln
formal grün, die Invariante „Prod stammt aus sauberem Staging" trotzdem **nicht bewiesen**. Das ist
mehr als der bekannte `ship.sh`-Existenz-Bug (E3): selbst mit „Staging-grün"-Prüfung fehlt das
**Artifact-Provenance-Modell** (Digest-/Commit-Bindung). → **Auflösung:** Invariante umdefiniert auf
`repo@sha → artifact@digest → staging-health → prod`; R3 digest-gebunden; P0.5-Ledger bindet die Kette.

**AD-E2 (HOCH) — „grün-30d" ist Goodhart-anfällig, aber anders als intern vermutet.**
Nicht wegen fehlender Merges (≥N-Merges würde *neues* Theater erzeugen), sondern wegen **fehlender
Frische-/Dependency-Evidenz**: ein Repo kann 30 Tage grün *aussehen*, ohne je frisch gegen die
aktuelle Dependency-Auflösung gelaufen zu sein. → **Auflösung:** R2 auf Frische-Quorum umgestellt
(≥4 Läufe/30d, letzter <7d, aktueller SHA + Constraint-Snapshot), kein Merge-Kriterium.

**Bestätigt + verschärft:** E6 (Dependency-Drift) ist laut externer Runde der **eigentliche Primär-
Hebel**, nicht ein späteres Item — ohne iil-Cohort-Constraints härtet die Invariante nur die
Gewinner-Repos. → P0.5 eingeführt; OOTB `iil-distribution` (§9) als Pilot empfohlen.

**Konfliktmatrix Runde 1:** Es gab **keinen Dissens** zwischen externem und internem Review — die
externe Runde war rein *additiv* (Provenance-Kette, Frische-Quorum, Dependency-als-Primär-Hebel,
Canary-Ringe, Hotfix-ohne-Bypass). Die interne Synthese-Richtung wurde ausdrücklich bestätigt
(„Überarbeiten, aber Richtung beibehalten").

---

## 7. Deep-Dive: warum „Regel" hier konkret eine „Abfolge" ersetzt

Konkrete Abfolge heute (Beispiel, belegt): `platform-audit.yml` (cron) detektiert fehlendes
Scaffold → `continue-on-error: true` (C2) → grüner Job trotz rotem Report → Issue wird erstellt →
Mensch sieht Issue → Mensch fixt → nächster Drift schleicht rein, weil **nichts den Merge hindert**.
Das ist die „Abfolge", die der Auftrag durch eine „Regel" ersetzt sehen will.

Die Regel-Form: Sobald ein Repo R1+grün-30d erfüllt, ist sein shared-Check `required` (R2b) →
der Drift *kann nicht mehr mergen* → keine Detektion-Issue-Fix-Abfolge nötig. Die Abfolge entfällt
**für jedes Repo ab dem Moment, in dem es den Zustand verdient hat** — graduell, nicht per Dekret.

---

## 8. Alternativen

| # | Alternative | Pro | Contra | Verdikt |
|---|---|---|---|---|
| A | **Status quo** (Detektoren + manuelle `/ci-green-program`-Wellen) | existiert, kein Umbau | offener Regelkreis; Drift kehrt zurück (Sisyphos) | verworfen — der Auftrag will genau das ersetzen |
| B | **Naive Invariante** (alle Checks sofort required, promote-only by Konvention) | konzeptuell sauber | AD-1/2/3 tödlich; friert Flotte ein, kein Enforcement-Code | verworfen |
| C | **Synthese (dieses Konzept)** — Enforcement folgt Grün pro Repo, P0 zuerst, Gates als Code | adressiert alle Treffer; graduell; deterministisch | mehr Vorarbeit (P0 + Reconciler); langsamer | **empfohlen** |
| D | **Nur P0+R1+R5** (Konvergenz + Meter, kein Enforcement) | minimal-invasiv, kein Freeze-Risiko | „bleibt grün" nicht garantiert — nur gemessen | Fallback, falls Reconciler scheitert (= Kill-Gate-Ausgang) |

---

## 9. Out-of-the-Box

1. **Required folgt Grün, nicht umgekehrt** — die zentrale Inversion: Enforcement als *Funktion des
   gemessenen Zustands*, nicht als Vorbedingung. Löst AD-1 strukturell.
2. **Prod als reine Projektion von Staging** — kein eigener Prod-Build-Pfad; Prod ist
   definitionsgemäß ein retaggtes grün-Staging-Image. „Staging+Prod sauber" wird Konstruktion,
   nicht Prüfziel — *sobald* das Promote-Gate Code ist (R3).
3. **Der Meter misst seinen eigenen Nenner** (`registry_coverage_drift`, §11) — Frühwarnung gegen
   „Meter wird blind", bevor es weh tut.
4. **Threshold-Check-Bot statt Selbsteinstufung** (aus konzept-Skill Backlog OOTB-5): künftig
   könnte ein Bot prüfen, ob ein Repo R1 nur *formal* (mit `skip_tests:true`/`coverage:0`) erfüllt
   — formale Adoption ≠ echte. Backlog.
5. **Self-Termination als Exit-Code, nicht als Vorsatz** — der Meter schließt sein Issue bei
   Vollabdeckung (C4-Muster); das Programm endet maschinell, nicht per Mensch-Entscheidung.
6. **`iil-distribution` — Release-Train statt repo-weisem Dependency-Heilen (externe Runde, P0.5-Pilot).**
   Behandle die iil-*-Libraries wie eine **Distribution**: ein Meta-Repo erzeugt ereignis-/monatsbasierte
   **Cohort-Releases** (`iil-dist-2026.06.1`) mit `constraints.txt`, SBOM, getesteter Library-Kombination,
   Consumer-Matrix-Ergebnis und signiertem Artefakt. Hubs pinnen **eine Distribution**, nicht einzelne
   iil-*-Versionen. Vorteil: der teuerste Drift-Treiber (E6) wird an der **Quelle** kontrolliert; R1/R2/R3
   bekommen einen beweisbaren Dependency-Kontext. Nachteil: mehr Release-Disziplin, eine kaputte zentrale
   Distribution kann viele Repos blocken → **Pilot mit 3 Hubs + den wichtigsten iil-*-Libraries**, nicht
   Big-Bang.

---

## 10. Befunde (verdichtet)

| ID | Befund | Schwere | Beleg |
|---|---|---|---|
| B1 | Detektoren werfen Exit-Code weg (`continue-on-error`) | hoch | C1, C2 |
| B2 | Kein Branch-Protection-as-Code/-Audit existiert | kritisch | Repo-Suche (H1-Check offen) |
| B3 | `ship.sh promote` prüft Existenz, nicht Grün | hoch | C5 |
| B4 | Zwei konkurrierende „SSoT"-Registries | hoch | C6, C7 |
| B5 | Staging existiert für ~4/22 Repos | hoch | C8 |
| B6 | Reusables durchweg `@main`-gepinnt | mittel | Maintainer-Agent (Pfad 1) |
| B7 | `budgets.toml`-Ratchet per `--update-budgets` umgehbar | mittel | C10 |
| B8 | ADR-209 ≠ CI-Health (Fehl-Label im Memory) | niedrig | C9 |

---

## 11. Top-5-Risiken

| # | Risiko | Wahrsch. | Wirkung | Gegenmaßnahme |
|---|---|---|---|---|
| R-1 | R2 friert rote Repos ein (Goodhart) | hoch ohne Umbau | Dev-Freeze, Gate-Erosion | „required folgt Grün-30d" (R2b); nie Flotten-Schalter |
| R-2 | Branch-Protection driftet (kein Reconciler) | hoch | „Invariante" ist Default das driftet | Reconciler als P-Item; Kill-Gate koppelt daran |
| R-3 | `@main`-Bruch trifft Flotte unsichtbar | mittel-hoch | 40 Repos rot ohne Diff | `@v1`-Tag + Renovate-Bump-PRs (R1) |
| R-4 | Waiver werden de-facto permanent | mittel | `continue-on-error` durch Hintertür | `expires` maschinell vom Meter gelesen; `budget_sum_trend`-Alarm |
| R-5 | Meter wird blind (Hand-Listen-Nenner) | mittel | „95 % grün" ist Fiktion | Nenner = `gh repo list`; `registry_coverage_drift`-Frühwarnung |
| R-6 | Überschriebenes `:staging`-Tag wird fälschlich als „grün" promotet (Provenance-Lücke) | hoch | „Prod aus sauberem Staging" formal grün, real unbewiesen | R3 digest-gebunden; Ledger erzwingt `artifact_digest == staging_health_digest` (externe Runde AD-E1) |
| R-7 | Erzwingendes Gate ist No-Op (nie für seine Defektklasse rot) | hoch | „Invariante" vertraut ungeprüftem Prüfer | **R7** Fault-Injection-Test grün als Vorbedingung für `required` (Live-Beleg F-A, PR #480) |
| R-8 | `lifecycle` deklariert ≠ Prod-Laufzeit (discord-Quadrant) | mittel-hoch | totes Repo crash-loopt unsichtbar auf Prod | **R6** `prod_runtime_observed`-Probe widerspricht der Deklaration; Eskalation über R5 |
| R-9 | `canonical.yaml` ↔ `github_repos.yaml`/`repos.yaml` driften (Multi-Inventar post-ADR-234) | mittel | zwei Reconciler, zwei Wahrheiten (heute real) | **P0-Neuerdung** — ein Ziel-SSoT `canonical.yaml`, alle Reconciler lesen nur diese |

**Frühwarn-Metriken (deterministisch, kein LLM — konform `feedback_repo_health_rule_discipline`):**
- `registry_coverage_drift` = |org-live-repos (gh)| − |konsolidierte-Registry ∩ live|; `>0 für >7 Tage` → blockierender Issue.
- `budget_sum_trend` = Σ `budgets.toml`; **darf nur fallen**; jeder Monatsanstieg = `--update-budgets`-Missbrauch, an einem Skalar ablesbar.

---

## 12. Empfehlungen (konkret, verifizierbar — keine generischen Recs)

1. **P0 zuerst:** `scripts/repo-registry.yaml` + `registry/repos.yaml` zu **einer** Datei mergen;
   Felder `lifecycle`, `staging`, `waiver[]` ergänzen; Live-Liste aus `gh repo list` ableiten.
   *Verifizierbar:* nach Merge existiert genau eine Datei mit `# Single Source of Truth`.
1b. **P0.5 (Primär-Hebel, externe Runde):** `constraints/iil-cohort-<YYYY.MM>.txt` zentral erzeugen
   + ein abgeleitetes `clean_state`-Ledger (§5) pro Repo aus GitHub+Registry generieren.
   *Verifizierbar:* Ledger enthält pro Repo `artifact_digest` == `staging_health_digest` oder `prod_promotable:false`.
2. **R2a (billig, sofort):** `continue-on-error: true` aus `megatest.yml:60` und
   `platform-audit.yml:87` entfernen — Röte wird sichtbar (noch nicht blockierend).
3. **R2b (das eigentliche Werk):** `tools/branch-protection-reconciler.py` bauen, das pro `live`-Repo
   den shared-CI-Check als `required` setzt **gdw. Frische-Quorum** (≥4 Läufe/30d, letzter <7d, aktueller
   SHA + Constraint-Snapshot, keine Waiver, nicht sunset) — inkl. Drift-Audit (`gh api …/protection`).
4. **R3 (digest-gebunden):** `ship.sh promote` so umbauen, dass es **denselben `artifact_digest`**
   promotet, für den das Ledger CI-green + staging-health-green belegt — **kein Retag eines `:staging`-Tags**
   (überschreibbar). Hotfix = Beschleunigung über ephemere Emergency-Staging mit demselben Digest, kein Gate-Bypass.
5. **R1:** gerollten `@v1`-Tag auf `_ci-*.yml` einführen + Renovate-Config für Consumer; Migration
   `@main → @v1` als gegatete Welle (wie F1).
6. **R5:** `pypi-ci-adoption-gate.yml` (C4) zu einem generischen `ci-adoption-meter.yml` verallgemeinern
   (Nenner = `gh repo list`) + `registry_coverage_drift`/`budget_sum_trend` als Frühwarn-Jobs.

---

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** Alternative **C** (Synthese) annehmen, **P0 + R2a** sofort starten
(billig, kein Freeze-Risiko). Nach externer Runde **neu priorisiert:** **P0.5 (iil-Cohort-Constraints +
Cleanliness-Ledger) ist der Primär-Hebel** und steht vor dem R2b-Reconciler — sonst härtet die
Invariante nur Gewinner-Repos (E6). R3 wird **digest-gebunden** umgesetzt (Provenance-Kette), nicht
als Tag-Retag. Die Promote-/Staging-Hälfte läuft parallel als ADR-157-Umsetzungs-Strang.

**Org-weiter ADR nötig** für: Enforcement-Boundary (Branch-Protection-as-Code), Reusable-
Versionierungsstrategie (`@v1` + Canary-Ringe), Registry-SSoT-Konsolidierung, **Artifact-Provenance/
Digest-Bindung des Promote-Gates** und **iil-Dependency-Cohort/`iil-distribution`** (eigene
Architektur-Entscheidung, neue Boundary). **Kein** ADR-209 (C9).

**Kill-Gate (messbar, datiert; Amendment 2026-06-06 erweitert um c–e):** Wenn bis **2026-09-01**
(a) die Registries **nicht** zu **einer** SSoT (`canonical.yaml`) konsolidiert sind **oder**
(b) der Branch-Protection-as-Code-Reconciler **nicht** existiert **oder**
(c) **kein** erzwingendes Gate einen **grünen Fault-Injection-Test (R7)** trägt — verifizierbar: ≥1 Gate, dessen Injection-Test in CI nachweislich rot wird, wenn der Defekt eingespielt wird — **oder**
(d) die **Runtime-Reality-Probe (R6)** nicht täglich gegen alle `deploy:`-Repos läuft (HTTP + Container-Presence, `lifecycle`↔`prod_runtime_observed` als Issue) **oder**
(e) `drift_check.py`/`registry_coverage_drift` **nicht** `canonical.yaml` als Quelle lesen (heute: `repo-registry.yaml`/`github_repos.yaml` — verifizierbar per `grep REGISTRY_FILE`),
ist die „Invariante" Theater → Konzept auf `sunset`, Rückfall auf reines `/ci-green-program` (Alternative D).
**Teil-Sunset (Amendment):** Sind (a)/(b) erfüllt, aber (c)/(d)/(e) nicht → die *Enforcement*-Hälfte
(R2b/R3 als `required`) entfällt, die *Detektions*-Hälfte (P0/R5/R6-read-only/`registry_coverage_drift`)
bleibt — kein Rückbau, nur „Detect-only" statt „erzwungen".
**Exception-Budget:** max. **2** aktive Registry-Waiver pro Repo ohne Eskalation; jeder mit
`expires` ≤ 90 Tage; abgelaufen = CI-Fail.

**30/60/90 (nach externer Runde neu geschnitten):**
- **30 Tage:** P0 (eine Registry) + R2a (Detektoren ehrlich) + `registry_coverage_drift`-Job live;
  **P0.5-Start:** erster `iil-cohort`-Constraint-Snapshot + Ledger-Generator (read-only).
- **60 Tage:** `iil-distribution`-Pilot mit 3 Hubs (E6-Primär-Hebel); R2b-Reconciler im Dry-Run mit
  **Frische-Quorum** über alle live-Repos; erste 5 Repos „required nach verdientem frischem Grün".
  **R6 read-only** (Runtime-Reality-Probe) über alle `deploy:`-Repos; **R7** Fault-Injection-Test für
  den ersten `required`-Gate-Kandidaten (kein `required` ohne grünen Injection-Test).
- **90 Tage:** R3 **digest-gebundenes** Promote-Gate für die 3–4 Repos *mit* Staging; ADR(s) accepted;
  R6-Widerspruchs-Eskalation scharf; R7-Injection-Test für **jeden** `required`-Gate; `canonical.yaml`
  als alleinige Reconciler-Quelle; Kill-Gate-Check (a–e: Registry konsolidiert? Reconciler? Injection-Test
  grün? Runtime-Probe live? Quelle = canonical?).

---

## Anhang — Off-Ramp dieses Docs

Wird dieses Konzept → ADR(s): `pipeline_status` auf `pilot` ziehen, Doc als Quelle markieren,
`adr_threshold` auflösen. Wird es verworfen (Kill-Gate): `sunset` + Begründung. Ohne `review_by`-Pflege
(2026-07-01) gilt es per Lifecycle-Konvention als `stale`.
