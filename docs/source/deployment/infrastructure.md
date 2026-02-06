# Infrastruktur

Siehe auch: [Architektur-Übersicht](../architecture/infrastructure.md)

## Server-Setup

- **Provider**: Hetzner Cloud
- **IP**: 88.198.191.108
- **OS**: Ubuntu 24.04 LTS
- **Docker**: Docker Engine + Compose v2
- **Registry**: GitHub Container Registry (GHCR)

## Verzeichnisstruktur (VM)

```text
/srv/
├── bfagent/
│   ├── docker-compose.prod.yml
│   ├── .env.prod                  # Secrets (nie in Git)
│   ├── scripts/
│   │   └── deploy-remote.sh      # Deploy-Script
│   ├── backups/                   # Auto-Backups vor Deploy
│   └── deployments.jsonl          # Audit-Log
└── travel-beat/
    ├── docker-compose.prod.yml
    └── .env.prod
```

## Shared Services

| Service | Container | Port | Zweck |
|---------|-----------|------|-------|
| PostgreSQL 16 | bfagent_db | 5432 | Shared Database |
| Redis 7 | bfagent_redis | 6379 | Cache + Celery Broker |
| Caddy | bfagent_caddy | 80 | Reverse Proxy + Auto-TLS |

## Docker Network

Alle Apps nutzen das externe Netzwerk `bf_platform_prod`:

```bash
docker network create bf_platform_prod
```

## CI/CD Pipeline

Reusable Workflows in `platform/.github/workflows/`:

| Workflow | Zweck |
|----------|-------|
| `_ci-python.yml` | Lint, Test, Security Scan |
| `_build-docker.yml` | Build + Push zu GHCR |
| `_deploy-hetzner.yml` | SSH Deploy via `deploy-remote.sh` |

App-Repos nutzen diese via `uses: achimdehnert/platform/.github/workflows/_*.yml@main`.

## Health Endpoints

| Endpoint | Zweck | Checks |
|----------|-------|--------|
| `/livez/` | Liveness (Prozess lebt) | Keine |
| `/healthz/` | Readiness (Traffic-fähig) | DB, Redis, Disk, Migrations |
| `/health/` | Legacy Health Check | DB, Cache |

## Backup

```bash
# Automatisch vor jedem Deploy via deploy-remote.sh
# Manuell:
docker exec bfagent_db pg_dumpall -U bfagent | gzip > backup.sql.gz
```

## GitHub Secrets

| Secret | Zweck |
|--------|-------|
| `DEPLOY_SSH_KEY` | Ed25519 Private Key |
| `DEPLOY_USER` | SSH User (`deploy`) |
| `STAGING_HOST` / `PROD_HOST` | Server IP/Hostname |
| `SLACK_WEBHOOK_URL` | Deploy-Benachrichtigungen |

Konfiguriere **GitHub Environment Protection Rules** für `production`:
mindestens 1 Required Reviewer, nur `main` Branch + `v*` Tags.
