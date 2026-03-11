---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "bfagent: chat conversation logging in AIUsageLog"
---

# ADR-037: Chat Conversation Logging & Quality Management

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Proposed |
| **Date**    | 2026-02-16 |
| **Author**  | Achim Dehnert / Cascade AI |
| **Scope**   | platform, travel-beat, bfagent, weltenhub, risk-hub |
| **Related** | ADR-034 (Chat-Agent Platform), ADR-036 (Chat-Agent Ecosystem) |
| **Package** | `chat-logging` (new, in `platform/packages/`) |

---

## 1. Executive Summary

All chat-agent interactions are currently ephemeral — stored only in
`InMemorySessionBackend` and lost on container restart. This ADR introduces
`chat-logging`, a reusable Django package providing:

1. **Persistent conversation storage** with full message history
2. **Outcome tracking** — goal, result, artifacts created
3. **Use-case discovery** — auto-detection of unmet user needs
4. **Evaluation framework** — integration with DeepEval and LangFuse
5. **Django Admin QM dashboard** — filter, search, review, export

**Phased rollout:**
- **Phase 1**: SQL models, LoggingSessionBackend, Django Admin, DriftTales integration
- **Phase 2**: DeepEval/LangFuse evaluation, auto-detection of use-case candidates

---

## 2. Context & Problem Statement

### 2.1 Current State

| Component | Status | Issue |
|-----------|--------|-------|
| `InMemorySessionBackend` | Active | Lost on restart |
| `RedisSessionBackend` | Available | No SQL querying |
| Conversation logging | None | Cannot review past interactions |
| Quality management | None | No metrics or evaluation |
| Use-case tracking | None | Unmet needs go unnoticed |

### 2.2 Why This Matters

Without persistent logging, the team cannot:
- **Improve prompts** — no visibility into real user queries
- **Prioritize features** — no data on what users want but can't get
- **Measure quality** — no success rate, latency, or hallucination metrics
- **Debug issues** — no audit trail
- **Demonstrate value** — no data on artifacts created via chat

---

## 3. Package Structure

```
platform/packages/chat-logging/
├── pyproject.toml
└── src/chat_logging/
    ├── __init__.py
    ├── models.py        # 4 Django models
    ├── admin.py         # Admin with filters, inlines, actions
    ├── backends.py      # LoggingSessionBackend
    ├── detection.py     # Use-case discovery (Phase 2)
    ├── evaluation.py    # DeepEval/LangFuse (Phase 2)
    ├── exporters.py     # JSONL, CSV export
    └── migrations/
```

**Dependencies:** `django>=5.0`, `chat-agent>=0.1.0`
**Optional:** `deepeval>=1.0`, `langfuse>=2.0` (for Phase 2)

---

## 4. Data Model

### 4.1 ChatConversation

Root entity for a chat session. Stores context (goal), outcome, and QM fields.

**Key fields:**
- `session_id`, `user`, `app_name`, `tenant_id` — identification
- `goal_type` (trip_planning | story_config | enrichment | chapter_writing | research | general)
- `goal_summary` — auto-extracted or manual
- `outcome_status` (completed | partial | abandoned | error)
- `outcome_summary`, `outcome_artifacts` (JSONField, e.g. `{"trip_id": 42}`)
- `satisfaction_rating` (1-5), `review_status`, `review_notes`, `improvement_tags`
- `message_count`, `total_tokens`, `total_tool_calls`, `total_latency_ms`, `models_used`
- `started_at`, `ended_at`

**Indexes:** `(app_name, started_at)`, `(outcome_status, app_name)`, `(review_status)`, `(goal_type, app_name)`

### 4.2 ChatMessage

Individual messages within a conversation.

**Key fields:**
- `conversation` (FK), `role` (system | user | assistant | tool)
- `content`, `model`, `tool_calls` (JSONField), `tool_call_id`
- `tokens_used`, `latency_ms`, `created_at`

### 4.3 UseCaseCandidate

Auto-detected or manually flagged unmet user needs.

**Key fields:**
- `conversation` (FK), `trigger_message` (FK)
- `detection_method` (no_tool_match | explicit_decline | repeated_rephrase | session_abandoned | tool_error | manual)
- `user_intent`, `app_name`, `frequency`
- `status` (new | confirmed | planned | implemented | rejected)
- `priority` (low | medium | high), `notes`

### 4.4 EvaluationScore

Scores from automated evaluation runs (Phase 2).

**Key fields:**
- `conversation` (FK), `evaluator` (deepeval | langfuse | custom)
- `metric_name` (e.g. answer_relevancy, faithfulness, tool_correctness)
- `score` (0.0-1.0), `reason`, `metadata` (JSONField)
- Unique constraint: `(conversation, evaluator, metric_name)`

---

## 5. LoggingSessionBackend

Transparent wrapper — persists messages to DB while delegating session
management to the wrapped backend. **Zero code changes in views.**

```python
from chat_logging import LoggingSessionBackend

backend = LoggingSessionBackend(
    wrapped=InMemorySessionBackend(),
    app_name="drifttales",
    user=user,
)
agent = ChatAgent(..., session_backend=backend)
```

**Behavior:**
- `load()` → delegates to wrapped backend
- `save()` → delegates + persists new messages to `ChatMessage` table
- `delete()` → finalizes conversation (sets `ended_at`, computes metrics) + delegates

### 5.1 Integration in Each App

Only the agent factory changes — no view modifications:

```python
# travel-beat: apps/trips/agent/__init__.py
def create_trip_agent(user=None, ...):
    from chat_logging import LoggingSessionBackend

    backend = LoggingSessionBackend(
        wrapped=InMemorySessionBackend(),
        app_name="drifttales",
        user=user,
    )
    return ChatAgent(..., session_backend=backend)
```

---

## 6. Django Admin

### 6.1 ChatConversation Admin

- **List display:** session_id, app_name, user, goal_type, outcome_status, message_count, review_status, started_at
- **Filters:** app_name, goal_type, outcome_status, review_status, date range
- **Search:** messages__content (fulltext), goal_summary, outcome_summary, user__email
- **Inlines:** ChatMessageInline, UseCaseCandidateInline, EvaluationScoreInline
- **Actions:** mark_reviewed, export_as_jsonl, run_evaluation

### 6.2 UseCaseCandidate Admin

- **List display:** user_intent, app_name, detection_method, frequency, status, priority
- **Editable inline:** status, priority (for quick triage)
- **Filters:** status, priority, app_name, detection_method

---

## 7. Phase 1 — SQL Logging & Admin

**Timeline:** 1-2 days | **Scope:** Models + Backend + Admin + DriftTales

### Deliverables

| # | Deliverable | Details |
|---|-------------|---------|
| 1 | `chat-logging` package | pyproject.toml, models, migrations, admin |
| 2 | `LoggingSessionBackend` | Wrapper with message persistence |
| 3 | Django Admin | Filters, search, inlines, JSONL export |
| 4 | DriftTales integration | Update `create_trip_agent()` factory |
| 5 | Vendored wheel | Build + add to travel-beat/requirements/wheels/ |
| 6 | Deploy | Migration + container recreate |

### What Phase 1 Enables

- Browse all conversations in Django Admin
- Filter by app, goal type, outcome, date
- Full-text search across message content
- Review workflow (pending → reviewed → action_taken)
- Manual tagging with improvement_tags
- JSONL export for external analysis

---

## 8. Phase 2 — Evaluation & Auto-Detection

**Timeline:** 3-5 days | **Depends on:** Phase 1 deployed

### 8.1 Use-Case Auto-Detection

Detect unmet needs from conversation patterns:

| Signal | Detection Method |
|--------|-----------------|
| Agent responds without tool call when user expects action | `no_tool_match` |
| Agent says "Das kann ich leider nicht" | `explicit_decline` (regex/classifier) |
| User rephrases >2x | `repeated_rephrase` (similarity check) |
| Session ends with < 3 messages, no artifact | `session_abandoned` |
| Tool dispatch raises error | `tool_error` |

**Implementation:** Post-save signal on `ChatConversation` triggers detection pipeline.
Similar intents are grouped by embedding similarity → `frequency` counter incremented.

### 8.2 Evaluation Framework

#### DeepEval Integration

```python
from chat_logging.evaluation import run_deepeval

# Batch evaluate all unscored conversations from last 24h
results = run_deepeval(
    app_name="drifttales",
    since=timedelta(hours=24),
    metrics=[
        "answer_relevancy",
        "tool_correctness",
        "conversation_completeness",
    ],
)
# Results stored in EvaluationScore table
```

**Metrics available:**
- `AnswerRelevancy` — Is the response relevant to the query?
- `Faithfulness` — Does the agent hallucinate?
- `ToolCorrectness` — Was the right tool selected?
- `ConversationCompleteness` — Was the goal achieved?
- `Toxicity` — Inappropriate content check
- `LatencyPerMessage` — Custom metric for response time

#### LangFuse Integration (Optional)

```python
from chat_logging.evaluation import LangFuseExporter

# Export conversations to self-hosted LangFuse for tracing UI
exporter = LangFuseExporter(
    host="http://langfuse:3000",  # Docker service
    public_key="...",
    secret_key="...",
)
exporter.export_conversations(app_name="drifttales", last_n=100)
```

LangFuse provides:
- Visual conversation trace viewer
- Score dashboards and trends
- Prompt versioning and A/B testing
- Self-hosted via Docker (fits our infrastructure)

### 8.3 Management Commands

```bash
# Run evaluation on recent conversations
python manage.py evaluate_conversations --app drifttales --since 24h

# Detect use case candidates
python manage.py detect_use_cases --app drifttales --since 7d

# Export for fine-tuning
python manage.py export_conversations --app drifttales --format jsonl --output data/
```

---

## 9. QM Dashboard Queries

Example queries the Admin enables:

| Question | Filter |
|----------|--------|
| Where do users abandon? | `outcome_status=abandoned`, sort by frequency |
| Which prompts need work? | `review_status=pending`, `improvement_tags` not empty |
| What can't the agent do? | UseCaseCandidate `status=new`, sort by frequency |
| How good is trip planning? | `goal_type=trip_planning`, avg evaluation scores |
| What's the success rate per app? | Group by `app_name`, `outcome_status` |
| Slowest conversations? | Sort by `total_latency_ms` desc |

---

## 10. Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| LangFuse only (no SQL) | Rich UI, tracing | External dependency, no Django Admin integration | Rejected — we want SQL for querying + LangFuse as optional Phase 2 add-on |
| Redis persistence | Simple, fast | No SQL filtering, no Admin | Rejected — insufficient for QM |
| Custom dashboard (no Admin) | Full control | High effort, maintenance | Rejected — Django Admin is free and powerful |
| Log to file (JSONL) | Zero overhead | No querying, manual analysis | Rejected — too primitive for QM |

---

## 11. Migration Path

1. **Phase 1:** Add `chat_logging` to `INSTALLED_APPS`, run migrations, update agent factory
2. **Phase 2:** Install `deepeval`/`langfuse` extras, add cron for batch evaluation
3. **Future:** Shared chat-widget (ADR-036) emits satisfaction rating → stored in `satisfaction_rating`

---

## 12. Decision Outcome

- **New package:** `platform/packages/chat-logging/`
- **4 models:** ChatConversation, ChatMessage, UseCaseCandidate, EvaluationScore
- **Integration:** LoggingSessionBackend wrapper (zero view changes)
- **Admin:** Full QM dashboard with filters, search, export
- **Phase 1:** SQL + Admin + DriftTales (immediate)
- **Phase 2:** DeepEval + LangFuse + Auto-Detection (follow-up)
