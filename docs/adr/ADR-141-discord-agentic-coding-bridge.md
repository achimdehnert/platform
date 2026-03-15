---
status: "draft"
date: 2026-03-13
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-114-discord-ide-like-communication-gateway.md", "ADR-116-dynamic-model-router.md", "ADR-079-temporal-workflow-engine.md", "ADR-080-multi-agent-coding-team-pattern.md", "ADR-081-agent-guardrails-code-safety.md", "ADR-082-llm-tool-integration-autonomous-coding.md", "ADR-045-secrets-management.md", "ADR-120-unified-deployment-pipeline.md"]
implementation_status: not_started
implementation_evidence: []
---

# ADR-141: Discord → Agentic Coding Bridge (Layer 4)

---

## 1. Kontext & Problemstellung

Der Discord Bot (ADR-114) bietet aktuell drei Layer:

| Layer | Commands | Fähigkeit |
|-------|----------|-----------|
| **1 — Ops** | `/task`, `/deploy`, `/approve`, `/reject` | GitHub Issues + Labels, Deploy-Trigger |
| **2 — LLM** | `/chat` | Fragen beantworten via llm_mcp (GPT-4o) |
| **3 — Bridge** | `/ask` | GitHub Issue mit `cascade-task` Label erstellen |

**Layer 3 ist ein Briefkasten, kein Agent.** `/ask` erstellt ein Issue, aber niemand greift es automatisch auf. Ein Mensch muss Windsurf/Cascade öffnen, das Issue lesen und manuell umsetzen.

### Fehlende Fähigkeit

Ein Nutzer soll über Discord eine Coding-Aufgabe beauftragen können, die **automatisch** umgesetzt wird:

```
Discord: /code repo:coach-hub task:"Fix den 500er auf /assessments/"
   → Branch wird erstellt
   → Agent analysiert Code, implementiert Fix
   → Tests laufen
   → PR wird geöffnet
   → Discord-Notification mit PR-Link
```

### Warum nicht Cascade/Windsurf?

Cascade ist eine **IDE-Extension** ohne Remote-API oder Headless-Modus. Es kann nicht programmatisch von außen angesteuert werden. Eine alternative Agent-Architektur ist nötig.

---

## 2. Entscheidungskriterien

- **Autonomie**: Agent muss ohne menschliche Interaktion Code ändern und PR öffnen können
- **Sicherheit**: Keine direkten Prod-Deploys — nur PRs mit Review-Pflicht
- **Kosten**: LLM-Kosten kontrollierbar (ADR-116), kein SaaS-Vendor-Lock-in
- **Integration**: Nahtlos in bestehende Discord-Bot + GitHub-Infrastruktur
- **Qualität**: Ruff, Bandit, Tests müssen vor PR-Erstellung laufen
- **Transparenz**: Jeder Schritt muss im Discord-Thread nachvollziehbar sein

---

## 3. Betrachtete Optionen

### Option A: GitHub Actions + LLM Agent

```
Discord /code → GitHub Issue [auto-code] → Actions Workflow →
   checkout → LLM-Agent (aider) → Branch + PR → Discord Notify
```

- **Pro**: Kein eigener Server nötig, GitHub-native, Audit-Trail
- **Contra**: Runner-Limits (6h), keine persistente Session, teuer bei langen Tasks

### Option B: Self-Hosted Aider auf hetzner-prod

```
Discord /code → API-Call an Agent-Container →
   git clone → Aider CLI → Branch + PR → Discord Notify
```

- **Pro**: Volle Kontrolle, keine Zeitlimits, lokaler Zugriff auf DB/Logs
- **Contra**: Server-Ressourcen (RAM/CPU), Security-Risiko bei Code-Execution

### Option C: Hybrid (Aider auf Server, GitHub Actions für CI)

```
Discord /code → Aider-Container (hetzner-prod) →
   git clone → Aider → push Branch →
   GitHub Actions CI → Aider liest CI-Ergebnis → Fix-Iteration →
   PR öffnen → Discord Notify
```

- **Pro**: Trennung von Code-Generierung und Validierung
- **Contra**: Aider bypassed llm_mcp (ADR-116), keine ScopeLock-Guardrails (ADR-081), kein DB-State, kein AuditStore

### Option D: StepExecutor-Bridge (Platform-native) ✅

```
Discord /code → AgentTaskService (DB) → Celery Task →
   git clone → StepExecutor (ADR-082) + LLMClient (llm_mcp) →
   ScopeLock-Verifier → git push → GitHub Actions CI →
   CI-Feedback-Loop (max. 3x) → PR öffnen → Discord Notify
```

- **Pro**: Nutzt bestehende ADR-080/081/082-Infrastruktur (StepExecutor, ToolRegistry, ScopeLock, AuditStore, RollbackEngine), LLM-Kosten via llm_mcp trackbar, DB-First State
- **Contra**: Höherer initialer Aufwand als Aider-CLI

---

## 4. Entscheidung

**Option D: StepExecutor-Bridge** — Platform-native Agent-Ausführung.

### Begründung

1. **Kein paralleles System**: ADR-080/081/082 definieren StepExecutor, ToolRegistry, ScopeLock, AuditStore und RollbackEngine. Ein externes CLI-Tool (Aider) würde all diese accepted ADRs umgehen.
2. **LLM-Kosten trackbar**: StepExecutor nutzt `LLMClient` → `llm_mcp` → ADR-116 Budget-Tracking. Aider ruft OpenAI/Anthropic direkt auf und umgeht das gesamte Kosten-Controlling.
3. **Guardrails**: ADR-081 `ALWAYS_FORBIDDEN_PATHS` verhindert technisch, dass der Agent `migrations/`, `.env*`, `docker-compose.prod.yml` oder Secrets ändert.
4. **DB-First State**: Jeder Task ist ein `AgentTask`-Record (BigAutoField PK, public_id, tenant_id, deleted_at). Kein ephemerer Container-State.
5. **CI-Pipeline wiederverwendet**: GitHub Actions für CI/CD ist bereits etabliert (ADR-120 Reusable Workflows).
6. **Celery statt Custom-Scheduler**: ADR-079 (Temporal) ist accepted aber `implementation_status: none`. Celery ist bereits im Stack und reicht für sequentielle Agent-Tasks.

### Warum nicht Aider?

Aider ist ein exzellentes CLI-Tool, aber es ist ein **eigenständiges System** mit eigenem Kontextfenster-Management, eigenen LLM-Calls und keiner Anbindung an Platform-Guardrails. Wenn gewünscht, kann Aider als `AiderTool` in die ToolRegistry (ADR-082) eingebettet werden — als ein Tool unter vielen, nicht als Replacement für StepExecutor.

---

## 5. Architektur

### 5.1 Komponenten-Übersicht

```
┌───────────────┐     ┌──────────────────────┐
│  Discord Bot  │────▶│  AgentTaskService     │
│  /code cmd    │     │  (Service-Layer)      │
└───────────────┘     └──────────┬───────────┘
                                  │ create AgentTask (DB)
                                  │ dispatch Celery Task
                                  ▼
                       ┌──────────────────────┐
                       │  Celery Worker        │
                       │  coding_agent_task()  │
                       └──────────┬───────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
   ┌──────────────────┐ ┌─────────────────┐ ┌────────────────┐
   │ GitCloneStep     │ │ StepExecutor    │ │ CIPollingStep  │
   │ (Deploy-Key via  │ │ (ADR-082)       │ │ (GitHub API)   │
   │  ADR-045)        │ │                 │ │                │
   └──────────────────┘ └────────┬────────┘ └────────────────┘
                                  │
              ┌────────────────────┼──────────────────┐
              ▼                    ▼                   ▼
   ┌──────────────────┐  ┌─────────────────┐ ┌───────────────┐
   │ LLMClient        │  │ ToolRegistry    │ │ ExecutionBudget│
   │ (llm_mcp routing │  │ + ScopeLock     │ │ $5 Hard-Stop  │
   │  ADR-116)        │  │ (ADR-081)       │ │ (ADR-116)     │
   └──────────────────┘  └─────────────────┘ └───────────────┘
                                  │
              ┌────────────────────┼──────────────────┐
              ▼                    ▼                   ▼
   ┌──────────────────┐  ┌─────────────────┐ ┌───────────────┐
   │  AgentIteration  │  │  AuditStore     │ │ Discord Thread│
   │  (DB Record)     │  │  (DB)           │ │ (Live-Updates)│
   └──────────────────┘  └─────────────────┘ └───────────────┘
```

### 5.2 Datenmodell (DB-First)

Platform-Standards: `BigAutoField PK`, `public_id UUIDField`, `tenant_id BigIntegerField`, `deleted_at`, `UniqueConstraint`.

#### AgentTask

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | BigAutoField (PK) | Auto-generiert |
| `public_id` | UUIDField (unique, indexed) | Externe Referenz |
| `tenant_id` | BigIntegerField (indexed) | Kein FK — Platform-Standard |
| `repo_name` | CharField(100) | `achimdehnert/<repo>` |
| `task_description` | TextField | Aufgabenbeschreibung |
| `priority` | CharField(10) | `low` / `medium` / `high` |
| `status` | CharField(20, indexed) | `queued` → `running` → `ci_waiting` → `ci_iterating` → `pr_open` / `failed` / `cancelled` |
| `discord_user_id` | CharField(64) | Wer hat den Task ausgelöst |
| `discord_channel_id` | CharField(64) | Quell-Kanal |
| `discord_thread_id` | CharField(64) | Live-Update-Thread |
| `github_issue_number` | IntegerField (nullable) | Zugehöriges Issue |
| `branch_name` | CharField(200) | `ai/agent/<public_id>` |
| `pr_number` | IntegerField (nullable) | Ergebnis-PR |
| `pr_url` | URLField | Link zum PR |
| `iteration_count` | PositiveSmallIntegerField | Aktuelle Iteration |
| `llm_cost_usd` | DecimalField(8,4) | Kumulierte Kosten |
| `error_message` | TextField | Fehlerbeschreibung bei `failed` |
| `celery_task_id` | CharField(200) | Celery Task-ID für Status-Abfrage |
| `deleted_at` | DateTimeField (nullable) | Soft-Delete |
| `created_at` / `updated_at` | DateTimeField | Timestamps |

**Constraint:** `UniqueConstraint(fields=["repo_name", "branch_name"], condition=Q(deleted_at__isnull=True) & ~Q(branch_name=""), name="uq_agent_task_repo_branch_active")`

#### AgentIteration

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | BigAutoField (PK) | Auto-generiert |
| `public_id` | UUIDField (unique) | Externe Referenz |
| `tenant_id` | BigIntegerField (indexed) | Kein FK |
| `task` | ForeignKey(AgentTask) | Zugehöriger Task |
| `iteration_number` | PositiveSmallIntegerField | 1, 2, oder 3 |
| `ci_run_id` | CharField(64) | GitHub Actions Run-ID |
| `ci_status` | CharField(20) | `pending` / `success` / `failure` / `timeout` |
| `ci_failure_log` | TextField | Extrahierter Fehler |
| `llm_prompt_tokens` | IntegerField | Token-Verbrauch |
| `llm_completion_tokens` | IntegerField | Token-Verbrauch |
| `llm_cost_usd` | DecimalField(8,4) | Kosten dieser Iteration |
| `deleted_at` | DateTimeField (nullable) | Soft-Delete |
| `created_at` / `updated_at` | DateTimeField | Timestamps |

**Constraint:** `UniqueConstraint(fields=["task", "iteration_number"], name="uq_agent_iteration_task_number")`

### 5.3 Discord Command

```
/code repo:<repo-name> task:<beschreibung> [priority:low|medium|high]
```

**Flow:**
1. Bot validiert Repo gegen Allowlist + prüft Discord-Rolle `developer`
2. `AgentTaskService.create_task()` erstellt DB-Record (Status: `queued`)
3. GitHub Issue erstellt mit Label `[auto-code]`
4. Discord-Thread für Live-Updates erstellt
5. Celery-Task `coding_agent_task.delay(task_public_id)` dispatched
6. Worker: `git clone` → Branch `ai/agent/<public_id>`
7. Worker: StepExecutor (ADR-082) → LLMClient (llm_mcp) → Code implementieren
8. Worker: `AgentScopeGuard.verify_changed_files()` — ALWAYS_FORBIDDEN_PATHS prüfen
9. Worker: `git push` → GitHub Actions CI abwarten (Polling mit Backoff, max. 10 Min)
10. Bei CI-Failure + iteration < 3: AgentIteration-Record → StepExecutor mit CI-Fehler-Kontext → zurück zu 7
11. Bei CI-Success: PR öffnen → `AgentTaskService.mark_pr_open()`
12. Discord-Thread: PR-Link + Zusammenfassung + Kosten posten
13. Bei 3x CI-Failure: `AgentTaskService.mark_failed()` → Discord-Notification

### 5.4 Sicherheits-Gates

| Gate | Mechanismus | ADR-Referenz |
|------|-------------|--------------|
| **Repo-Allowlist** | `ALLOWED_REPOS: frozenset` im Service-Layer (später DB-Config) | — |
| **Branch-Protection** | `main` ist geschützt — Agent pusht nur `ai/agent/<id>` | ADR-081 |
| **ScopeLock** | `ALWAYS_FORBIDDEN_PATHS`: `*/migrations/*.py`, `.env*`, `docker-compose.prod.yml`, `*.pem/.key/.crt`, `.github/workflows/*.yml`, `Dockerfile*` | ADR-081 |
| **ExecutionBudget** | Hard-Stop bei $5 LLM-Kosten pro Task — `BudgetExceededError` vor jedem LLM-Call | ADR-116 |
| **Kein Deploy** | Agent hat kein SSH zu Prod, kein Deploy-Recht | ADR-120 |
| **Review-Pflicht** | PRs benötigen manuelles Approval vor Merge | GitHub Branch Rules |
| **Discord-Rolle** | Nur `@developer` Rolle kann `/code` nutzen | ADR-114 Guards |
| **Audit-Log** | Jeder Agent-Run als `AgentTask` + `AgentIteration` in DB, zusätzlich `#audit-log` Discord-Channel | ADR-082 AuditStore |
| **Idempotenz** | `UniqueConstraint` auf `(repo_name, branch_name)` verhindert doppelte Tasks | Platform-Standard |

### 5.5 LLM-Routing

**Alle LLM-Calls gehen über `llm_mcp` (ADR-116)** — kein direkter API-Zugriff:

```
StepExecutor → LLMClient → POST llm_mcp/v1/chat
   → llm_calls-Tabelle (Kosten-Tracking, Grafana Dashboard)
   → Budget-Guard (RuleBasedBudgetRouter, ADR-116)
   → OpenRouter → GPT-4o / Claude 3.5 Sonnet
```

### 5.6 Kontext-Injection

Der Agent bekommt automatisch Kontext:
- `platform-context` MCP: ADR-Regeln, Banned Patterns, Architektur-Facts
- Repo-spezifische `CORE_CONTEXT.md` und `AGENT_HANDOVER.md`
- Letzte 5 Commits auf `main` (für Kontext)
- Aktuelle CI-Status
- `AgentIteration.ci_failure_log` bei Fix-Iterationen

### 5.7 Server-Ressourcen

hetzner-prod (88.198.191.108): 22 GB RAM, 8 vCPU, 150 GB Disk.
Aktuell: ~89 Container, ~10 GB RAM belegt, 35 GB Disk frei.

| Aspekt | Limit | Begründung |
|--------|-------|------------|
| **Container RAM** | 2 GB (`mem_limit`) | Git-Clone + StepExecutor + LLM-Context |
| **Container CPU** | 2 CPU (`cpus`) | Parallelität zu anderen Services |
| **Workspace** | `/opt/agent-workspaces/<task-id>/` | Nicht `/tmp/` — überlebt Reboot, dediziertes Volume |
| **Disk-Quota** | Max. 2 GB pro Workspace, Cleanup nach Task-Ende | Root-Partition schützen |
| **Parallelität** | 1 Task pro Repo (Celery-Mutex via Repo-Name) | Keine Branch-Konflikte |

---

## 6. Implementierungs-Plan

| Phase | Inhalt | Dateipfade (mcp-hub) | Aufwand |
|-------|--------|---------------------|---------|
| **0** | ADR-141 finalisieren (dieses Dokument) | `platform/docs/adr/` | 1h |
| **1** | Django-Modelle: `AgentTask`, `AgentIteration` + Migration | `models/agent_task.py`, `models/agent_iteration.py` | 2h |
| **2** | Service-Layer: `AgentTaskService` (create, mark_failed, mark_pr_open) | `services/agent_task_service.py` | 2h |
| **3** | Discord `/code` Command + Guards | `discord/handlers.py` (erweitern) | 1h |
| **4** | `AgentScopeGuard` (ADR-081 ALWAYS_FORBIDDEN_PATHS) | `services/agent_scope_guard.py` | 1h |
| **5** | Celery-Task: `coding_agent_task` mit StepExecutor-Bridge | `tasks/coding_agent_task.py` | 3h |
| **6** | CI-Polling: GitHub Actions API + Exponential Backoff | `services/ci_polling_service.py` | 1h |
| **7** | PR-Erstellung + Discord Live-Updates (Thread) | `services/github_pr_service.py`, `discord/notify.py` | 2h |
| **8** | ExecutionBudget Hard-Stop ($5) via llm_mcp | Erweiterung `coding_agent_task.py` | 1h |
| **9** | Shell-Skript mit `set -euo pipefail` für Git-Ops | `scripts/agent_git_ops.sh` | 1h |
| **10** | Secret-Management: Deploy-Keys via `read_secret()` (ADR-045) | `config/secrets.py` Erweiterung | 1h |
| **11** | i18n: `_()` in allen Models, Services, Discord-Messages | Alle neuen Dateien | 1h |
| **12** | Tests: pytest-Suite für AgentTask, ScopeGuard, Service | `tests/test_agent_*.py` | 2h |

**Gesamt: ~19h über 3-4 Sessions.**

### Pilot-Repos

Start mit `coach-hub` und `risk-hub` — beide haben gute Test-Coverage als CI-Gate.

---

## 7. Offene Fragen

| Frage | Empfehlung | Status |
|-------|-----------|--------|
| Temporal oder Celery? | **Celery** — ADR-079 ist accepted aber nicht implementiert. Celery reicht für sequentielle Tasks. Migration zu Temporal wenn ADR-079 implementiert wird. | Entschieden |
| Parallele Tasks? | 1 pro Repo (Celery-Mutex via Repo-Name). Keine Branch-Konflikte. | Entschieden |
| LLM-Modell für Coding? | Claude 3.5 Sonnet oder GPT-4o — Routing via llm_mcp konfigurierbar (ADR-116). | Offen |
| Allowlist in DB oder Code? | Initial als `frozenset` im Code, Migration zu DB-Config in Phase 2+. | Entschieden |
| Welche Repos zuerst? | `coach-hub` + `risk-hub` als Piloten. | Entschieden |
| Aider als Fallback-Tool? | Optional: `AiderTool` als Wrapper in ToolRegistry, ScopeLock greift trotzdem. Nicht als Primär-Engine. | Offen |

---

## 8. Abgrenzung

- **Kein Ersatz für Cascade/Windsurf** — komplexe, architektonische Tasks bleiben in der IDE
- **Kein Auto-Merge** — PRs werden immer manuell reviewed
- **Kein Prod-Zugriff** — Agent arbeitet nur mit Git, nie mit laufenden Containern
- **Scope Phase 1: Bugfixes + kleine Features** — keine Multi-File-Refactorings
- **Kein neues Workflow-System** — Celery-Task, kein Custom-Scheduler
- **Kein externer CLI-Agent** — StepExecutor (ADR-082) ist die Execution-Engine

---

## 9. Review-Referenz

Vollständiger Review mit 19 Befunden und produktionsreifem Code:
→ `docs/adr/reviews/ADR-141-review.md`
