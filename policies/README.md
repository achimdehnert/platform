# Org-Wide Policies

These files codify cross-repo defaults for the Achim Dehnert / iil.gmbh org
landscape (achimdehnert, ttz-lif, meiki-lra). They are loaded by Claude Code
on every session via `~/.claude/CLAUDE.md`.

**SSoT = this directory** (`platform/policies/`, versioned). `~/.claude/policies/`
is a symlink into a pinned platform worktree (`~/github/platform-pinned/policies/`)
— same pattern as `~/.claude/commands` → `platform-workflows`. The
`inject_policies.py` hook and `claude-policy` CLI read that path unchanged.

## Files

| Policy | What it answers |
|---|---|
| `llm-routing.md` | Which LLM provider/model for a given task? (Groq/Cerebras first) |
| `session-routing.md` | Which Claude Code session model? (tier-discipline) |
| `adr-threshold.md` | Does this work require an ADR? |
| `platform-agents.md` | Where does a new cross-cutting agent live? (dev-hub) |
| `claude-skills.md` | When to build a CC slash-command skill, and how |
| `orchestrator.md` | When to query orchestrator MCP, and how it relates to these files |

## Override pattern (per-repo)

If a repo needs to deviate from an org policy, add a `## Policy Overrides`
section to that repo's `CLAUDE.md`:

```markdown
## Policy Overrides

- **llm-routing**: only local Ollama (`mistral:7b-instruct`) — data must not
  leave the perimeter. Reason: ttz-lif compliance. Approved 2026-05-11.
- **platform-agents**: use this repo's `apps/` instead of dev-hub —
  reason: …
```

Repo overrides take precedence over org defaults.

## Updating a policy

1. Edit the relevant `<topic>.md` file here, in a **platform PR**
2. Bump the `## Changelog` section at the bottom of that file
3. Merge → the pinned worktree picks it up on next refresh; CI mirrors the
   change to orchestrator-side memory (Phase 2b — see dev-hub#51). Until 2b
   lands: run `claude-policy push` from a session with prod SSH access.
4. Communicate the change to the team (e.g. dev-hub TechDocs page)

## Conflict resolution

Highest precedence wins (top of list):

1. `<repo>/CLAUDE.md` `## Policy Overrides:` (git-tracked)
2. Orchestrator MCP memory (live, where loaded)
3. `platform/policies/<topic>.md` (versioned file-based default)

`claude-policy pull` can detect drift between 2 and 3.
