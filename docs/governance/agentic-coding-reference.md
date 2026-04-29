# Agentic Coding — Workflow-Übersicht & ADR-Referenzen

> Ausgelagert aus `.windsurf/workflows/agentic-coding.md` (2026-04-29, ADR-175)
> Wird am Ende des `/agentic-coding` Workflows konsultiert

---

---

## Workflow auf einen Blick (v4)

```
Phase 0: Contract Verification → PCV A/B/C/D/E               (moderate+ | trivial: nur D)
Step 0:  Governance Check      → <ctx>_get_context_for_task   (complexity >= moderate)
Step 1:  analyze + plan        → analyze_task, plan_task       (immer)
Step 2:  Kostenschätzung       → get_cost_estimate             (complex+)
Step 3:  Implementieren        → Developer Gate 1              (immer)
Step 3.5 Proactive Tasks       → CHANGELOG, ADR-Impact, Scan   (immer)
Step 4:  Guardian              → ruff, bandit, pytest          (immer)
Step 5:  Self-Review           → Checkliste + log_action       (immer)
Step 6:  QA Gate               → check_gate / request_approval (immer)
Step 7:  Commit + PR                                           (immer)
Step 8:  AuditStore + Issue    → log_action, Issue-Kommentar   (immer)
```

---

## Referenzen

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-067: Work Management — Issues, AI-Agent-Protokoll
- ADR-068: Adaptive Model Routing — Routing-Matrix, Quality Metrics
- ADR-080: Multi-Agent Coding Team Pattern — Handoff, Parallelisierung, Rollback
- ADR-107: Extended Agent Team — Deployment Agent, Review Agent
- ADR-108: Agent QA Cycle — QualityEvaluator, TaskCompletionChecker, AuditStore
- ADR-173: Document Intake Routing — Ursprung des Contract Verification Pattern
