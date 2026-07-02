# Policy: Claude Code Session Routing

**Trigger words:** session, opus, sonnet, /fast, /model, session model,
welcher modus, which mode, claude code modus

## Rule

Claude Code session-level model choice should follow the same tier-discipline
as the action-level `llm-routing.md` policy. As of 2026-07, the top generally
available tier is **Fable 5** (`claude-fable-5`, Mythos-class — sits *above*
Opus). It is meant for "agentic flows, complex synthesis, only with explicit
justification" — and because it is the most expensive tier, defaulting a whole
session to it for routine work is the same anti-pattern the spend data below
flags, only sharper. Most day-to-day work (lint cleanup, model-string sweeps,
drift workflows, log inspections, deploy checks) is Tier 3 at most.

Concrete spend evidence — 2026-05-13 in this repo's `llm_calls` table:

| Date | Calls | Cost (USD) | Model |
|---|---|---|---|
| 2026-05-13 | 1554 | **$608** | claude-opus-4-7 |
| 2026-05-12 | 2233 | **$969** | claude-opus-4-7 |

At Sonnet pricing ($3/$15 vs Opus $15/$75) those two days would have been
~$120 + ~$190 = ~$310 instead of $1577. The work product would be
indistinguishable for the kinds of tasks that ran. (Numbers are Opus-4.7-era;
the ratio only widens with Fable on top — the principle scales, re-measure via
the `llm_calls` table, don't trust these exact figures.)

## Tier map for Claude Code sessions (Claude 5 family)

| Task type | Recommended | Why |
|---|---|---|
| Multi-agent orchestration (`/repo-optimize`, `/platform-audit`, adversarial falsification) | **Fable 5** | Frontier synthesis + judging across many agent outputs — the tier's home turf |
| ADR drafting / architectural reasoning with cross-repo or security/reversibility stakes | **Fable 5** | Real Tier-4 work — synthesis across many ADRs and policies |
| Heavy single-repo reasoning / large multi-file implementation / thorough design review | **Opus 4.8** | Hard but not frontier — Opus reasoning without the Mythos premium |
| Code review of someone else's PR | **Sonnet 5** | Tier 3 — sufficient for review depth |
| Single-PR implementation (bug fix, feature) from a clear spec | **Sonnet 5** | Tier 3 |
| Lint cleanup / mass rename / mechanical edits | **Sonnet 5** or `/fast` | Tier 3 or Tier 2 |
| Log inspection / DB queries / deploy babysitting / status checks | **Haiku 4.5** or `/fast` | Cheap, fast, low complexity |

Model IDs: `claude-fable-5` · `claude-opus-4-8` · `claude-sonnet-5` · `claude-haiku-4-5-20251001`.

## How to apply

- **At session start**: choose the appropriate model via `/model` based on the
  intended work for that session. Do not start on Fable/Opus and stay there by
  default.
- **Mid-session**: if the workload changes (e.g. finished the architectural
  part, now doing mechanical follow-up edits), call `/model` to step down. This
  works with the running context preserved — switching does not reset the session.
- **`/fast` toggle**: stays on the Opus family with faster output — useful when
  you want Opus reasoning depth on a long context but reduced per-turn latency.
  Same cost class as regular Opus (available on Opus 4.8/4.7).

## Who can switch the model (and who cannot)

Tier discipline is only actionable if you know which lever exists:

- **The model cannot switch itself.** There is no self-escalation and no tool
  for the assistant to change its own running session model. `/model` is a
  user-only CLI command. `/escalate` is a *user trigger* that only prints a
  recommendation — it does not swap the model. Do not claim "I'll downshift".
- **The user switches the interactive session** via `/model` (mid-session, context
  preserved). That is the escalation/de-escalation path for a single session.
- **The assistant routes per delegated task, not per self.** When it fans work out
  to subagents (Agent / Task / Workflow tools), it sets each subagent's `model`
  independently — e.g. a Fable main loop spawning Sonnet finders. Same for
  `orchestrator__*` / `headless_run`, which pick the model per action/job. This
  is the real "up/downshift by task": choose the executor's tier, don't expect a
  model to re-tier itself.

## Fable-session: do vs. delegate (producer / consumer + labels)

A Fable-tier session is expensive; spending it on Tier-3 execution wastes the tier.
The pattern:

- **Do inline** the Tier-4 part (analysis, design, decision, orchestration) **and**
  anything trivial (a 2-line fix costs less done than delegated — there is a floor).
- **Delegate** bounded, clear-pattern implementation by writing an **execution-ready
  issue** (files, exact change, test plan, pitfalls — so the executor need not
  re-reason) labelled `model:sonnet-5` or `model:opus-4-8`.
- **Consumer** = a session of that tier: the human runs `/model <tier>` then
  `/issues-offen` / `/issues-abarbeiten` filtered on the label, or the headless
  queue picks it up. (Model-label-aware routing in `process-agent-queue` is a
  future extension, not yet wired — until then a human starts the right-tier session.)
- The label is a **recommendation to the consumer**, not self-routing — see the
  section above on who can switch.

## What the assistant should do

When the assistant notices a session running on a tier above the queued work
(e.g. Fable/Opus doing predominantly Tier-3-or-below work), it should mention this
once early in the session — not every turn — with a concrete recommendation. Example:

> "This session is on Fable 5. The work I see queued is lint cleanup + a couple of
> deploys — Tier 3/2 in `llm-routing.md` terms. A `/model` swap to Sonnet 5 would
> cut spend sharply without affecting outcome quality on this kind of work. Want me
> to remind once or never?"

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
- 2026-07-02: Claude 5 family update. Tier map re-based on Fable 5 (Mythos,
  new Tier-4 top) / Opus 4.8 / Sonnet 5 / Haiku 4.5 + model IDs. Added
  "Who can switch the model" (self-switch is impossible; `/model` is user-only;
  `/escalate` only recommends; the assistant routes per-subagent, not per-self)
  and "Fable-session: do vs. delegate" (execution-ready issues + `model:sonnet-5`
  / `model:opus-4-8` label convention, consumed by a right-tier session or the
  headless queue). Old spend figures kept but flagged Opus-4.7-era. Grounded in a
  session where a Fable main loop delegated 8 `/repo-optimize` finders to Sonnet.
