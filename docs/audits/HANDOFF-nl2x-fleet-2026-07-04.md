# HANDOFF: NL2X-Fleet-Optimierung — Übergabe an Folge-Session

> **Zweck:** Eine zukünftige Session (beliebig leistungsfähiges LLM, frischer Kontext)
> kann mit diesem Dokument + dem Audit-Report sofort aufsetzen und weiterarbeiten,
> ohne den ursprünglichen Chat-Verlauf zu kennen.
> **Ground Truth:** `AUDIT-nl2x-fleet-2026-07-04.md` (gleicher Ordner) — alle Befunde
> dort mit `datei:zeile` belegt. Dieses Dokument enthält nur Arbeitsanweisungen.
> **Stand:** 2026-07-04. Je älter dieses Dokument, desto wichtiger Abschnitt 0.3 (Re-Grounding).

> **Live-Status: achimdehnert/platform#913** — der Gate-/WP-Stand in DIESEM Dokument ist eingefroren (Stand 2026-07-04 ~13:00 UTC) und wird nicht nachgeführt; §2/§3-Status sind historisch. Methode (§0 Re-Grounding) bleibt gültig.

---

## 0. Sofort-Start (erste 15 Minuten, Reihenfolge einhalten)

1. **Audit-Report lesen**: `platform/docs/audits/AUDIT-nl2x-fleet-2026-07-04.md` — Executive Summary + Roadmap (§1, §8) genügen für den Einstieg; Detail-Befunde (§3–5) erst bei Bearbeitung des jeweiligen Arbeitspakets.
2. **Policies laden** (bindend, nicht optional): `~/.claude/policies/{evidence-discipline,autonomy-gates,llm-routing,adr-threshold,platform-agents,claude-skills}.md`. Kernregeln kompakt in Abschnitt 6.
3. **Re-Grounding (PFLICHT vor jedem Edit)** — der Fleet-Stand kann sich seit 2026-07-04 geändert haben. Billigste Checks:
   ```bash
   # Ist der odoo-Legacy-Fallback noch da? (Befund P1-🔴 #2)
   rg -n 'allow_write|def _execute_sql' ~/github/odoo-hub/addons/mfg_nl2sql/controllers/nl2sql_controller.py
   # Callt ttz-hub noch OpenAI? (Befund P1-🔴 #1)
   rg -n 'gpt-4o-mini|litellm' ~/github/ttz-hub/services/aifw_service/aifw_service/views.py
   # Golden-Suite noch CI-blind?
   rg -n 'NL2CAD_TESTDATA' ~/github/nl2cad/tests/test_realdata_golden.py
   # Pins noch driftend?
   rg -n 'nl2cad-core' ~/github/cad-hub/requirements.txt ~/github/risk-hub/pyproject.toml
   # aifw-Version (Kern):
   rg -n '^version' ~/github/aifw/pyproject.toml
   ```
   Ist ein Befund nicht mehr reproduzierbar → Arbeitspaket als erledigt/obsolet markieren, NICHT trotzdem umsetzen.
4. **Entscheidungs-Gates prüfen** (Abschnitt 2): Liegt vom User (Achim) inzwischen eine Entscheidung vor (Chat, Issue, ADR)? Ohne Entscheidung: Gate-Items NICHT selbst entscheiden, gate-freie Arbeitspakete (Abschnitt 3) zuerst.

## 1. Mission

Die drei NL→Struktur-Domänen der Flotte (**NL2SQL** in aifw/odoo-hub/ttz-hub, **CAD** in nl2cad/cad-hub/risk-hub/mcp-hub, **IoT** in nl2iot-hub) konsolidieren, absichern und mit Eval-Infrastruktur versehen. Zielbild (Audit §7):
- **Ein** NL2SQL-Kern (`aifw.nl2sql`), keine Forks.
- **Eine** Brandschutz/Ex-Zonen-Engine (`nl2cad-core`), ifc_mcp wrappt statt dupliziert.
- **Ein** Eval-Standard (Golden-Set-Format + Runner) als CI-Gate in allen drei Domänen.
- Prompts in promptfw (ADR-146), Routing policy-konform (Groq-first, ttz=Ollama).
- IoT: erst ab MVP-Start relevant; dann SIL-Gate als Code + Evals ab Tag 1.

## 2. Entscheidungs-Gates (nur User entscheidet — historischer Stand ~13:00 — Live: #913)

| Gate | Frage | Optionen | Blockiert |
|---|---|---|---|
| G1 | ttz-hub Sovereignty: OpenAI-Call ersetzen oder Ausnahme? | (a) Migration Ollama/Mistral-EU (b) schriftliche Ausnahme | WP4-Umfang; Prod-Deploy von WP4 |
| G2 | odoo-hub Prod-Fix-Freigabe (Prod-Addon!) | Fix-PR ja/nein; Fallback entfernen vs. absichern | WP1-Merge/Deploy |
| G3 | ADR „NL2X-Kern in aifw + Eval-Standard" gewollt? | ja → Draft schreiben; nein → Einzelmaßnahmen ohne ADR | WP7, WP8 |
| G4 | Audit+Handoff committen (platform, main oder PR)? | ✅ freigegeben 2026-07-04 („committe audit+handoff") | — |
| G5 🔴 | **nl2cad: echte Kundendaten als Test-Fixtures im Repo** — `tests/fixtures/minimal.ifc` (37 MB, Bendl-Modell inkl. Klarname/E-Mail/Telefon im IFC-Header), `minimal.dxf` vermutlich analog; git-getrackt seit langem | Bereinigung = History-Rewrite (irreversibel!) + Fixture-Ersatz durch synthetische Modelle (Basis existiert seit WP2) | Entscheidung + Zeitpunkt (History-Rewrite invalidiert Clones) |
| G6 | nl2cad: Repo-Secret `NL2CAD_TESTDATA_URL` setzen, damit der gated Realdata-Golden-Job echt läuft | Secret anlegen (tar.gz-Korpus, private Ablage) + einen CI-Lauf prüfen | Realdata-Eval in CI |

**Autonomie-Regel:** Branch → Edits → PR → CI-Fix ist gate-frei; Merge in Prod-Pfade (odoo-hub, ttz-hub prod), Publish (PyPI), Deploy = Freigabe nötig (autonomy-gates.md).

## 3. Arbeitspakete — ready-to-execute (je 1 Branch + 1 PR, Reihenfolge = Priorität)

### WP1 🔴 odoo-hub: Legacy-NL2SQL-Fallback entschärfen  [braucht G2 für Merge; PR bauen ist gate-frei]
- **Ist:** `addons/mfg_nl2sql/controllers/nl2sql_controller.py:354-370` — `_execute_sql` auf `request.env.cr` (RW), nur Regex-Schutz; `allow_write`-Param `:231-232`. Duplikat in `addons_v19/mfg_nl2sql` (788 LOC, abweichend).
- **Soll (Minimalfix):** `allow_write` entfernen; `_execute_sql` vor Ausführung `SET TRANSACTION READ ONLY` + `statement_timeout` setzen (Muster: `aifw/src/aifw/nl2sql/engine.py:377-388`); ODER Fallback komplett entfernen und hart auf aifw_service verweisen (bevorzugt, wenn Prod die URL gesetzt hat → Hypothese H-odoo zuerst prüfen, §4).
- **Beide Addon-Versionen** (v18+v19) fixen oder v18 deprecaten — nicht nur eine.
- **Akzeptanz:** Kein Codepfad exekutiert LLM-SQL ohne RO-Transaktion; Regression-Test `test_should_reject_write_sql_in_fallback`; CI grün.

### WP2 🟠 nl2cad: Golden-Suite in CI aktivieren — ✅ ERLEDIGT (PR nl2cad#38, gemergt 2026-07-04; synthetisches Golden-Set läuft immer, Realdata-Job gated auf Secret `NL2CAD_TESTDATA_URL` → Gate G6)
- **Ist:** `tests/test_realdata_golden.py:24-28` skipt ohne `NL2CAD_TESTDATA`; CI überspringt.
- **Soll:** Testdaten als CI-Artefakt/LFS/Release-Asset bereitstellen, Workflow-Step setzt `NL2CAD_TESTDATA`, Suite wird Pflicht-Gate. Falls Testdaten Kundenmodelle sind (prüfen!): anonymisiertes Subset erzeugen — nicht einfach hochladen (Sovereignty).
- **Akzeptanz:** CI-Lauf zeigt Golden-Tests als executed (nicht skipped); Gate rot bei Sollwert-Abweichung.

### WP3 🟠 nl2cad: Parser-Härtung — ✅ ERLEDIGT (PR nl2cad#39, gemergt 2026-07-04; defusedxml, max_bytes in allen parse_bytes-Pfaden, Geom-Fallback-Zeitbudget statt hartem Timeout — Begründung im PR)
- **Ist:** `bcf_parser.py:18,87,96,112` stdlib-ET auf fremden bcfzip-Inhalten; kein Parse-Timeout (grep `signal.alarm|setrlimit` = 0); Byte-Loader ohne Größenlimit (`loaders.py:34-56`).
- **Soll:** `defusedxml` als Dependency (BCF-Pfad); konfigurierbares `max_bytes` in `parse_bytes`-Loadern (Default z.B. 500 MB, wie cad-hub); Timeout um `ifcopenshell.geom`-Fallback (subprocess/Signal).
- **Akzeptanz:** Tests: oversized Upload → ValueError; Entity-Blowup-XML → sauberer Fehler; bestehende 31 Testdateien grün.

### WP4 🟠 ttz-hub: Fork eliminieren + Routing policy-konform  [G1 für Modellwahl]
- **Ist:** `services/aifw_service/aifw_service/views.py` — Custom-NL2SQL, `import aifw` fehlt, Begründungs-Kommentar `:8-11` seit aifw≥0.7 überholt; OpenAI-Direktcall; tote Dep `requirements.txt:4`.
- **Soll:** Migration auf `aifw.nl2sql.NL2SQLEngine` (Vorbild: `odoo-hub/services/aifw_service/`); ttz-Stärken dabei **in aifw übernehmen, nicht verlieren**: dedizierte RO-DB-Rolle (`docker/db/init.sql:14-17`), `evaluate.py`+`nl2sql_examples.json` (Keimzelle für WP7), 50 Tests portieren. Modell gemäß G1.
- **Akzeptanz:** kein Custom-LLM/SQL-Code mehr in views.py; `iil-aifw`-Pin korrekt; Tests portiert und grün; kein OpenAI-Call (bzw. dokumentierte Ausnahme).

### WP5 🟡 Pins & Aufräumen — TEILWEISE ERLEDIGT (2026-07-04: risk-hub#377 ✅ gemergt, ttz-hub#24 ✅ gemergt, cad-hub#31 🟡 grün aber Merge=Prod-Deploy nl2cad.de → wartet auf manuellen Merge durch Achim)
- cad-hub: `requirements.txt:12` → `nl2cad-core[ifc]>=0.4.0,<1.0`; toten `apps/ifc/parser/parser.py` (`IfcCompleteParser`) entfernen (vorher Hypothese H-cadhub-dead prüfen, §4).
- risk-hub: `pyproject.toml:54` git-Dep auf Tag `nl2cad-core@0.4.0` (oder PyPI wie cad-hub — konsistent machen).
- ttz-hub: tote `aifw>=0.5.0`-Dep raus (Teil von WP4 möglich).
- ~~bfagent: CAD-Doku-/Skript-Reste archivieren~~ **OBSOLET** (2026-07-04): bfagent ist auf GitHub archiviert (read-only, seit 2026-06-03) — Entscheidung Achim: nicht entarchivieren. Fertiger Commit liegt auf lokalem Branch `chore/archive-cad-leftovers-adr-029` (530d6a5) für den Fall späterer Reaktivierung.
- **Akzeptanz:** Builds reproduzierbar; keine Referenz auf Entferntes; CI grün.

### WP6 🟡 aifw: Seed + Prompt-Governance — ✅ ERLEDIGT (PR aifw#31, gemergt 2026-07-04; Groq-first Seed, retired Modell-IDs ersetzt, promptfw-Auflösung mit Builtin-Fallback; kein Release — Version bleibt 0.11.5)
- **Ist:** `management/commands/init_aifw_config.py:33-81` ohne Groq/Cerebras, teils veraltete Modell-IDs; `SYSTEM_PROMPT_TEMPLATE` hardcoded (`engine.py:52-116`) ≠ ADR-146.
- **Soll:** Groq `llama-3.3-70b-versatile` + Cerebras als Tier-1a-Default für `nl2sql`-ActionType; IDs gegen `mcp-hub/docs/known-dead-models.txt` bereinigen; Prompt als promptfw-`PromptStack` (iil-promptfw≥0.8, Extra `[promptfw]` existiert schon).
- **Akzeptanz:** frisches Seed erzeugt policy-konformes Routing; Prompt editierbar via promptfw; bestehende Tests grün.

### WP7 🟠 Eval-Standard: NL2SQL-Accuracy als CI-Gate  [G3 beeinflusst Ort/Form]
- **Keimzelle:** `ttz-hub/services/aifw_service/evaluate.py` + `nl2sql_examples.json` (16 Beispiele) → generalisieren nach aifw als `aifw.nl2sql.eval` (Golden-Set-Format: NL-Input, Ground-Truth-SQL bzw. Ground-Truth-Resultset, Toleranz).
- **Akzeptanz:** `make eval-nl2sql` liefert Accuracy-%; CI-Gate mit Schwellwert; Golden-Set versioniert im Repo; Modellwechsel erzeugt sichtbaren Accuracy-Diff.

### WP8 🟠 mcp-hub: ifc_mcp auf nl2cad-core umstellen  [größtes WP; nach G3]
- **Ist:** `ifc_mcp/src/ifc_mcp/infrastructure/ifc/parser.py:14-18` eigenes ifcopenshell; `presentation/tools/{ex_protection_tools,fire_plan_tools}.py` duplizieren `nl2cad.core.analyzers`. ~1 Testdatei.
- **Soll:** infrastructure-Schicht wrappt `nl2cad.core` (Parser + Analyzer); MCP-Tool-Signaturen stabil halten; Tests ergänzen (Vergleichstests Eigenbau-Output vs. nl2cad-Output VOR Umbau = Regressions-Netz).
- **Vorher prüfen:** Hypothese H-ifcmcp (ist es überhaupt deployt/genutzt? §4). Wenn ungenutzt → Archivierung statt Umbau (billiger).

## 4. Hypothesen zuerst verifizieren (aus Audit §9 — je <10 min)

| ID | Hypothese | Billigster Check |
|---|---|---|
| H-odoo | Prod hat `aifw_service_url` gesetzt (sonst ist unsicherer Pfad aktiv) | Odoo-Konfigparameter in Prod lesen (read-only, gate-frei) |
| H-ttz | OpenAI-Call verletzt Kundenvertrag | `ttz-hub/docs/Angebot_KI_Werkleiterassistent_Phase1_IIL.md` + Vertrag lesen |
| H-pypi | PyPI-Versionen nl2cad-Pakete = Repo-Tags | `pip index versions nl2cad-core` |
| H-ifcmcp | ifc_mcp ist produktiv deployt | `rg ifc ~/github/platform/infra/ports.yaml` + `gh run list -R achimdehnert/mcp-hub` |
| H-cadhub-dead | `IfcCompleteParser` wirklich unreferenziert | `rg -w IfcCompleteParser ~/github/cad-hub --glob '!apps/ifc/parser/*'` |

## 5. Erweiterter Optimierungs-Backlog (Stufe 2 — nach WP1–WP8)

**Eval & Quality-Engineering** (größter Hebel):
- **Nightly-Eval mit Trend-Tracking**: Accuracy je Domäne/Modell über Zeit (Drift-Erkennung bei Provider-Modellwechseln); Telemetrie-Anschluss an ADR-116/196-Router (Outcome-Feedback existiert dort schon).
- **Query-Log-Mining**: echte NL-Anfragen aus Prod (odoo-Cockpit, ttz) privacy-gefiltert als Golden-Set-Kandidaten — das Set wächst mit realer Nutzung statt handkuratiert zu veralten.
- **Shadow-Mode**: neues/billigeres Modell parallel gegen Prod-Anfragen laufen lassen (nur Logging, keine Antwort) → Kosten/Quality-Pareto je ActionType datenbasiert; erst dann Tier-Downgrade (Groq-first mit Beleg statt Hoffnung).
- **Clarification-Rate als Metrik**: aifw hat `clarification.py` — messen, wie oft nachgefragt wird; hohe Rate = Schema-Semantik-Lücke (Semantic-Bridge-Ausbau).

**Sicherheit Stufe 2:**
- **Eine geteilte SQL-Policy-Komponente**: die drei divergierenden Regex-Blocklisten (aifw/odoo/ttz) durch ein importiertes Modul ersetzen — Blocklist-Fixes wirken dann fleet-weit.
- **Mandanten-/Row-Scoping für NL2SQL**: heute nur Tabellen-Allowlists; generierte Queries automatisch mit Tenant-Filter wrappen (Views oder RLS).
- **NL2X-Audit-Log**: wer stellte welche NL-Frage, welches SQL/Artefakt wurde erzeugt+ausgeführt — Compliance-Anforderung sobald ttz/meiki (Government/LRA) NL2SQL produktiv nutzen.
- **Rate-Limits + Kosten-Caps** auf NL2X-Endpoints (LLM-Kosten-DoS).

**Architektur Stufe 2:**
- **NL2X-Interface in aifw**: `translate → validate → gate → execute → feedback` als abstrakte Pipeline mit Domain-Adaptern (SQL heute, DXF-Generator als zweiter Adapter, IoT/ST-Code als dritter ab MVP). Erst NACH WP7 (Eval zuerst — sonst refactort man ohne Regressions-Netz). Das ist der Kern von G3/ADR.
- **ADR-085-Anschluss**: NL→TaskGraph-Pipeline (UseCasePipeline) mit NL2X verheiraten — komplexe NL-Aufträge („analysiere Halle 3 und erzeuge Ex-Zonen-Plan") dekomponieren in NL2X-Einzelschritte.
- **Data-Sovereignty für NL2X-Datenquellen regeln** (Governance-Lücke §6.4): Darf Schema-Kontext/CAD-Kundengeometrie an externe Provider? Als Abschnitt im G3-ADR oder eigene Policy — betrifft ttz/meiki unmittelbar.

**IoT (erst ab MVP-Start):**
- SIL-Gate aus `nl2iot-hub/docs/adr/ADR-001:80-86` als **Code** (nicht Doku) bauen — als dritter NL2X-Adapter; Evals + Static-Analysis-Gate ab erstem Commit; Platform-ADR dann Pflicht (heute governance-los).
- Dangling `policies/llm-routing.md`-Referenz in nl2iot-ADR auf Org-Policy-Pfad korrigieren (1-Zeilen-Fix, kann in WP5).

## 6. Constraints kompakt (Vollform in den Policy-Dateien)

- **Evidenz vor Behauptung**: prüfbare Aussage erst prüfen, dann schreiben; „gebaut + lokal grün" ≠ „funktioniert in Prod" — Werkzeug einmal echt im Zielkontext laufen lassen, bevor „validiert".
- **Tests**: `make test`, nie rohes pytest; vorher `config/settings/test.py` + Makefile lesen.
- **Nach `git switch`**: `git branch --show-current` vor jedem Edit.
- **Commits**: `[feat|fix|refactor|docs|test|chore](scope): description`; Tests `test_should_*`.
- **Scope-Checkpoint**: drittes Repo ODER Prod/Publish erreicht → innehalten, User-Freigabe. Generisches „mach autonom" ist KEINE Prod/Publish-Freigabe.
- **LLM-Routing**: Groq/Cerebras free-tier first; ttz-hub/meiki-hub nur lokales Ollama; keine hardcoded Modell-IDs (ADR-084), kein `-latest` (ADR-208); Prompts nach promptfw (ADR-146).
- **Action Board** als Antwortformat ab ≥3 Items (Buckets 🟢/🔵/🟡⛔/✅, stabile IDs).

## 7. Statusführung

- Fortschritt in DIESEM Dokument nachtragen: WP-Status (☐ → 🟡 → ✅ + PR-Link) direkt an den WP-Überschriften, Gates in §2 mit Entscheidung + Datum.
- Bei substanzieller Arbeit: GitHub-Issue als Tracking-Anker (Policy claude-skills §Review-Gate 6) — ein Sammel-Issue „NL2X-Fleet-Konsolidierung" mit WP-Checkliste genügt.
- Session-Ende: `/session-ende` (Wissen sichern, committen nach Freigabe G4).

---
*Erstellt 2026-07-04 aus dem 4-Agenten-Audit (siehe AUDIT-nl2x-fleet-2026-07-04.md §Abdeckung). Nicht committet — Gate G4.*
