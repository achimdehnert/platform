---
description: Deploy production with safety gates, health checks, rollback on failure
---

# /run-prod — Production Deploy

## Wann `/run-prod` — und wann nicht?

`/run-prod` ist der **manuelle Notfall-Handpfad** (direktes `docker compose` am Server mit
sauberem Ja/Nein-Gate) — nicht der Standard-Pfad (Deploy-Trias-Kanon 2026-07-04).

- **Wann `/run-prod`:** Standard-Deploy via `/ship` ist nicht möglich (Server-seitiger
  Short-Trigger / CI nicht erreichbar) und du musst per Hand direkt am `docker compose`
  deployen.
- **Wann NICHT / stattdessen:**
  - Regulärer Prod-Deploy → **`/ship`** (kanonischer Standard: verify → push → CI → migrate
    → health-check).
  - Deploy fehlgeschlagen, Prod rot → **`/rollback`**.
  - `/deploy` (infra-deploy-Actions) ist **deprecated** — nicht mehr verwenden.

## ⚠️ GATE: Explizite Bestätigung erforderlich
Frage den User: "Prod-Deploy für `<REPO>` bestätigen? (ja/nein)"
→ Bei "nein": Abbruch
→ Bei "ja": weiter mit Step 1

## Pre-flight: Kontext laden
1. Lies `.windsurf/rules/project-facts.md` im aktuellen Repo
2. Extrahiere: `prod_port`, `prod_url`, `health_endpoint`, Container-Prefix
3. Merke aktuellen Image-SHA als Rollback-Punkt

## Step 1: Aktueller Stand dokumentieren
// turbo
```bash
git log --oneline -5
docker compose -f docker-compose.prod.yml ps
```

## Step 2: Aktuellen Image-Tag für Rollback sichern
// turbo
```bash
docker compose -f docker-compose.prod.yml images | tee /tmp/pre-deploy-images.txt
```

## Step 3: Build
```bash
docker compose -f docker-compose.prod.yml build 2>&1 | tail -20
```

## Step 4: Zero-Downtime Deploy
```bash
docker compose -f docker-compose.prod.yml up -d --no-deps web 2>&1 | tail -10
```

## Step 5: Migrations
```bash
CONTAINER=$(docker compose -f docker-compose.prod.yml ps -q web | head -1)
docker exec "$CONTAINER" python manage.py migrate --no-input 2>&1 | tail -10
```

## Step 6: Health Check (3 Versuche)
```bash
PROD_PORT=$(grep -E "prod.*\|.*[0-9]{4}" .windsurf/rules/project-facts.md 2>/dev/null | grep -oE "[0-9]{4,5}" | head -1)
for i in 1 2 3; do
  sleep 5
  curl -sf "http://localhost:${PROD_PORT}/livez/" && echo "✅ Prod healthy (Versuch $i)" && break
  echo "⚠️  Versuch $i fehlgeschlagen"
  [ $i -eq 3 ] && echo "❌ ROLLBACK empfohlen — siehe /rollback"
done
```

## Step 7: Vollständiger Status
// turbo
```bash
docker compose -f docker-compose.prod.yml ps
```

## Bei Fehler: Rollback
```bash
# Vorherige Images wiederherstellen:
# docker compose -f docker-compose.prod.yml down web
# docker tag <previous-image> current
# docker compose -f docker-compose.prod.yml up -d web
```

## Ergebnis ausgeben
Zeige:
- ✅ / ❌ Deploy-Status
- Prod URL aus project-facts.md
- Response-Time des Health-Checks
