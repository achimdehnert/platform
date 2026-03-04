---
id: ADR-098
title: Production Infrastructure Tuning Standard
status: Accepted
date: 2026-03-04
author: Achim Dehnert
tags: [infrastructure, docker, performance, hetzner, gunicorn, postgresql, redis, sysctl]
supersedes: []
related: [ADR-021, ADR-022, ADR-078, ADR-056]
---

# ADR-098: Production Infrastructure Tuning Standard

## Context

The platform runs 7 apps on a single Hetzner CPX32 PROD server (4 vCPU, 8 GB RAM, 160 GB NVMe)
and a CX32 DEV server (4 vCPU, 8 GB RAM, 80 GB NVMe). Each app has its own compose stack
(web + worker + beat + db + redis).

A systematic performance and reliability audit (captured in `docs/adr/inputs/bf-tuning-audit.sh`)
revealed the following risk areas across all 7 stacks:

1. **No CPU or memory limits** — any one container can exhaust the shared 4-core host
2. **Docker daemon defaults** — live-restore disabled, BuildKit GC unconfigured, logs unbounded
3. **Linux kernel defaults** — swappiness 60, somaxconn 128, inotify limits too low for 7 apps
4. **PostgreSQL defaults** — `random_page_cost=4.0` (wrong for NVMe), `max_connections=100`
   per instance → 7 × 100 = 700 theoretical connections on 8 GB
5. **Redis defaults** — no `maxmemory`, no eviction policy → unbounded growth → OOM
6. **Gunicorn sync workers** — no `max-requests` recycling → memory leak over days;
   no `gthread` worker class → suboptimal for HTMX I/O workloads
7. **No compose hardening** — missing `shm_size`, missing log options, missing restart policies

## Decision

Adopt a **3-layer tuning standard** applied consistently across PROD and DEV servers:

- **Layer 0 — Server**: Docker daemon + Linux kernel (`sysctl`) parameters
- **Layer 1 — Compose**: Per-service resource limits, logging config, restart policy, `shm_size`
- **Layer 2 — Runtime**: Gunicorn, PostgreSQL, Redis tuning via ENV / compose `command`

All parameters are **tier-differentiated** by app type (standard / I/O-heavy / CPU-heavy).

Compliance is enforced by the audit script `scripts/server/bf-tuning-audit.sh`
(read-only, CI-safe, outputs JSON for monitoring integration).

## Rationale

| Risk | Without Tuning | With This ADR |
|------|---------------|---------------|
| CPU starvation | One busy Gunicorn kills all 7 apps | `cpus: "1.0"` limit per web container |
| RAM exhaustion | 7 × unlimited = OOM at any time | Budget: 7.97 GB ≤ 8 GB (see §2.2) |
| Disk fill | Logs grow unbounded | json-file max-size 10m, BuildKit GC 5 GB |
| Slow queries | PG uses wrong plan (seq scan) | `random_page_cost=1.1` for NVMe |
| Redis OOM | No eviction → server crash | `maxmemory 96mb allkeys-lru` |
| Memory leak | Workers never restart | `--max-requests 1000` |
| Downtime on Docker upgrade | All containers stop | `live-restore: true` |

---

## Specification

### §1 — Docker Daemon (`/etc/docker/daemon.json`)

Applied to **both PROD (88.198.191.108) and DEV (46.225.113.1)** servers.

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5",
    "compress": "true"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": { "Name": "nofile", "Hard": 65536, "Soft": 65536 }
  },
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "max-concurrent-downloads": 6,
  "max-concurrent-uploads": 3,
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "5GB",
      "policy": [
        { "keepStorage": "2GB", "filter": ["unused-for=168h"] },
        { "keepStorage": "5GB", "all": true }
      ]
    }
  }
}
```

**Key decisions:**
- `live-restore: true` — containers survive daemon restarts (zero-downtime Docker upgrades)
- `userland-proxy: false` — use kernel NAT (iptables), faster than userspace proxy
- `builder.gc` — prevents unbounded build cache growth (critical with 7 apps building on DEV)
- `log-opts` — prevents logs from filling the 160 GB NVMe

### §2 — Linux Kernel / sysctl (`/etc/sysctl.d/99-docker-perf.conf`)

```bash
# Network performance
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# Memory management
vm.swappiness = 10
vm.overcommit_memory = 1
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5

# File handles (7 apps × 4 services × many sockets)
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
```

**Key decisions:**
- `vm.swappiness=10` — avoid swap on NVMe hosts; swapping defeats the NVMe latency advantage
- `vm.overcommit_memory=1` — required for Docker (prevents false-positive OOM kills on fork)
- `net.core.somaxconn=65535` — default 128 is too low for 7 Gunicorn stacks behind Nginx

### §3 — Compose Hardening (per-service resource limits)

#### §3.1 RAM Budget (PROD — 8 GB / 7 Apps)

| Service | Limit | × 7 apps | Subtotal |
|---------|-------|-----------|----------|
| web | 384M | × 7 | 2.688 GB |
| worker | 512M | × 7 | 3.584 GB |
| db | 512M | shared* | — |
| redis | 128M | × 7 | 0.896 GB |
| OS + Docker | — | — | 0.800 GB |
| **Total** | | | **7.97 GB ✓** |

*Apps sharing the bfagent postgres (weltenhub) do not add a separate db container.

#### §3.2 Standard Compose Template (all apps)

```yaml
services:
  web:
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 384M
          cpus: "1.0"
        reservations:
          memory: 192M
          cpus: "0.25"

  worker:
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.5"
        reservations:
          memory: 256M
          cpus: "0.5"

  beat:
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"
        reservations:
          memory: 64M
          cpus: "0.1"

  db:
    restart: unless-stopped
    shm_size: "128m"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.75"
        reservations:
          memory: 256M
          cpus: "0.25"

  redis:
    restart: unless-stopped
    command: >
      redis-server
      --maxmemory 96mb
      --maxmemory-policy allkeys-lru
      --save ""
      --appendonly no
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"
        reservations:
          memory: 48M
          cpus: "0.1"

  migrate:
    restart: "no"
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
```

#### §3.3 App-Tier Overrides

| App | Type | `web.cpus` | `web.memory` | `worker.cpus` | Reason |
|-----|------|-----------|-------------|--------------|--------|
| travel-beat | Standard HTMX | 1.0 | 384M | 1.5 | Baseline |
| weltenhub | Standard HTMX | 1.0 | 384M | 1.5 | Baseline |
| risk-hub | Standard HTMX | 1.0 | 384M | 1.5 | Baseline |
| bfagent | AI/I/O-heavy | 1.0 | 384M | 2.0 | LLM calls in worker |
| mcp-hub | I/O-heavy | 1.0 | 384M | 2.0 | Many concurrent SSH/API calls |
| trading-hub | CPU+WebSocket | 1.5 | 384M | 1.5 | Signal computation CPU-bound |
| cad-hub | CPU-heavy | 2.0 | 512M | 2.0 | IFC parsing is CPU+RAM heavy |

### §4 — PostgreSQL Tuning

Applied via compose `command:` directive (no config file mount needed):

```yaml
  db:
    command: >
      postgres
      -c shared_buffers=128MB
      -c work_mem=4MB
      -c maintenance_work_mem=64MB
      -c effective_cache_size=256MB
      -c max_connections=50
      -c checkpoint_completion_target=0.9
      -c wal_buffers=8MB
      -c random_page_cost=1.1
      -c log_min_duration_statement=200
      -c log_connections=off
      -c log_disconnections=off
```

**Key decisions:**
- `random_page_cost=1.1` — **critical for NVMe**. Default 4.0 causes PostgreSQL to prefer
  sequential scans over index scans, which is wrong for SSD/NVMe storage.
- `max_connections=50` — 7 × 50 = 350 total (sufficient); default 100 wastes RAM
- `work_mem=4MB` — low because 50 connections × 4MB = 200MB per instance
- `log_min_duration_statement=200` — slow query logging (200ms threshold)

### §5 — Gunicorn Configuration

```bash
# entrypoint.sh — parametrizable via .env.prod
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
GUNICORN_THREADS=${GUNICORN_THREADS:-2}
GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS:-gthread}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-30}
GUNICORN_KEEPALIVE=${GUNICORN_KEEPALIVE:-5}
GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS:-1000}
GUNICORN_MAX_REQUESTS_JITTER=${GUNICORN_MAX_REQUESTS_JITTER:-100}

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS}" \
    --threads "${GUNICORN_THREADS}" \
    --worker-class "${GUNICORN_WORKER_CLASS}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    --keep-alive "${GUNICORN_KEEPALIVE}" \
    --max-requests "${GUNICORN_MAX_REQUESTS}" \
    --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --forwarded-allow-ips "*"
```

**Per-app `.env.prod` overrides:**

| App | `GUNICORN_WORKERS` | `GUNICORN_THREADS` | Reason |
|-----|-------------------|--------------------|--------|
| Standard (travel-beat, risk-hub, weltenhub) | 2 | 2 | 4 effective threads, low memory |
| bfagent, mcp-hub | 2 | 4 | I/O-heavy (LLM/SSH calls) |
| trading-hub | 3 | 2 | More WebSocket connections |
| cad-hub | 2 | 1 | CPU-bound, threading hurts |

**Key decisions:**
- `gthread` worker class over `sync` — better for HTMX partial rendering (I/O-bound)
- `max-requests=1000` + jitter — prevents memory leak from long-running workers
- `keep-alive=5` — reduces connection overhead with Nginx upstream keep-alive

### §6 — Redis per App

```yaml
  redis:
    command: >
      redis-server
      --maxmemory 96mb
      --maxmemory-policy allkeys-lru
      --save ""
      --appendonly no
```

- `maxmemory 96mb` with `allkeys-lru` eviction — graceful degradation, no OOM
- `save "" --appendonly no` — no persistence on PROD (Celery task state is ephemeral)
- Container memory limit 128MB = maxmemory (96MB) + Redis overhead (~25%)

---

## Implementation

### Priority Matrix

| Priority | Change | Impact | Effort |
|----------|--------|--------|--------|
| P0 | `cpus:` limits in all 7 compose files | Stability +++ | 30 min |
| P0 | `vm.swappiness=10` on PROD | Stability ++ | 5 min |
| P0 | Redis `maxmemory` + eviction policy | Safety +++ | 15 min |
| P0 | `random_page_cost=1.1` in all PostgreSQL | Performance ++ | 15 min |
| P1 | `gthread` + `max-requests` in Gunicorn | Reliability ++ | 1h |
| P1 | Log max-size in all compose files | Disk safety ++ | 30 min |
| P1 | `live-restore: true` in Docker daemon | Uptime ++ | 10 min |
| P1 | `shm_size: 128m` in all db services | PG stability + | 30 min |
| P2 | Full sysctl profile in `/etc/sysctl.d/` | Network + | 15 min |
| P2 | PostgreSQL `max_connections=50` | Resource + | 30 min |
| P2 | BuildKit GC in daemon.json | Disk + | 10 min |

### Tooling

```
scripts/server/
├── bf-tuning-audit.sh      # Read-only audit (promoted from docs/adr/inputs/)
├── apply-server-tuning.sh  # Apply daemon.json + sysctl (run once per server)
└── compose-hardening/
    └── template.yml        # Canonical compose snippet (merge into each app)
```

### Verification

After applying:

```bash
# 1. Run audit (should show 0 FAIL)
bash scripts/server/bf-tuning-audit.sh

# 2. JSON for CI/monitoring
bash scripts/server/bf-tuning-audit.sh --json | jq '.totals'

# 3. Spot-check per app
bash scripts/server/bf-tuning-audit.sh --app travel-beat
```

---

## Consequences

### Positive
- Eliminates noisy-neighbor CPU starvation across 7 apps
- RAM budget fits within 8 GB with ~200 MB headroom
- PostgreSQL query plans improve for NVMe workloads (index scans preferred)
- Redis cannot OOM the server
- Docker daemon upgrades cause zero app downtime
- Disk cannot fill from unrotated logs or build cache

### Negative / Trade-offs
- CPU limits may throttle cad-hub during large IFC file uploads (mitigated by tier override)
- Redis `--save ""` means Celery beat schedules reset on Redis restart
  (acceptable: all beat schedules are defined in Django settings, not Redis state)
- `max_connections=50` per PG instance — mitigated by Django built-in connection pooling

### Non-Goals
- Multi-server load balancing (future ADR)
- Application-level caching strategies (ADR-027)
- Nginx host-level tuning

---

## Compliance Verification

The audit script `scripts/server/bf-tuning-audit.sh` checks all parameters defined here.
It MUST pass with 0 FAIL before any new app is onboarded (gate in `onboard-repo.md`).

CI integration (future):
```yaml
- name: Infrastructure tuning audit
  run: ssh root@88.198.191.108 'bash /opt/scripts/bf-tuning-audit.sh --json' \
       | jq -e '.totals.fail == 0'
```
