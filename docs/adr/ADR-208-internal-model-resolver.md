---
status: accepted
date: 2026-05-16
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-199-rejected, ADR-201, ADR-203, mcp-hub#37, mcp-hub#41]
---

# ADR-208: Interner Model-Resolver — versionierte Alias→Pin+Preis-Map (ohne Service)

## Status

Accepted (2026-05-16) — ratifiziert aus dem Advocatus-Diabolus-Review von
ADR-201 + ADR-203. Ersetzt die Richtung von ADR-203 (dort `superseded`).
Implementierung gemäß Skizze offen (`implementation_status: none`).

## Context

Drei ADRs umkreisen dieselbe fehlende Schicht:

- **ADR-199** wollte eine Model-Routing-*Authority* und wurde nach 4 Review-
  Runden als **over-engineered** abgelehnt (Service/GitOps-Routing zu schwer).
- **ADR-203** versucht Drift-Wartung über Provider-`-latest` zu lösen →
  silent vendor drift, Reproduzierbarkeit/Cost-Tracking kaputt (dort Amendment).
- **ADR-201** dupliziert Pricing-Wissen (`PRICING_USD_PER_MTOK`) und liest
  Session-Kosten pro Turn aus der Prod-DB.

Nicht-offensichtlicher Befund: ADR-199 wurde zu Recht als *schwere* Variante
verworfen — aber „kein 199" ≠ „die leichte Essenz von 199". 201 und 203 kaufen
diese Essenz jeweils teuer und unvollständig ein. **Es fehlt genau ein
Primitiv: Model-Identität + Pricing als eine versionierte Quelle.**

## Decision

Ein **interner Resolver** als *Daten*-Artefakt, **kein Service, keine
Routing-Logik** (bewusste Abgrenzung zum verworfenen ADR-199):

- Eine versionierte Datei (`iil_routing/model_resolver.yaml`, GitOps):

  ```yaml
  aliases:
    iil/opus-current:   { model: anthropic/claude-opus-4-7,    price_in: 15.0, price_out: 75.0 }
    iil/sonnet-current: { model: anthropic/claude-sonnet-4-6,  price_in: 3.0,  price_out: 15.0 }
    iil/haiku-current:  { model: anthropic/claude-haiku-4-5,   price_in: 0.8,  price_out: 4.0 }
    iil/fast-current:   { model: groq/llama-3.3-70b-versatile, price_in: 0.59, price_out: 0.79 }
  ```

- **Genau drei Konsumenten lesen daraus**, keiner hält eigenes Wissen:
  1. Routing-Surfaces (mcp-hub `model_selector`/`model_registry`/`review_adr`)
     referenzieren `iil/<rolle>-current` statt Pin oder Provider-`-latest`.
  2. `~/.claude/hooks/log_llm_call.py` zieht Pricing **nur** hieraus
     (`PRICING_USD_PER_MTOK` entfällt).
  3. ADR-201-Statusline liest Pricing + Rolle hieraus.
- **Update bei Modell-Retirement = 1 PR an dieser Datei** (mcp-hub#37-Fall),
  reviewbar, versioniert.
- **Reproduzierbarkeit:** jeder Call/Run loggt den *aufgelösten* Pin + die
  Resolver-Version (git sha). Audits/ADR-Reviews bleiben exakt nachvollziehbar.
- **Provider-`-latest` ist verboten** auf Routing-/Review-/Eval-/Audit-
  Surfaces (löst ADR-203 Risiko #1–#4 strukturell).

## Consequences

### Positiv

- Eine SSoT für Model-Identität *und* Pricing → ADR-201-Dict-Drift und
  ADR-203-Vendor-Drift fallen beide weg.
- ADR-203 ↔ ADR-201-Konflikt aufgelöst: aufgelöster Pin ⇒ `cost_usd` exakt.
- Keine neue Laufzeit-Abhängigkeit, kein Service — reversibel durch Löschen
  der Datei + Zurück-auf-Pin. Bewusst *kleiner* als das verworfene ADR-199.
- ADR-201 Open Questions 1+2 werden trivial (Rolle bekannt; keine Prod-DB
  im Per-Turn-Pfad nötig).

### Negativ / offen

- Die Update-Last bleibt intern (1 PR pro Retirement) — akzeptiert, weil
  Kontrolle/Observability/Reproduzierbarkeit das überwiegen.
- Migrationsaufwand: Routing-Surfaces + `log_llm_call.py` einmalig auf
  Resolver umstellen (~0.5 Tag). SQL-Rows analog ADR-203 §Implementations-
  Skizze, aber mit Alias→Pin statt Provider-Alias.
- Andere Provider (`groq/*`, `openai/*`) bleiben zunächst gepinnt im Resolver;
  einheitliches Naming ja, aber keine provider-übergreifende Auto-Drift
  (gewollt).

## Abgrenzung zu ADR-199 (warum das kein 199-Reboot ist)

| | ADR-199 (rejected) | ADR-208 |
|---|---|---|
| Form | Service / Routing-Authority | eine YAML-Datei |
| Logik | Routing-Entscheidung | nur Auflösung Alias→Pin+Preis |
| Laufzeit-Dep | ja | nein |
| Reversibel | schwer | Datei löschen |

ADR-199 wurde wegen *Schwere* verworfen — ADR-208 nimmt nur dessen
unstrittigen Kern (eine versionierte Identitäts-/Preis-Quelle) und lässt die
Routing-Authority bewusst weg.

## Implementierungs-Skizze (konkret)

### Ablage & Konsumweg (cross-repo)

Kanonisch in **mcp-hub** (dort leben die Routing-Surfaces), von `~/.claude`
mitbenutzt — Pointer/Vendor statt zweiter Wahrheit (gleiche Anti-Drift-Linie
wie ADR-018 Doku-Strategie):

```
mcp-hub/orchestrator_mcp/iil_routing/
  model_resolver.yaml          # SSoT (GitOps, reviewbar)
  model_resolver.schema.json   # Schema
  resolver.py                  # resolve(alias) -> {model, price_in, price_out, sha}
~/.claude/hooks/log_llm_call.py  # importiert resolver.py, sonst vendored Fallback-Copy
```

### Schema (Auszug, `model_resolver.schema.json`)

```json
{ "type":"object","required":["aliases"],
  "properties":{"aliases":{"type":"object","minProperties":1,
    "additionalProperties":{"type":"object",
      "required":["model","price_in","price_out"],
      "properties":{
        "model":{"type":"string","pattern":"^[a-z0-9_-]+/[A-Za-z0-9._-]+$"},
        "price_in":{"type":"number","exclusiveMinimum":0},
        "price_out":{"type":"number","exclusiveMinimum":0}}}}}}
```

### CI-Validator (deterministisch, analog meiki manifest-check)

`scripts/check-model-resolver.py`, Workflow on PR-paths:

1. Schema-Validierung.
2. Jeder `model` ist ein real auflösbarer litellm-String
   (`litellm.get_model_info(model)` ohne Exception) — **kein** `*-latest`
   erlaubt (Regex-Block `-latest$`).
3. Kein verwaister Alias: jeder in Surfaces referenzierte `iil/<rolle>-current`
   existiert in `aliases` (grep über mcp-hub + policies).
4. Exit≠0 bricht den PR — „Resolver konsistent == Routing konsistent".

### Migration je Surface (idempotent, ein PR)

| Surface | Heute | Nachher |
|---|---|---|
| `orchestrator_mcp/model_selector.py` `_ROUTE_TABLE` | Pins | `iil/<rolle>-current` via `resolver.resolve()` |
| `orchestrator_mcp/model_registry.py` `_FALLBACK` | Pins | dito |
| `orchestrator_mcp/skills/review_adr.py` `_DEFAULT_REVIEW_MODEL` | Pin | `iil/opus-current` |
| `dev-hub aifw_llm_models` / `aifw_action_types.default_model_id` | Pin-Rows | Alias-Rows + UPDATE (SQL analog ADR-203 §Skizze, aber Alias→Pin) |
| `~/.claude/policies/llm-routing.md` | Tier-Liste mit Pins | Alias-Namen |
| `~/.claude/hooks/log_llm_call.py` | `PRICING_USD_PER_MTOK` | `resolver.resolve()`; loggt `resolved_model` + `resolver_sha` |

### Phasen

| Phase | Aufwand | Lieferung |
|---|---|---|
| 1 | 30 min | `model_resolver.yaml` + Schema + `resolver.py` + CI-Validator (grün) |
| 2 | 1 h | `log_llm_call.py` auf Resolver; Regressionstest gegen 30 historische Calls (`cost_usd` ≤ 1 % Abweichung) |
| 3 | 1 h | mcp-hub Surfaces + `review_adr` umstellen; `*-latest`-Grep = 0 |
| 4 | 1 h | dev-hub SQL-Migration (`0047_aifw_alias_rows.sql`) + policies-Update |
| 5 | 30 min | ADR-201-Statusline liest `resolver.resolve()`; Rollback-Test |

### Rollback

Eine Datei + Loader entfernen, Surfaces zurück auf Pin (git revert des
Migrations-PR). Keine Laufzeit-Dependency, kein Datenverlust — der Resolver
ist Daten, kein Service.

### Mapping Phasen → Acceptance

Phase 1→AC1, Phase 3→AC2, Phase 2→AC3, Phase 2/5→AC4, ADR-Amendments→AC5.

## Acceptance Criteria

- [ ] `model_resolver.yaml` existiert, GitOps-versioniert, CI-validiert (Schema + jeder `model` ist ein real auflösbarer litellm-String)
- [ ] mcp-hub Routing-Surfaces referenzieren `iil/<rolle>-current`, kein Provider-`-latest`, keine verstreuten Pins
- [ ] `log_llm_call.py` zieht Pricing aus dem Resolver; `PRICING_USD_PER_MTOK` entfernt; `cost_usd` unverändert akkurat (Regressionstest gegen 30 historische Calls)
- [ ] Jeder geloggte Call enthält aufgelösten Pin + Resolver-git-sha
- [ ] ADR-203-Amendment + ADR-201-Amendment referenzieren ADR-208

## Changelog

- 2026-05-16: Initial. Proposed. Konsolidiert die in ADR-201/203 verstreuten
  Workarounds zur leichten Essenz des verworfenen ADR-199.
