# Policy: Claude Code Session Routing
<!-- rule_class: B | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 (KONZ-038 D4) -->

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
drift workflows, log inspections, deploy checks) is T3 at most.

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

## Tier ladder (T5–T1)

One numbering across both routing policies. `llm-routing.md` uses the same rungs
for action-level API calls; this file maps Claude Code **sessions** onto them.

| Tier | Model | Model ID | $/1M in → out |
|---|---|---|---|
| **T5** | Claude Fable 5 | `claude-fable-5` | 10 → 50 |
| **T4** | Claude Opus 5 | `claude-opus-5` | 5 → 25 |
| **T3** | Claude Sonnet 5 | `claude-sonnet-5` | 3 → 15 (intro 2 → 10 until 2026-08-31) |
| **T2** | Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 1 → 5 |
| **T1** | Groq / Cerebras open models | see `llm-routing.md` | ~1–2 orders below T2 |

T1 is API-only — there is no Claude Code session on a non-Anthropic model. For
sessions the ladder starts at T2.

**Opus 4.8 (`claude-opus-4-8`, 5 → 25) is no longer the T4 default** — Claude
Opus 5 replaced it at identical pricing. Keep 4.8 only where a run must stay
reproducible against it; it is otherwise a strict downgrade at the same cost.

## Tier map for Claude Code sessions

| Task type | Recommended | Why |
|---|---|---|
| Multi-agent orchestration, fan-out layer (`/repo-optimize` finders/skeptics, `/platform-audit` sub-agents) | **T3 · Sonnet 5** | Bounded, spec'd sub-tasks — this is what the fan-out is *for* |
| Multi-agent orchestration, orchestrator layer (`/repo-optimize`, `/platform-audit`) — default | **T4 · Opus 5** | Large-context bookkeeping + moderate judgment (prompt design, dedupe against prior reports, synthesis into one report, PR triage) — not itself frontier reasoning in the typical run |
| … orchestrator layer — escalate to Fable mid-run | **T5 · Fable 5**, only on trigger | Escalate *once a concrete need appears*, not upfront: (a) a skeptic pass reports a genuine unresolved conflict between findings that a further Sonnet skeptic pass can't settle, (b) the report surfaces a novel cross-repo architecture trade-off with no existing ADR/pattern to lean on, (c) explicit user ask for the deepest pass. Grounded in a 2026-07-08 run: 8 finders + 6 skeptics on Sonnet resolved every conflict (incl. one two-finder disagreement) themselves; the orchestrator's own work was consistently Opus-shaped, including PR review of the two delegate PRs (which is Sonnet-tier per the row below) — Fable's premium went unused end to end. |
| ADR drafting / architectural reasoning with cross-repo or security/reversibility stakes | **T5 · Fable 5** | Genuine top-rung work — synthesis across many ADRs and policies |
| Heavy single-repo reasoning / large multi-file implementation / thorough design review | **T4 · Opus 5** | Hard but not frontier — Opus reasoning without the T5 premium |
| Code review of someone else's PR | **T3 · Sonnet 5** | Sufficient for review depth |
| Single-PR implementation (bug fix, feature) from a clear spec | **T3 · Sonnet 5** | |
| Lint cleanup / mass rename / mechanical edits | **T3 · Sonnet 5** or `/fast` | |
| Log inspection / DB queries / deploy babysitting / status checks | **T2 · Haiku 4.5** or `/fast` | Cheap, fast, low complexity |

## How to apply

- **At session start**: choose the appropriate model via `/model` based on the
  intended work for that session. Do not start on Fable/Opus and stay there by
  default.
- **Mid-session**: if the workload changes (e.g. finished the architectural
  part, now doing mechanical follow-up edits), call `/model` to step down. This
  works with the running context preserved — switching does not reset the session.
- **`/fast` toggle**: stays on the Opus family with faster output — useful when
  you want Opus reasoning depth on a long context but reduced per-turn latency.
  Available on **Opus 5 and Opus 4.8 only**; Opus 4.7 fast mode was removed and
  now errors. **Not the same cost class as regular Opus:** fast mode on Opus 5
  bills at 10 → 50 per 1M, i.e. T5 pricing for a T4 model. Reach for it to buy
  latency, never to save money, and check the `llm_calls` table afterwards.

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

A T5 session is expensive; spending it on T3 execution wastes the tier.
The pattern:

- **Do inline** the T5 part (analysis, design, decision, orchestration) **and**
  anything trivial (a 2-line fix costs less done than delegated — there is a floor).
- **Delegate** bounded, clear-pattern implementation by writing an **execution-ready
  issue** (files, exact change, test plan, pitfalls — so the executor need not
  re-reason) labelled `model:sonnet-5` (T3) or `model:opus-5` (T4).
- **Consumer** = a session of that tier: the human runs `/model <tier>` then
  `/issues-offen` / `/issues-abarbeiten` filtered on the label, or the headless
  queue picks it up. (Model-label-aware routing in `process-agent-queue` is a
  future extension, not yet wired — until then a human starts the right-tier session.)
- The label is a **recommendation to the consumer**, not self-routing — see the
  section above on who can switch.

## What the assistant should do

When the assistant notices a session running on a tier above the queued work
(e.g. Fable/Opus doing predominantly T3-or-below work), it should mention this
once early in the session — not every turn — with a concrete recommendation. Example:

> "This session is on Fable 5. The work I see queued is lint cleanup + a couple of
> deploys — T3/T2 in `llm-routing.md` terms. A `/model` swap to Sonnet 5 would
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
- 2026-07-08: Split the "Multi-agent orchestration ... Fable 5, home turf" row —
  the blanket claim was itself an exception to this policy's own "don't default
  to the top tier" rule, and a full 8-finder + 6-skeptic `/repo-optimize` run
  showed the exception wasn't earning its premium: every finder/skeptic
  conflict (including a genuine two-finder disagreement) resolved on Sonnet,
  and the orchestrator's own remaining work — prompt design, dedupe, report
  synthesis, PR review — was Opus-shaped (PR review is explicitly Sonnet-tier
  two rows below). New default: orchestrator layer = Opus 4.8; escalate to
  Fable only on a concrete trigger (unresolved cross-finding conflict, novel
  architecture trade-off with no ADR precedent, explicit user ask for max
  depth) — not upfront. Fan-out layer (finders/skeptics) unchanged at Sonnet.
- 2026-07-31: Tier ladder made explicit as **T5–T1** and shared with
  `llm-routing.md`, so one numbering covers actions and sessions. T4 default
  moved Opus 4.8 → **Claude Opus 5** (same 5 → 25 pricing, strictly better);
  4.8 kept only for reproducibility against prior runs. Added a price column
  per rung. Corrected the `/fast` note: fast mode is **Opus 5 / Opus 4.8 only**
  (4.7 fast mode was removed and now errors) and is **not** the same cost class
  as regular Opus — on Opus 5 it bills at 10 → 50, i.e. T5 pricing for a T4
  model. Prose switched from "Tier-3"/"Tier-4" to T3/T4; the 2026-05 spend
  table keeps its historical `claude-opus-4-7` rows unchanged.
