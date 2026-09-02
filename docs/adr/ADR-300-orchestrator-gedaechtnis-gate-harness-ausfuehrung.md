---
status: accepted
decision_date: 2026-09-02
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-101, ADR-112, ADR-186]
related: [ADR-010, ADR-075, ADR-080, ADR-086, ADR-176, ADR-197, ADR-224, ADR-238, ADR-256, ADR-280, ADR-285]
implementation_status: not_started
last_reviewed: 2026-09-02
staleness_months: 6
---

<!-- ADR-300 — Basis: docs/templates/adr-template.md v2.1 · Anker platform#2606 E2 · Rev 0.2 nach /adr-challenger (#2642) -->

# ADR-300: Orchestrator = Gedächtnis + Audit, Harness = Ausführung

> **Kennzeichnung (Lotsen-Charta, Punkt 3):** Dieses ADR wurde von einem Agenten
> vorgeschlagen und **erweitert dessen Handlungsraum** — Harness-Primitiven treten an die
> Stelle von Orchestrator-Werkzeugen, die heute einen zentralen Kontrollpunkt darstellen.
> Nur Vorschlag, ungebündelt (keine Policy, kein Profil, keine Permission wird geändert);
> die Entscheidung liegt beim Owner.

## Metadaten

| Attribut | Wert |
|---|---|
| **Status** | Proposed (platform, 2026-09-02) |
| **Autor** | Claude Code (Vorschlag) — Entscheidung: Achim Dehnert |
| **Amends** | ADR-101 (Tool-Budget §9), ADR-112 (Gedächtnis + SkillRegistry), ADR-186 (Headless-Pipeline, Tool-Einstieg) |
| **Relates to** | ADR-010, ADR-075, ADR-080/086, ADR-176, ADR-197, ADR-224/256, ADR-238, ADR-280/285 |
| **Review-/Kill-Gate** | **2026-10-31** |

## Repo-Zugehörigkeit

| Repo | Rolle | Betroffene Pfade |
|---|---|---|
| `platform` | Primär | `docs/adr/`, `skills/`, `.windsurf/workflows/`, `registry/orchestrator-tools.yaml` (neu), CI-Zähler |
| `mcp-hub` | Primär | `orchestrator_mcp/tools/` (6 Module, 35 Tools), Dispatch-Test; `headless/`, `agent_team/` bleiben Code |
| Policy-Kanon | Sekundär | `policies/orchestrator.md` — Folge-PR nach Accept, nicht Teil dieses ADR |

---

## 1. Context and Problem Statement

Der Orchestrator-MCP wurde als zentrale Agenten-Steuerung entworfen: Planung, Delegation,
Headless-Läufe, Workflow- und Kommando-Ausführung, dazu Gedächtnis, Gates und Audit.
Seitdem hat die Claude-Code-Harness die Ausführungsseite selbst übernommen. Zurück bleibt
ein Server, dessen Werkzeuge zu drei Vierteln niemand ruft, der aber in jeder Session voll
geladen wird und den `policies/orchestrator.md` (Mai 2026) zur „authoritative source"
für Routing, Memory, LLM-Calls **und** Headless-Läufe erklärt.

**Ist-Zustand (Audit 2026-09-02, platform#2606; Konsumenten im Repo nachgemessen):**
35 registrierte Tools (memory 9, gate 6, workflow 6, exec 5, misc 5, job 4). Von
`skills/` und `.windsurf/workflows/` konsumiert: **8** — `agent_memory_search`,
`agent_memory_upsert`, `check_recurring_errors`, `discord_notify`, `estimate_job`,
`find_similar_errors`, `record_job_measurement`, `session_stats`. **27 ohne Konsument**,
darunter alle `workflow_*`, alle `run_*`, `plan_and_execute`, `delegate_subtask`,
`headless_run`, `check_gate`, `request_approval`. Verhaltenstests **5/35**; der
Dispatch-Test prüft nur „exactly 35 tools". Jede Session lädt alle 35 Schemata.

Die Harness bietet nativ: Subagenten (Agent-Tool, Fork, Worktree-Isolation),
Mehr-Agenten-Workflows, `/loop`, Plan-Modus, Hooks (Stop/PreToolUse). `/schedule`
(Cloud-Routinen) ist per Owner-Entscheid 2026-07-11 **read-only** und kein Ersatz für
schreibende Läufe.

Randbefund, keine Entscheidung: die Modell-Fallbacks in `orchestrator_mcp/model_registry.py`
und `headless/adapters/claude.py` liegen eine Generation hinter `policies/llm-routing.md`
— betroffen ist nur die Ausführungs-Familie, die niemand pflegt, weil niemand sie ruft.

## 2. Considered Options

| Option | Kern | Urteil |
|---|---|---|
| **A — Aufteilen** ✅ | Orchestrator behält Gedächtnis + Audit; Ausführung/Planung geht an die Harness, deprecated mit Frist | gewählt |
| B — Alles behalten | Status quo | abgelehnt: 35 Schemata/Session, 27 ohne Aufrufer, 30 ohne Test — auf Dauer und lautlos wachsend |
| C — Alles deprecaten | Orchestrator abschalten | abgelehnt: verliert das Gedächtnis-SSoT (pgvector, Zerfall, `claude-policy`-Sync) und den Audit-Ort, die `orchestrator.md` und die Charta (Punkte 9/10) voraussetzen |
| D — Skills zwingen, die 27 zu rufen | Konsum erzeugen | abgelehnt: verankert einen HTTP-Umweg für Dinge, die die Harness besser kann (Subagent statt `delegate_subtask`, Bash statt `run_git`) |

Preis von A: zwei Systeme mit einer Naht — was die Harness ausführt, sieht der
Orchestrator nur, wenn ein Hook oder Skill es zurückmeldet. Diese Naht ist heute nicht
gebaut (0 Konsumenten für `log_action`, `check_gate`, `request_approval`).

## 3. Decision Outcome

### D1 — Der Orchestrator bleibt Autorität für Gedächtnis und Audit

| Domäne | Werkzeuge (16) | Konsument heute |
|---|---|---|
| Gedächtnis | `agent_memory_search`, `agent_memory_upsert`, `agent_memory_context`, `memory_backfill` | 2/4 |
| Audit / Freigabe | `log_action`, `get_audit_log`, `check_gate`, `request_approval` | 0/4 |
| Fehlermuster | `check_recurring_errors`, `find_similar_errors`, `log_error_pattern` | 2/3 |
| Messung / Kosten | `session_stats`, `record_job_measurement`, `estimate_job`, `get_cost_estimate` | 3/4 |
| Benachrichtigung | `discord_notify` | 1/1 |

„Autorität" heißt: neue Funktion in diesen Domänen entsteht im Orchestrator, nicht in
der Harness und nicht in einem Skill-lokalen Speicher.

**Bewusst „Audit", nicht „Gate".** Die heute wirksamen Gates sind PreToolUse-Hooks in
`~/.claude/settings.json` — maschinenlokal, hand-verteilt. `check_gate`/`request_approval`
haben keinen Aufrufer; ein Gate, das nur freiwillige Meldungen sieht, ist ein Audit-Log.
Der Titel „Gate" wird dem Orchestrator **erst verliehen, wenn die Naht gebaut ist**: ein
Stop-/PreToolUse-Hook, der `check_gate` blockierend ruft und in ≥2 Repos nachweislich
feuert, plus ein `log_action`-Konsument. Das ist Bedingung im Kill-Gate (§6), kein
Fallback.

**D1 schützt die Domäne, nicht das einzelne Werkzeug.** Acht der 16 Werkzeuge haben
keinen Konsument; für sie gilt dieselbe Frist wie für D2 — erwarteter Ausgang ist ein
Konsument, sonst geht auch ein D1-Werkzeug aus der Registrierung (die Daten bleiben).

### D2 — Die Ausführungs-/Planungs-Familie wird deprecated

| Familie | Werkzeuge (19) | Ersatz |
|---|---|---|
| Planung / Delegation | `plan_and_execute`, `delegate_subtask`, `agent_plan_task`, `agent_team_status`, `analyze_task`, `get_full_context` | Plan-Modus, Agent-Tool (Fork, Worktree), Workflows |
| Headless / Workflow | `headless_run`, `workflow_list`, `workflow_run`, `workflow_execute`, `run_workflow`, `list_job_types` | interaktiv: Workflows, `/loop`; **unbeaufsichtigt und schreibend: Actions-Cron auf self-hosted Runner + Headless-Bridge als Bibliothek** (ADR-186 OQ4, ADR-075) |
| Kommando-Ausführung | `run_command_safe`, `run_git`, `run_lint`, `run_tests` | Bash-Tool unter Permission-System + PreToolUse-Hooks |
| Prüfung / Review | `deploy_check`, `review_adr`, `cascade_log_response` | Skills (`/adr-review`, `/deploy`), Stop-Hooks |

Der souveräne Nacht-Pfad ist damit **kein** MCP-Werkzeug und **nicht** `/schedule`: der
Actions-Job ruft `orchestrator_mcp.headless` direkt. Das ist der Weg, den ADR-186 OQ4
bereits gewählt hat; `headless_run` als MCP-Einstieg war nie der Nacht-Pfad und hat auch
keinen Aufrufer. ADR-238 wählte die Headless-Bridge als Choke-Point für mutierende
Aktionen — sie bleibt als Bibliothek erhalten. `run_command_safe` war dort die verifizierte
Schwachstelle (Injection, geschlossen in mcp-hub#99); seine Entfernung ist kein
Containment-Verlust.

**Frist: 60 Tage ab Accept, spätestens Kill-Gate 2026-10-31.** Regel: *Ein Tool ohne
Konsument in `skills/` oder `.windsurf/workflows/` nach Ablauf der Frist wird aus der
Registrierung entfernt.* Wer ein D2-Werkzeug braucht, benennt innerhalb der Frist einen
Konsument mit Aufruf im Text — ein Konsument, der nur zum Erhalt geschrieben wird, ist
Option D durch die Hintertür und wird im Review verworfen. Deprecation ist sichtbar: die
Schema-Beschreibung trägt ab Accept `[DEPRECATED ADR-300, Frist 2026-10-31]`, damit auch
Aufrufer außerhalb des Zählers es lesen. Entfernung betrifft die **Registrierung**, nicht
den Code: `headless/` und `agent_team/` bleiben bis zu einer eigenen Entscheidung im Repo.

**Enforcement (🌀 Kanon-Entscheidung braucht Gate).** `platform` führt eine
Konsumenten-Registry (`registry/orchestrator-tools.yaml`: je Tool Domäne D1/D2, Status
`aktiv`/`deprecated`/`entfernt`, Konsumenten als Pfade). Ein CI-Check prüft Grep gegen
Registry (Referenz auf deprecated/unbekanntes Tool = Fund) und Registry gegen Grep
(`aktiv` ohne existierenden Konsument = Fund); `mcp-hub` ersetzt „exactly 35" durch einen
Abgleich mit derselben Datei. Konsumenten außerhalb `platform` (CI-Jobs, `claude-policy`,
Headless-Container) werden in der Registry **deklariert** — der Grep ergänzt die
Deklaration, er ersetzt sie nicht. Start SUGGEST (repo-health-rule-discipline), GATING mit
dem Kill-Gate.

### Amendments

| ADR | Was sich ändert |
|---|---|
| ADR-101 | §9 zählt den Orchestrator mit **3** Tools im 100-Tool-Budget; Ist sind **35** — das Budget ist längst lautlos gesprengt. Befund, kein Verdienst dieses ADR. Ziel nach Kill-Gate ≤16; die Budgetzeile wird nachgezogen. Die Aussage „Orchestrator = Cross-Repo-Orchestrierung" wird auf Gedächtnis + Audit eingeengt. |
| ADR-112 | Gedächtnis-Rolle **bestätigt**. Die `SkillRegistry` im Orchestrator ist nicht mehr Quelle der Skills — seit ADR-280/285 ist `platform/skills/` die einzige Kanonik; ADR-112 sprach das nie aus, dieses ADR tut es. |
| ADR-186 | `headless_run` als MCP-Tool deprecated; die Pipeline bleibt als Bibliothek und wird über den in OQ4 entschiedenen Actions-Cron gerufen. |

ADR-080/086 nennen keines der Tools (Verweis nur auf den Pfad `agent_team/`) — daher
`related`, nicht `amends`. ADR-197 (Client-seitiges Pruning aller MCP-Server) bleibt
offen; seine Ablehnung von „Server-side filtering" (Session-Filter) greift hier nicht,
weil D2 dauerhaft entfernt statt je Session filtert.

---

## 4. Implementation Details

| # | Schritt | Repo | Wann |
|---|---|---|---|
| 1 | Registry anlegen, 35 Tools klassifizieren, 8 Konsumenten eintragen; CI-Zähler SUGGEST | platform | mit Accept |
| 2 | Deprecation-Präfix in 19 Schemata; Dispatch-Test → Registry-Abgleich | mcp-hub | mit Accept |
| 3 | Folge-PR `policies/orchestrator.md`: Rolle = Gedächtnis + Audit; „Headless = main consumer" streichen; Registry verlinken | Policy-Kanon | nach Accept |
| 4 | Naht bauen: `check_gate`-Hook (blockierend) + `log_action`-Konsument; D1-Werkzeuge ohne Aufrufer: Konsument oder Registry-Eintrag mit Grund | platform | bis 2026-10-31 |
| 5 | Kill-Gate: Frist prüfen, Tools ohne Konsument entfernen, Zähler GATING | mcp-hub + platform | 2026-10-31 |

## 5. Was dieses ADR NICHT entscheidet

- **Keine Änderung an `policies/orchestrator.md` selbst** — Folge-PR nach Accept (§4 #3).
- **Kein Abbau des Dienstes**: Transport (ADR-224/256), Deployment, Schlüssel-Rotation,
  `claude-policy`-Sync bleiben. Der Dienst wird schmaler, nicht abgeschaltet.
- **Keine Aussage über dev-hub-Apps**; rufen sie MCP-Tools, sind sie zu deklarieren.
- **Keine Entscheidung über die Modell-IDs** (§1 Randbefund) und **kein Löschen von Code**
  unter `headless/` oder `agent_team/`.
- **Keine Entscheidung über ADR-197.**

## 6. Risks und Kill-Gate

| # | Risiko | Mitigation |
|---|---|---|
| R1 | Am Kill-Gate wird ein `headless_run`-Konsument „gerettet", weil der Nacht-Pfad nicht verstanden ist | Nacht-Pfad steht in D2 ausdrücklich (Actions-Cron + Bibliothek); Review liest Konsumenten, nicht nur den Zähler |
| R2 | D2 höhlt D1 aus: ohne Naht sieht der Audit-Ort nur freiwillige Meldungen; der Folge-PR schriebe „Orchestrator = Gate" als Behauptung fest | „Gate" wird erst mit gebauter, feuernder Naht verliehen (D1); bis dahin heißt die Rolle Audit |
| R3 | Zähler grün, weil Konsumenten außerhalb `platform` undeklariert sind | Deklarationspflicht; Deprecation-Präfix erreicht auch undeklarierte Aufrufer |

**Kill-Gate 2026-10-31.** Verworfen wird das ADR, wenn seine Begründung widerlegt ist,
nicht wenn etwas nicht umgesetzt wurde:

1. Haben ≥3 der 19 D2-Werkzeuge echte (nicht rettende) Konsumenten bekommen, war „die
   Harness hat sie eingeholt" falsch → D2 auf die tatsächlich ersetzbaren einengen.
2. **Bedingung Gate-Titel:** Ist die Naht (blockierender `check_gate`-Hook in ≥2 Repos +
   `log_action`-Konsument) nicht gebaut, bleibt D1 bei „Gedächtnis + Audit"; der
   Folge-PR darf „Gate" dann nicht schreiben.
3. Sonst: Kill-Gate bestanden — Zähler GATING, deprecated-Tools aus der Registrierung,
   jede Session lädt ≤16 Orchestrator-Schemata.

## 7. More Information

platform#2606 (Audit, E2) · platform#2642 (Entwurf, /adr-challenger-Review) ·
`policies/orchestrator.md`, `adr-threshold.md` (kehrt akzeptierte Entscheidungen um,
cross-cutting, Perimeter → ADR-pflichtig) · Agent-Memory-Store (`orchestrator_mcp/memory/`).

## 8. Changelog

| Datum | Version | Änderung |
|---|---|---|
| 2026-09-02 | 0.1 | Entwurf (proposed), vorgeschlagen von Claude Code; Anker platform#2606 E2 |
| 2026-09-02 | 0.2 | Nach /adr-challenger: D1 = Gedächtnis + Audit (Gate an Naht gebunden), Nacht-Pfad = Actions-Cron + Bibliothek, ADR-101-Budget 3→35 als Befund, ADR-080/086 → related, R3 nach ADR-238 umgekehrt, D3 → Enforcement-Absatz, 412 → ≤220 Zeilen |
| 2026-09-02 | 1.0 | **accepted** — Freigabe durch Owner im Kapitäns-Kanal („ADR-300 accept"). Umsetzung D2/Enforcement/Modell-IDs: mcp-hub#244 (Kill-Gate 2026-11-01); Policy `policies/orchestrator.md` im Folge-PR nachgezogen |
