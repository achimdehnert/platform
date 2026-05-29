---
description: Start local Docker environment, run health checks, report status
---

# /run-local — Start Local Environment

## Pre-flight: Kontext laden
1. Lies `.windsurf/rules/project-facts.md` im aktuellen Repo
2. Extrahiere: `compose_local`, `local_port`, `local_health_url`, Container-Prefix
3. Prüfe ob `.env` existiert (falls nicht: `.env.example` als Hinweis zeigen)

## Step 0: Compose-Datei + App-Service erkennen
// turbo
```bash
# Compose-Datei robust wählen: local → dev → generisch (NICHT docker-compose.yml
# annehmen — viele Repos haben nur dev/prod). Deckt sich mit gen_project_facts.
for c in docker-compose.local.yml docker-compose.dev.yml docker-compose.yml; do
  [ -f "$c" ] && COMPOSE="$c" && break
done
echo "COMPOSE=${COMPOSE:-<keine>}"
# Hat das Compose einen App-/web-Service (oder nur DB/Redis)?
if [ -n "${COMPOSE:-}" ] && grep -qE '^\s{2,}(web|app|django|[a-z-]*-web):' "$COMPOSE"; then
  echo "MODE=docker (App-Service im Compose)"
else
  echo "MODE=host (Compose hat nur Infra → App via 'make dev' auf dem Host)"
fi
```

> **Zwei Modi:**
> - **MODE=host** (Compose hat nur DB/Redis, z. B. ausschreibungs-hub): App läuft auf dem
>   Host via `make dev` → `platform/scripts/dev.sh`. Das übernimmt für Multi-Tenant-Repos
>   `migrate_schemas --shared` + `seed_public_tenant` (platform:ADR-219). Dann Step 1 starten:
>   `docker compose -f "$COMPOSE" up -d` (nur DB/Redis), danach `make dev`.
> - **MODE=docker**: App-Container wird mitgebaut → unten weiter.

## Step 1: .env prüfen
// turbo
```bash
test -f .env && echo "✅ .env vorhanden" || echo "⚠️  .env fehlt — kopiere .env.example"
```

## Step 2: Docker Build + Start
// turbo
```bash
for c in docker-compose.local.yml docker-compose.dev.yml docker-compose.yml; do [ -f "$c" ] && COMPOSE="$c" && break; done
docker compose -f "$COMPOSE" up -d --build 2>&1 | tail -20
```

## Step 2b: Multi-Tenant Bring-up (nur django_tenants — platform:ADR-219)
// turbo
```bash
for c in docker-compose.local.yml docker-compose.dev.yml docker-compose.yml; do [ -f "$c" ] && COMPOSE="$c" && break; done
if grep -rqsE 'django_tenants\.postgresql_backend' config/ 2>/dev/null; then  # NUR schema-per-tenant (nicht row-level/RLS — ADR-219)
  WEB=$(docker compose -f "$COMPOSE" ps --services 2>/dev/null | grep -E 'web|app|django' | head -1)
  if [ -n "$WEB" ]; then
    docker compose -f "$COMPOSE" exec -T "$WEB" python manage.py migrate_schemas --shared --noinput
    docker compose -f "$COMPOSE" exec -T "$WEB" python manage.py seed_public_tenant || \
      echo "⚠️  Kein seed_public_tenant — laut ADR-219 Pflicht für django_tenants-Repos"
  else
    echo "ℹ️  Kein App-Service im Compose → Multi-Tenant-Setup macht 'make dev' (dev.sh)"
  fi
fi
```

## Step 3: Warten bis healthy (max 60s)
// turbo
```bash
for c in docker-compose.local.yml docker-compose.dev.yml docker-compose.yml; do [ -f "$c" ] && COMPOSE="$c" && break; done
for i in $(seq 1 12); do
  STATUS=$(docker compose -f "$COMPOSE" ps --format json 2>/dev/null | python3 -c "
import sys, json
data = sys.stdin.read()
try:
    services = [json.loads(line) for line in data.strip().split('\n') if line]
    unhealthy = [s['Service'] for s in services if s.get('Health','') not in ('healthy','')]
    print('WAIT: ' + ', '.join(unhealthy) if unhealthy else 'OK')
except: print('WAIT')
" 2>/dev/null || echo "WAIT")
  [ "$STATUS" = "OK" ] && break
  echo "Warte... ($i/12) $STATUS"
  sleep 5
done
```

## Step 4: Health Check
```bash
LOCAL_PORT=$(grep -E "local_port|Local.*\|.*[0-9]{4}" .windsurf/rules/project-facts.md 2>/dev/null | grep -oE "[0-9]{4,5}" | head -1)
curl -sf "http://localhost:${LOCAL_PORT:-8000}/livez/" && echo "✅ App healthy" || echo "❌ Health check failed"
```

## Step 5: Status Report
// turbo
```bash
for c in docker-compose.local.yml docker-compose.dev.yml docker-compose.yml; do [ -f "$c" ] && COMPOSE="$c" && break; done
docker compose -f "$COMPOSE" ps
```

## Ergebnis ausgeben
Zeige:
- ✅ / ❌ pro Container (bzw. Host-Runserver-Status bei MODE=host)
- URL: `http://localhost:<PORT>`
- Fehler aus Logs falls unhealthy: `docker compose -f "$COMPOSE" logs --tail=20 <web-service>`
