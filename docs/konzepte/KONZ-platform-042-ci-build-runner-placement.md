---
concept_id: KONZ-platform-042
title: Cross-Repo CI/Build-Runner-Placement — ubuntu-latest vs. ci-nonprod vs. Bootstrap-Automation
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: [platform:ADR-257, platform:ADR-222, platform:ADR-156, platform:ADR-289, platform:ADR-248]
adr_threshold: "Amendment zu ADR-257 nötig (Alternative E wird zur Ausweichoption zurückgestuft, neuer Default-Pfad ubuntu-latest+SSH ergänzt). Kein neuer Org-ADR — die Placement-Frage bleibt in ADR-257s Geltungsbereich."
review_by: 2026-09-10
kill_criteria: "K1-K4 in §13, UND-verknüpft, Stichtag 30 Tage nach Merge dieses Konzepts. Bei Nichterfüllung: Rückfall auf ADR-257 Alternative E (self-hosted staging-ci) als alleinigen Pfad, dieses Konzept auf superseded."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "platform#1217 (Issue-Body)", commit_or_pr: "https://github.com/achimdehnert/platform/issues/1217", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-257-ci-host-isolation-non-prod-runner.md, commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C3, source_path: infra/host-maintenance/runner-nonprod-runbook.md, commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C4, source_path: "infra/hosts.yaml (prod-Block, Zeile 24-56)", commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C5, source_path: "infra/hosts.yaml (staging-Block, Zeile 116-150)", commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C6, source_path: "infra/hosts.yaml (netcup-Block, Zeile 191-244)", commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C7, source_path: "infra/hosts.yaml (prod-b-Block, Zeile 57-115)", commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C8, source_path: "infra/hosts.yaml (runners:-Sektion, Zeile 252-320)", commit_or_pr: origin/main@9cd5f89d, opened_in_session: true}
  - {claim_id: C9, source_path: "platform#1078 (Issue-Body, offen)", commit_or_pr: "https://github.com/achimdehnert/platform/issues/1078", opened_in_session: true}
  - {claim_id: C10, source_path: "billing-hub#30 (PR-Body + Files-Diff ci.yml/deploy.yml)", commit_or_pr: "https://github.com/achimdehnert/billing-hub/pull/30", opened_in_session: true}
  - {claim_id: C11, source_path: "recruiting-hub#17 (PR-Body)", commit_or_pr: "https://github.com/achimdehnert/recruiting-hub/pull/17", opened_in_session: true}
  - {claim_id: C12, source_path: "billing-hub Secrets-Liste (DEPLOY_HOST/USER/SSH_KEY seit 2026-03-11)", commit_or_pr: "gh secret list -R achimdehnert/billing-hub", opened_in_session: true}
  - {claim_id: C13, source_path: "shared-ci/.github/workflows/_deploy-unified.yml (runs_on/deploy_runs_on-Mechanik, Zeile 64-417)", commit_or_pr: "shared-ci@main", opened_in_session: true}
  - {claim_id: C14, source_path: "platform#1845 (Issue-Body, geschlossen 2026-08-10)", commit_or_pr: "https://github.com/achimdehnert/platform/issues/1845", opened_in_session: true}
  - {claim_id: C15, source_path: "shared-ci git log _deploy-unified.yml (11 Commits seit v1.0.0)", commit_or_pr: "shared-ci@main", opened_in_session: true}
  - {claim_id: C16, source_path: "Adversarialer Fan-out: 3 unabhängige Agenten (Steelman/Advocatus-Diabolus/Maintainer-2028), blind gegeneinander", commit_or_pr: "diese Session, 2026-08-11", opened_in_session: true, provenance: subagent-fanout}
created: 2026-08-11
---

# KONZ-platform-042 — Cross-Repo CI/Build-Runner-Placement

**Tier-Entscheidung: T3** — Cross-Repo (≥9 Hubs + shared-ci + platform-Infra betroffen), SSoT-Frage
(`infra/hosts.yaml` als Runner-Register), Amendment-Kandidat für ADR-257 (Placement-Achse).
Auto-Eskalations-Trigger "Cross-Repo" + "SSoT-Verschiebung" greifen unabhängig von der
Selbsteinstufung des Auftrags-Issues. Adversarialer Fan-out mit drei unabhängigen internen Agenten
(Steelman / Advocatus Diabolus / Maintainer-2028) am 2026-08-11, Konfliktmatrix §6.4.

## 1. Executive Summary

**Basis-Korrektur zuerst:** Das Auftrags-Issue (#1217, erstellt 2026-07-16) beschreibt die Lage
korrekt für seinen Zeitpunkt, ist aber inzwischen auf zwei Achsen überholt. (a) Die als Auslöser
zitierte `prod-server`-RAM-Überbuchung (#1078, 3,7x Committed_AS/CommitLimit) ist durch eine externe
Freeze-Episode (#1314) + Migrationswelle nach `prod-b` **entspannt** (46% RAM statt vormals 100%
Swap) — die Dringlichkeit ist gesunken, das strukturelle Argument (geteilte Engine = Blast-Radius)
bleibt aber unverändert gültig. (b) Der im Issue nur als CI-Job getestete `ubuntu-latest`-Pfad
existiert in `shared-ci/_deploy-unified.yml` bereits **vollständig für Build UND Deploy** (SSH-Pfad
über `scp-action`+`ssh-action`, seit shared-ci#22/~2026-07-10) — eine vierte, im Issue nicht genannte
Option, die weder einen neuen Host noch Bootstrap-Automation braucht. Zugleich ist der bisher
einzige `ci-nonprod`-Host (`staging`) selbst in eine neue Ressourcenkrise gelaufen (Swap 100%,
gemessen 2026-07-30) — Alternative E aus ADR-257 degradiert gerade, während dieses Konzept läuft.

**Kernempfehlung:** `ubuntu-latest` wird der **Default für die Build/Test-Phase** der gesamten
Flotte. Der SSH-Deploy-Pfad wird **nicht** pauschal für den Restart-Schritt übernommen — er hat
zwei dokumentierte Produktions-Incidents (2026-07-10, 2026-08-09) durch dieselbe Docker-Action-
Regressionsklasse, deren geforderter Regress-Wächter-Lint noch nicht existiert. `deploy_runs_on:
prod-server` bleibt vorerst Pflicht, bis der Lint gebaut UND mindestens ein echter Prod-Deploy über
den SSH-Pfad beobachtet ist (schließt die seit 25 Tagen offene Lücke in billing-hub#30/recruiting-
hub#17s eigenem Testplan). Die `netcup`-Frage wird **nicht** implizit mitentschieden — ADR-289 R3
bleibt bewusst offen, dieses Konzept trifft dazu keine Aussage. Bootstrap-Automation für
self-hosted-Runner (REC-10) wird **nicht** fallengelassen, sondern auf einen kleineren Scope
reduziert: nur für den dokumentierten Ausnahmefall (netzwerk-isolierte Ressourcen), nicht als
Flotten-Investition.

**Wichtigste Unsicherheit:** Ob der SSH-Deploy-Pfad nach dem 2026-08-10-Fix stabil bleibt, ist
unbewiesen — er ist bereits zweimal durch dieselbe Fehlerklasse gebrochen. Der Kill-Gate-Zeitraum
(30 Tage) ist bewusst kurz gewählt, um diese Unsicherheit schnell zu klären, statt sie zu vererben.

## 2. Scope & Evidenzbasis

**In dieser Session real geöffnet** (E2/E3, siehe `evidence_manifest`): Issue #1217, ADR-257,
Runbook, `infra/hosts.yaml` (5 Host-Blöcke + Runner-Sektion), Issue #1078, PR billing-hub#30 (Body +
Diff), PR recruiting-hub#17 (Body), `gh secret list` billing-hub, `shared-ci/_deploy-unified.yml`
(Zeile 64-417), Issue #1845, `git log` auf `_deploy-unified.yml`.

**Annahmen (markiert):** Dass `recruiting-hub` dieselben `DEPLOY_HOST`/`DEPLOY_USER`/`DEPLOY_SSH_KEY`-
Secrets wie billing-hub trägt, wurde **nicht** geprüft (H — billigster Check: `gh secret list -R
achimdehnert/recruiting-hub`). Dass der Regress-Wächter-Lint aus #1845 noch nicht existiert, ist ein
Negativ-Beleg aus dem Issue-Text selbst, nicht durch eigene Grep-Suche auf `_deploy-unified.yml`
oder `.github/workflows/` bestätigt (H — billigster Check: `grep -rn "runs.using: docker" shared-ci/`
bzw. Suche nach einem neuen Lint-Workflow).

**Nicht prüfbar in dieser Session:** Ob der Hygiene-Check aus ADR-257 REC-6/8 ("scheduled read-only
Check je Runner-Host") tatsächlich läuft — in keiner geöffneten Datei referenziert, aber auch nicht
aktiv widerlegt (kein Cron-Job-Verzeichnis durchsucht).

## 3. Infrastruktur-Fit

Dieses Konzept betrifft Infra-Platzierung, nicht die Klickdummy-/ADR-211-Domäne — die
Standard-Checkliste (I1-I4, Genesor-Lifecycle, Parity-Bridge) ist hier **nicht anwendbar** und wird
bewusst übersprungen (kein Klickdummy-Bezug). Stattdessen die für diese Domäne relevanten Bausteine:

| Infrastruktur-Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---:|---|---|---|---|
| ADR-257 (CI-Host-Isolation) | ✓ | Kill-Gate, Label-Gate | Amendment: Default-Pfad ergänzen | mittel | Kill-Gate 2026-09-24 hängt an Runner-Registrierung, die dieses Konzept zurückstuft — muss im Amendment adressiert werden |
| ADR-222 (CI-Workflow-Familien) | ✓ | unverändert | — | niedrig | Workflow-Achse bleibt unberührt, nur Runner-Input `runs_on` wird anders gesetzt |
| ADR-156 (Deploy-Pipeline) | ✓ | Deploy bleibt auf `prod-server` legitim | — | niedrig | Konzept ändert daran vorerst nichts |
| ADR-289 (netcup-Rollen) | ✓ | R1 unverändert | **nicht** | hoch, wenn ignoriert | R3 (CI-Runner) bleibt explizit vertagt — dieses Konzept trifft dazu KEINE Aussage, um keinen impliziten Owner-Beschluss vorwegzunehmen |
| `infra/hosts.yaml` (Runner-SSoT) | ✓ | als Register | neuer Eintrag `runs_on`-Policy pro Repo (optional, nicht Pflicht) | niedrig | bleibt SSoT, keine zweite Wahrheit geschaffen |
| `runner-label-check.yml` (Label-Gate) | ✓ | unverändert | ggf. `ALLOWED_EXTRA` um Kommentar ergänzen | niedrig | Enforcement bleibt beim bestehenden Gate |
| `_deploy-unified.yml` (shared-ci) | ✓ | Build-Zweig sofort | Deploy-Zweig NICHT sofort (Kill-Gate-gebunden) | hoch | zentrale, von 48 Repos konsumierte Datei mit dokumentierter Regressionshistorie |

## 4. Steelman

*(Ergebnis des unabhängigen Steelman-Agenten, ungekürzt.)*

Diese Entscheidung ist eine ehrliche Anerkennung dessen, was der bereits gebaute Mechanismus
leistet, statt eine parallele Investition in ein "Pet"-Runner-Modell fortzuschreiben, das strukturell
überlastet ist. Der SSH-Composite-Pfad in `_deploy-unified.yml` existiert bereits produktionsreif
seit shared-ci#22 (vor Issue #1217), ist also kein neues Risiko, sondern ungenutzte, längst
vorhandene Kapazität — und billing-hub PR#30 zeigt live, dass der hybride Split (Build auf
`ubuntu-latest`, Deploy-Restart gepinnt) bereits funktioniert und die Secrets seit März bereitstehen.
Der Verzicht auf eine Runner-Verlagerung staging→netcup ist korrekt an ADR-289 R3 gebunden
("vertagt, kein Owner-Beschluss") und vermeidet damit genau die Art von unautorisiertem Scope-Creep,
vor der die eigene Governance warnt. Das Zurückstellen der Bootstrap-Automation ist konsequent: wenn
die Flotte überwiegend auf GitHub-hosted wechselt, sinkt der ROI einer Self-Hosted-Provisioning-
Investition automatisch. Besonders stark: die Entscheidung entlastet den `staging`-Host genau in dem
Moment, wo Ground-Truth-Daten (100% Swap, 2,3GB frei, Load 3,6) zeigen, dass er der eigentliche
Flaschenhals ist, und zieht die Konsequenz aus Issue #1078s eigener Kernempfehlung. Die
GHCR-Erneuerung im SSH-Pfad (frischer Login per Workflow-Token) ist eine echte Verbesserung
gegenüber dem in #1078 Befund 4 dokumentierten Credential-Poisoning-Muster.

## 5. Konzeptdefinition

**5.1 Kernthese** — Dieses Konzept sagt: `ubuntu-latest wird Default für Build/Test der gesamten
Flotte; der SSH-Deploy-Pfad wird als zweiter Schritt aktiviert, sobald ein Regress-Wächter existiert
und ein echter Prod-Deploy ihn verifiziert hat — bis dahin bleibt Deploy auf prod-server gepinnt.`

**5.2 Problem** — *Beobachtung:* billing-hub/recruiting-hub hängen 25 Tage mit offenen PRs, weil
`ci-nonprod` per-repo registriert werden muss und der einzige Host dafür (`staging`) selbst
ressourcenkritisch ist. *Interpretation:* Die im Issue gestellte Frage "ubuntu-latest vs. ci-nonprod
vs. Bootstrap-Automation" ist unvollständig — eine vierte Option (SSH-Deploy) existiert bereits.
*Hypothese:* Die Fleet-weite Registrierung von self-hosted Runnern (Bootstrap-Automation, REC-10)
ist die falsche Investition, wenn die meisten Repos gar keinen self-hosted Runner brauchen.
*Offene Frage:* Ob der SSH-Deploy-Pfad nach dem 2026-08-10-Fix stabil genug ist, um ihn zum
Fleet-Default zu machen — **nicht** in dieser Session klärbar, da er noch nie unter echter
Deploy-Last seit dem Fix beobachtet wurde.

**5.3 Zielbild** — Möglich wird: Build/Test-CI für neue und bestehende Repos ohne
Runner-Provisionierungs-Schritt. Sichtbar riskant wird: der SSH-Deploy-Pfad als Single-Point mit
Regressionshistorie, wenn er unkontrolliert Fleet-weit übernommen wird. Leichter wird die
Entscheidung "self-hosted ja/nein" pro Repo, weil die Default-Antwort jetzt "nein" statt "ja,
aber Runner fehlt" ist.

**5.4 Nicht-Ziele** — Löst NICHT: die GHCR-Credential-Leak-Wurzel (#1078 Befund 4, `docker logout`
fehlt in `deploy.sh`) — bleibt unabhängiges Ticket. Löst NICHT: die `netcup`-Rollenfrage (ADR-289
R3) — bewusst nicht Gegenstand. Kein neues System-of-Record: `infra/hosts.yaml` bleibt SSoT für
Runner, dieses Konzept fügt keine zweite Registrierungsquelle hinzu.

**5.5 Artefakte**

| Artefakt | Neu/Geändert | Owner | Normativ? | Generiert? | Lebenszyklus | Risiko |
|---|---|---|---:|---:|---|---|
| ADR-257 (Amendment) | Geändert | Achim Dehnert | ✓ | nein | lebt mit ADR | mittel |
| `shared-ci/.github/workflows/lint-no-docker-actions.yml` (NEU, Regress-Wächter) | Neu | Achim Dehnert | ✓ (Gate) | nein | dauerhaft | niedrig |
| `infra/host-maintenance/runner-nonprod-runbook.md` | Geändert (Status-Korrektur + §9 Realität) | Achim Dehnert | teilweise | nein | lebt mit Runbook | niedrig |
| `infra/hosts.yaml` | unverändert (kein neuer Eintrag zwingend) | Achim Dehnert | ✓ (SSoT) | nein | lebt mit Datei | niedrig |
| billing-hub#30 / recruiting-hub#17 | unverändert im Kern, Merge freigegeben | Achim Dehnert | — | nein | PR-Lifecycle | niedrig |

**5.8 Enforcement-Modell**

| Regel | Level | Mechanismus | Owner | Ausnahme? | Ablaufdatum nötig? |
|---|---|---|---|---:|---:|
| Build/Test-Default = `ubuntu-latest` | Review | PR-Review bei neuen `runs_on: self-hosted`-Workflows | Achim Dehnert | ja, dokumentierter Netzwerk-Bedarf | nein (Default, kein Ablauf) |
| Kein `runs.using: docker` in `_deploy-unified.yml` | CI-Gate (neu) | Regress-Wächter-Lint | Achim Dehnert | nein | — |
| Deploy bleibt auf `prod-server`, bis Kill-Gate erfüllt | Doku + Review | `deploy_runs_on: prod-server` explizit pinnen (bereits Praxis in billing-hub#30) | Achim Dehnert | nein vor Kill-Gate-Erfüllung | 30 Tage (Kill-Gate) |

**5.9 Minimal Viable Concept** — Genau diese Felder/Dateien: (1) ADR-257-Amendment-Absatz, der den
`ubuntu-latest`-Default für Build/Test dokumentiert und das Kill-Gate 2026-09-24 an "Escape-Hatch-
Runner bleibt für Ausnahmefälle registriert" statt "Fleet-weite Registrierung" umformuliert; (2)
Regress-Wächter-Lint in shared-ci (einzelner neuer Workflow, prüft `_deploy-unified.yml` + alle
Composite-Actions in `shared-ci/actions/` auf `runs.using: docker`); (3) billing-hub#30 und
recruiting-hub#17 mergen, `deploy_runs_on: prod-server` bleibt wie im Diff bereits gesetzt. Bewusst
NICHT drin: SSH-Deploy-Pfad als Default, netcup-Entscheidung, Bootstrap-Automation für die Flotte.
**Erfolgsnachweis:** beide PRs gemerged + nächster echter Deploy beider Repos grün (schließt den
offenen Testplan-Punkt). **Rückbau:** ADR-257-Amendment revertieren, `runs_on` in den betroffenen
Workflows zurück auf `ci-nonprod`/`self-hosted` — reiner Konfigurationsrückbau, kein Datenverlust.

**5.10 Full Concept** — Nach erfolgreichem MVC + 30 Tagen Regress-Wächter-Stabilität: SSH-Deploy-Pfad
wird zweiter Default für Repos ohne netzwerk-isolierten Bedarf, `deploy_runs_on` wird optional statt
Pflicht-Pin. Bootstrap-Automation wird nur noch für den dann klar umrissenen Ausnahmefall gebaut
(nicht Fleet-weit).

## 6. Adversariale Analyse

**6.1 😈 Advocatus Diabolus** *(Ergebnis des unabhängigen Agenten, ungekürzt)*

1. **Doppelquelle (Deploy-Pfad, `bestehende Lücke nicht geschlossen`):** Kein harter Cutover-Termin
   für den Abbau von `prod-server`, nur "schrittweise, sobald Repos wechseln" — zwei koexistierende
   Wahrheiten über "wo läuft Deploy" auf unbestimmte Zeit. billing-hub PR#30s Kommentar spricht
   fälschlich von "Non-Prod-Runner (staging-ci, Label ci-nonprod)", während der Code `ubuntu-latest`
   setzt — Code und Text sind im selben, ungemergten PR bereits inkonsistent.
2. **SSoT nur behauptet (ADR-257, `Governance-Lücke`):** Das Label-Gate erzwingt "kein CI auf
   prod-server" über den `ci-nonprod`-Runner; die Kandidaten-Entscheidung stuft ihn zur
   Ausweichoption zurück, ohne dass `ubuntu-latest` ein äquivalentes Enforcement-Gate erhält.
   Kill-Gate 2026-09-24 bleibt formal bestehen, obwohl die Entscheidung den Runner faktisch entwertet.
3. **SSoT nur behauptet (Runbook, `SSoT-Risiko`):** Frontmatter-Status "Entwurf" widerspricht
   ADR-257-Text "materialisiert".
4. **Tool wird zur Boundary (`neuer Failure-Mode`):** `_deploy-unified.yml` wird faktisch zur
   Prod-Verfügbarkeitsgrenze der Flotte erklärt — zwei dokumentierte Live-Incidents, Regress-Wächter
   existiert noch nicht.
5. **Manuelle Pflicht ohne Enforcement (`Operationalisierungsrisiko`):** Die Exception-Klausel
   "konkreter Bedarf für host-lokale Ausführung" nennt kein Prüfkriterium/Gate — jedes Repo kann sich
   analog attestieren und dauerhaft auf `prod-server` verbleiben.
6. **Formal erfüllen, praktisch umgehen:** Ein Team erfüllt die Entscheidung bereits durch
   `runs_on: ubuntu-latest` für CI/Test, während der riskantere Teil (Deploy/Restart) unverändert
   bleibt — recruiting-hub#17 benennt das selbst.
7. **"Sichtbar machen" schwächer als "verhindern":** #1078-Befund 4 (GHCR-Credential-Leak) bleibt
   offen und unberührt.
8. **Governance-Bypass (netcup, `unklare Ownership`):** ADR-289 R3 "vertagt" — die Entscheidung
   trifft implizit dieselbe Wahl (netcup nicht nutzen), ohne den geforderten Owner-Beschluss.
9. **Fallengelassene Automation als Verhinderungslücke:** REC-10 war der einzige Mechanismus, der
   Runner-Registrierung auditierbar statt manuell-fehleranfällig gemacht hätte.
10. **Unverifizierter Claim als Entscheidungsgrundlage:** billing-hub PR#30s Testplan-Punkt ist
    unchecked — die Entscheidung generalisiert einen nie production-verifizierten Pfad.

**6.2 🔮 Maintainer 2028** *(Ergebnis des unabhängigen Agenten, ungekürzt)*

- Kill-Gate 2026-09-24 hängt an einem Hygiene-Check-Nachweis, der nirgends belegt ist — der
  self-hosted-Pfad verliert unter diesem Konzept Aufmerksamkeit, genau während sein eigenes ADR ihn
  noch beobachtet sehen will.
- Der SSH-Deploy-Pfad ist zweimal in vier Wochen production-gebrochen (2026-07-10, 2026-08-09),
  derselbe Fehlermodus — Wiederholung ist die begründete Erwartung ohne Regress-Wächter.
- "Production-verifiziert" ist auch nach 25 Tagen nicht eingelöst (Testplan-Punkt unchecked).
- `staging` trägt den einzigen Pilot-Runner UND ist selbst in einer Swap-100%-Krise — bricht der
  Host, bricht der einzige Beleg, auf den sich das ADR-257-Kill-Gate stützen müsste.
- Runbook §9 ist real nur zu 1 von 4 Schritten umgesetzt, Schritt 3 lief bereits am Runbook vorbei
  (billing-hub/recruiting-hub nutzen ubuntu-latest statt des vorgesehenen self-hosted-Pfads).
- #1078 Befund 4 (GHCR-Leak) ist unabhängig vom Runner-Ort — ein Maintainer könnte fälschlich
  ableiten "Runner-Migration = Security-Hygiene erledigt".
- `prod`-RAM-Entspannung ist eine Momentaufnahme (manuelle Freeze-Episode), kein Gate verhindert
  erneutes Abrutschen.
- Bootstrap-Automation fallenlassen erzeugt eine Einmaligkeits-Falle: wird der Pilot-Runner neu
  aufgesetzt (z.B. weil `staging` kollabiert), gibt es keine wiederholbare, dokumentierte
  Registrierung mehr — nur Fragmente aus dieser Session.
- Vier Hosts mit je eigener ADR-Zuordnung (ADR-292/289/257/156), uneinheitliche `verified:`-Daten
  (2026-06-17 bis 2026-08-04) — kein erkennbarer einheitlicher Prüfzyklus.

**6.3 Synthese** — Alle drei Agenten konvergieren auf denselben materiellen Kern: der SSH-Deploy-Pfad
ist die eigentliche Risikoquelle (Regressionshistorie, kein Regress-Wächter, nie production-
verifiziert unter den hier betrachteten PRs) und darf deshalb **nicht** ungeprüft zum Fleet-Default
für den Deploy-Schritt werden — nur Steelman hält das Restrisiko für durch bestehende Mitigationen
(frischer GHCR-Login, Secrets vorhanden) für tragbar, Diabolus/Maintainer-2028 stufen es als
blockierend ein. Diese Konvergenz hat direkt in §1/§5.9 zur Entkopplung von Build-Default
(sofort) und Deploy-Default (Kill-Gate-gebunden) geführt.

**6.4 Konfliktmatrix**

| Punkt | Steelman | Advocatus Diabolus | Maintainer 2028 | Bewertung |
|---|---|---|---|---|
| netcup NICHT als Runner-Ziel wählen | Korrekte Governance-Zurückhaltung — respektiert ADR-289 R3 "vertagt", vermeidet Scope-Creep | Governance-Bypass — die Entscheidung trifft implizit dieselbe Wahl (nicht-netcup) OHNE den geforderten Owner-Beschluss einzuholen | (keine explizite Stellungnahme) | **Echter Dissens.** Beide lesen dieselbe Tatsache (netcup wird nicht gewählt) entgegengesetzt: Unterlassung als Zurückhaltung vs. Unterlassung als impliziter Beschluss. Aufgelöst in §12/REC durch explizite Formulierung: dieses Konzept trifft **keine** netcup-Aussage, weder positiv noch negativ — das schließt die Lücke, die Diabolus zu Recht benennt, ohne Steelmans Zurückhaltungs-Argument zu verletzen. |
| Deploy-Schritt auf `ubuntu-latest`+SSH übernehmen | Trägt bereits, Secrets vorhanden, GHCR-Login sogar besser als Status quo | Nie production-verifiziert, zwei Incidents, kein Regress-Wächter — blockierend | Wiederholung ist die begründete Erwartung ohne Regress-Wächter — blockierend | **Keine Divergenz in der Konsequenz** (2 von 3 gegen sofortige Übernahme), nur in der Risikoeinschätzung. Übernommen: Deploy-Übernahme wird Kill-Gate-gebunden, nicht sofort. |
| Bootstrap-Automation (REC-10) fallenlassen | Konsequent — ROI sinkt automatisch bei sinkendem self-hosted-Bedarf | Verhinderungslücke — einziger auditierbarer Registrierungsmechanismus fällt weg | Einmaligkeits-Falle bei Pilot-Runner-Neuaufsetzung | **Keine Divergenz in der Konsequenz** (2 von 3 gegen vollständiges Fallenlassen). Übernommen: Scope auf Ausnahmefall reduziert statt komplett gestrichen (§5.10). |

## 7. Deep-Dive

1. **SSoT/Drift** — `infra/hosts.yaml` bleibt normativ für Runner-Existenz; `runs_on`-Werte in
   Workflow-Dateien sind abgeleitet/pro-Repo-konfiguriert, keine zweite Wahrheit. Drift-Risiko: das
   Runbook (§9-Migrationsreihenfolge) ist bereits von der Praxis überholt (M28-Befund) — bei Konflikt
   gilt der tatsächliche Workflow-Code, nicht das Runbook-Dokument; Runbook wird in REC-4 nachgezogen.
2. **Boundary/Komplexität** — keine neue Grenze/Service; `_deploy-unified.yml` wird als bestehende
   gemeinsame Datei stärker genutzt (Erweiterung, kein neuer Baustein).
3. **Governance** — Owner für ADR-257-Amendment: Achim Dehnert. Ausnahme (host-lokaler Bedarf):
   dokumentationspflichtig im jeweiligen Repo-PR (kein Freifahrtschein, s. Diabolus-Punkt 5) —
   REC-3 schließt diese Lücke mit einem Pflichtfeld.
4. **Security & Prod-Sicherheit** — `ubuntu-latest` für Build/Test reduziert Angriffsfläche
   (kein Docker-Socket-Zugriff auf einem geteilten Prod-nahen Host für Test-Jobs). GHCR-Credential-
   Leak (#1078 Befund 4) bleibt unberührt — als eigenständiges Risiko in §11 geführt, nicht durch
   dieses Konzept adressiert.
5. **Datenschutz** — kein PII-Bezug; CI/Build-Artefakte auf `ubuntu-latest` sind ephemer (kein
   persistenter Host).
6. **Testbarkeit** — n/a für dieses Konzept selbst (keine Test-Coverage-Frage, sondern
   Infrastruktur-Placement).
7. **CI/CD & Betrieb** — Rollback ist reiner Konfigurationsrückbau (5.9). Verhalten bei
   `ubuntu-latest`-Kapazitätsgrenzen (GitHub-Runner-Queues) nicht geprüft — Annahme (H): unkritisch
   bei aktuellem Flottenvolumen, kein Beleg in dieser Session erhoben.
8. **Migration** — Pilot bereits vorhanden (billing-hub#30/recruiting-hub#17, ungenutzt seit 25
   Tagen wegen dieser offenen Konzeptfrage) — kein neuer Pilot nötig, nur Merge-Freigabe.
9. **Messbarkeit** — Frühindikator: Anzahl Repos mit `runs_on: ubuntu-latest` ohne CI-Rot binnen
   30 Tagen. Spätindikator: Zahl echter Prod-Deploys über den SSH-Pfad ohne Incident binnen 60 Tagen
   (Kill-Gate-Signal für Full Concept, §5.10). Vanity-Metrik zu vermeiden: reine PR-Merge-Zahl ohne
   Deploy-Verifikation (genau der Fehler, den billing-hub#30 aktuell vorlebt).

## 8. Alternativen

**A — Status quo (nur ADR-257 Alternative E, self-hosted auf staging), radikal kleiner:**
Idee: nichts ändern, billing-hub#30/recruiting-hub#17 auf `ci-nonprod` umstellen und auf
Runner-Registrierung warten. Nutzt bestehende Infra 1:1. Einfacher: ja, kein Amendment nötig.
Gefährlicher: `staging` ist bereits in einer Ressourcenkrise (Swap 100%) — ein zweiter Runner
verschärft genau das Risiko, das die Kandidaten-Entscheidung vermeidet. Teurer: Bootstrap-Automation
für jeden weiteren Host müsste sofort gebaut werden. **Verwerfen:** löst die 25-Tage-Blockade nicht,
verschärft die staging-Krise.

**B — netcup sofort als neuer CI-Host aktivieren, technischer:** Idee: Runner nach netcup verlagern,
da Ressourcen (12 Kerne, 31GB, gemessene 43k IOPS) objektiv besser als staging. Nutzt ungenutzte
Kapazität. Einfacher: technisch ja. Gefährlicher: übergeht ADR-289 R3 "vertagt — je neuer
Owner-Beschluss" ohne diesen Beschluss einzuholen — der exakte Governance-Bypass, den §6.4 als
Konfliktpunkt identifiziert. **Verwerfen** (für dieses Konzept) — eigener Entscheidungsstrang, der
einen expliziten netcup-Owner-Beschluss braucht, nicht durch dieses Konzept vorwegzunehmen.

**C — Vollständige Bootstrap-Automation zuerst bauen (REC-10 wie ursprünglich gefordert),
organisatorischer:** Idee: reproduzierbares Skript für self-hosted-Runner-Registrierung bauen, bevor
weitere Repos migrieren. Nutzt ADR-257s eigene Folge-Artefakt-Forderung. Einfacher: nein, signifikant
mehr Aufwand (L statt S). Gefährlicher: nein. Teurer: ja — Investition in ein Modell, dessen
Bedarf laut Kernthese gerade sinkt. Besser: nur wenn sich zeigt, dass `ubuntu-latest`+SSH für einen
signifikanten Repo-Anteil NICHT trägt (z.B. wegen Netzwerk-Isolation wie beim GPU-Fall). **Verwerfen**
als Sofortmaßnahme, **behalten** als bedingte Alternative (Trigger: >3 Repos mit dokumentiertem
Ausnahmebedarf).

## 9. Out-of-the-Box

**Shadow-Mode 30 Tage für den SSH-Deploy-Pfad:** Statt Kill-Gate als harte Schwelle: den SSH-
Deploy-Pfad parallel zum echten `deploy_runs_on: prod-server`-Pfad als **read-only Dry-Run** laufen
lassen (SSH-Verbindung + Datei-Sync testen, ohne `deploy.sh` auszuführen) für 30 Tage, bevor er
scharf geschaltet wird. Vorteil: Stabilitätsnachweis ohne Produktionsrisiko. Nachteil: zusätzlicher
CI-Zeitaufwand pro Lauf. Wann sinnvoll: falls der Regress-Wächter-Lint allein nicht überzeugt.
Verworfen für den MVC (Overhead unverhältnismäßig zum aktuellen Blockade-Druck), vorgemerkt für
Full Concept.

**Kill-Switch statt Off-Ramp für `ci-nonprod`:** Statt den self-hosted-Pfad schrittweise
auslaufen zu lassen, einen expliziten Stichtag setzen, ab dem `runs_on: self-hosted` für CI/Test
(nicht Deploy) im Label-Gate hart abgelehnt wird — erzwingt die Migration statt sie optional zu
lassen. Vorteil: verhindert die von Diabolus benannte "formal erfüllen, praktisch umgehen"-Lücke.
Nachteil: kollidiert mit dem dokumentierten Ausnahmefall (GPU/wg0-Netzwerk-Isolation). Wann
sinnvoll: nach Ablauf des in REC-3 geforderten Ausnahme-Nachweisverfahrens. Vorgemerkt für Full
Concept, nicht MVC.

**Property-based statt Pilot-only Verifikation des SSH-Pfads:** Statt auf einen einzelnen echten
Prod-Deploy zu warten (aktuell einziger Verifikationsplan), einen synthetischen Health-Check-Loop
bauen, der den SSH-Pfad gegen einen Wegwerf-Zielhost mehrfach täglich durchspielt. Vorteil: schneller
Stabilitätsnachweis als 30 Tage warten. Nachteil: zusätzliche Infra (Wegwerf-Host), die dieses
Konzept eigentlich vermeiden will. Verworfen — würde den Kernvorteil (kein neuer Host) selbst
unterlaufen.

## 10. Befunde

| ID | Rolle | Kategorie | Befund (1 Satz) | Evidenz | Schweregrad | Confidence | Betroffener Teil |
|---|---|---|---|---|---|---|---|
| SSOT-1 | Diabolus | SSoT-Risiko | Runbook-Frontmatter "Entwurf" widerspricht ADR-257-Textbehauptung "materialisiert" | C3, C2 | mittel | hoch | Runbook |
| GOV-1 | Diabolus/M28 | Governance-Lücke | Kill-Gate 2026-09-24 (ADR-257) hängt an Runner-Registrierung, die dieses Konzept zurückstuft, ohne dass das Kill-Gate selbst angepasst wird | C2 | hoch | hoch | ADR-257 |
| GOV-2 | Diabolus | Governance-Bypass | netcup-Nichtwahl trifft implizit die ADR-289-R3-Entscheidung ohne Owner-Beschluss | C6, §6.4 | mittel | mittel | ADR-289 |
| AD-1 | Diabolus/M28 | neuer Failure-Mode | SSH-Deploy-Pfad (`_deploy-unified.yml`) hat 2 dokumentierte Production-Incidents durch dieselbe Regressionsklasse (Docker-Action beim Job-Setup), Regress-Wächter fehlt noch | C13, C14, C15 | kritisch | hoch | shared-ci |
| AD-2 | Diabolus | bestehende Lücke nicht geschlossen | GHCR-Credential-Leak (#1078 Befund 4, fehlendes `docker logout`) bleibt unabhängig vom Runner-Ort ungelöst | C9 | mittel | hoch | deploy.sh |
| OPS-1 | M28 | Wartungslast | Runbook §9-Migrationsreihenfolge ist real nur zu 1/4 Schritten umgesetzt, Praxis (ubuntu-latest) weicht bereits vom Dokument ab | C3, C10, C11 | mittel | hoch | Runbook |
| OPS-2 | M28 | Frühindikator fehlt | Hygiene-Check aus ADR-257 REC-6/8, der das Kill-Gate speisen soll, ist in keiner geöffneten Quelle als existierend belegt | C2 | mittel | mittel (H) | ADR-257 |
| ARCH-1 | Diabolus/M28 | Formal erfüllt, praktisch umgangen | Deploy-/Restart-Schritt (der ressourcenkritischere Teil) bleibt bei sofortiger Übernahme unverändert auf `prod-server`, während CI/Test-Migration als "erledigt" gelesen werden könnte | C11 | hoch | hoch | Kandidaten-Entscheidung |
| MIG-1 | Steelman | positiv | billing-hub#30 belegt lebend, dass der Build-Split (ubuntu-latest CI, prod-server Deploy) bereits ohne neue Secrets funktioniert | C10, C12 | positiv | hoch | billing-hub |
| ARCH-2 | Steelman | positiv | staging-Ressourcenkrise (Swap 100%) macht die Rückstufung von self-hosted als Default sachlich dringlich, unabhängig von der SSH-Pfad-Frage | C5 | positiv | hoch | staging |

## 11. Top-5-Risiken

1. **SSH-Deploy-Pfad-Regression (AD-1).** Warum wichtig: zentrale, von 48 Repos konsumierte Datei
   mit zwei Production-Incidents in vier Wochen. Schadensszenario: Fleet-weite Übernahme vor
   Regress-Wächter → dritter Incident, diesmal an mehr Repos gleichzeitig. Wahrscheinlichkeit: mittel
   (Muster wiederholte sich bereits 2x). Impact: hoch (Prod-Deploy-Ausfall). Kleinster wirksamer Fix:
   Regress-Wächter-Lint bauen, BEVOR Deploy-Schritt migriert (REC-2). Stärkster Gegenbeleg: Fix ist
   seit 2026-08-10 wieder aktiv, Ursache verstanden. Restunsicherheit: kein Nachweis, dass der Fix
   diesmal dauerhaft hält.
2. **Kill-Gate-Governance-Lücke (GOV-1).** Warum wichtig: ADR-257 könnte formal auf `rejected`
   kippen, obwohl dieses Konzept bewusst denselben Zustand herbeiführt. Schadensszenario: Am
   2026-09-24 wird ADR-257 automatisch als gescheitert gelesen, obwohl die Absicht dahinter (CI weg
   von prod-server) erfüllt ist. Wahrscheinlichkeit: hoch ohne Fix. Impact: mittel (Verwirrung,
   Fehlinterpretation, kein technischer Schaden). Kleinster wirksamer Fix: Amendment-Absatz in
   ADR-257, der das Kill-Gate umformuliert (REC-1). Gegenbeleg: keiner. Restunsicherheit: keine.
3. **Runbook-Praxis-Drift (OPS-1).** Warum wichtig: künftige Sessions/Maintainer lesen das Runbook
   als Wahrheit. Schadensszenario: jemand registriert manuell einen weiteren self-hosted-Runner nach
   der alten §9-Reihenfolge, obwohl die Flotte längst zu ubuntu-latest gewechselt ist. Wahrschein-
   lichkeit: mittel. Impact: niedrig-mittel (Doppelarbeit, kein Datenschaden). Kleinster wirksamer
   Fix: Runbook-Status + §9 korrigieren (REC-4). Gegenbeleg: keiner. Restunsicherheit: keine.
4. **Exception-Klausel ohne Gate (Diabolus-Punkt 5).** Warum wichtig: könnte den beabsichtigten
   Default unterlaufen. Schadensszenario: jedes Repo attestiert sich einen "Netzwerk-Bedarf" und
   bleibt dauerhaft auf `prod-server`, der Umstieg passiert nie. Wahrscheinlichkeit: niedrig-mittel
   (nur ein Entscheider, Achim selbst). Impact: niedrig (kein technischer Schaden, nur verfehltes
   Ziel). Kleinster wirksamer Fix: Pflichtfeld "Ausnahme-Begründung" im PR-Text (REC-3). Gegenbeleg:
   Einzelentscheider-Repo — Selbst-Umgehung ist unwahrscheinlicher als bei einem Team. Restunsicher-
   heit: gering.
5. **GHCR-Credential-Leak bleibt offen (AD-2).** Warum wichtig: unabhängig vom Runner-Ort, betrifft
   jeden künftigen Deploy auf `prod-server`. Schadensszenario: nächster Docker-Action-Pull auf dem
   Host scheitert erneut an einer toten Credential, unabhängig davon, ob CI vorher auf ubuntu-latest
   lief. Wahrscheinlichkeit: hoch (bereits 2x aufgetreten, Ursache nicht gefixt). Impact: mittel
   (Deploy-Fail, kein Datenverlust). Kleinster wirksamer Fix: außerhalb dieses Konzepts — Verweis auf
   #1078 Befund 4 als eigenständiges Ticket (REC-5). Gegenbeleg: SSH-Pfad umgeht das Problem bereits
   teilweise (frischer Workflow-Token). Restunsicherheit: bleibt für den self-hosted-Direktpfad.

## 12. Empfehlungen

**REC-1** (Bezug: GOV-1). Ziel: Kill-Gate-Formulierung an die neue Default-Logik anpassen. Konkrete
Änderung: `docs/adr/ADR-257-ci-host-isolation-non-prod-runner.md` §Kill-Gate — Bedingung "kein
dedizierter Non-Prod-Runner registriert+in Betrieb" umformulieren zu "weder ein dedizierter
Non-Prod-Runner für Ausnahme-Repos in Betrieb NOCH ein aktiver Regress-Wächter für den
ubuntu-latest+SSH-Pfad" (ODER-verknüpft statt starr auf Runner-Existenz). Aufwand: S. Risiko der
Änderung: niedrig (reine Text-Klarstellung). Verifikation: ADR-Review-Lauf (`iil-adrfw validate`).
Akzeptanzkriterium: Kill-Gate-Text erwähnt beide Pfade explizit. Owner-Vorschlag: Achim Dehnert.

**REC-2** (Bezug: AD-1). Ziel: Regress-Wächter aus #1845 tatsächlich bauen, bevor Deploy-Schritt
migriert. Konkrete Änderung: neuer Workflow `shared-ci/.github/workflows/lint-no-docker-actions.yml`
(oder Erweiterung eines bestehenden Lints), der `_deploy-unified.yml` + alle in
`shared-ci/actions/` referenzierten Composite-/Docker-Actions nach `runs.using: docker` durchsucht
und rot wird. Aufwand: M. Risiko der Änderung: niedrig (additiver Gate). Verifikation: Lint bewusst
gegen einen simulierten Docker-Action-Commit testen (muss rot werden). Akzeptanzkriterium: Lint läuft
in shared-ci CI, ist required. Owner-Vorschlag: Achim Dehnert.

**REC-3** (Bezug: Diabolus-Punkt 5, Top-Risiko 4). Ziel: Exception-Klausel für host-lokale Ausführung
gate-fähig machen. Konkrete Änderung: PR-Template-Ergänzung (oder Kommentar-Konvention) — jeder PR,
der `runs_on: self-hosted`/`ci-nonprod` NEU setzt, muss einen Satz "Ausnahme-Begründung:
<Netzwerk-Ressource/Grund>" im PR-Body tragen. Aufwand: S. Risiko: niedrig. Verifikation: Stichprobe
nächster 3 PRs mit self-hosted-Bezug. Akzeptanzkriterium: Begründung vorhanden. Owner-Vorschlag:
Achim Dehnert.

**REC-4** (Bezug: OPS-1, SSOT-1). Ziel: Runbook-Status und -Reihenfolge an die reale Praxis
anpassen. Konkrete Änderung: `infra/host-maintenance/runner-nonprod-runbook.md` Frontmatter-Status
von "Entwurf" auf einen ehrlichen Zwischenstatus setzen (z.B. "Alternative E pilotiert, Default-Pfad
seit KONZ-platform-042 = ubuntu-latest") + §9 um den tatsächlichen Ablauf (ubuntu-latest zuerst,
self-hosted nur Ausnahme) ergänzen. Aufwand: S. Risiko: niedrig. Verifikation: Diff-Review.
Akzeptanzkriterium: kein Widerspruch mehr zwischen ADR-257-Text und Runbook-Frontmatter.
Owner-Vorschlag: Achim Dehnert.

**REC-5** (Bezug: AD-2, Top-Risiko 5). Ziel: GHCR-Credential-Leak als eigenständiges, von diesem
Konzept unabhängiges Ticket sichtbar halten (nicht durch Runner-Placement-Fix fälschlich als gelöst
missverstehen lassen). Konkrete Änderung: Kommentar auf #1078 mit Verweis auf dieses Konzept + Status
"Befund 4 bleibt offen, unabhängig von KONZ-platform-042". Aufwand: S. Risiko: keins. Verifikation:
Kommentar sichtbar auf #1078. Akzeptanzkriterium: Kommentar gepostet. Owner-Vorschlag: Achim Dehnert.

**REC-6** (Bezug: MIG-1, Kernempfehlung). Ziel: 25-Tage-Blockade auflösen. Konkrete Änderung:
billing-hub#30 und recruiting-hub#17 mergen (Code bereits korrekt: `runs_on: ubuntu-latest`,
`deploy_runs_on: prod-server` gepinnt). Aufwand: S. Risiko: niedrig (Diff bereits geprüft). Verifi-
kation: nächster echter Deploy beider Repos beobachten (schließt den offenen Testplan-Punkt).
Akzeptanzkriterium: Build-Job grün, Deploy-Job grün, kein RAM-Oversubscription-Symptom. Owner-
Vorschlag: Achim Dehnert.

## 13. Entscheidung + Kill-Gate + 30/60/90

**Empfehlung: als MVP annehmen.** Wichtigste Begründung: löst die 25-Tage-Blockade sofort (REC-6),
ohne den unbewiesenen SSH-Deploy-Pfad zu übernehmen — genau die Trennung, auf die alle drei
adversarialen Agenten (mit unterschiedlicher Gewichtung) konvergieren. Stärke: nutzt bereits
vorhandene, unbenutzte Kapazität (SSH-Pfad seit ~2026-07-10) statt neuer Investition. Schwäche: löst
die strukturelle Deploy-Kontention auf `prod-server` nicht, nur die Build-Kontention. Sofortmaßnahme:
REC-6 (Merge) + REC-1 (Kill-Gate-Text) sofort, REC-2 (Regress-Wächter) vor jeder Deploy-Pfad-
Erweiterung. Unsicherheit: SSH-Pfad-Stabilität nach dem 2026-08-10-Fix unbewiesen. Finaler
Threshold-Status: Amendment zu ADR-257 (kein neuer Org-ADR).

**Kill-Gate (Pflicht, UND-verknüpft, Stichtag 2026-09-10 = 30 Tage nach Merge):**
- **K1:** billing-hub#30 UND recruiting-hub#17 gemerged, mindestens je ein echter Prod-Deploy
  beobachtet, beide grün.
- **K2:** Regress-Wächter-Lint (REC-2) existiert und läuft required in shared-ci CI.
- **K3:** ADR-257-Amendment (REC-1) gemerged.
- **K4:** kein dritter Docker-Action-Regressions-Incident in `_deploy-unified.yml` bis zum Stichtag.

Bei Nichterfüllung (auch nur eines Kriteriums): Rückfall auf ADR-257 Alternative E (self-hosted
`staging-ci`) als alleinigen Pfad; dieses Konzept wird `superseded`, Runbook-§9-Reihenfolge bleibt
maßgeblich. **Exception-Budget:** max. eine datiert begründete 14-Tage-Verlängerung, falls K1/K2 an
externer Abhängigkeit (z.B. GitHub-Runner-Verfügbarkeit) hängt — kein Budget für K3/K4.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 — billing-hub#30 + recruiting-hub#17 gemerged + grüner Prod-Deploy | offen | — |
| K2 — Regress-Wächter-Lint required in shared-ci CI | offen | — |
| K3 — ADR-257-Amendment gemerged | offen | — |
| K4 — kein dritter Docker-Action-Incident bis Stichtag | offen (laufend beobachtet) | — |

**30/60/90:**
- **30 (bis 2026-09-10):** Owner Achim Dehnert. Minimalartefakte: REC-1 bis REC-6 umgesetzt.
  Erste Validierung: K1-K4 auswerten.
- **60 (bis 2026-10-10):** Falls Kill-Gate erfüllt: Full Concept (§5.10) pilotieren an 2-3 weiteren
  Repos aus der "≥9 Hubs"-Restflotte. Erste Gegenbelege/False-Positives sammeln (z.B. Repos mit
  Docker-Socket-Bedarf, die auf ubuntu-latest scheitern).
- **90 (bis 2026-11-08):** Kill-Gate für Full Concept auswerten → Fleet-weit ausrollen / auf
  MVC-Stand einfrieren / stoppen und auf Alternative A zurückfallen.
