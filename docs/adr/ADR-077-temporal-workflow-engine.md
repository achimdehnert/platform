---
status: proposed
date: 2026-02-23
decision-makers: Achim Dehnert
consulted: –
informed: –
---

# ADR-077: Adopt Temporal Self-Hosted as Primary Durable Workflow Engine

## Metadaten

| Attribut          | Wert                                                                              |
|-------------------|-----------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                          |
| **Scope**         | platform                                                                          |
| **Erstellt**      | 2026-02-23                                                                        |
| **Autor**         | Achim Dehnert                                                                     |
| **Reviewer**      | –                                                                                 |
| **Supersedes**    | –                                                                                 |
| **Superseded by** | –                                                                                 |
| **Relates to**    | ADR-068 (Adaptive Model Routing), ADR-066 (AI Engineering Squad + Gate-Mechanismus), ADR-059 (ADR Drift Detection), ADR-075 (Deployment Execution Strategy) |

## Repo-Zugehörigkeit

| Repo           | Rolle    | Betroffene Pfade / Komponenten                                                          |
|----------------|----------|-----------------------------------------------------------------------------------------|
| `platform`     | Referenz | `docs/adr/`, `governance-deploy/docker-compose.yml`                                    |
| `bfagent`      | Primär   | `apps/bfagent/tasks.py`, `apps/bfagent/agents/orchestrator.py`, `docker-compose.prod.yml` |
| `mcp-hub`      | Primär   | `orchestrator_mcp/agent_team/workflows.py`, `orchestrator_mcp/agent_team/models.py`    |
| `deploy-hub`   | Sekundär | `.github/workflows/`, `scripts/deploy-remote.sh`                                       |
| `dev-hub`      | Sekundär | `apps/catalog/` (Workflow-Monitoring-Integration)                                       |

---

## Decision Drivers

- **AI-driven Development als Normalzustand**: Cascade und andere Agents führen gleichzeitig 50–200 Micro-Workflows pro Arbeitstag aus. Die bisherige Celery-only-Architektur hat keine Durability über Session-Grenzen.
- **Kontext-Verlust bei Agent-Sessions**: Wenn eine Cascade-Session endet, ist der Workflow-Kontext verloren. Kein Replay-Mechanismus, kein Checkpoint-Restore, keine History.
- **Human-in-the-Loop Gates (ADR-066)**: Gate 2+ erfordert Pause/Resume-Semantik. Celery hat keinen nativen Mechanismus — nur Polling-Workarounds.
- **Cross-System-Workflows ohne Atomizität**: `bfagent → mcp-hub → deploy-hub`-Flows existieren implizit, sind aber nicht atomar, nicht beobachtbar und nicht kompensierbar bei Fehlern.
- **N8n als Afterthought**: `trigger_n8n_webhook()` in `tasks.py` ist fire-and-forget ohne State-Sync zurück. N8n auf Hostinger (`n8n.srv1154685.hstgr.cloud`) ist extern und nicht in die Platform-Infrastruktur integriert.
- **Drei konkurrierende Workflow-Konzepte**: `Pipeline` (bfagent/orchestrator.py), `WorkflowExecution` (mcp-hub/workflows.py), Celery Tasks (bfagent/tasks.py) — drei Implementierungen desselben Konzepts ohne gemeinsame Sprache.

---

## 1. Context and Problem Statement

Die Platform betreibt heute drei strukturell inkompatible Workflow-Systeme, die denselben konzeptuellen Bedarf abdecken, aber keines davon vollständig erfüllt.

**bfagent** hat eine `Pipeline`-Klasse (`orchestrator.py`) mit immutable `AgentState`, Parallel-Execution und Conditional Branching — aber ohne Persistenz. Celery Tasks (`tasks.py`) führen lang laufende Operationen aus (`process_requirement_task`, `execute_delegated_task`, `auto_illustrate_chapter_task`) — aber mit Redis als Result-Backend (`CELERY_RESULT_EXPIRES = 3600`), d.h. State verfällt nach einer Stunde. N8n (Hostinger: `n8n.srv1154685.hstgr.cloud`) wird als optionaler Webhook-Trigger genutzt (`trigger_n8n_webhook`) ohne Callback-Mechanismus.

**mcp-hub** hat `WorkflowExecution` mit `TaskStatus`-Enum (8 States: CREATED → ASSIGNED → IN_PROGRESS → TESTING → IN_REVIEW → DONE / BLOCKED / FAILED) und Funktionen `advance_workflow`, `request_changes` — aber vollständig in-memory, kein persistierter State über Session-Grenzen.

**deploy-hub** nutzt GitHub Actions als Workflow-Engine für CI/CD — das ist korrekt und bleibt unverändert.

### 1.1 Ist-Zustand

```
bfagent (Requirement erstellt)
    → Celery: process_requirement_task()
        → analyze_requirement()     [sync, in-process]
        → work_on_requirement()     [LLM-Call, bis 30min]
        → trigger_n8n_webhook()     [fire-and-forget, kein Callback]
    → State: Redis, verfällt nach 1h (CELERY_RESULT_EXPIRES=3600)
    → Bei Worker-Crash: State verloren, kein Checkpoint-Retry

mcp-hub (Agent-Team-Workflow)
    → WorkflowExecution             [in-memory Python-Objekt]
        → advance_workflow()
        → request_changes()
    → State: verloren bei Session-Ende
    → Kein Audit-Trail, keine History

Cross-System (implizit, nicht dokumentiert):
    bfagent → [HTTP] → mcphub-api:8080 → mcp-hub
    bfagent → [Webhook] → N8n (Hostinger) → ???
    GitHub Push → GitHub Actions → deploy-hub → Hetzner
```

### 1.2 Warum jetzt

Drei Faktoren konvergieren: (1) AI-Agents als primäre Entwickler — Session-Grenzen sind häufig, Kontext-Verlust ist strukturell. (2) Gate-Mechanismus (ADR-066) wird in ADR-068 Phase 6 implementiert — ohne Pause/Resume ist Gate 2+ nicht realisierbar. (3) Cross-System-Flows wachsen mit coach-hub und weiteren Repos.

---

## 2. Considered Options

### Option A: Temporal Self-Hosted als primäre Workflow-Engine ✅

Temporal ist ein Open-Source Durable Execution System (ursprünglich von Uber/Cadence-Team entwickelt). Workflows sind Python-Funktionen die transparent persistiert, replayed und über System-Grenzen koordiniert werden. Der Temporal-Server verwaltet Workflow-State in PostgreSQL. Worker sind Python-Prozesse die Activities ausführen.

**Kernkonzepte:**
- **Workflow**: Deterministische Python-Funktion, die den Ablauf definiert. Wird bei Crash automatisch replayed.
- **Activity**: Nicht-deterministischer Code (I/O, LLM-Calls, HTTP). Wird mit Retry-Policy ausgeführt.
- **Signal**: Externer Event der einen laufenden Workflow beeinflusst (z.B. Gate-Approval, N8n-Callback).
- **Query**: Synchrone Abfrage des aktuellen Workflow-State ohne Seiteneffekte.
- **Task Queue**: Kanal zwischen Temporal-Server und Worker-Prozessen. Je Repo eine Queue.

**Pros:**
- Durable Execution: Workflow-State überlebt Worker-Crash, Server-Restart, Code-Deploy
- Replay: Vollständiger Execution-History-Stack — Time-Travel-Debugging
- Signals: Externer Trigger (N8n Callback, GitHub Webhook, Mensch) kann laufenden Workflow fortsetzen
- Pause/Resume: `workflow.wait_condition()` — nativer Gate-Mechanismus ohne Polling
- Cross-System: Activities laufen in verschiedenen Repos, Workflow koordiniert sie atomar
- Versioning: `workflow.patched()` — laufende Workflows brechen nicht bei Code-Deploy
- Self-hosted: PostgreSQL als Backend — keine externe Abhängigkeit, keine Cloud-Kosten
- Python-SDK: `temporalio>=1.7` — idiomatisches async Python

**Cons:**
- Neue Infrastruktur: Temporal-Server als zusätzlicher Docker-Stack (~512MB RAM)
- Determinismus-Anforderung: Kein `datetime.now()`, kein `random`, kein I/O direkt im Workflow-Code
- Migration: Bestehende Celery-Tasks müssen schrittweise in Activities umgewandelt werden

### Option B: Celery Canvas als Workflow-Engine

**Pros:**
- Keine neue Dependency — Celery 5.5.3 läuft bereits in bfagent
- Django-native, bekannte Patterns, kein Onboarding-Aufwand
- `chain()`, `group()`, `chord()` decken einfache sequentielle und parallele Flows ab

**Cons:**
- Kein Pause/Resume → Gate-Mechanismus (ADR-066) nicht realisierbar ohne Polling-Workaround
- State in Redis, verfällt nach 1h (`CELERY_RESULT_EXPIRES=3600`) → keine Durability
- Kein Replay → kein Time-Travel-Debugging, kein Checkpoint-Restore bei Crash
- `chord` schlägt komplett fehl wenn ein Task in der `group` fehlschlägt — kein partielles Rollback
- Kein Workflow-Versioning → laufende Workflows brechen bei Code-Deploy
- **Abgelehnt weil:** Alle sechs nicht-verhandelbaren Anforderungen (Durability, Human-Gate, Cross-System, Replay, Versioning, Observability) sind strukturell nicht erfüllbar — nur durch wachsende Workaround-Schichten

### Option C: Prefect Self-Hosted

**Pros:**
- Python-native `@flow` + `@task` Dekoratoren — minimale Code-Änderung gegenüber bestehendem Code
- Gute UI out-of-the-box, aktive Community
- Self-hosted möglich (Prefect Server + SQLite/PostgreSQL)

**Cons:**
- Cloud-Bias: Prefect Cloud ist der primäre Use Case, Self-hosted ist Second-Class (weniger Features, schlechtere Docs)
- Kein nativer Signal-Mechanismus für Human-in-the-Loop — externe Events können laufende Flows nicht direkt beeinflussen
- Schwächere Durability-Garantien: Prefect replayed nicht vollständig — bei Crash wird der Flow neu gestartet, nicht fortgesetzt
- Keine native Cross-System-Koordination über mehrere Worker-Pools hinweg
- **Abgelehnt weil:** Fehlender Signal-Mechanismus macht Gate 2+ (ADR-066) nicht realisierbar; schwächere Durability ist für AI-Agent-Sessions nicht akzeptabel

### Option D: Django-FSM + Celery (Hybrid)

**Pros:**
- State in PostgreSQL via Django-Migrations — persistent, kein Redis-Verfall
- Kein neues Framework — Django-FSM ist ein kleines, gut getestetes Package
- Explizite State-Transitions mit Guards — gut lesbar für einfache Model-States

**Cons:**
- Kein Cross-System-Support — FSM-State ist an ein Django-Model gebunden, nicht über Repos hinweg
- Saga-Compensation manuell implementieren → fehleranfällig, kein Framework-Support
- Kein Replay, kein Time-Travel-Debugging
- Drei Frameworks statt zwei (Django + Django-FSM + Celery) — höhere Komplexität
- **Abgelehnt weil:** Löst Durability + Cross-System + Human-Gate nicht vollständig; Django-FSM wird bewusst nicht eingeführt (einfache Model-States bleiben `CharField` mit `choices`)

---

## 3. Decision Outcome

**Gewählte Option: Option A — Temporal Self-Hosted auf dev-server (46.225.113.1)**

Temporal ist die einzige Option die alle sechs nicht-verhandelbaren Anforderungen strukturell erfüllt: Durability, Observability, Human-in-the-Loop, Retry-Semantics, Cross-System-Atomizität, Workflow-Versioning. Option B (Celery Canvas) scheidet aus, weil Pause/Resume und Replay fundamentale Architektur-Lücken sind — nicht durch Workarounds schließbar. Option C (Prefect) scheitert am fehlenden Signal-Mechanismus: externe Events können laufende Flows nicht direkt beeinflussen, was Gate 2+ (ADR-066) strukturell unmöglich macht. Option D (Django-FSM) ist auf einzelne Django-Models beschränkt und skaliert nicht auf Cross-Repo-Flows. Der Infrastruktur-Overhead von Temporal (~512MB RAM, ein zusätzlicher Docker-Stack) ist gerechtfertigt: der dev-server hat ausreichend Kapazität, und die PostgreSQL-Instanz von bfagent wird mitgenutzt — kein zusätzlicher Datenbankserver nötig.

**Koexistenz-Modell (kein Big-Bang-Replace):**

| System             | Status           | Neuer Scope nach Migration                                      |
|--------------------|------------------|-----------------------------------------------------------------|
| **Temporal**       | Neu              | Primäre Workflow-Engine: alles mit State, Cross-System, Gate    |
| **Celery**         | Reduziert        | Nur: Scheduled Tasks (Beat) + echte Fire-and-Forget ohne State  |
| **N8n**            | Bleibt           | External Event Bus: sendet Signals an laufende Temporal-Workflows |
| **GitHub Actions** | Bleibt           | CI/CD: wird von Temporal als Activity getriggert               |
| **Django-FSM**     | Nicht eingeführt | Simple Model-States bleiben als `CharField` mit `choices`       |

---

## 4. Implementation Details

### 4.1 Temporal Self-Hosted Stack (Docker)

Temporal nutzt die bestehende PostgreSQL-Instanz von bfagent (`bfagent_db` Container im Netzwerk `bf_platform_prod`) mit einem separaten Schema `temporal`. Kein zusätzlicher PostgreSQL-Container nötig.

> **Hinweis `temporalio/auto-setup`**: Dieses Image führt beim ersten Start automatisch das Schema-Setup aus (erstellt Keyspace/Schema in PostgreSQL). Es ist für Self-hosted Single-Node-Deployments geeignet und wird von Temporal offiziell für genau diesen Use Case empfohlen. Für Multi-Node-Cluster wäre `temporalio/server` + manuelles `temporal-sql-tool` korrekt — das ist hier nicht nötig.
>
> **Hinweis `DB: postgres12`**: Das ist der interne Treiber-Name in Temporal (nicht die PostgreSQL-Version). `postgres12` bedeutet: "nutze den PostgreSQL-Treiber" — kompatibel mit PostgreSQL 12, 13, 14, 15, 16. Der bfagent-Stack nutzt PostgreSQL 15/16, das ist vollständig kompatibel.

```yaml
# docker-compose.temporal.yml — dev-server, Netzwerk: bf_platform_prod
services:
  temporal:
    image: temporalio/auto-setup:1.26
    container_name: temporal_server
    restart: unless-stopped
    environment:
      DB: postgres12
      DB_PORT: 5432
      POSTGRES_USER: bfagent
      POSTGRES_PWD: ${POSTGRES_PASSWORD}
      POSTGRES_SEEDS: bfagent_db   # bestehender Container im Netzwerk
      DYNAMIC_CONFIG_FILE_PATH: /etc/temporal/dynamicconfig.yaml
    ports:
      - "127.0.0.1:7233:7233"   # gRPC — nur lokal, kein externer Zugriff (kein Auth)
    volumes:
      - ./temporal/dynamicconfig.yaml:/etc/temporal/dynamicconfig.yaml:ro
    networks:
      - bf_platform_prod

  temporal-ui:
    image: temporalio/ui:2.34
    container_name: temporal_ui
    restart: unless-stopped
    environment:
      TEMPORAL_ADDRESS: temporal:7233
      TEMPORAL_CORS_ORIGINS: "https://bfagent.iil.pet"
    ports:
      - "0.0.0.0:8233:8080"   # HTTP UI → Nginx exposed
    networks:
      - bf_platform_prod

networks:
  bf_platform_prod:
    external: true
    name: bf_platform_prod
```

```yaml
# temporal/dynamicconfig.yaml
frontend.enableServerVersionCheck:
  - value: false
limit.maxIDLength:
  - value: 255
```

**Namespace-Setup (einmalig nach erstem Start):**
```bash
temporal operator namespace create platform-dev \
  --retention 30d \
  --description "Platform AI Workflows — Dev"
```

**Nginx für Temporal UI (Produktionsserver 88.198.191.108):**
```nginx
server {
    server_name temporal.iil.pet;
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/temporal.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/temporal.iil.pet/privkey.pem;
    location / {
        proxy_pass http://46.225.113.1:8233;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4.2 Python SDK — Shared Client (platform_context)

```python
# platform_context/temporal_client.py
import os
from temporalio.client import Client

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "temporal:7233")
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "platform-dev")

_client: Client | None = None

async def get_temporal_client() -> Client:
    """Singleton — Temporal-Client ist teuer zu erstellen, wird gecacht."""
    global _client
    if _client is None:
        _client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)
    return _client
```

**Requirements-Ergänzung (alle betroffenen Repos):**
```
temporalio>=1.7.0
```

### 4.3 Workflow 1: RequirementProcessingWorkflow (bfagent)

Ersetzt `process_requirement_task` in `apps/bfagent/tasks.py`.

```python
# apps/bfagent/workflows/requirement_processing.py
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from dataclasses import dataclass

@dataclass
class RequirementInput:
    requirement_id: str
    initiative_id: str | None = None

@dataclass
class GateApprovalSignal:
    approved: bool
    approver: str
    comment: str = ""

@workflow.defn
class RequirementProcessingWorkflow:
    """
    Durable replacement für process_requirement_task (Celery).

    State-Machine:
        CREATED → ANALYZING → EXECUTING → [AWAITING_GATE] → COMPLETED
                                                ↑ Signal: gate_approval
                                                ↓ Timeout 24h → ESCALATED
    """

    def __init__(self) -> None:
        self._gate_signal: GateApprovalSignal | None = None
        self._state = "CREATED"

    @workflow.signal
    def gate_approval(self, signal: GateApprovalSignal) -> None:
        self._gate_signal = signal

    @workflow.query
    def current_state(self) -> str:
        return self._state

    @workflow.run
    async def run(self, input: RequirementInput) -> dict:
        # Step 1: Analyse (schnell, 5min Timeout)
        self._state = "ANALYZING"
        analysis = await workflow.execute_activity(
            "analyze_requirement_activity",
            input.requirement_id,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # Step 2: Gate VOR Execution — wenn Analyse-Score niedrig, erst Mensch fragen
        # (Gate nach Execution wäre sinnlos: Arbeit bereits erledigt)
        if analysis.get("quality_score", 100) < 60:
            self._state = "AWAITING_GATE"
            await workflow.wait_condition(
                lambda: self._gate_signal is not None,
                timeout=timedelta(hours=24),
            )
            if not self._gate_signal or not self._gate_signal.approved:
                self._state = "REJECTED"
                return {"ok": False, "reason": "Gate rejected by human reviewer"}

        # Step 3: Execution (lang laufend, bis 30min, LLM-Calls)
        self._state = "EXECUTING"
        await workflow.execute_activity(
            "work_on_requirement_activity",
            args=[input.requirement_id, analysis],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=30)),
        )

        # Step 4: N8n-Notification (fire-and-forget, 1 Versuch)
        await workflow.execute_activity(
            "notify_n8n_activity",
            args=[input.requirement_id, "completed"],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        self._state = "COMPLETED"
        return {"ok": True, "requirement_id": input.requirement_id}
```

### 4.4 Workflow 2: AgentTeamWorkflow (mcp-hub)

Ersetzt `WorkflowExecution` (in-memory) in `orchestrator_mcp/agent_team/workflows.py`. Implementiert ADR-066 Gate-Mechanismus und ADR-068 Quality-Feedback-Loop nativ.

```python
# orchestrator_mcp/workflows/agent_team_workflow.py
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from dataclasses import dataclass

@dataclass
class AgentTeamInput:
    workflow_type: str      # "adr_development" | "test_existing" | "re_engineering"
    task_description: str
    model_tier: str         # aus ADR-068 TaskRouter
    requires_gate: int      # 0=auto, 1=notify, 2=approve, 3=block, 4=human-only

@workflow.defn
class AgentTeamWorkflow:
    """
    Durable replacement für WorkflowExecution (mcp-hub, in-memory).
    Implementiert ADR-066 Gate-Mechanismus via Temporal Signals.
    Implementiert ADR-068 Quality-Feedback-Loop via Activities.

    State-Machine (entspricht TaskStatus-Enum in models.py):
        CREATED → ROUTING → EXECUTING → TESTING → IN_REVIEW
            → AWAITING_GATE (bei requires_gate >= 2)
            → DONE | BLOCKED | FAILED
    """

    def __init__(self) -> None:
        self._gate_approved: bool | None = None
        self._reviewer: str = ""

    @workflow.signal
    def gate_decision(self, approved: bool, reviewer: str) -> None:
        self._gate_approved = approved
        self._reviewer = reviewer

    @workflow.run
    async def run(self, input: AgentTeamInput) -> dict:
        routing = await workflow.execute_activity(
            "route_task_activity", input,
            start_to_close_timeout=timedelta(minutes=2),
        )
        result = await workflow.execute_activity(
            "execute_agent_team_activity", args=[input, routing],
            start_to_close_timeout=timedelta(minutes=60),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        quality = await workflow.execute_activity(
            "evaluate_quality_activity", result,
            start_to_close_timeout=timedelta(minutes=5),
        )
        if input.requires_gate >= 2:
            self._gate_approved = None
            await workflow.wait_condition(
                lambda: self._gate_approved is not None,
                timeout=timedelta(hours=48),
            )
            if not self._gate_approved:
                return {"ok": False, "reason": f"Gate {input.requires_gate} rejected by {self._reviewer}"}
        await workflow.execute_activity(
            "update_routing_matrix_activity", args=[routing, quality],
            start_to_close_timeout=timedelta(minutes=1),
        )
        return {"ok": True, "quality_score": quality.get("composite_score")}
```

### 4.5 Workflow 3: CrossSystemSagaWorkflow (platform_context)

Für Flows die mehrere Repos koordinieren. Garantiert automatische Kompensation (Rollback) wenn ein Schritt fehlschlägt.

```python
# platform_context/workflows/cross_system_saga.py
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from dataclasses import dataclass

@dataclass
class SagaStep:
    activity_fn: str
    args: dict
    compensation_fn: str
    compensation_args: dict
    task_queue: str = "bfagent-queue"

@workflow.defn
class CrossSystemSagaWorkflow:
    """
    Saga-Pattern für Cross-System-Workflows.
    Wenn Schritt N fehlschlägt → Schritte N-1..1 automatisch kompensiert.

    Beispiel-Flow:
        bfagent(Requirement) → mcp-hub(Code) → deploy-hub(Deploy)
    Rollback:
        deploy-hub(Rollback) → mcp-hub(Revert) → bfagent(Reopen)
    """

    @workflow.run
    async def run(self, steps: list[SagaStep]) -> dict:
        completed: list[SagaStep] = []
        for step in steps:
            try:
                await workflow.execute_activity(
                    step.activity_fn, step.args,
                    task_queue=step.task_queue,
                    start_to_close_timeout=timedelta(minutes=30),
                )
                completed.append(step)
            except Exception as e:
                for done_step in reversed(completed):
                    await workflow.execute_activity(
                        done_step.compensation_fn, done_step.compensation_args,
                        task_queue=done_step.task_queue,
                        start_to_close_timeout=timedelta(minutes=10),
                        retry_policy=RetryPolicy(maximum_attempts=5),
                    )
                return {"ok": False, "failed_at": step.activity_fn, "error": str(e)}
        return {"ok": True, "steps_completed": len(steps)}
```

### 4.6 N8n-Repositionierung: Von Fire-and-Forget zu Signal-Sender

```
Heute (unidirektional):
    bfagent → POST /webhook/requirement-process → N8n (Hostinger)
    (kein Callback, kein State-Sync)

Nach Migration (bidirektional):
    Temporal-Workflow → Activity: notify_n8n_activity()
        → POST /webhook/requirement-process → N8n (Hostinger)
        → N8n verarbeitet (Slack, Email, externe APIs)
        → N8n → POST /api/n8n/signal/ → bfagent
            → bfagent sendet Signal an laufenden Workflow:
              handle.signal("n8n_callback", payload)
```

```python
# apps/api/views_n8n_callback.py — neuer Endpoint in bfagent
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from asgiref.sync import async_to_sync
from platform_context.temporal_client import get_temporal_client

@csrf_exempt
@require_http_methods(["POST"])
def n8n_callback(request):
    """N8n sendet Ergebnis zurück → Temporal Signal an laufenden Workflow.

    Hinweis: async_to_sync() statt asyncio.run() — Django ist WSGI-synchron,
    asyncio.run() würde einen neuen Event-Loop erzeugen und ist fragil.
    asgiref.sync.async_to_sync() ist der Django-idiomatische Weg.
    """
    payload = json.loads(request.body)
    workflow_id = payload.get("workflow_id")
    signal_name = payload.get("signal", "n8n_callback")

    async def _send():
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(signal_name, payload)

    async_to_sync(_send)()
    return JsonResponse({"ok": True})
```

### 4.7 Worker-Konfiguration (je Repo ein Worker-Container)

```python
# apps/bfagent/temporal_worker.py
import asyncio
from temporalio.worker import Worker
from platform_context.temporal_client import get_temporal_client
from .workflows.requirement_processing import RequirementProcessingWorkflow
from .activities.requirement_activities import (
    analyze_requirement_activity,
    work_on_requirement_activity,
    notify_n8n_activity,
)

async def run_worker():
    client = await get_temporal_client()
    worker = Worker(
        client,
        task_queue="bfagent-queue",
        workflows=[RequirementProcessingWorkflow],
        activities=[
            analyze_requirement_activity,
            work_on_requirement_activity,
            notify_n8n_activity,
        ],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(run_worker())
```

```yaml
# Ergänzung in docker-compose.prod.yml (bfagent)
  bfagent-temporal-worker:
    image: ghcr.io/achimdehnert/bfagent-web:${IMAGE_TAG:-latest}
    container_name: bfagent_temporal_worker
    restart: unless-stopped
    env_file: .env.prod
    environment:
      TEMPORAL_ADDRESS: temporal:7233
      TEMPORAL_NAMESPACE: platform-dev
    command: ["python", "-m", "apps.bfagent.temporal_worker"]
    depends_on:
      - temporal
      - postgres
    networks:
      - bf_platform_prod
```

### 4.8 Determinismus-Regeln für Workflow-Code

Temporal replayed Workflow-Code bei Crash. Nicht-deterministischer Code führt zu `NonDeterminismError`.

| Erlaubt im Workflow | Verboten im Workflow (→ in Activity auslagern) |
|---------------------|------------------------------------------------|
| `workflow.now()` | `datetime.now()`, `datetime.utcnow()` |
| `workflow.random()` | `random.random()`, `uuid.uuid4()` |
| `await workflow.execute_activity(...)` | Direkter HTTP-Call, DB-Query, Filesystem-I/O |
| `workflow.wait_condition(...)` | `time.sleep()`, `asyncio.sleep()` |
| `workflow.patched("feature-v2")` | Direkte Code-Änderung ohne Versioning |


---

## 5. Migration Tracking

| Repo / Service         | Phase | Status          | Datum | Notizen                                                          |
|------------------------|-------|-----------------|-------|------------------------------------------------------------------|
| `platform`             | 1     | ✅ Abgeschlossen | 2026-02-23 | `docker-compose.temporal.yml` + Namespace `platform-dev` + UI auf Port 8233 |
| `bfagent`              | 2     | ✅ Abgeschlossen | 2026-02-23 | `RequirementProcessingWorkflow` + Activities + Worker + `temporalio` in requirements |
| `bfagent`              | 2     | ⬜ Ausstehend   | –     | N8n-Callback-Endpoint `/api/n8n/signal/` implementieren         |
| `bfagent`              | 2     | ⬜ Ausstehend   | –     | `execute_delegated_task` → Temporal Activity                    |
| `mcp-hub`              | 3     | ✅ Abgeschlossen | 2026-02-23 | `AgentTeamWorkflow` + Activities + Worker + `temporalio` in pyproject.toml + `temporal_client.py` |
| `platform_context`     | 3     | ⬜ Ausstehend   | –     | `CrossSystemSagaWorkflow` + `get_temporal_client()` als shared  |
| `deploy-hub`           | 4     | ⬜ Ausstehend   | –     | `DeploymentWorkflow` als Temporal-Wrapper um GitHub Actions API |
| `dev-hub`              | 5     | ⬜ Ausstehend   | –     | Temporal UI in dev-hub Monitoring-Dashboard integrieren         |
| Celery (bfagent)       | 6     | ⬜ Ausstehend   | –     | Celery auf Scheduled Tasks + echte Fire-and-Forget reduzieren   |

---

## 6. Consequences

### 6.1 Good

- **Durability**: Workflow-State überlebt Agent-Session-Ende, Worker-Crash, Code-Deploy — strukturell, nicht durch Workarounds
- **Time-Travel-Debugging**: Vollständiger Execution-History-Stack — wer hat was wann warum ausgeführt, mit welchen Inputs
- **Gate-Mechanismus nativ**: `workflow.wait_condition()` ist der natürliche Ausdruck von ADR-066 Gates — kein Polling, kein Workaround
- **Cross-System-Atomizität**: Saga-Pattern mit automatischer Kompensation — `bfagent → mcp-hub → deploy-hub` als atomare Einheit
- **N8n bidirektional**: N8n kann Ergebnisse zurücksenden via Signal — echter Integration-Loop statt fire-and-forget
- **Skalierung**: Temporal Worker skalieren horizontal — mehr Agents = mehr Worker-Prozesse, kein Bottleneck im Workflow-State
- **Observability**: Temporal UI zeigt alle laufenden, abgeschlossenen und fehlgeschlagenen Workflows mit vollständiger History und Retry-Counts

### 6.2 Bad

- **Determinismus-Anforderung**: Workflow-Code darf keine nicht-deterministischen Operationen enthalten. Erfordert Disziplin und Code-Review-Regeln.
- **Neue Infrastruktur**: Temporal-Server als zusätzlicher Docker-Stack (~512MB RAM auf dev-server 46.225.113.1)
- **Migration-Aufwand**: Bestehende Celery-Tasks müssen schrittweise in Activities umgewandelt werden (6 Phasen, nicht Big-Bang)

### 6.3 Nicht in Scope

- **Temporal Cloud**: Bewusst ausgeschlossen — Self-hosted auf dev-server vermeidet externe Abhängigkeit und Cloud-Kosten
- **Elasticsearch für Visibility**: Optional, wird in Phase 1 nicht installiert — Temporal funktioniert ohne es (reduzierte Such-Features in UI)
- **Visual Workflow Builder** (React Flow in bfagent): Deferred — Temporal UI ist ausreichend für Monitoring
- **Django-FSM**: Nicht eingeführt — `CharField` mit `choices` reicht für einfache Model-States

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| Determinismus-Verletzung im Workflow-Code | Mittel | Hoch | Code-Review-Regel: kein I/O, kein `datetime.now()` direkt im `@workflow.defn`-Block; Ruff-Lint-Regel geplant |
| Temporal-Server-Ausfall | Niedrig | Hoch | `restart: unless-stopped` + PostgreSQL-Backup (ADR-075); Temporal ist designed für Restart-Recovery ohne State-Verlust |
| Migration-Unterbrechung (Celery parallel zu Temporal) | Mittel | Mittel | Phasenweise Migration; Celery-Tasks bleiben als Shim bis Phase 6 abgeschlossen |
| PostgreSQL-Schema-Konflikt | Niedrig | Mittel | Temporal nutzt eigenes Schema `temporal` — kein Konflikt mit `public` Schema von bfagent |
| Lernkurve für neue Agents (Determinismus-Regeln) | Mittel | Niedrig | Determinismus-Regeln in ADR dokumentiert (§4.8); Workflow-Beispiele in `platform_context` als Referenz |
| N8n (Hostinger) als Single Point of Failure | Mittel | Niedrig | N8n ist nur External Event Bus — Temporal-Workflows funktionieren auch ohne N8n-Callback (Timeout-Fallback) |

---

## 8. Confirmation

1. **Temporal UI Monitoring**: Alle Workflows sind über `temporal.iil.pet` (Phase 1) sichtbar — kein Workflow läuft ohne Temporal-Eintrag. Prüfung: Wöchentliche Review der fehlgeschlagenen Workflows in Temporal UI.
2. **Celery-Task-Audit**: Nach Phase 6 darf kein Celery-Task mehr State-behaftete Workflows ausführen. Prüfung: `grep -r "process_requirement_task\|execute_delegated_task" apps/` muss leer sein.
3. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 12 Monate. Drift-Check-Paths: `bfagent/apps/bfagent/workflows/`, `mcp-hub/orchestrator_mcp/workflows/`

---

## 9. More Information

- [Temporal Python SDK Dokumentation](https://docs.temporal.io/develop/python)
- [Temporal Self-Hosted Setup (Docker)](https://docs.temporal.io/self-hosted-guide/setup)
- [Temporal Determinism Guide](https://docs.temporal.io/workflows#deterministic-constraints)
- [Saga Pattern in Temporal](https://docs.temporal.io/workflows#long-running-workflows)
- ADR-059: ADR Drift Detection — Drift-Detector prüft dieses ADR auf Aktualität (Staleness-Schwelle: 12 Monate)
- ADR-066: AI Engineering Squad + Gate-Mechanismus — `AgentTeamWorkflow` ersetzt in-memory `WorkflowExecution`; Gate 2+ via `workflow.wait_condition()`
- ADR-068: Adaptive Model Routing — `route_task_activity` + `evaluate_quality_activity` + `update_routing_matrix_activity` als Temporal Activities
- ADR-075: Deployment Execution Strategy — `DeploymentWorkflow` wraps GitHub Actions API (Phase 4)

---

## 10. Changelog

| Datum      | Autor          | Änderung                                                                 |
|------------|----------------|--------------------------------------------------------------------------|
| 2026-02-23 | Achim Dehnert  | Initial: Status Proposed                                                 |
| 2026-02-23 | Achim Dehnert  | Review: Pros für B/C/D ergänzt; Gate-Logik korrigiert (vor Execution); `asyncio.run` → `async_to_sync`; Singleton-Client; Port 7233 intern; ADR-Referenzen korrigiert |

---

<!--
  GOVERNANCE-HINWEISE:

  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - bfagent/apps/bfagent/workflows/
      - mcp-hub/orchestrator_mcp/workflows/
      - platform_context/temporal_client.py
  - supersedes_check: true

  techdocs-Sync:
  - Kategorie: platform
  - Tags: temporal, workflow-engine, durability, cross-system, human-in-the-loop, saga, celery, n8n

  Review-Checkliste: /docs/templates/adr-review-checklist.md
  Template-Version: 2.0 (2026-02-21)
-->

