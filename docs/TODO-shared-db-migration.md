# TODO: Shared PostgreSQL Migration

**Status:** Geplant für später  
**Priorität:** Niedrig  
**Breaking:** Nein (non-breaking migration möglich)

## Ziel

Eine PostgreSQL-Instanz mit mehreren Datenbanken statt separater Container pro App.

## Vorteile

- ~600MB RAM Ersparnis auf Hetzner
- Einfacheres Localhost-Setup (1 Container statt 3)
- Zentrales Backup

## Architektur (Ziel)

```
PostgreSQL (Port 5432)
├── bfagent_dev / bfagent_prod
├── travel_beat_dev / travel_beat_prod  
└── mcphub_dev / mcphub_prod
```

## Migrations-Schritte

### 1. Platform docker-compose.yml erstellen

```yaml
# platform/docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: platform
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./docker/postgres/init:/docker-entrypoint-initdb.d
      - platform_postgres:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 2. Init-Script erstellen

```sql
-- platform/docker/postgres/init/01-create-databases.sql
CREATE DATABASE bfagent_dev;
CREATE DATABASE travel_beat_dev;
CREATE DATABASE mcphub_dev;

CREATE USER bfagent WITH PASSWORD 'bfagent_dev_2024';
CREATE USER travel_beat WITH PASSWORD 'travel_beat_dev_2024';

GRANT ALL PRIVILEGES ON DATABASE bfagent_dev TO bfagent;
GRANT ALL PRIVILEGES ON DATABASE travel_beat_dev TO travel_beat;
```

### 3. Apps umstellen (nur .env ändern)

```bash
# bfagent/.env
DATABASE_URL=postgresql://bfagent:bfagent_dev_2024@localhost:5432/bfagent_dev

# travel-beat/.env.local  
DATABASE_URL=postgresql://travel_beat:travel_beat_dev_2024@localhost:5432/travel_beat_dev
```

### 4. Alte Container entfernen

```bash
# Nach erfolgreicher Migration
docker compose -f docker-compose.yml down -v  # bfagent
docker compose -f docker-compose.local.yml down -v  # travel-beat
```

## Hetzner Production

Gleiche Strategie - ein PostgreSQL Container mit mehreren DBs.

---

**Erstellt:** 2026-01-27  
**Autor:** Cascade
