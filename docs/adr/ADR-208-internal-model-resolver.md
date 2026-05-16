---
status: proposed
date: 2026-05-16
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-199-rejected, ADR-201, ADR-203, mcp-hub#37, mcp-hub#41]
---

# ADR-208: Interner Model-Resolver — versionierte Alias→Pin+Preis-Map (ohne Service)

## Status

Proposed — entstanden aus dem Advocatus-Diabolus-Review von ADR-201 + ADR-203
(2026-05-16). Schließt die Lücke, die beide bisher separat umgehen.

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

## Acceptance Criteria

- [ ] `model_resolver.yaml` existiert, GitOps-versioniert, CI-validiert (Schema + jeder `model` ist ein real auflösbarer litellm-String)
- [ ] mcp-hub Routing-Surfaces referenzieren `iil/<rolle>-current`, kein Provider-`-latest`, keine verstreuten Pins
- [ ] `log_llm_call.py` zieht Pricing aus dem Resolver; `PRICING_USD_PER_MTOK` entfernt; `cost_usd` unverändert akkurat (Regressionstest gegen 30 historische Calls)
- [ ] Jeder geloggte Call enthält aufgelösten Pin + Resolver-git-sha
- [ ] ADR-203-Amendment + ADR-201-Amendment referenzieren ADR-208

## Changelog

- 2026-05-16: Initial. Proposed. Konsolidiert die in ADR-201/203 verstreuten
  Workarounds zur leichten Essenz des verworfenen ADR-199.
