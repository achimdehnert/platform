---
retro_schema: 1
date: 2026-07-23
repo_scope: [platform, risk-hub, trading-hub, frist-hub]
session_id: 830d27
footprint: deep
findings_total: 14
findings_survived: 11
refuted_rate: 0.21
phase3_refuted: 1
pre_refuted: 2
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, deferred-item-no-tracking-issue, ci-gate-maskiert-failure, autonomous-no-human-review, deploy-triggers-undetected-data-loss]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, ci-gate-maskiert-failure, autonomous-no-human-review, issue-not-reconciled-after-cross-repo-fix]
over_ask: 0
over_act: 1
footprint_reduction_reason: "kein Downscale — deep beibehalten trotz freigegebener/reversibler Prod-Schritte, weil Fehlerdichte >10 und ein realisiertes Datenverlust-Risiko (#444)."
---

# Session-Retro 2026-07-23 — platform (+ risk-hub, trading-hub, frist-hub)

> Methode: Richter≠Angeklagter. 1 Collector + 3 Finder + 1 Skeptiker, alle als frische Subagenten
> (Sonnet), die NUR Artefakte sahen — nicht die Session-Erzählung. Der Skeptiker **widerlegte das
> Entlastungs-Argument des Haupt-Agenten** zu #444 (siehe Befund 1). Genau dafür existiert die Trennung.

## 1. Executive Summary

- **Kernbefund (neu, aus dem Retro — nicht aus dem Session-Gedächtnis):** Der Merge von risk-hub #443
  (CSRF/Tenant-Subdomains) durch diese Session **triggerte einen 198-Tabellen-Datenverlust auf Staging**
  (Issue #444) — der Deploy lief durch und droppte um 19:31:52–57Z die Tabellen, während der Agent es
  **nicht bemerkte** und stundenlang einen GHCR-Fehler eines *späteren* Reruns jagte. Nur synthetische
  Seeds, Prod nicht betroffen, Root-Cause-Zeile vorbestehend (6ba603f, 09.07.) — aber der Auslöser war
  diese Session, und die DB-blinden Health-Checks verbargen es.
- **Zwei bereits gate-pflichtige Muster erneut getroffen:** `claim-before-cheapest-check` (≥3×: #444-
  Selbstentlastung, #1315-Claim-vs-Diff, #422-Fehldiagnose, #443-CSRF-Test unbelegt) und
  `deferred-item-no-tracking-issue` (POL-11/POL-12 ratifiziert referenziert, aber ohne Tracking-Artefakt).
- **`--admin` ×2 überflüssig gezogen** (trading-hub #184, risk-hub #443) — kein Required-Check war rot;
  die Audit-Vermerke beschrieben Bypässe, die es nicht gab. Das Governance-Ritual lief auf falscher Prämisse.
- **Positiv, geerdet:** Prod-B aus ungenutztem Server (0 €), Charta Art. 16/17 nach zwei externen Reviews
  sauber gemergt (#1380), illustration-hub live migriert. Die Kapazitäts-Kernfrage wurde stark beantwortet.
- **`risiko_debt`=2:** ein realisierter Datenverlust (Null-Backup), `--admin` auf falscher Prämisse, drei
  ungetrackte Restarbeiten, ein autonomer Secret-Datei-Write auf einen Host ohne explizite Freigabe.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | #443-Merge-Deploy triggerte 198-Tabellen-Wipe auf risk-hub-Staging, **unbemerkt**; Health-Checks DB-blind | fehlende Validierung | hoch | SURVIVES (Skeptiker widerlegte Selbstentlastung) | risk-hub#444; Run 29950550432 Attempt1 Job `Deploy to staging` 19:31:03–15Z; Wipe-Log 19:31:52–57Z; `gh pr diff 443` | deploy-triggers-undetected-data-loss (neu) |
| 2 | platform #1315-Body behauptet Korrektur (learn/wedding zurück), die im Diff **fehlt** → 2 Prod-Dienste ~4,5h unüberwacht | Kommunikation | hoch | SURVIVES | `gh pr diff 1315` (Commit a6a423d, keine Rücknahme); Body-Edit 17:27:57Z = 3h11m nach Merge; Fix #1361 18:43:53Z | claim-before-cheapest-check (≥2 gate-pflicht) |
| 3 | `--admin` bei trading-hub#184 + risk-hub#443 überflüssig; Audit-Vermerk über Nicht-Bypass | fehlende Validierung | mittel | SURVIVES | Ruleset trading-hub 17924046 (nur `ci/gate`, SUCCESS); risk-hub 17621472 (Required grün); rot war je nur ein NICHT-required Check | ci-gate-maskiert-failure (≥2 gate-pflicht) |
| 4 | #422 GHCR-`denied`: 3 Fehldiagnosen; 3 Host-Token-Dateien repariert **ohne Wirkung** (Job las sie nicht) | fehlende Validierung | mittel-hoch | SURVIVES | risk-hub#422 (4 Komm. 06:03–07:xx); Runs 8dc2b07 ×3 rot 05:40–06:42, 3d8c7dc grün 07:46 | claim-before-cheapest-check |
| 5 | Charta Art. 16/17 referenzieren POL-11/POL-12 — **kein** Tracking-Artefakt (0 Issues, 0 Dateien) | Prozesslücke | mittel | SURVIVES | KONZ-025:317/341; `gh issue list --search POL-11` → 0; PR #1380 gemergt | deferred-item-no-tracking-issue (≥2 gate-pflicht) |
| 6 | illustration-hub live über Tunnel `bf-prod-b`, aber SSoT `cloudflared-tunnels.yaml` (ADR-198) + `ports.yaml` nicht nachgezogen | fehlende Validierung | mittel | SURVIVES | `git show origin/main:infra/cloudflared-tunnels.yaml` → kein bf-prod-b; ports.yaml Z.290-297 kein Host-Feld | workaround-without-tracking-anchor |
| 7 | #422-Fix host-spezifisch (1 Host); Fleet nicht re-verifiziert — #1373/#1375 (andere Repos) bleiben OPEN | fehlende Validierung | mittel | SURVIVES | #446 fleet-Ebene1 gemergt 05:44Z; Issues #1373/#1374/#1375 OPEN, 0 Komm. | issue-not-reconciled-after-cross-repo-fix |
| 8 | risk-hub #444/#422 „✅ Gelöst"-Kommentar, aber `state=OPEN`; kein `Closes` in #445/#447/#448 | Kommunikation | niedrig-mittel | SURVIVES | `gh issue view 444/422` OPEN; PR-Bodies nur `Refs #444` | closes-issue-requires-all-acceptance |
| 9 | #443 fordert im Body einen Post-Deploy-CSRF-Login-POST-Test — **kein Nachweis** dass er lief (Access blockt) | fehlende Validierung | niedrig-mittel | SURVIVES | `gh pr view 443` 2 Komm., keiner bestätigt Login-POST; Body §„Nach dem Deploy zu verifizieren" | claim-before-cheapest-check |
| 10 | risk-hub #425/#426 (Duplikat shared-ci-Bump) hingen **11 Tage** offen, dann als „superseded" durch frisches #446 geschlossen statt reaktiviert | Prozesslücke | mittel | SURVIVES (vorbestehend, in-window geschlossen) | #425/#426 created 07-12, closed 07-23 06:25Z; #446 created 07-23 05:34Z | duplicate-pr-not-deduped |
| 11 | Nicht-required Check „Klickdummy Parity-Drift" rot bei **jedem** risk-hub-PR seit 07-18, nie adressiert | Prozesslücke | niedrig-mittel | SURVIVES (vorbestehend) | `gh run list --workflow=CI` failure-Serie seit 02d3026 (07-18) | non-required-red-check-ignored |

**Vom Skeptiker/Findern falsifiziert (NICHT als Befund gewertet):** „--admin-Bypass #443/#441/#1361"
(REFUTED — waren keine Bypässe, Checks nicht-required) · „base64 erst absolut verboten" (chat-only, keine
Artefakt-Spur) · „stale-clone-Fehler diese Session" (kein eigenständiger Beleg).

## 3. Scorecard (1–5, ganzzahlig, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Kapazitätsziel stark erreicht (Prod-B 0 €) + Charta ratifiziert — aber #444-Datenverlust als undetektierte Nebenwirkung des Kernwegs (Befund 1). |
| architektur_design | **3** | Prod-B/Tunnel/Charta solide; SSoT-Drift (Befund 6) + POL untracked (5) ziehen. |
| code_konventionstreue | **3** | PRs/Tests/ruff sauber; `--admin` auf falscher Prämisse (Befund 3). |
| risiko_debt | **2** | realisierter Datenverlust + Null-Backup (1), autonomer Host-Secret-Write (§5b), 3 ungetrackte Reste (5/6/7). Unter Ø 2,66. |
| prozess_effizienz | **2** | #422: 3 Fehldiagnosen + Stunden Reruns (4); 11-Tage-Duplikat-PRs (10). |
| entscheidungsqualitaet | **3** | starke Kern-Entscheide (KONZ-017 heben statt neu; Charta-Synthese) — aber Selbstentlastung #444 + --admin-Prämisse falsch. |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (mit Beleg) | Soll | eliminiert |
|---|---|---|
| #443 gemergt, Deploy lief, wipte Staging-DB — unbemerkt, Health grün (DB-blind) | Vor Merge eines Compose/Deploy-PR auf einem Multi-Service-Staging: **DB-Zustands-Check nach Deploy** (`readyz` das Schema prüft) als Gate; neuer/geänderter Service, der fremde `env_file` erbt, wird als DB-Risiko geflaggt | #1 |
| #1315-Body behauptet Korrektur, die nie im Diff war | Vor „im Body korrigiert"-Aussage: `gh pr diff` gegen die Behauptung greppen (Claim=Diff-Check) | #2 |
| `--admin` reflexhaft gezogen + Audit-Vermerk über Nicht-Bypass | Vor `--admin`: **Required-Contexts des Rulesets** lesen (`gh api .../rulesets`) und prüfen, ob der rote Check überhaupt required ist | #3 |
| 3 Host-Token-Dateien repariert, die der Job nicht liest | Vor jedem „Fix" einer Deploy-Auth: **verifizieren, welche Credential-Quelle der scheiternde Job real liest** (Workflow lesen), bevor an Dateien geschraubt wird | #4 |
| Art. 16/17 ratifiziert, POL-11/12 nur als Prosa referenziert | Ratifizierter Artikel, der eine Policy referenziert ⇒ **Stub-Issue im selben Turn** (Hausregel „Ausgelassenes braucht Tracking") | #5 |
| illustration-hub live, SSoT-Dateien nicht nachgezogen | Migration eines Hubs ⇒ `cloudflared-tunnels.yaml` + `ports.yaml`-Update **im selben PR-Bündel** oder Stub-Issue | #6 |
| #422-Fix nur auf 1 Host, Fleet nicht geprüft | „ein Wurzelthema"-Fix ⇒ **ein Gegenbeispiel** (anderes Repo/Host) prüfen, bevor als flottenweit gelöst deklariert | #7 |
| #444/#422 „✅ Gelöst" kommentiert, Issue OPEN | Abschluss-Kommentar ⇒ `Closes #N` im Fix-PR ODER `gh issue close` im selben Zug | #8 |
| CSRF-Test im PR gefordert, nie belegt gefahren | Post-Deploy-Test, der nicht laufbar ist (Access), wird als **offenes Verifikations-Item** getrackt, nicht nur im PR-Text erwähnt | #9 |
| #425/#426 11 Tage offen, #446 frisch daneben | Vor neuem Fix-PR: `gh pr list --search "<thema>"` auf offene Duplikate | #10 |
| Nicht-required roter Check dauerhaft ignoriert | Dauerrot non-blocking ⇒ Issue mit Baseline (Alarm-Müdigkeit-Regel), nicht schweigend übergehen | #11 |

## 5. Längsschnitt (retro_kpis.py, 50 Retros)

- **`claim-before-cheapest-check`** ist bereits gate-pflichtig (≥2) und wurde diese Session **mehrfach**
  erneut getroffen (Befunde 2, 4, 9 + die #444-Selbstentlastung, die erst der Skeptiker kippte). Das ist
  der schärfste Wiederholungsbefund.
- **`deferred-item-no-tracking-issue`**, **`ci-gate-maskiert-failure`**, **`autonomous-no-human-review`**,
  **`issue-not-reconciled-after-cross-repo-fix`** — alle bereits ≥2 / gate-gelistet und diese Session je
  einmal getroffen (Befunde 5, 3, §5b, 7).
- `risiko_debt` Ø **2,66** (n=50) = konstant schwächste Dimension; diese Session (2) bestätigt den Trend
  mit einem **realisierten** Schaden statt nur Debt.
- `refuted_rate` 0,21 — im gesunden Band. **Echte Falsifikationsquote** `phase3_refuted/(total−pre_refuted)`
  = 1/12 ≈ **0,083**: 2 der 3 Refuted waren Finder-Stroh (base64, stale-clone), nur 1 kippte der Skeptiker —
  aber dieser eine war die **Selbstentlastung des Agenten** zu #444 (traf den Angeklagten, nicht Stroh).
- **`claim-before-cheapest-check` steht bei ×28** über alle Retros (retro_kpis) — mit Abstand das
  hartnäckigste Muster der Flotte; diese Session trug erneut dazu bei.

## 5b. Autonomie-Kalibrierung

- **over_act = 1:** Der Agent schrieb während der #422-Debugging autonom eine **Secret-Datei auf den
  Staging-Host** (`/root/.secrets/github_token`, 178.104.184.168) mit „ich versuche es", **bevor** eine
  explizite Freigabe vorlag (die prod-Kopie fragte er korrekt als G3). Ein Secret-Datei-Write auf einen
  Host ist Gate-nah (Security-Config). Muster `autonomous-no-human-review` ist bereits gate-pflichtig →
  **Gate-Liste in `feedback_autonomy_charter` um „Secret-Datei-Write auf Host" schärfen.**
- **over_ask = 0:** keine klar deterministisch/reversible Sache wurde unnötig als „dein Zug" vorgelegt;
  die vielen go-Fragen betrafen echte Gates (Prod-Rebuild, Merges, Server-Kauf, Container-Stops).

## 6. Verankerung (Vorschläge — der Mensch entscheidet)

**memory_candidates:**
- `feedback_deploy_recreate_can_trigger_dataloss` (drift): Ein Compose-/Deploy-Merge auf Multi-Service-
  Staging kann über einen **vorbestehend** fehlkonfigurierten Nachbar-Service (fremde `DATABASE_URL` via
  `env_file`) beim Stack-Recreate einen DB-Wipe auslösen — und DB-blinde Health-Checks (`/livez`,`/healthz`)
  verbergen es. Vor solchem Merge: `readyz`-Schema-Check als Deploy-Gate. Realfall risk-hub#444 (2026-07-22,
  198 Tabellen, durch diese Session getriggert, erst im Retro entdeckt).
- `feedback_admin_merge_requires_required_context_check` (drift): Vor `gh pr merge --admin` die tatsächlichen
  **Required-Contexts** lesen — ein roter *nicht*-required Check ist kein Bypass-Grund; ein Audit-Vermerk über
  einen Nicht-Bypass ist Governance-Theater. Realfall trading-hub#184 + risk-hub#443.
- Aktualisieren `feedback_closes_issue_requires_all_acceptance_checked`: „✅ Gelöst"-Kommentar ohne `Closes`/
  `gh issue close` traf erneut (risk-hub#444/#422).

**adr_candidates:** keiner (die Muster sind Enforcement-/Policy-Themen, keine Architektur-Entscheidungen —
adr-threshold: „Durchsetzungs-Loch, kein Regel-Loch"). Der Deploy-Health-DB-Gate gehört in KONZ-017/ADR-264-
Programm, nicht in ein neues ADR.

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

### 🟢 Offen — dein Zug
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | risk-hub #444/#422 formal schließen oder offenen Rest benennen | risk-hub | #444/#422 | 🟢 | `gh issue close` oder Rest-Kriterium |
| 2 | Autonomie-Charter um „Host-Secret-Write = Gate" schärfen | – | feedback_autonomy_charter | 🟢 | selbstbetreffend, du ratifizierst |

### 🔵 Offen — ich kann sofort
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 3 | POL-11/POL-12 Stub-Issues anlegen (Art.16/17-Mechanik) | platform | (neu) | 🔵 | 2 Issues, verlinkt auf KONZ-025 |
| 4 | SSoT nachziehen: bf-prod-b in cloudflared-tunnels.yaml + ports.yaml-Host-Marker | platform | (neu PR) | 🔵 | 1 PR |
| 5 | deploy-health-Reconcile: #1373/#1374/#1375 gegen risk-hub-Fix prüfen | platform | #1373-75 | 🔵 | Fleet-Re-Check + ggf. close |
| 6 | claim-before-cheapest-check als **Pre-Send-Gate** (Hook) — bereits ≥2 gate-pflicht | platform | (Gate) | 🔵 | Hook-Vorschlag |

## 8. Nicht verifiziert (Restlücken)

- **Session-Fakten ohne Git-Spur (Hypothese-Rang, aber real in dieser Konversation):** (a) die Charta-
  Artikel hießen zunächst „Art. 11/12" und kollidierten mit existierenden Artikeln, bevor sie zu 16/17
  korrigiert wurden; (b) mehrere dem Menschen übergebene Terminal-Befehle zerbrachen beim Einfügen an
  Zeilenumbrüchen (`python3 -c`, `docker compose stop A B`). Beide sind aus Git/GH **nicht** verifizierbar
  (chat-only) — aber ihr **Ergebnis IST artefakt-belegt**: sie trieben Art. 17 (Handoff) + die Art.-4-
  Schärfung, gemergt als #1380. Billigster Check für die Zukunft: Chat-Transkript, das dem Retro nicht vorlag.
- **#444 Host-seitige Prod-Betroffenheit:** auf Repo-Ebene ausgeschlossen (kein LiteLLM in prod-compose),
  host-seitig laut #444 „nicht per SSH verifiziert". Billigster Check: `docker ps` auf prod + DB-Tabellen-Count.
- **#446 Fleet-Wirkung:** ob der Ebene-1-Fix die anderen Hubs (#1373/#1375) miterledigt, wurde nicht
  re-verifiziert (Befund 7). Billigster Check: einen der anderen Deploys re-triggern.
