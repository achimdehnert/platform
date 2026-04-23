---
description: Start local Docker environment, run health checks, report status
---

# /run-local — Start Local Environment

## Pre-flight: Kontext laden
1. Lies `.windsurf/rules/project-facts.md` im aktuellen Repo
2. Extrahiere: `compose_local`, `local_port`, `local_health_url`, Container-Prefix
3. Prüfe ob `.env` existiert (falls nicht: `.env.example` als Hinweis zeigen)

## Step 1: .env prüfen
// turbo
```bash
test -f .env && echo "✅ .env vorhanden" || echo "⚠️  .env fehlt — kopiere .env.example"
```

## Step 2: Docker Build + Start
// turbo
```bash
docker compose -f docker-compose.local.yml up -d --build 2>&1 | tail -20
```

## Step 3: Warten bis healthy (max 60s)
// turbo
```bash
for i in $(seq 1 12); do
  STATUS=$(docker compose -f docker-compose.local.yml ps --format json 2>/dev/null | python3 -c "
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
docker compose -f docker-compose.local.yml ps
```

## Ergebnis ausgeben
Zeige:
- ✅ / ❌ pro Container
- URL: `http://localhost:<PORT>`
- Fehler aus Logs falls unhealthy: `docker compose -f docker-compose.local.yml logs --tail=20 web`
