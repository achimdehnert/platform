---
id: ADR-098
title: "Adopt 3-Layer Tuning Standard for PROD/DEV Hetzner Infrastructure"
status: Accepted
date: 2026-03-04
decision-makers: Achim Dehnert
consulted: –
informed: –
tags: [infrastructure, docker, performance, hetzner, gunicorn, postgresql, redis, sysctl]
supersedes: []
related: [ADR-021, ADR-022, ADR-042, ADR-056, ADR-063, ADR-078]
implementation_status: partial
---

# ADR-098: Adopt 3-Layer Tuning Standard for PROD/DEV Hetzner Infrastructure

## Context

The platform runs 7+ apps across two Hetzner servers:

| Server | Role | Type | vCPU | RAM | Disk | IP |
|--------|------|------|------|-----|------|----|
| **PROD** | All production apps | CPX52 | 16 | 32 GB | 320 GB NVMe | 88.198.191.108 |
| **DEV** | Windsurf remote, CI runners | CCX33 | 8 | 32 GB | 240 GB NVMe | 46.225.113.1 |
| **Odoo-PROD** | Odoo ERP | CPX32 | 4 | 8 GB | 160 GB NVMe | 46.225.127.211 |

Each app has its own compose stack (web + worker + beat + db + redis).

A systematic performance and reliability audit (captured in `scripts/server/bf-tuning-audit.sh`)
revealed the following risk areas across all stacks:

1. **No CPU or memory limits** — any one container can exhaust the shared host
2. **Docker daemon defaults** — live-restore disabled, BuildKit GC unconfigured, logs unbounded
3. **Linux kernel defaults** — swappiness 60, somaxconn 128, inotify limits too low for 7+ apps
4. **PostgreSQL defaults** — `random_page_cost=4.0` (wrong for NVMe), `max_connections=100`
5. **Redis defaults** — no `maxmemory`, no eviction policy → unbounded growth → OOM
6. **Gunicorn sync workers** — no `max-requests` recycling → memory leak over days
7. **No compose hardening** — missing `healthcheck`, `depends_on`, `shm_size`, log options
8. **Celery worker OOM** — DEV: `weltenhub_celery` OOM-killed (exit 137) due to 256M cgroup limit
   with 2 prefork workers needing ~350M. Fixed 2026-03-04: limit raised to 512M.

## Decision Drivers

- **Stability**: eliminate OOM crashes and noisy-neighbor CPU starvation across all apps
- **Performance**: correct PostgreSQL planner for NVMe (`random_page_cost=1.1`)
- **Reliability**: worker memory-leak prevention via `max-requests`
- **Operations**: zero-downtime Docker daemon upgrades via `live-restore`
- **Disk safety**: bounded logs and build-cache to prevent NVMe fill

## Considered Options

| Option | Description | Verdict |
|--------|-------------|---------|
| **A — 3-Layer in-place tuning (chosen)** | daemon.json + sysctl + compose hardening on existing servers | ✅ Adopted |
| **B — PgBouncer + shared PostgreSQL** | One PgBouncer + one PostgreSQL instance for all apps | ❌ Rejected |
| **C — Upgrade to larger server** | More headroom instead of tuning | ✅ Applied for DEV (CCX33) |
| **D — Separate DB server (CPX21)** | Offload all PostgreSQL to a dedicated node | ❌ Rejected |

### Option A — Pros and Cons

| Pros | Cons |
|------|------|
| Zero migration risk — no architectural change | Requires per-repo compose file changes |
| Tuning applies immediately without redeploy | `vm.overcommit_memory=1` shifts OOM risk to kernel |
| Audit script verifies compliance automatically | |
| All changes reversible (backups kept) | |

### Option B — Why Rejected

PgBouncer adds operational complexity (connection pooling config per app, different ORM
behavior, transaction pooling incompatible with Django's session-based connection handling)
without eliminating the root cause (unbounded containers). Max-connections tuning per
instance (50) achieves 80% of the benefit at 0% of the complexity.

### Option C — Applied for DEV

DEV server upgraded from CPX32 (4 vCPU, 8 GB RAM) to CCX33 (8 vCPU, 32 GB RAM, dedicated)
on 2026-03-04 due to severe memory pressure (Swap 100% full, remote session instability).
PROD (CPX52, 32 GB) already has sufficient headroom for current load.

### Option D — Why Rejected

A separate DB server requires network-based DB connections, changes `DATABASE_URL` on all
apps, adds a single point of failure in the network path, and complicates the deployment
matrix. Per-instance `max_connections=50` and `shm_size` achieve sufficient isolation at
current load.

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

> **Note**: `storage-driver` is intentionally omitted — the kernel-native `overlayfs`
> driver on Ubuntu 24.04 is equivalent to `overlay2` and must not be overridden.

**Key decisions:**
- `live-restore: true` — containers survive daemon restarts (zero-downtime Docker upgrades)
- `userland-proxy: false` — use kernel NAT (iptables), faster than userspace proxy
- `builder.gc` — prevents unbounded build cache growth (critical with 7+ apps building on DEV)
- `log-opts` — prevents logs from filling the NVMe

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

# File handles (7+ apps × 4 services × many sockets)
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
```

**Key decisions:**
- `vm.swappiness=10` — avoid swap on NVMe hosts; swapping defeats the NVMe latency advantage
- `vm.overcommit_memory=1` — required for Docker (prevents false-positive OOM kills on fork)
- `net.core.somaxconn=65535` — default 128 is too low for 7+ Gunicorn stacks behind Nginx

### §3 — Compose Hardening (per-service resource limits)

#### §3.1 RAM Budget (PROD + DEV — 32 GB each)

Both PROD (CPX52) and DEV (CCX33) have 32 GB RAM. The table shows **memory limits (ceilings)**
and **reservations (guaranteed minimums)**. With 32 GB, the ceiling total (~11.7 GB) leaves
~20 GB headroom — no overcommit risk at current app count.

| Service | Limit | ×N | Ceiling | Reservation | ×N | Guaranteed |
|---------|-------|----|---------|-------------|-----|------------|
| web | 512M | ×7 | 3.584 GB | 256M | ×7 | 1.792 GB |
| worker | 512M | ×7 | 3.584 GB | 256M | ×7 | 1.792 GB |
| beat¹ | 128M | ×5 | 0.640 GB | 64M | ×5 | 0.320 GB |
| redis | 128M | ×7 | 0.896 GB | 48M | ×7 | 0.336 GB |
| db | 512M | ×6² | 3.072 GB | 256M | ×6 | 1.536 GB |
| OS + Docker | — | — | 0.800 GB | — | — | 0.800 GB |
| **Max Ceiling** | | | **12.576 GB ✓** | **Guaranteed Min** | | **6.576 GB ✓** |

¹ Only bfagent, travel-beat, weltenhub, cad-hub, mcp-hub run Celery Beat (5 apps).
² weltenhub shares bfagent's PostgreSQL container — 6 separate db instances, not 7.

> **Headroom**: 32 GB − 12.6 GB ceiling = **~19 GB free** — comfortable for current load.
> Monitoring alert recommended at >24 GB total RAM usage (75% of 32 GB).

#### §3.2 Standard Compose Template (all apps)

This template is **complete and ADR-022-compliant** — merge into each app's
`docker-compose.prod.yml`. Replace `${APP_NAME}` and `${APP_PORT}` with app-specific values.
Full template: `scripts/server/compose-hardening/template.yml`.

```yaml
services:

  web:
    image: "ghcr.io/achimdehnert/${APP_NAME}:${IMAGE_TAG:-latest}"
    command: ["web"]
    env_file: .env.prod
    ports:
      - "127.0.0.1:${APP_PORT}:8000"
    depends_on:
      migrate:
        condition: service_completed_successfully
      db:
        condition: service_healthy
    healthcheck:
      test:
        - "CMD"
        - "python"
        - "-c"
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')"
      interval: 30s
      timeout: 5s
      start_period: 60s
      retries: 3
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
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"

  worker:
    image: "ghcr.io/achimdehnert/${APP_NAME}:${IMAGE_TAG:-latest}"
    command: ["worker"]
    env_file: .env.prod
    healthcheck:
      test: ["CMD-SHELL", "celery -A config inspect ping --timeout 10 2>/dev/null | grep -q OK"]
      interval: 60s
      timeout: 15s
      retries: 3
      start_period: 60s
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
          cpus: "0.25"
```

#### §3.3 App-Tier Overrides

| App | Type | Beat | `web.cpus` | `web.memory` | `worker.cpus` | Reason |
|-----|------|------|-----------|-------------|--------------|--------|
| travel-beat | Standard HTMX | ✅ | 1.0 | 512M | 1.5 | Baseline |
| weltenhub | Standard HTMX | ✅ | 1.0 | 512M | 1.5 | Baseline |
| risk-hub | Standard HTMX | ❌ | 1.0 | 768M | 1.5 | No scheduled tasks |
| bfagent | AI/I/O-heavy | ✅ | 1.0 | 512M | 2.0 | LLM calls in worker |
| mcp-hub | I/O-heavy | ✅ | 1.0 | 512M | 2.0 | Many concurrent SSH/API calls |
| trading-hub | CPU+WebSocket | ❌ | 1.5 | 512M | 1.5 | Signal computation CPU-bound |
| cad-hub | CPU-heavy | ✅ | 2.0 | 512M | 2.0 | IFC parsing is CPU+RAM heavy |

### §4 — PostgreSQL Tuning

Applied via compose `command:` directive (see §3.2 template — included in `db` service).

**Key decisions:**
- `random_page_cost=1.1` — **critical for NVMe**. Default 4.0 causes PostgreSQL to prefer
  sequential scans over index scans, which is wrong for SSD/NVMe storage
- `max_connections=50` — 6 × 50 = 300 total (sufficient); default 100 wastes RAM
- `work_mem=4MB` — low because 50 connections × 4MB = 200MB per instance
- `log_min_duration_statement=200` — slow query logging (200ms threshold)

### §5 — Gunicorn Configuration

Parametrized via `.env.prod`:

```bash
# .env.prod additions (all apps)
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
GUNICORN_WORKER_CLASS=gthread
GUNICORN_TIMEOUT=30
GUNICORN_KEEPALIVE=5
GUNICORN_MAX_REQUESTS=1000
GUNICORN_MAX_REQUESTS_JITTER=100
```

**Per-app overrides (only the differing values):**

| App | `GUNICORN_WORKERS` | `GUNICORN_THREADS` | Reason |
|-----|-------------------|--------------------|--------|
| Standard (travel-beat, risk-hub, weltenhub) | 2 | 2 | Baseline |
| bfagent, mcp-hub | 2 | 4 | I/O-heavy (LLM/SSH calls) |
| trading-hub | 3 | 2 | More WebSocket connections |
| cad-hub | 2 | 1 | CPU-bound, threading hurts |

**Key decisions:**
- `gthread` worker class — better for HTMX partial rendering (I/O-bound)
- `max-requests=1000` + jitter — prevents memory leak from long-running workers
- `keep-alive=5` — reduces connection overhead with Nginx upstream keep-alive

### §6 — Redis per App

- `maxmemory 96mb` with `allkeys-lru` eviction — graceful degradation, no OOM
- `--save "" --appendonly no` — no persistence on PROD (Celery task state is ephemeral)
- Container memory limit 128MB = maxmemory (96MB) + Redis overhead (~25%)

---

## Implementation

### Priority Matrix

| Priority | Change | Impact | Effort | Status |
|----------|--------|--------|--------|--------|
| 🔴 P0 | sysctl (swappiness, somaxconn, inotify) | Stability +++ | 5 min | ✅ Applied DEV 2026-03-04 |
| 🔴 P0 | `live-restore: true` in daemon.json | Uptime ++ | 10 min | ✅ Applied DEV 2026-03-04 |
| 🔴 P0 | DEV server upgrade CPX32→CCX33 (8vCPU, 32GB) | Headroom +++ | 30 min | ✅ Done 2026-03-04 |
| 🔴 P0 | weltenhub_celery OOM fix (256M→512M) | Stability ++ | 5 min | ✅ Fixed 2026-03-04 |
| 🔴 P0 | cad-hub/risk-hub worker healthcheck added | Reliability ++ | 10 min | ✅ Fixed 2026-03-04 |
| 🔴 P0 | Redis `maxmemory` + eviction per app | Safety +++ | 30 min | ⏳ Pending PROD |
| 🔴 P0 | `random_page_cost=1.1` per app | Performance ++ | 30 min | ⏳ Pending PROD |
| 🟡 P1 | `healthcheck` + `depends_on` in all compose files | Reliability ++ | 1h | ✅ Applied 4 repos 2026-03-04 |
| 🟡 P1 | Gunicorn `gthread` + `max-requests` per app | Reliability ++ | 1h | ⏳ Pending |
| 🟡 P1 | Log max-size in all compose files | Disk safety ++ | 30 min | ✅ Applied 2026-03-04 |
| 🟡 P1 | `shm_size: 128m` in all db services | PG stability + | 30 min | ⏳ Pending |
| 🟢 P2 | BuildKit GC in daemon.json | Disk + | 10 min | ✅ Applied DEV 2026-03-04 |
| 🟢 P2 | PostgreSQL `max_connections=50` | Resource + | 30 min | ⏳ Pending |
| 🟢 P2 | Swap deactivated on DEV | Stability + | 5 min | ✅ Done 2026-03-04 |

### Tooling

```
scripts/server/
├── bf-tuning-audit.sh      # Read-only compliance audit (JSON output for CI)
├── apply-server-tuning.sh  # Idempotent Layer-0 setup (daemon.json + sysctl)
└── compose-hardening/
    └── template.yml        # ADR-022-compliant compose template (merge into each app)
```

---

## Consequences

### Positive
- Eliminates noisy-neighbor CPU starvation across all apps
- PostgreSQL query plans improve for NVMe workloads (index scans preferred)
- Redis cannot OOM the server
- Docker daemon upgrades cause zero app downtime
- Disk cannot fill from unrotated logs or build cache
- Workers recycle every 1000 requests — no long-term memory leak
- DEV server stable: 32 GB RAM, dedicated vCPU, no swap — Windsurf remote sessions stable

### Negative / Trade-offs
- `vm.overcommit_memory=1` shifts OOM pre-checking to the kernel OOM killer —
  acceptable because container limits act as the actual guard
- Redis `--save ""` means Celery beat schedules reset on Redis restart
  (acceptable: all beat schedules are defined in Django settings, not Redis state)
- `max_connections=50` per PG instance — mitigated by Django's built-in connection pooling

### Non-Goals
- Multi-server load balancing (future ADR)
- Application-level caching strategies (ADR-027)
- Nginx host-level tuning (Nginx runs on host, not in Docker)
- PgBouncer connection pooling (rejected in Considered Options — see Option B)

---

## Confirmation

Compliance is verified by `scripts/server/bf-tuning-audit.sh`. The script MUST exit
with 0 FAIL before any new app repo is onboarded (gate in `docs/guides/onboard-repo.md`
§7 Compliance Checklist).

**CI integration** (after ADR-078):
```yaml
- name: Infrastructure tuning audit
  run: |
    ssh -o BatchMode=yes \
        -o StrictHostKeyChecking=accept-new \
        root@${DEPLOY_HOST} \
        'bash /opt/scripts/bf-tuning-audit.sh --json' \
    | jq -e '.totals.fail == 0'
```

**Drift detection:**
- `staleness_months: 6`
- `drift_check_paths: [scripts/server/bf-tuning-audit.sh, docker-compose.prod.yml]`

---

## Appendix A — Canonical `entrypoint.sh`

All apps MUST use this pattern. The `MODE` variable is passed via compose `command:`.

```bash
#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-web}"

case "${MODE}" in
    web)
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers              "${GUNICORN_WORKERS:-2}" \
            --threads              "${GUNICORN_THREADS:-2}" \
            --worker-class         "${GUNICORN_WORKER_CLASS:-gthread}" \
            --timeout              "${GUNICORN_TIMEOUT:-30}" \
            --keep-alive           "${GUNICORN_KEEPALIVE:-5}" \
            --max-requests         "${GUNICORN_MAX_REQUESTS:-1000}" \
            --max-requests-jitter  "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
            --access-logfile - \
            --error-logfile - \
            --log-level info \
            --forwarded-allow-ips "*"
        ;;
    worker)
        exec celery -A config worker \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;
    beat)
        exec celery -A config beat \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --schedule=/tmp/celerybeat-schedule
        ;;
    migrate)
        exec python manage.py migrate --noinput
        ;;
    *)
        echo "ERROR: Unknown mode '${MODE}'. Usage: entrypoint.sh [web|worker|beat|migrate]" >&2
        exit 1
        ;;
esac
```
