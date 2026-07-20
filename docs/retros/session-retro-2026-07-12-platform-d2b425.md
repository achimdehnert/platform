---
retro_schema: 1
date: 2026-07-12
repo_scope: [platform, shared-ci, cad-hub, 137-hub, wedding-hub, weltenhub, risk-hub, coach-hub, dms-hub, and-18-bump-consumers]
session_id: d2b425
footprint: deep
findings_total: 21
findings_survived: 14   # 14 Rohfunde (SURVIVES), nach Dimensions-Dedup 9 Tabellenzeilen in §2
refuted_rate: 0.33
phase3_refuted: 3
pre_refuted: 4
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [claim-before-cheapest-check, ci-replace-requires-job-catalog-diff, stale-local-clone-as-ground-truth, scope-checkpoint-not-durably-recorded, planned-phase-no-issue]
recurring_findings: [claim-before-cheapest-check, ci-replace-requires-job-catalog-diff, stale-local-clone-as-ground-truth, scope-checkpoint-not-durably-recorded, planned-phase-no-issue, ruleset-bypass-without-durable-audit-artifact, mass-ci-wave-self-host-contention, bump-wave-no-preflight-on-known-red-repos]
over_ask: 0
over_act: 0
footprint_reduction_reason: "n/a — deep beibehalten (≥3 Repos, mehrere Prod-Deploys, Governance-Config-Änderung Ruleset-Bypass; keine Reduktion)"
---

# Session-Retro 2026-07-12 — platform (Session d2b425)

Reviewte Session: eine lange Fable-5-Session mit drei T3-Konzepten (KONZ-017 Fleet-Konvergenz,
KONZ-018 PyPI-Fleet, KONZ-019 Agenten-Autonomie), deren W0-Ausführung, zwei gelösten
Prod-Incidents (137-hub OOM+Healthcheck, cad-hub xdist), einer shared-ci-v1.0.11-Bump-Welle über
~22 Consumer-Repos, einer Standing-Authorization-Policy-Ratifikation und mehreren Prod-Deploys.
Methode: Richter≠Angeklagter — Collector (haiku) + 3 blinde Finder (sonnet) + 3 Skeptiker je
Dimension (sonnet, `git fetch origin`-Pflicht). Nur SURVIVES im Report.

## 1. Executive Summary

- **Die Session löste ihr eigenes Kernproblem im Kleinen vor, während sie es im Großen adressierte:**
  Signal G (Merge-Freigabe-Roundtrips) war durchgängig hoch — genau die Friktion, die KONZ-019/
  SA-Policy beheben sollen; die Session demonstrierte das Autonomie-Problem live.
- **Stärkster Einzel-Survivor (hoch): cad-hub#39 war ein unvollständiger Fix** — nur `ci.yml`
  gepatcht, der zweite `_ci-python`-Aufrufer in `deploy.yml` blieb auf `auto` → Prod-Deploy-Gate
  ~5h24min rot, Nachzieh-PR #42 nötig. Das Job-Katalog-Diff-Memory existierte genau dafür.
- **Wichtige Falsifikation: der `pytest_workers=4`-Fix ist NICHT widerlegt.** weltenhub#41 crashte
  trotz `WORKERS=4` — aber an transienter Host-Kontention (5+ Repos zeitgleich CI im 14:00-Fenster
  der Bump-Welle), nicht an Fix-Versagen. Die Bump-Welle erzeugte ihre eigene Last.
- **Governance-Beobachtung (mittel): 2 Ruleset-Bypass-Episoden ohne durables In-Repo-Audit** —
  Episode 1 (4 platform-PRs) lebt nur in der GitHub-Ruleset-History; das IaC-Template
  (`bypass_actors: []`) driftete 2× unbemerkt.
- **Sauber getrackt trotz vieler offener Enden:** alle bewusst aufgeschobenen Punkte (wedding-Tests
  #33, aifw-tenacity #1108, Owner-Block #1094) haben durable Issues — `risiko_debt` liegt mit 3
  über dem 23-Retro-Schnitt von 2.70.

## 2. Befund-Tabelle (nur SURVIVES; Duplikate über Dimensionen konsolidiert)

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | cad-hub#39 fixte nur `ci.yml`, nicht die separate `deploy.yml`-`_ci-python`-Call-Site → Prod-Deploy-Gate ~5h24min rot, #42 als Nachzug nötig | fehlende Validierung | **hoch** | SURVIVES | cad-hub#39 (files=ci.yml only), Run 29183210419 failure `WORKERS=auto`, cad-hub#40 (06:53–12:18), #42 (12:12:53Z) | `claim-before-cheapest-check` (≥2) + `ci-replace-requires-job-catalog-diff` (→×2) |
| 2 | wedding-Blocker: Ausgangsziel „Blocker klären" wuchs zu CI-System-Migration; Tests via `skip_tests:true` umgangen statt wiederhergestellt, PR #32 noch OPEN | Scope-Wachstum | **hoch** | SURVIVES | wedding-hub#32 OPEN, `skip_tests:true`; #33 (Tests-Restore vertagt) | `scope-checkpoint-not-durably-recorded` (≥2) |
| 3 | 2 Ruleset-Bypass-Episoden (4 API-Edits) ohne durables In-Repo-Audit-Artefakt für Episode 1 (#1088/90/91/93); IaC-Template `bypass_actors:[]` driftete 2× unbemerkt | Prozesslücke/Governance | mittel | SURVIVES | rulesets/17621471/history (4 Versionen 09:17–12:20); nur #1097 nennt Bypass im Text | `ruleset-bypass-without-durable-audit-artifact` (×1) |
| 4 | Bump-Welle-Timing überlastete den geteilten self-hosted-Runner-Host — 5+ Repos zeitgleich CI/Deploy (14:00-Fenster) → weltenhub#41 + risk-hub xdist-Crashes trotz `WORKERS=4` (Host-Kontention, NICHT Fix-Versagen); kein Tracking-Issue | Prozesslücke | mittel | SURVIVES | Run 29195454601 (`WORKERS=4` + „node down"), Timing vs. risk-hub/tax/trading PRs 13:54–14:10 | `mass-ci-wave-self-host-contention` (×1) |
| 5 | Kein Preflight-Filter gegen bekannt-rote/blockierte Zielrepos in der Bump-Welle: coach-hub#40 (bekannt kaputt, PROJECT_PAT), dms-hub (bekannt Runner-Issue #1087), risk-hub-Dupe #425/#426 (7min Abstand, byte-identisch) | Prozesslücke | mittel | SURVIVES | coach-hub#40 CI-fail, dms-hub Run queued, risk-hub#425 vs #426 (createdAt Δ7min, gleicher Diff) | `bump-wave-no-preflight-on-known-red-repos` (×1) |
| 6 | aifw-tenacity-Fleet-Bug (#1108) reaktiv bei wedding-CI gefunden statt präventiv per Canary — obwohl KONZ-018 den Bug selbst vorhersagte + 🌀 `aifw-nodeps-whackamole` bekannt ist; kein Canary-Gate im aifw-Repo | Prozesslücke | mittel | SURVIVES | #1108 (17:59Z, nennt 🌀-Muster); aifw origin/main .github/workflows/ hat kein Canary | `claim-before-cheapest-check`-Familie |
| 7 | KONZ-019 (#1104 OPEN) fordert für sein Kill-Gate ein Reminder-Issue („nicht nur review_by — M28-1-Lehre"), das noch nicht existiert → riskiert beim Merge exakt den Drift, den es benennt | verfrühte Festlegung ohne Tracking | gering | SURVIVES | #1104 OPEN, kein KONZ-019-Reminder-Issue auffindbar | `planned-phase-no-issue` (≥2) |
| 8 | Stacked-PR-Fehler: platform#1089 versehentlich auf dem KONZ-017-Doc-Branch statt main erstellt → CLOSED, #1090 neu aufgesetzt | Branch-Hygiene | gering | SURVIVES | #1089 CLOSED 07:24Z (Owner-Kommentar nennt Stacked-Fehler), #1090 MERGED | — |
| 9 | dms-hub Deploy-Health-Issue #1087 (Runner nie zugewiesen, Routine-erstellt 05:36Z) blieb in der Session unaufgegriffen, obwohl sie Deploy-Incidents (137/cad) bearbeitete + dms-hub bumpte | Backlog-Sichtbarkeit | gering | SURVIVES | #1087 OPEN, 0 Referenz in #1094/#1097/KONZ | — |

**Gegenbeweise (pre_refuted, wichtig gegen Fehlattribution, NICHT als Fehler gezählt):** tax-hub#55 +
trading-hub#126 Deploy-FAILUREs sind NICHT von der Bump-Welle verursacht — platform#1069/#1070
existierten seit 2026-07-11 (verschiedene Signaturen: „missing server host" / GHCR-403). ·
pytest_workers-Tag-Pin-Grenze wurde in shared-ci#24 korrekt kommuniziert. · wedding-`skip_tests`-
Trade-off wurde unmittelbar in #33 getrackt (kein stiller Coverage-Verlust).

**REFUTED (Phase 3, nicht im Report):** „pytest_workers-Fix empirisch widerlegt" (real:
Host-Kontention, §Befund 4) · „platform-PRs per Admin-Override gemergt" (real: temporärer
bypass_actor-Edit, per API-History belegt) · „Bump-Welle nicht verifizierbar" (real: 21
Consumer-Bump-PRs existieren; Finder suchte im falschen Repo).

## 3. Scorecard (1–5, anker-basiert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | 3 Konzepte + W0 + 2 Incidents erreicht; wedding-Ziel unerfüllt (Befund 2), 4 Bump-PRs offen — erreicht mit kleinen Mängeln |
| architektur_design | **4** | KONZ-017/018/019 tief + adversarial + selbstkorrigierend (Profil-C-Verwerfung); kleiner Mangel: Job-Katalog-Diff bei cad-hub nicht angewandt (Befund 1) |
| code_konventionstreue | **3** | Worktree-Disziplin + saubere PRs, ABER cad-hub#39 unvollständiger Fix trotz existierendem 🌀-Memory + Stacked-PR #1089 — signifikante Abweichung (Befund 1, 8) |
| risiko_debt | **3** | viele offene PRs/deferred items, ABER ALLE mit durablem Tracking-Issue (#33/#1108/#1094); über dem 23-Retro-Schnitt 2.70, aber Befund 3/4/7 = ungetrackte/lückenhafte Restrisiken |
| prozess_effizienz | **3** | viel geliefert, aber viel Rework: wedding 4 CI-Iterationen, cad #39→#42, Stacked-PR, Bump-Push-Skript-Bug, selbstverursachte Host-Kontention, hohes Signal G (Befund 1,2,4,5,8) |
| entscheidungsqualitaet | **4** | adversariale Konzepte, ehrliche Scope-Checkpoints, dokumentierte Fallbacks (wedding skip_tests), Profil-C-Selbstverwerfung — vorbildlich bis auf verfehlte Preflight-Entscheide (Befund 5) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert; |Soll| == 9 Survivors)

| Ist (beobachtet, mit Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| cad-hub#39 als „Fix" gemergt, nur ci.yml geprüft (Run 29183210419 rot) | Vor „Fix erledigt": `grep -rl '_ci-python' .github/workflows/` — ALLE Call-Sites patchen (Job-Katalog-Diff-Memory anwenden) | #1 |
| wedding „Blocker klären" wurde 4-stufiger CI-Umbau ohne Scope-Checkpoint | Bei 2. Iterationsschicht: innehalten + Scope-Wachstum spiegeln (Blocker-Fix vs. CI-Migration trennen) | #2 |
| Bypass-Episode 1 nur in GitHub-History, kein Repo-Artefakt | Jede Bypass-Nutzung erzeugt im selben Turn eine Zeile im PR-Body ODER ein Governance-Log-Issue (ADR-267-Break-Glass-Muster: Auto-Incident) | #3 |
| 24 Bump-PRs → gleichzeitige CI-Läufe → Host-Kontention (weltenhub/risk crashten) | Bump-Merges von Anfang an staffeln (Host-Last-Gate), nicht erst nach den ersten Fails; ODER Merge-Queue | #4 |
| coach/dms/risk in Bump-Welle trotz bekannt-rotem/blockiertem Zustand | Preflight je Zielrepo: `gh pr checks` + offene-Deploy-Health-Issues prüfen, bekannt-rote überspringen+melden | #5 |
| aifw-tenacity erst bei wedding-CI reaktiv gefunden | KONZ-018-eigene Canary-Empfehlung VOR Stub-Migration ausführen (aifw-Consumer-Canary-Gate) | #6 |
| KONZ-019 Kill-Gate-Reminder-Issue nur im Dokument gefordert | Reminder-Issue beim Konzept-PR-Erstellen anlegen, nicht „bei Annahme" (M28-1-Fix sofort) | #7 |
| #1089 auf Doc-Branch statt main erstellt | `git branch --show-current` + Base-Check vor jedem `switch -c` (Memory `commit-on-main-recurs`) | #8 |
| Routine-Issue #1087 (dms-Runner) blieb unaufgegriffen | Session-Start: offene `deploy-health`-Issues der Scope-Repos einlesen, bevor gleiche Repos angefasst werden | #9 |

## 5. Längsschnitt (retro_kpis.py — maschinell gezählt)

`python3 tools/retro_kpis.py` über alle `docs/retros/session-retro-*.md` gelaufen (inkl. dieser
Datei): **10 Slugs sind ≥2 = Gate-PR-Pflicht** — davon durch DIESE Session verstärkt/getroffen:
- **`claim-before-cheapest-check`** (≥2, gate) — Befund 1 (cad-hub#39 als erledigt ohne Deploy-Check) + Befund 6 (aifw predictive-nicht-angewandt). Dominanter wiederkehrender Kern.
- **`ci-replace-requires-job-catalog-diff`** — war ×1 (589606), mit Befund 1 jetzt **×2 ⇒ neu gate-pflichtig**.
- **`stale-local-clone-as-ground-truth`** (≥2, gate) — die KONZ-018-Erdung dieser Session hatte es **3×** (researchfw-Gate, ttz-hub-Pin, weltenhub-Branch), alle vom Adversariat gefangen. Bestätigt die Gate-Notwendigkeit.
- **`scope-checkpoint-not-durably-recorded`** (≥2, gate) — Befund 2 (wedding).
- **`planned-phase-no-issue`** (≥2, gate) — Befund 7 (KONZ-019 Reminder).

**Neue Slugs (×1, Beobachtung):** `ruleset-bypass-without-durable-audit-artifact` (Befund 3),
`mass-ci-wave-self-host-contention` (Befund 4), `bump-wave-no-preflight-on-known-red-repos` (Befund 5).

`refuted_rate`-Trend: 0.33 diese Session — im gesunden Band (Vorwerte 0.00–0.50). `risiko_debt`
bleibt fleet-weit schwächste Dimension (Ø 2.70/23) — diese Session mit 3 leicht darüber.

## 5b. Autonomie-Kalibrierung

- **`over_ask` = 0:** Kein Fall, wo etwas deterministisch/reversibles fälschlich vorgelegt wurde.
  Die vielen Merge-Freigaben waren **korrekt** Gate 2 (Auto-Deploy = Prod) bzw. Gate 3
  (Ruleset-Bypass). promptfw#27 wurde unter SA-1 **autonom** gemergt (kein Deploy) — korrekt.
- **`over_act` = 0:** Kein Gate autonom überschritten. Die 2 Ruleset-Bypass-Episoden liefen NACH
  je wörtlicher Freigabe („go ruleset-bypass" / „go ruleset-bypass für #1097"); der Classifier
  blockte korrekt, als „go autonom" zu unspezifisch war (Roundtrip erzwungen — die Gate-Disziplin
  hielt).
- **Meta-Beobachtung (kein over_act, aber Signal-G-Muster):** Das hohe Signal G dieser Session ist
  die empirische Rechtfertigung für die in derselben Session erarbeitete SA-Policy (SA-1/SA-3
  ratifiziert) — die Autonomie-Grenze kalibriert sich hier aus gemessener Reibung, wie 5b es will.

## 6. Verankerung (kopierfertige Kandidaten — Mensch entscheidet)

**memory_candidates:**
```
name: ci-replace-requires-all-callsites-not-just-one
type: feedback
drift: true
body: Ein CI-Versions-/Worker-Fix ist erst vollständig, wenn ALLE Aufrufer des Reusable-Workflows
  im Repo gepatcht sind — nicht nur die zuerst gemeldete Datei. cad-hub#39 fixte pytest_workers
  nur in ci.yml; deploy.yml rief _ci-python separat mit 'auto' → Prod-Deploy 5h24 rot (#42 nötig).
  Vor 'Fix erledigt': grep -rl '_ci-python' .github/workflows/. Verwandt: [[ci-replace-requires-job-catalog-diff]].
```
```
name: mass-bump-wave-stagger-and-preflight
type: feedback
body: Eine Fleet-weite Bump-Welle (N Consumer-PRs) braucht (a) Staffelung der Merges von Anfang an
  (gleichzeitige CI/Deploy-Läufe sättigen den geteilten self-hosted-Host → xdist-Crashes, hier
  weltenhub#41+risk-hub trotz WORKERS=4) und (b) Preflight je Zielrepo (bekannt-rote/blockierte
  überspringen: coach-hub#40 PROJECT_PAT, dms-hub Runner #1087, risk-hub-Dupe #425/#426).
```
```
name: ruleset-bypass-needs-durable-artifact-per-use
type: feedback
body: Jede temporäre Ruleset-bypass_actor-Nutzung braucht im selben Turn ein durables Artefakt
  (PR-Body-Zeile ODER Governance-Log-Issue) — nicht nur die GitHub-Ruleset-History. Episode 1
  (4 platform-PRs, 09:17-09:18) hatte keins; nur #1097 nannte den Bypass. IaC-Template
  bypass_actors:[] driftete 2× unbemerkt. Vorbild: ADR-267 Break-Glass (Auto-Incident+retro-Review).
```

**adr_candidates:** keiner neu — die drei Konzept-PRs (#1088/#1093/#1104) decken die Architektur ab;
das Bypass-Governance-Thema (Befund 3) gehört als Amendment-Kandidat zu ADR-267 (Break-Glass auf
Merge-Ruleset ausweiten), nicht als neuer ADR — wird in KONZ-019 §5.4 bereits als Nicht-Ziel/
Leitplanke benannt.

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

**🔵 Offen — ich kann sofort**
1. aifw-Consumer-Canary vor Stub-Migration — https://github.com/achimdehnert/platform/issues/1108
2. KONZ-019-Reminder-Issue anlegen (falls #1104 gemergt wird) — https://github.com/achimdehnert/platform/pull/1104

**🟢 Offen — dein Zug**
3. Bump-Rest: 4 offene PRs + risk-hub-Dupe schließen — https://github.com/achimdehnert/platform/issues/1094
4. dms-hub Runner-Entscheidung (eigener Runner vs. github-hosted) — https://github.com/achimdehnert/platform/issues/1087

**✅ Erledigt (diese Session, verifiziert)**
5. cad-hub Fix komplettiert + live (Image-SHA==main) — https://github.com/achimdehnert/cad-hub/pull/43
6. 137-hub Incident gelöst (Health=healthy) — https://github.com/achimdehnert/137-hub/pull/66
7. wedding-Blocker strukturell gelöst (ci/gate CLEAN) — https://github.com/achimdehnert/wedding-hub/pull/32
8. aifw-tenacity + wedding-Tests getrackt — https://github.com/achimdehnert/wedding-hub/issues/33

## 8. Nicht verifiziert (Restlücken)

- **Live-Artefakt der 13 „grünen" Bump-Deploys:** nur cad-hub wurde per Image-SHA==main + `/livez`
  live verifiziert; die übrigen 12 stützen sich auf `run-conclusion=success`. Billigster Check:
  je Repo `docker inspect <web> --format '{{.Config.Image}}'` == main-SHA + `/livez` 200.
- **weltenhub#41 Host-Kontention vs. Rest-Ursache:** Der Skeptiker belegte `WORKERS=4` + „node down"
  + Timing-Overlap, aber die *genaue* Crash-Mechanik (memcg-OOM vs. Test-Interaktion) ist nicht aus
  dmesg belegt. Billigster Check: `ssh … dmesg -T | grep -iE 'oom' um 14:00-14:10`.
- **Signal-G-Zahl exakt:** „hoch" ist qualitativ belegt (viele Merge-Roundtrips), nicht als exakte
  Roundtrips/Entscheidung gezählt. Billigster Check: `measure-evidence-discipline.py`-Analog für Merge-Gates.
