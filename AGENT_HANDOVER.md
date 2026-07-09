# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

> **Stand: Juni 2026** — CC-first (ADR-230), cc-skill-dist, 7 MCP-Server

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-07-05 — ADR-265/266 accepted · PyPI-Fleet-Build + ADR-Fleet-Audit-Tooling · KONZ-012 Org-Migration · Retro×3)

**Sessions 2026-07-04/05:** Zwei große Stränge — (1) ADR-265/266 accepted + PyPI-Fleet-Build-Phase, (2) ADR-Fleet-Audit-Tooling + platform-SSoT-Org-Migrations-Konzept (KONZ-012). Plus drei adversariale Retros.

- **ADRs accepted/aktualisiert:** **ADR-265** (untrack distributed symlink targets fleetwide) + **ADR-266** (PyPI-Fleet-Lifecycle/Publishing-Konvergenz) **accepted** (#930, Entscheid Achim 07-04). **ADR-255 Rev 4** (#937) — REC-1 GitHub-Owner-Bedingung erfüllt (iilgmbh 2 Owner live verifiziert). **ADR-256 → partial** (#952) — `/mcp` live + externe Clients migriert (#128 resolved). **ADR-211 Rev 23** (#957) — Content-Screen-Typ (KONZ-009, additiv opt-in).
- **ADR-Fleet-Audit:** erster `/adr-fleet-audit`-Lauf (#916, Skill #909); F-3-Status-Flip-Triage (#929: 6 accept · 1 superseded · 1 void); ADR-Fleet-Werkzeuge persistiert + Skill-Vokabular auf adrfw-Schema (#933).
- **PyPI-Fleet (ADR-266 Build):** Inventar-Wahrheit + tote Publisher raus + Auth-Evidenz (#910); resolve-install-extra Komma-Listen (#915); Health-Workflow + origin/main-Ground-Truth (#912). `_ci-pypi` gate-Aggregat-Job + mypy_blocking + enable/bandit_blocking (#920/#938/#941).
- **KONZ-platform-012** (#939) — platform-SSoT-Org-Migration nach iilgmbh, phasen-/vorbedingungs-gegatet (T3, 3 blinde Adversarial-Agenten). Phase-A/B-Runbooks: Owner-Recovery/Leaver (#940), Runner-Reprovisionierung + Secret-Re-Population (#943). Siehe CC-Memory `project_platform_org_migration_konz012`.
- **Tooling/CI:** `sync-drift-meter` read-only Fleet-Drift-Melder (ADR-265 REC-3, #951). sync-registry C-8-Fixes (mehrschichtig: #904/#911/#926). Guard-Tests + SKIP-Aggregation für `sync-workflows.sh` (#950). handover-banner-CI-Gate + repo-session self-healing reap (Retro f5e1d, `handoff-banner-gate.yml`). Neue Skills `/kd-scout` (#942) + `/kd-review` (#944); Routing-Kanon + workflow-index-Reparatur (#905).
- **Retros:** e17299 (07-04, #918) + Increment (#925); NL2X-Fleet-Audit + Retro (07-04, #917/#932); session-retro 2026-07-05 iil-adrfw 0.7.0 (#948).
- **Offen:** ADR-242 Wave 3 unverändert gated (§0 + platform#811); Deploy-Health billing-hub/cad-hub (§0 Prio 2); shared-ci#17-Rollout (ADR-264 Build); MCP-Client `/sse`→`/mcp` (Rest von ADR-256).

## ⚡ Vorheriger Stand (2026-07-03 — ADR-264 Deployment-SSoT ACCEPTED · 2 Prod-Incidents gelöst · Retro×2)

**Diese Session (2026-07-02/03, 54a76c):** Deployment-Strategie-Arc end-to-end — Analyse → Konzept → ADR → Accept → erste Bausteine. Plus zwei Prod-Incidents diagnostiziert+gefixt und zwei adversariale Retros.

- **ADR-264 accepted** (#882): kanonische Deployment-SSoT (Staging→Prod-Promotion + Supersession-Gate). Supersession-Matrix rettete ADR-021 (52 §-Refs → `related`, NICHT abgelöst); 075/120/156/210 → `superseded_by: ADR-264`. Extern o3-reviewed (#881, „überarbeiten" eingearbeitet). Basis: KONZ-platform-011 (#859). Enforcement: `tools/check_deploy_adr_supersession.py` (9 Tests) + SUGGEST-Step in `adr-validate.yml`; Promotion zu gating = Teil des Rollouts.
- **Prod-Incidents gelöst (Host 88.198.191.108):** (a) orchestrator `/mcp` 404 — mcp-hub#165 (stateless Streamable-HTTP) + fehlender nginx-`location /mcp` am Host; IaC-Spiegel nachgezogen (#887). Live: `/mcp` → 307. (b) travel-beat 502 — web/caddy down + totes `bfagent_platform`-Netz; ADR-022-Fix travel-beat#57 deployed, Host-Netz-Krücke entfernt. Live: `/livez/` → 200. (c) **Host-Overload Load 356** — 23+ Repo-Runner auf dem EINEN Prod-Host (ADR-257 nicht fleet-ausgerollt) → T3-Konzept-Kandidat „Runner-Host-Isolation".
- **Canary + Registry:** prod-uptime-canary Label-Upsert+Close-when-green (#877) + Retry/Backoff (#887, Wirksamkeit noch unbewiesen — Retry feuerte noch nie); Registry-Drift aus #883 per `flip` gefixt (#890). **Befund: „Registry-Konsistenz (ADR-234 P0)" ist NICHT required** (nur `guardian`) → in Wave-3-Scope (#811-Kommentar 2026-07-03).
- **Retros (deep + incr):** `docs/retros/session-retro-2026-07-03-platform-54a76c{,-incr}.md`. `claim-before-cheapest-check` org-weit **×9** → `evidence_claim_scanner.py` scannt jetzt **published PR-/Issue-Bodies** (7/7 Tests). Neue Drift-Memories: host-fix-must-mirror-to-iac · host-bandaid-check-accepted-adr-first.
- **Offen:** shared-ci#17 (Deploy-Artefakt-Verify, warn-only — Review→v1.0.8→Consumer-Bump) · MCP-Client `/sse`→`/mcp` umstellen (dann Orchestrator-404 dauerhaft weg) · #883-Koordinationskommentar (Retro-incr #4) · T3-Konzept Runner-Host-Isolation · ADR-264 Build-Phase (D2-Promotion-Pilot + Rollback-Drill, 30/60/90 in KONZ-011).

> **Ältere Stände** (2026-06-20 F4/Wave-2, 2026-06-12 T5 usw.) → [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## 0. Aktuelle Prioritäten (2026-07-02 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — GATED auf shared-ci-`ci / gate`-Konvergenz; **Konvergenz-Programm GESTARTET 2026-07-02 (Freigabe Achim)**: Tracking **platform#811**, Phase-1-Sonnet-Queue = learn-hub#23 · recruiting-hub#10 · travel-beat#55. Befund-Kette: 0/26 Kandidaten emittieren `ci / gate` auf main (ABER Methodik-Blindfleck: PR-only-Trigger — Pre-Flight je Repo am PR-Head!); `iilgmbh/shared-ci` (Org-Transfer! nicht mehr achimdehnert) hat den `gate`-Job **seit v1.0.5** (`name: "gate"`, `if: always()`); Check-Kontext = `<Caller-Job> / gate` → Caller-Job MUSS `ci` lowercase ohne `name:`-Override sein (learn-hub-Bug: `name: "CI"` → `CI / …`). Phase 2 = ~23 Standalone-Libs (Worklist in #811). Erst nach Phase 1+2: `wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter. | `[Sonnet, via #811]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra). **Re-Check 2026-07-02: weitgehend geheilt** — onboarding-hub grün (seit 06-24), 137-hub grün (seit 06-21), weltenhub grün (07-01, cancelled=Concurrency benign); dms-hub weiter `cancelled` (benign, letzte Runs 06-09). **tax-hub „Issue Triage" 3× failure (07-01/02)** — Root-Cause `Input required and not supplied: github-token` (Repo hat 0 Secrets, `PROJECT_PAT` fehlt; risk-/coach-hub identisches Muster + PAT = grün). **Fix-PR iilgmbh/tax-hub#20 offen** (Fallback `PROJECT_PAT \|\| github.token`; Self-Approval-Block → wartet auf Owner-Merge; bei Merge `[skip ci]` beachten — deploy.yml feuert auf push:main ohne paths-Filter). Alternative: PROJECT_PAT als Secret setzen (Owner). | `[du/Owner]` |

> **Fortschritt 2026-07-03 (Session 54a76c):** Prio 1 (Wave 3): Scope +„Registry-Konsistenz required machen" (#811-Kommentar — Check ist heute NICHT required, nur `guardian`; Realfall #883/#884/#885 mergten rot). Prio 2 (Deploy-Health): **ADR-264 accepted** = strategischer Rahmen steht; travel-beat-Deploy wieder grün (#57); mcp-hub `/mcp` live; Rest-Item = shared-ci#17-Rollout.
>
> **Fortschritt 2026-07-06 (ERLEDIGT):** **Prio 1 — Wave-3 Phase 1 KOMPLETT** (alle 3 gemergt, `ci / gate` real grün verifiziert): learn-hub#25 (`name:"CI"`-Override raus) · recruiting-hub#13 + travel-beat#62 (**Option A1 = additiver `ci`-Job neben bestehender bespoke Test-CI**, kein Coverage-Verlust — der ursprüngliche #811-Befund „KEIN PR-getriggertes ci.yml" war für beide veraltet). recruiting#10/travel#55/learn#23 auto-closed. **Nächster Wave-3-Schritt = Phase 2** (~23 Standalone-Libs, Worklist in #811), dann Apply. **Prio 2 — Deploy-Health geheilt + live:** billing-hub 403 = **Package-`Manage Actions access` fehlte dem Repo** (NICHT Workflow — identische deploy.yml wie cad-hub, das grün pushte); Owner-Fix im Package-Setting → Rerun grün, `billing.iil.pet/healthz` 200. cad-hub = transienter GHA-Cache-Timeout → Rerun grün, `nl2cad.de/healthz` 200. **Neu: Runbook `docs/runbooks/ghcr-403-push-actions-access.md` (#967) + CC-Memory `reference_ghcr_403_push_package_actions_access`.**

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
