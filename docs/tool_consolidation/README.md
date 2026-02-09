# Tool Consolidation Pattern for MCP Server

Dispatch-Pattern to reduce many MCP tools to a few consolidated meta-tools.

**Status: PRODUCTION** (deployed, default-on since Feb 2026)

## Problem

| Client | Tool-Limit | Consequence |
|--------|-----------|------------|
| Windsurf | ~100 | Tools get ignored |
| Cursor | 40 | Hard-limit, rest invisible |
| Claude Code | No limit, ~700 tokens/tool | Context window exhausted |
| Claude Desktop | 100 | Tools get truncated |

## Solution: Dispatch-Pattern

```text
BEFORE: server_list, server_create, server_delete, ...  (9 tools)
AFTER:  server_manage(action="list|create|delete", ...)  (1 tool)
```

## Production Architecture

```text
mcp-hub/deployment_mcp/src/deployment_mcp/consolidated/
├── __init__.py
├── base.py              # ConsolidatedTool + @action decorator
├── registry.py          # Tool instantiation + MCP registration
├── server_tool.py       # 9 actions
├── firewall_tool.py     # 7 actions
├── docker_tool.py       # 13 actions (incl. container_exec)
├── database_tool.py     # 9 actions
├── network_tool.py      # 19 actions (SSL + DNS)
├── env_tool.py          # 8 actions (env + secrets)
├── ssh_tool.py          # 6 actions
├── git_tool.py          # 14 actions
├── system_tool.py       # 8 actions (system + nginx + logs)
├── cicd_tool.py         # 8 actions (GitHub Actions + deploy)
└── pip_tool.py          # 5 actions
```

## Autonomous Local Tools (Orchestrator MCP)

```text
mcp-hub/orchestrator_mcp/local_tools.py
├── run_tests      # pytest via WSL, parse pass/fail/skip
├── run_lint       # ruff check/fix on mcp modules
├── run_git        # status/diff/log/add_commit_push
└── run_command_safe  # allowlisted commands only
```

## Production Result

| Category | Before (Tools) | After (Tools) | Actions | Status |
|----------|---------------|---------------|---------|--------|
| Hetzner Server | 9 | **1** `server_manage` | 9 | DONE |
| Firewall | 7 | **1** `firewall_manage` | 7 | DONE |
| Docker | 13 | **1** `docker_manage` | 13 | DONE |
| PostgreSQL | 9 | **1** `database_manage` | 9 | DONE |
| SSL + DNS | 19 | **1** `network_manage` | 19 | DONE |
| Env + Secrets | 8 | **1** `env_manage` | 8 | DONE |
| SSH Remote | 6 | **1** `ssh_manage` | 6 | DONE |
| Git | 14 | **1** `git_manage` | 14 | DONE |
| System | 8 | **1** `system_manage` | 8 | DONE |
| CI/CD + Deploy | 8 | **1** `cicd_manage` | 8 | DONE |
| Pip | 5 | **1** `pip_manage` | 5 | DONE |
| Debug | 1 | **1** `mcp_runtime_info` | 1 | DONE |
| **TOTAL** | **107** | **12** | **107** | |

**Reduction: 89%** (107 -> 12 MCP tools)

## Key Design Decisions

1. **Wrapper pattern** - consolidated tools delegate to existing tool functions
2. **`DEPLOYMENT_MCP_CONSOLIDATED` env** - defaults to `true`, set `false` for legacy
3. **dict return type** - not strings, preserving structured data
4. **Automatic schema generation** - JSON Schema from Python type hints
5. **Confirm-check** - destructive actions require `confirm=true`
6. **Action descriptions** - `[R]`/`[W]`/`[!]` prefixes in tool description

## Commits

- `cd39f42` - consolidated tools + container_exec + canary_deploy + run_tests
- `bc5860f` - local_tools.py extraction + run_lint/run_git/run_command_safe
- `d7ee212` - wsl.exe path fix + ruff lint fixes
