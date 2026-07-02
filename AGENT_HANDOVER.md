# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

> **Stand: Juni 2026** — CC-first (ADR-230), cc-skill-dist, 7 MCP-Server

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-06-20 — F4 geschlossen + ADR-242 Wave 2 live; Wave 3 vorbereitet)

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

## ⚡ Vorheriger Stand (2026-06-19 — comic-hub ADR-252: ADR→Code, end-to-end live verifiziert)

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

## 0. Aktuelle Prioritäten (2026-06-24 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — GATED auf shared-ci-`ci / gate`-Konvergenz (ADR-209-Programm, NICHT ad-hoc); erst danach `wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter erweitern. Worklist/Voraussetzung s. „Aktueller Stand 2026-06-20". | `[du/Sonnet]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra): onboarding-hub = leeres `STAGING_HOST`-Secret (Deploy/Staging) · 137-hub = Docker-Build-Fail · dms/tax = `cancelled` (Concurrency, benign) · weltenhub = Docker build. | `[du/Owner]` |

> **✅ Retired/erledigt (2026-06-24, hart verifiziert — billigster Check gemacht):**
> - **F4 CI-grün** als Code-CI-Programm GESCHLOSSEN (Fleet-Scan: 0 Lint/Test/Coverage-Rot; alle Roten = Deploy-Stage). **Kein Sonnet-Material mehr** — nicht erneut als Sonnet-Queue listen.
> - **coach-hub #28** gemergt 2026-06-15 (+ Dep-Fix #31, PAT/Org-Transfer). Strang zu.
> - **ADR-242 Wave 1+2** live (11 Repos geschützt, `ci / gate`).
> - **F1 `.windsurf`-Nachzügler** gesweept (lastwar-bot, iil-voice-agent) — F1 ist KEIN Einmal-Endzustand, periodisch `tools/f1-windsurf-sweep.sh` (dry-run) gegen die API laufen lassen.

**✅ Erledigt (2026-06-10):** weltenhub#16 gemergt verifiziert → **ref-sweep 12/12 komplett** · **research-hub#6** gemergt (2 teardown-Bugs gefixt: async-ORM-Connection-Leak + flush-CASCADE vs django_tenancy-FK).

**✅ Erledigt (2026-06-09):** wedding-hub#19 · onboarding-hub#2 · weltenhub pytest-Fixes · F4-Fixes: weltenhub 5, wedding-hub 3, onboarding-hub 1 · **shared-ci `v1.0.2` + `v1.0.3`** · **mcp-hub#106** + **trading-hub#14** · 11/12 ref-sweep-PRs.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#81 merged) · F1 .windsurf-Untrack vollständig (0 `.windsurf`-Files auf origin/main).

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
