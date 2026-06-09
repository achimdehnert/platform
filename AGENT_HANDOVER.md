# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

> **Stand: Juni 2026** — CC-first (ADR-230), cc-skill-dist, 7 MCP-Server

## ⚡ Aktueller Stand (2026-06-09 — shared-ci v1.0.2 / ref-sweep-Incident)

**Letzte Session (2026-06-09 — shared-ci-Tag-Fix + 2 broke Prod-Mains repariert):** Der ref-sweep auf `iilgmbh/shared-ci@v1.0.1`/`@v1.0.0` war **defekt** — der Tag wurde **vor** #461 geschnitten und kennt den Input `deploy_runs_on` nicht; runner-pinnende Consumer (mcp-hub, trading-hub mit `deploy_runs_on: prod-server`) lösten beim Merge→main einen reusable-WF **`startup_failure`** aus (Deploy startet nie, Live-Service blieb auf altem Image). Fix: `deploy_runs_on` (#461) **+** import_smoke-`--entrypoint sh`-Bypass (cad-hub#21) aus `platform@main` nach shared-ci portiert → **`iilgmbh/shared-ci#4` merged, Tag `v1.0.2`** (Parität zu platform@main). Beide broke Mains **forward**-gefixt (statt Revert auf mutable `@main`): **mcp-hub#106** + **trading-hub#14** gemergt → beide Deploys **success**, `orchestrator.iil.pet/healthz/` **200** + `ai-trades.de/livez/` **200**. Alle 12 offenen Sweep-PRs auf `@v1.0.2` re-pointet (gehalten auf F4). Drift-Memory: `feedback_sharedci_tag_stale_vs_platform_main`.
> **Zweitfund (offen):** „ref-sweep gated auf F4, no-bypass" ist **unenforced** — **0/14 Hubs** haben Branch-Protection auf `main` (`GET /branches/main/protection` → 404). trading-hub#13 wurde **manuell rot gemergt** (kein Auto-Merge) → brach Prod-Deploy. „No-bypass" ist reine Konvention; required-status-checks = eigener Governance-Task (ADR-Kandidat).

**Davor (2026-06-08):** **F4-acute abgeschlossen** — alle 6 trivialen `ai-assignable`-Issues zu (researchfw#4, weltenfw#5, learn-hub#8, trading-hub#9 bereits closed; travel-beat#37 + recruiting-hub#6 verifiziert bereits auf main grün → kommentiert + closed, kein PR nötig). **ADR-212 Phase-1 verifiziert komplett** — dev-hub#56 war stale Hand-PR, superseded durch **dev-hub#81 (merged)** + platform#485. Org-weite `ai-assignable`-DO-NOW-Queue ist **leer**.

**Davor (2026-06-05 — github-admin / risk-hub-Launch / KONZ-002):** risk-hub **live in Prod** als Kundenprodukt (schutztat.de) + Cross-Tenant-Edit-Fix (PR #168, merged); **Profil-B-GitHub-App** aufgesetzt (App 3971306, Token-Smoke grün); **KONZ-002 ref-sweep** über 17 Hubs; **deep Session-Retro** (Report: `~/shared/session-retro-2026-06-05-platform-ghadmin.md`).

**Offen — direkt umsetzbar (erster Zug nächste Session):**
- **M6 Profil B fertig:** `~/.bashrc`-Block (`GH_APP_ID=3971306`, `claude-ent()`) **✅ vorhanden** (bashrc:126–132); offen nur noch **manuell**: App auf **„Any account"** + Install auf `iilgmbh`+`bahn-sqf` → dann `claude-ent iilgmbh` = Org-Admin. Details: `docs/PROFILE_B.md`.
- **12 gehaltene ref-sweep-PRs** (`achimdehnert/platform`→`iilgmbh/shared-ci@v1.0.2`, **alle 2026-06-09 auf v1.0.2 re-pointet**: weltenhub#16, wedding-hub#19, travel-beat#38, tax-hub#4, recruiting-hub#7, onboarding-hub#2, illustration-hub#8, dms-hub#3, coach-hub#28, cad-hub#23, billing-hub#6, research-hub#6) → mergen sobald **F4** das jeweilige Repo grün macht (kein CI-/Security-Bypass; Gate ist Konvention, s. Zweitfund oben). **mcp-hub#98 + trading-hub#13 raus aus dieser Liste** — beide bereits @v1.0.1 gemergt+gebrochen, forward-gefixt via #106/#14 (done).
- **Branch-Protection-Lücke (NEU 2026-06-09):** 0/14 Hubs haben required-status-checks auf `main` → „no-bypass" unenforced. Entscheiden ob fleet-weit required-checks (ADR) — Friktion mit minutenlang `queued` self-hosted-Checks bedenken. Nicht reflexhaft flippen.
- **#7 risk-hub→Enterprise-Transfer:** bewusst **deferred** (Bake + geplantes Fenster; gegated hinter KONZ-002 S2). `platform`-Self-Refs (publish-Workflows) separat/vorsichtig sweepen.
- **shared-ci Issue #3:** eigene CI (actionlint) für die reusable Workflows.

**Kontext-Memories (auto-load):** 🌀 `feedback_sharedci_tag_stale_vs_platform_main` (NEU) · `project_profile_b_app_state` · `project_riskhub_prod_launch` · `project_riskhub_entitlement_gaps` · 🌀 `feedback_commit_on_main_recurs` · 🌀 `feedback_merge_to_main_triggers_deploy`.

---

## 0. Aktuelle Prioritäten (2026-06-09)

| Prio | Task | Tier |
|---|---|---|
| 1 | **F4 CI-grün-Programm (Breite)** — weiterhin ~34 Repos rote main-CI (akute `ai-assignable`-Tranche ✅ leer); nächste Welle = Ruff/Config-Drift an der Quelle, nicht Issue-für-Issue | `[Sonnet]` |
| 2 | **12 ref-sweep-PRs mergen** (auf `@v1.0.2`) — pro Repo sobald dessen main-CI grün (gated auf F4; Gate unenforced → Disziplin); Liste oben | `[Sonnet]` |
| 3 | **M6 Profil-B fertigstellen** — nur noch manuell: App „Any account" + Org-Installs iilgmbh/bahn-sqf (`docs/PROFILE_B.md`); bashrc-Block schon da | `[manuell]` |
| 4 | **Branch-Protection-Entscheid** — required-status-checks fleet-weit ja/nein (ADR-Kandidat); macht „no-bypass" real | `[du/ADR]` |

**✅ Erledigt (2026-06-09):** **shared-ci `v1.0.2`** (deploy_runs_on #461 + import_smoke-Bypass cad-hub#21, `iilgmbh/shared-ci#4` merged+getaggt) · **mcp-hub#106** (→@v1.0.2, Deploy success, orchestrator /healthz/ 200) · **trading-hub#14** (→@v1.0.2, Deploy success, ai-trades.de/livez/ 200) · **12 Sweep-PRs auf @v1.0.2 re-pointet** (inkl. research-hub#6 das auf @v1.0.0 zeigte) · Drift-Memory + Branch-Protection-Lücke (0/14) dokumentiert.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 trivialen `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#56 stale → superseded by dev-hub#81 merged; verifiziert) · **F1 .windsurf-Untrack vollständig** (Distributor retired, gesamte Flotte inkl. dev-hub clean; 2 zuletzt entdeckte Residual-Libs iil-django-commons#1 + riskfw#1 untrackt+gemergt → 0 `.windsurf`-100644 auf origin/main; N/A: adr-doctor leerer Repo, platform = SSoT) · **3 mergebare PRs gemergt** (platform #476 Profil-B, #478 main-tree-guard, `iilgmbh/shared-ci` #2 immutable ref — alle merged 2026-06-05, war stale als „offen" gelistet).

**KONZ-002 Enterprise-Konsolidierung:** Kill-Gate **(c) Portabilität ✅ erfüllt** (Feuerübung Runde 1, 2026-06-03; §15 D1-konform). Offen nur **extern**: (a) Kostenbestätigung + (b) Government-Sign-off, Frist **2026-08-15** — User-getrieben, keine Coding-Prio. Richtung ALT-D, Umsetzung gegated.

**CC-Skill-Dist** (platform): `doctor.py` DRIFT-SCORE 0 ✓ (74 Skills, 2026-06-01)

---

## 1. MCP-Server & Prefixes (aktuell)

| Prefix | MCP-Server | Zweck |
|--------|-----------|-------|
| `mcp0_` | **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| `mcp1_` | **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| `mcp2_` | **orchestrator** | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint |
| `mcp3_` | **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| `mcp4_` | **paperless-docs** | Dokumente, Rechnungen, Archive |
| `mcp5_` | **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| `mcp6_` | **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

**Wichtigste Tool-Calls (Claude Code — `mcp__<server>__<tool>` Format):**
- GitHub: `mcp__github__create_issue`, `mcp__github__get_pull_request`
- Memory: `mcp__orchestrator__agent_memory_context(task_description, top_k=5)`
- Deploy-Status: `mcp__orchestrator__deploy_check(action="health", repo=...)`
- Browser: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`

> Windsurf-Agents nutzen `mcp0_`–`mcp6_`-Prefixe — aber Windsurf wird seit ADR-230 nicht mehr zum Coden eingesetzt (nur ADR-Review-Subset).

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

**Alle 41 Repos in einer Registry:**

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
- **Django Hubs** (22): risk-hub, coach-hub, billing-hub, cad-hub, trading-hub, pptx-hub, travel-beat, weltenhub, wedding-hub, recruiting-hub, dms-hub, ausschreibungs-hub, illustration-hub, research-hub, writing-hub, learn-hub, dev-hub, odoo-hub, mcp-hub, 137-hub, bfagent, tax-hub
- **Python Libraries** (14): aifw, authoringfw, promptfw, illustration-fw, learnfw, weltenfw, outlinefw, researchfw, testkit, iil-reflex, iil-ingest, iil-enrichment, iil-fieldprefill, nl2cad
- **Infra** (5): platform, mcp-hub, infra-deploy, iil-relaunch, lastwar-bot

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
