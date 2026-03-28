# Hub Visual Identity System (ADR-051)

> **AI-Resistant Design DNA + Automated Mutation Engine**
> Jeder Hub hat eine kodierte Persönlichkeit — messbar, automatisiert, zukunftssicher.

---

## Quick Start

```bash
# 1. Install
make install

# 2. Validate all DNA schemas
make validate

# 3. Generate all CSS token files
make generate

# 4. Audit AI fingerprint scores
make audit

# 5. Mutate failing hubs (requires ANTHROPIC_API_KEY)
make mutate
```

---

## Architecture

```
hub_dnas/{hub}.yaml          ← Source of Truth (edit this)
    ↓  make generate
generated/pui-tokens-{hub}.css  ← Include in base.html
    ↓  make audit
reports/audit-report.json    ← CI gate (score < 40)
    ↓  make mutate
hub_dnas/{hub}.yaml (evolved) ← Auto-updated by Claude API
```

---

## Hub DNA Files (14 Hubs)

| Hub | Personality | Aesthetic | Fonts |
|-----|-------------|-----------|-------|
| bieterpilot | industrial authority | institutional-minimalism | Syne + Barlow |
| risk-hub | analytical precision | terminal-precision | Syne + Manrope |
| travel-beat | wanderlust editorial | editorial-travel | Playfair + Work Sans |
| weltenhub | cosmic ambition | cosmic-editorial | Fraunces + Nunito |
| pptx-hub (Prezimo) | bold creative | creative-professional | Plus Jakarta + DM Sans |
| coach-hub | warm growth | organic-warmth | Lora + Figtree |
| billing-hub | financial clarity | financial-clarity | DM Serif + Lexend |
| trading-hub | terminal speed | terminal-dark | Barlow Condensed + Barlow |
| cad-hub | engineering rigour | technical-blueprint | Yantramanav + Barlow |
| research-hub | intellectual depth | scholarly-editorial | Crimson Pro + Work Sans |
| mcp-hub | AI-native tooling | cyber-technical | Outfit + Manrope |
| doc-hub | archival permanence | archival-warmth | Newsreader + DM Sans |
| bfagent | agent intelligence | ai-native-precision | Lexend + Figtree |
| dev-hub | developer portal | developer-portal | Plus Jakarta + Manrope |

---

## Integrating in Django

### 1. In `base.html` (per hub)

```html
{# Load hub-specific tokens — replaces pui-tokens.css from ADR-049 #}
{% load static %}
<link rel="stylesheet" href="{% static 'css/pui-tokens-{{ APP_NAME }}.css' %}">
```

### 2. Deploy generated CSS

Copy `generated/pui-tokens-*.css` into each hub's `static/css/` directory,
or serve from a shared static directory.

### 3. Context Processor (existing, ADR-049)

```python
# config/context_processors.py
def app_metadata(request):
    return {"APP_NAME": settings.HUB_NAME}
```

---

## Adding a New Hub

1. Create `hub_dnas/{hub-name}.yaml` using an existing file as template
2. Run `make validate` to check the schema
3. Run `make generate HUB={hub-name}` to generate CSS
4. Run `make audit HUB={hub-name}` to check fingerprint score
5. If score >= 40: `make mutate HUB={hub-name}`

---

## Mutation Engine

The mutation engine uses Claude API to evolve hub DNA when fingerprint scores
are too high (>= 40). It preserves brand personality while eliminating patterns
that AI detection tools recognize.

```bash
# Requires ANTHROPIC_API_KEY in environment
export ANTHROPIC_API_KEY=sk-ant-...

# Mutate all failing hubs
make mutate

# Aggressive mutation for high scores
make mutate STRENGTH=high

# Preview without API calls
make mutate-dry
```

Mutated DNA is staged in `hub_dnas/_mutated/` for review before being merged
back to `hub_dnas/`. In CI, this happens automatically via PR.

---

## Updating Detection Patterns

As new AI fingerprint detection methods emerge:

1. Add patterns to `detection_patterns/ai_patterns_v2.yaml` (new version file)
2. Run `make audit` — scores will update automatically
3. Run `make mutate` for any hubs that now fail the new threshold

The versioned pattern files ensure auditability of what patterns were active
at any point in time.

---

## CI Gate

The `design-audit.yml` workflow runs on every PR that touches `hub_dnas/`,
`detection_patterns/`, or `tools/design_dna/`. It posts a score table to the PR
and fails the check if any hub scores >= 40.

The `design-mutate.yml` workflow runs quarterly and can be triggered manually.
It creates a PR with updated DNA files for review.
