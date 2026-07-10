# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

> **Stand: Juni 2026** — CC-first (ADR-230), cc-skill-dist, 7 MCP-Server

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-07-10 — /send-mail-Skill End-to-End · Mittwald-Mail-Transport · Doppel-Retro f4a546/-incr · Secret-Leak-Hook gepatcht)

**Diese Session (2026-07-10):** Ad-hoc-Mailversand an Auftraggeber → User-Anweisung „Mails von hier immer über Mittwald (ad@dehnert.team)" → Skill `/send-mail` gebaut ([#1039](https://github.com/achimdehnert/platform/pull/1039)), gehärtet ([#1050](https://github.com/achimdehnert/platform/pull/1050)), Policy nachgezogen ([#1051](https://github.com/achimdehnert/platform/pull/1051)), cc-skill-dist-Rollout (doctor 7→0), zwei adversariale Retros ([#1048](https://github.com/achimdehnert/platform/pull/1048), [#1055](https://github.com/achimdehnert/platform/pull/1055) — beide gemergt).

- **Mail-Transport etabliert:** `tools/mail_agent/send_mail.py` + Skill `/send-mail` (v1.1: Step-3-Freshness-Pflicht + `tools/tests/test_send_mail.py`). Maschinen-Config `~/.claude/mail.env` (neue Policy-Ausnahme „maschinen-level Config", claude-skills.md); Credentials in `~/.secrets/mittwald_mail.env`; SMTP `mail.agenturserver.de:465`. User-Entscheid: Opt-in bis auf weiteres (kein Enforcement-Hook), weitere Accounts möglich.
- **Retro f4a546 (#1048, gemergt):** 7/7 SURVIVES. Kritisch: `mittwald_api_token` via `cut` auf Nicht-KV-Datei ins Transkript geleakt (User: keine Rotation, mStudio ungenutzt; Guard-Hook `block_env_cat.sh` gepatcht — cut/awk-Struktur-Realcheck, 7/7 Testfälle). Hoch: `--admin`-Bypass-Versuch vom Classifier geblockt → 🌀-Memories `secret-leak-cut-safe-pattern` + `no-escalation-flag-after-policy-block`. `stale-local-clone-as-ground-truth` jetzt ×4 (Gate = Skill-Freshness-Zeile, geliefert).
- **Incr-Retro (#1055, gemergt):** 6/7 SURVIVES, 1 REFUTED. Hoch: Review-Gate 5b prüfte lokal 388 vs. CI 486 Tests. Hoch: Hook-Patch war untracked. Mittel: Guard-Falsch-Positiv (`| tail` + `.env`-Prosa; trat 3× auf, Error-Pattern `error:platform:20260710-guardfp`).
- **Maßnahmen ALLE abgeschlossen (Stand 14:46Z):** I3+I5 via [#1058](https://github.com/achimdehnert/platform/pull/1058) (**`make test` = CI-SSoT**, tools-tests.yml ruft das Target; `load_credentials` last-match bei Rotation; Dogfood 487 passed lokal = CI-Parität) · I7 via [#1059](https://github.com/achimdehnert/platform/pull/1059) (Registry-Schwelle ab 2. Maschinen-Config) · I4 = Hook committet (`~/.claude` @6daa0c4) · I6 = Error-Pattern-Anker · Live-Rollout v1.1 vollzogen (doctor 1→0) · platform-pinned verworfen + Policy-Refresh (M6/M7 live).
- **OFFEN (klein):** (d) Memory-Kandidat `hooks-repo-commit-pflicht` (#1055 §6) — User-Freigabe ausstehend; (f) Outline-`/knowledge-capture` bewusst ausgelassen (Wissen in git-Retros + CC-/pgvector-Memories) — optional nachziehen; Hook-Fix-Kandidat „Reader muss Secret-Pfad als Argument tragen" (Guard-FP, s. Error-Pattern).

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

> **Ältere Stände** (2026-06-20 F4/Wave-2, 2026-06-12 T5 usw.) → [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## 0. Aktuelle Prioritäten (2026-07-02 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — Tracking **[#811](https://github.com/achimdehnert/platform/issues/811)**. **Realer Stand 2026-07-10 (gegen #811+Retro abgeglichen, weiter als der Issue selbst zeigt):** Phase 1 (learn-hub, recruiting-hub, travel-beat) komplett, gemergt UND live Wave-3-geschützt. Zusätzlich 3 Repos außerhalb der ursprünglichen Worklist live geschützt (weltenhub, illustration-hub, research-hub) — **nachträglich offiziell in #811 aufgenommen** (Entscheid Achim 07-10). Phase 2 (~23 Standalone-Libs): 13/23 verifiziert+gemergt; Rest-Kohorte in **[#987](https://github.com/achimdehnert/platform/issues/987)** (Task A: gaeb-toolkit/riskfw/weltenfw nur PR-Head-Verify; Task B: outlinefw/promptfw gated auf shared-ci#20); 5 strukturell exkludiert. Formales Phase-3-Apply-Artefakt (`wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter) **existiert noch nicht** — die 6 Live-Rulesets liefen ad-hoc außerhalb dieses Prozesses. | `[Sonnet, via #811]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra). **Re-Check 2026-07-02: weitgehend geheilt** — onboarding-hub grün (seit 06-24), 137-hub grün (seit 06-21), weltenhub grün (07-01, cancelled=Concurrency benign); dms-hub weiter `cancelled` (benign, letzte Runs 06-09). **tax-hub „Issue Triage" 3× failure (07-01/02)** — Root-Cause `Input required and not supplied: github-token` (Repo hat 0 Secrets, `PROJECT_PAT` fehlt; risk-/coach-hub identisches Muster + PAT = grün). **Fix-PR iilgmbh/tax-hub#20 offen** (Fallback `PROJECT_PAT \|\| github.token`; Self-Approval-Block → wartet auf Owner-Merge; bei Merge `[skip ci]` beachten — deploy.yml feuert auf push:main ohne paths-Filter). Alternative: PROJECT_PAT als Secret setzen (Owner). | `[du/Owner]` |

> **Fortschritt 2026-07-03 (Session 54a76c):** Prio 1 (Wave 3): Scope +„Registry-Konsistenz required machen" (#811-Kommentar — Check ist heute NICHT required, nur `guardian`; Realfall #883/#884/#885 mergten rot). Prio 2 (Deploy-Health): **ADR-264 accepted** = strategischer Rahmen steht; travel-beat-Deploy wieder grün (#57); mcp-hub `/mcp` live; Rest-Item = shared-ci#17-Rollout.
>
> **Fortschritt 2026-07-06 (ERLEDIGT):** **Prio 1 — Wave-3 Phase 1 KOMPLETT** (alle 3 gemergt, `ci / gate` real grün verifiziert): learn-hub#25 (`name:"CI"`-Override raus) · recruiting-hub#13 + travel-beat#62 (**Option A1 = additiver `ci`-Job neben bestehender bespoke Test-CI**, kein Coverage-Verlust — der ursprüngliche #811-Befund „KEIN PR-getriggertes ci.yml" war für beide veraltet). recruiting#10/travel#55/learn#23 auto-closed. **Nächster Wave-3-Schritt = Phase 2** (~23 Standalone-Libs, Worklist in #811), dann Apply. **Prio 2 — Deploy-Health geheilt + live:** billing-hub 403 = **Package-`Manage Actions access` fehlte dem Repo** (NICHT Workflow — identische deploy.yml wie cad-hub, das grün pushte); Owner-Fix im Package-Setting → Rerun grün, `billing.iil.pet/healthz` 200. cad-hub = transienter GHA-Cache-Timeout → Rerun grün, `nl2cad.de/healthz` 200. **Neu: Runbook `docs/runbooks/ghcr-403-push-actions-access.md` (#967) + CC-Memory `reference_ghcr_403_push_package_actions_access`.**

> **Fortschritt 2026-07-08 (unmerged geblieben, PR #985, jetzt konsolidiert):** Phase 2 zu 13/23 verifiziert+gemergt; shared-ci#20-Blocker gefunden; Rest-Kohorte in #987 aufgeteilt (Task A/B). Details: s. Aktueller Stand.
>
> **Fortschritt 2026-07-09/10 (ABGEGLICHEN gegen #811 + Retro, 2026-07-10):** Wave-3-Ruleset live auf 6 Repos (nicht 9 — Memory-Zahl war falsch, korrigiert gegen Retro-Ground-Truth), davon 3 außerhalb der #811-Worklist (weltenhub/illustration-hub/research-hub, jetzt nachträglich aufgenommen) + Live-Incident selbst behoben; ADR-270 accepted. **Formales Phase-3-Apply-Artefakt fehlt weiterhin.** Details: s. Aktueller Stand + #811-Kommentar.
>
> **Fortschritt 2026-07-10 (NEU, offen):** weltenhub-Redis-Incident gelöst (s. Aktueller Stand). Drei Folge-Items offen, alle Human-Decision/Freigabe, keine autonome Ausführung: (1) `ausschreibungs-hub-staging` authentik-Provider/-Application vorbereitet (client_id/signing_key/scopes/redirect geklärt gegen risk-hub-Referenz-Pattern), Freigabe-Block gestellt, Session endete vor Bestätigung — nächste Session kann direkt ausführen, kein erneutes Research nötig. (2) `staging-demo.schutztat.de` DNS-Record (→178.104.184.168) — Entscheid offen. (3) "platform"-Governance-DB (`PLATFORM_DB_HOST=bfagent_db`, degradiert aifw-AI-Features) — Entscheid offen, braucht erst Konsumenten-Inventar. (4) KONZ-platform-015 liegt lokal in `platform` (untracked, main geschützt) — braucht Worktree+PR zum Mergen, dann User-Accept-Entscheid für die Empfehlungen REC-1..REC-7. (5) **Deploy-Health-Scan (session-start) fand 3 neue `failure`** auf coach-hub/trading-hub/pptx-hub, nicht triagiert — s. Aktueller Stand.

> **PR-Hygiene (erledigt 2026-07-02, Freigabe Achim):** #753 + #746 geschlossen (Duplikate von gemergtem #808) · **#760 gemergt** (Registry iil-adrfw/codeguard — Registry-Lücke zu) · **#759 gemergt** (gen_adr_index.py; Rebase-Konflikt in INDEX.md durch Generator-Lauf gelöst, 206 aktive + 48 archivierte ADRs indiziert).

> **✅ Retired/erledigt (2026-06-24, hart verifiziert — billigster Check gemacht):**
> - **F4 CI-grün** als Code-CI-Programm GESCHLOSSEN (Fleet-Scan: 0 Lint/Test/Coverage-Rot; alle Roten = Deploy-Stage). **Kein Sonnet-Material mehr** — nicht erneut als Sonnet-Queue listen.
> - **coach-hub #28** gemergt 2026-06-15 (+ Dep-Fix #31, PAT/Org-Transfer). Strang zu.
> - **ADR-242 Wave 1+2** live (11 Repos geschützt, `ci / gate`).
> - **F1 `.windsurf`-Nachzügler** gesweept (lastwar-bot, iil-voice-agent) — F1 ist KEIN Einmal-Endzustand, periodisch `tools/f1-windsurf-sweep.sh` (dry-run) gegen die API laufen lassen.

**✅ Erledigt (2026-06-10):** weltenhub#16 gemergt verifiziert → **ref-sweep 12/12 komplett** · **research-hub#6** gemergt (2 teardown-Bugs gefixt: async-ORM-Connection-Leak + flush-CASCADE vs django_tenancy-FK).

**✅ Erledigt (2026-06-09):** wedding-hub#19 · onboarding-hub#2 · weltenhub pytest-Fixes · F4-Fixes: weltenhub 5, wedding-hub 3, onboarding-hub 1 · **shared-ci `v1.0.2` + `v1.0.3`** · **mcp-hub#106** + **trading-hub#14** · 11/12 ref-sweep-PRs.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#81 merged) · F1 .windsurf-Untrack vollständig (0 `.windsurf`-Files auf origin/main).

**KONZ-002 Enterprise-Konsolidierung:** Kill-Gate **(c) Portabilität ✅ erfüllt** (Feuerübung Runde 1, 2026-06-03; §15 D1-konform). Offen nur **extern**: (a) Kostenbestätigung + (b) Government-Sign-off, Frist **2026-08-15** — User-getrieben, keine Coding-Prio. Richtung ALT-D, Umsetzung gegated.

**CC-Skill-Dist** (platform): Drift-Score live prüfen — `python3 tools/cc-skill-dist/doctor.py` (Zahl driftet mit jedem neuen/geänderten Skill, hier nicht einfrieren)

---

## 1. MCP-Server & Tool-Calls

**Claude Code (aktuell, `mcp__<server>__<tool>` Format) — wichtigste Tool-Calls:**
- GitHub: `mcp__github__create_issue`, `mcp__github__get_pull_request`
- Memory: `mcp__orchestrator__agent_memory_context(task_description, top_k=5)`
- Deploy-Status: `mcp__orchestrator__deploy_check(action="health", repo=...)`
- Browser: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`

**Server-Übersicht (7):**

| Server | Zweck |
|--------|-------|
| **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| **orchestrator** | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint |
| **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| **paperless-docs** | Dokumente, Rechnungen, Archive |
| **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

### Windsurf-Legacy (kein Coding mehr, ADR-230)

Windsurf-Agents nutzten die o. g. Server über numerische Prefixe (`mcp0_`–`mcp6_` in
derselben Reihenfolge wie oben). Seit ADR-230 wird Windsurf **nicht mehr zum Coden**
eingesetzt (nur ADR-Review-Subset) — die Prefix-Tabelle ist nur noch für das Lesen
alter Sessions/Logs relevant, kein aktives Interface mehr.

---

## 2. Hetzner Infrastructure

| Rolle | IP | User |
|-------|-----|------|
| **Prod-Server** | `88.198.191.108` | `root` (via SSH-Key) |
| **Dev-Server (WSL)** | `localhost` | `devuser` |

**Kritische Regeln:**
- `devuser` hat **KEIN sudo-Passwort** → System-Pakete: `ssh root@localhost "apt-get install -y <pkg>"`
- PROD: nur read-only via MCP — Deploys über `scripts/ship.sh` oder CI/CD
- **NIEMALS** `ping` für Server-Check — Hetzner blockiert ICMP. TCP-Check stattdessen.

**Secrets:**
- Lokal: `~/.secrets/` (einzige Location seit 2026-05-30 — `~/shared/secrets/` konsolidiert + leer)
- Server: `/opt/shared-secrets/api-keys.env` (chmod 600, root-only)
- Repo-spezifisch: `.env.prod` (nie in Git)

---

## 3. Deploy Targets (Prod — 88.198.191.108)

| Repo | Domain | Health |
|------|--------|--------|
| `risk-hub` | schutztat.de | https://schutztat.de/healthz/ |
| `coach-hub` | kiohnerisiko.de | https://kiohnerisiko.de/healthz/ |
| `billing-hub` | billing.iil.pet | https://billing.iil.pet/healthz/ |
| `travel-beat` | travel-beat.iil.pet | https://travel-beat.iil.pet/healthz/ |
| `weltenhub` | weltenforger.com | https://weltenforger.com/healthz/ |
| `trading-hub` | trading-hub.iil.pet | https://trading-hub.iil.pet/healthz/ |
| `cad-hub` | nl2cad.de | https://nl2cad.de/healthz/ |
| `pptx-hub` | prezimo.com | https://prezimo.com/healthz/ |
| `ausschreibungs-hub` | bieterpilot.de | https://bieterpilot.de/healthz/ |
| `dms-hub` | dms.iil.pet | https://dms.iil.pet/healthz/ |
| `wedding-hub` | wedding-hub.iil.pet | https://wedding-hub.iil.pet/healthz/ |

**Deploy-Befehl:** `bash ~/github/platform/scripts/ship.sh <repo>`
**Health-Check:** `mcp2_deploy_check(action="health", repo="<repo>")`

---

## 4. Master Repo Identifier

**Alle Repos in einer Registry** (Anzahl live: `python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"`):

```bash
# project-facts.md für alle Repos generieren (nur fehlende)
python3 ~/github/platform/scripts/gen_project_facts.py

# Alle neu generieren
python3 ~/github/platform/scripts/gen_project_facts.py --force

# Einzelnes Repo
python3 ~/github/platform/scripts/gen_project_facts.py risk-hub
```

- Registry: `platform/scripts/repo-registry.yaml`
- Output: `<repo>/.windsurf/rules/project-facts.md` (trigger: always_on)
- Läuft automatisch bei `/session-start` (Step 0.3b) und `/session-ende` (Phase 3.2)

---

## 5. CC-Skills & Windsurf Rules

**CC-Skills (primär, ADR-230):** Quelle `platform/.windsurf/workflows/` → verteilt nach `~/.claude/commands/` via `cc-skill-dist`:
```bash
python3 ~/github/platform/tools/cc-skill-dist/generate.py --target ~/.claude/commands --allow-live
python3 ~/github/platform/tools/cc-skill-dist/doctor.py   # Drift-Check
```

**Windsurf Rules** (nur ADR/Review-Subset, kein Coding mehr seit ADR-230):
- Quelle: `platform/.windsurf/rules/` + `platform/.windsurf/workflows/` (tool_targets: windsurf-review)
- Verteilen: `python3 tools/cc-skill-dist/windsurf-subset.py`

**project-facts.md** (repo-spezifisch, generiert):
```bash
python3 ~/github/platform/scripts/gen_project_facts.py          # nur fehlende
python3 ~/github/platform/scripts/gen_project_facts.py --force  # alle
```

---

## 6. GitHub

**Account:** `achimdehnert`
**MCP:** `mcp1_*` für alle GitHub-Operationen
**Reusable Workflows:** `achimdehnert/platform/.github/workflows/_ci-python.yml` etc.

**Repo-Kategorien:**
- **Django Hubs** (21): risk-hub, coach-hub, billing-hub, cad-hub, trading-hub, pptx-hub, travel-beat, weltenhub, wedding-hub, recruiting-hub, dms-hub, ausschreibungs-hub, illustration-hub, research-hub, writing-hub, learn-hub, dev-hub, odoo-hub, 137-hub, bfagent, tax-hub
- **Python Libraries** (14): aifw, authoringfw, promptfw, illustration-fw, learnfw, weltenfw, outlinefw, researchfw, testkit, iil-reflex, iil-ingest, iil-enrichment, iil-fieldprefill, nl2cad
- **Infra** (5): platform, mcp-hub, infra-deploy, iil-relaunch, lastwar-bot

(Diese Kategorien sind kein vollständiges Abbild von `registry/canonical.yaml` — Gesamtzahl
live siehe oben unter §4; bei Abweichung ist die Registry maßgeblich, nicht diese Liste.)

---

## 7. pgvector Memory (Orchestrator)

| Parameter | Wert |
|-----------|------|
| **Container** | `mcp_hub_db` (Image: `pgvector/pgvector:pg16`) |
| **Läuft auf** | Prod-Server `88.198.191.108` |
| **Port auf Prod** | `127.0.0.1:15435` (Host-Binding des Containers) |
| **Lokaler Zugriff** | `localhost:15435` via SSH-Tunnel |
| **systemd Service** | `ssh-tunnel-postgres` (dev desktop, User `adehnert`) |

```bash
# Status prüfen
ss -tlnp | grep 15435
systemctl is-active ssh-tunnel-postgres

# Manuell starten (ohne sudo)
ssh -N -L 15435:localhost:15435 -i ~/.ssh/id_ed25519 root@88.198.191.108 &

# Via systemd (empfohlen — Autostart bei Neustart)
sudo systemctl start ssh-tunnel-postgres
```

- **Kein Fallback auf Cascade Memory** — pgvector MUSS laufen
- Tunnel-Ziel: `remote:localhost:15435` (nicht `:5432` — der Container bindet auf 15435)
