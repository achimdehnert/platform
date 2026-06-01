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
created: 2026-06-01
---

# KONZ-platform-001 — Sauberer Repo-Zustand als erzwungene Invariante

> **Tier T3.** Begründung (erster Satz, harte Auto-Eskalations-Trigger): org-weit über ~41 Repos,
> kehrt die heutige *Detect-and-file-issue*-Posture um, führt eine **neue Enforcement-Boundary**
> (Branch-Protection-as-Code) und eine **Reusable-Versionierungsstrategie** ein, verschiebt **SSoT**
> (zwei Registries → eine). Jeder einzelne dieser Trigger erzwingt mind. T2; die Summe ist T3.

---

## 1. Executive Summary

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

## 5. Konzeptdefinition — die sechs Bausteine (revidiert, in zwingender Reihenfolge)

> **Leitsatz:** *Green by construction; Enforcement folgt dem Grün-Zustand pro Repo, erzwingt ihn nie voraus.*

**P0 — Registry-Konsolidierung (versteckte Vorbedingung, zuerst).**
Zwei „SSoT"-Registries (C6/C7) → **eine**. Felder mind.: `type`, `lifecycle: live|maintenance|dead`,
`staging:{…}|null`, `deploy:{…}`, `waiver:[{gate, reason, expires}]`. Die **Live-Repo-Liste wird
NICHT aus der Hand-Liste**, sondern aus `gh repo list` abgeleitet und gegen die Registry abgeglichen
(schließt das „Meter wird blind"-Loch, §6/Maintainer-Pfad 2). Ohne P0 erben R1/R2/R5 die Ambiguität.

**R1 — Konvergenz auf shared reusable Workflows (erste Regel, deterministisch).**
Jedes `live`-Repo konsumiert `_ci-python.yml`/`_ci-pypi.yml`/`_ci-odoo.yml` via `uses:`. **Pin via
gerolltem `@v1`-Major-Tag + Renovate/Dependabot-Bump-PR**, **nicht `@main`** (sonst async-unsichtbarer
Flottenbruch — Maintainer-Pfad 1; heute referenzieren die Reusables durchweg `@main`). Diese
Versionierungsstrategie ist selbst ADR-pflichtig.

**R2 — Enforcement folgt Grün, pro Repo (umgebaut, NICHT Flotten-Schalter).**
Zwei getrennte Schritte: (a) `continue-on-error` aus den Detektoren entfernen (billig, sofort) —
macht Röte *sichtbar*, noch nicht blockierend. (b) Ein **Branch-Protection-as-Code-Reconciler**
(neu — existiert nicht) setzt den shared-CI-Check pro Repo **erst dann** als `required`, wenn das
Repo **30 Tage grün** war. *Required folgt der Grün-Rate, statt sie zu erzwingen.* Damit wird kein
rotes Repo eingefroren; der Status wird verdient, nicht verordnet.

**R3 — Promote-Gate als Code (umgebaut).**
`ship.sh promote` muss vor dem Retag den **Staging-CI/Health-Grün-Status verifizieren** (nicht nur
Image-Existenz, C5). Gilt **nur für Repos mit gebautem Staging** (heute 3–4, C8) → Staging-Rollout
(ADR-157-Umsetzung) ist eine **explizite Vorbedingung**, kein stillschweigend angenommener Zustand.
**Hotfix-Pfad explizit modellieren** (dokumentierter, ablaufender Notfall-Bypass = Registry-Waiver).

**R4 — Ausnahmen als Registry-Feld (kein drittes File).**
Waiver leben als `waiver:[{gate, reason, expires}]` **in der konsolidierten Registry** (P0), nicht in
einer separaten `docs/ci-waivers.md` (existiert nicht; wäre nur `continue-on-error` umbenannt).
Meter (R5) und Required-Logik (R2) lesen **dieselbe** Quelle; Ablauf maschinell.

**R5 — dünner Rest-Task: Event-Handler + abgeleiteter Meter (ehrlicher Nenner).**
Einziger verbleibender *laufender* Anteil. Event-Handler für `UNKNOWN`/neuartige Fehler
(`/ci-green-program` Phase 3); Adoption-Meter abgeleitet aus GitHub (Muster C4), **Nenner =
`gh repo list` live**, nicht Hand-Liste. Plus zwei Frühwarn-Metriken (§11). Selbst-abschaltend per
`/ci-green-program`-Exit (≥90 % Adoption ∧ <10 % Red-Rate/30d) — *nur ehrlich mit echtem Nenner*.

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

**Frühwarn-Metriken (deterministisch, kein LLM — konform `feedback_repo_health_rule_discipline`):**
- `registry_coverage_drift` = |org-live-repos (gh)| − |konsolidierte-Registry ∩ live|; `>0 für >7 Tage` → blockierender Issue.
- `budget_sum_trend` = Σ `budgets.toml`; **darf nur fallen**; jeder Monatsanstieg = `--update-budgets`-Missbrauch, an einem Skalar ablesbar.

---

## 12. Empfehlungen (konkret, verifizierbar — keine generischen Recs)

1. **P0 zuerst:** `scripts/repo-registry.yaml` + `registry/repos.yaml` zu **einer** Datei mergen;
   Felder `lifecycle`, `staging`, `waiver[]` ergänzen; Live-Liste aus `gh repo list` ableiten.
   *Verifizierbar:* nach Merge existiert genau eine Datei mit `# Single Source of Truth`.
2. **R2a (billig, sofort):** `continue-on-error: true` aus `megatest.yml:60` und
   `platform-audit.yml:87` entfernen — Röte wird sichtbar (noch nicht blockierend).
3. **R2b (das eigentliche Werk):** `tools/branch-protection-reconciler.py` bauen, das pro `live`-Repo
   den shared-CI-Check als `required` setzt **gdw. 30d grün** — inkl. Drift-Audit (`gh api …/protection`).
4. **R3:** `ship.sh promote` um eine **Staging-Grün-Verifikation** vor dem Retag erweitern (C5);
   Hotfix-Bypass als ablaufenden Registry-Waiver modellieren.
5. **R1:** gerollten `@v1`-Tag auf `_ci-*.yml` einführen + Renovate-Config für Consumer; Migration
   `@main → @v1` als gegatete Welle (wie F1).
6. **R5:** `pypi-ci-adoption-gate.yml` (C4) zu einem generischen `ci-adoption-meter.yml` verallgemeinern
   (Nenner = `gh repo list`) + `registry_coverage_drift`/`budget_sum_trend` als Frühwarn-Jobs.

---

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** Alternative **C** (Synthese) annehmen, **P0 + R2a** sofort starten
(billig, kein Freeze-Risiko), **R2b-Reconciler** als ADR-pflichtigen Kern-Baustein priorisieren.
Die Promote-/Staging-Hälfte (R3) läuft parallel als ADR-157-Umsetzungs-Strang.

**Org-weiter ADR nötig** für: Enforcement-Boundary (Branch-Protection-as-Code), Reusable-
Versionierungsstrategie (`@v1` + Bump-Bot), Registry-SSoT-Konsolidierung. **Kein** ADR-209 (C9).

**Kill-Gate (messbar, datiert):** Wenn bis **2026-09-01** (a) die Registries **nicht** zu einer SSoT
konsolidiert sind **oder** (b) der Branch-Protection-as-Code-Reconciler **nicht** existiert, ist die
„Invariante" Theater → Konzept auf `sunset`, Rückfall auf reines `/ci-green-program` (Alternative D).
**Exception-Budget:** max. **2** aktive Registry-Waiver pro Repo ohne Eskalation; jeder mit
`expires` ≤ 90 Tage; abgelaufen = CI-Fail.

**30/60/90:**
- **30 Tage:** P0 (eine Registry) + R2a (Detektoren ehrlich) + `registry_coverage_drift`-Job live.
- **60 Tage:** R2b-Reconciler im Dry-Run über alle live-Repos; erste 5 Repos „required nach 30d grün".
- **90 Tage:** R3-Promote-Gate als Code für die 3–4 Repos *mit* Staging; ADR(s) accepted; Kill-Gate-Check.

---

## Anhang — Off-Ramp dieses Docs

Wird dieses Konzept → ADR(s): `pipeline_status` auf `pilot` ziehen, Doc als Quelle markieren,
`adr_threshold` auflösen. Wird es verworfen (Kill-Gate): `sunset` + Begründung. Ohne `review_by`-Pflege
(2026-07-01) gilt es per Lifecycle-Konvention als `stale`.
