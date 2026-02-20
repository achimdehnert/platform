---
id: ADR-053
title: "deployment-mcp Robustness — Circuit Breaker, Timeout-Fixes & Async Job Pattern"
status: implemented
date: 2026-02-20
author: Achim Dehnert
owner: Achim Dehnert
scope: mcp-hub / deployment_mcp
tags: [mcp-hub, deployment, ssh, robustness, circuit-breaker, async, reliability]
related: [ADR-044, ADR-042, ADR-021]
last_verified: 2026-02-20
implemented: 2026-02-20
commit: 4888fc0
---

# ADR-053: deployment-mcp Robustness — Circuit Breaker, Timeout-Fixes & Async Job Pattern

## Context

The `deployment-mcp` server is the central infrastructure management tool used
by Windsurf (Cascade) to deploy, monitor, and operate all platform services via
SSH, Docker, and Hetzner Cloud APIs.

**Observed failure mode:** All MCP tool calls hang indefinitely — including
trivial calls like `ssh_manage { action: exec, command: "echo OK", timeout: 5 }`.
The server becomes unresponsive and must be restarted manually.

### Root Cause Analysis (Code-verified)

The `deployment_mcp` codebase already has meaningful protections:
`asyncio.wait_for()` in `server.py`, per-host SSH semaphores with timeout,
`_kill_proc()` with a 5s bound, and transient-error retry. Despite this, the
following combination of issues causes full server hangs:

**RC-1: Semaphore timeout equals command timeout (30s)**

```python
# ssh_client.py:174
await asyncio.wait_for(sem.acquire(), timeout=timeout)  # timeout = 30s
```

With `_SSH_CONCURRENCY = 4`: four hanging SSH calls fill all semaphore slots.
Every subsequent call waits 30s for a slot → the single-threaded asyncio event
loop is effectively blocked for 30s per new call.

**RC-2: `ssh_manage` missing from `TOOL_TIMEOUTS`**

```python
# timeout_config.py
DEFAULT_TIMEOUT: int = 120   # ssh_manage falls through to this
```

A caller-supplied `timeout: 5` argument is a *hint to the SSH subprocess*, not
to the server-level `asyncio.wait_for()`. The server waits up to 120s before
giving up on a hung `ssh_manage` call.

**RC-3: Consolidated `ssh_manage` makes multiple sequential SSH calls**

Each sub-call occupies a semaphore slot. If sub-call 1 hangs, sub-call 2 waits
for a slot → deadlock within a single tool invocation.

**RC-4: No health-check or watchdog**

A crashed or deadlocked server process is not detected until the next tool call
also hangs. No automatic restart, no circuit-breaking.

### Assessment of Existing Protections

| Mechanism | Present | Effective | Gap |
|-----------|---------|-----------|-----|
| `asyncio.wait_for()` in `server.py` | ✅ | Partial | Does not protect against event-loop stall |
| SSH semaphore with timeout | ✅ | Partial | Semaphore timeout = command timeout → no headroom |
| `_kill_proc()` with 5s bound | ✅ | Partial | `proc.communicate()` cancel can itself stall |
| Transient-error retry | ✅ | Yes | Works for short outages |
| Per-tool timeouts | ✅ | Partial | `ssh_manage` not listed → gets 120s default |
| Health-check / watchdog | ❌ | — | Not present |
| Circuit breaker | ❌ | — | Not present |
| Async job pattern | ❌ | — | Not present |

---

## Decision

Implement robustness improvements in three ordered phases. Each phase is
independently deployable and provides immediate value.

### Phase 1 — Timeout Fixes (Low risk, immediate impact)

#### 1a: Add `ssh_manage` and SSH tools to `TOOL_TIMEOUTS`

```python
# deployment_mcp/timeout_config.py
TOOL_TIMEOUTS: dict[str, int] = {
    # existing entries ...
    "ssh_manage":    60,   # consolidated SSH tool
    "ssh_exec":      60,   # direct SSH exec
    "ssh_file_read": 30,
    "ssh_file_write": 30,
    "ssh_file_exists": 15,
    "ssh_dir_list":  30,
    "http_check":    20,
}
```

#### 1b: Decouple semaphore-acquire timeout from command timeout

```python
# ssh_client.py — _run_once()
SEM_ACQUIRE_TIMEOUT = 10  # seconds — independent of command timeout

sem = _get_semaphore(self.host)
try:
    await asyncio.wait_for(sem.acquire(), timeout=SEM_ACQUIRE_TIMEOUT)
except asyncio.TimeoutError:
    raise asyncio.TimeoutError(
        f"SSH semaphore busy for {SEM_ACQUIRE_TIMEOUT}s (host={self.host})"
    )
```

A hung call now fails fast (10s) instead of blocking for the full command
timeout (30s).

#### 1c: Watchdog background task

```python
# server.py — run_server()
async def _watchdog(interval: int = 30) -> None:
    """Log semaphore pressure every 30s for observability."""
    while True:
        await asyncio.sleep(interval)
        for host, sem in _SSH_SEMAPHORES.items():
            busy = _SSH_CONCURRENCY - sem._value
            if busy > 0:
                logger.warning(
                    "SSH semaphore: %d/%d slots busy host=%s",
                    busy, _SSH_CONCURRENCY, host,
                )

async def run_server() -> None:
    # ... existing setup ...
    async with stdio_server() as streams:
        watchdog = asyncio.create_task(_watchdog())
        try:
            await server.run(read_stream, write_stream, ...)
        finally:
            watchdog.cancel()
```

### Phase 2 — Circuit Breaker (Medium effort, high impact)

A per-host circuit breaker prevents cascading failures when a remote host
becomes unreachable or unresponsive.

#### States

```
CLOSED ──(N failures)──► OPEN ──(reset_timeout)──► HALF_OPEN
  ▲                                                      │
  └──────────────(1 success)────────────────────────────┘
```

#### Implementation

New file: `deployment_mcp/clients/circuit_breaker.py`

```python
from __future__ import annotations
import asyncio, time, logging
from dataclasses import dataclass, field
from typing import Any, Coroutine

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3
RESET_TIMEOUT_S   = 30
_BREAKERS: dict[str, "CircuitBreaker"] = {}


def get_breaker(host: str) -> "CircuitBreaker":
    if host not in _BREAKERS:
        _BREAKERS[host] = CircuitBreaker(host)
    return _BREAKERS[host]


@dataclass
class CircuitBreaker:
    host: str
    state: str = "closed"          # closed | open | half_open
    failure_count: int = 0
    last_failure_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def call(self, coro: Coroutine) -> Any:
        async with self._lock:
            if self.state == "open":
                elapsed = time.monotonic() - self.last_failure_at
                if elapsed >= RESET_TIMEOUT_S:
                    self.state = "half_open"
                    logger.info("Circuit HALF_OPEN host=%s", self.host)
                else:
                    remaining = int(RESET_TIMEOUT_S - elapsed)
                    raise RuntimeError(
                        f"Circuit OPEN host={self.host},"
                        f" retry in {remaining}s"
                    )
        try:
            result = await coro
            await self._record_success()
            return result
        except Exception:
            await self._record_failure()
            raise

    async def _record_success(self) -> None:
        async with self._lock:
            self.failure_count = 0
            if self.state == "half_open":
                self.state = "closed"
                logger.info("Circuit CLOSED host=%s", self.host)

    async def _record_failure(self) -> None:
        async with self._lock:
            self.failure_count += 1
            self.last_failure_at = time.monotonic()
            if self.failure_count >= FAILURE_THRESHOLD:
                self.state = "open"
                logger.error(
                    "Circuit OPEN host=%s after %d failures",
                    self.host, self.failure_count,
                )
```

Integration in `SSHClient.run()`:

```python
# ssh_client.py
from ..clients.circuit_breaker import get_breaker

async def run(self, command, timeout=None, retries=None):
    breaker = get_breaker(self.host)
    return await breaker.call(
        self._run_with_retry(command, timeout, retries)
    )
```

Circuit-breaker state exposed via existing `mcp_runtime_info` tool:

```python
# tools/debug_tools.py
from ..clients.circuit_breaker import _BREAKERS
from ..clients.ssh_client import _SSH_SEMAPHORES, _SSH_CONCURRENCY

async def mcp_runtime_info() -> dict:
    return {
        # ... existing fields ...
        "circuit_breakers": {
            host: {"state": cb.state, "failures": cb.failure_count}
            for host, cb in _BREAKERS.items()
        },
        "ssh_semaphores": {
            host: {"busy": _SSH_CONCURRENCY - sem._value, "total": _SSH_CONCURRENCY}
            for host, sem in _SSH_SEMAPHORES.items()
        },
    }
```

### Phase 3 — Async Job Pattern for Long-Running Operations

Long-running tools (deploy, compose up, DB backup/restore) block the
single-threaded MCP server for minutes. The async job pattern decouples
submission from completion.

#### Job lifecycle

```
job_start(tool, args) → {"job_id": "abc123"}   ← returns immediately
job_status("abc123")  → {"status": "running", "elapsed_s": 12}
job_status("abc123")  → {"status": "done", "result": {...}}
```

#### In-process `JobManager` (no Redis required)

New file: `deployment_mcp/jobs/job_manager.py`

```python
import asyncio, uuid, time
from dataclasses import dataclass, field
from typing import Any, Coroutine

@dataclass
class Job:
    id: str
    tool_name: str
    status: str = "pending"    # pending | running | done | failed
    result: Any = None
    error: str | None = None
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None

class JobManager:
    MAX_JOBS = 50
    JOB_TTL  = 3600   # 1h

    def __init__(self):
        self._jobs: dict[str, Job] = {}

    async def submit(self, tool_name: str, coro: Coroutine) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, tool_name=tool_name)
        self._jobs[job_id] = job
        self._evict()
        asyncio.create_task(self._run(job, coro))
        return job_id

    async def _run(self, job: Job, coro: Coroutine) -> None:
        job.status = "running"
        try:
            job.result = await coro
            job.status = "done"
        except Exception as exc:
            job.error = str(exc)
            job.status = "failed"
        finally:
            job.finished_at = time.monotonic()

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [
            jid for jid, j in self._jobs.items()
            if j.finished_at and (now - j.finished_at) > self.JOB_TTL
        ]
        for jid in expired:
            del self._jobs[jid]
        if len(self._jobs) > self.MAX_JOBS:
            oldest = sorted(self._jobs.items(), key=lambda x: x[1].started_at)
            for jid, _ in oldest[:len(self._jobs) - self.MAX_JOBS]:
                del self._jobs[jid]

_job_manager = JobManager()

def get_job_manager() -> JobManager:
    return _job_manager
```

New MCP tools: `job_start`, `job_status`, `job_list` (new file
`deployment_mcp/tools/job_tools.py`).

Tools eligible for async mode:

```python
ASYNC_ELIGIBLE = {
    "compose_up", "compose_pull", "compose_down",
    "bfagent_deploy_web", "canary_deploy",
    "db_backup", "db_restore",
    "git_clone",
}
```

---

## Consequences

### Positive

- **Phase 1**: Hanging calls fail within 10–60s instead of blocking for 120s.
  Semaphore pressure is visible in the log file.
- **Phase 2**: After 3 SSH failures on a host, all subsequent calls fast-fail
  for 30s. No cascading deadlock. Circuit state is observable via
  `mcp_runtime_info`.
- **Phase 3**: Deploy, compose, and backup operations never block the MCP
  server. Windsurf can poll status without holding a connection.
- **All phases**: Backward-compatible — no changes to existing tool signatures
  or MCP protocol.

### Negative

- Phase 2 adds a new module (`circuit_breaker.py`) and state that must be
  considered when debugging SSH failures.
- Phase 3 introduces a new polling pattern — Windsurf (Cascade) must call
  `job_status` after `job_start` for long-running tools.
- In-process `JobManager` state is lost on server restart (acceptable — jobs
  are short-lived infrastructure operations).

### Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Circuit opens on transient network blip | Medium | `FAILURE_THRESHOLD=3` requires 3 consecutive failures |
| Job state lost on MCP server restart | Low | Operations are idempotent; re-run is safe |
| `job_status` polling adds round-trips | Low | Windsurf polls every ~5s; overhead is negligible |

---

## Alternatives Considered

### A: Redis Queue as job backend

Use Redis to persist job state and allow multiple MCP server instances to
coordinate. **Rejected for now** because: adds an external dependency,
increases operational complexity, and the in-process `JobManager` achieves
the same result for the single-instance use case. Can be adopted later if
multi-instance coordination becomes necessary.

### B: Remote Worker Agent on the server

Run a small FastAPI service on `88.198.191.108` that executes commands locally
(no SSH overhead). MCP server becomes a pure HTTP client. **Deferred** — higher
implementation effort; Phases 1–3 should resolve the blocking issue first.

### C: Increase SSH concurrency only

Raise `_SSH_CONCURRENCY` from 4 to 8. **Rejected** — does not address the root
cause (semaphore timeout equals command timeout) and increases resource pressure
on the remote host.

---

## Implementation Plan

| Phase | Files changed | Effort | Prerequisite |
|-------|--------------|--------|--------------|
| 1a — Timeout entries | `timeout_config.py` | 15 min | — |
| 1b — Semaphore decoupling | `clients/ssh_client.py` | 20 min | — |
| 1c — Watchdog task | `server.py` | 20 min | — |
| 2 — Circuit Breaker | `clients/circuit_breaker.py` (new), `ssh_client.py`, `debug_tools.py` | 2h | Phase 1 |
| 3 — Async Jobs | `jobs/job_manager.py` (new), `tools/job_tools.py` (new), `server.py` | 4h | Phase 2 |

Each phase is independently releasable via the existing `mcp-hub` CI/CD pipeline.
