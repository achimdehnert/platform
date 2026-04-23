---
description: Deploy and verify staging environment with health checks
---

# /run-staging — Staging Environment

## Pre-flight: Kontext laden
1. Lies `.windsurf/rules/project-facts.md` im aktuellen Repo
2. Extrahiere: `staging_port`, `staging_url`, Container-Prefix
3. **Gate**: Bestätige dass Staging-Deploy gewünscht ist

## Step 1: Git Status prüfen
// turbo
```bash
git status --short && git log --oneline -3
```

## Step 2: Aktuelle Images bauen
```bash
docker compose -f docker-compose.staging.yml build --no-cache 2>&1 | tail -10
```

## Step 3: Staging starten / updaten
```bash
docker compose -f docker-compose.staging.yml up -d 2>&1 | tail -20
```

## Step 4: Migrations ausführen
```bash
CONTAINER=$(docker compose -f docker-compose.staging.yml ps -q web | head -1)
docker exec "$CONTAINER" python manage.py migrate --no-input 2>&1 | tail -10
```

## Step 5: Health Check
```bash
STAGING_PORT=$(grep -E "staging.*\|.*[0-9]{4}" .windsurf/rules/project-facts.md 2>/dev/null | grep -oE "[0-9]{4,5}" | head -1)
curl -sf "http://localhost:${STAGING_PORT}/livez/" && echo "✅ Staging healthy" || echo "❌ Staging health check failed"
```

## Step 6: Status Report
// turbo
```bash
docker compose -f docker-compose.staging.yml ps
```

## Ergebnis ausgeben
Zeige:
- ✅ / ❌ pro Container
- Staging URL aus project-facts.md
- Letzte 20 Log-Zeilen bei Fehler
