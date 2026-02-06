# Docker Deployment

## Per-App Compose Files

Jede App hat ein eigenes `docker-compose.prod.yml` in `/opt/<app>/`.

## Weltenhub

```yaml
services:
  weltenhub-web:       # Django/Gunicorn (:8081)
  weltenhub-celery:    # Background tasks
  weltenhub-beat:      # Scheduled tasks
```

## BF Agent

```yaml
services:
  bfagent-web:         # Django/Gunicorn (:8000)
```

## Deploy-Workflow

```bash
# 1. Code auf Server bringen
scp app.tar.gz root@88.198.191.108:/tmp/
ssh root@88.198.191.108 "cd /opt/<app> && tar xzf /tmp/app.tar.gz"

# 2. Image bauen
docker build -t ghcr.io/achimdehnert/<app>:latest .

# 3. Container neu starten
docker compose -f docker-compose.prod.yml up -d --force-recreate <service>

# 4. Migrations ausführen
docker exec <container> python manage.py migrate

# 5. Status prüfen
docker compose -f docker-compose.prod.yml ps
docker logs <container> --tail 50
```

## Healthchecks

Alle Web-Container haben einen Healthcheck auf `/health/`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Resource Limits

| Service | Memory Limit | Memory Reserved |
|---------|-------------|----------------|
| weltenhub-web | 512 MB | 256 MB |
| weltenhub-celery | 256 MB | — |
| bfagent-web | 512 MB | 256 MB |
