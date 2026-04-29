# Deployment Guide — <Repo-Name>

## Voraussetzungen

- Docker + Docker Compose v2
- Zugriff auf Hetzner Server (SSH-Key hinterlegt)
- `.env.prod` vorhanden (Template: `.env.example`)

---

## Lokale Umgebung

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec <web-container> python manage.py migrate
docker compose exec <web-container> python manage.py createsuperuser
```

Health-Check: http://localhost:<PORT>/livez/

---

## Production Deployment

```bash
bash scripts/ship.sh
```

Oder manuell:

```bash
# 1. Image bauen
docker build -t ghcr.io/achimdehnert/<repo>/<repo>-web:latest .

# 2. Auf Server deployen
ssh root@88.198.191.108
docker stop <container> && docker rm <container>
docker compose -f docker-compose.prod.yml up -d
```

Health-Check: https://<prod-url>/healthz/

---

## Health-Endpunkte

| Endpunkt | Zweck | Erwartung |
|---|---|---|
| `/livez/` | Liveness (kein DB-Check) | HTTP 200 immer |
| `/healthz/` | Readiness (DB + Redis) | HTTP 200 wenn bereit |

---

## Secrets / Konfiguration

```
.env.prod                     ← Repo-spezifische Werte
/opt/shared-secrets/api-keys.env  ← Geteilte LLM-Keys (Server)
```

**Nie** Secrets im Code oder in `docker-compose.prod.yml` unter `environment:`.
Immer `env_file:` nutzen.

---

## Rollback

```bash
# Letztes funktionierendes Image identifizieren
docker images ghcr.io/achimdehnert/<repo>/<repo>-web

# Rollback
docker stop <container> && docker rm <container>
docker run -d --name <container> \
  --env-file .env.prod \
  ghcr.io/achimdehnert/<repo>/<repo>-web:<previous-tag>
```

---

## Migrations-Workflow

```bash
# Vor jedem Build — Konflikte prüfen
python manage.py migrate --check

# Migration erstellen
python manage.py makemigrations <app>

# Anwenden (Production)
docker exec <container> python manage.py migrate
```

---

## Monitoring

- **Logs:** `docker logs <container> --tail=100 -f`
- **Health:** `curl https://<prod-url>/healthz/`
- **DB:** `docker exec <db-container> psql -U <user> -d <db> -c "SELECT NOW();"`
