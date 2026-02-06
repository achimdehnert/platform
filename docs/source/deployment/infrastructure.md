# Infrastruktur

Siehe auch: [Architektur-Übersicht](../architecture/infrastructure.md)

## Server-Setup

- **Provider**: Hetzner Cloud
- **IP**: 88.198.191.108
- **OS**: Ubuntu 24.04 LTS
- **Docker**: Docker Engine + Compose v2

## Shared Services

| Service | Container | Port | Zweck |
|---------|-----------|------|-------|
| PostgreSQL 16 | bfagent_db | 5432 | Shared Database |
| Redis 7 | bfagent_redis | 6379 | Cache + Celery Broker |
| Nginx | nginx | 80/443 | Reverse Proxy + TLS |

## Docker Network

Alle Apps nutzen das externe Netzwerk `bf_platform_prod`:

```bash
docker network create bf_platform_prod
```

## Backup

```bash
# PostgreSQL Dump
docker exec bfagent_db pg_dump -U bfagent weltenhub > weltenhub_backup.sql

# Alle Datenbanken
docker exec bfagent_db pg_dumpall -U bfagent > full_backup.sql
```
