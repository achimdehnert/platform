# Agent Handover — Archiv

> Ausgelagerte „## ⚡ Vorheriger Stand"-Blöcke aus `AGENT_HANDOVER.md`, die älter als
> 2026-06-19 sind (Konvention: `AGENT_HANDOVER.md` hält nur den aktuellen Stand + 1
> vorherigen Stand; alles Ältere wandert hierher). Rein historisch — nicht als aktueller
> Stand lesen, nur als Kontext/Nachschlagewerk für vergangene Sessions.
>
> Ausgelagert: 2026-07-15 (Handover-Refresh 07-12→07-15), 2026-07-12 (Handover-Refresh 07-09/10→07-10), 2026-07-10 (Handover-Refresh 07-05→07-09), 2026-07-06 (Handover-Refresh 07-03→07-05), 2026-07-02 (Issue #821, Teil 2).

## ⚡ Vorheriger Stand (2026-07-10 — /send-mail-Skill End-to-End · Mittwald-Mail-Transport · Doppel-Retro f4a546/-incr · Secret-Leak-Hook gepatcht)

**Diese Session (2026-07-10):** Ad-hoc-Mailversand an Auftraggeber → User-Anweisung „Mails von hier immer über Mittwald (ad@dehnert.team)" → Skill `/send-mail` gebaut ([#1039](https://github.com/achimdehnert/platform/pull/1039)), gehärtet ([#1050](https://github.com/achimdehnert/platform/pull/1050)), Policy nachgezogen ([#1051](https://github.com/achimdehnert/platform/pull/1051)), cc-skill-dist-Rollout (doctor 7→0), zwei adversariale Retros ([#1048](https://github.com/achimdehnert/platform/pull/1048), [#1055](https://github.com/achimdehnert/platform/pull/1055) — beide gemergt).

- **Mail-Transport etabliert:** `tools/mail_agent/send_mail.py` + Skill `/send-mail` (v1.1: Step-3-Freshness-Pflicht + `tools/tests/test_send_mail.py`). Maschinen-Config `~/.claude/mail.env` (neue Policy-Ausnahme „maschinen-level Config", claude-skills.md); Credentials in `~/.secrets/mittwald_mail.env`; SMTP `mail.agenturserver.de:465`. User-Entscheid: Opt-in bis auf weiteres (kein Enforcement-Hook), weitere Accounts möglich.
- **Retro f4a546 (#1048, gemergt):** 7/7 SURVIVES. Kritisch: `mittwald_api_token` via `cut` auf Nicht-KV-Datei ins Transkript geleakt (User: keine Rotation, mStudio ungenutzt; Guard-Hook `block_env_cat.sh` gepatcht — cut/awk-Struktur-Realcheck, 7/7 Testfälle). Hoch: `--admin`-Bypass-Versuch vom Classifier geblockt → 🌀-Memories `secret-leak-cut-safe-pattern` + `no-escalation-flag-after-policy-block`. `stale-local-clone-as-ground-truth` jetzt ×4 (Gate = Skill-Freshness-Zeile, geliefert).
- **Incr-Retro (#1055, gemergt):** 6/7 SURVIVES, 1 REFUTED. Hoch: Review-Gate 5b prüfte lokal 388 vs. CI 486 Tests. Hoch: Hook-Patch war untracked. Mittel: Guard-Falsch-Positiv (`| tail` + `.env`-Prosa; trat 3× auf, Error-Pattern `error:platform:20260710-guardfp`).
- **Maßnahmen ALLE abgeschlossen (Stand 14:46Z):** I3+I5 via [#1058](https://github.com/achimdehnert/platform/pull/1058) (**`make test` = CI-SSoT**, tools-tests.yml ruft das Target; `load_credentials` last-match bei Rotation; Dogfood 487 passed lokal = CI-Parität) · I7 via [#1059](https://github.com/achimdehnert/platform/pull/1059) (Registry-Schwelle ab 2. Maschinen-Config) · I4 = Hook committet (`~/.claude` @6daa0c4) · I6 = Error-Pattern-Anker · Live-Rollout v1.1 vollzogen (doctor 1→0) · platform-pinned verworfen + Policy-Refresh (M6/M7 live).
- **Nachzug 2026-07-11/12:** (d) Memory `hooks-repo-commit-pflicht` vom User freigegeben + geschrieben ✅. **Guard-Hook v3 deployed** (argument-basierte Erkennung via shlex-Segment-Analyse; die 3 Guard-Falsch-Positive vom 07-10 als Regressionstests fixiert, Matrix 15/15; `~/.claude` @5347b51; Error-Pattern `error:platform:20260710-guardfp` auf FIXED; dokumentierte Grenzen: sed/python -c/cp) ✅. **OFFEN bleibt nur (f):** Outline-`/knowledge-capture` optional (Wissen in git-Retros f4a546/-incr + CC-/pgvector-Memories).

## ⚡ Vorheriger Stand (2026-07-09/10 — weltenhub-Prod-Incident gelöst · KONZ-platform-015 (Infra-Transparenz) · authentik-Rollout drastisch verkleinert · 2 offene Human-Decisions)

**Diese Session (2026-07-09/10):** Ausgelöst durch "authentik Rollout"-Anfrage → weltenhub-Prod-500er-Incident gefunden+gefixt → User-Auftrag "Konzept für transparente/stabile Infra" → T3-Konzept mit 3-Agenten-Adversariat + Fable-5-Synthese. Parallel-Session fand einen zweiten, artverwandten Incident (stale DNS).

- **weltenhub Prod-Incident GELÖST:** `/oidc/authenticate/` lieferte HTTP 500 (Redis-Session-Write-Fehler). Root Cause: `.env.prod` referenzierte `bfagent_redis`/`bfagent_db` (Container des dekommissionierten `bfagent` nicht mehr existent) statt der bereits vorhandenen eigenen `weltenhub_redis`/`weltenhub_db`-Container (via host-only `/opt/hub-builds/weltenhub/docker-compose.override.yml`, NICHT in git — eigener Befund im Konzept). Fix: `sed` in `.env.prod` (Hostname-Swap) + `docker compose up -d --force-recreate` (reiner `docker restart` reicht NICHT, lädt `env_file` nicht neu — Lehre). Live verifiziert: `/oidc/authenticate/` → 302, `/healthz/` → 200.
- **Noch OFFEN (nicht autonom entscheidbar, Human-Decision):** (a) zweite DB-Alias `PLATFORM_DB_HOST` zeigt weiterhin auf totes `bfagent_db` — degradiert 6 aifw-AI-Enrichment-Features (`GovernanceRouter`); unklar ob eine "platform"-Governance-DB überhaupt noch gebraucht wird. (b) `staging-demo.schutztat.de` — DNS-A-Record zeigt auf `178.104.184.168` (alter, superseded ADR-210-Ära-Host "staging-platform"), serviert falschen Content; von einer PARALLELEN Session gefunden, dort noch nicht final entschieden (umbiegen vs. löschen).
- **onboarding-hub:** User-Entscheidung — App wird nicht weiterentwickelt, kein Django-OIDC bauen. Stattdessen Cloudflare Access Application (`schulungspass.de`, Policy: nur `achim.dehnert@iil.gmbh`) erstellt + live verifiziert (302 auf Cloudflare-Login).
- **travel-beat:** ursprünglich als "Middleware-Fix nötig" vermutet (Analogie zu risk-hub PR #164) — live widerlegt: kein Bug, authentik-Application bereits vollständig live (well-known 200, korrekter 302-Redirect). Kein Fix nötig.
- **authentik-Rollout drastisch verkleinert:** von "10 Hubs × Staging+Prod" auf **5 Hubs × nur Staging** — Live-Check zeigte, dass **Prod bei ALLEN 9 verbleibenden Hubs bereits fertig ist** (ADR-142 `implementation_evidence` war veraltet). Von den 5 Staging-Lücken (137-hub, ausschreibungs-hub, pptx-hub, trading-hub, writing-hub) ist nur **ausschreibungs-hub** überhaupt erreichbar (Staging-Domains der anderen 4 antworten nicht — separater, nicht-authentik-bezogener Befund). `ausschreibungs-hub-staging`-Provider/Application-Erstellung **vorbereitet, aber NICHT ausgeführt** — Freigabe-Block gestellt, Session endete vor Bestätigung. Existenz-Check (ak shell) bestätigt: alle 5 Slugs fehlen noch.
- **KONZ-platform-015 geschrieben** (`docs/konzepte/KONZ-platform-015-...md`, T3, 3-Agenten-Adversariat Steelman/Diabolus/Maintainer-2028 + Fable-5-Synthese): Kern-Empfehlung — ADR-021 §2.17 (Compose-Sync-Guard) + ADR-264 D1 (Supersession-Gate) um eine Fehlerklasse erweitern (Runtime-Referenzen auf dekommissionierte Infra), NICHT ADR-210 (das ist selbst schon superseded — eigener Fund der Synthese). Entscheidung: **als MVP annehmen**, Kill-Gate **2026-09-07**. Noch NICHT als PR gemergt (main-Branch-Protection).
- **Neue, ungeprüfte Befunde aus dem Konzept:** `registry/repos.yaml` deckt nur 3/10 Prod-Hubs am `bf_platform_prod`-Netz ab; `verify-staging-strategy` (ADR-210) existiert nicht als CI-Ziel; `github_repos.yaml` erhebt konkurrierenden SSoT-Anspruch (Stand 2026-04-03).
- **Session 2026-07-08 (unmerged geblieben, PR #985, jetzt hier konsolidiert):** Phase-2-Sweep über die ~23 Standalone-Lib-Kandidaten aus #811 — **13/23 Repos Wave-3-ready** (`ci / gate` real verifiziert+gemergt): aifw, authoringfw, iil-adrfw, iil-django-commons, iil-reflex, apo-hub, iil-codeguard, iil-ingest, learnfw, researchfw, iil-testkit, lastwar-bot, iil-demo-fixture. **Struktureller Blocker gefunden:** `iilgmbh/shared-ci`s `_ci-pypi.yml` hat keinen `gate`-Job (anders als `_ci-python.yml` seit v1.0.5) → blockiert 5 Repos strukturell; Fix-PR **shared-ci#20** offen (Owner/Fleet-gated). Folge-Issue **[#987](https://github.com/achimdehnert/platform/issues/987)** trennt die Rest-Kohorte in Task A (3 Repos bereits auf `platform@main`-Kopie, nur PR-Head-Verifikation nötig: gaeb-toolkit, riskfw, weltenfw) und Task B (2 Repos gated auf shared-ci#20: outlinefw, promptfw). 5 Repos strukturell exkludiert (bahn-hub, decks-hub, design-hub, odoo-hub, nl2cad). **Deploy-Health-Nebenfunde derselben Session:** trading-hub GHCR 403 direkt nach Push, coach-hub `pip install` bricht an privatem Git-Dependency `django-lms-lite` ohne CI-Auth — beide nicht bearbeitet.
- **Parallel-Session 2026-07-09 (ADR-242-Wave-3 + ADR-270 + Evidence-Hook) — Zahlen korrigiert gegen Retro-Ground-Truth (`docs/retros/session-retro-2026-07-09-platform-589606.md`), pgvector-Memory hatte "9 Repos" behauptet, tatsächlich waren es 6:** main-required-checks-Ruleset auf **6 Repos appliziert** (illustration-hub, research-hub, weltenhub, learn-hub, travel-beat, recruiting-hub) — davon learn-hub/travel-beat/recruiting-hub bereits #811-Phase-1, **weltenhub/illustration-hub/research-hub waren NIE Teil der #811-Worklist** (Scope-Erweiterung ad-hoc, nicht über den in #811 selbst definierten Phase-3-Prozess `wave3-repos.json`+Apply-Workflow). **ADR-270** (Merge-Automatisierung Tier A/B) erstellt+accepted, per Amendment §5.1 rescoped. **Live-Incident selbst entdeckt+behoben:** Ruleset auf illustration-hub/research-hub nur anhand stale Check-Run-Historie appliziert (nicht Dateiinhalt) → 6 PRs blockiert; `ci`-Job nachgerüstet, Ruleset sicher reapplied — **live re-verifiziert 2026-07-10: beide Repos `ci / gate`-konform, alle PRs `CLEAN`.** Alle 6 Rulesets sind aktuell live+aktiv (verifiziert via API). Entscheidung Achim 2026-07-10: die 3 Scope-Erweiterungs-Repos werden **nachträglich offiziell in #811 aufgenommen** (nicht rückgängig gemacht).
- **session-start-Scan 2026-07-10 (Deploy-Health, noch nicht trianagiert):** Live-Check aller Prod-Repo-Deploy-Runs zeigt 3 `failure`, die weder in §0 Prio 2 noch in einer Memory-Session erwähnt sind: **coach-hub** (07-06, Steps "Install dependencies" + "Build and push" — evtl. Rezidiv des bekannten PAT/Org-Transfer-Musters, nicht neu verifiziert), **trading-hub** (07-07, Step "Import smoke (gate deploy on a runnable image)"), **pptx-hub** (07-09, Step "Build and push" — zeitlich nah an der Wave-3-Ruleset-Apply auf demselben Repo, Zusammenhang nicht geprüft). Root-Cause je Repo noch offen.

## ⚡ Vorheriger Stand (2026-07-03 — ADR-264 Deployment-SSoT ACCEPTED · 2 Prod-Incidents gelöst · Retro×2)

**Diese Session (2026-07-02/03, 54a76c):** Deployment-Strategie-Arc end-to-end — Analyse → Konzept → ADR → Accept → erste Bausteine. Plus zwei Prod-Incidents diagnostiziert+gefixt und zwei adversariale Retros.

- **ADR-264 accepted** (#882): kanonische Deployment-SSoT (Staging→Prod-Promotion + Supersession-Gate). Supersession-Matrix rettete ADR-021 (52 §-Refs → `related`, NICHT abgelöst); 075/120/156/210 → `superseded_by: ADR-264`. Extern o3-reviewed (#881, „überarbeiten" eingearbeitet). Basis: KONZ-platform-011 (#859). Enforcement: `tools/check_deploy_adr_supersession.py` (9 Tests) + SUGGEST-Step in `adr-validate.yml`; Promotion zu gating = Teil des Rollouts.
- **Prod-Incidents gelöst (Host 88.198.191.108):** (a) orchestrator `/mcp` 404 — mcp-hub#165 (stateless Streamable-HTTP) + fehlender nginx-`location /mcp` am Host; IaC-Spiegel nachgezogen (#887). Live: `/mcp` → 307. (b) travel-beat 502 — web/caddy down + totes `bfagent_platform`-Netz; ADR-022-Fix travel-beat#57 deployed, Host-Netz-Krücke entfernt. Live: `/livez/` → 200. (c) **Host-Overload Load 356** — 23+ Repo-Runner auf dem EINEN Prod-Host (ADR-257 nicht fleet-ausgerollt) → T3-Konzept-Kandidat „Runner-Host-Isolation".
- **Canary + Registry:** prod-uptime-canary Label-Upsert+Close-when-green (#877) + Retry/Backoff (#887, Wirksamkeit noch unbewiesen — Retry feuerte noch nie); Registry-Drift aus #883 per `flip` gefixt (#890). **Befund: „Registry-Konsistenz (ADR-234 P0)" ist NICHT required** (nur `guardian`) → in Wave-3-Scope (#811-Kommentar 2026-07-03).
- **Retros (deep + incr):** `docs/retros/session-retro-2026-07-03-platform-54a76c{,-incr}.md`. `claim-before-cheapest-check` org-weit **×9** → `evidence_claim_scanner.py` scannt jetzt **published PR-/Issue-Bodies** (7/7 Tests). Neue Drift-Memories: host-fix-must-mirror-to-iac · host-bandaid-check-accepted-adr-first.
- **Offen:** shared-ci#17 (Deploy-Artefakt-Verify, warn-only — Review→v1.0.8→Consumer-Bump) · MCP-Client `/sse`→`/mcp` umstellen (dann Orchestrator-404 dauerhaft weg) · #883-Koordinationskommentar (Retro-incr #4) · T3-Konzept Runner-Host-Isolation · ADR-264 Build-Phase (D2-Promotion-Pilot + Rollback-Drill, 30/60/90 in KONZ-011).

## ⚡ Vorheriger Stand (2026-06-20 — F4 geschlossen + ADR-242 Wave 2 live; Wave 3 vorbereitet)

**Diese Session (2026-06-20):** Handover-Prio #1 (F4) abgeschlossen → entsperrte ADR-242
Wave 2, beide Programme sauber verzahnt.

**F4 CI-grün = als code-CI-Programm GESCHLOSSEN.** Fleet-Survey (last push-run/default,
API): **37/50 grün**; **alle 9 roten sind Deploy-Stage** (G5/Owner/Infra) — NULL code-CI
(Lint/Test/Coverage). Restrot = Deploy-Health (separates Programm, nie autonom).
6 `update-project-facts.yml`-Retire-PRs alle gemergt. Detail: CC-Memory
`project_f4_ci_green_program`.

**ADR-242 Branch-Protection — Wave 2 LIVE, jetzt 11 Repos geschützt:**
- **Wave 1 (7):** platform, risk-hub, mcp-hub, billing-hub, cad-hub, coach-hub, dev-hub.
- **Wave 2 (4, neu 2026-06-20):** ausschreibungs-hub, trading-hub, wedding-hub, writing-hub
  — Rulesets #17924045/46/47/49, `enforcement=active`, bypass leer, required check
  **`ci / gate`**. Config-PR **#607** (wave2-repos.json + `apply-branch-protection.yml`
  auf `wave`-Input generalisiert); Apply via Dispatch (dry-run 4/0 → scharf 4/4).
- **Negativ-Test bestanden** (Confirmation §3): ausschreibungs-hub#127 (absichtl.
  Syntax-Fehler) → `ci / gate` FAILURE → `mergeStateStatus=BLOCKED` → Merge-API abgelehnt
  → PR geschlossen + Branch gelöscht.
- **Meter deckt jetzt Wave 1+2** (#611): `branch_protection_meter.py --expected` nimmt
  mehrere Wave-Dateien; Mo 06:00 UTC; Live-Smoke `11 konform · 0 Verletzungen`.

**→ WAVE 3 — Voraussetzung + Worklist (erster Zug eines neuen Strangs):**
- **Gate (ADR-242 §Entscheidung-1):** required check MUSS der stabile Aggregat-Job
  **`ci / gate`** sein — fragile per-Job-Namen sind verboten. Deshalb war Wave 2 nur
  4 Repos: von ~30 grünen unprotected Repos hatten nur diese den Aggregat-Gate.
- **Wave-3-Kandidaten = ~26 grüne Repos OHNE stabilen `ci / gate`** (Snapshot 2026-06-20,
  bei Ausführung neu scannen): aifw, apo-hub*, authoringfw, bahn-hub, decks-hub, design-hub,
  gaeb-toolkit, iil-adrfw, iil-codeguard, iil-demo-fixture, iil-django-commons, iil-ingest,
  iil-reflex, iil-testkit, lastwar-bot, learn-hub, learnfw, nl2cad, odoo-hub, outlinefw,
  promptfw, recruiting-hub, researchfw, riskfw, travel-beat, weltenfw.
  (*apo-hub hat nur den fragilen `Coverage Gate (≥0%)`-Namen — kein Kandidat ohne Fix.)
- **Voraussetzung vor Apply = shared-ci-`ci / gate`-Konvergenz** (ADR-209-Programm, NICHT
  diese Session): die shared-ci-Consumer (learn-hub/recruiting-hub/travel-beat emittieren
  `ci / *` aber kein `ci / gate` → shared-ci-Version ohne Aggregat-Job; bump nötig); die
  Standalone-CI-Libs (iil-*, *fw mit `test (3.12)`/`lint`-Jobs) brauchen Konvergenz auf
  `_ci-python.yml` ODER einen eigenen Aggregat-Gate-Job. Erst danach `wave3-repos.json`
  anlegen + `apply-branch-protection.yml wave=3` dispatchen + Negativ-Test + Meter-Liste
  erweitern.
- **Artefakte:** `governance/rulesets/{wave1,wave2}-repos.json`,
  `main-required-checks-template.json`, `.github/workflows/apply-branch-protection.yml`
  (`wave`-Input), `tools/branch_protection_meter.py` (`--expected` multi-file),
  `.github/workflows/branch-protection-meter.yml`. Pre-Flight-Pflicht je Repo (Lehre
  `feedback_adr242_wave1_doc_vs_reality`): Check-Name auf PR-Head + grüne main-CI +
  `ci / gate` läuft auf `pull_request` (sonst PR-Deadlock).

## ⚡ Vorheriger Stand (2026-06-12 — T5-Programm: ADR-243/244/245 proposed + 7-Issue-Sonnet-Queue)

**Diese Session (2026-06-12, Fable/Tier-4-5):**
- **Tier-4/5-Codebase-Analyse** (platform + 17 PyPI-Pakete, 6 parallele Agents; 3 falsifizierte
  Agent-Claims dokumentiert in CC-Memory `t5-optimierungsprogramm`).
- **PR #551 gemergt** (squash `bcdb910`): **ADR-243** iil-corefw (Shared Runtime Core) ·
  **ADR-244** Rule-Lifecycle-Loop (4 Engines inkl. Guardian!) · **ADR-245** Provider-Policy-Engine
  (free-tier-first als Code) — **alle `proposed`**, je `/adr-review`-t (4.2/3.8/3.7) + Findings
  als Fixups drin. Dazu **ADR-234 §11.2** (P0-Restschuld Verteilungs-Schicht) + INDEX-Reparatur
  (237–242 nachgetragen, **241 = reservierte Nummer ohne Datei**).
- **Sonnet-Queue erstellt** (alle `ai-assignable`): platform#552 shared-ci-Sweep (Tag-vs-main-Check
  Pflicht!) · platform#553 Pipeline-Doku · iil-testkit#6 Gotcha-Fixtures · iil-codeguard#2
  Suppression (Marker-Dialekte beachten, s. Issue-Kommentar) · iil-enrichment#2 + gaeb-toolkit#7
  publish.yml · risk-hub#177 (blocked by enrichment#2) · riskfw#4 (Owner-Entscheid Rename).

**Offen — erster Zug nächste Session:**
- **Externes ADR-243-Review einarbeiten:** Briefing liegt in
  `~/shared/adr-handoff-ADR-243-2026-06-12.md` (wartet auf GPT-Antwort vom User) →
  Step-5-Rückfluss-Gate (ID-Tagging `[valid]`/…), dann Accept-Entscheide 243→244/245
  (Sequenz: 245 braucht 243-Fehlerkategorien; 244-Severity-Heimat hängt an 243-Status).
- **Knowledge-Capture nachholen:** Outline-MCP war in dieser Session nicht gebunden —
  Session-Wissen liegt nur in pgvector (`session:platform:20260612*`) + CC-Memory.
- Plus unverändert: ADR-242 Phase 3/4, coach-hub#28, F4-Breite (s. Vorheriger Stand).

## ⚡ Vorheriger Stand (2026-06-11 — M6 ✅, ADR-242 accepted + Phase-2-Rollout ✅)

**Diese Session (2026-06-11):**
- **M6 Profil-B ✅ abgeschlossen** — PR #536 gemergt; bashrc-Block gesetzt; App public; Tokens iilgmbh+bahn-sqf grün.
- **ADR-242 accepted** — PR #535 gemergt; `status: accepted`, `implementation_status: in_progress`.
- **Rollout Phase 2 ✅** — 3 PRs parallel gemergt:
  - #540: `ci / gate` Aggregat-Job in `platform/_ci-python.yml` (required-check-Basis)
  - #541: `governance/rulesets/` — Template + Wave-1-Liste (7 Repos) + `tools/apply-branch-protection.sh`
  - #542: `workflow_dispatch`-Workflow `apply-branch-protection.yml` — Pilot über GitHub Actions UI
- **Permission** `Bash(gh api repos/*/rulesets*)` in `.claude/settings.local.json` gesetzt (ab nächster Session wirksam für direkten Script-Run).

**Offen — direkt umsetzbar (erster Zug nächste Session):**
- **ADR-242 Phase 3 (Pilot):** Workflow via GitHub Actions UI triggern: Actions → "ADR-242: Apply Branch Protection (Wave 1)" → `dry_run: true` → dann live. ODER: `bash tools/apply-branch-protection.sh` direkt (Permission in settings.local.json ab nächster Session).
- **ADR-242 Phase 4:** `branch-protection-meter` Workflow + Discord-Alert (ADR-242 §Rollout 4)
- **coach-hub #28**: STOP — `django-lms-lite` privater Repo, kein CI-Zugriff. Dep-Entscheid.
- **F4 CI-grün-Programm (Breite):** ~34 Repos rote main-CI; nächste Welle = Ruff/Config-Drift an der Quelle.

## ⚡ Vorheriger Stand (2026-06-10 — ref-sweep abgeschlossen; nur coach-hub#28 offen)

**Diese Session (2026-06-10, später):** **research-hub#6 gemergt** (squash, `7b3260d`). Zwei
unabhängige teardown-Bugs gefixt (beide mit Standalone-Repro reproduziert, dann CI-grün):
(1) async-ORM leakt worker-thread-DB-Connection (`asyncio.run` schließt sie nie) →
`being accessed by other users` — Fix `await sync_to_async(connections.close_all)()` im
Service; (2) `transaction=True`-flush-TRUNCATE ohne CASCADE scheitert an
`tenancy_module_membership` (django_tenancy FK→auth_user, ADR-130) — Fix conftest-Fixture
`sql_flush allow_cascade=True`. ⚠️ **Vorherige Diagnose „django-tenancy nicht für 3.12
verfügbar" war FALSCH** (Paket ist da, aus risk-hub/packages). Fleet-Pattern → Memory
`feedback_transaction_true_async_test_teardown`. Nur noch **coach-hub#28** offen (Dep-Entscheid).

**Diese Session (2026-06-10):** weltenhub#16 verifiziert gemergt (2026-06-09 16:46 UTC) → **ref-sweep 12/12 ✅ komplett**.

**Vorherige Session (2026-06-09 — F4-Fixes + Ref-Sweep-Abschluss):** `shared-ci v1.0.3` trägt `pg_isready -U test_user`-Fix. 5 multi-layer F4-Fixes für weltenhub, 3 für wedding-hub, 1 für onboarding-hub. Alle 12 Sweep-PRs gemergt (illustration#8, wedding#19, onboarding#2, travel-beat#38, tax-hub#4, recruiting-hub#7, dms-hub#3, cad-hub#23, billing-hub#6, mcp-hub#106/trading-hub#14, **weltenhub#16**). coach-hub#28 + research-hub#6 = STOP (research-hub#6 inzwischen gefixt+gemergt, s.o.).

**Davor (2026-06-09 — shared-ci v1.0.2):** `deploy_runs_on`-Fix → v1.0.2; mcp-hub + trading-hub forward-gefixt; alle 12 Sweep-PRs auf @v1.0.2 re-pointet. Drift: `feedback_sharedci_tag_stale_vs_platform_main`.

**Davor (2026-06-08):** F4-acute ✅, ADR-212 Phase-1 ✅, F1 .windsurf-Untrack ✅.

**Offen — direkt umsetzbar (erster Zug nächste Session):**
- **coach-hub #28**: STOP — `django-lms-lite` ist privater GitHub-Repo, kein CI-Zugriff (Test + Security Scan scheitern an `git clone … Authentication failed`). Entscheiden: Dep öffentlich machen / mirror / als Wheel vendoren / PAT-Zugriff fixen. = einzige offene ref-sweep-PR; Dep-Architektur-Entscheid, kein Test-Fix.
- **M6 Profil B fertig:** nur noch manuell: App auf **„Any account"** + Install auf `iilgmbh`+`bahn-sqf` → dann `claude-ent iilgmbh` = Org-Admin. Details: `docs/PROFILE_B.md`.
- **Branch-Protection-Lücke:** 0/14 Hubs haben required-status-checks auf `main` → no-bypass unenforced. ADR-Kandidat.
- **#7 risk-hub→Enterprise-Transfer:** deferred (gegated hinter KONZ-002 S2).
- **shared-ci Issue #3:** eigene CI (actionlint) für die reusable Workflows.

**Kontext-Memories (auto-load):** 🌀 `feedback_sharedci_tag_stale_vs_platform_main` · `project_profile_b_app_state` · `project_riskhub_prod_launch` · 🌀 `feedback_commit_on_main_recurs` · 🌀 `feedback_merge_to_main_triggers_deploy`.

---

## ⚡ Stand (2026-06-19 — comic-hub ADR-252: ADR→Code, end-to-end live verifiziert)

**Diese Session (2026-06-19):** comic-hub von „ist das möglich?" bis zum **lauffähigen,
released, end-to-end verifizierten Produktionspfad** durchgezogen.

**Architektur (platform ADR-252, proposed + 4 Amendments, alle auf main):**
- Thin-Composer über weltenfw/authoringfw/illustration-fw, **gegated**. PRs #597/#598/#599/#604.
  2 externe Cross-Provider-Reviews + `/adr-challenger` eingearbeitet.
- **Gate 0a** (Spike, fal ~$1) = **CONDITIONAL PASS**: Einzelidentität (D1) stark; Multi-Ref-Co-Gen
  (D4) untauglich (1/6) → **Compositing** (empirisch 2/2 belegt). Engine **Qwen-Image-Edit** (Apache-2.0).
- **Gate 1** Klickdummy **live**: https://iil.pet/kd/comic-hub/klickdummy/comic-lifecycle/ (CF-Access).
- **Hub-vs-View ENTSCHIEDEN = O1-B** (Modul in illustration-hub; Produkt-Input: Experiment +
  persistente Projekte + mandantenfähig).

**Code (auf main, getestet):**
- **comics-Modul** illustration-hub `apps/comics/` (ComicProject/Page/Panel/PanelCharacter/
  SpeechBubble/GenerationManifest) — PR #12.
- **ConsistentSequenceAgent** illustration-fw — **PyPI 0.3.0** (OIDC Trusted Publishing, PR #14+#15).
- **FalSequenceBackend** + **render_panel** (Persistenz: Asset+Manifest, Panel.render_asset) —
  illustration-hub PR #13+#14.
- **Live-E2E verifiziert**: render_panel gegen echtes fal → echtes Mehrpersonen-Panel + persistiert
  (gegateter Test `RUN_LIVE_FAL=1`; Bild `~/shared/comic-spike/out/E2E_render_panel.png`).

**Offen (bewusst, keine offenen PRs):**
- **illustration-fw #10** typisierter Capability-Vertrag (Post-Gate-0).
- **Gate 0b** Self-Host auf RTX 4090 (beim cloud→lokal-Switch; Qwen ist Brückenmodell).
- ~~finale menschliche Rubrik-Bewertung der Spike-Bilder~~ → **2026-06-20 PASS bestätigt** (Achim):
  Gate 0a final bestanden, kein Vorbehalt offen (`~/shared/comic-spike/gate-0a-result-2026-06-19.md`).
- **Nachschärfen = laufzeit-Optimierungs-Funktion** in ADR-252 verankert (`Review→Retry`-Kante der
  State-Machine: (a) identitätserhaltender Re-Roll im MVP-Review · (b) gegatete Quality-Escalation
  Relight/Upscale/Engine-Switch/LoRA). Umsetzungs-Detail → illustration-hub Use-Case.
- Detail-CC-Memory: `project_comic_hub_adr252`. pgvector-Session-Summary war 404 (MCP-Flapping) → nachtragen.

> Lehren (Drift-vermeidend): genesor-Quelle = **iil-pet-portal** (nicht `~/github/genesor`) ·
> `fal_client.subscribe()` hängt → `submit()`+poll · `password:` + `id-token:write` zusammen =
> OIDC aus (403) · Merge-/Publish-Claims gegen GitHub/PyPI-Simple-Index verifizieren (Aggregat-JSON laggt) ·
> ein D4-Panel war zu wenig (Härtetest falsifizierte optimistisches PASS) · pgrep self-match → `ps|grep '[d]'`.

---

---

## ⚡ Stand (2026-07-05 — ADR-265/266 accepted · PyPI-Fleet-Build + ADR-Fleet-Audit-Tooling · KONZ-012 Org-Migration · Retro×3)

**Sessions 2026-07-04/05:** Zwei große Stränge — (1) ADR-265/266 accepted + PyPI-Fleet-Build-Phase, (2) ADR-Fleet-Audit-Tooling + platform-SSoT-Org-Migrations-Konzept (KONZ-012). Plus drei adversariale Retros.

- **ADRs accepted/aktualisiert:** **ADR-265** (untrack distributed symlink targets fleetwide) + **ADR-266** (PyPI-Fleet-Lifecycle/Publishing-Konvergenz) **accepted** (#930, Entscheid Achim 07-04). **ADR-255 Rev 4** (#937) — REC-1 GitHub-Owner-Bedingung erfüllt (iilgmbh 2 Owner live verifiziert). **ADR-256 → partial** (#952) — `/mcp` live + externe Clients migriert (#128 resolved). **ADR-211 Rev 23** (#957) — Content-Screen-Typ (KONZ-009, additiv opt-in).
- **ADR-Fleet-Audit:** erster `/adr-fleet-audit`-Lauf (#916, Skill #909); F-3-Status-Flip-Triage (#929: 6 accept · 1 superseded · 1 void); ADR-Fleet-Werkzeuge persistiert + Skill-Vokabular auf adrfw-Schema (#933).
- **PyPI-Fleet (ADR-266 Build):** Inventar-Wahrheit + tote Publisher raus + Auth-Evidenz (#910); resolve-install-extra Komma-Listen (#915); Health-Workflow + origin/main-Ground-Truth (#912). `_ci-pypi` gate-Aggregat-Job + mypy_blocking + enable/bandit_blocking (#920/#938/#941).
- **KONZ-platform-012** (#939) — platform-SSoT-Org-Migration nach iilgmbh, phasen-/vorbedingungs-gegatet (T3, 3 blinde Adversarial-Agenten). Phase-A/B-Runbooks: Owner-Recovery/Leaver (#940), Runner-Reprovisionierung + Secret-Re-Population (#943). Siehe CC-Memory `project_platform_org_migration_konz012`.
- **Tooling/CI:** `sync-drift-meter` read-only Fleet-Drift-Melder (ADR-265 REC-3, #951). sync-registry C-8-Fixes (mehrschichtig: #904/#911/#926). Guard-Tests + SKIP-Aggregation für `sync-workflows.sh` (#950). handover-banner-CI-Gate + repo-session self-healing reap (Retro f5e1d, `handoff-banner-gate.yml`). Neue Skills `/kd-scout` (#942) + `/kd-review` (#944); Routing-Kanon + workflow-index-Reparatur (#905).
- **Retros:** e17299 (07-04, #918) + Increment (#925); NL2X-Fleet-Audit + Retro (07-04, #917/#932); session-retro 2026-07-05 iil-adrfw 0.7.0 (#948).
- **Offen:** ADR-242 Wave 3 unverändert gated (§0 + platform#811); Deploy-Health billing-hub/cad-hub (§0 Prio 2); shared-ci#17-Rollout (ADR-264 Build); MCP-Client `/sse`→`/mcp` (Rest von ADR-256).
