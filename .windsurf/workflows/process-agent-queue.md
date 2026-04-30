---
description: Auto-Issues über Nacht abarbeiten — Queue-Prozessor für labels:auto Issues (Wave 3, Optimierung 2)
---

# /process-agent-queue — Auto-Issue Queue Processor

> **Zweck:** Die Ernte der Auto-Issues. Arbeitet Issues mit Label `auto` systematisch ab —
> über Nacht, mit Budget-Cap, ohne Human-Trigger pro Task.
> **Baut auf:** `/agentic-coding` v6 (Router + Downgrade) + `/session-start` Phase 2.5 (Learning).

---

## Voraussetzungen

- `mcp2_agent_memory` erreichbar (pgvector Tunnel aktiv)
- `mcp1_list_issues` / `create_issue` verfügbar (GitHub MCP)
- GROQ_API_KEY oder OPENAI_API_KEY in `~/.secrets/` für autonome LLM-Calls
- Genug Budget für geplante Operationen (`mcp2_session_stats` prüfen)

---

## Phase 0: Pre-Flight — Budget + Health

```bash
export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
PLATFORM_DIR="${GITHUB_DIR}/platform"
DATE=$(date +%Y-%m-%d)
LOG="/tmp/agent-queue-${DATE}.log"

echo "╔══════════════════════════════════════════╗"
echo "║  🤖 AGENT QUEUE PROCESSOR                ║"
echo "║  $(date '+%Y-%m-%d %H:%M')                       ║"
echo "╚══════════════════════════════════════════╝"
```

**Budget-Check:**
```
MCP: <orc>_session_stats(days=1)
→ Wenn today_spend_usd > 0.80 * daily_budget → Queue skippen, User benachrichtigen
```

**Health-Check:**
```
MCP: <orc>_deploy_check(action="health")
→ Wenn > 1 Service rot → Queue NICHT starten (Infrastruktur-Fix hat Priorität)
```

---

## Phase 1: Queue befüllen

### 1.1 Issues mit `auto`-Labels abholen (alle Repos)

```
# Platform-Issues (adr-candidates aus Session-Start Phase 2.5)
<gh>_list_issues(
    owner="achimdehnert", repo="platform",
    labels=["auto-detected"],
    state="open"
)

# Refactoring-Flags aus allen aktiven Repos (von /agentic-coding Step 3.5 D)
for repo in risk-hub bfagent weltenhub tax-hub coach-hub ...:
    <gh>_list_issues(
        owner="achimdehnert", repo=<repo>,
        labels=["refactor", "auto"],
        state="open"
    )
```

→ **Aggregierte Queue** = alle offenen Auto-Issues, dedupliziert nach (repo, issue_number).

### 1.2 Filtern

**Überspringen wenn:**
- Issue hat Assignee (Mensch arbeitet schon dran)
- Issue hat Label `blocked` oder `wont-fix`
- Issue älter als 30 Tage (stale — User soll entscheiden)
- Issue enthält `[blocker]` oder `[needs-human]` im Titel

### 1.3 Sortierung: Complexity ASC

Pro Issue einmalig:

```
MCP: <orc>_analyze_task(description=issue.body)
→ complexity ∈ {trivial, simple, moderate, complex, architectural}
```

**Sortier-Reihenfolge:**
1. `trivial` (gpt_low, ~$0.001) — zuerst abarbeiten
2. `simple` (gpt_low)
3. `moderate` (swe, ~$0.003)
4. `complex` (opus, ~$0.015) — zuletzt
5. `architectural` → **NICHT auto-verarbeiten**, Eskalation an User

**Ausschluss-Guards** (nie auto-verarbeiten, egal welche complexity):
- `task_type ∈ {infra, deployment, breaking_change}` → Gate 3+
- `complexity == architectural` → Gate 2+, Human-Review nötig
- `task_type == security` → always human

---

## Phase 2: Worker-Loop

Pro Issue in der sortierten Queue:

### 2.1 Budget-Check vor jedem Task

```
MCP: <orc>_session_stats(days=1)
if today_spend_usd + estimated_cost > daily_budget * 0.95:
    echo "💰 Budget-Limit erreicht — stoppe Queue"
    break
```

### 2.2 Auto-Dispatch (nutzt Router aus /agentic-coding v6)

```
# Siehe /agentic-coding v6 "Auto-Dispatch Router"
if gate_level <= 1 and complexity in {trivial, simple}:
    # Pfad A: Fully-Autonomous
    result = <orc>_run_workflow(
        task_description=issue.body,
        task_type=<from analyze>,
        complexity=<from analyze>,
        affected_paths=<from issue body "Betroffene Komponenten">,
        acceptance_criteria=<from issue body "Akzeptanzkriterien">
    )
elif gate_level == 2:
    # Pfad B: Semi-Agentic → skippen, markieren für nächste manuelle Session
    <gh>_add_issue_comment(
        owner, repo, issue_number,
        body="⏸️  Queue-Processor: Gate 2 benötigt Cascade als Tech Lead. "
             "Beim nächsten `/agentic-coding` Run wird dieses Issue aufgegriffen."
    )
    continue
else:  # gate >= 3
    # Pfad C: Human-First → nur Notify
    <gh>_add_issue_comment(
        owner, repo, issue_number,
        body="⚠️  Queue-Processor: Gate 3+ (deploy/security/breaking) — "
             "Human-Approval erforderlich. Task übersprungen."
    )
    continue
```

### 2.3 Ergebnis-Protokoll

Pro Issue ins Log:

```
[2026-04-30 03:15] risk-hub#42 [refactor] JSONField(audit_log) → complexity=trivial
  Model: gpt_low | Cost: $0.0012 | Duration: 42s
  Result: ✅ PR #188 created — tests green, ruff clean
  
[2026-04-30 03:16] risk-hub#47 [refactor] template 52 lines missing data-testid → complexity=simple
  Model: gpt_low | Cost: $0.0008 | Duration: 18s  
  Result: ✅ PR #189 created
  
[2026-04-30 03:17] platform#82 [adr-candidate] coroutine JSON → complexity=complex
  Model: opus | Skipped (gate >= 2, marked for manual review)
```

### 2.4 Fail-Handling

**Bei Fail in `run_workflow`:**
- Max 1 Retry mit Model-Downgrade (siehe Cost-Downgrade-Ladder)
- Bei 2× Fail → Issue-Comment mit Fehler-Log + Label `auto-failed`
- **Issue bleibt offen** (kein automatisches Schließen)
- `<orc>_log_error_pattern(...)` für Learning in nächster Session

---

## Phase 3: Zusammenfassung + Discord-Notify

Nach Queue-Ende:

```bash
TOTAL_PROCESSED=<counter>
TOTAL_SUCCESS=<counter>
TOTAL_COST=$(echo "$spend_accumulated" | bc)
REMAINING_QUEUE=<open auto-issues>

echo "═══ Queue Run Summary ═══"
echo "Processed: $TOTAL_PROCESSED"
echo "Success:   $TOTAL_SUCCESS (✅ PRs erstellt)"
echo "Skipped:   $TOTAL_SKIPPED (Gate 2+ oder Guards)"
echo "Failed:    $TOTAL_FAILED"
echo "Cost:      \$${TOTAL_COST}"
echo "Remaining queue: $REMAINING_QUEUE issues"
```

```
MCP: <orc>_discord_notify(
    title="🤖 Agent Queue Run beendet",
    message=f"✅ {success}/{total} erfolgreich | 💰 ${cost} | 📋 {remaining} offen",
    level="success"
)
```

---

## Phase 4: Session-Memory Update

```
MCP: <orc>_agent_memory_upsert(
    entry_key=f"queue-run:{YYYY-MM-DD}",
    entry_type="context",
    title=f"Queue-Run {date}: {success}/{total} PRs",
    content="<Detailliertes Log>",
    tags=["queue-run", "agentic-coding", "automation"]
)
```

---

## Trigger-Optionen

### A) Manuell (sofort)
```bash
/process-agent-queue
```

### B) Cron (empfohlen: nachts)
```bash
# In crontab (dev-desktop oder Hetzner):
# 0 3 * * * cd $HOME/github/platform && windsurf-cli run /process-agent-queue
```

### C) GitHub Actions (Platform-weit)
```yaml
# .github/workflows/agent-queue.yml (in platform repo)
on:
  schedule:
    - cron: '0 3 * * *'  # 3 AM UTC täglich
  workflow_dispatch:       # manuell triggerbar

jobs:
  process-queue:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Agent Queue
        env:
          GITHUB_TOKEN: ${{ secrets.AGENT_BOT_PAT }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: python3 scripts/process_agent_queue.py
```

---

## Sicherheits-Guards

**Nie auto-verarbeiten:**
1. Issues in `main` Branch ohne PR-Review (Repo-Policy)
2. Issues mit Labels `security`, `blocker`, `production-data`, `breaking-change`
3. Issues in Repos mit roten Health-Checks (`<orc>_deploy_check`)
4. Wenn Budget > 90% des Tagesbudgets erreicht
5. Wenn `<orc>_check_recurring_errors` aktive BLOCKER-Patterns meldet (10×+)

**Rollback-Pfad bei Fehler:**
- Agent committed immer auf **Feature-Branch** (nie direkt main)
- PR wird mit `draft: true` erstellt — User muss explizit mergen
- Bei 3+ Consecutive Fails → Queue-Run wird automatisch abgebrochen

---

## Metriken (für spätere Dashboard-Integration)

Pro Run als JSON in `$GITHUB_DIR/platform/metrics/queue-runs/<date>.json`:

```json
{
  "run_id": "2026-04-30-03-00",
  "duration_sec": 2847,
  "processed": 12,
  "success": 9,
  "skipped": 2,
  "failed": 1,
  "cost_usd": 0.047,
  "models_used": {"gpt_low": 10, "swe": 2},
  "prs_created": ["risk-hub#188", "risk-hub#189", "..."],
  "remaining_queue": 23
}
```

→ Langfristig: Dashboard zeigt Throughput, Cost-Trend, Success-Rate.

---

## Referenzen

- `/agentic-coding` v6 — Auto-Dispatch Router + Cost-Downgrade (Wave 1)
- `/session-start` Phase 2.5 — Error-Learning (Wave 2)
- ADR-068 — Agent Team Architecture
- ADR-081 — Scope-Lock (Queue darf nur Issues mit klarem Scope verarbeiten)
- ADR-154 — Memory Store für Run-History
