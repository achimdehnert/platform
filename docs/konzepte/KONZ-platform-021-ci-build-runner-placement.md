---
concept_id: KONZ-platform-021
title: "Cross-Repo CI/Build-Runner-Placement — GitHub-hosted Default, ci-nonprod als Opt-out (ADR-257 Rev 4)"
pipeline_status: idea
tier: T3
owner: "Achim Dehnert"
spec_refs: []   # Infra-/CI-Konzept ohne ADR-211-Spec-Bezug — es existiert keine SoR-Spec für Runner-Topologie; SSoT ist infra/hosts.yaml (C3)
adr_threshold: "Amendment (ADR-257 Rev 4) — Reversal-Trigger erfüllt (Mechanismus-Wechsel einer accepted Entscheidung); Alternative: neues ADR mit partial-supersedes"
review_by: "2026-09-24"
kill_criteria: "Bis 2026-09-24: (a) shared-ci-Deploy-Verzweigung für Misch-Config gefixt (deploy_runs_on statt runs_on, Consumer-Canary grün), (b) 1 echter Build+Deploy-Lauf mit runs_on=ubuntu-latest + deploy_runs_on=prod-server grün (billing-hub, workflow_dispatch/staging), (c) Actions-Minuten-Baseline gemessen (Plan+Monatsverbrauch dokumentiert) und Fleet-Prognose <80% Freikontingent ODER Spending-Limit bewusst entschieden — sonst sunset, Fallback Alternative B (ci-nonprod + Minimal-Bootstrap), ADR-257-Kill-Gate feuert regulär. Exception-Budget: max. eine 30-Tage-Verlängerung."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "docs/adr/ADR-257-ci-host-isolation-non-prod-runner.md", commit_or_pr: "main (accepted, Rev 3)", opened_in_session: true}
  - {claim_id: C2, source_path: "infra/host-maintenance/runner-nonprod-runbook.md", commit_or_pr: "main (Header stale: 'proposed')", opened_in_session: true}
  - {claim_id: C3, source_path: "infra/hosts.yaml", commit_or_pr: "main (Runner-SSoT)", opened_in_session: true}
  - {claim_id: C4, source_path: "platform#1078 (RAM-Oversubscription prod-server)", commit_or_pr: "#1078", opened_in_session: true}
  - {claim_id: C5, source_path: "billing-hub PR#30 (Branch-YAML ci.yml+deploy.yml)", commit_or_pr: "achimdehnert/billing-hub#30", opened_in_session: true}
  - {claim_id: C6, source_path: "recruiting-hub PR#17", commit_or_pr: "achimdehnert/recruiting-hub#17", opened_in_session: true}
  - {claim_id: C7, source_path: "iilgmbh/shared-ci/.github/workflows/_deploy-unified.yml (Inputs Z.64-79; Deploy-Verzweigung Z.313/316/367/383/395)", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C8, source_path: "gh api repos/achimdehnert/{travel-beat,billing-hub,recruiting-hub,cad-hub}/actions/runners + orgs/achimdehnert/actions/runners (404)", commit_or_pr: "live 2026-07-16", opened_in_session: true}
  - {claim_id: C9, source_path: "travel-beat .github/workflows/{ci,deploy,runner-label-check}.yml", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C10, source_path: "deploy.yml/ci.yml von coach-hub, wedding-hub, pptx-hub, weltenhub, trading-hub, cad-hub, dev-hub (runs_on-Inputs)", commit_or_pr: "main, live 2026-07-16", opened_in_session: true}
  - {claim_id: C11, source_path: "platform/.github/workflows/_ci-python.yml:610-629 (Label-Check-Logik, ALLOWED_EXTRA=set(), parst nur job['runs-on'])", commit_or_pr: "main", opened_in_session: true}   # geöffnet durch Maintainer-2028-Subagent dieser Session
  - {claim_id: C12, source_path: "_deploy-unified.yml Z.203-204 (cache-from/to type=gha); billing-hub Actions-Secrets (DEPLOY_SSH_FINGERPRINT fehlt)", commit_or_pr: "main / Secrets-API live", opened_in_session: true}   # geöffnet durch Diabolus-Subagent dieser Session
  - {claim_id: C13, source_path: "gh api users/achimdehnert/settings/billing/actions → 404 + Scope-Fehler ('user'-Scope fehlt)", commit_or_pr: "live 2026-07-16 (negatives Ergebnis)", opened_in_session: true}
created: "2026-07-16"
---

# KONZ-platform-021 — CI/Build-Runner-Placement: GitHub-hosted Default, ci-nonprod als Opt-out

> Auftrag: platform#1217 (`/konzept`). Tier-Entscheidung: **T3** — Cross-Repo (10 Hubs),
> Amendment an eine accepted ADR-Entscheidung (Reversal-Trigger der Auto-Eskalation),
> plus SSoT-Berührung (hosts.yaml/Label-Konvention). Adversariales Fan-out mit drei
> blinden Agenten (Steelman / Advocatus Diabolus / Maintainer-2028) + Synthese mit
> Konfliktmatrix durchgeführt (§6).
>
> Einbettung: Dieses Konzept ist die **Build-Plane-Säule** des übergeordneten
> Betriebsmodells „dev/staging/prod" (User-Direktive 2026-07-16, Parallel-Session:
> „Build-Plane ≠ Run-Plane — Images werden nie auf dem Prod-Host gebaut; Build auf
> ephemerem CI → Registry → Prod pullt nur"). Es erzeugt keine zweite Wahrheit zu
> KONZ-platform-015 (Dead-Reference/Registry-Achse) — andere Fehlerklasse, gleiche Fleet.

---

## 1. Executive Summary

**Empfehlung: annehmen als gehärtete Fassung — aber erst nach drei harten Vorab-Gates, von denen eines die offenen PRs #30/#17 aktuell blockiert.** Kernidee: GitHub-hosted `ubuntu-latest` wird der Fleet-Default für CI- **und** Build-Jobs; der self-hosted `ci-nonprod`-Runner wird vom (gescheiterten) Default zum getrackten Opt-out degradiert; Deploy-Jobs bleiben unverändert auf `prod-server` (ADR-156). Die stärkste Stütze: Die Pilot-Empirie hat den Pet-Runner-Pfad bereits falsifiziert — travel-beat referenziert `ci-nonprod` in keinem Workflow, sechs Hubs sind organisch auf `ubuntu-latest` konvergiert, und `achimdehnert` ist ein User-Account ohne Org-Runner-API, womit jede Runner-Skalierung O(n) manuelle SSH-Registrierungen kostet. Das größte Risiko (Diabolus AD-1, verifiziert): `_deploy-unified.yml` verzweigt die Deploy-*Mechanik* an `inputs.runs_on`, nicht an `deploy_runs_on` — die Misch-Config der offenen PRs würde den Prod-Deploy still von lokalem atomic-sync auf einen nie gelaufenen SSH-Loopback umschalten (billing-hub fehlt zudem das `DEPLOY_SSH_FINGERPRINT`-Secret). **PRs #30/#17 dürfen so nicht gemergt werden.** Das MVC: (1) shared-ci-Fix der Deploy-Verzweigung + Consumer-Canary, (2) ein echter Build+Deploy-Beweis mit Misch-Config, (3) einmalige Minuten-Baseline (braucht `user`-Scope — heute nicht abfragbar, Human-Item). Die wichtigste Revision gegenüber dem Entwurf (Konflikt K3): Das Minimal-Bootstrap-Skript wird **doch** eingecheckt und der konsumentenlose travel-beat-Runner deregistriert — Zombie-Runner ohne Wiederaufbau-Skript ist die schlechteste Kombination. Die größte Unsicherheit bleibt das Minuten-Budget (private Repos, Plan und Verbrauch unverifiziert, C13) — deshalb ist es Kill-Gate-Bedingung (c), kein Vertrauensvorschuss.

## 2. Scope & Evidenzbasis

**Inputs:** Issue platform#1217 (Auftrag + Vorab-Evidenz), drei blinde adversariale Agenten-Analysen, eigene Verifikation in dieser Session (alle Pfade im `evidence_manifest`).

**In dieser Session real geöffnet:** ADR-257 (C1), Runbook (C2), hosts.yaml (C3), #1078 (C4), beide abhängige PRs inkl. Branch-YAML (C5/C6), `_deploy-unified.yml` Inputs + Deploy-Verzweigung (C7), Live-Runner-Stand via API inkl. Org-404 (C8), travel-beat-Workflows (C9), Fleet-Workflows von 7 weiteren Hubs (C10). Durch Subagenten dieser Session geöffnet: Label-Check-Logik `_ci-python.yml:610-629` (C11), GHA-Layer-Cache-Nutzung + billing-hub-Secrets (C12).

**Negativ-Verifiziert:** Actions-Billing-API nicht abfragbar — Token ohne `user`-Scope (C13). **Deshalb Hypothese (H): GitHub-Plan, Freikontingent (2000 oder 3000 min/Monat) und aktueller Monatsverbrauch.** Billigster Check: `gh auth refresh -h github.com -s user`, dann `gh api users/achimdehnert/settings/billing/actions`.

**Annahmen (markiert):** (H1) Build-Dauer auf hosted Runnern ist mit `type=gha`-Cache (C12) vergleichbar oder moderat langsamer als self-hosted — nie gemessen. (H2) Der 2×-Fehlschlag der billing/recruiting-Deploys ist RAM-Druck (#1078-Signatur) — Kill-Signal wurde in #1078 selbst nicht belegt. (H3) wedding-hub `@v1.0.5` kennt `deploy_runs_on` noch nicht — Preflight pro Repo nötig, Tag-Historie nicht geprüft.

## 3. Infrastruktur-Fit

Die ADR-211-/Klickdummy-Achsen (I1–I4, F11/F17/F18/F19, Genesor-Pipeline, Parity-Bridges) sind für dieses Infra-Konzept **nicht einschlägig** — keine Spec, kein Klickdummy, kein UI. Geprüft und relevant:

| Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---|---|---|---|---|
| shared-ci `_deploy-unified.yml` ubuntu-Pfad | ja | ✓ (First-Class-Input, scp/ssh-Fallback) | ✓ **Fix nötig:** Deploy-Steps verzweigen an `runs_on` statt `deploy_runs_on` (C7) | **hoch** | Misch-Config schaltet Prod-Mechanik um — Blocker für #30/#17 |
| `deploy_runs_on`-Input (Build/Deploy-Trennung) | ja | ✓ | — | niedrig | ADR-156-Carve-out bleibt unangetastet |
| `runner-label-check` / `_ci-python.yml:610-629` | ja | teilweise | strukturell blind für `with: runs_on:`-Inputs (C11) | **hoch** | Enforcement muss neu geschnitten werden (§5.8), nicht kopiert |
| `infra/hosts.yaml` (Runner-SSoT) | ja | ✓ | ✓ `consumers:`-Feld je Runner | niedrig | tötet „Runner ohne Konsument"-Klasse (M28-3) |
| ADR-257 Entscheidungen 1–3 (Invariante) | ja | ✓ | Rev 4: Mechanismus-Teil ersetzen | mittel | Invariante „CI nie auf Prod-Host" bleibt; nur das *Wie* flippt |
| ADR-270-Tiering (Merge-Staffelung) | ja | ✓ | — | niedrig | Rollout-Reihenfolge Tier-gestaffelt |
| Kill-Gate-Wächter (Cloud-Routine, live) | ja | ✓ | konsumiert neues maschinenlesbares Kill-Gate | niedrig | M28-4: Gate braucht Aktuator, nicht nur Datum |
| `adr-threshold`-Policy | ja | ✓ | — | — | Reversal ⇒ ADR-pflichtig; Form (Rev 4 vs. neues ADR) in §13 |

## 4. Steelman (kondensiert, aus blindem Agenten-Lauf)

ADR-257s eigentliche Entscheidung ist die **Invariante** „CI/Test läuft nicht auf dem Prod-Host" (Entscheidung 1); der „dedizierte Non-Prod-Runner" war nur das damals gewählte Mittel, und Kill-Gate (ii) testet das Mittel statt der Invariante. GitHub-hosted erfüllt die Invariante *stärker*: Es ist der ephemere Endzustand, den ADR-257 selbst als Evolutionsziel benennt („optional später Terraform/ARC/ephemer") — ohne je Bootstrap, Runbook-Härtung, Hygiene-Check oder Quarantäne-Playbook betreiben zu müssen; die Fehlerklasse „Runner-Pollution/Host-Port-Bindung/verwaister Prozess" (Kill-Gate-Bedingung (i)) ist auf ephemeren Runnern strukturell unerfüllbar. Die Empirie hat entschieden: null `ci-nonprod`-Adoption in Monaten, sechs Hubs organisch auf `ubuntu-latest`, User-Account ohne Org-Runner-API macht den Pet-Pfad zu O(n) manueller SSH-Pflege. Der Entwurf kanonisiert den real gelebten Zustand, statt gegen ihn anzuregieren, und implementiert exakt die Build-Plane-Säule des übergeordneten Betriebsmodells. *(Synthese-Korrektur: Die Steelman-Aussage „0 Zeilen shared-ci-Änderung nötig" ist durch AD-1 falsifiziert — siehe K1.)*

## 5. Konzeptdefinition

### 5.1 Kernthese

Dieses Konzept sagt: **CI- und Build-Jobs der Fleet laufen per Default auf GitHub-hosted `ubuntu-latest` (ephemer, im Code-Default der shared-ci-Familien verankert, nicht nur als Prosa); der self-hosted `ci-nonprod`-Pfad wird zum getrackten, per Minimal-Bootstrap-Skript reproduzierbaren Opt-out; Deploy-Jobs bleiben auf `deploy_runs_on: prod-server` — umgesetzt als ADR-257 Rev 4, das die Falsifikation des Pet-Runner-Mechanismus durch die Pilot-Empirie ausdrücklich anerkennt statt das Kill-Gate zu umgehen.**

### 5.2 Problem

**Beobachtung (verifiziert):** (i) billing-hub/recruiting-hub-Deploys schlugen je 2× still fehl; prod-server ist 3,7× memory-überbucht bei ~30 Stacks auf 8 GB (C4). (ii) Der ADR-257-Pilot ist Schein-vollzogen: Runner registriert und online, aber **kein** Workflow routet dorthin; travel-beats Build läuft auf plain `self-hosted`, das seit der Registrierung **beide** Runner nichtdeterministisch matcht (C8/C9). (iii) `ci-nonprod` ist per-Repo registriert, Org-Runner sind auf dem User-Account nicht verfügbar (API 404, C8) — Skalierung = ~10 manuelle SSH-Registrierungen. (iv) Das geforderte Bootstrap-Skript existiert nicht; Runbook-Header ist stale (C2). (v) Die `ci.yml`s von 6 Hubs laufen bereits auf `ubuntu-latest` — der Schmerz konzentriert sich auf die `Build`-Jobs in `deploy.yml` (C10). (vi) Die offenen PRs #30/#17 sind ungetestet gegen den echten Build-Job und schalten unbemerkt die Deploy-Mechanik um (C5/C7).

**Interpretation:** Der accepted Mechanismus (per-Repo-Pet-Runner) ist an Adoptionskosten gescheitert, nicht an seiner Invariante. Die Fleet ist organisch zum hosted Pfad konvergiert, der in shared-ci bereits First-Class ist.

**Hypothesen (markiert):** H1–H3 aus §2. **Offene Frage (Human):** Minuten-Budget/Spending-Limit-Politik (C13).

### 5.3 Zielbild

Kein CI-/Build-Job der Fleet kann auf dem Prod-Host laufen — nicht per Verbot, sondern weil der Code-Default der shared-ci-Familien auf `ubuntu-latest` steht und ein in der Familie mitreisender Fail-fast-Guard plain `self-hosted` für CI/Build hart abbricht. Opt-outs sind zählbar (Fleet-Scan), reproduzierbar (Bootstrap-Skript im Repo) und tragen einen getrackten Grund. Runner ohne Konsument existieren nicht (hosts.yaml `consumers:`-Diff). Der Prod-Deploy-Pfad (atomic-sync auf `prod-server`) bleibt byte-identisch zu heute.

### 5.4 Nicht-Ziele

- **Kein Anfassen der Deploy-Mechanik** über den AD-1-Fix hinaus — ADR-156-Pfad bleibt.
- **Keine Voll-Provisioning-Automation** (Terraform/ARC) — nur das 30-Zeilen-Bootstrap-Skript (Destillat aus Runbook §3).
- **Kein neues Statusmodell / keine zweite Runner-Wahrheit** — `hosts.yaml` bleibt einzige SSoT, `ALLOWED`-Mengen werden daraus geparst, nie hartcodiert dupliziert.
- **Keine Entscheidung über public/private-Sichtbarkeit der Repos** (würde Minuten-Frage auflösen, ist aber eigene Governance-Frage).
- **Kein Rückbau des Staging-Hosts** — nur der konsumentenlose Runner-Service.

### 5.5 Artefakte

| Artefakt | Neu/Geändert | Owner | Normativ? | Lebenszyklus | Risiko |
|---|---|---|---|---|---|
| shared-ci-PR: Deploy-Steps verzweigen an `deploy_runs_on \|\| runs_on` (AD-1-Fix) + Fail-fast-Guard gegen plain `self-hosted` bei CI/Build | Geändert | shared-ci-Owner | ja | Tag-Bump, Consumer-Canary Pflicht | mittel |
| shared-ci-Default `runs_on: ubuntu-latest` (statt `self-hosted`) in `_ci-python.yml` + `_deploy-unified.yml` | Geändert | shared-ci-Owner | ja | Breaking-Change-Prozess, gestaffelt | mittel |
| ADR-257 Rev 4 (Mechanismus-Ersetzung + neues Kill-Gate, §13) | Geändert | Achim | ja | ADR-Lifecycle, 2. Owner-Review | niedrig |
| `infra/scripts/bootstrap_ci_runner.sh` (Minimal-Destillat Runbook §3) | Neu | Achim | nein | lebt mit Opt-out-Pfad | niedrig |
| `hosts.yaml`: `consumers:`-Feld, staging-ci-Eintrag → `deregistered`, Kommentar-Bereinigung | Geändert | Registry-CODEOWNERS | ja | SSoT | niedrig |
| Fleet-Scan (scheduled, platform): parst `with.runs_on`/`deploy_runs_on` aller Fleet-Workflows via API, diffed gegen hosts.yaml, zählt Opt-outs, prüft Runner-Konsumenten | Neu | Achim | nein (Mess-Gate) | wire-before-extend: existiert erst nach 1 rotem Testlauf | mittel |
| billing-hub#30 / recruiting-hub#17: Kommentar-Drift fixen, erst nach shared-ci-Fix + Build-Beweis mergen | Geändert | Achim | — | einmalig | niedrig |
| travel-beat-Drift-Fix (`runs_on: ubuntu-latest` explizit) + Runner-Deregistrierung, selber PR-Zug wie Rev 4 | Geändert | Achim | — | einmalig | niedrig |

### 5.6 Datenmodell (minimal)

`hosts.yaml` Runner-Eintrag, neues Feld: `consumers: [<repo>/<workflow>#<input>, …]` — Pflicht bei `status: online`; leer ⇒ Fleet-Scan rot („Runner ohne Konsument"). Keine zweite Wahrheit: Der Fleet-Scan **misst** die realen Konsumenten via API und diffed gegen die Deklaration; bei Widerspruch gewinnt die Messung (Befund), nie die Deklaration.

### 5.7 Prozessmodell (Rollout-Lifecycle)

1. **Gate-Phase (MVC, §5.9):** shared-ci-AD-1-Fix → Consumer-Canary auf billing-hub@feature-ref → 1 echter `workflow_dispatch`-Deploy (staging) mit Misch-Config → Minuten-Baseline (Human-Item C13).
2. **Pilot-Merge:** #30/#17 (Kommentare gefixt) mergen; nächsten echten Deploy beobachten.
3. **Amendment:** ADR-257 Rev 4 per PR (2. Owner-Review, platform-Ruleset); im selben Zug travel-beat-Drift-Fix + Runner-Deregistrierung + hosts.yaml + Bootstrap-Skript.
4. **Fleet-Welle:** Default-Flip in shared-ci + Tag-Bump; Consumer gestaffelt (ADR-270-Muster), Preflight je Repo: Tag-Version kennt `deploy_runs_on`? (H3, wedding-hub `@v1.0.5`), `deploy_runs_on: prod-server` explizit setzen wo fehlend (coach/wedding/pptx/weltenhub deployen heute auf plain `self-hosted`!).
5. **Mess-Betrieb:** Fleet-Scan scharf; Opt-out-Zähler ≥3 ⇒ Scan wird rot mit „Bootstrap-Automation jetzt fällig".
6. **Off-Ramp:** Dieses Doc → ADR-257 Rev 4 (Quelle vermerken); bei Kill: sunset + Alternative B.

### 5.8 Enforcement-Modell

| Regel | Level | Mechanismus | Owner | Ausnahme? |
|---|---|---|---|---|
| E1: CI/Build nie auf Prod-Host | hart | Code-Default `ubuntu-latest` + Fail-fast-Guard **in** der shared-ci-Familie (reist mit SHA-Tag, nicht umgehbar ohne Familienaustritt) | shared-ci-Owner | Opt-out nur via `ci-nonprod` |
| E2: plain `self-hosted` für CI/Build verboten | hart | derselbe Guard (bricht Job ab); NICHT der per-Repo-Label-Check (strukturell blind für `with.runs_on`, C11 — wird nicht fleet-kopiert) | shared-ci-Owner | nein |
| E3: Opt-out nur getrackt | Review + Scan | Issue-Label `runner-optout` + `hosts.yaml consumers:`; Fleet-Scan zählt, ≥3 ⇒ rot | Achim | — |
| E4: Runner ohne Konsument existiert nicht | Scan | Fleet-Scan diffed hosts.yaml-`consumers` gegen reale Nutzung | Achim | — |
| E5: Kill-Gate maschinenlesbar | Governance | Frontmatter-Kriterien + Kill-Gate-Wächter-Routine (existiert, live) | Achim | 1× 30 Tage |

**Ehrliche Enforcement-Grenze:** E3/E4 existieren erst, wenn der Fleet-Scan gebaut, verdrahtet und einmal absichtlich rot gelaufen ist (wire-before-extend, KONZ-015-Lehre). Bis dahin sind sie Review-Disziplin, kein Exit-Code — das wird nicht als geschlossen verkauft.

### 5.9 Minimal Viable Concept

1. **shared-ci-PR (AD-1-Fix):** Deploy-Step-Conditions von `inputs.runs_on` auf `deploy_runs_on || runs_on` umstellen; Fail-fast-Guard einbauen. Consumer-Canary: billing-hub-PR gegen feature-ref grün ziehen (Memory-Regel „Reusable-WF vor Merge auf Consumer verifizieren").
2. **Ein echter Beweis:** billing-hub `workflow_dispatch` (target staging) mit `runs_on: ubuntu-latest` + `deploy_runs_on: prod-server` — Build **und** Deploy-Step-Pfad im Log verifizieren (atomic-sync lokal, kein SSH-Loopback). Vorher prüfen: `DEPLOY_SSH_FINGERPRINT`-Secret-Frage (C12) wird durch den Fix obsolet oder muss gesetzt werden.
3. **Minuten-Baseline (Human):** `gh auth refresh -s user` → Billing-API → Plan/Verbrauch/Spending-Limit dokumentiert in #1217.

Bewusst NICHT im MVC: Default-Flip, Fleet-Welle, Fleet-Scan, Runner-Deregistrierung, Rev 4. **Erfolg:** die drei Kill-Gate-Bedingungen (a)–(c) erfüllt. **Rückbau:** Consumer bleiben auf altem Tag; kein Artefakt des MVC ist irreversibel.

### 5.10 Full Concept

MVC + Default-Flip in shared-ci, Fleet-Welle über alle 10 Hubs (inkl. explizites `deploy_runs_on: prod-server` bei coach/wedding/pptx/weltenhub — dort deployt heute plain `self-hosted`), Fleet-Scan mit Opt-out-Zähler und Konsumenten-Diff, ADR-257 Rev 4, travel-beat-Bereinigung (Drift-Fix + Deregistrierung), `bootstrap_ci_runner.sh`, Kommentar-/Runbook-/hosts.yaml-Bereinigung (M28-7), scheduled Minuten-Check mit Schwellwert-Alarm.

## 6. Adversariale Analyse (blinde Agenten, unverdünnt in den Agenten-Reports; hier kondensiert)

**Diabolus (Top-Angriffe):** AD-1 Deploy-Mechanik-Flip via `inputs.runs_on` (kritisch, verifiziert — auch durch eigene Session-Reads); AD-2 Label-Check blind für `with.runs_on`-Inputs; AD-3 „Fleet-Default" existiert nur als Prosa, Code-Default bleibt `self-hosted` (Doppelquelle, Code gewinnt); AD-4 korrelierter Fleet-Ausfall bei Minuten-Erschöpfung/GitHub-Incident, Gate derzeit nicht ausführbar; AD-5 Rev 4 als getarnte Supersession + Selbst-Immunisierung des Kill-Gates; AD-6 Opt-out-Kriterium ohne Messmechanismus, Layer-Cache-Argument durch `type=gha` entkräftet; AD-7 Zombie-Runner + kein Bootstrap = schlechteste Kombination; AD-8 Kommentar-Drift schon im Rollout-PR.

**Maintainer-2028 (Top-Verrottungen):** M28-1 die fleet-weite Label-Check-Zusage wird zum dritten Mal gebrochen (2× belegt: REC-2/3 und Runbook §4 liegen als ausbuchstabierter Einzeiler seit 18 Tagen unumgesetzt, `ALLOWED_EXTRA=set()` vs. hosts.yaml divergent); M28-2 Backslide auf plain `self-hosted` unter Incident-Druck → halbe Build-Flotte 2028 wieder auf dem 8-GB-Prod-Host; M28-3 travel-beat-Runner als Waisenkind, beim Staging-Incident gelöscht; M28-4 Kill-Gate ohne Aktuator (Hygiene-Check nie gebaut; ADR-201/209 als Präzedenz für ewiges in-progress); M28-5 „≥3 Opt-outs"-Schwelle ohne Zähler; M28-6 Fleet-Default auf ungemessenem Minuten-Fundament; M28-7 Stale-Kommentar-Kaskade (Runbook `proposed`, PR-Kommentare, hosts.yaml-Note).

**Konfliktmatrix (Pflicht, belegte Dissense):**

| K | Steelman sagt | Diabolus/M28 sagt | Synthese-Entscheid |
|---|---|---|---|
| K1 | „0 Zeilen shared-ci-Änderung nötig — ubuntu ist First-Class" | AD-1: Deploy-Verzweigung mechanisch falsch für Misch-Config | **Diabolus gewinnt.** MVC-Schritt 1 = shared-ci-Fix; #30/#17 bis dahin blockiert |
| K2 | „Kosten ehrlich als Gate internalisiert" | AD-4/M28-6: Gate nicht ausführbar (kein user-Scope) ⇒ wird gewaived | **Beide.** Gate bleibt, wird aber Kill-Gate-Bedingung (c) mit benanntem Kommando + Human-Item, nicht Absichtserklärung |
| K3 | Entwurf: „Bootstrap nicht bauen <3 Repos" | AD-7 + M28-3/5: Zombie ohne Skript + Schwelle ohne Zähler | **Entwurf revidiert.** Minimal-Skript einchecken, Runner deregistrieren, Zähler = Fleet-Scan |
| K4 | „Amendment erfüllt den Geist des ADR besser als der Buchstabe" | AD-5: getarnte Supersession, Kill-Gate-Umschreibung = Selbst-Immunisierung | **Synthese.** Rev 4 erkennt die Falsifikation ausdrücklich an (Kill-Gate hat funktioniert), ersetzt den Mechanismus-Teil transparent; Alternative „neues ADR" als Option in §13 dokumentiert; 2. Owner-Review erzwungen |
| K5 | „Enforcement existiert schon (Label-Check + ALLOWED_EXTRA-Hook)" | AD-2/M28-1: Check strukturell blind + Redistributions-Latenz über 10 Repo-Kopien | **Diabolus/M28 gewinnen.** Enforcement neu geschnitten: in-Familie-Guard + zentraler Fleet-Scan; der per-Repo-Check wird NICHT fleet-kopiert |

## 7. Deep-Dive (Kernachsen)

**SSoT/Drift:** Drei konkurrierende Wahrheiten existieren heute schon: ADR-Prosa („Pilot travel-beat"), hosts.yaml-Note („wird hierher gelenkt") und Code (nichts wird gelenkt). Das Konzept reduziert auf zwei Träger mit klarer Rangfolge: Code-Default in der shared-ci-Familie (erzwingend) + hosts.yaml (deklarativ, per Scan gegen Realität gedifft). Hartcodierte `ALLOWED`-Mengen in Repo-Kopien werden abgeschafft statt synchronisiert.

**Enforcement:** Die Lehre aus C11 ist strukturell: Ein Check, der nur `job["runs-on"]` parst, kann eine Fleet, die über `workflow_call`-Inputs routet, nicht schützen — egal wie oft man ihn kopiert. Der einzige Ort, der jede Nutzung sieht, ist die Familie selbst (Guard) plus ein zentraler API-Scan (Messung). Das folgt dem KONZ-015-Muster „Forcing-Function im unüberspringbaren Pfad".

**Kosten/Verfügbarkeit:** Der hosted Pfad tauscht einen lokalen, unkorrelierten Failure-Mode (ein Host verrottet) gegen einen korrelierten (Minuten-Erschöpfung/GitHub-Incident trifft alle 10 Hubs gleichzeitig, und der Build sitzt im Deploy-Pfad). Mitigation: gemessene Baseline vor Accept (Kill-Gate c), scheduled Schwellwert-Check danach, und ein reproduzierbarer Opt-out als Break-Glass — deshalb ist das Bootstrap-Skript kein Nice-to-have, sondern die Fluchttür des korrelierten Modus.

**Migration:** Reihenfolge ist Risikosteuerung: erst Mechanik-Fix (K1), dann Beweis, dann Amendment, dann Welle. Die vier Hubs ohne jegliche `runs_on`-Inputs (coach/wedding/pptx/weltenhub) sind die riskantesten — dort ändert die Welle auch das *Deploy*-Placement von plain `self-hosted` auf explizit `prod-server` (heute nur zufällig richtig, weil kein zweiter Runner registriert ist) — plus Tag-Preflight (H3).

## 8. Alternativen

**B — Pet-Runner-Pfad zu Ende bauen (Bootstrap-Automation + ~10 Registrierungen).** Erfüllt ADR-257 wörtlich; volle Kontrolle über Cache/Minuten. Aber: O(n) manuelle Pflege auf User-Account ohne Org-API, gesamte Betriebslast (Härtung, Hygiene, Patch) bleibt, und die Pilot-Empirie zeigt null organische Adoption. **Bleibt als dokumentierter Fallback des Kill-Gates** — nicht als Default.

**C — Hybrid nach Job-Klasse:** `ci.yml` hosted, `deploy.yml`-Build self-hosted (`ci-nonprod`). Minimiert Minuten-Risiko für die teuersten Jobs. Aber: behält die komplette Pet-Betriebslast für genau die Job-Klasse, die am seltensten läuft, und braucht trotzdem den AD-1-Fix + Registrierungen. Verworfen als Default; entspricht faktisch dem Opt-out-Pfad, der ja bleibt.

**D — Status quo + Symptomfixes** (Container-Limits auf prod-server, Swap erhöhen). Adressiert #1078-Symptome, lässt die Blast-Radius-Klasse intakt, widerspricht accepted ADR-257. Verworfen.

## 9. Out-of-the-Box

1. **Kill-Gate als Falsifikations-Erfolg framen:** Rev 4 dokumentiert ausdrücklich „Kill-Gate (ii) hätte gefeuert; die Falsifikation wird anerkannt" — das erste Mal, dass ein Kill-Gate der Org sichtbar *funktioniert* statt still überfahren zu werden. Präzedenzwert für alle künftigen Gates (gegen M28-4-Klasse).
2. **Der Fail-fast-Guard als Familien-Gen:** Ein Guard-Step, der in *jeder* shared-ci-Familie mitreist, ist das erste Enforcement der Org, das Redistributions-Latenz strukturell nicht kennt — Kandidat für weitere Invarianten (z. B. KONZ-015s Dead-Reference-Gate).
3. **Public-Repos-Frage als Kosten-Nullifier:** Öffentliche Repos hätten unbegrenzte hosted Minuten. Eine bewusste Sichtbarkeits-Entscheidung pro Hub würde die Minuten-Achse komplett auflösen — eigene Governance-Frage, hier nur benannt.
4. **Depot-Optimierung statt Pet:** Sollte Build-Dauer je zum Problem werden, sind gemanagte Runner-Dienste (größere hosted Runner, Build-Cloud) der nächste Prüfschritt vor jedem Rückfall auf Pets — Prüfreihenfolge im Opt-out-Issue-Template verankern.

## 10. Befunde

| ID | Rolle | Befund (1 Satz) | Evidenz | Schwere | Confidence |
|---|---|---|---|---|---|
| F-1 | Session | Deploy-Steps in `_deploy-unified.yml` verzweigen an `inputs.runs_on` — Misch-Config schaltet Prod-Deploy auf ungetesteten SSH-Loopback | C7 (E2) | **kritisch** | hoch |
| F-2 | Session | Pilot travel-beat routet nichts nach `ci-nonprod`; Build matcht nichtdeterministisch beide Runner | C8/C9 (E2/E3) | hoch | hoch |
| F-3 | Session | Org-Runner auf User-Account nicht verfügbar (404) — Pet-Pfad ist strukturell O(n) manuell | C8 (E3) | hoch | hoch |
| F-4 | Session | 6 von 10 Hub-`ci.yml`s bereits `ubuntu-latest`; Schmerz konzentriert auf `deploy.yml`-Build | C10 (E2) | mittel | hoch |
| F-5 | Diabolus | Label-Check parst nur `job["runs-on"]` — blind für `with.runs_on`-Inputs der gesamten Fleet | C11 (E2) | **kritisch** | hoch |
| F-6 | Diabolus | shared-ci-Code-Default bleibt `self-hosted` — „Fleet-Default hosted" wäre reine Prosa | C7 (E2) | hoch | hoch |
| F-7 | Diabolus | billing-hub fehlt `DEPLOY_SSH_FINGERPRINT`; PR-Kommentare widersprechen PR-Code | C12/C5 (E2/E3) | hoch | hoch |
| F-8 | Diabolus/M28 | Minuten-Budget unverifizierbar (Token ohne user-Scope) — Fleet-Default stünde auf H-Fundament | C13 (E3) | hoch | hoch |
| F-9 | M28 | Runbook §4-Zusage (`ALLOWED_EXTRA`-Erweiterung) liegt als Einzeiler 18 Tage unumgesetzt — dritte Wiederholung derselben Zusage wäre Papier | C2/C11 (E2) | hoch | hoch |
| F-10 | M28 | 4 Hubs (coach/wedding/pptx/weltenhub) deployen heute auf plain `self-hosted` — nur zufällig richtig geroutet | C10 (E2) | hoch | hoch |
| F-11 | M28 | Kill-Gate-Datenquelle (Hygiene-Check) wurde nie gebaut; Kill-Gates ohne Aktuator werden still überfahren (Präzedenz ADR-201/209) | Agent-E2 | mittel | mittel-hoch |

## 11. Top-5-Risiken

1. **Merge von #30/#17 vor dem shared-ci-Fix** → erster Prod-Deploy läuft über nie getesteten SSH-Loopback mit fehlendem Fingerprint-Secret (F-1/F-7). Mitigation: PRs explizit blockiert bis MVC-1/2.
2. **Minuten-Erschöpfung als korrelierter Fleet-Deploy-Freeze** (F-8, AD-4). Mitigation: Kill-Gate (c) vor Accept, scheduled Schwellwert-Check, Break-Glass = Opt-out-Pfad mit Skript.
3. **Backslide auf plain `self-hosted` unter Incident-Druck** (M28-2) → Builds wieder auf 8-GB-Prod-Host, unbemerkt. Mitigation: Fail-fast-Guard in der Familie (nicht umgehbar), nicht der blinde per-Repo-Check.
4. **Enforcement bleibt Papier wie 2× zuvor** (F-9, M28-1). Mitigation: Guard + Fleet-Scan sind Teil der Rev-4-PR-Kette mit wire-before-extend-Nachweis (1 absichtlich roter Lauf), nicht Follow-ups.
5. **Governance-Präzedenz „Kill-Gate wird umgeschrieben, wenn es greift"** (AD-5). Mitigation: Rev 4 erkennt die Falsifikation ausdrücklich an; §13 dokumentiert die Alternative „neues ADR"; 2. Owner-Review entscheidet die Form.

## 12. Empfehlungen (konkret, verifizierbar)

- **REC-1 (Blocker):** In `iilgmbh/shared-ci/_deploy-unified.yml` alle Deploy-Step-Conditions (Z. 313/367/383/395-Klasse) von `inputs.runs_on` auf `inputs.deploy_runs_on || inputs.runs_on` umstellen; Consumer-Canary billing-hub@feature-ref vor Tag-Bump. Bis dahin: #30/#17 nicht mergen (Kommentar in beide PRs).
- **REC-2:** Fail-fast-Guard-Step in `_ci-python.yml` + `_deploy-unified.yml`: Abbruch, wenn effektiver CI/Build-Runner-Kontext plain `self-hosted` ohne `ci-nonprod`/hosted-Label ist.
- **REC-3:** Code-Default `runs_on` → `ubuntu-latest` in beiden Familien (eigener, gestaffelter Bump nach MVC-Beweis).
- **REC-4:** `workflow_dispatch`-Beweis-Lauf billing-hub (staging) mit Misch-Config; Log-Nachweis „atomic-sync lokal" in #1217 verlinken.
- **REC-5 (Human):** `gh auth refresh -s user` → Billing-Baseline (Plan, Verbrauch, Spending-Limit) als Kommentar in #1217.
- **REC-6:** ADR-257 Rev 4 mit ausdrücklicher Falsifikations-Anerkennung; im selben PR-Zug: travel-beat-Drift-Fix, `staging-ci`-Deregistrierung, `hosts.yaml`-`consumers:`-Feld, `bootstrap_ci_runner.sh`, Runbook-Header-Fix.
- **REC-7:** Fleet-Scan (scheduled, platform) inkl. Opt-out-Zähler (≥3 ⇒ rot mit „Bootstrap-Automation fällig") — Existenznachweis per absichtlich rotem Lauf.
- **REC-8:** Fleet-Welle mit Pflicht-Preflight je Repo (Tag kennt `deploy_runs_on`?; `deploy_runs_on: prod-server` explizit bei coach/wedding/pptx/weltenhub).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidungsempfehlung:** Kernthese (§5.1) annehmen — als **gehärtete Fassung** (K1–K5-Revisionen eingearbeitet), Form: ADR-257 **Rev 4** mit ausdrücklicher Anerkennung der Mechanismus-Falsifikation. Alternative Form (falls der 2. Owner-Review AD-5 höher gewichtet): neues ADR mit `supersedes: [ADR-257]` bei identischem Inhalt. **Human-Gates:** ADR-Accept (Achim), Minuten-Baseline (REC-5), Merge-Freigabe #30/#17 nach REC-1/REC-4.

**Kill-Gate (messbar, datiert — Stichtag 2026-09-24, aligned mit ADR-257):** siehe `kill_criteria` im Frontmatter. Exception-Budget: max. eine begründete 30-Tage-Verlängerung.

| Kriterium | Status (offen/erfüllt/verworfen) | Beleg |
|---|---|---|
| (a) shared-ci-Deploy-Verzweigung gefixt + Consumer-Canary grün | offen | — |
| (b) 1 echter Build+Deploy mit Misch-Config grün (billing-hub, dispatch/staging) | offen | — |
| (c) Minuten-Baseline gemessen, Prognose <80% Freikontingent ODER Spending-Limit-Entscheid dokumentiert | offen | — |

**30/60/90:** T+30: MVC komplett (REC-1/2/4/5), #30/#17 gemergt, erster echter Deploy beobachtet. T+60: Rev-4-PR-Zug gemergt (REC-6), Default-Flip (REC-3) auf ≥3 Consumern. T+90 (= Stichtag): Fleet-Welle abgeschlossen oder Kill-Gate-Entscheid; Fleet-Scan live mit einem nachgewiesenen roten Testlauf.

---

## Changelog

- 2026-07-16: Initial (T3, aus platform#1217). Drei blinde Agenten + Konfliktmatrix K1–K5;
  Entwurfs-These in K3 revidiert (Minimal-Bootstrap wird eingecheckt, Zombie-Runner deregistriert).
