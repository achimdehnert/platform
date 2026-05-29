---
title: Token-Reduction Strategy
date: 2026-05-11
author: Achim Dehnert
status: draft
context: Max-Plan-Quota schonen, vermeidbare Opus-Last reduzieren
data_basis: llm_calls (1123 calls / 7d, claude_code source)
---

# Konzept: Token-Verbrauch reduzieren

## 1. Truth-Source-Klärung (kritisch)

| Was wir messen | Was wir zahlen | Quelle |
|---|---|---|
| `cost_usd` in `llm_calls` (~$260/Tag heute) | **$0** zusätzlich — Max-Plan-Flatrate | API-Pricing × Token-Counts |
| Per-Turn-Tokens (Opus, Sonnet) | Verbrauchen **Max-Plan-Quota** | Anthropic Console (`claude.ai/settings/usage`) |
| OpenAI/OpenRouter via `task_pipeline` | **Real-paid** | Token-Counts × API-Preis |

**Wichtig**: Anthropic Admin API zeigt **nur API-Workspace-Calls**, nicht Max-Plan-CC-Traffic. Quota-Visibility nur via `claude.ai/settings/usage` (kein API-Endpoint). Echte-$-Visibility via Admin-API für `task_pipeline`/`agent_team`/`aifw`.

## 2. Was die Daten zeigen (letzte 7 Tage)

### Pro-Turn-Verteilung (Claude Code)

| Perzentil | Tokens |
|---|---|
| p50 | 84,845 |
| p90 | 198,872 |
| p99 | 347,166 |
| max | 370,185 |

**Median-Turn = 85k Tokens.** Die Hälfte aller Turns ist groß.

### Top-Sessions nach Verbrauch

| Session | Turns | Ø Tok/Turn | Total Tok | Notional $ |
|---|---|---|---|---|
| `cc-2132b232` (jetzt) | 193 | 217k | **42.0M** | $90.63 |
| `cc-41d3a1c2` | 127 | 100k | 12.7M | $29.98 |
| `cc-5dae04fd` | 107 | 83k | 8.8M | $18.55 |
| `cc-37b8f513` | 80 | 108k | 8.7M | $26.32 |
| `cc-92384772` | 82 | 105k | 8.6M | $23.35 |

### Per-Turn-Wachstum (Beispiel `cc-2132b232`)

```
turn  1:  27k tokens
turn 10:  63k
turn 20:  86k
turn 25: 111k
turn 50: ~150k   (extrapoliert)
turn100: ~250k   (extrapoliert)
turn193: 343k    (real, letzter Turn)
```

**Konversation wächst um ~3–4k Tokens pro Turn.** Bei 200 Turns landet jeder Turn bei 300k+.

### Overkill-Pattern

| Klasse | Calls | Total Tok | Notional |
|---|---|---|---|
| **overkill** (out<500 tok, in>100k) | 244 | 37.4M | $77.56 |
| maybe (out<500 tok, in>30k) | 223 | 14.6M | $46.19 |
| fine | 437 | 53.0M | $165.33 |

**22% aller Opus-Calls sind Overkill** — riesiger Input für winzige Antwort. Klassische "Was ist X?"-Fragen die ein Sonnet-Lookup auch geleistet hätte.

### Cache-Hit-Rate

`prompt_share = 0.99` über alle großen Sessions = **99% des Inputs ist Cache-Read** (0.1× Preis). Anthropic-Caching greift exzellent. Aber: Cache-Reads zählen voll zur Token-Quota auch wenn sie billig sind.

## 3. Ursachenanalyse (priorisiert)

| Ursache | Anteil am Tokenverbrauch | Mechanismus |
|---|---|---|
| **Lange Sessions ohne Reset** | ~60% | Konversation wächst linear, jeder Turn sendet bisherigen State |
| **Overkill-Calls auf Opus** | ~22% | Trivial-Antwort auf Riesen-Context |
| **Tool-Output-Akkumulation** | ~10% | grep/read-Output bleibt im Context, wird Turn-für-Turn re-gesendet |
| **CLAUDE.md / Memory-Bloat** | ~5% | Pro-Repo CLAUDE.md + globale Memory wird in jedem Turn mitgeschickt |
| **Echte Heavy-Reasoning** | ~3% | ADR-Review, komplexe Analyse — gerechtfertigter Opus-Einsatz |

## 4. Hebel (priorisiert nach Wirkung × Aufwand)

### H1 — Session-Discipline (höchster Impact, niedriger Aufwand)

**Problem**: 193-Turn-Sessions im selben Topic (siehe `cc-2132b232` heute).
**Maßnahme**:
- **Neue Session** bei Themenwechsel — nicht "weiter im selben Chat"
- Faustregel: nach 30 Turns prüfen ob Topic noch dasselbe ist; wenn nein → `Ctrl+L` (Clear) oder neue Session
- `/clear` löscht Konversation, neue Session beginnt bei ~5k Tokens statt 200k+
- Erwartete Reduktion: **50–70 %** auf Long-Tail-Sessions

**Quantifizierung**: heute `cc-2132b232` = 42M Tokens. Bei 5 Sessions à 38 Turns statt 1 Session à 193 Turns: ~12M Tokens (= 71% Reduktion).

### H2 — `/compact` periodisch (moderater Impact, kein Aufwand)

**Problem**: Auch innerhalb sinnvoller Sessions wächst Context.
**Maßnahme**:
- Alle ~30 Turns oder bei Erreichen von ~100k Total-Context: `/compact`
- CC erstellt eine Zusammenfassung, ersetzt frühere Turns
- Erwartete Reduktion: **30–50 %** auf die Folge-Turns

### H3 — Model-Switching pro Subtask (hoher Impact, manuell)

**Problem**: Sonnet-Quota = **0%** genutzt, alles auf Opus.
**Maßnahme**:
- `/model sonnet` für: File-Lesen + Zusammenfassen, Tool-Glue, Status-Checks, Linting-Output
- `/model haiku` für: einzelne Lookups, Boolean-Fragen, einfache Klassifikation
- `/model opus` nur für: Reasoning-heavy (ADR-Analyse, Architektur, komplexer Code)
- Erwartete Reduktion: **40–60 %** Opus-Quota-Last bei gleichem Output

**Quantifizierung**: 244 Overkill-Calls × 200k Ø = 49M Tok → wenn auf Sonnet (3x cheaper): gleiche Token-Anzahl, aber **schont Opus-Quota komplett** und nutzt freie Sonnet-Quota.

### H4 — `task_pipeline` als MCP-Tool (hoher Impact, bereits gebaut)

**Problem**: Sub-Aufgaben (Listen, Audit, simple Code) laufen in Opus statt delegiert.
**Maßnahme**:
- CC ruft `orchestrator__plan_and_execute(prompt)` für delegierbare Sub-Aufgaben
- Pipeline routed via Matrix → gpt-4o-mini / gpt-4o → **0 Anthropic-Quota**
- Setup ist live (siehe ADR-Konversation heute)
- Erwartete Reduktion: **100 % auf delegierte Subtasks** (= komplett quota-frei)

**Wann anwenden**: Tasks die als "List", "Audit", "Generate Tests", "Refactor X to Y" beschreibbar sind.

### H5 — Tool-Output-Hygiene (mittlerer Impact, technisch)

**Problem**: `grep` mit `head -100` bleibt im Context — nächste 50 Turns sehen diese 100 Zeilen jedesmal.
**Maßnahme**:
- Pro Tool-Call nur das Minimum lesen (`head`, `tail`, `--limit`, gezielte Pfade)
- Bei großen File-Reads: zuerst `wc -l`, dann gezielter Range
- Hook-Idee: `PostToolUse` für `Bash` truncated Outputs > 5k Zeichen mit Hinweis
- Erwartete Reduktion: **5–15 %** Baseline pro Session

### H6 — CLAUDE.md-Diet (niedriger Impact, einmaliger Aufwand)

**Problem**: Jeder Turn schickt CLAUDE.md + Memory mit. Wenn die 5k Tokens groß sind, summiert sich das.
**Maßnahme**:
- CLAUDE.md auf < 2k Tokens halten
- MEMORY.md unter 200 Zeilen (System sagt nach 200 wird truncated — ist also schon implementiert)
- Erwartete Reduktion: **3–8 %** Baseline pro Turn

## 5. Was NICHT funktioniert (geprüft / verworfen)

| Idee | Warum nicht |
|---|---|
| CC-Modell zentral auf Sonnet zwingen | CC-Sessions sind kontextgebunden — Opus-Routing für Reasoning oft gerechtfertigt |
| Pre-Session-Hook der Modell vorschlägt | LLM-Klassifikation der ersten Nachricht kostet selbst Tokens; ROI fraglich |
| Auto-`/compact`-Hook nach N Turns | CC unterstützt Hooks aber nicht Modifikation der laufenden Konversation |
| ADR-194 Universal-Gateway | SPoF + Bootstrap-Paradox; siehe Reviews |
| OpenRouter für alles | 5% Markup, US-Daten-Routing, CC-Compat-Risiko |

## 6. Aktionsplan

| Phase | Maßnahme | Aufwand | Erwartete Reduktion | Verantwortlich |
|---|---|---|---|---|
| **Sofort** | Session-Discipline (H1) — Faustregel "neue Session bei Themenwechsel" | 0 | -50% | du |
| **Sofort** | `/model sonnet` für Routine-Tasks (H3) | 0 | -40% Opus-Quota | du |
| **Sofort** | `task_pipeline` MCP-Tool für delegierbare Subtasks (H4) | 0 | -100% auf delegiert | du (bei jedem passenden Prompt) |
| **Diese Woche** | Tool-Output-Hygiene-Hook (H5) | ~1 PT | -5–15 % | mir, falls gewünscht |
| **Diese Woche** | CLAUDE.md-Audit pro Repo (H6) | ~0.5 PT | -3–8 % | du oder mir |
| **2 Wochen** | Wöchentlicher Token-Report (Memory-Pflege "selbstlernende Matrix" Stufe 2) | ~1 PT | Sichtbarkeit | mir |
| **2 Wochen** | Dashboard-Panel "Top Overkill-Calls" | ~0.3 PT | Awareness | mir |

## 7. Messgrößen

Erfolg messen anhand:
1. **Avg-Tokens-per-Turn** (Ziel: p50 < 50k, p90 < 150k — heute 85k / 199k)
2. **Wöchentliche Anthropic-Max-Quota** (claude.ai/settings/usage — Ziel: <50% bei aktueller Workload)
3. **Sonnet-Quota-Auslastung** (heute: 0% — Ziel: 20–40% = Opus-Entlastung)
4. **Tasks via `plan_and_execute`** (heute: ~5 — Ziel: alle delegierbaren Sub-Aufgaben)
5. **Anteil "overkill"-Calls** (heute 22% — Ziel: <10%)

## 8. Offene Fragen

1. **Hat Anthropic einen Pre-Session-Model-Picker?** Wenn CC eine "auto-mode" oder Routing-API anbietet (Claude Code Speed Mode beta `fast-mode-2026-02-01`), könnte das Modell pro Turn dynamisch wählen. Stand 2026-01: nur statisches `/model`.
2. **`/compact` Quality-Loss messbar?** Wenn Compact wichtige Details vergisst, kann's teurer werden weil Re-Erklärung nötig. Erst beobachten.
3. **Wann lohnt sich `task_pipeline` nicht?** Bei Tasks die echtes Reasoning + großen Codebase-Context brauchen (z.B. "audit this ADR"), ist Opus im CC besser. Faustregel: wenn Sub-Task selbständig formulierbar ist und Output kompakt, dann delegieren.
