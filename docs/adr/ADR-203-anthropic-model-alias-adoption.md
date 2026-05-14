---
status: rejected
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-199-rejected, ADR-201, mcp-hub#37, mcp-hub#41]
rejected-after: 4th-round advocatus-diaboli (concurrent with ADR-202). Silent-drift trade against today's loud-drift makes this strictly worse than the status-quo + drift-workflow (mcp-hub#41). The Internal-Alias-Alternative (sketched in original proposal) is the better pattern but doesn't justify a separate ADR — kann ad-hoc als simple Python-Konstante eingeführt werden.
---

# ADR-203: Anthropic Model-Alias Adoption (REJECTED)

## Status

**Rejected** after 4th-round advocatus-diaboli review.

## Rejection Rationale

Three structural issues:

1. **Silent-drift ist schlimmer als loud-drift.** Heute: dead model → 404 → mcp-hub#41 Drift-Workflow öffnet Issue innerhalb 24 h → wir fixen. Mit Aliases: Anthropic ändert silent das alias-target → Calls succeed weiter aber mit anderem Modell → wir merken's erst via Cost-Drift (kein systematisches Tracking dafür).

2. **Pricing-Tracking wird inakkurat.** `PRICING_USD_PER_MTOK` (in `~/.claude/hooks/log_llm_call.py`) ist by-model-string. Alias → variable target → unsere geloggten cost_usd-Werte werden falsch. Real-Time-Cost-Tracking (ADR-201 hat das gerade gefixt) bricht.

3. **Internal-Alias-Alternative ist klar besser** — das ADR enthält sie selbst aber empfiehlt das schlechtere Pattern. Internal aliases (`iil/sonnet-current`) behalten Provider-Independence + kontrollierte Drift-Geschwindigkeit + einheitliches Naming. Aber selbst die Internal-Alias-Variante rechtfertigt **kein eigenes ADR** — kann als simple Python-Konstante in `iil_routing/aliases.py` eingeführt werden wenn nötig.

**Status-quo-Pattern (pinned versions + mcp-hub#41 Drift-Workflow)** ist die stabilste Variante. Keine Architektur-Änderung nötig.

---

# (Archive) Original v0-Proposal-Text

## Context

Heute pinnen wir an konkrete Versionen: `anthropic/claude-sonnet-4-6`, `anthropic/claude-opus-4-7`, `anthropic/claude-haiku-4-5`. Drift-Risiko: wenn Anthropic ein Modell retired (siehe mcp-hub#37 — `claude-3-5-sonnet-20241022` war exakt das), müssen wir N Surfaces updaten.

Anthropic bietet rolling Aliases: `claude-sonnet-4-latest`, `claude-opus-4-latest`, etc. Drift-Wartung verschiebt sich damit **zum Provider**.

## Decision

Alle Anthropic-Referenzen in den Routing-Surfaces auf rolling aliases umstellen:

| Heute | Nach Adoption |
|---|---|
| `anthropic/claude-sonnet-4-6` | `anthropic/claude-sonnet-4-latest` |
| `anthropic/claude-opus-4-7` | `anthropic/claude-opus-4-latest` |
| `anthropic/claude-haiku-4-5` | `anthropic/claude-haiku-4-latest` (falls existent) |

Surfaces betroffen:
- `mcp-hub:orchestrator_mcp/model_selector.py` _ROUTE_TABLE
- `mcp-hub:orchestrator_mcp/model_registry.py` _FALLBACK
- `mcp-hub:orchestrator_mcp/skills/review_adr.py` _DEFAULT_REVIEW_MODEL (ADR-201 ist hier vermutlich schon der nächste Update)
- `dev-hub:aifw_action_types.default_model_id` (SQL UPDATE auf alias-Rows)
- `dev-hub:aifw_llm_models` neue Rows mit alias names
- `~/.claude/policies/llm-routing.md` Tier-Liste

NICHT betroffen:
- `groq/*`, `cerebras/*`, `openai/*`, `mistral/*` — andere Provider haben unterschiedliche Alias-Strategien, einzeln evaluieren
- `model_route_configs` DB-Tabelle (mcp-hub#47 ist erst 24h alt, drift-frei)

## Phasen

| Phase | Aufwand | Lieferung |
|---|---|---|
| 1 | 30 min | Verifizieren via `litellm.completion(model='anthropic/claude-sonnet-4-latest', ...)` ob alle 3 Aliases von litellm akzeptiert sind |
| 2 | 1 h | SQL-Migration (`0045_aifw_alias_rows.sql` + `0046_model_route_configs_alias.sql`) |
| 3 | 1 h | Code-Updates in mcp-hub (`model_selector.py`, `model_registry.py`, `skills/review_adr.py`) |
| 4 | 30 min | Policy-Files updaten + Drift-Workflow re-baseline (`docs/known-dead-models.txt`) |

## Acceptance Criteria

- [ ] `litellm.completion(model='anthropic/claude-sonnet-4-latest', ...)` gibt eine erfolgreiche Antwort
- [ ] mcp-hub Drift-Workflow nächster Run zeigt 0 dead-strings unter den aliased entries
- [ ] Cost-Tracking (`llm_calls.cost_usd`) bleibt akkurat — Anthropic billt unter dem aufgelösten model, nicht unter dem alias

## Risiken (kritisch zu lesen)

### Vendor-seitige Risiken (silently failing modes)

1. **Alias-Target ändert sich ohne Vorwarnung**: heute zeigt `claude-sonnet-4-latest` auf `claude-sonnet-4-6`. Morgen vielleicht auf `claude-sonnet-5-mini` mit anderer Qualität / anderem Pricing. Wir merken es nicht via Drift-Workflow (Alias resolved weiter), nur via Cost-Drift-Beobachtung.
2. **Pricing-Drift**: PRICING_USD_PER_MTOK in `log_llm_call.py` ist by-model-string. Wenn Anthropic der alias auf ein günstigeres/teureres Modell zeigen lässt, ist unser Cost-Estimate falsch. Mitigation: nur Anthropic's eigenes Usage-Reporting als ground truth verwenden (lebt nicht in unserem Stack).
3. **Behavioral drift**: alias-target kann subtle Antwort-Stil ändern. Tests die heute grün sind können morgen rot werden ohne dass wir etwas geändert haben.
4. **Reproduzierbarkeit**: Prompts gegen `-latest` ergeben heute ≠ in 3 Monaten. Für ADR-Reviews und Audits oft problematisch.

### Architektur-Risiken

5. **Inkonsistenz**: nur Anthropic aliases, andere Provider weiterhin pinned. Architektur ist mixed.
6. **Vendor-Lock-in tiefer**: Adoption von alias-Pattern macht Migration zu z.B. OpenAI härter — keine 1:1-Alias-Map.

## Out-of-the-Box-Alternative: Internal Aliases statt Provider-Aliases

Anstatt Anthropic's alias zu adoptieren, **bauen wir unsere eigenen**:

```python
# in iil_routing.aliases:
INTERNAL_ALIAS = {
    "iil/sonnet-current":  "anthropic/claude-sonnet-4-6",
    "iil/opus-current":    "anthropic/claude-opus-4-7",
    "iil/haiku-current":   "anthropic/claude-haiku-4-5",
    "iil/fast-current":    "groq/llama-3.3-70b-versatile",
}
```

Vorteile: Provider-Independence, kontrollierte Drift-Geschwindigkeit, einheitliches Naming über alle Provider.
Nachteil: wir tragen die Update-Last (statt sie zu Anthropic zu verschieben).

**Trade-off:** ADR-203 verschiebt Update-Last extern aber öffnet silent-drift; Internal-Aliases halten Last intern aber verhindern silent-drift.

## Implementations-Skizze (falls accepted)

```sql
-- 0045_aifw_alias_rows.sql
INSERT INTO aifw_llm_models (provider_id, name, display_name, ...)
SELECT id, 'claude-sonnet-4-latest', 'Claude Sonnet 4 (rolling alias)', ...
  FROM aifw_llm_providers WHERE name='anthropic'
ON CONFLICT (provider_id, name) DO NOTHING;
-- (repeat for opus-4-latest, haiku-4-latest)

-- update default_model_id für die 5-6 action_codes
UPDATE aifw_action_types
   SET default_model_id = (SELECT id FROM aifw_llm_models m
                            JOIN aifw_llm_providers p ON p.id=m.provider_id
                            WHERE p.name='anthropic' AND m.name='claude-sonnet-4-latest')
 WHERE code IN ('orchestrator.developer','headless.edit','skill.review_adr','headless.quality_sweep');
```

## Why optional, why this order

ADR-201 (Pricing Visibility) erhöht die Sichtbarkeit dass Anthropic-Aliase ihr Verhalten ändern. ADR-203 verschiebt das Drift-Problem, eliminiert es nicht. **Erst nach ADR-201-Messung** entscheiden ob die Cost-Sichtbarkeit + Drift-Workflow zusammen genug sind oder ob alias-adoption die Wartung weiter senkt.

## Changelog

- 2026-05-14: Initial. Status: proposed, conditional on ADR-201 measurement + explicit user acceptance of vendor-side silent-drift trade-off.
