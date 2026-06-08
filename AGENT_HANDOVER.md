# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

> **Stand: Juni 2026** — CC-first (ADR-230), cc-skill-dist, 7 MCP-Server

## ⚡ Aktueller Stand (2026-06-08 — F4-acute / ADR-212-Verifikation)

**Letzte Session (2026-06-08):** **F4-acute abgeschlossen** — alle 6 trivialen `ai-assignable`-Issues zu (researchfw#4, weltenfw#5, learn-hub#8, trading-hub#9 bereits closed; travel-beat#37 + recruiting-hub#6 verifiziert bereits auf main grün → kommentiert + closed, kein PR nötig). **ADR-212 Phase-1 verifiziert komplett** — dev-hub#56 war stale Hand-PR, superseded durch **dev-hub#81 (merged)** + platform#485. Org-weite `ai-assignable`-DO-NOW-Queue ist **leer**.

**Davor (2026-06-05 — github-admin / risk-hub-Launch / KONZ-002):** risk-hub **live in Prod** als Kundenprodukt (schutztat.de) + Cross-Tenant-Edit-Fix (PR #168, merged); **Profil-B-GitHub-App** aufgesetzt (App 3971306, Token-Smoke grün); **KONZ-002 ref-sweep** über 17 Hubs; **deep Session-Retro** (Report: `~/shared/session-retro-2026-06-05-platform-ghadmin.md`).

**Offen — direkt umsetzbar (erster Zug nächste Session):**
- **M6 Profil B fertig:** `~/.bashrc`-Block (`GH_APP_ID=3971306`, `claude-ent()`) **✅ vorhanden** (bashrc:126–132); offen nur noch **manuell**: App auf **„Any account"** + Install auf `iilgmbh`+`bahn-sqf` → dann `claude-ent iilgmbh` = Org-Admin. Details: `docs/PROFILE_B.md`.
- **14 gehaltene ref-sweep-PRs** (`achimdehnert/platform`→`iilgmbh/shared-ci@v1.0.1`, verifiziert 2026-06-08 noch offen: weltenhub#16, wedding-hub#19, travel-beat#38, trading-hub#13, tax-hub#4, recruiting-hub#7, onboarding-hub#2, mcp-hub#98, illustration-hub#8, dms-hub#3, coach-hub#28, cad-hub#23, billing-hub#6, research-hub#6) → mergen sobald **F4** das jeweilige Repo grün macht (kein CI-/Security-Bypass).
- **#7 risk-hub→Enterprise-Transfer:** bewusst **deferred** (Bake + geplantes Fenster; gegated hinter KONZ-002 S2). `platform`-Self-Refs (publish-Workflows) separat/vorsichtig sweepen.
- **shared-ci Issue #3:** eigene CI (actionlint) für die reusable Workflows.

**Kontext-Memories (auto-load):** `project_profile_b_app_state` · `project_riskhub_prod_launch` · `project_riskhub_entitlement_gaps` · 🌀 `feedback_commit_on_main_recurs`.

---

## 0. Aktuelle Prioritäten (2026-06-08)

| Prio | Task | Tier |
|---|---|---|
| 1 | **F4 CI-grün-Programm (Breite)** — weiterhin ~34 Repos rote main-CI (akute `ai-assignable`-Tranche ✅ leer); nächste Welle = Ruff/Config-Drift an der Quelle, nicht Issue-für-Issue | `[Sonnet]` |
| 2 | **14 ref-sweep-PRs mergen** — pro Repo sobald dessen main-CI grün (gated auf F4, kein Bypass); Liste oben | `[Sonnet]` |
| 3 | **M6 Profil-B fertigstellen** — nur noch manuell: App „Any account" + Org-Installs iilgmbh/bahn-sqf (`docs/PROFILE_B.md`); bashrc-Block schon da | `[manuell]` |

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
