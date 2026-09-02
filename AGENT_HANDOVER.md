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

## ⚡ Aktueller Stand (2026-09-02 mittags — Lotsen-Wachstum: Regelkreis gebaut, Retro fand zwei Loecher darin, beide geschlossen)

**Zeitanker:** HEAD `d381e63a` · `rev-list --count` 3920 · geschrieben 2026-09-02

**Zielzustand ([#2618](https://github.com/achimdehnert/platform/issues/2618), Owner-Go „8 go" auf den vorgelegten Zielzustand, danach „5 6 7 go", „11 go 12 merge", „24 go 25 go", „27 go"): drei der vier Kriterien erreicht, das vierte verschoben mit Tracking.** (1) Sensor nominiert aus Retro-Evidenz — `retro_kpis.py --nominierung`, Klasse ≥2 ⇒ NOMINIERT, `over_act` derselben Klasse sperrt: **erreicht**, laeuft ueber 110 Retros. (2) Befoerderungen einzeln im Registry-Format vorlegen: **erreicht** (Verfahren steht, noch kein Anlass). (3) Modellwechsel loest Re-Qualifikation je Vollmacht aus statt Total-Reset: **Regel ratifiziert (Runbook §3a), Traegerfeld `assessed_with` in der Registry fehlt** — verschoben, getrackt in #2618. (4) Rueckbau bleibt symmetrisch (Art. 8.2): **erreicht**, unveraendert.

**Gemergt (vier PRs):** [#2617](https://github.com/achimdehnert/platform/pull/2617) Sensor `--nominierung` + Einstufung MAJOR/MINOR/SUFFIX + Runbook §0/§3a + Detektor-Log · [#2653](https://github.com/achimdehnert/platform/pull/2653) Retro-Report c36878 · [#2659](https://github.com/achimdehnert/platform/pull/2659) `docs/governance/` und die Charta review-pflichtig · [#2661](https://github.com/achimdehnert/platform/pull/2661) Datums-Snapshot als eigene Einstufungs-Dimension. Geschlossen: [#2654](https://github.com/achimdehnert/platform/issues/2654), [#2655](https://github.com/achimdehnert/platform/issues/2655).

**Die Retro fand zwei echte Loecher im gerade Gebauten — beide geschlossen.** (a) `docs/governance/` fiel durch CODEOWNERS **und** `sa_m.governance_pfade`; das `main`-Ruleset traegt `required_approving_review_count: 0`, ohne CODEOWNERS-Treffer verlangt GitHub gar kein Approval. Ein PR mit nur dem Runbook waere ungeprueft gemergt — dort steht §3a ueber die Vollmachten. #2617 bekam sein Review nur, weil zufaellig eine `.windsurf/`-Datei mitgebuendelt war: **der Bundling-Verstoss machte ihn sicherer als die Regel es getan haette.** (b) `fam_major()` schnitt nach der ersten Ziffernfolge ab, `haiku-4-5-<datum>` → `haiku-4-9-<datum>` galt als MINOR — Vollmachten waeren aktiv geblieben. Beide Fixes mit Rot-Beweis gegen die alte Fassung, Gegenproben unveraendert, Live-Kopien verteilt (Doctor Drift 0).

**Erster echter Beweislauf des Modellwechsel-Detektors:** `~/.claude/hooks/state/model-changes.log` traegt seit `2026-09-02T08:48:20Z` seine erste Zeile (`claude-fable-5-1[1m] → opus = MAJOR`). Das Gate hatte seit dem Bau am 2026-08-02 nie gefeuert. **Einschraenkung:** `gate_wirkung.py` fuehrt es weiterhin als `unerprobt`, weil es Retro-Slugs zaehlt, keine Log-Zeilen — realer Beleg und Werkzeugsicht gehen auseinander.

**Eigene Fehler, im Lauf gefangen:** (1) „13/13 gruen" statt 14 Checks — der Stop-Hook blockte und erzwang den Beleglauf (**Gate hat gefangen**). (2) Dem Owner die Chronologie des Review-Bots falsch berichtet; die Run-Historie zeigt Dispatches vor **und** nach dem Merge — dieselbe Klasse, diesmal ohne Zahl-Marker, deshalb ungefangen. (3) Im Retro-Report `claim-before-cheapest-check` als „wirksam" etikettiert, waehrend der reproduzierte Lauf RUECKFAELLIG zeigt — vom Meta-Reviewer gefunden, §5a ersetzt. (4) Erster Branch-Versuch per `git switch -c` im geteilten Haupt-Tree, vom Guard geblockt.

**Rueckfaelliges Gate behandelt (Phase 0f):** `claim-before-cheapest-check` steht bei 69 vor / 3 nach dem Bau, der dritte Rueckfall stammt aus dieser Sitzung. Gewaehlte Antwort **ausweiten** (umbauen scheidet aus — der Hook feuert am richtigen Punkt; herabstufen scheidet aus — er hat im selben Lauf gefangen), Umsetzung getrackt in [#2666](https://github.com/achimdehnert/platform/issues/2666). Die drei uebrigen rueckfaelligen Gates stammen aus fremden Sitzungen und bleiben bewusst unberuehrt.

**SA-4: 1 Anwendung (Zielzustand #2618 vorab vorgelegt und angenommen) · 0 Einzel-OK trotz Klassen-Deckung · 0 Fehlanwendungen.** Prod-Schritt: keiner. Live-Eingriff: zweimal `cc-skill-dist --allow-live` nach Owner-Go, beide mit Backup, Doctor Drift 0 / Dangling 0.

**Autonomie-Kalibrierung:** `over_ask` 0 · `over_act` 0, beide Klassenlisten leer. Erste Retro mit den neuen Feldern `over_ask_klassen`/`over_act_klassen` — der Sensor bekommt aus dieser Sitzung kein Futter, und das ist ein ehrliches Ergebnis, kein Versaeumnis.

**Offen (Owner):** [#2662](https://github.com/achimdehnert/platform/issues/2662) hartcodierter DB-Fallback mit Zugangsdaten im Quelltext, auf `main` rot, nur lokal sichtbar · [#2664](https://github.com/achimdehnert/platform/issues/2664) Kurzname gegen volle Modell-ID gilt als MAJOR und wuerde alle Vollmachten suspendieren (Design-Entscheidung, kein Mapping) · [#2666](https://github.com/achimdehnert/platform/issues/2666) Gate-Ausweitung · [#2618](https://github.com/achimdehnert/platform/issues/2618) Registry-Feld `assessed_with` und Rubber-Stamp-Messfeld.

**Fremd, liegen gelassen:** Commits in iil-pet-portal, illustration-hub, meiki-hub, writing-hub aus parallelen Sitzungen — nicht angefasst.

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
