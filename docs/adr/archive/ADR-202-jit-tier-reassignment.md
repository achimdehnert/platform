---
status: rejected
archived_reason: "rejected — nicht adoptiert"
archived: 2026-05-17
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-068, ADR-116, ADR-196, ADR-199-rejected, ADR-201, ADR-204]
---

# ADR-202: JIT-Tier-Reassignment — start cheap, escalate (REJECTED)

## Status

**Rejected** after 4th-round advocatus-diaboli review.

## Rejection Rationale

Five structural issues:

1. **Tool-call-chains break the retry-pattern.** Agentic loops have state — first Tier-1a attempt may have modified a file; a Tier-3 retry can't undo that. JIT is only safe for stateless completions, which is the minority of LLM calls in this codebase.
2. **Cost-Sketch ist Wunschdenken.** 5×-Ersparnis hängt an 80/20 Trefferquote — keine Daten dafür. Realistisch eher 40-60 % Eskalation.
3. **Heuristic-Trigger sind regex-fragil.** „uncertainty" matched legitime ehrliche Antworten („I'm not sure but probably X").
4. **Latency-Doublung bei interactive UX.** 20 % der Tasks dauern 2× — bei Claude Code merkbar.
5. **Outcome-Log-Pollution.** 20 % der Tasks → 2 Rows in `llm_calls`. Schema-Change `parent_task_id` nötig, ADR ignoriert das.

**Better alternative**: ADR-204 (Pre-Session Wizard) adressiert das Workflow-Problem direkt am User-Touchpoint statt reaktive Korrektur pro Call.

---

# (Archive) Original v0-Proposal-Text

## Context

Aktuelle Routing-Annahme in allen Surfaces (`model_route_configs`, `model_selector._ROUTE_TABLE`, `aifw_action_types`, Claude Code Session): **wir wählen das Modell *vor* dem Call**. Up-front, predictive, basierend auf statischer Klassifizierung.

Echte Engineering-Arbeit folgt aber einem anderen Muster: probier billig, schau ob's reicht, eskaliere bei Bedarf. Analog zu JIT-Compilation-Tiers (Interpretation → Baseline-JIT → Optimizing-JIT).

Kostenrechnung als Plausibilitäts-Skizze:
- 80 % der Tasks **könnten** von Tier 1a (Cerebras llama-70B, ~$0.59/M) gelöst werden
- 20 % brauchen tatsächlich Tier 3 (Sonnet, $3/$15)
- Up-front 100 % Sonnet: 100 × $0.30 = $30
- JIT (Tier 1a → Tier 3 falls nötig): 0.8 × $0.005 + 0.2 × ($0.005 + $0.30) = $0.063
- **~5× Ersparnis** falls die Eskalations-Heuristik 80/20 trifft

## Decision

Ein Library-Wrapper `iil_routing_jit` (oder Erweiterung der ADR-201-Library) der `litellm.completion(...)` umhüllt:

```python
from iil_routing_jit import call_with_escalation

result = call_with_escalation(
    messages=[...],
    tier_chain=["1a", "3"],      # cheap → premium
    escalation_triggers=[
        "truncated",                # finish_reason == 'length' unerwartet
        "empty",                    # response < 50 chars
        "uncertainty",              # "I don't know" Marker
        "error",                    # provider returned 5xx/4xx
    ],
    max_escalations=1,
)
# result.final_model, result.cost_usd_total, result.attempts (list)
```

### Eskalations-Trigger (heuristisch, dokumentiert ehrlich als „best-effort")

| Trigger | Detection | False-positive-Risiko |
|---|---|---|
| `truncated` | `finish_reason == 'length'` AND output < 90% of max_tokens | niedrig |
| `empty` | `len(content.strip()) < 50` | niedrig |
| `uncertainty` | Regex `\b(I don't know\|I'm not sure\|cannot answer\|unclear)\b` | **hoch** — agent kann legitim Unsicherheit ausdrücken |
| `error` | HTTP 5xx / Timeout / RateLimitError | sehr niedrig |
| `tool_call_missing` | Caller erwartete Tool-Call, kam keiner | mittel |

Jeder Trigger ist **opt-in**. Caller wählt was zur Aufgabe passt — keine globale Default-Aktivierung.

### Outcome-Logging

Jeder Attempt wird in `llm_calls` mit `routing_reason='jit_attempt_<n>'` persistiert. Ein zusätzlicher `task_id`-Suffix (`-jit1`, `-jit2`) gruppiert die Attempts logisch. Cost-Tracking aggregiert auf parent-task_id.

## Phasen

| Phase | Aufwand | Lieferung |
|---|---|---|
| 1 | 1 Tag | Library-Skelett, JIT-Logik, 4 Trigger implementiert + Tests |
| 2 | 1 Tag | Wrap einen Konsumenten (Vorschlag: `skill.drift_narrate` — heute Tier 1a, geringes Risiko falls JIT failsafe nötig) |
| 3 | 7-14 Tage | Beobachtung: cost-per-completion vs baseline, Escalation-Rate, False-Positive-Rate |
| 4 | optional | Rollout auf weitere Konsumenten falls Phase 3 positiv |

**Phase 3 ist der Entscheidungspunkt.** Wenn JIT pro Task mehr Latenz produziert als Wert spart, abbrechen.

## Acceptance Criteria

- [ ] Eskalations-Rate (Tier 1a → 3) bei `skill.drift_narrate` < 25 % über 7 Tage (sonst war Tier 1a falsch gewählt vorher)
- [ ] Average cost per successful completion ↓ um ≥ 30 % vs Baseline
- [ ] Average latency per completion erhöht sich um ≤ 50 % (Cerebras ist schnell, Eskalation nur in 20 % der Fälle)
- [ ] False-Positive-Rate des `uncertainty`-Triggers < 5 % (manuell stichprobenartig geprüft)

## Risiken (ehrlich benannt)

- **Latenz-Doublung bei Eskalation**: 20 % der Calls dauern 2× so lang. Bei interactive UX (Claude Code) merkbar. Mitigated durch async/streaming nicht im Scope dieses ADRs.
- **Heuristik-Fragilität**: `uncertainty`-Regex erzeugt false positives. Mitigated durch opt-in pro Caller + Stichproben-Audit.
- **Provider-Rate-Limits auf Tier 1a**: wenn JIT-Pattern Cerebras/Groq hämmert, häufiger 429s → wäre kontraproduktiv. Mitigated durch existing fallback chain in litellm.
- **Outcome-Logging-Pollution**: 20 % der Calls erzeugen 2 Rows. Aggregation muss bewusst gemacht werden in Reports.
- **JIT lohnt sich nur für simple completions** (1-shot Q&A). Tool-call-chains + agentic loops eignen sich **nicht** — der erste Call definiert ein Zustands-Path den ein 2. Versuch nicht reproduzieren kann.

## Why optional, why this order

Wenn ADR-201 (Pricing Visibility) den Spend bereits durch Bewusstsein adressiert, ist ADR-202 redundant. JIT macht den User-Layer überflüssig und damit auch dessen positiven Bewusstseins-Effekt verloren. **Erst nach ADR-201-Messung entscheiden.**

## Changelog

- 2026-05-14: Initial. Status: proposed, conditional on ADR-201 measurement outcome.
