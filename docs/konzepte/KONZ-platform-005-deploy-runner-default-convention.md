---
concept_id: KONZ-platform-005
title: Deploy-Runner-Default-Konvention (shared-ci runs_on)
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []          # N/A — Infra/CI-Konvention, kein ADR-211-Klickdummy-Spec-Thema
adr_threshold: org-weiter ADR
review_by: 2026-09-10
kill_criteria: "Wenn nach dem Flip >0 Repos still auf den falschen Host deployen (cp-Erfolg am falschen /opt) ODER ein Sovereign-Org-Repo (_deploy-unified) ohne Override auf prod-server geroutet wird → Flip zurücknehmen (1-Zeilen-Revert in shared-ci)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "iilgmbh/shared-ci/.github/workflows/_deploy-unified.yml@v1.0.2 (inputs runs_on/deploy_runs_on)", commit_or_pr: "v1.0.2", opened_in_session: true}
  - {claim_id: C2, source_path: "achimdehnert/wedding-hub actions run 27290001839 (deploy/Production atomic-sync)", commit_or_pr: "run-27290001839", opened_in_session: true}
  - {claim_id: C3, source_path: "Fleet-Scan deploy.yml runs_on/deploy_runs_on über 20 deploybare achimdehnert-Repos", commit_or_pr: "session-scan-2026-06-10", opened_in_session: true}
  - {claim_id: C4, source_path: "platform/.github/workflows/runner-health.yml (REQUIRED_LABEL=prod-server, MAIN_ORG=achimdehnert, Z.45/46/99-119)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-021-unified-deployment-pattern.md §2.17 (Z.416-426)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C6, source_path: "ttz-hub/.github/workflows/deploy.yml (runs-on ubuntu-latest); meiki-hub pages.yml (ubuntu-latest) — kein _deploy-unified-Konsum", commit_or_pr: "local", opened_in_session: true}
  - {claim_id: C7, source_path: "achimdehnert cad-hub/risk-hub/dev-hub erfolgreiche Deploy-Runs — labels=[prod-server]", commit_or_pr: "session-api-2026-06-10", opened_in_session: true}
  - {claim_id: C8, source_path: "platform/.github/workflows/{platform-audit,sync-policies-to-orchestrator,sync-adrs-to-devhub}.yml runs-on Labels", commit_or_pr: "main", opened_in_session: true}
created: 2026-06-10
---

# KONZ-platform-005 — Deploy-Runner-Default-Konvention

**Tier-Entscheidung (erster Satz): T3.** Auslöser nicht verhandelbar: die Änderung betrifft eine
**geteilte reusable Workflow** (`iilgmbh/shared-ci/_deploy-unified.yml`), wirkt **cross-repo über
~20 deploybare Repos** und ist ein **Default-Reversal** (self-hosted → prod-server). Jeder einzelne
dieser Trigger erzwingt mind. T2; in Kombination → T3 mit adversarialem Agenten-Fan-out.

## Kernthese (ein Satz)
Der shared-ci-Deploy-Runner-Default ist **invertiert** — der generische, fehlroutbare Wert
(`self-hosted`) ist Default, Korrektheit (`prod-server`) erfordert pro Repo einen aktiven Pin;
die Lösung ist, den **sicheren Wert zum Default** zu machen, den Guard von *zufällig laut* auf
*absichtlich laut* zu heben und die **wenigen echten Ausnahmen** (heute: writing-hub) an einer
Stelle zu kodifizieren.

---

## 1. Executive Summary
`_deploy-unified.yml@v1.0.2` resolved den Deploy-Runner über `deploy_runs_on` (Default `""` →
Fallback auf `runs_on`, Default `"self-hosted"`) **(C1)**. Ohne expliziten Pin kann ein beliebiger
`self-hosted`-Runner den Prod-Deploy greifen — verifiziert an **wedding-hub run 27290001839**:
Runner `dev-hetzner` (labels `["self-hosted"]`) griff, hatte kein `/opt/wedding-hub` → `cp: … No
such file or directory` am atomic-sync-Step **(C2)**. Fleet-Scan **(C3)**: **13 Repos** nutzen den
unsicheren Default (latent fehlroutbar), **6** pinnen `prod-server` (redundant), **1** echte
Ausnahme (writing-hub, `ubuntu-latest`, Remote-SCP-Modell). Vorschlag: Default → `prod-server`,
plus drei begleitende Bausteine (intentionaler Guard, Introspektion, Versions-Konvergenz), weil
der nackte Flip allein neue Risiken birgt (s. §6/§11).

## 2. Scope & Evidenzbasis
- **In-Scope:** der Deploy-Runner-Label-Default in `_deploy-unified.yml`; die 6 redundanten Pins;
  die Ausnahmen-Kodifikation.
- **Out-of-Scope (eigene Stränge):** shared-ci-Versions-Konvergenz (eigener Sweep, hier nur als
  **Vorbedingung**), die ADR-021-§2.17-Migration selbst.
- **Evidenz:** alle Claims C1–C8 in dieser Session geöffnet (Manifest oben). Nicht Klickdummy/
  ADR-211-bezogen → `spec_refs` bewusst leer; F11/F17/F18/F19 (Genesor-Klickdummy-Items) sind hier
  **nicht anwendbar** (geprüft: anderes Subsystem).

## 3. Infrastruktur-Fit
- `prod-server` ist **kein loser String, sondern aktiv erzwungen**: `runner-health.yml` setzt
  `REQUIRED_LABEL = "prod-server"` und re-labelt Runner darauf — aber nur für `MAIN_ORG =
  "achimdehnert"` **(C4)**. cad-hub/risk-hub/dev-hub-Deploys laufen verifiziert auf
  `labels=["prod-server"]` **(C7)**. → Der Flip-Zielwert ist real und gewartet.
- **Label-Taxonomie ist uneinheitlich:** der Deploy-Pfad nutzt `prod-server`, platform-eigene
  Jobs nutzen `[self-hosted, prod]` (platform-audit, sync-policies) bzw. `[self-hosted, hetzner,
  dev]` (sync-adrs) **(C8)**. Zwei nebeneinander lebende Konventionen — der ADR muss die Taxonomie
  kodifizieren, nicht nur einen Default kippen.

## 4. Steelman (stärkste Pro-Sicht)
Der Default ist rückwärts: er liefert die *unsichere* Annahme an 13 Repos, wo sie latent liegt,
bis ein Runner-Label-Race einen Prod-Deploy still fehlroutet (C2 ist der Beweis, kein Hypothetik).
Korrektheit per Wachsamkeit (6/20 erinnern den Pin) skaliert nicht; ein sicherer Default invertiert
die Last — man muss aktiv *opt-out*, und opt-out ist ein sichtbarer, reviewbarer Akt. „Prod
deployt auf den Prod-Host" ist ein Plattform-Fakt, kein Repo-Detail → gehört in
`_deploy-unified.yml`, nicht in 6 driftende Kopien. Nach dem Flip gibt es **genau eine** sichtbare
Abweichung (writing-hub) statt 6 sicherheitsrelevanter Pins, die optisch nicht von den 13 fehlenden
zu unterscheiden sind. Low-regret: 1-Zeilen-Default, trivial revertierbar; §2.17 macht jeden
Edge-Case zu einem roten CI-Run statt einer Prod-Korruption.

## 5. Konzeptdefinition (die Setzung — `D`, mit Alternativen in §8)
**Regel:** „Sicherer Default + Fehler-by-Design wenn die Annahme bricht + die wenigen echten
Ausnahmen explizit an *einer* Stelle." Operationalisiert in **vier gekoppelten Bausteinen** (der
Flip allein ist abgelehnt — s. §6):
1. **Flip:** `_deploy-unified.yml` Default-Runner `self-hosted` → `prod-server`.
2. **Intentionaler Guard:** vor dem atomic-sync eine **explizite Assertion**, dass der Runner das
   erwartete Label trägt bzw. `/opt/<app>` existiert — damit „laut scheitern" nicht von einem
   `cp`-Nebeneffekt abhängt (§6 AD-4).
3. **Introspektion:** den **aufgelösten Runner-Label + den shared-ci-Ref** ins Deploy-Log echoen
   („deploying via label=X from ref=Y") — gegen Debuggability-Verlust (§6 AD-5, Maintainer-2028).
4. **Ausnahmen-Register:** writing-hub (`ubuntu-latest`) als einzige kodifizierte Ausnahme im ADR;
   neue Ausnahmen brauchen einen ADR-Eintrag.

## 6. Adversariale Analyse (3 unabhängige Agenten + Synthese)
Drei Agenten, blind zueinander (Steelman §4 / Advocatus Diabolus / Maintainer-2028).

**Advocatus Diabolus — Top-Einwände (nach Verifikation eingeordnet):**
- **AD-1 „prod-server ist kein Vertrag":** **WIDERLEGT.** runner-health.yml erzwingt das Label
  aktiv (C4); 3 Deploys laufen darauf (C7). Der Diabolus übersah die Enforcement-Workflow.
- **AD-2 „Sovereign-Orgs fehlrouten":** **WIDERLEGT für heute.** ttz-hub/meiki-hub konsumieren
  `_deploy-unified` **nicht** (beide `ubuntu-latest`) (C6). → wird **Vorbedingung**, kein Blocker:
  falls künftig ein ttz/meiki-Repo `_deploy-unified` adoptiert, muss es `runs_on` überschreiben.
- **AD-3 „silent-wrong ersetzt loud-missing":** **TEILGÜLTIG, zukünftig.** Greift nur für ein Repo,
  dessen Prod *nicht* prod-server ist und das den Default erbt — heute existiert keins
  (writing-hub explizit, ttz/meiki kein Konsum). Mitigiert durch Baustein 2+3.
- **AD-4 „§2.17 ist zufällig load-bearing":** **GÜLTIG.** §2.17 fängt Wrong-Runner nur
  *inzidentell* (cp scheitert an fehlendem `/opt/<app>`) (C5). Ein künftiges `mkdir -p` ließe den
  cp gelingen → stiller Fehl-Deploy. → **Baustein 2** macht den Guard intentional.
- **AD-5 „Pins löschen tötet Self-Documentation":** **GÜLTIG.** „Wohin deployt dies Repo?" wird
  zum Zwei-Hop-Lookup (welcher shared-ci-Tag → welcher Default in dem Tag). → **Baustein 3**;
  Pins NICHT blind löschen (§13 offene Entscheidung).
- **AD-6/7 „Versions-Drift macht Flip nicht-atomar / Root-Cause untouched":** **GÜLTIG & zentral.**
  Ein Tag-Default erreicht ein Repo erst beim Bump → unbekanntes Fenster mit gemischtem Zustand;
  Label-Hygiene + Drift bleiben sonst unberührt. → **Baustein 4** + Versions-Konvergenz-Vorbedingung.

**Maintainer-2028:** Verdikt 6/10 net-positiv — *aber* die Autoren optimierten für den sauberen
Steady-State und unterbauten **Propagation & Introspektion**: Versions-Drift erzeugte ein
8-Monats-Split-Brain (Repos auf Pre-Flip-Tags deployten weiter auf `self-hosted`, unbemerkt weil
beide Labels auf derselben Box auflösten — bis der generische Runner abgebaut wurde → 4 Repos
`startup_failure` gleichzeitig). Größter Wunsch: **nicht der ADR, sondern ein Lint, der failt wenn
ein Repo einen shared-ci-Tag *vor* dem Flip pinnt**, + die Log-Echo-Zeile (Baustein 3).

### Konfliktmatrix (belegte Dissense)
| # | Achse | Steelman | Diabolus / Maintainer | Auflösung (verifiziert) |
|---|-------|----------|------------------------|--------------------------|
| K1 | prod-server real? | „gewarteter Default" | „nur String/Beispiel" | **Steelman** — runner-health erzwingt (C4/C7) |
| K2 | Sovereign-Risiko | (nicht adressiert) | „Compliance-Blocker" | **Diabolus überzogen** — kein Konsum heute (C6) → Vorbedingung |
| K3 | §2.17 als Backstop | „§2.17 fängt alles" | „nur inzidentell, fragil" | **Diabolus** — Baustein 2 nötig |
| K4 | 6 Pins löschen | „Net-Code-Reduktion" | „tötet Debuggability" | **Maintainer** — Baustein 3, Löschung offen (§13) |
| K5 | Versions-Drift | (unterschätzt) | „der eigentliche Killer" | **Maintainer/Diabolus** — Baustein 4 + Vorbedingung |

→ Echte Divergenz auf K1, K3, K4, K5 (kein wertloser Fan-out). K1/K2 durch In-Session-Verifikation
zugunsten/zulasten beider Seiten entschieden.

## 7. Deep-Dive — Versions-Drift als Hauptrisiko
Repos pinnen `_deploy-unified.yml@{v1.0.0|1|2|3|main}` (C3). Ein Default-Flip in `vX` erreicht nur
Repos, die auf `vX` bumpen. Folge: temporär **nicht-uniform unsicher** (manche default→prod-server,
manche noch self-hosted, manche `@main` = beweglich). Das ist potenziell *schlechter* als der
heutige uniform-unsichere Zustand, weil schwerer zu reasonen — und genau das Muster, das am
2026-06-09 schon einen Fleet-Break auslöste (`feedback_sharedci_tag_stale_vs_platform_main`).
→ **Der Flip darf nicht vor einer Versions-Konvergenz auf *einen* Tag ausgerollt werden**, oder
muss mit dem Pre-Flip-Tag-Lint (Baustein 4) abgesichert sein.

## 8. Alternativen
- **A0 Status quo:** 13 Repos latent fehlroutbar; verworfen (C2 brennt bereits).
- **A1 Nur die 3 akuten Repos pinnen** (bereits getan: wedding/billing/recruiting-PRs): löst akut,
  ändert den Default-Drift nicht — Interim, nicht Lösung.
- **A2 Flip-only** (nackt, ohne Bausteine 2–4): vom Adversariat verworfen (AD-4/5/6).
- **A3 (empfohlen) Flip + 4 Bausteine + Versions-Konvergenz-Vorbedingung.**
- **A4 `deploy_runs_on` *required* machen (fail-closed auf leer) statt Default flippen:** hält
  Fehler laut *by design* und Intent am Call-Site, aber erzwingt einen Pin in *jedem* Repo (mehr
  Ausnahmen-Pflege, gegen das Ziel). Starker Gegenkandidat — in §13 als Entscheidungs-Fork.

## 9. Out-of-the-Box
- **OOTB-1 (umgesetzt im Konzept):** „ship the default **and a way to see the default**" — die
  Log-Echo-Zeile (Baustein 3) ist billiger und wirksamer als der ADR selbst (Maintainer-Lehre).
- **OOTB-2 Label-as-data:** Runner-Label nicht hardcoden, sondern aus der Registry pro App ableiten
  (`registry.<app>.deploy_runner`) — macht `prod-server` vs künftige Sovereign-Labels zu Daten, nicht
  zu shared-ci-Defaults. Größer; Backlog-Kandidat, adressiert AD-2 strukturell.
- **OOTB-3 Threshold-Check-Bot:** statt Selbst-Einstufung des Tiers ein Bot, der Konzepte gegen die
  Auto-Eskalations-Trigger prüft (vom konzept-Skill selbst als Backlog OOTB-5 genannt).

## 10. Befunde
| ID | Befund | Evidenz | Schwere |
|----|--------|---------|---------|
| B1 | 13 Repos latent prod-fehlroutbar (unsicherer Default) | C3 | hoch |
| B2 | Wrong-Runner-Fehlroute real eingetreten | C2 | hoch |
| B3 | §2.17 fängt Wrong-Runner nur inzidentell | C5 | mittel |
| B4 | Versions-Drift → nicht-atomare Propagation/Split-Brain | C3 + Memory | hoch |
| B5 | Label-Taxonomie uneinheitlich (prod-server vs [self-hosted,prod]) | C8 | mittel |
| B6 | Pins-Löschen senkt Debuggability | Maintainer/AD-5 | mittel |

## 11. Top-5-Risiken
1. **Split-Brain durch Versions-Drift** (B4) — Mitigation: Versions-Konvergenz *vor* Flip + Pre-Flip-Tag-Lint.
2. **Stiller Fehl-Deploy falls §2.17-cp künftig gelingt** (B3) — Mitigation: intentionaler Guard (Baustein 2).
3. **Künftiger Sovereign-Konsum ohne Override** (AD-2) — Mitigation: Vorbedingung + Registry-Label (OOTB-2).
4. **Debuggability-Verlust durch Pin-Löschung** (B6) — Mitigation: Log-Echo + Löschung gated (§13).
5. **Blast-Radius: ein schlechter shared-ci-Default bricht alle** — Mitigation: gestaffelter Rollout, ein kanonischer Tag, kein `@main`.

## 12. Empfehlungen (konkret)
- **R1:** `_deploy-unified.yml` — Input-Default `runs_on: "self-hosted"` → `"prod-server"` (Flip).
- **R2:** `_deploy-unified.yml` — vor atomic-sync `test -d "$(dirname "$APP_PATH")"` + Label-Assertion; sonst `::error` fail-loud (intentionaler Guard).
- **R3:** `_deploy-unified.yml` — `echo "deploy: app=$APP runner_label=$RESOLVED ref=$SHARED_CI_REF"` als erste Deploy-Step-Zeile (Introspektion).
- **R4:** neuer Lint in shared-ci-CI: fail wenn ein Consumer einen `_deploy-unified`-Tag *vor* dem Flip-Tag pinnt (gegen Split-Brain).
- **R5:** ADR (Deploy-Runner-Konvention) kodifiziert: Default=prod-server, Ausnahmen-Register {writing-hub: ubuntu-latest}, Label-Taxonomie.
- **R6:** writing-hub behält explizit `runs_on: "ubuntu-latest"` + Kommentar mit ADR-Verweis.

## 13. Entscheidung + Kill-Gate + 30/60/90
**Offene Entscheidungs-Forks (für den User / ADR):**
- **F-α:** A3 (Flip + Bausteine) **vs** A4 (`deploy_runs_on` required, kein Default-Flip)? A3 trifft
  „wenige Ausnahmen" besser; A4 hält Intent am Call-Site. *Empfehlung: A3.*
- **F-β:** Die 6 redundanten Pins **löschen** (Uniformität) **oder behalten** (Debuggability, B6)?
  *Empfehlung: behalten, aber auf 1 Zeile + Kommentar normalisieren — Intent bleibt grep-bar.*
- **F-γ:** Versions-Konvergenz als **harte Vorbedingung** vor dem Flip, oder Flip + Pre-Flip-Lint
  parallel? *Empfehlung: Konvergenz zuerst (D3-Sweep), dann Flip.*

**Kill-Gate (messbar):** Wenn nach Rollout **>0 Repos** still auf den falschen Host deployen
(cp-Erfolg am falschen `/opt`) ODER ein Sovereign-Repo ohne Override auf prod-server landet → Flip
1-Zeilen-Revert in shared-ci. **Exception-Budget:** 1 manueller Pin-Workaround erlaubt bis
**2026-09-10** (review_by); danach muss jede Abweichung im Ausnahmen-Register stehen.

**30/60/90:** *30* — Versions-Konvergenz + R2/R3 in shared-ci, ein kanonischer Tag. *60* — Flip
(R1) + R4-Lint, gestaffelt (Kohorte cad/risk/dev zuerst, sind schon prod-server). *90* — ADR (R5)
accepted, Pins normalisiert (F-β), Kill-Gate-Review.

---
*Vorstufe zu ADR „Deploy-Runner-Konvention". Adversariat: 3 unabhängige Agenten (Steelman/
Advocatus-Diabolus/Maintainer-2028) + In-Session-Verifikation der strittigen Claims (K1/K2).*
