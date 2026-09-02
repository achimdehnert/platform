---
status: proposed
decision_date: 2026-09-02
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-080, ADR-086, ADR-101, ADR-112, ADR-186]
related: [ADR-010, ADR-176, ADR-197, ADR-224, ADR-238, ADR-256, ADR-280, ADR-282, ADR-285]
implementation_status: not_started
last_reviewed: 2026-09-02
staleness_months: 6
---

<!--
  ADR-300 — Basis: docs/templates/adr-template.md v2.1
  Anker: platform#2606, Owner-Entscheidung E2 („27 Orchestrator-Tools: konsumieren oder deprecaten")
-->

# ADR-300: Orchestrator = Gedächtnis + Gate, Harness = Ausführung

> **Kennzeichnung (Lotsen-Charta, Punkt 3):** Dieses ADR wurde von einem Agenten
> vorgeschlagen und **erweitert dessen Handlungsraum** — Harness-Primitiven
> (Subagenten, Workflows, Hooks, `/loop`, `/schedule`) treten an die Stelle von
> Orchestrator-Werkzeugen, die heute einen zentralen Kontrollpunkt darstellen. Es ist
> ausdrücklich **nur ein Vorschlag**; die Entscheidung liegt beim Owner. Der Vorschlag
> ist ungebündelt: er ändert keine Policy, kein Profil und keine Permission.

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-09-02                                                           |
| **Autor**       | Claude Code (Vorschlag) — Entscheidung: Achim Dehnert                |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Amends**      | ADR-080, ADR-086 (Agent-Team im Orchestrator), ADR-101 (Tool-Budget), ADR-112 (Skill-Registry + Gedächtnis), ADR-186 (Headless-Pipeline) |
| **Relates to**  | ADR-010 (MCP-Tool-Governance), ADR-176 (MCP-Server-SSoT), ADR-197 (Tool-Pruning), ADR-224/256 (Transport), ADR-238 (Containment), ADR-280/282/285 (Skill-Lane) |
| **Review-/Kill-Gate** | **2026-10-31**                                                 |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                                         |
|----------------|------------|------------------------------------------------------------------------|
| `platform`     | Primär     | `docs/adr/`, `skills/`, `.windsurf/workflows/`, Konsumenten-Zähler (CI) |
| `mcp-hub`      | Primär     | `orchestrator_mcp/tools/` (6 Module, 35 Tools), `orchestrator_mcp/headless/`, `orchestrator_mcp/agent_team/`, Dispatch-Test |
| `~/.claude`    | Sekundär   | `policies/orchestrator.md` — Folge-PR nach Accept (nicht Teil dieses ADR) |
| `dev-hub`      | Referenz   | Apps, die Orchestrator-Daten lesen — **keine Aussage in diesem ADR**   |

---

## Decision Drivers

- **35 Schemata je Session, 8 Konsumenten.** Jede Claude-Code-Session lädt alle 35
  Tool-Schemata des Orchestrators; von Skills und Workflows konsumiert werden 8. Die
  übrigen 27 kosten Kontext in jeder Session und liefern nichts zurück.
- **30 von 35 Tools ohne Verhaltenstest.** Der Dispatch-Test prüft nur „exactly 35
  tools". Ein Werkzeug, das niemand aufruft und niemand testet, ist kein Werkzeug,
  sondern eine Angriffs- und Drift-Fläche.
- **Die Harness hat die Ausführungs-Familie eingeholt.** Subagenten (Agent-Tool, Fork,
  Worktree-Isolation), Mehr-Agenten-Workflows, `/loop`, `/schedule` (Cloud-Routinen),
  Plan-Modus und Hooks (Gates an Stop/PreToolUse) sind nativ da. Ein Orchestrator-Tool,
  das dasselbe über einen HTTP-Umweg tut, ist die schlechtere Bauform.
- **Gedächtnis und Gate sind das, was die Harness nicht hat.** Session-übergreifendes
  Gedächtnis mit Zerfall (pgvector-Store, `agent_memory_*`), Audit-Log, Fehlermuster, Kostenmessung und Freigaben
  brauchen einen Ort außerhalb der Session. `policies/orchestrator.md` und die
  Lotsen-Charta setzen genau das voraus.
- **Nichts darf lautlos wachsen.** Die Zahl 27 ist über Monate entstanden, ohne dass
  ein Check sie gemeldet hätte. Was nicht gemessen wird, wächst nach.

---

## 1. Context and Problem Statement

Der Orchestrator-MCP (`mcp-hub/orchestrator_mcp/`) wurde als zentrale Steuerung für
Agenten entworfen: Planung, Delegation, Headless-Läufe, Workflow-Ausführung,
Kommando-Ausführung mit ScopeLock, dazu Gedächtnis, Gates und Audit. Seitdem hat sich
die Claude-Code-Harness die Ausführungsseite selbst angeeignet. Zurück bleibt ein
Server, dessen Werkzeuge zu drei Vierteln niemand ruft, der aber in jeder Session voll
geladen wird und dessen Policy ihn zur „authoritative source" erklärt.

`policies/orchestrator.md` legt heute fest: Routing, Memory, LLM-Calls und Headless-Läufe
liegen beim Orchestrator; „Headless/CI runs always have it (that's its main consumer)".
Diese Festlegung stammt aus dem Mai 2026 und beschreibt eine Aufgabenteilung, die so
nicht mehr gelebt wird.

### 1.1 Ist-Zustand (Audit 2026-09-02, platform#2606)

| Messgröße | Wert | Quelle |
|---|---|---|
| Registrierte Tools | **35** in 6 Modulen (memory 9, gate 6, workflow 6, exec 5, misc 5, job 4) | `orchestrator_mcp/tools/` |
| Von Skills/Workflows konsumiert | **8**: `agent_memory_search`, `agent_memory_upsert`, `check_recurring_errors`, `discord_notify`, `estimate_job`, `find_similar_errors`, `record_job_measurement`, `session_stats` | `grep -rhoE "orchestrator__[a-z_]+" skills/ .windsurf/workflows/` |
| Ohne Konsument | **27**, darunter `plan_and_execute`, `delegate_subtask`, `headless_run`, `agent_plan_task`, `agent_team_status`, `check_gate`, `deploy_check`, `review_adr`, `request_approval`, `get_full_context`, `memory_backfill`, alle `workflow_*`, alle `run_*` | dito |
| Verhaltenstests | **5/35**: `analyze_task`, `headless_run`, `run_command_safe`, `run_git`, `session_stats` | `mcp-hub/tests/` |
| Dispatch-Test | prüft nur „exactly 35 tools" | `mcp-hub/tests/` |
| Schemata je Session | 35 (alle), unabhängig vom Repo | globale `mcpServers` in `~/.claude/settings.json` |
| Harness-Primitiven | Subagenten (Agent/Fork/Worktree), Workflows, `/loop`, `/schedule`, Plan-Modus, Hooks | Claude-Code-Harness, Stand 2026-09 |

Nachgemessen im Repo `platform` am 2026-09-02: die 8 konsumierten Tools sind genau die
Gedächtnis-, Fehlermuster- und Messwerkzeuge; kein einziges Ausführungs- oder
Planungswerkzeug hat einen Aufrufer.

**Symptom am Rande, keine Entscheidung dieses ADR:** Die Modell-Fallbacks in
`orchestrator_mcp/model_registry.py` (`claude-opus-4-7`, `claude-sonnet-4-6`) und
`orchestrator_mcp/headless/adapters/claude.py` liegen eine Generation hinter
`policies/llm-routing.md` (5er-Familie). Betroffen ist ausschließlich die
Ausführungs-Familie — ein weiterer Beleg dafür, dass dieser Teil nicht gepflegt wird,
weil ihn niemand benutzt.

### 1.2 Warum jetzt

platform#2606 hat die Zahlen auf den Tisch gelegt und mit E2 die Frage gestellt:
konsumieren oder deprecaten. Beides ist Arbeit; nichts zu tun ist die dritte Option und
kostet weiter 35 Schemata pro Session bei sinkender Testabdeckung. Die Entscheidung fällt
vor dem nächsten Ausbau des Orchestrators — danach wäre sie teurer.

---

## 2. Considered Options

### Option A: Aufteilen — Orchestrator behält Gedächtnis + Gate, Ausführung geht an die Harness ✅

Der Orchestrator bleibt **Autorität** für zwei Domänen, die außerhalb der Session leben
müssen: Gedächtnis und Gate/Audit. Die Ausführungs-/Planungs-Familie wird deprecated und
nach einer Frist entfernt, es sei denn, ein benannter Konsument entsteht.

**Pros:**
- Behält genau das, was `orchestrator.md` und die Charta voraussetzen (Gedächtnis-SSoT,
  Freigaben, Audit)
- Entfernt die 19 Werkzeuge, für die die Harness die bessere Bauform hat
- Jedes verbleibende Werkzeug hat einen benannten Konsument — und damit einen Grund

**Cons:**
- Zwei Systeme statt eines: Ausführung in der Harness, Gedächtnis/Gate im Orchestrator;
  die Naht (was loggt die Harness zurück?) muss ausdrücklich gebaut werden
- ADR-186 (Headless-Pipeline, 44 Tests, Phase 1) verliert seinen Aufrufer, wenn kein
  Konsument für `headless_run` entsteht

### Option B: Alles behalten (Status quo)

**Pros:**
- Keine Arbeit, kein Verlust an Optionen

**Cons:**
- 35 Schemata je Session, 27 ohne Aufrufer, 30 ohne Test — auf Dauer
- Die Zahl wächst weiter, weil kein Check sie meldet → **Abgelehnt weil:** der Zustand
  ist genau das Problem, das E2 benennt

### Option C: Alles deprecaten — Orchestrator abschalten

**Pros:**
- Ein System weniger, keine Naht

**Cons:**
- Verliert das Gedächtnis-SSoT (pgvector, Zerfall, `claude-policy`-Sync), das
  `orchestrator.md` und die Charta (Punkt 9/10: durable Artefakte, unbestätigte
  Memory-Kandidaten) voraussetzen
- Verliert Audit-Log und Freigabe-Pfad, für die die Harness nur lokale Hooks bietet →
  **Abgelehnt weil:** die Harness hat kein session-übergreifendes Gedächtnis und keinen
  zentralen Audit-Ort

### Option D: Skills zwingen, die 27 zu konsumieren

**Pros:**
- Nutzt, was gebaut ist; keine Entfernung

**Cons:**
- Erzeugt Aufrufer für Werkzeuge, die die Harness besser kann (Subagent statt
  `delegate_subtask`, Hook statt `check_gate`-Aufruf im Skill, Bash statt `run_git`)
- Verankert einen HTTP-Umweg als Pflicht → **Abgelehnt weil:** Konsum um des Konsums
  willen ist kein Grund

---

## 3. Decision Outcome

**Gewählte Option: Option A — Aufteilen.** Drei Entscheidungen, D1–D3.

### D1 — Der Orchestrator bleibt Autorität für Gedächtnis und Gate/Audit

| Domäne | Werkzeuge (16) | Konsument heute |
|---|---|---|
| Gedächtnis | `agent_memory_search`, `agent_memory_upsert`, `agent_memory_context`, `memory_backfill` | 2 von 4 |
| Gate / Freigabe / Audit | `check_gate`, `request_approval`, `get_audit_log`, `log_action` | 0 von 4 |
| Fehlermuster | `check_recurring_errors`, `find_similar_errors`, `log_error_pattern` | 2 von 3 |
| Messung / Kosten | `session_stats`, `record_job_measurement`, `estimate_job`, `get_cost_estimate` | 3 von 4 |
| Benachrichtigung | `discord_notify` | 1 von 1 |

„Autorität" heißt: neue Funktion in diesen Domänen entsteht **im Orchestrator**, nicht in
der Harness und nicht in einem Skill-lokalen Speicher. Die Harness liest und schreibt
über diese Werkzeuge; sie ersetzt sie nicht.

**D1 schützt die Domäne, nicht das einzelne Werkzeug.** Acht der 16 D1-Werkzeuge haben
heute keinen Konsument. Für sie gilt dasselbe Kill-Gate wie für D2 (§3.2) — mit dem
Unterschied, dass der erwartete Ausgang ein Konsument ist (z.B. ein Stop-Hook, der
`log_action` ruft; `check_gate` aus einem Merge-Skill), nicht die Entfernung. Wer bis
zum Gate keinen Konsument bekommt, geht trotzdem aus der Registrierung; die Daten
dahinter (Audit-Tabellen, Memory-Store) bleiben.

### D2 — Die Ausführungs-/Planungs-Familie wird deprecated

| Familie | Werkzeuge (19) | Harness-Primitive, die es ersetzt |
|---|---|---|
| Planung / Delegation | `plan_and_execute`, `delegate_subtask`, `agent_plan_task`, `agent_team_status`, `analyze_task`, `get_full_context` | Plan-Modus, Agent-Tool (Fork, Worktree), Mehr-Agenten-Workflows |
| Headless / Workflow | `headless_run`, `workflow_list`, `workflow_run`, `workflow_execute`, `run_workflow`, `list_job_types` | `/schedule` (Cloud-Routinen), `/loop`, Workflows |
| Kommando-Ausführung | `run_command_safe`, `run_git`, `run_lint`, `run_tests` | Bash-Tool unter Permission-System + Hooks (PreToolUse) |
| Prüfung / Review | `deploy_check`, `review_adr`, `cascade_log_response` | Skills (`/adr-review`, `/deploy`), Stop-Hooks |

**Übergangsfrist: 60 Tage ab Accept**, spätestens bis zum Kill-Gate **2026-10-31**.
Regel: *Ein Tool ohne Konsument in `skills/` oder `.windsurf/workflows/` nach Ablauf
der Frist wird aus der Registrierung entfernt.* Wo ein Werkzeug doch gebraucht wird
— naheliegend `headless_run` für Nacht-Queues ohne interaktive Session
(`/process-agent-queue`) — muss **innerhalb der Frist ein benannter Konsument**
(Skill oder Workflow, mit Aufruf im Text) entstehen. Sonst geht es. Ein Konsument, der
nur zum Erhalt des Werkzeugs geschrieben wird, verstößt gegen die Ablehnung von
Option D; das prüft der Review, nicht der Zähler.

Deprecation ist **sichtbar**: die Tool-Beschreibung im Schema trägt ab dem Accept den
Präfix `[DEPRECATED ADR-300, Frist 2026-10-31]`, damit jeder Aufrufer — auch einer, den
der Zähler nicht sieht — es in seinem eigenen Kontext liest.

### D3 — Messbarkeit: Konsumenten-Zähler als CI-Check

Damit die 27 nicht nachwächst, gibt es eine **Konsumenten-Registry** in `platform`
(`registry/orchestrator-tools.yaml`): je Tool die Domäne (D1/D2), der Status
(`aktiv` / `deprecated` / `entfernt`) und die Konsumenten als Pfade. Ein CI-Check in
`platform` (Workflow neben `adr-validate.yml`) prüft:

1. **Grep gegen Registry:** Jede Referenz `orchestrator__<tool>` in `skills/` und
   `.windsurf/workflows/` gehört zu einem registrierten Tool. Eine Referenz auf ein
   `deprecated`-Tool ist ein Fund (SUGGEST bis zum Kill-Gate, danach GATING).
2. **Registry gegen Grep:** Jeder in der Registry eingetragene Konsument-Pfad existiert
   und enthält den Aufruf. Ein `aktiv`-Tool ohne Konsument ist ein Fund.
3. **Registry gegen Registrierung:** `mcp-hub` ersetzt den Dispatch-Test „exactly 35"
   durch einen Abgleich mit derselben Registry-Datei (Snapshot im Test-Fixture, Drift =
   rot). Damit driften Registrierung und Zählung nicht auseinander.

Der Zähler sieht nur `platform`. Konsumenten außerhalb (CI-Jobs, `claude-policy`-CLI,
Headless-Container, dev-hub-Apps) müssen **in der Registry deklariert** werden; der
Grep ist Ergänzung, nicht Ersatz der Deklaration. Der Check startet **SUGGEST**
(repo-health-rule-discipline) und wird mit dem Kill-Gate GATING.

---

## 4. Implementation Details

### 4.1 Reihenfolge

| # | Schritt | Repo | Wann |
|---|---|---|---|
| 1 | Registry-Datei anlegen, 35 Tools klassifizieren (D1/D2), heutige 8 Konsumenten eintragen | platform | mit Accept |
| 2 | Konsumenten-Zähler (SUGGEST) in CI | platform | mit Accept |
| 3 | Deprecation-Präfix in den Schemata der 19 D2-Tools | mcp-hub | mit Accept |
| 4 | Dispatch-Test „exactly 35" → Registry-Abgleich | mcp-hub | mit Accept |
| 5 | Folge-PR `policies/orchestrator.md` (Rolle neu schneiden, „Headless = main consumer" streichen) | `~/.claude` → platform (Policy-Kanon) | nach Accept |
| 6 | Konsumenten für D1-Werkzeuge ohne Aufrufer bauen oder bewusst nicht (Registry-Eintrag mit Grund) | platform | bis 2026-10-31 |
| 7 | Kill-Gate: Frist prüfen, Tools ohne Konsument aus Registrierung entfernen, Zähler GATING | mcp-hub + platform | 2026-10-31 |

### 4.2 Was mit dem Code hinter den D2-Tools geschieht

Entfernung aus der **Registrierung** ist nicht Löschung des Codes. `orchestrator_mcp/
headless/` und `orchestrator_mcp/agent_team/` bleiben bis zu einer eigenen Entscheidung
im Repo (ADR-186 ist `proposed`, ADR-080/086 `accepted`). Dieses ADR nimmt ihnen die
Tool-Oberfläche, nicht die Existenz. Ob der Code danach ein Bibliotheks-Konsument (z.B.
aus einem Nacht-Container heraus) bleibt oder archiviert wird, entscheidet der Review am
Kill-Gate mit den dann gemessenen Konsumenten.

### 4.3 Amendments im Einzelnen

| ADR | Was sich ändert |
|---|---|
| ADR-080 / ADR-086 | Das Agent-Team wird nicht mehr über Orchestrator-Tools (`agent_plan_task`, `agent_team_status`, `delegate_subtask`) gefahren, sondern über Harness-Subagenten und Workflows. Conventions, Gates und Reflexion (§2 in ADR-086) bleiben. |
| ADR-101 | Das Tool-Budget (§3, 76/100) wird um die 19 D2-Tools entlastet; die Aussage „Orchestrator = Steuerung" wird auf Gedächtnis + Gate eingeengt. |
| ADR-112 | Gedächtnis-Rolle **bestätigt** (D1). Die `SkillRegistry` im Orchestrator ist seit ADR-280/285 nicht mehr die Quelle der Skills; die Ausführung über Orchestrator-Tools entfällt. |
| ADR-186 | `headless_run` als MCP-Tool ist deprecated; die Pipeline bleibt als Code. Ein Konsument (Nacht-Queue) muss bis zum Kill-Gate benannt sein, sonst verliert ADR-186 seinen Tool-Einstieg. |

ADR-197 (repo-aware Tool-Pruning, `proposed`) wird nicht amendiert: es zielt auf **alle**
MCP-Server und auf Client-seitiges Ausblenden. Dieses ADR nimmt dem Orchestrator-Anteil
den Druck Server-seitig — der Rest von ADR-197 bleibt offen.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` | 1 — Registry + Zähler (SUGGEST) | ⬜ Ausstehend | – | §3 D3, §4.1 #1–2 |
| `mcp-hub` | 1 — Deprecation-Präfix + Dispatch-Test | ⬜ Ausstehend | – | §4.1 #3–4 |
| Policy-Kanon | 2 — `orchestrator.md` Folge-PR | ⬜ Ausstehend | – | §4.1 #5, nach Accept |
| `platform` | 3 — D1-Konsumenten | ⬜ Ausstehend | – | §4.1 #6 |
| `mcp-hub` + `platform` | 4 — Kill-Gate | ⬜ Ausstehend | 2026-10-31 | §4.1 #7 |

---

## 6. Consequences

### 6.1 Good

- Jede Session lädt nach dem Kill-Gate ≤16 statt 35 Orchestrator-Schemata; jedes davon
  hat einen benannten Aufrufer
- Die Rolle des Orchestrators ist in einem Satz sagbar: *Gedächtnis und Gate, nicht
  Ausführung* — das ist auch der Satz, der in `orchestrator.md` fehlt
- Testabdeckung wird ehrlich: 5 Tests für 16 Tools statt 5 für 35; die Lücke ist
  kleiner und benannt
- Ein Zähler statt eines Audits alle paar Monate

### 6.2 Bad

- Zwei Systeme mit einer Naht: was die Harness ausführt, sieht der Orchestrator nur,
  wenn ein Hook oder Skill es zurückmeldet (`log_action`). Die Naht ist heute nicht
  gebaut (0 Konsumenten für `log_action`, `check_gate`, `request_approval`)
- ADR-186 (Headless) und ADR-080/086 (Agent-Team) verlieren ihre Tool-Oberfläche;
  Arbeit, die dort steckt (44 Tests, 160+ Tests), wird zu Bibliotheks-Code ohne Aufrufer
- Konsumenten außerhalb von `platform` sind für den Zähler unsichtbar; die Registry
  muss gepflegt werden — ein neuer Pflegeort

### 6.3 Nicht in Scope

Siehe §7 „Was dieses ADR NICHT entscheidet".

---

## 7. Was dieses ADR NICHT entscheidet

- **Keine Änderung an `policies/orchestrator.md` selbst.** Die Policy ist Policy-Kanon
  und wird **nach** Accept in einem Folge-PR angepasst (Rolle: Gedächtnis + Gate;
  Streichung von „Headless/CI runs … main consumer"; Verweis auf die Registry). Dieses
  ADR liefert die Begründung, nicht den Text.
- **Kein Abbau des Orchestrator-Dienstes.** Transport (ADR-224/256), Deployment, Schlüssel-
  Rotation, `claude-policy`-Sync bleiben unverändert. Der Dienst wird schmaler, nicht
  abgeschaltet.
- **Keine Aussage über dev-hub-Apps.** Apps, die Orchestrator-Tabellen lesen oder eigene
  Sichten darauf bauen, sind nicht Gegenstand; sie sind, wenn sie MCP-Tools rufen, als
  Konsumenten in die Registry einzutragen.
- **Keine Entscheidung über die Modell-IDs** in `model_registry.py` / `headless/adapters/`
  (§1.1 Symptom). Wird `headless_run` behalten, ist der Nachzug auf die 5er-Familie Teil
  des Konsumenten-PR; wird es entfernt, erledigt sich die Frage.
- **Keine Entscheidung über ADR-197** (Client-seitiges Pruning aller MCP-Server).
- **Kein Löschen von Code** unter `orchestrator_mcp/headless/` oder `agent_team/` (§4.2).

---

## 8. Risks

| # | Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|---|---|---|---|---|
| R1 | **Souveräner Nacht-Pfad fällt weg.** `/schedule` läuft in der Anthropic-Cloud; für Repos mit strengen Daten (Gov/LRA) sind Cloud-Routinen read-only oder ausgeschlossen. `headless_run` ist heute der einzige Weg, unbeaufsichtigt **auf eigener Infrastruktur** zu laufen. | mittel | hoch | Frist + benannter Konsument (`/process-agent-queue`) statt sofortiger Entfernung; Kill-Gate entscheidet mit Messung, nicht mit Annahme |
| R2 | **Gate ohne Sicht auf die Ausführung.** `check_gate`/`request_approval`/`log_action` sind nur so gut wie das, was zurückgemeldet wird. Wandert die Ausführung in die Harness, sieht der Audit-Ort nur freiwillige Meldungen; Hooks sind Maschinen-Konfiguration, kein zentraler Zwang (Perimeter-Asymmetrie). D2 kann D1 aushöhlen. | mittel | hoch | Naht als D1-Konsument bauen (Stop-Hook → `log_action`) **vor** dem Kill-Gate; Registry-Eintrag mit Grund, wenn nicht |
| R3 | ScopeLock/Containment (ADR-238) lebte in `run_command_safe`; die Harness hat kein Server-seitiges Äquivalent | niedrig | mittel | ADR-238 bleibt; Hooks (PreToolUse) als lokales Gegenstück; Restlücke im Review benennen |
| R4 | Zähler meldet grün, weil Konsumenten außerhalb `platform` nicht deklariert sind | mittel | mittel | Deklarationspflicht in der Registry; Deprecation-Präfix im Schema erreicht auch undeklarierte Aufrufer |
| R5 | Konsumenten werden geschrieben, um Werkzeuge zu retten (Option D durch die Hintertür) | niedrig | niedrig | Review am Kill-Gate liest die Konsumenten, nicht nur den Zähler |

R1 und R2 sind die beiden stärksten Gegenargumente gegen D2. Beide sprechen nicht gegen
die Aufteilung, sondern gegen eine Entfernung **ohne gebaute Naht** — deshalb Frist und
Kill-Gate statt sofortigem Schnitt.

---

## 9. Confirmation

Das ADR ist umgesetzt, wenn am **2026-10-31** gilt:

- [ ] `registry/orchestrator-tools.yaml` existiert, klassifiziert alle registrierten Tools
- [ ] Konsumenten-Zähler läuft in `platform`-CI und ist GATING
- [ ] `mcp-hub`-Dispatch-Test gleicht gegen die Registry ab (kein „exactly N")
- [ ] Jedes registrierte Tool hat ≥1 deklarierten, existierenden Konsument
- [ ] Kein registriertes Tool trägt den Status `deprecated` (entweder Konsument oder entfernt)
- [ ] `policies/orchestrator.md` ist per Folge-PR angepasst
- [ ] Jede Session lädt ≤16 Orchestrator-Schemata (gemessen an der Tool-Liste bei Session-Start)

## Kill-Gate

**Messpunkt 2026-10-31.** Verworfen wird das ADR, wenn seine Begründung widerlegt ist —
nicht, wenn etwas nicht umgesetzt wurde:

- Zeigt die Messung, dass D2-Werkzeuge **doch** laufend gebraucht werden (≥3 der 19 mit
  echten, nicht rettenden Konsumenten), war die Prämisse „Harness hat sie eingeholt"
  falsch → D2 wird auf die tatsächlich ersetzbaren Werkzeuge eingeengt, das ADR
  überarbeitet.
- Ist die Naht (R2) bis dahin nicht gebaut und `log_action`/`check_gate` weiter ohne
  Konsument, ist D1 als „Autorität für Gate" nicht eingelöst → D1 wird auf Gedächtnis
  eingeengt oder die Naht wird zur Bedingung der Entfernung.
- Beides nicht eingetreten → Kill-Gate bestanden, Zähler GATING, deprecated-Tools raus.

---

## Glossar

| Begriff | Bedeutung |
|---|---|
| Harness | Die Claude-Code-Laufzeit: Tools, Subagenten, Workflows, Hooks, Permission-System |
| Konsument | Skill/Workflow/Job, der ein Orchestrator-Tool **im Text** aufruft |
| Registrierung | Die Liste der Tools, die der Orchestrator per MCP `tools/list` anbietet |
| Naht | Der Rückkanal Harness → Orchestrator (Hook oder Skill ruft `log_action` u.ä.) |

## 10. More Information

- platform#2606 — Audit vom 2026-09-02, Owner-Entscheidung E2
- `~/.claude/policies/orchestrator.md` — heutige Rollen-Festlegung (Folge-PR)
- `~/.claude/policies/adr-threshold.md` — „reverses or replaces an existing architectural
  decision" + cross-cutting → ADR-pflichtig
- Agent-Memory-Store (pgvector + zeitlicher Zerfall, `orchestrator_mcp/memory/`) —
  Grundlage von D1; das ursprüngliche Memory-ADR liegt unter `docs/adr/archive/`

## 11. Changelog

| Datum | Version | Änderung |
|---|---|---|
| 2026-09-02 | 0.1 | Entwurf (proposed), vorgeschlagen von Claude Code; Anker platform#2606 E2 |
