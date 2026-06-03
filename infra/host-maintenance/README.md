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

## P3 — Weekly safe cleanup timer (the actual prevention)

`host-cleanup-tier1.sh` = unattended-safe subset of `/infra-cleanup` Tier 1
**plus a prune of unused images >7 days old** (the piece builder-GC does *not*
cover); never volumes, never `_tool`, never in-flight `_work`. Install:

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

## Changelog
- 2026-06-03: Initial. P1–P3 prevention bundle; split from the reclaim-only
  `/infra-cleanup` skill (no daemon-restart as a cleanup side effect).
