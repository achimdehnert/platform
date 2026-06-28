# Host Disk Prevention (P1–P3)

Closes the recurring "disk fills to 100%" leak on self-hosted Runner/app hosts
(prod incident 2026-06-03: `88.198.191.108` `/` at 100% / 0 MB → all CI broke,
postgres service containers couldn't `initdb`). The `/infra-cleanup` skill
*reclaims* on demand; this bundle *prevents* recurrence.

> ⚠️ **The real leak is P3, not P1/P2.** Verified on prod `88.198.191.108`
> (2026-06-03 `/infra-cleanup` dry-run): P1+P2 were **already configured** there
> (log rotation `max-size 10m/max-file 5`; builder GC `keepStorage 5GB`), yet the
> disk still hit 100%. Reason: builder GC caps the **build cache** (~1 GB, working),
> **not unused images** — and nothing prunes those (40.96 GB had accumulated).
> **P3 (scheduled image prune) is the fix that was missing.**

## P1+P2 — Docker daemon config (CONDITIONAL — verify per host first)

Many hosts already have this (prod did). **Check before changing; never clobber:**
```bash
ssh root@<host> 'cat /etc/docker/daemon.json 2>/dev/null || echo "(none)"'
```
Only if `log-opts` / `builder.gc` are absent, merge the keys from
`daemon.json.recommended`, then `systemctl restart docker` (⚠️ bounces all
containers — schedule a window). Not applied by the `/infra-cleanup` skill.

## P3 — Daily safe cleanup timer (the actual prevention)

`host-cleanup-tier1.sh` = unattended-safe subset of `/infra-cleanup` Tier 1
**plus a prune of unused images >7 days old** (the piece builder-GC does *not*
cover); never volumes, never `_tool`, never in-flight `_work`. Install:

> ⚠️ **Cadence is daily, not weekly.** Originally `OnCalendar=Sun` (weekly).
> On `88.198.191.108` (multi-hub host, ~7 `trading-hub` image tags @ 2.7 GB
> stack up between runs) the disk filled mid-week and a **travel-beat deploy
> failed Sat 2026-06-27** (`apt-get … No space left` in the build's apt layer) —
> the Sunday cleanup then freed it Sun 06-28. Weekly let a full week of churn
> accumulate. The script is cheap + conservative (idempotent prunes, only
> `_work/*/_temp` scratch, no checkout wipe), so daily has no downside and
> matches the host's documented *daily* image churn.

```bash
scp infra/host-maintenance/host-cleanup-tier1.sh root@<host>:/opt/infra/host-cleanup-tier1.sh
scp infra/host-maintenance/infra-cleanup.{service,timer} root@<host>:/etc/systemd/system/
ssh root@<host> 'chmod +x /opt/infra/host-cleanup-tier1.sh && \
  systemctl daemon-reload && systemctl enable --now infra-cleanup.timer && \
  systemctl list-timers infra-cleanup.timer'
```

## Relationship to `/infra-cleanup`

| Concern | Tool |
|---|---|
| On-demand reclaim (incident / ad-hoc), tiered + gated | `/infra-cleanup` skill |
| Standing prevention (config + scheduled safe prune) | this bundle |
| Aggressive reclaim (`image prune -a` no-filter, full `_work`, volumes) | human-driven only, via skill with explicit confirm |

## Session-Worktree GC (ADR-233 — separate concern, dev/session host)

Closes the recurring `worktree-orphan-accumulation` slug (≥2× across
`~/shared/session-retro-*.md`, flagged gate-pflichtig by `retro_kpis.py`).
`tools/worktree-reaper.py` already reaps merged-PR worktrees correctly
(squash-aware, dirty-guard, restore-manifest, `unknown=KEEP`) — but **nothing
ran it with `--apply`**: `repo-session end` only handles the single passed
worktree on explicit human invocation, so orphans from `gh pr merge` without
`end` piled up (2026-06-24: 3 merged worktrees + open leases back to 06-10).

`worktree-reaper-all.sh` iterates every repo under `$GITHUB_DIR` that has
session worktrees and runs the reaper `--apply` per repo — **merged-only,
never `--include-stale`, never touches branches/remote**. Logs to
`~/.repo-session/reaper.log`.

> ⚠️ Unlike P1–P3 (prod/runner hosts, **root**), this runs on the **dev/session
> machine as the session user** — it needs that user's `gh` auth and `~/github`
> checkout. Hence a systemd **`--user`** timer, not a system timer.

Install (per session host, **explicit human step — merging this PR changes
nothing**):
```bash
mkdir -p ~/.config/systemd/user
cp infra/host-maintenance/worktree-reaper.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now worktree-reaper.timer
systemctl --user list-timers worktree-reaper.timer
# Damit der Timer ohne aktive Login-Session feuert:
loginctl enable-linger "$USER"
```
Dry-run first to inspect the plan without removing anything:
```bash
( cd ~/github/<repo> && python3 ~/github/platform/tools/worktree-reaper.py )
```

## Changelog
- 2026-06-28: P3 cadence weekly → **daily** (`infra-cleanup.timer` `OnCalendar=Sun`
  → `*-*-* 04:00`). Weekly let image churn fill the disk mid-week → travel-beat
  deploy failed Sat 2026-06-27 (apt `No space left`) the day before the Sunday run.
- 2026-06-03: Initial. P1–P3 prevention bundle; split from the reclaim-only
  `/infra-cleanup` skill (no daemon-restart as a cleanup side effect).
- 2026-06-24: Session-Worktree GC added (`worktree-reaper-all.sh` +
  `worktree-reaper.{service,timer}`, systemd --user) — closes the missing
  scheduled `--apply` invocation behind ADR-233's reaper (gate for
  `worktree-orphan-accumulation`).
