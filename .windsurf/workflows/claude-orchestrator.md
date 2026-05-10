---
description: Claude Code als Initial-Orchestrator — Plant Tasks BEVOR Windsurf sie anfasst. Verhindert "alles selbst machen"-Pattern.
---

# /claude-orchestrator — Claude als Initial-Orchestrator

> **Problem**: Windsurf/Cascade hat einen "yes-and"-Bias — es handelt sofort, ohne Delegation.
> **Lösung**: Claude Code plant den Task headless, erstellt ein GitHub Issue, Windsurf implementiert NUR aus dem Issue.
>
> **Wann nutzen**: Bei jeder Aufgabe mit `gate_level >= 2` (>5 Dateien, cross-repo, neue Architektur).

---

## Schritt 1 — Cascade: Gate-Check VOR dem Start

**BEVOR Cascade irgendetwas implementiert:**

```
MCP: mcp4_analyze_task(description="<user request>")
→ {task_type, complexity, gate_level, recommended_model}
```

| gate_level | Vorgehen |
|-----------|---------|
| 0–1 (trivial/simple) | Cascade direkt — kein Orchestrator nötig |
| 2 (moderate) | `/agentic-coding` Pfad B — Cascade als Tech Lead |
| **3+ (complex/architectural)** | **Diesen Workflow ausführen** |

---

## Schritt 2 — Claude Code: ADR-Check

```
MCP: mcp2_adr_query(question="<was geplant ist>", domain="<relevant>")
```

- Falls passende ADR: in Issue verlinken
- Falls keine ADR, aber neue Architektur: `mcp2_adr_propose(...)` → Entwurf erstellen
- **Implementierung erst nach ADR-Klärung**

---

## Schritt 3 — Claude Code: Task zerlegen

```
MCP: mcp4_agent_plan_task(
    task_description="<vollständige Beschreibung>",
    repo="<repo-name>",
    task_type="<feature|bugfix|refactor|infra>",
    gate_level=3,
    affected_paths=["<paths>"],
    acceptance_criteria=["<kriterien>"]
)
→ {branches: [{subtask, model_tier, estimate_min, acceptance}]}
```

---

## Schritt 4 — Claude Code: GitHub Issue erstellen

```
MCP: mcp1_create_issue(
    owner="achimdehnert",
    repo="<repo>",
    title="[AUTO] <task_description>",
    labels=["auto", "gate-3", "complexity-<level>"],
    body="""
## Plan (erstellt von Claude Code Initial-Orchestrator)

**Gate Level**: 3
**Complexity**: <level>
**Model Tier**: <tier>
**ADR**: <ADR-NNN oder 'keine nötig'>

## Subtasks
- [ ] <subtask 1> — Modell: <tier>, ~<N> min
- [ ] <subtask 2> — Modell: <tier>, ~<N> min

## Betroffene Dateien
<liste>

## Akzeptanzkriterien
- [ ] <kriterium 1>
- [ ] <kriterium 2>

## Kontext aus pgvector
<mcp4_agent_memory_context(query=task_description).top_3_results>

---
*Auto-erstellt von /claude-orchestrator. Windsurf implementiert NUR aus diesem Issue.*
"""
)
```

---

## Schritt 5 — Windsurf: Implementiert NUR aus dem Issue

Windsurf öffnet das Issue und:
1. Liest Plan und Akzeptanzkriterien
2. Implementiert Subtask für Subtask
3. Hakt ab: `[x] <subtask>` → postet Kommentar
4. Am Ende: alle Kriterien erfüllt → Issue schließen

**VERBOTEN während der Implementierung:**
- Scope über die Issue-Subtasks hinaus ausweiten
- Neue Subtasks hinzufügen ohne Kommentar + User-Bestätigung
- Issue schließen ohne alle `[ ]` als `[x]` zu haben

---

## Schritt 6 — Memory sichern

```
MCP: mcp4_agent_memory_upsert(
    entry_key="task:<repo>:<issue_number>",
    entry_type="context",
    title="[DONE] <issue_title>",
    content="<Was wurde gemacht, welche Entscheidungen, Lerneffekte>",
    tags=["<repo>", "<task_type>", "completed"]
)
```

---

## Warum Claude Code als Orchestrator?

| Eigenschaft | Windsurf/Cascade | Claude Code (Orchestrator) |
|------------|-----------------|--------------------------|
| Bias | "yes-and" — sofort handeln | Analyse-zuerst |
| Kontext | IDE-Session, User-Druck | Headless, kein Zeitdruck |
| Scope-Creep | hoch | niedrig (plant, implementiert nicht) |
| Repo-Zugriff | lokaler Workspace | cross-repo via GitHub API |
| ADR-Awareness | via MCP (reaktiv) | explizit als Pflicht-Schritt |

**Kernprinzip**: Claude Code *plant und delegiert*. Windsurf *implementiert nur*.
Das Issue ist der Vertrag — beide Seiten halten sich daran.
