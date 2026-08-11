---
status: proposed
decision_date: 2026-08-11
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: []
implementation_status: not_started
last_reviewed: 2026-08-11
staleness_months: 6
tags: [llm, aifw, speicher, architektur, gateway]
---

# ADR-294: LLM-Gateway statt litellm in jedem Prozess

## Kontext

Die RAM-Baseline der Flotte (platform#1899, `docs/analysis/2026-08-11-fw-speicher-baseline.md`)
hat gezeigt: der litellm-Import kostet ~190 MiB RSS pro Python-Prozess. Seit iil-aifw 0.11.7
(aifw#40) ist der Import **lazy** — Prozesse ohne LLM-Verkehr (beat, viele Worker) sparen die
190 MiB dauerhaft (gemessen: beat 225→88 MiB, web 333→169 MiB direkt nach Deploy).

Ungelöst bleibt: **jeder Prozess, der auch nur einen LLM-Call macht, lädt litellm wieder
voll** — bei N LLM-aktiven Prozessen zahlt der Host N × ~190 MiB. litellm bringt dabei
Provider-Abstraktion, Routing und Kostendaten mit, die aifw nutzt (`cost_per_token`,
`acompletion`).

## Entscheidung (vorgeschlagen)

Ein zentraler **LLM-Gateway-Prozess** je Host (Kandidat: bestehender mcp-hub/llm_mcp oder
ein schlanker aifw-Serve-Modus) übernimmt alle litellm-Aufrufe. aifw erhält ein zweites
Backend `AIFW_BACKEND=gateway`, das statt `litellm.acompletion` einen HTTP-Call
(httpx, lokales Loopback/Docker-Netz) an den Gateway macht. Default bleibt `local`
(litellm in-process) — Migration pro Repo per Env-Umschaltung, jederzeit reversibel.

## Konsequenzen

- (+) litellm-RSS fällt genau **einmal pro Host** an statt einmal pro LLM-aktivem Prozess.
- (+) Zentrale Stelle für Rate-Limits, Budget-Enforcement, Audit-Log (heute je Prozess).
- (−) Neuer Hop im LLM-Pfad: Latenz (< 5 ms Loopback) und ein neuer Single Point of
  Failure — Gateway braucht Healthcheck + Fallback (`local`-Backend als Notschalter).
- (−) Streaming muss durch den Gateway durchgereicht werden (SSE/chunked) — der
  aufwendigste Teil der Umsetzung.

## Voraussetzungen / offene Punkte vor Accept

1. **K4-Zahlen abwarten** (platform#1899): Wie viele Prozesse sind nach dem
   lazy-Rollout real LLM-aktiv (litellm resident)? Lohnt erst ab ~3+ Prozessen/Host.
2. Gateway-Kandidat entscheiden: mcp-hub/llm_mcp erweitern vs. aifw-Serve-Modus.
3. Groq-first-Routing (policies/llm-routing.md) muss unverändert greifen.

## Alternativen

- **Status quo (lazy litellm):** bereits umgesetzt; löst N×190 MiB für LLM-aktive
  Prozesse nicht.
- **litellm durch Direkt-SDKs ersetzen** (httpx je Provider in aifw): spart RAM ohne
  neuen Prozess, verliert aber litellms Provider-Breite und Kostendaten — höhere
  Pflegekosten in aifw.
