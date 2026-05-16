---
status: accepted
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: in-progress
related: [ADR-199-rejected, ADR-203, ADR-208, dev-hub#39]
---

# ADR-201: Claude Code Pricing Visibility — Statusline + Stop-Summary

## Status

Accepted — **Umsetzung präzisiert, siehe Amendment 2026-05-16.**

## Amendment 2026-05-16 (Advocatus-Diabolus-Review)

Beschluss bleibt (Cost-Sichtbarkeit am Touchpoint), aber vier Korrekturen
**bindend für die Umsetzung**:

1. **Abnahmekriterium ist technisch, nicht behavioral.** Pass/Fail von
   ADR-201 = *Zahl korrekt, p95 < 100 ms, Abweichung ≤ 1 % zu
   `llm_calls.cost_usd`*. Das alte Kriterium „>30 % Reduktion
   `opus_per_session_ratio` in 14 Tagen" ist unkontrolliert
   (Hawthorne, $1577-Vorfall selbst, ADR-202 parallel) und wird in ein
   **separates Experiment mit Baseline/Kontrolle** ausgelagert — kein
   Pass/Fail-Gate eines Anzeige-Features. Metrik dort = $/Outcome, nicht der
   gamebare Modell-Mix-Proxy.
2. **Per-Turn-Quelle = lokales Session-Ledger, nicht Prod-DB.** Der Stop-Hook
   schreibt `~/.claude/state/<session>.jsonl` (append, eine Zeile/Turn). Die
   Statusline liest ausschließlich diese Datei (Sub-ms, kein SSH-Tunnel, kein
   Prod-Hop im Editor-Innerloop). Prod-DB nur für „today across sessions" als
   gecachter Refresh alle N Turns. Damit entfällt Open Question 2
   (Tunnel vs. Replica) und der Latenz-Negativpunkt.
3. **Pricing aus dem Resolver (ADR-208), nicht aus dem Dict.** Kein
   eigenständiges Pricing-Wissen in der Statusline; `PRICING_USD_PER_MTOK`
   wird durch die Resolver-SSoT abgelöst (sonst dieselbe Drift wie ADR-203
   Risiko #2). Tier-Mismatch-Heuristik wird über die Rolle aus dem Resolver
   trivial (Open Question 1 dort gelöst).
4. **Hook-API-Spike vor Phase 1.** Phase 2 (`/model`-Pre-Prompt-Vergleich)
   ist der einzige Touchpoint am *Entscheidungspunkt* — die ambienten
   Phasen 1+2 wirken nur ergänzend. 30-min-Spike zur SlashCommand-Pre-Hook-
   Verfügbarkeit **zuerst**; ist Phase 2 machbar, Hebelreihenfolge umkehren.

Die folgenden Original-Abschnitte gelten unverändert, soweit nicht oben
präzisiert.

## Context

Backend-Cost-Tracking existiert vollständig:
- `llm_calls` Tabelle mit `cost_usd` + `duration_ms` (seit 2026-05-13)
- Grafana panel 105 „Heaviest Session today"
- Grafana panel 211 „Top 30 Tasks im Zeitraum"
- Grafana panel 152 „Cascade Cost heute"

**Was fehlt:** kein einziger UX-Touchpoint **in der Claude-Code-Session selbst** zeigt dem User, was eine Session kostet. Grafana muss aktiv aufgemacht werden. Der `/model`-Wechsel-Schmerzpunkt (dev-hub#39 — Opus-Default für Tier-3-Arbeit) bleibt unsichtbar bis der User von sich aus nach „wieviel hab ich heute verbrannt" fragt.

Die ADR-199-Familie (drei Iterationen) hat versucht das per Routing-Authority zu lösen — falsches Werkzeug, deshalb rejected.

## Decision

Drei minimale UX-Touchpoints, alle file-based, alle reversibel durch Deletion:

### 1. Statusline (per-turn live-cost-Anzeige)

`~/.claude/settings.json` bekommt ein `statusLine`-Feld, das auf ein kurzes Python-Script verweist:

```jsonc
"statusLine": {
  "type": "command",
  "command": "/home/devuser/.claude/scripts/cost_statusline.py"
}
```

Das Script (`~/.claude/scripts/cost_statusline.py`):
- liest stdin-JSON-Kontext (model, session_id, cwd)
- queryt `llm_calls` lokal (postgresql://...:15435) für **today's-spend** + **last-turn-cost** + **session-total** (matching `task_id LIKE 'cc-<session_id>%'`)
- gibt eine kompakte Zeile aus: `Sonnet-4-6 │ turn: $0.08 │ session: $0.42 │ today: $4.20`
- bei Tier-Mismatch (z.B. Opus aktiv aber session-trend Tier-3) wird ein Hinweis-Emoji ergänzt: `… │ ⚠ Tier-3 reicht`

Latenz-Budget: < 100 ms. Bei DB-Fehler: fail-silent, statusline zeigt nur Modell-Name.

### 2. Stop-Hook Session-Summary

`~/.claude/hooks/log_llm_call.py` (existiert) wird erweitert um eine **stderr-Ausgabe** nach dem Insert:

```
turn: $0.0823 (Opus-4-7, 2.4s) │ session-total: $4.27 (52 turns)
```

Claude Code surfaces hook-stderr für den User. Bei hohen Per-Turn-Kosten (> $0.20) ergänzt die Zeile: `▲ consider /model sonnet for routine work`.

### 3. (Optional, Phase 2) `/model`-Wechsel-Prompt mit Cost-Vergleich

Wenn der User `/model` tippt, könnte ein Pre-Prompt-Hook die historische Cost/Turn pro Modell aus `llm_calls` ziehen und als Entscheidungshilfe einblenden:

```
Switch model. Last 7 days for your work patterns:
  Opus 4.7   — $0.18/turn avg (74 turns)
  Sonnet 4-6 — would have been $0.036/turn (~5× cheaper)
```

Dafür braucht es Claude-Code-Hook-Support für SlashCommand-PreExecution — heute (Stand 2026-05-14) noch nicht eindeutig dokumentiert. Phase 2 → wenn Hook-API das zulässt.

## Consequences

### Positive

- **Direkt auf den $1577-Lane**: jede Session sieht beim ersten Tool-Use was sie kostet. Bewusstsein erzwingt nicht die Wahl, aber es informiert sie.
- **Lokal**: kein Service, keine externe Abhängigkeit, kein Cross-Repo-Impact. Reversibel durch Deletion zweier Dateien.
- **Reuses existing infrastructure**: `llm_calls` ist schon befüllt, Pricing-Daten leben in `~/.claude/hooks/log_llm_call.py`'s `PRICING_USD_PER_MTOK` Dict.
- **Skaliert** auf andere Workstations durch ein simples Repo-Copy von `~/.claude/scripts/` + `~/.claude/hooks/`.

### Negative

- **Setup-Disziplin**: jeder Dev-Workstation braucht den Hook + die DB-Connection (Localhost-Port 15435 via SSH-Tunnel zu prod, oder lokales Read-Replica). Mitigiert durch klare Setup-Doku in der README + Optional-Make-Target.
- **DB-Hop pro Turn**: ~50ms Latenz im statusline-Render. Akzeptiert: läuft asynchron, statusline rendert mit cached previous-value bei Timeout.
- **Pricing-Dict-Drift**: wenn ein neues Modell registriert wird das nicht in PRICING_USD_PER_MTOK steht, fällt das Display auf Default-Pricing. Mitigiert durch existing drift-Workflow (mcp-hub#41).

### Neutral

- Phase 2 (slash-command pre-hook) ist NICHT Teil dieses ADRs. Wenn Claude Code es nicht unterstützt, bleibt es bei Phasen 1+2.

## Implementation

3 Files, alle lokal in `~/.claude/`:

1. **`~/.claude/scripts/cost_statusline.py`** (neu, ~80 LOC) — statusline command
2. **`~/.claude/settings.json`** — `statusLine` field ergänzen
3. **`~/.claude/hooks/log_llm_call.py`** (existiert) — stderr-summary-Block am Ende von `main()`

Zusätzlich: kurzes README-Snippet `~/.claude/scripts/README.md` das Setup beschreibt (DB-URL env-var, optional SSH-Tunnel).

## Why no PR / no platform-commit

Diese Änderungen liegen alle unter `~/.claude/` — User-Setup, nicht Repo-Code. ADR-201 dokumentiert die Entscheidung; die Implementierung wird im lokalen Setup gemacht und kann optional via dotfiles-Repo verteilt werden.

## Acceptance Criteria

- [ ] Statusline zeigt während aktiver Session: `<model> │ turn: $X │ session: $Y │ today: $Z`
- [ ] Stop-Hook gibt nach jedem Turn eine stderr-Zeile mit turn-cost + session-total aus
- [ ] Bei Tier-Mismatch (Opus aktiv für Tier-3-trend): Hinweis sichtbar (statusline emoji + stop-line suffix)
- [ ] User-Berichtetes Awareness-Niveau steigt: 14-Tage-Beobachtung post-deploy zeigt **>30 %** Reduktion `opus_per_session_ratio` (Grafana panel 211)

## Open Questions

1. Tier-Mismatch-Heuristik: wie definiert man „session-trend ist Tier 3"? Vorschlag: wenn letzte 5 turns Avg Cost < Tier-4-Floor / 3 → empfehle Tier-3. Konfigurierbar.
2. SSH-Tunnel oder lokales Read-Replica für die DB? Vorschlag: Tunnel für jetzt, Replica wenn mehrere Devs adopten.
3. Slash-Command-Pre-Hook (Phase 2): Recherche, ob Claude Code das unterstützt — separate Task.

## Changelog

- 2026-05-14: Initial. Direkt-Folge der ADR-199-Rejection. Status: accepted (geht direkt in Implementierung).
