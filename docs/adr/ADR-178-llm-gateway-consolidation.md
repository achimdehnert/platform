# ADR-178: LLM Gateway Consolidation

- **Status:** Accepted
- **Date:** 2026-05-05
- **Deciders:** achimdehnert
- **Related:** ADR-115 (LLM Usage Logging), ADR-116 (Agent Team Tracking), ADR-176 (MCP-Server SSoT)

## Context and Problem Statement

The `mcp-hub` repository contains **three separate LLM Gateway implementations** that have accumulated over time. This creates confusion about which module is authoritative, complicates maintenance, and blocks the rename requested in Issue #12.

### Current State (Production, 2026-05-05)

| Container | Image | Entrypoint | Port | Status |
|-----------|-------|-----------|------|--------|
| `0aa21798612b_llm_gateway` | `ghcr.io/achimdehnert/mcp-hub/llm-gateway:latest` | `python -m llm_mcp.http_gateway` | 8100 | Running (5 weeks), **likely unused** |
| `llm_mcp` | `iilgmbh/llm_mcp_service:latest` | `uvicorn llm_mcp_service.main:app` | 8001 | Running, **active** (119 calls logged) |

### Code Modules in Repository

| Module | Role | API Surface | DB Integration |
|--------|------|-------------|----------------|
| `llm_mcp/http_gateway.py` | **V0** — Legacy gateway | `/generate`, `/models`, `/health` | None (uses `LLMService` class) |
| ~~`llm_mcp/main.py`~~ | **V1** — Dead code (**deleted** `43fa59e`) | `/v1/chat`, `/v1/agent`, `/health` | Inline asyncpg (hardcoded pricing) |
| `llm_mcp/server.py` | MCP-stdio server | MCP tools for Cascade | Via `LLMService` |
| `llm_mcp_service/main.py` | **V2** — Active gateway | `/v1/chat`, `/v1/agent`, `/health` | SQLAlchemy + BackgroundTasks |
| `llm_mcp_service/tools.py` | Function Calling | 5 read-only tools | GitHub API, pgvector |
| `llm_mcp_service/services/` | Usage logging + pricing | DB-backed pricing with cache | `llm_calls`, `llm_model_pricing` |

### Problems

1. **Naming confusion**: `llm_mcp` contains both a MCP-stdio server AND a legacy HTTP gateway (`http_gateway.py`), plus V1 dead code (`main.py`, now deleted)
2. **V1 is dead code**: `llm_mcp/main.py` duplicates V2 but lacks tools, BackgroundTasks, and proper pricing — never deployed
3. **V0 consumes resources**: The `0aa21798612b_llm_gateway` container runs but appears unused (no calls from it in `llm_calls`)
4. **Issue #12 blocked**: Renaming `llm_mcp_service` → `llm_gateway` requires understanding which code is live

## Decision Drivers

- Production stability (V2 is active with 119 logged calls)
- Code clarity and maintainability
- Issue #12 completion (rename to `llm_gateway`)
- Minimal risk during migration

## Considered Options

### Option A: Rename-only (V2 stays, V1 deleted)

Rename `llm_mcp_service/` → `llm_gateway/`, delete dead V1 code from `llm_mcp/main.py`, stop V0 container.

- **Pro**: Minimal risk, fast, no feature changes to active service
- **Pro**: V2 is strict superset of V1 — nothing lost
- **Con**: V0's `/models` + `/generate` surface disappears (unknown consumers possible)

### Option B: Merge V0+V2 into unified `llm_gateway`

Combine V0's model-registry features (`/models`, `/generate`) with V2's modern implementation, then rename.

- **Pro**: Preserves all API surfaces
- **Con**: Significant dev effort, V0 uses completely different API contract (prompt-based vs message-based)
- **Con**: V0's `LLMService` class (DB model registry) has no current consumers

### Option C: Status quo + documentation

Keep both running, document clearly, address later.

- **Pro**: Zero risk
- **Con**: Perpetuates confusion, Issue #12 stays blocked, resources wasted on V0

## Decision Outcome

**Chosen: Option A — Rename-only with V1 deletion**

### Rationale

- V2 (`llm_mcp_service`) is the only actively used gateway (119 calls since 2026-03-09)
- V0's `/generate` and `/models` endpoints serve a completely different API contract (prompt-based, not message-based) — no current consumers
- V1 (`llm_mcp/main.py`) is an unmaintained copy of V2 without its improvements — pure dead code
- The MCP-stdio server (`llm_mcp/server.py`) must remain as `llm_mcp` (it's the Cascade MCP entrypoint)

## Migration Plan

### Phase 1: Cleanup (no downtime) — ✅ done

1. ~~Delete `llm_mcp/main.py` (dead V1 code)~~ — done (commit `43fa59e`, 2026-05-05)
2. ~~Migrate `tests/test_llm_mcp.py` to import from `llm_mcp_service.main`~~ — done (same commit)
3. ~~Confirm `llm_mcp/` retains only MCP-stdio files~~ — done: `server.py`, `service.py`, `db.py`, `__main__.py`, `__init__.py`, `providers/`
4. ~~Stop and remove V0 container (`0aa21798612b_llm_gateway`)~~ — done (2026-05-05, confirmed unused)
5. ~~Delete `llm_mcp/http_gateway.py`~~ — done (commit `ddb17af`, 2026-05-05)

### Phase 2: Rename — ✅ done

1. ~~Rename directory: `llm_mcp_service/` → `llm_gateway/`~~ — done (commit `5929e60`, 2026-05-05)
2. ~~Update all internal imports~~ — done (same commit)
3. ~~Update `docker-compose.llm-mcp.yml`: service name, container name, image tag~~ — done
4. ~~Update `docker-compose.yml`: orchestrator LLM URL default~~ — done
5. ~~Update Dockerfile CMD: `uvicorn llm_gateway.main:app`~~ — done
6. ~~Consolidate image to `ghcr.io/achimdehnert/mcp-hub/llm-gateway`~~ — done
7. Rebuild image + deploy — **pending** (next deploy)

### Phase 3: Naming alignment

1. Update CORS origins in orchestrator referencing old container name
2. Update `platform/docs/mcp/SERVERS.md`
3. Close Issue #12 Task 1

## Consequences

### Positive

- Single, clear LLM gateway module (`llm_gateway/`)
- No dead code confusion
- One fewer running container in production
- Issue #12 unblocked

### Negative

- V0's `/models` and `/generate` API surface is removed (if any unknown consumer exists, it breaks)
- Image rebuild required for Phase 2

### Risks

- **Risk**: Unknown consumer of V0 (`/generate` endpoint)
  - **Mitigation**: Monitor V0 container logs for 1 week before stopping; check nginx access logs for port 8100

## Technical Notes

### Registry Consolidation

- V0 uses `ghcr.io/achimdehnert/mcp-hub/llm-gateway:latest` (GitHub Container Registry)
- V2 uses `iilgmbh/llm_mcp_service:latest` (Docker Hub, legacy org)
- Phase 2 should consolidate to `ghcr.io/achimdehnert/mcp-hub/llm-gateway:latest` (platform standard)

### Database (unchanged)

- Tables `llm_calls` + `llm_model_pricing` in `orchestrator_mcp` DB on `mcp_hub_db` container
- User: `orchestrator` (despite the name — shared DB for all mcp-hub services)
- 23 columns including `agent_role`, `complexity`, `routing_reason` (ADR-116)
- Migration: `0042_llm_calls_and_pricing.py` (already applied)

### Feature Parity V1→V2 (confirming V1 deletion is safe)

| Feature | V1 has | V2 has | V2 improvement |
|---------|--------|--------|----------------|
| `/v1/chat` | ✅ | ✅ | + tools, history, repo/source/tenant fields |
| `/v1/agent` | ✅ | ✅ | + BackgroundTasks, SQLAlchemy logging |
| Retry logic | ✅ | ✅ | Same (2 attempts) |
| Auth (Bearer) | ✅ | ✅ | Same |
| CORS | ✅ | ✅ | Same |
| Pricing | Hardcoded dict | DB-backed + cache | More accurate, historized |
| Error logging | Inline asyncpg | BackgroundTasks (K-02) | Non-blocking |
| Function Calling | ❌ | ✅ | 5 read-only tools |
| Conversation History | ❌ | ✅ | Last 10 messages |

**Conclusion**: V2 is a strict superset of V1. Deleting V1 loses nothing.
