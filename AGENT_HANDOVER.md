# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents** — MCP-Tool-Mappings,
Infra-Zugänge, Deploy-Targets, Scripting-Referenz. **Arbeitsstand, nicht Archiv:**
jedes Byte hier kostet Kontext in *jeder* Sitzung.

<!-- KONVENTION — gilt fuer JEDE H2-Sektion, nicht nur fuer "## ⚡"-Bloecke:
     Stand-Bloecke: aktueller + hoechstens EIN vorheriger, soweit der Deckel es traegt.
     Jede andere Sektion haelt nur, was heute handlungsleitend ist; sobald sie Verlauf
     ansammelt (erledigte Punkte, "Fortschritt <Datum>", Reconciliation-Vermerke),
     wandert sie als GANZES nach AGENT_HANDOVER_ARCHIVE.md — dort ANHAENGEN mit
     Datumsmarke und Herkunftszeile, nichts loeschen, und Offenes vorher als Kurzzeile
     nach "## Offene Fäden" retten. Details unten: "## Konventionen dieser Datei". -->

**Archiv älterer Stände und ausgelagerter Sektionen:**
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## ⚡ Aktueller Stand (2026-09-03 nachmittags/abends — Phase C 56/56 abgeschlossen, Zug A SECURITY.md + Notices: Pilot durch, Welle 9 PRs offen)

**Zeitanker:** HEAD `072f6e7a` · `rev-list --count` 4090 · geschrieben 2026-09-03

**Zielzustand (Owner-Worte 2026-09-03 „21 Vorschlag Phase C · 22 go · 23 teste gx10/gpu-box" → erreicht; „43 A · 44 ausschreibungs-hub + dev-hub raus · 45 go · 56 go" → [#2787](https://github.com/achimdehnert/platform/issues/2787) Zug A: Pilot **erreicht** (trading-hub#202 + writing-hub#1007 gemergt, coach-hub Preflight-Ausfall), Welle **verschoben mit Anker** — 9 PRs offen, Merges gestaffelt beim Owner.**

**Gemergt (7 PRs, 4 Repos).** Phase C [dev-hub#321](https://github.com/achimdehnert/dev-hub/pull/321) (56/56, Median Readiness 52, 53 P1 in 33 Repos) · Bewerter-Fix + Renderer [#2782](https://github.com/achimdehnert/platform/pull/2782) ([#2780](https://github.com/achimdehnert/platform/issues/2780)) · Melder 0.7.1/0.7.1b über den Hop [#2781](https://github.com/achimdehnert/platform/pull/2781) (gx10/gpu-box antworten; Tab-Kollaps in `bash read`) · Werkzeug `tools/welle_security_notices.py` + `docs/templates/SECURITY.md` [#2788](https://github.com/achimdehnert/platform/pull/2788) · [trading-hub#202](https://github.com/achimdehnert/trading-hub/pull/202) (kein Deploy, `paths-ignore` greift) · [writing-hub#1007](https://github.com/achimdehnert/writing-hub/pull/1007) (**deployte** — Filter fiel offen, [writing-hub#1008](https://github.com/achimdehnert/writing-hub/issues/1008)).

**Welle offen (Owner mergt ≤ 3/h, jeder Merge deployt):** [137-hub#95](https://github.com/achimdehnert/137-hub/pull/95) · [billing-hub#45](https://github.com/achimdehnert/billing-hub/pull/45) · [cad-hub#63](https://github.com/achimdehnert/cad-hub/pull/63) · [decks-hub#80](https://github.com/achimdehnert/decks-hub/pull/80) · [dms-hub#70](https://github.com/achimdehnert/dms-hub/pull/70) · [learn-hub#45](https://github.com/achimdehnert/learn-hub/pull/45) · [tax-hub#133](https://github.com/iilgmbh/tax-hub/pull/133) (iilgmbh) · [weltenhub#74](https://github.com/achimdehnert/weltenhub/pull/74) · [travel-beat#96](https://github.com/achimdehnert/travel-beat/pull/96) **erst nach Runner** (#95). Ausgelassen: bahn-hub, risk-hub (Deploy rot), wedding-hub (Deploy hängt 13 d), recruiting-hub (archiviert). **Zug B (Lockfile) nicht freigegeben** (Zahlen in #2737).

**Befunde:** writing-hub-Doku-Filter blind (kein `gh` auf `ci-nonprod`, Fail-open; meine Aussage „Pfadfilter greift" war Definition statt Lauf) · `pr_merge_sa.py` zählt veraltete Läufe, Rerun liest alten PR-Text ([#2784](https://github.com/achimdehnert/platform/issues/2784)) · Hop-Aufbau dreifach ([#2783](https://github.com/achimdehnert/platform/issues/2783)) · Owner mergte Dependabot auf shared-ci v1.1.14 (intern ungepinnt, [shared-ci#73](https://github.com/iilgmbh/shared-ci/issues/73)) · Preflight: Label heißt `deploy-failure-escalation`, Archiv-Status fehlte, tax-hub lebt in iilgmbh · 3 Sonnet-Subagenten brachen beim Monitor-Warten ab (Memory).

**Nächster Schritt:** Owner mergt die Welle gestaffelt; „57 go" → 36 Repos ohne Prod-Deploy (kein Deploy, keine Staffelung; Brief wie in #2787, Preflight + „archiviert?"). Danach K5-Messung (`future_readiness_score.py` je Repo, D08.4/D11.2 ok) und Vorher/Nachher-Zeile in dev-hub `docs/audits/future-readiness/`. Parallel: writing-hub#1008 (gh auf ci-nonprod ODER urllib), v2.4 aus #2737.

**SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen. SA-M: 3 Merges per Mandat (#2788 W1/M1 nach Freigabe-Vermerk im Issue-Body, trading-hub#202 W0, #2781/#2782/dev-hub#321 durch Owner). Delegation: 4 Sonnet-Subagenten nach Brief (Phase C 458k, Melder 151k, Werkzeug 148k, Welle 139k Tokens), Prüfung + Fixes inline. Session `session_01Lob9LxJAYX6hGAHGMF29oh`.

**0h Fremdabnahme (Sonnet, nur Artefakte):** Zielzustand A (Phase C + gx10/gpu-box) **nicht erreicht → verschoben mit Anker**: Scorecard trug `achimdehnert/platform` zweimal mit Rubrik `2.3-deterministic` (Canary 10:30 P1=1 vs. Phase C P1=0) — Fix [dev-hub#325](https://github.com/achimdehnert/dev-hub/pull/325) (Rubrik `2.3-deterministic/phase-c` für die drei Canary-Zeilen), Merge beim Owner (dev-hub deployt bei jedem Push, Prod-Rückstand); alle übrigen A-Kriterien ERFÜLLT mit Beleg. Zielzustand B (Zug A) **erreicht**, inkl. der selbst dokumentierten Abweichung writing-hub#1008. 0e Clear-Härte: alle drei Fragen NEIN (Freigabe-Wortlaut im #2787-Body, Zug-B-Zahlen in #2737, Klassifikationsregeln in dev-hub 01-scope, „57" im Stand-Block dekodiert). Ende-Runner: E.5 ungeprüft (#2782 #2788), E.6 Werkzeugfehler (GitHub-Drosselung) — beides Lücke, keine Entwarnung; E.7 dirty nur fremde Bäume (dev-hub Haupt-Tree, meiki-hub, risk-hub).

## Offene Fäden (über den Session-Stand hinaus)

Je eine Zeile mit Link, kein Verlauf. Frisches steht oben im Stand-Block, Historie in
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md). Jede Zeile zeigt auf ein
**offenes** Issue — ist es geschlossen, gehört sie ins Archiv, nicht hierher.

1. KONZ-054 Systembild, Kill-Gate 2026-10-15; Owner-Punkte #2486/#2504/#2507, Reste #2480: https://github.com/achimdehnert/platform/issues/2516
2. KONZ-051 ux-review-agent, Kill-Gate 2026-09-30; K1 3/9, K3 offen: https://github.com/achimdehnert/writing-hub/issues/766
3. Volume-Deckung prod (40 Volumes), K2 = Owner-Gate, Löschliste #2258: https://github.com/achimdehnert/platform/issues/2300
4. KONZ-052-Rest: `PYPI_API_TOKEN` löschen (Owner-Wort, dann #1904 zu), Erstrelease iil-enrichment/gaeb-toolkit: https://github.com/achimdehnert/platform/issues/2380
5. PyPI-Org `iil`: Support-Antwort, Frist 2026-09-08, danach Konto härten: https://github.com/achimdehnert/platform/issues/2291
6. Gate-Deckung: 11 ungedeckte Slugs, 28 %: https://github.com/achimdehnert/platform/issues/2234
7. Wirksamkeits-Bilanz der Gates: gemessen, Konsequenz je Gate offen: https://github.com/achimdehnert/platform/issues/2374
8. Concurrency je Ziel-Umgebung: 13 gleichlautende PRs in der Flotte offen: https://github.com/achimdehnert/platform/issues/2229
9. `deploy_wirkung`-Restbefunde: https://github.com/achimdehnert/platform/issues/2148
10. risk-hub hängt >26 Commits zurück (DSB-Tätigkeitsnachweis), Migrationen additiv geprüft — deployen, sobald auf `main` nicht mehr gearbeitet wird; Repo liegt in `iilgmbh`.
11. Rollende Melder legen an statt zu aktualisieren, ~38 Kandidaten: https://github.com/achimdehnert/platform/issues/2140
12. shared-ci-Bänder: App-Repos v1.1.10 ×17 / v1.0.11 ×2, `ttz-lif`+`meiki-lra` ungemessen: https://github.com/achimdehnert/platform/issues/2087
13. ADR-Zweitmeinungen ohne Rückkanal, 19 von 24 ohne Antwort: https://github.com/achimdehnert/platform/issues/2088
14. `hygiene_melder.py` meldet invertiert (Footer mitgehasht), drei Phasen dieselbe Wurzel: https://github.com/achimdehnert/platform/issues/2054
15. Public→Private Welle 1: Owner-Freigabe fehlt, F entsperrt ADR-255: https://github.com/achimdehnert/platform/issues/2119
16. 14 Draft-PRs LLM-Readiness + zwei KONZ-Entwürfe mit Owner-Fragen: https://github.com/achimdehnert/platform/pull/2110
17. ADR-242 Wave 3: Phase-2-Rest, Apply-Artefakt fehlt: https://github.com/achimdehnert/platform/issues/811
18. CI-Runner `ci-gpu` auf eigenen Server (braucht keine GPU), Kosten = Owner-Wort: https://github.com/achimdehnert/platform/issues/2543
19. GX10: Mehrbenutzer-Durchsatz ungemessen, beide gemessenen Motoren sind Einzelstrom: https://github.com/achimdehnert/platform/issues/2544
20. GX10 als zweites Trainingsgerät, K4 Vergleichslauf 4090 ↔ GX10: https://github.com/achimdehnert/robo-lab/issues/58
21. Mail-Ansicht: leerer Körper braucht „Inhalt im Anhang": https://github.com/achimdehnert/platform/issues/2597
22. Owner: die 20 mechanisch gesetzten `frist_grund`-Texte auf `todo.iil.pet` sichten (Spalte Frist) — mechanisch je Bucket gesetzt, nicht redigiert.
23. Megatest-Erstlauf, 15 Befunde unbearbeitet und ohne Tracking-Issue ([Lauf 30619024656](https://github.com/achimdehnert/platform/actions/runs/30619024656), 2026-08-02) — vor Wiederaufnahme neu messen.
24. Gegenprobe Wochenlauf `ttz-hub`: beim nächsten Lauf, der ttz-hub wirklich ändert, müssen Checks am erzeugten PR erscheinen (kein Issue).
25. Session-Skills modellfest (#2690): Drill-Vorlage #2719, Backfill Positivkontrolle #2703, Ruleset-Entscheid bis 2026-10-02: https://github.com/achimdehnert/platform/issues/2690
26. #2750 K4/K5-Bilanz, sobald das Ledger 5 Fable-Sessions nach 2026-09-03 trägt (Stand 2); K5-Basisdefinition = Owner-Wort: https://github.com/achimdehnert/platform/issues/2750
27. Orchestrator-MCP-Schlüssel rotiert 2026-09-03: andere Maschinen prüfen, toter Block in settings.json: https://github.com/achimdehnert/platform/issues/2769
28. Future-Readiness: v2.4 aus 36 Regelkandidaten + Portfolio-Auswertung der 56 Phase-C-Berichte (dev-hub#321): https://github.com/achimdehnert/platform/issues/2737
29. Evidenz-Generator-Rest (Rate-Limit-Vorabcheck, visibility-Check); Werkzeuge #2767 gemergt, #2782 offen: https://github.com/achimdehnert/platform/issues/2736
30. shared-ci Band-Tag v1.1.15 nach Pinning-Merge; Dependabot-Bumps nicht auf v1.1.14 mergen (Owner, Prod-Gate): https://github.com/iilgmbh/shared-ci/issues/73
31. travel-beat: beide self-hosted Runner offline, Pinning-PR #94 hängt: https://github.com/achimdehnert/travel-beat/issues/95
32. ADR-262 Frontmatter nach Welle 1 (7 Repos umgesetzt, Status not-started): https://github.com/achimdehnert/platform/issues/2770
33. session_ende_checks.sh E.3/E.5 blind für platform (Pfad statt Repo-Name): https://github.com/achimdehnert/platform/issues/2773
34. Hop-Zugang (ssh_via) dreifach in drei Melder-Werkzeugen, gemeinsamer Helfer: https://github.com/achimdehnert/platform/issues/2783
35. pr_merge_sa.py zählt veraltete Läufe gleichnamiger Checks als rot: https://github.com/achimdehnert/platform/issues/2784
36. Zug A SECURITY.md + THIRD_PARTY_NOTICES.md: 9 PRs gestaffelt mergen, 4 ausgelassen, 36 Repos ohne Prod-Deploy warten auf Owner-Wort: https://github.com/achimdehnert/platform/issues/2787
37. writing-hub Doku-Filter fällt offen (kein gh auf ci-nonprod), jeder Doku-Merge deployt: https://github.com/achimdehnert/writing-hub/issues/1008
38. Sitzung 6e320e79 (Mailcheck/DSGVO/EPIC): `load_credentials` beendet den Prozess statt zu werfen — Wurzel hinter #2755; Ledger #185–#188 offen, Papiere `~/shared/retentionsscanner/`: https://github.com/achimdehnert/platform/issues/2752

## Konventionen dieser Datei

**Rotation:** aktueller Stand + höchstens ein vorheriger; jede andere H2-Sektion nur,
solange sie handlungsleitend ist. Verlauf wandert als Ganzes ins Archiv (anhängen,
Datumsmarke, Herkunftszeile), Offenes vorher nach „## Offene Fäden" retten. In der
Praxis trägt der Deckel meist nur **einen** Stand-Block: wer einen neuen schreibt,
lagert den alten im selben Zug aus.

**Byte-Deckel 20.000** — `python3 scripts/checks/handover_byte_cap.py`, als Gate im
Workflow `handover-append-only` an jedem PR. Reißt er, wird ausgelagert, nicht der
Deckel angehoben. Anlass: am 2026-09-02 war die Datei 116.116 B, davon 85 % nie
ausgelagerte Historie ([#2606](https://github.com/achimdehnert/platform/issues/2606)).

### Zeitanker — Pflicht je Stand-Block

Jeder `## ⚡ Aktueller Stand`-Block trägt **als erste Zeile** einen Zeitanker: die
Werte, gegen die eine frische Instanz in **einem** Kommando prüfen kann, ob dieser
Text noch den Stand beschreibt oder hinterherhinkt.

```
**Zeitanker:** HEAD `<sha7>` · `rev-list --count` <n> · geschrieben <YYYY-MM-DD>
```

Prüfen (ein Kommando, read-only):

```bash
git fetch -q origin && echo "ist: $(git rev-parse --short origin/main) / $(git rev-list --count origin/main)"
```

**Weicht der Ist-Wert ab, ist der Block veraltet — nicht falsch, aber überholt.** Das ist
die einzige Aussage, die der Anker trägt; er ersetzt kein Lesen. Fehlt ein Wert, wird
`nicht erhoben` eingetragen — **nie** ein geschätzter.

Warum: Ohne Anker war „hinkt der Handover nach?" nur durch Lesen beantwortbar, und das
unterblieb — Realfall 2026-07-15, drei konkurrierende Handover-PRs nebeneinander
(`session-retro-2026-07-15-platform-c494a2`). Übernommen aus dem Fremdsystem SB-Neu, wo
derselbe Anker eine Sechs-Commit-Drift in einer Sekunde sichtbar machte.

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
**Reusable Workflows:** SSoT ist `iilgmbh/shared-ci/.github/workflows/` (auf Tags gepinnt).
platform hält nur noch `_ci-pypi.yml` selbst (19 Consumer, ADR-226); `_ci-python.yml`/`_ci-odoo.yml`
sind retired (#1423).

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
