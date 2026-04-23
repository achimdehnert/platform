---
trigger: always_on
---

# Project Facts: <REPO_NAME>

## Environments

| Env | Compose File | Host Port | Health URL | Public URL |
|-----|-------------|-----------|------------|------------|
| local | `docker-compose.local.yml` | `<LOCAL_PORT>` | `http://localhost:<LOCAL_PORT>/livez/` | http://localhost:<LOCAL_PORT> |
| staging | `docker-compose.staging.yml` | `<STAGING_PORT>` | `http://localhost:<STAGING_PORT>/livez/` | https://<STAGING_DOMAIN> |
| prod | `docker-compose.prod.yml` | `<PROD_PORT>` | `http://localhost:<PROD_PORT>/livez/` | https://<PROD_DOMAIN> |

## Docker Containers

| Container | Name | Purpose |
|-----------|------|---------|
| web | `<PREFIX>_web` | gunicorn:8000 |
| db | `<PREFIX>_db` | postgres:16 |
| redis | `<PREFIX>_redis` | redis:7 |
| worker | `<PREFIX>_worker` | celery (optional) |

## Database

- **DB name**: `<DB_NAME>`
- **DB user**: `<DB_USER>`
- **DB container**: `<PREFIX>_db`
- **Migrations**: `docker exec <PREFIX>_web python manage.py migrate`

## System Dependencies (Server)

- **Install ohne sudo**: `ssh root@localhost "apt-get install -y <package>"`
- devuser hat KEIN sudo-Passwort

## Django Settings

- Local: `config.settings.local`
- Staging: `config.settings.staging` (or production)
- Prod: `config.settings.production`
- **Secrets**: `.env` (nicht in Git) — Template: `.env.example`

## Make Targets

```bash
make test          # unit tests
make test-v        # verbose
make lint          # ruff
make migrate       # run migrations (local)
make shell         # Django shell
```

## Git / GitHub

- Repo: `https://github.com/achimdehnert/<REPO_NAME>`
- Branch: `main`
- Push: `git push` (SSH-Key konfiguriert)
