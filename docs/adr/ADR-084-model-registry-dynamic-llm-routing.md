---
status: accepted
date: 2026-02-25
implemented: 2026-02-25
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-068-adaptive-model-routing.md
related: ADR-068, ADR-082, ADR-045, ADR-080
---

# ADR-084: Model Registry — Dynamisches LLM-Modell-Routing mit datenbankgestützter Tier-Verwaltung

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Accepted                                                             |
| **Scope**      | Platform-wide — AI Infrastructure                                    |
| **Repo**       | platform / mcp-hub                                                   |
| **Erstellt**   | 2026-02-25                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Reviewer**   | –                                                                    |
| **Supersedes** | –                                                                    |
| **Amends**     | ADR-068 (Adaptive Model Routing) — erweitert Tier-Konzept            |
| **Relates to** | ADR-068 (Routing), ADR-082 (LLM-Tool-Integration), ADR-045 (Secrets), ADR-080 (Multi-Agent) |

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-25 | Achim Dehnert | v0: Initial Draft — PostgreSQL Model Registry, Tier-Abstraktion, OpenRouter-Sync |
| 2026-02-25 | Achim Dehnert | v1: Review-Fixes — Decision Drivers, ADR-075-Konformität, Confirmation, Migration-Tracking |
| 2026-02-25 | Achim Dehnert | v2: Status Proposed → Accepted nach Review |
| 2026-02-26 | Achim Dehnert | v3: **Groq Provider Amendment** — 9 Groq-Modelle, Migration 002, erweiterte TierRules, Provider-Constraint |

### v3 Amendment: Groq Provider Integration (2026-02-26)

**Änderungen:**

1. **Schema:** `chk_provider` Constraint erweitert um `'groq'`, `'moonshot'`, `'alibaba'`, `'meta'`
2. **Migration:** `registry_mcp/migrations/002_add_groq_provider.sql`
3. **TierRules:** 9 neue Groq-spezifische Mapping-Regeln in `model_registry_updater.py`
4. **Seed-Daten:** 9 Groq-Modelle (alle `is_active=TRUE`, `is_default_for_tier=FALSE`)

**Neue Groq-Modelle:**

| Model | Tier | Context | Besonderheit |
|-------|------|---------|-------------|
| `qwen-qwen3-32b` | standard | 131k | Bestes Coding-Modell auf Groq |
| `openai-gpt-oss-120b` | premium | 131k | Größtes Modell auf Groq |
| `openai-gpt-oss-20b` | budget | 131k | Klein + schnell |
| `llama-3.3-70b-versatile` | standard | 131k | Bewährter Workhorse |
| `llama-4-scout-17b-16e-instruct` | standard | 512k | MoE, riesiger Context |
| `llama-3.1-8b-instant` | budget | 131k | Ultra-schnell, einfache Tasks |
| `groq-compound` | premium | 131k | Agentic System mit Tool Use |
| `groq-compound-mini` | budget | 131k | Leichterer Agentic |
| `kimi-k2-instruct-0905` | standard | 131k | Moonshot MoE via Groq |

**Groq-Playground zum Testen:** https://console.groq.com/playground
