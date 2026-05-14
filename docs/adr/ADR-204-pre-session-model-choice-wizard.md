---
status: proposed
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-199-rejected, ADR-201, ADR-202-rejected, ADR-203-rejected, dev-hub#39]
---

# ADR-204: Pre-Session Model-Choice Wizard

## Status

Proposed — conditional. Wird implementiert **nur falls ADR-201 (Pricing Visibility) den Spend nach 14 Tagen nicht ausreichend reduziert** (Schwellwert: avg `opus_per_session_ratio` ↓ < 30 % über Baseline).

## Context

Nach Rejection von ADR-199 (3 Iterationen), ADR-202 (JIT — Tool-Call-Chains brechen es), ADR-203 (Alias — silent-drift) und Akzeptanz von ADR-201 (Visibility): bleibt **ein ungelöstes Workflow-Problem**.

dev-hub#39 dokumentierte: $1577 / 48 h auf Opus 4-7. Root-Cause war nicht Routing-Architektur, nicht Modell-Drift, nicht Bandit-Mangel — sondern:

> Der User wählt am Anfang einer Session `/model opus` weil er „komplexe Architektur-Arbeit" erwartet, macht dann aber 4 Stunden lint-cleanup auf demselben Opus-Modell.

ADR-201 macht den Spend **sichtbar** in der Session. **Aber zeigen ≠ ändern.** Der User kann den Statusline-Wert weiter ignorieren. 14 Tage Beobachtung post-ADR-201 wird zeigen ob Awareness alleine reicht.

Falls nicht: dieser ADR. Direkt am Workflow-Touchpoint statt am Routing- oder Visibility-Layer.

## Decision

Beim **ersten User-Prompt einer neuen Claude-Code-Session** zeigt ein UserPromptSubmit-Hook ein 3-Sekunden-Menü als injected context:

```
📋 Modell-Wahl für diese Session (3s Wizard)

Welche Arbeit erwartest du primär?

  [1] Architectural    → Opus 4-7   ($15/$75/M)    "ADR drafting, cross-cutting"
  [2] Multi-file refactor → Sonnet 4-6 ($3/$15/M)  "Real implementation work"
  [3] Single PR / bug fix → Sonnet 4-6 ($3/$15/M)  "Most common: code + tests"
  [4] Lint / format / mechanical → Haiku 4-5 ($1/$5/M)
  [5] Status checks / inspection → Groq 70B ($0.59/$0.79/M)

Default: [3] Sonnet 4-6  ·  Aktuell aktiv: <current_model>
↳ Beantworte mit `/model <name>` ODER ignoriere für default.
```

**Mechanismus** (keine echte Wizard-Interaktion — Claude Code kennt das nicht):
- Hook firet beim **ersten UserPromptSubmit** pro session (state via `~/.claude/hooks/state/<session>.json`)
- Hook prüft `current_model` (aus `~/.claude/settings.json` oder env)
- Falls aktuell Opus 4-7 + erste Userantwort nicht offensichtlich Tier-4 (Klassifizierung via Cerebras llama3.1-8b in ~$0.0001): empfehle Downgrade
- Output via UserPromptSubmit `additionalContext`: das Menü erscheint EINMAL pro Session vor dem ersten Tool-Use
- User reagiert mit `/model <new>` ODER tippt einfach weiter (= akzeptiert default)

## Implementation

Eine neue Datei `~/.claude/hooks/session_model_advisor.py`:

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook — fires at session start, recommends a model
based on the user's first message. Cerebras-classifies the prompt into
a tier and emits a 3-sec wizard as additionalContext.

ADR-204 Phase 1.
"""
# ~100 LOC: state check, Cerebras classify, output additionalContext JSON
```

Settings.json wird erweitert:

```jsonc
"UserPromptSubmit": [
  { "matcher": "", "hooks": [
    {
      "type": "command",
      "command": "/home/devuser/.claude/hooks/session_model_advisor.py",
      "timeout": 5
    },
    // existing inject_policies.py stays
    { "type": "command", "command": "/home/devuser/.claude/hooks/inject_policies.py", "timeout": 5 }
  ]}
]
```

State tracking via `~/.claude/hooks/state/<session_id>.json`:
```json
{ "wizard_shown": true, "first_classification": "tier-3", "shown_at": "2026-05-14T18:30:00Z" }
```

## Acceptance Criteria

- [ ] Hook firet **exakt einmal** pro Session (state file verhindert Doppel-Firing)
- [ ] Cerebras-Klassifikation dauert < 1 sek (sonst skip + show menu ohne classification)
- [ ] User-Adoption messbar: 14 Tage post-deploy zeigt `<modelswap_within_first_3_turns> / <total_sessions>` ≥ 40 %
- [ ] avg `opus_per_session_ratio` sinkt um ≥ 50 % vs. ADR-201-only-Baseline

## Risiken (ehrlich)

1. **3-Sek-Wizard ist Friction** — manche User wollen das nicht jeden Session-Start. Mitigation: opt-out via env var `IIL_SKIP_WIZARD=1`.
2. **Cerebras-Klassifikator-Fragility** — bei ambiguous prompts ("hilf mir") klassifiziert er random. Mitigation: bei Unsicherheit kein Hint, Wizard zeigt neutral.
3. **Hook-Latenz blockt UserPromptSubmit** — Claude Code wartet auf Hook-Completion (5sec timeout). Hook muss fail-fast bei Cerebras-Timeout.
4. **State-File-Pollution** — über Zeit sammeln sich State-Files. Mitigation: cleanup-Cron der >30-Tage-alte Files löscht.
5. **Doppel-Empfehlung mit Statusline** — Statusline (ADR-201) zeigt ständig Tier-Hint, Wizard auch beim Start. Redundanz akzeptiert: Wizard ist explizit-pflichtig, Statusline ist passiv.

## Why this is the right level (vs ADR-199/202/203)

| ADR | Layer | Erzwingt? |
|---|---|---|
| ADR-199 (rejected) | Routing-Service | Ja (komplett unter Mensch wegnehmen) |
| ADR-201 (accepted) | Display | Nein (Mensch sieht's, ignoriert vielleicht) |
| ADR-202 (rejected) | Per-Call Retry | Maschine entscheidet pro Call |
| ADR-203 (rejected) | Provider-Alias | Provider entscheidet |
| **ADR-204** | **Session-Start UX** | **User entscheidet einmal — aber bewusst** |

ADR-204 ist der **einzige Ansatz der den Mensch IM Loop hält + ihn explizit dazu auffordert die richtige Wahl zu treffen**. Das ist die UX-Antwort, nicht die Architektur-Antwort.

## Out-of-the-Box-Variante (optional Phase 2)

**Budget-Cap-Modus statt Wizard:** wenn User über `IIL_DAILY_BUDGET=20` ein Tagesbudget setzt, refused Claude Code weitere LLM-Calls nach Erreichen ohne explicit `/model --bypass-budget`. Direktes Behaviorist-Hebel — Wizard ist Sanft-Nudge, Budget ist Hard-Cap.

Phase 2 nur falls Wizard nicht reicht. Pattern derselbe (UserPromptSubmit-Hook), zusätzlicher Check `today_total < budget`.

## Changelog

- 2026-05-14: Initial. Status: proposed, conditional on ADR-201's 14-day spend measurement outcome. Direct successor to ADR-201, alternative to rejected ADR-202+203.
