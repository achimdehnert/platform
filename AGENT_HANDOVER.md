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

## ⚡ Aktueller Stand (2026-09-03 abends — Mailcheck, DSGVO-Löschungen Mandant A, AVV Dienstleister W, EPIC-Preisanalyse)

**Zeitanker:** HEAD `072f6e7a` · `rev-list --count` 4090 · geschrieben 2026-09-03

**Zielzustand (Owner-Wort 2026-09-03 „mache mailcheck und todolist", danach 14 Folgeaufträge im Chat): erreicht** — Mailcheck gelaufen (Ledger 58 → 68 Vorgänge, 10 neu #179–188, 2 geschlossen), drei PRs gemergt ([#2749](https://github.com/achimdehnert/platform/pull/2749) Datumsmarke im Verlauf · [#2755](https://github.com/achimdehnert/platform/pull/2755) `SystemExit` aus `load_credentials` · [#2777](https://github.com/achimdehnert/platform/pull/2777) Vorgangs-Schlagworte per IMAP), zwei DSGVO-Löschvorgänge in risk-hub prod nachgetragen, AVV IIL↔Webbetreuer gesendet, sechs Papiere zum Retentionsflächenscanner in `~/shared/retentionsscanner/` (Einschätzung, Preisszenarien, Verhandlungsstrategie — je DE+EN) vor dem EPIC-Termin 18:00. Jedes Kriterium einzeln verifiziert (Outline-Lessons ×3, pgvector `session:platform:20260903:6e320e79-mailcheck-epic`).

**Offen, Owner-Zug:** [#2752](https://github.com/achimdehnert/platform/issues/2752) `load_credentials` beendet den Prozess statt zu werfen (Wurzel; #2755 ist das Pflaster) · [risk-hub#718](https://github.com/iilgmbh/risk-hub/issues/718) `create_deletion_request` setzt keinen Tenant-Kontext, auf Prod unbenutzbar · Ledger-Vorgänge #185 (drei TOM-Korrekturen → externe DSB Mandant B, Frist 10.09.), #186 (C5-Kurzbestätigung des Hosters von Mandant B), #187 (Pentest Mandant C: Weg mit IT-Leiter Mandant B klären, 05.09.), #188 (EPIC: **BIPA-Rechte am Prototyp klären** — entscheidet Kauf vs. Entwicklungsvertrag; SCALGO-Anfrage liegt in IIL-Entwürfe).

**Befunde:** (1) **risk-hub Deploy seit 11:54 rot, vier Läufe in Folge** — `Secret Detection (gitleaks)` findet 2 Leaks auf `main` (01ccdd5) — **beide in `.gitleaksignore` Zeile 2, Regel `generic-api-key`**: die Suppressions-Datei triggert selbst die Regel, kein neuer Wert im Code; Prod läuft weiter auf 800b4e4 vom 02.09.; Run [33801027904](https://github.com/iilgmbh/risk-hub/actions/runs/33801027904) — **nicht meine Commits**, drei Parallel-Leases auf risk-hub heute. (2) Runner-Pfadbug: `session_ende_checks.sh` verdoppelt absolute `TARGET_REPO`-Pfade → E.3 blind (SKIP), **E.5 falsches PASS** trotz drei eigener PRs ([#2789](https://github.com/achimdehnert/platform/issues/2789)). (3) RLS: `Mandate.objects.count()` ohne `set_db_tenant` gab 0 bei bestehendem Mandat — Lesen lügt leise, Schreiben scheitert laut (Outline-Lesson). (4) Push-Gate #2740 zweimal falsch diagnostiziert („kaputt", „flaky"), Ursache war der Worktree-Stand vor #2738 — Lesson „grün hier, rot dort = Standsverdacht". (5) AVV-PDF mit 7 Formatfehlern ging raus, weil Inhaltsprüfung das Layout nicht sieht — Lesson. (6) Mandant-B-Mail 13.08. (Index 28915) seit Ingest verschoben, in keinem naheliegenden Ordner auffindbar.

**Nächster Schritt:** Owner meldet Ergebnis des EPIC-Termins (sechs Fragen in `Price-Scenarios-EPIC` §8) → #188 fortschreiben; Rückruf IT-Leiter Mandant B → #185/#186/#187 fortschreiben; risk-hub gitleaks triagieren (`.gitleaksignore` hat 2 Suppressions, der Fund ist neu) — Owner-Zug, weil Deploy = Prod. Dann #2789 fixen (`basename "$1"`), damit E.3/E.5 wieder messen.

**SA-4:** 0 Anwendungen · 0 Einzel-OK · 0 Fehlanwendungen. Alle drei Merges heute durch den Owner (Chat-Go nach Review). Delegation: keine Subagenten. Session `6e320e79-9465-4a48-8fd4-c3043aa1d6b2`.

**0e Clear-Härte:** (1) Owner-Entscheide im Ledger je Vorgang mit Wortlaut · (2) Scratchpad enthält nur Wegwerf-Extrakte, alle Deliverables unter `~/shared/<mandant>/` und `~/shared/retentionsscanner/` · (3) Ledger verweist auf keinen `/tmp`-Pfad (grep leer, Positivkontrolle: Vorgänge nennen `~/shared`-Pfade). **0h:** übersprungen — Footprint lean (1 Repo, 3 PRs, kein Prod-Merge durch mich; die risk-hub-Prod-Schreibvorgänge waren Datenpflege, kein Deploy).

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
