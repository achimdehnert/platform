# ADR-208 Phase 1 — Resolver-Kern (Spezifikation, umsetzungsbereit)

**Status:** planned · **Blockiert durch:** PR #149 (ADR-208 muss auf `main`)
**Datum:** 2026-05-17 · **Scope:** *nur* Resolver-Kern, **keine** Konsumenten-Migration
**Ziel-Repo:** `mcp-hub` (kanonisch laut ADR-208) · Spec-Home: `platform`

> Aus dem Advocatus-Diabolus-Review (ADR-201/203 → ADR-208). Bewusst minimal:
> Phase 1 ist selbst-enthalten, reversibel (Verzeichnis löschen), risikoarm.
> Die riskanten Migrationen (mcp-hub-Routing, dev-hub-SQL) sind **separate,
> owner-koordinierte Folge-PRs** — nie mit Phase 1 gebündelt.

## Vorbedingung (hart)

ADR-208 ist derzeit nur auf `adr/201-pricing-visibility` (PR #149). **Erst
nach Merge von #149 nach `main`** starten — sonst Bau gegen nicht-Trunk-Stand.

## Deliverables Phase 1 (eine PR, Ziel mcp-hub)

```
mcp-hub/orchestrator_mcp/iil_routing/
  model_resolver.yaml          # SSoT
  model_resolver.schema.json   # Schema (additionalProperties:false)
  resolver.py                  # resolve(alias) -> dataclass
mcp-hub/scripts/check-model-resolver.py   # CI-Validator
mcp-hub/.github/workflows/model-resolver-check.yml
```

### 1. `model_resolver.yaml`

```yaml
version: 1
aliases:
  iil/opus-current:      { model: anthropic/claude-opus-4-7,             price_in: 15.0, price_out: 75.0 }
  iil/sonnet-current:    { model: anthropic/claude-sonnet-4-6,           price_in: 3.0,  price_out: 15.0 }
  iil/fast-current:      { model: cerebras/qwen-3-235b-a22b-instruct-2507, price_in: 0.0, price_out: 0.0 }
  iil/adr-review:        { model: cerebras/qwen-3-235b-a22b-instruct-2507, price_in: 0.0, price_out: 0.0 }
  iil/adr-review-deep:   { model: cerebras/zai-glm-4.7,                  price_in: 0.0,  price_out: 0.0 }
```
Preise = USD/MTok; Flatrate-Provider mit 0.0 markiert (Kosten via Provider-
Usage, nicht hier geschätzt — ADR-203-Lehre). Pin-Strings exakt, **nie**
`*-latest`.

### 2. `model_resolver.schema.json`

`type:object`, `required:[version,aliases]`, `additionalProperties:false`.
`aliases` → jedes Item `required:[model,price_in,price_out]`,
`model` Pattern `^[a-z0-9_-]+/[A-Za-z0-9._-]+$`, **Verbot** Regex `-latest$`,
Preise `number, >=0`.

### 3. `resolver.py` — API

```python
@dataclass(frozen=True)
class Resolved: alias:str; model:str; price_in:float; price_out:float; sha:str

def resolve(alias: str) -> Resolved   # KeyError bei unbekanntem Alias
def resolver_sha() -> str             # git-sha der YAML (Reproduzierbarkeit)
def list_aliases() -> list[str]
```
Lädt YAML einmalig (lru_cache). Für `~/.claude`-Konsumenten: optionaler
Vendor-Fallback-Pfad, kein Hard-Import auf mcp-hub.

### 4. CI-Validator (`check-model-resolver.py`, deterministisch)

1. Schema-Validierung.
2. Jeder `model` litellm-auflösbar (`litellm.get_model_info` ohne Exception).
3. Kein `-latest` (Regex-Block).
4. Kein verwaister Alias: jeder in Surfaces/Policies referenzierte
   `iil/<x>` existiert in `aliases` (grep mcp-hub + `policies/llm-routing.md`).
5. Exit≠0 bricht PR. Workflow on PR-paths `iil_routing/**`.

## Explizite Nicht-Ziele Phase 1

Keine Änderung an `model_selector.py` / `model_registry.py` / `review_adr.py`,
`log_llm_call.py`, dev-hub `aifw_*`, `policies/llm-routing.md`, adr-review-CLI.
Diese opten **danach** und einzeln ein (Phasenplan unten).

## Acceptance (Phase 1)

- [ ] `model_resolver.yaml` + Schema vorhanden, CI-Validator grün
- [ ] `resolve("iil/adr-review")` liefert korrekten Pin + sha; unbekannter Alias → KeyError
- [ ] `litellm`-Auflösbarkeit aller Modelle im CI bewiesen, 0 `*-latest`
- [ ] Reversibel: Verzeichnis entfernen → keine Konsumenten betroffen (da Phase 1 keine hat)

## Phasenplan (jede Phase = eigene PR + Owner)

| Phase | Inhalt | Repo | Risiko |
|---|---|---|---|
| **1** | Resolver-Kern (dieses Doc) | mcp-hub | niedrig |
| 2 | `log_llm_call.py` + adr-review-CLI: env→Alias (`ADR_REVIEW_MODEL=iil/adr-review`) | mcp-hub/platform | niedrig |
| 3 | mcp-hub Routing-Surfaces auf Aliase | mcp-hub | **mittel** (Live-Routing) |
| 4 | dev-hub `aifw_*` SQL-Migration | dev-hub | **mittel** |
| 5 | ADR-201-Statusline liest Resolver | ~/.claude | niedrig |

## Risiko/Lehren (eingebaut)

- **Pin-Disziplin:** CI verbietet `-latest` → ADR-203 Risiko #1–#4 strukturell aus.
- **Preis-Drift:** Flatrate = 0.0 + Provider-Usage als Ground-Truth (kein falsches Cost-Estimate).
- **Reproduzierbarkeit:** Konsumenten loggen `resolver_sha()` → Audit nachvollziehbar.
- **Kein Service:** reine Daten + Loader, Abgrenzung zum verworfenen ADR-199 (schwere Variante).
