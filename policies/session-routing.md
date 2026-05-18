# Policy: Claude Code Session Routing

**Trigger words:** session, opus, sonnet, /fast, /model, session model,
welcher modus, which mode, claude code modus

## Rule

Claude Code session-level model choice should follow the same tier-discipline
as the action-level `llm-routing.md` policy. The current default — running
every session on Opus 4.7 — is **Tier 4** in policy terms and meant for
"agentic flows, complex synthesis, only with explicit justification".
Most day-to-day work (lint cleanup, model-string sweeps, drift workflows,
log inspections, deploy checks) is Tier 3 at most.

Concrete spend evidence — 2026-05-13 in this repo's `llm_calls` table:

| Date | Calls | Cost (USD) | Model |
|---|---|---|---|
| 2026-05-13 | 1554 | **$608** | claude-opus-4-7 |
| 2026-05-12 | 2233 | **$969** | claude-opus-4-7 |

At Sonnet pricing ($3/$15 vs Opus $15/$75) those two days would have been
~$120 + ~$190 = ~$310 instead of $1577. The work product would be
indistinguishable for the kinds of tasks that ran.

## Tier map for Claude Code sessions

| Task type | Recommended | Why |
|---|---|---|
| ADR drafting / architectural reasoning | **Opus 4.7** | Real Tier-4 work — synthesis across many ADRs and policies |
| Multi-repo refactor with cross-file implications | **Opus 4.7** | Tier-4 reasoning load |
| Code review of someone else's PR | **Sonnet 4.6** | Tier 3 — sufficient for review depth |
| Single-PR implementation (bug fix, feature) | **Sonnet 4.6** | Tier 3 |
| Lint cleanup / mass rename / mechanical edits | **Sonnet 4.6** or `/fast` | Tier 3 or Tier 2 |
| Log inspection / DB queries / deploy babysitting | `/fast` (Opus 4.6) | Same model family, faster output |
| Quick "what does this do" / status checks | `/fast` | Cache-friendly, low complexity |

## How to apply

- **At session start**: choose the appropriate model via `/model` based on the
  intended work for that session. Do not start on Opus 4.7 and stay there by
  default.
- **Mid-session**: if the workload changes (e.g. finished the architectural
  part, now doing mechanical follow-up edits), call `/model` to step down.
- **`/fast` toggle**: stays on the Opus 4.X family but with faster output —
  useful when you want Opus reasoning depth on a long context but reduced
  per-turn latency. Same cost class as regular Opus.

## What the assistant should do

When the assistant notices a session running on Opus 4.7 doing predominantly
Tier-3-or-below work, it should mention this once early in the session —
not every turn — with a concrete recommendation. Example:

> "This session is on Opus 4.7. The work I see queued is lint cleanup +
> running a couple of deploys — Tier 3/2 in `llm-routing.md` terms. A `/model`
> swap to Sonnet 4.6 would cut spend by ~5× without affecting outcome quality
> on this kind of work. Want me to remind once or never?"

Do not nag.

## Per-repo / org overrides

- ttz-lif / meiki-lra: same logic but choice is constrained to what's available
  via Ollama-local — see the per-repo CLAUDE.md.
- Sessions that run *over* CI (headless_runs, ultrareview) follow `llm-routing.md`
  for the agent / action_code, not this policy.

## Changelog

- 2026-05-13: Initial. Promoted after observing $1577 / 5969 Opus calls in
  24 hours of Claude Code session work that was almost entirely Tier-3 in
  scope (PR drafting, lint cleanup, drift sweeps). See dev-hub#39.
