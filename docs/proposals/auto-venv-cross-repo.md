# Proposal: Auto-Venv for Multi-Repo Workspace

## Problem

When working across multiple repos (bfagent, travel-beat, risk-hub, etc.)
in WSL, `cd`'ing between directories does **not** switch the active
virtualenv. This leads to:

- `ImportError: No module named 'celery'` (or any project-specific dep)
- Silent wrong-version bugs (e.g. Pydantic v1 vs v2)
- Wasted debugging time

**Root cause**: All 7 repos have their own `.venv`, but bash does not
auto-switch when you enter a different project directory.

## Solution

### Option A: Zero-dependency bash hook (recommended, immediate)

A `cd` override in `~/.bashrc` that auto-activates `.venv/bin/activate`
when entering a project directory.

**Install**:
```bash
echo 'source ~/github/platform/scripts/auto-venv.sh' >> ~/.bashrc
source ~/.bashrc
```

**File**: `platform/scripts/auto-venv.sh`

**Pros**:
- Zero dependencies, works immediately
- No sudo required
- Handles nested `cd`, `pushd`/`popd` via simple hook
- Deactivates old venv before activating new one

**Cons**:
- Only works in bash (zsh needs separate hook)
- `pushd`/`popd` not covered by default (can be added)

### Option B: direnv (better long-term, needs sudo)

`direnv` is the industry standard for per-directory env management.

**Install**:
```bash
sudo apt-get install direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
```

Then add `.envrc` to each repo:
```bash
# .envrc
layout python-venv .venv
```

**Pros**:
- Industry standard, well-tested
- Handles env vars too (not just venv)
- Supports bash, zsh, fish
- `.envrc` files version-controlled per repo

**Cons**:
- Requires sudo for installation
- Requires `direnv allow` per repo on first use

## Recommendation

**Start with Option A now** (zero friction, already created).
**Migrate to Option B** when sudo is available or on next server setup.

## Affected Repos

All 7 repos already have `.venv` directories:

| Repo | `.venv` | Python |
|------|---------|--------|
| bfagent | ✅ | 3.11 |
| mcp-hub | ✅ | 3.11 |
| platform | ✅ | 3.11 |
| pptx-hub | ✅ | 3.11 |
| risk-hub | ✅ | 3.11 |
| travel-beat | ✅ | 3.11 |
| weltenhub | ✅ | 3.11 |

## Testing

```bash
# After sourcing auto-venv.sh:
cd ~/github/risk-hub && which python
# → /home/dehnert/github/risk-hub/.venv/bin/python

cd ~/github/travel-beat && which python
# → /home/dehnert/github/travel-beat/.venv/bin/python

cd ~/github/travel-beat && python -m pytest apps/trips/tests/test_enrichment.py -x
# → All tests pass (no ImportError)
```
