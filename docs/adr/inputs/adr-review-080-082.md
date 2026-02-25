# ADR-Review: ADR-080 & ADR-082

## Kritischer Architektur-Review für produktionskritischen Code

**Reviewer:** Claude (Opus 4.6) — Rolle: Kritischer ADR-Reviewer  
**Datum:** 2026-02-25  
**Scope:** ADR-080 (Multi-Agent Coding Team Pattern) + ADR-082 (LLM-Tool-Integration)  
**Stack-Kontext:** Django + HTMX + Postgres 16 auf Hetzner VMs via Docker, WSL + MCP

---

## Executive Summary

Beide ADRs sind **architektonisch solide und überdurchschnittlich gut dokumentiert** — mit klarer Problemstellung, nachvollziehbaren Optionen-Bewertungen und expliziten Confirmation-Kriterien. Die Kombination aus ADR-080 (Handoff + Parallelisierung) und ADR-082 (LLM-Execution-Layer) bildet eine kohärente Progression vom strukturierten Framework zum autonomen System.

**Gesamturteil: 7 Befunde, davon 2 kritisch, 3 erheblich, 2 informell.**

Die kritischen Punkte betreffen (1) fehlende Context-Engineering-Strategie im StepExecutor und (2) eine unzureichende Fehlerbehandlung im Tool-Call-Loop. Diese müssen vor Implementierung adressiert werden.

---

## TEIL A: ADR-080 — Multi-Agent Coding Team Pattern

### Befund A1: AgentHandoff-Modell — vorbildlich, aber `context_summary` zu starr

**Befund:** Das `AgentHandoff`-Pydantic-Model ist hervorragend designt — jedes Feld hat klare Semantik, die `to_cascade_instruction()`-Methode macht den Übergang zum LLM-Prompt explizit. Allerdings ist `context_summary: str` mit `≤ 500 Zeichen` ein statisches Feld, das die Context-Qualität künstlich limitiert.

**Risiko:** ERHEBLICH — 500 Zeichen reichen für triviale Tasks, aber bei COMPLEX-Tasks mit mehreren `artifacts_produced` und `decisions_made` geht kritischer Kontext verloren. Google ADK (Dez. 2025) zeigt, dass "Context Engineering" — die gezielte Komprimierung und Schichtung von Kontext — eine Schlüsselkompetenz für Multi-Agent-Systeme ist. Ein statisches Zeichenlimit widerspricht diesem Prinzip.

**Empfehlung:**
- `context_summary` durch ein zweistufiges Modell ersetzen: `summary_short: str` (≤ 500, für Logging/PR-Body) und `context_payload: dict[str, Any]` (strukturierter Vollkontext für den empfangenden Agent)
- Alternative: `context_summary` als computed property, das abhängig von `task.complexity` zwischen kurz (SIMPLE) und ausführlich (COMPLEX/ARCHITECTURAL) skaliert
- Dies fügt sich nahtlos in die bestehende `to_cascade_instruction()`-Methode ein

### Befund A2: Planner-Bypass-Logik — korrekt, aber fehlende Grenzfall-Behandlung

**Befund:** Die Bypass-Bedingung `if task.complexity < TaskComplexity.COMPLEX: return TaskGraph.single_branch(task)` ist sauber. Allerdings fehlt die Behandlung des Falls, wenn `complexity` zur Laufzeit von einem Evaluator hochgestuft wird (z.B. Developer erkennt in Phase 4, dass der Task eigentlich COMPLEX ist).

**Risiko:** MITTEL — Bei einem laufenden Workflow kann der Planner nicht nachträglich aktiviert werden. Der Workflow läuft sequentiell weiter, obwohl Parallelisierung nötig wäre.

**Empfehlung:**
- Explizit im ADR dokumentieren: "Complexity-Upgrade zur Laufzeit triggert Level-2-Rollback (Tech Lead Review) — kein nachträglicher Planner-Eingriff."
- Dies ist kein Architektur-Defizit, sondern eine bewusste Designentscheidung, die nur dokumentiert werden muss.

### Befund A3: Rollback-Leiter — stark, aber Loop-Guard unvollständig

**Befund:** Die 4-stufige Eskalationsleiter ist gut durchdacht. Der "Max 1 Re-Engineer-Retry pro Level" Guard verhindert L1→L2→L1-Loops. Allerdings fehlt ein expliziter Guard gegen L2→L3→L2-Loops (Tech Lead schickt zurück an Human, Human schickt zurück an Tech Lead).

**Risiko:** NIEDRIG — In der Praxis unwahrscheinlich, da L3 Human-in-the-Loop ist und ein Mensch den Loop erkennen würde. Trotzdem sollte die Invariante kodifiziert sein.

**Empfehlung:**
- Globalen `max_escalation_count: int = 3` auf Workflow-Ebene einführen. Jeder Rollback-Level-Wechsel inkrementiert den Counter. Bei Überschreitung → L4 (Task-Abort).
- Bereits im `WorkflowResult` oder `AgentHandoff` tracken: `escalation_history: list[tuple[int, str]]` (Level, Reason).

### Befund A4: MAX_PARALLEL_BRANCHES = 3 — pragmatisch, aber ohne Begründung

**Befund:** Der Wert 3 ist als Entscheidung dokumentiert, aber die Herleitung fehlt. Ist 3 aus Erfahrung, aus Ressourcen-Limits, aus Token-Budget-Überlegungen?

**Risiko:** INFORMELL — Kein technisches Risiko, aber ein ADR-Qualitätsmerkmal: Entscheidungsparameter sollten begründet sein.

**Empfehlung:**
- Einzeiler in §11 ergänzen: "MAX_PARALLEL_BRANCHES = 3 weil (a) typische Feature-Tasks in ≤ 3 unabhängige Sub-Tasks zerfallen, (b) höhere Parallelität Token-Budget pro Run sprengt, (c) Merge-Komplexität superlinear wächst."

---

## TEIL B: ADR-082 — LLM-Tool-Integration Autonomous Coding

### Befund B1 (KRITISCH): StepExecutor — fehlende Context-Engineering-Strategie

**Befund:** Der `StepExecutor.run()`-Ablauf ist:
1. System-Prompt aus `handoff.to_cascade_instruction()`
2. LLM-Call mit Tools
3. Tool-Call-Loop
4. Finales LLM-Call → neuer AgentHandoff

Dieser Ablauf ignoriert ein kritisches Problem: **Context-Window-Management**. Bei einem `max_tool_calls: int = 20` und jedem Tool-Call, der Ergebnisse zurückgibt (File-Inhalte, Git-Diffs, Shell-Output), wächst der Conversation-Context rapide. Ein `read_file` auf eine 500-Zeilen-Datei + ein `git_diff` + ein `search_code` kann den Context schnell auf 50k+ Tokens aufblasen.

Google ADK (Dez. 2025) hat exakt dieses Problem adressiert mit "Context Compaction" — eine Strategie, die nach N Tool-Calls den bisherigen Context komprimiert. Anthropic's eigenes Multi-Agent-Research-System (Feb. 2026) nutzt "compression by design" — Subagents liefern nur komprimierte Ergebnisse an den Lead Agent.

**Risiko:** KRITISCH — Ohne Context-Management:
1. Token-Budget wird schneller als erwartet erreicht (ExecutionBudget greift zu spät)
2. LLM-Qualität degradiert bei langen Kontexten (bekanntes "lost in the middle" Problem)
3. Cost pro Run wird unvorhersehbar

**Empfehlung:**
```python
@dataclass
class StepExecutor:
    # ... bestehende Felder ...
    max_context_tokens: int = 100_000  # Soft-Limit für Context-Größe
    compaction_threshold: int = 15     # Nach N Tool-Calls: Context komprimieren

    def _maybe_compact_context(
        self,
        messages: list[Message],
        tool_call_count: int,
    ) -> list[Message]:
        """Context Compaction nach Google ADK Pattern.

        Komprimiert ältere Tool-Results zu Summaries,
        behält System-Prompt und letzte 3 Tool-Results intakt.
        """
        if tool_call_count < self.compaction_threshold:
            return messages
        # Komprimiere Messages[1:-3] zu Summary via Budget-Tier LLM
        # System-Prompt (messages[0]) bleibt stabil (Cache-freundlich)
        # Letzte 3 Messages bleiben vollständig (Recency)
        ...
```

Zusätzlich: `max_tool_calls=20` sollte an `task.complexity` gekoppelt sein — SIMPLE braucht selten >5, MODERATE selten >12.

### Befund B2 (KRITISCH): Tool-Call-Loop — keine Retry/Error-Recovery

**Befund:** Der `StepExecutor.run()` definiert einen "Tool-Call-Loop" in Schritt 3, aber das ADR spezifiziert nicht, was passiert wenn:
- Ein `FileWriteTool`-Call eine `ScopeViolationError` wirft → Wird der gesamte Step abgebrochen oder bekommt das LLM die Fehlermeldung als Feedback?
- Ein `ShellTool`-Call einen Timeout hat → Retry mit längerem Timeout oder Abort?
- Die LLM-Response malformed ist (kein valider Tool-Call, kein valider AgentHandoff) → Parse-Error-Handling?

**Risiko:** KRITISCH — Ohne definierte Error-Recovery wird der StepExecutor in Production fragil. Jeder der genannten Fälle ist bei autonomem Coding wahrscheinlich (LLMs generieren regelmäßig invalide Tool-Calls).

**Empfehlung:**
```python
class ToolCallErrorStrategy(Enum):
    """Definierte Error-Recovery-Strategien für Tool-Call-Failures."""
    RETRY_WITH_FEEDBACK = "retry"   # Fehlermeldung an LLM zurückgeben, erneut versuchen
    SKIP_AND_CONTINUE = "skip"      # Tool-Call überspringen, nächsten Step
    ABORT_STEP = "abort"            # Step abbrechen → Rollback-Leiter

# Mapping pro Error-Typ
TOOL_ERROR_STRATEGIES: dict[type[Exception], ToolCallErrorStrategy] = {
    ScopeViolationError: ToolCallErrorStrategy.RETRY_WITH_FEEDBACK,  # LLM soll Pfad korrigieren
    TimeoutError: ToolCallErrorStrategy.RETRY_WITH_FEEDBACK,         # mit kürzerem Scope
    PermissionError: ToolCallErrorStrategy.ABORT_STEP,               # Architektur-Fehler → L2
    BudgetExceededError: ToolCallErrorStrategy.ABORT_STEP,           # Hard-Stop
    json.JSONDecodeError: ToolCallErrorStrategy.RETRY_WITH_FEEDBACK, # LLM-Output malformed
}
```

Plus: `max_tool_call_retries: int = 3` pro einzelnem Tool-Call (nicht pro Step). Drei Fehlversuche auf demselben Tool-Call → Step abbrechen.

### Befund B3: LLMClient Provider-Mapping — DynamicLLMClient-Duplikation

**Befund:** ADR-082 §5.4 definiert einen neuen `LLMClient` mit `OpenAIProvider`, `AnthropicProvider`, `OllamaProvider`. Laut Plattform-Architektur existiert bereits das `DynamicLLMClient`-Pattern im `creative-services` Package. ADR-082 erwähnt diese bestehende Infrastruktur nicht.

**Risiko:** ERHEBLICH — Zwei parallele LLM-Client-Abstraktionen in derselben Platform widersprechen Separation of Concern und erzeugen Maintenance-Overhead. Wenn `creative-services` den Provider-Wechsel bereits abstrahiert, sollte `orchestrator_mcp` das nutzen statt neu zu implementieren.

**Empfehlung:**
- Prüfen ob `DynamicLLMClient` aus `creative-services` als Dependency in `orchestrator_mcp` nutzbar ist
- Falls ja: ADR-082 §5.4 ändern zu "LLMClient wraps DynamicLLMClient mit orchestrator-spezifischem Tool-Calling-Interface"
- Falls nein (z.B. wegen Circular Dependencies): explizit im ADR begründen warum eine separate Implementierung nötig ist, und mittelfristig Extraktion in `platform_core` planen

### Befund B4: Shell-Allowlist — zu permissiv für autonome Ausführung

**Befund:** Die Shell-Allowlist enthält `"git add"` und `"git log"`. `git add` ist eine schreibende Operation, die Dateien in den Staging-Bereich bringt. In Kombination mit `git_commit` (das "staged only" Writes macht) kann ein Agent beliebige Dateien committen, die er vorher per `git add` gestaged hat — auch solche außerhalb des ScopeLocks.

**Risiko:** ERHEBLICH — Der ScopeLock greift bei `FileWriteTool`, aber `git add` umgeht diesen Check. Ein Agent könnte eine bereits existierende Datei (die nicht im ScopeLock ist) stagen und committen, ohne dass `FileWriteTool` involviert war.

**Empfehlung:**
- `git add` aus der Shell-Allowlist entfernen
- Stattdessen ein dediziertes `GitStageTool` implementieren, das ScopeLock-validiert:
```python
class GitStageTool(BaseTool):
    """git add mit ScopeLock-Validierung (ADR-082 Fix B4)."""
    is_write_operation = True  # Triggert ScopeLock-Check in ToolRegistry

    def execute(self, args: dict) -> ToolResult:
        path = args["path"]
        # ScopeLock-Check wird von ToolRegistry.execute() erzwungen
        return run_shell(f"git add {shlex.quote(path)}")
```
- `git log` kann in der Allowlist bleiben (read-only)

### Befund B5: Feature-Flag-Loading via `os.getenv()` — kein Validierungs-Layer

**Befund:** Die `AutonomousFeatures` werden direkt aus Environment-Variablen geladen:
```python
developer_implement=os.getenv("AUTONOMOUS_DEVELOPER", "false").lower() == "true"
```
Kein Fehler bei Typos (`"True"`, `"1"`, `"yes"` → alle `False`). Keine Validierung ob die Kombination von Flags sinnvoll ist (z.B. `tech_lead_review=True` ohne `developer_implement=True` macht wenig Sinn).

**Risiko:** MITTEL — Silent Failure bei Konfigurationsfehlern. Ein Ops-Engineer, der `AUTONOMOUS_DEVELOPER=1` setzt, erwartet Aktivierung und bekommt sie nicht.

**Empfehlung:**
```python
def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Strikte Boolean-Parsing mit Fehler bei unbekannten Werten."""
    raw = os.getenv(name, str(default)).lower().strip()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no", ""):
        return False
    raise ValueError(
        f"Invalid boolean for {name}={raw!r}. "
        f"Expected: true/false/1/0/yes/no"
    )

@dataclass(frozen=True)
class AutonomousFeatures:
    developer_implement: bool = False
    re_engineer_root_cause: bool = False
    tech_lead_design: bool = False
    tech_lead_review: bool = False
    planner_llm_decompose: bool = False

    def __post_init__(self) -> None:
        # Invariante: Phase 2 setzt Phase 1 voraus
        if self.tech_lead_design and not self.developer_implement:
            raise ValueError(
                "AUTONOMOUS_TECH_LEAD_DESIGN requires AUTONOMOUS_DEVELOPER=true"
            )
```

---

## TEIL C: Cross-ADR-Analyse (080 + 081 + 082)

### Befund C1: Temporal-Integration nicht berücksichtigt

**Befund:** ADR-079 definiert Temporal als Primary Durable Workflow Engine. ADR-080 und ADR-082 referenzieren ADR-079 nicht. Der `run_workflow()` in `workflows.py` ist aktuell ein synchroner Python-Funktionsaufruf. Weder Handoff-Persistierung noch Budget-Tracking nutzen Temporal.

**Risiko:** MITTEL-LANGFRISTIG — Die aktuelle In-Memory-Workflow-Ausführung ist für Phase 1 akzeptabel. Aber bei parallelen Branches (ADR-080 §5.3) und autonomen Multi-Step-Executions (ADR-082) wird ein Crash mitten im Workflow zum Datenverlust-Problem. Temporal löst genau das.

**Empfehlung:**
- Im "Offene Fragen" oder "Deferred"-Abschnitt von ADR-082 ergänzen: "Phase 2+: `StepExecutor.run()` als Temporal Activity, `run_workflow()` als Temporal Workflow. Handoff-Persistierung via Temporal Signal statt AuditStore-only."
- Dies ist kein Blocker für Phase 1, aber die Architektur sollte die Temporal-Migration nicht verbauen.

### Befund C2: Test-Strategie-Lücke zwischen ADR-080 und ADR-082

**Befund:** ADR-080 fordert "160+ Unit-Tests grün", ADR-082 fordert "173+ bestehende Tests grün" plus 4 neue Test-Module. Allerdings fehlt eine **Integration-Test-Strategie** für den Übergang: Wie wird verifiziert, dass der Feature-Flag-Wechsel von `AUTONOMOUS_DEVELOPER=false` zu `true` unter identischen Bedingungen identische Ergebnisse liefert (abgesehen vom WAITING_APPROVAL-Status)?

**Risiko:** MITTEL — Ohne Parity-Tests zwischen Stub- und Autonomous-Mode können subtile Verhaltensunterschiede unentdeckt bleiben.

**Empfehlung:**
- `test_workflows_parity.py` ergänzen, das für eine definierte Menge von Test-Tasks beide Modi ausführt und die `AgentHandoff`-Outputs vergleicht (abzüglich der erwartbaren Unterschiede wie `status`, `artifacts_produced`, `cost_usd`).

---

## Zusammenfassung der Empfehlungen

| # | ADR | Schwere | Befund | Empfehlung (Kurzform) |
|---|-----|---------|--------|----------------------|
| B1 | 082 | **KRITISCH** | Kein Context-Window-Management im StepExecutor | Context Compaction nach ADK-Pattern einbauen |
| B2 | 082 | **KRITISCH** | Kein Error-Recovery im Tool-Call-Loop | ToolCallErrorStrategy-Enum + Retry-Logik definieren |
| A1 | 080 | ERHEBLICH | `context_summary` zu starr (500 Zeichen) | Zweistufiges Modell: short + payload |
| B3 | 082 | ERHEBLICH | LLMClient dupliziert DynamicLLMClient | Bestehende Infrastruktur aus creative-services prüfen |
| B4 | 082 | ERHEBLICH | `git add` in Shell-Allowlist umgeht ScopeLock | Dediziertes `GitStageTool` mit ScopeLock-Check |
| B5 | 082 | MITTEL | Feature-Flag-Parsing ohne Validierung | Striktes Bool-Parsing + Invarianten-Check |
| A2 | 080 | MITTEL | Kein Complexity-Upgrade zur Laufzeit | Dokumentieren als bewusste Design-Decision |
| A3 | 080 | NIEDRIG | Rollback-Loop-Guard unvollständig | Globaler `max_escalation_count` |
| A4 | 080 | INFO | MAX_PARALLEL_BRANCHES ohne Begründung | Herleitung im ADR ergänzen |
| C1 | 080+082 | MITTEL (deferred) | Temporal-Integration nicht berücksichtigt | Deferred-Notiz ergänzen, Architektur offen halten |
| C2 | 080+082 | MITTEL | Keine Parity-Tests Stub vs. Autonomous | `test_workflows_parity.py` ergänzen |

---

## Abschließende Bewertung

**ADR-080:** Reif für Production. Die Befunde A1–A4 sind Verbesserungen, keine Blocker. Das Handoff-Modell ist industrieweit Best Practice (vergleichbar mit Google ADK Handoff-Semantik, Anthropic Subagent-Pattern). Die Rollback-Leiter ist robuster als was die meisten Open-Source-Frameworks bieten.

**ADR-082:** Status "Proposed" ist korrekt — Befunde B1 und B2 **müssen adressiert werden** bevor der Status auf "Accepted" wechselt. B1 (Context-Engineering) und B2 (Error-Recovery) sind keine optionalen Verbesserungen, sondern strukturelle Voraussetzungen für autonome LLM-Execution. B3 (DynamicLLMClient-Prüfung) und B4 (git add ScopeLock-Bypass) sind erheblich und sollten im nächsten Review-Zyklus gelöst sein.

Die Gesamtarchitektur ADR-066 → 068 → 070 → 080 → 081 → 082 ist eine der solidesten Multi-Agent-Coding-Architekturen, die ich reviewt habe. Die konsequente Nutzung von Pydantic-Modellen, Feature-Flags, und Defense-in-Depth zeigt architektonische Reife.
