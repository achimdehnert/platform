# AUDIT: NL2X-Fleet — NL-to-SQL, CAD, IoT (2026-07-04)

> Read-only Cross-Repo-Audit über `~/github/**`. Vier parallele Analyse-Läufe
> (NL2SQL, CAD, IoT, ADR/Governance), Evidenz-Disziplin nach
> `policies/evidence-discipline.md`. Jede Aussage mit `datei:zeile` bzw.
> Kommando belegt; Unverifiziertes explizit als HYPOTHESE markiert.
> Keine Änderungen an Repos vorgenommen — einzige Schreibaktion ist diese Datei.

## 1. Executive Summary

Die drei Domänen sind Instanzen desselben Musters — **NL → validiertes
strukturiertes Artefakt** — in drei sehr unterschiedlichen Reifegraden:

| Domäne | Reife | Kern | Zentraler Befund |
|---|---|---|---|
| **NL2SQL** | Produktiv | `aifw.nl2sql` (iil-aifw 0.11.5) | 3–4 parallele Implementierungen; odoo-Legacy-Fallback führt LLM-SQL auf **RW-Cursor** aus; ttz-hub callt **OpenAI** trotz Sovereignty-Kontext |
| **CAD** | Produktiv | `nl2cad-core` 0.4.0 (PyPI, 6 Pakete) | Kern gesund (DI, kein Modell-Hardcode); `ifc_mcp` in mcp-hub ist **zweite Brandschutz/Ex-Zonen-Engine**; Golden-Suite CI-blind; Pin-Drift bei Konsumenten |
| **IoT** | Spec/Klickdummy | `nl2iot-hub` (0 Code-Dateien) | Kein Betriebscode, kein MQTT fleet-weit; SIL-Sicherheitsarchitektur vorbildlich **dokumentiert, aber nicht implementiert**; governance-los auf Platform-Ebene |

**Größte domänenübergreifende Lücke:** Es existiert fleet-weit **keine
NL2X-Accuracy-Eval-Infrastruktur** — kein Golden-Set mit Ground-Truth als
CI-Gate, keine Accuracy-Metrik, kein Regressions-Gate (ADR-223 nur
`proposed`, `impl_status: none`).

**Schwerste Einzelbefunde (Prio):**
1. 🔴 odoo-hub: Legacy-NL2SQL-Fallback exekutiert LLM-generiertes SQL auf dem Odoo-**Read-Write**-Cursor, Schutz nur Regex, `allow_write`-Flag vorhanden (`addons/mfg_nl2sql/controllers/nl2sql_controller.py:354-370`, `:231-232`).
2. 🔴 ttz-hub: NL2SQL callt OpenAI `gpt-4o-mini` direkt (`services/aifw_service/aifw_service/views.py`, `docker-compose.prod.yml:65`) — Org-Policy `llm-routing.md` sieht für ttz-hub „nur lokales Ollama" vor. Kein Sovereignty-Doc im Repo → Klärung nötig.
3. 🟠 mcp-hub `ifc_mcp`: eigenständige IFC/Ex-Zonen/Brandschutz-Engine parallel zu `nl2cad-core` (~1 Testdatei) statt Wrapper.
4. 🟠 Eval-Lücke überall: aifw ohne Accuracy-Harness; nl2cad-Golden-Suite in CI übersprungen; nl2iot ohne Tests.

## 2. Inventar (verifiziert per rg, klassifiziert)

### NL2SQL
| Repo | Dateien | Klassifikation |
|---|---|---|
| aifw (iil-aifw 0.11.5) | 26 | **Kern** — `src/aifw/nl2sql/` (engine 674 LOC, clarification, semantic bridge, few-shot, feedback) |
| odoo-hub | 176 | **Konsument + Legacy-Fork** — `services/aifw_service/` importiert `aifw.nl2sql.engine`; `addons/mfg_nl2sql` + `addons_v19/mfg_nl2sql` halten kopierte Fallback-Pipeline |
| ttz-hub | 22 | **Eigenständiger Fork** — trotz Namens „aifw_service" kein `import aifw` |
| platform, mcp-hub, dev-hub, writing-hub, iil-pet-portal | 2–1 | nur Erwähnung |

### CAD
| Repo | Dateien | Klassifikation |
|---|---|---|
| nl2cad | 143 | **Kern** — Monorepo, 6 Pakete: `nl2cad-core` 0.4.0, `-areas`/`-brandschutz`/`-gaeb`/`-nlp` 0.2.1, Meta `iil-nl2cadfw` 0.2.1 |
| cad-hub | 87 | **Konsument + Prod** (nl2cad.de, Port 8094) — plus toter In-Repo-Duplikat-Parser |
| risk-hub | 49 | **Konsument (schwer)** — explosionsschutz/brandschutz, 103 Erwähnungen |
| mcp-hub | 50 | **Duplikat** — `ifc_mcp` eigenständiger Parser + Analyse-Engine; `_archive/cad_mcp` stillgelegt |
| bfagent | 26 | nur Erwähnung — ADR-029-Extraktion abgeschlossen, Doku-/Skript-Reste |
| platform | 64 | nur Erwähnung (ADRs, ports.yaml) |

### IoT
| Repo | Dateien | Klassifikation |
|---|---|---|
| nl2iot-hub | 22 (0 Code) | **Kern (nur Spec/Klickdummy)** — NL→SPS-Logik-Assistent, ADR-211-Klasse `spec-demo` |
| genesor / iil-pet-portal | 9 / 14 | Konsument (Renderer/Portal-Ingest, keine IoT-Logik) |
| ausschreibungs-hub, ttz-hub | 3 / 2 | nur Erwähnung (Roadmap/Beispiele) |

Falsifiziert: coach-hub (0 Treffer), molkerei-landing (base64-Blob-False-Positive).
Fleet-weit `\bmqtt\b` in Code: **0 echte Treffer** — es existiert kein IoT-Betriebscode.

## 3. Befunde NL2SQL

### aifw (Kern) — solide, mit Lücken
- ✅ Defense-in-Depth: Regex-Blocklist (`engine.py:71-89`) + `ALWAYS_BLOCKED`-Tabellen (`engine.py:36-42`) + erzwungenes `SET TRANSACTION READ ONLY` (`engine.py:377-383`) + `statement_timeout` (`engine.py:385-388`) + LIMIT-Injektion (`engine.py:407-411`).
- ⚠️ **Read-only-Bypass**: läuft die Verbindung bereits `in_atomic_block`, greift nur die Regex-Blocklist (`engine.py:353-360`, dokumentiert per `logger.warning`).
- ⚠️ **Kein Accuracy-Eval**: 39 NL2SQL-nahe Tests (readonly 3, semantic 23, privacy 13), aber kein Golden-Set mit Ground-Truth-SQL.
- ⚠️ **Prompt hardcoded** (`SYSTEM_PROMPT_TEMPLATE`, `engine.py:52-116`) statt promptfw — Spannung zu ADR-146 (promptfw = SSoT für Prompts).
- ⚠️ **Kein Groq im Seed** (`management/commands/init_aifw_config.py:33-81`: ollama, claude-3-5-sonnet, haiku, gpt-4o, gpt-4o-mini, gemini-1.5-pro) — Policy „Groq free-tier first" nicht abgebildet; geseedete Modell-IDs teils veraltet (Gegencheck via mcp-hub `docs/known-dead-models.txt` empfohlen).

### odoo-hub — sauberer Konsument mit gefährlichem Altlast-Fallback
- ✅ Bevorzugter Pfad importiert den Kern: `_call_aifw_service` (`controllers/nl2sql_controller.py:416-441`); Pin `iil-aifw>=0.11.4,<1` aktuell.
- 🔴 **Legacy-Fork-Fallback**: vollständige eigene Pipeline (`sanitize_sql` :32-77, `_call_anthropic`/`_call_openai` :~255-317, `_translate_nl_to_sql`, `_execute_sql`). `_execute_sql` nutzt `request.env.cr` (voller Odoo-DB-User, **kein** read-only) in `cr.savepoint()` ohne `SET TRANSACTION READ ONLY` (`:354-370`). `allow_write`-Parameter (`:231-232`) würde DML durchlassen.
- 🔴 HYPOTHESE H4: ob Prod die `aifw_service_url` gesetzt hat, ist ungeprüft — wenn nicht, ist der unsichere Pfad **aktiv**. Billigster Check: Prod-Odoo-Konfigparameter lesen.
- 🟠 **Vierfach-Kopie**: `addons/mfg_nl2sql` UND `addons_v19/mfg_nl2sql` (788 LOC, abweichend) halten je eine Fork-Pipeline.
- 🟠 Fork umgeht aifw-Routing: Direktcalls `api.anthropic.com` / `api.openai.com`, Default `claude-sonnet-4-5-20250929` (`:223-227`, `:260-261`, `:294-295`) — kein Kostenlog, kein Groq-first.
- 🟡 Golden-Suite (`tests/test_nl2sql_golden.py`, 19 Tests) prüft nur Schema-XML-Konsistenz, keine NL→SQL-Accuracy (`:5-10`).

### ttz-hub — stärkste DB-Absicherung, aber Fork + Sovereignty-Frage
- ✅ Beste DB-Sicherung im Fleet: dedizierte Rolle `nl2sql_user` nur mit `GRANT SELECT` (`docker/db/init.sql:14-17`), Connection `-c default_transaction_read_only=on -c statement_timeout=10000` (`settings.py:55-61`), Tabellen-Allowlist (11 Tabellen), Kommentar-Stripping.
- ✅ Bester Eval-Ansatz im Fleet: `evaluate.py` + `nl2sql_examples.json` (16 Beispiele) + Env-A/B (`NL2SQL_MODEL`, `NL2SQL_FEWSHOT_K`); 50 Testfunktionen.
- 🔴 **Sovereignty-Konflikt**: `_call_llm` → litellm → OpenAI `gpt-4o-mini` (`views.py`, Key in `docker-compose.prod.yml:65`). Org-Policy `~/.claude/policies/llm-routing.md`: ttz-hub = **nur lokales Ollama**. Im Repo selbst fehlt jedes Sovereignty-Doc (keine CLAUDE.md). → Entscheidung nötig: migrieren (Ollama/Mistral-EU) oder Ausnahme schriftlich fixieren.
- 🟠 **Fork mit überholter Begründung**: `views.py:8-11` „aifw.nl2sql … not yet published as of aifw 0.5.0" — seit aifw ≥0.7 falsch. Kein `import aifw` im Service.
- 🟡 Tote Dependency: `requirements.txt:4` pinnt `aifw>=0.5.0,<1` (nie importiert; korrekter Distributionsname wäre `iil-aifw`).

## 4. Befunde CAD

### nl2cad (Kern) — gesund, Härtung + Eval fehlen
- ✅ Klare Struktur: Parser (ifc/dxf/dwg/step/bcf/mesh/geo/pointcloud) + Analyzer (brandschutz, ex_zonen, dxf, gebaeude_kennzahlen); NL→DXF als Nebenpfad `nlp/nl2dxf.py` mit **Dependency-Injection** (`llm_client=None` → Regex-Fallback, `nl2dxf.py:86-87`), 0 hartkodierte Modell-IDs.
- ✅ CI grün (Tests/CI/Lint success, main, 2026-07-04), 31 Testdateien.
- 🟠 **Golden-Suite CI-blind**: `tests/test_realdata_golden.py` (handverifizierte Sollwerte gegen echte ArchiCAD-Modelle) wird per `skipif(NL2CAD_TESTDATA)` in CI übersprungen (`:24-28`). Geometrie-Korrektheit ohne CI-Gate. Für NL→DXF existiert gar kein Golden-Set.
- 🟠 **Keine Parser-Härtung**: kein Parse-Timeout/Resource-Limit (grep `signal.alarm|setrlimit|multiprocessing.*timeout` = 0); `ifcopenshell.geom`-Fallback CPU/RAM-intensiv → DoS-Fläche. `bcf_parser.py:18` nutzt stdlib `xml.etree` auf fremden `.bcfzip`-Inhalten (`:87,96,112`); **kein defusedxml fleet-weit** (0 Treffer über nl2cad/cad-hub/mcp-hub/risk-hub). Byte-Loader ohne Größenprüfung in der Lib (`loaders.py:34-56`) — Limits nur bei Konsumenten.

### cad-hub — Prod-Konsument mit Drift + totem Duplikat
- ✅ Prod bestätigt: nl2cad.de / Port 8094 (`platform/infra/ports.yaml:247-254`), Deploy success 2026-06-23. Echter Lib-Konsument (`apps/ifc/tasks.py:15-16`, Compat-Shim `apps/ifc/services/ifc_parser.py:13-15`).
- 🟠 **Pin-Drift**: `requirements.txt:12` `nl2cad-core[ifc]>=0.1.0,<1.0` — nl2cad-CHANGELOG fordert `>=0.4.0` (neue Reader + IFC-Tiefe).
- 🟡 **Toter Duplikat-Parser**: `apps/ifc/parser/parser.py` (`IfcCompleteParser`, direktes ifcopenshell) nur innerhalb `apps/ifc/parser/` referenziert — sehr wahrscheinlich nicht bereinigter ADR-029-Rest.
- ✅ Upload-Limit vorhanden (500 MB, `apps/ifc/services/upload_service.py`) — großzügig, ohne Parse-Timeout dahinter.

### risk-hub — echter Konsument, unpinned
- ✅ Tiefe Nutzung von `nl2cad.core.parsers/analyzers/models` + `nl2cad.gaeb` (u.a. `src/explosionsschutz/template_views.py:1492-1493`, `services/dxf_service.py:145ff`); 18 CAD-Testdateien; Upload-Limits vorhanden.
- 🟠 **Unpinned git-Dependency**: `pyproject.toml:54` `nl2cad-core @ git+…#subdirectory=…` **ohne Tag/SHA** → trackt main-HEAD; cad-hub bezieht via PyPI → zwei Bezugswege, Versions-Skew-Risiko.

### mcp-hub / ifc_mcp — Parallel-Engine
- 🟠 **Duplikat hoch**: `ifc_mcp/src/ifc_mcp/infrastructure/ifc/parser.py:14-18` nutzt `ifcopenshell` direkt (kein nl2cad-Import); eigene Ex-Zonen-/Brandschutz-Tools (`presentation/tools/ex_protection_tools.py:50-266`, `fire_plan_tools.py:256-358`) duplizieren funktional `nl2cad.core.analyzers.{ex_zonen,brandschutz}_analyzer` → **zwei divergierende Brandschutz/Ex-Zonen-Engines im Fleet** (risk-hub nutzt die Lib, ifc_mcp die Eigenbau-Engine).
- 🟠 Test-Lücke: ~1 Testdatei im ifc_mcp-Baum.
- HYPOTHESE: ifc_mcp-Deploy-Status ungeprüft (Check: ports.yaml + `gh run list`).

### bfagent
- ✅ ADR-029-Extraktion abgeschlossen (kein `apps/cad_hub` mehr). Reste: Doku (`docs/source/hubs/cad_hub.rst`), Konzepte, Standalone-Skript `dxf-analysis/dxf_analysis_toolkit.py` → Aufräum-Chance, kein Risiko.

## 5. Befunde IoT

- **nl2iot-hub = Vertrags-/Spec-Phase**: 0 Code-Dateien; ADR-001 `class: spec-demo`, accepted 2026-05-26; MVP (~15 Tage) nicht begonnen (`docs/adr/ADR-001-klickdummy-nl2iot-mvp.md:24,105`). Kein Docker/Port/Deploy.
- **Kein Aktor-Risiko by design**: Fluss NL → Intent → ST-Skelett → Static-Analysis/Hazard-Lint → **Pflicht-Engineer-Approval** → Sandbox-PLC-Sim; Deployment auf Ziel-SPS explizit out-of-scope (`docs/analysen/sps-toolchain-analyse.md:84-114`).
- ✅ **SIL-Gate-Konzept vorbildlich**: `safety_class none` generativ / `sil1` Template+Approval+Audit-Hash / `sil2` +Co-Sign / `sil3-4` Output blockiert (`ADR-001:80-86`) — aber **nur dokumentiert, nicht implementiert**.
- 🟡 **Dangling Reference**: ADR verweist auf `policies/llm-routing.md` im Repo — Verzeichnis existiert dort nicht (Drift; gemeint ist die Org-Policy).
- 🟡 0 Tests, kein Test-/Build-CI (nur gitleaks `secret-scan.yml`). Keine Broker-Credentials (kein Broker existiert) — sauberer Negativ-Befund.
- **Governance-Lücke**: kein Platform-ADR zu IoT/nl2iot; die repo-lokalen ADRs decken nur die Klickdummy-Ebene.

## 6. Governance-Kontext (ADRs & Policies)

Bindend für alle NL2X-Pipelines:
- **ADR-084** Model Registry (keine hardcoded Modellnamen) · **ADR-208** Model-Resolver (`-latest` verboten auf Eval/Audit-Pfaden) · **ADR-146** promptfw = SSoT für Prompts · **ADR-085** NL→TaskGraph als offizielles NL→Struktur-Pattern (bfagent/cad-hub-Integration laut ADR selbst offen, Z.225-226) · **llm-routing.md**: Groq/Cerebras free-tier first; ttz-hub/meiki-hub = nur lokales Ollama · **platform-agents.md**: gemeinsamer Kern gehört in Framework-Paket (aifw/promptfw), nicht in Domänen-Hubs.

Relevant, aber ungebaut: ADR-223 (Model Screener + Quality-Benchmarks, proposed), ADR-133 (Shared AI Services, proposed), ADR-243 (iil-corefw, proposed), ADR-245 (Provider-Policy-Engine in aifw, impl none).

**Governance-Lücken:** (1) kein NL2X-Eval-/Benchmark-Standard (größte Lücke); (2) IoT platform-seitig ungeregelt; (3) kein ADR, das einen gemeinsamen NL2X-Kern festlegt (Doppelaufwand-Risiko in ADR-134:57 bereits benannt); (4) Data-Sovereignty für NL2X-*Datenquellen* (Schema-Kontext, CAD-Kundendaten an externe Provider) ungeregelt.

## 7. Cross-Domain-Synthese

Alle drei Domänen implementieren **NL → validiertes strukturiertes Artefakt** mit denselben Bausteinen (Prompt → LLM → Validierung → gated Execution → Feedback). Ist-Zustand der Bausteine:

| Baustein | NL2SQL (aifw) | CAD (nl2cad) | IoT (Spec) |
|---|---|---|---|
| Prompt-Verwaltung | hardcoded (≠ADR-146) | inline, LLM optional | konzeptionell |
| Modell-Routing | DB (AIActionType) ✅ | DI, konsumentenseitig ✅ | — |
| Output-Validierung | Regex+RO-Txn ✅ | Parser/Analyzer ✅ | SIL-Gate (Papier) |
| Execution-Gate | read-only DB | n/a (Analyse) | Engineer-Approval (Papier) |
| Accuracy-Eval | ❌ (nur ttz-Ansatz) | Golden-Suite CI-blind | ❌ |
| Feedback-Loop | example_feedback ✅ | ❌ | — |

**Konsolidierungs-Empfehlung (T2, right-sized):** Kein neues Repo, kein Big-Bang-Framework. Stattdessen:
1. **aifw als Heimat des NL2X-Kerns** — `aifw.nl2sql` ist das reifste Exemplar; Verallgemeinerung (Validierungs-/Gate-/Eval-Schnittstelle) dort, Prompts nach promptfw (ADR-146). Entspricht platform-agents-Policy.
2. **Ein Eval-Standard für alle drei**: Golden-Set-Format (Input-NL, Ground-Truth-Artefakt, Toleranz) + ein Runner; NL2SQL nutzt ttz-`evaluate.py` als Keimzelle, CAD aktiviert `test_realdata_golden.py` in CI, IoT bekommt es ab MVP-Start.
3. **Bewusst getrennt lassen**: Parser/Analyzer (nl2cad-core) und SPS-Sicherheitslogik — domänenspezifisch, keine erzwungene Abstraktion.
4. ADR-pflichtig (cross-cutting): Vorschlag **„ADR: NL2X-Kern in aifw + fleet-weiter Eval-Standard"** — nur Titel+Kontext, Entscheidung beim Owner.

## 8. Roadmap (priorisiert)

| Prio | Maßnahme | Repo | Aufwand | Erfolgskriterium |
|---|---|---|---|---|
| P1 🔴 | odoo Legacy-Fallback absichern: RO-Rolle oder Fallback entfernen; `allow_write` streichen; Prod-`aifw_service_url` verifizieren | odoo-hub | S–M | LLM-SQL-Exec nur noch über RO-Pfad; Regression-Test |
| P1 🔴 | ttz Sovereignty-Entscheid: Ollama/Mistral-EU-Migration ODER schriftliche Ausnahme | ttz-hub | M / S | kein OpenAI-Call bzw. ratifizierte Ausnahme |
| P2 🟠 | nl2cad Golden-Suite in CI aktivieren (Testdata-Artefakt/LFS) | nl2cad | S | Suite läuft in CI, Gate rot bei Geometrie-Drift |
| P2 🟠 | NL2SQL-Accuracy-Golden-Set als CI-Gate (Keimzelle ttz `evaluate.py` → aifw) | aifw | M | Accuracy-Metrik je Release sichtbar |
| P2 🟠 | Parser-Härtung: defusedxml (bcf), Parse-Timeout, Byte-Loader-Größenlimit | nl2cad | S–M | Härtungs-Tests grün |
| P3 🟠 | ttz-hub auf `aifw.nl2sql` migrieren (Fork #3 eliminieren; DB-Rollen-Setup als Vorbild in aifw übernehmen) | ttz-hub, aifw | M | kein Custom-NL2SQL-Code mehr; 50 Tests portiert |
| P3 🟠 | ifc_mcp auf nl2cad-core umstellen (Wrapper statt Eigenbau-Engine) | mcp-hub | M–L | eine Brandschutz/Ex-Zonen-Engine im Fleet |
| P3 🟡 | Pins fixen: cad-hub `>=0.4.0`; risk-hub git-Dep auf Tag/SHA | cad-hub, risk-hub | S | reproduzierbare Builds |
| P4 🟡 | Aufräumen: odoo v18/v19-Doppel-Addon konsolidieren; cad-hub `IfcCompleteParser` löschen; bfagent CAD-Doku-Reste; ttz tote `aifw`-Dep | 4 Repos | S | 0 tote Duplikate |
| P4 🟡 | aifw-Seed: Groq/Cerebras ergänzen, tote Modell-IDs gegen known-dead-models.txt bereinigen; Prompt → promptfw | aifw | S | Policy-konformes Default-Routing |
| P5 | ADR-Vorschlag „NL2X-Kern in aifw + Eval-Standard"; IoT-Platform-ADR erst ab MVP-Start | platform | S | Entscheidung dokumentiert |

## 9. Abdeckung & Restlücken

- Inventar per `rg -li` über alle ~70 Verzeichnisse unter `~/github` (node_modules/.git/venv/dist exkludiert), 3 Domänen-Muster + Gegenproben. 10 Repos tief analysiert, Rest als „nur Erwähnung" klassifiziert.
- **Verifiziert**: alle datei:zeile-Belege oben; CI-Status nl2cad/cad-hub via `gh run list`; Extraktion ADR-029.
- **Nicht verifiziert (Hypothesen + billigster Check)**:
  - H-odoo: Prod-`aifw_service_url` gesetzt? → Odoo-Konfigparameter in Prod lesen.
  - H-ttz: verletzt OpenAI-Call Kundenvertrag? → Angebots-/Vertragsdoku prüfen (`docs/Angebot_KI_Werkleiterassistent_Phase1_IIL.md`).
  - H-pypi: publizierte PyPI-Versionen der nl2cad-Pakete vs. Repo-Tags → `pip index versions nl2cad-core`.
  - H-ifcmcp: ifc_mcp produktiv deployt? → ports.yaml + `gh run list -R mcp-hub`.
  - H-cadhub-dead: `IfcCompleteParser` wirklich unreferenziert (Management-Commands)? → gezielter rg-Lauf.

---
*Audit-Methode: 4 parallele read-only Explore-Agenten (NL2SQL, CAD, IoT, Governance), Synthese durch Hauptsession. Erstellt von Claude Code am 2026-07-04. Nicht committet — Freigabe ausstehend.*
