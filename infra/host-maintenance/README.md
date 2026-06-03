# Host Disk Prevention (P1–P3)

Closes the recurring "disk fills to 100%" leak on self-hosted Runner/app hosts
(prod incident 2026-06-03: `88.198.191.108` `/` at 100% / 0 MB → all CI broke,
postgres service containers couldn't `initdb`). The `/infra-cleanup` skill
*reclaims* on demand; this bundle *prevents* recurrence.

> ⚠️ **Deliberate apply, not automatic.** P1/P2 require `systemctl restart docker`,
> which briefly bounces **all** containers on the host — schedule a window.
> Nothing here is applied by the `/infra-cleanup` skill (advisory only, by design).

## P1+P2 — Docker daemon config (log rotation + builder GC)

`daemon.json.recommended` shows the keys to ensure. **Merge** into the host's
existing `/etc/docker/daemon.json` (do not clobber other settings):

```bash
# inspect current
ssh root@<host> 'cat /etc/docker/daemon.json 2>/dev/null || echo "(none)"'
# after merging the keys from daemon.json.recommended:
ssh root@<host> 'systemctl restart docker'   # ⚠️ bounces all containers
```
- `log-opts max-size/max-file` → container logs can't grow unbounded.
- `builder.gc.defaultKeepStorage 20GB` → build cache self-capped.

## P3 — Weekly safe cleanup timer

`host-cleanup-tier1.sh` = unattended-safe subset of `/infra-cleanup` Tier 1
(+ image prune of **>30-day** unused only; never volumes, never `_tool`, never
in-flight `_work`). Install:

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
