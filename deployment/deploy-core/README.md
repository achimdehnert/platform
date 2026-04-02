# Deploy-Core Scripts (ADR-156)

Server-side deploy scripts for the IIL Platform. These scripts live on the
production server at `/opt/deploy-core/` and are triggered via SSH Short-Trigger
pattern (ADR-156) or GitHub Actions fallback (ADR-075).

## Scripts

| Script | Purpose | Duration |
|--------|---------|----------|
| `deploy.sh` | Main deploy: pull, migrate, recreate, health-check, rollback | 60-180s |
| `deploy-start.sh` | MCP-facing wrapper: starts deploy in background, returns JSON | <2s |
| `deploy-status.sh` | Status polling: returns JSON with status, PID, elapsed, log-tail | <1s |

## Usage

```bash
# Direct (on server):
bash /opt/deploy-core/deploy.sh risk-hub docker-compose.prod.yml 8001

# Via MCP Short-Trigger:
ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-start.sh risk-hub", timeout=10)

# Poll status:
ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-status.sh risk-hub")
```

## Arguments

| Arg | deploy.sh | deploy-start.sh | deploy-status.sh |
|-----|-----------|-----------------|------------------|
| `$1` | repo name (required) | repo name (required) | repo name (required) |
| `$2` | compose file (default: docker-compose.prod.yml) | compose file | — |
| `$3` | health port (default: 8000) | health port | — |

## Server Paths

```
/opt/deploy-core/          ← Scripts (this directory)
/var/run/deploy/           ← State files (lock, PID, status)
/var/log/deploy/           ← Log files + symlinks
/etc/logrotate.d/deploy-logs ← Log rotation (7 days)
```

## Deployment to Server

```bash
# From platform repo:
scp deployment/deploy-core/deploy*.sh root@88.198.191.108:/opt/deploy-core/
ssh root@88.198.191.108 "chmod +x /opt/deploy-core/*.sh"
scp deployment/deploy-core/logrotate_deploy-logs root@88.198.191.108:/etc/logrotate.d/deploy-logs
```

## References

- ADR-156: Reliable Deployment Pipeline
- ADR-075: Deployment Execution Strategy (amended by ADR-156)
- ADR-022: Code Quality & Docker Standards (COMPOSE_PROJECT_NAME)
