# ADR-141: PostgreSQL-Only Testing

**Status:** ACCEPTED  
**Datum:** 2026-03-12  
**Scope:** Alle Platform-Repos (coach-hub, risk-hub, billing-hub, etc.)

## Kontext

Tests in coach-hub liefen auf SQLite (in-memory), Production auf PostgreSQL.
Das führte zu:

1. **Versteckte Bugs:** PostgreSQL-spezifische Features (`SET session var`,
   `RESET`, JSON-Operatoren, RLS) crashen auf SQLite
2. **Workarounds statt Fixes:** `if connection.vendor == "postgresql"` Guards
   verstecken Produktionscode vor Tests
3. **Falsche Sicherheit:** 278 Tests grün auf SQLite, 65 davon rot auf
   PostgreSQL (TenantMiddleware `RESET app.tenant_id`)
4. **Feature-Drift:** Entwickler vermeiden PostgreSQL-Features, weil Tests
   auf SQLite laufen

## Entscheidung

**SQLite ist für Tests VERBOTEN.** Alle Tests laufen auf PostgreSQL.

### Umsetzung

1. **Eigenes Test-Settings-File:** `config/settings/testing.py`
   - `ENGINE: django.db.backends.postgresql`
   - `TEST.NAME: test_<project>`
   - `PASSWORD_HASHERS: [MD5PasswordHasher]` (Geschwindigkeit)
   - `EMAIL_BACKEND: locmem`

2. **pyproject.toml:**
   ```toml
   [tool.pytest.ini_options]
   DJANGO_SETTINGS_MODULE = "config.settings.testing"
   ```

3. **base.py Default:** PostgreSQL statt SQLite-Fallback
   ```python
   DATABASES = {"default": dj_database_url.config(
       default="postgres://...",
   )}
   ```

4. **Keine vendor-Guards:** Code darf `connection.vendor` NICHT prüfen,
   um SQLite-Kompatibilität herzustellen. PostgreSQL-Features sind erlaubt
   und erwünscht.

5. **build.py Ausnahme:** `collectstatic` darf weiterhin SQLite in-memory
   nutzen (kein DB-Zugriff nötig).

### Lokale Voraussetzungen

```bash
# PostgreSQL installieren (falls nicht vorhanden)
sudo apt install postgresql

# Test-DB anlegen
createdb -p 5434 <project>_test

# Alternativ via DATABASE_URL
export DATABASE_URL="postgres://user@localhost:5434/db"
```

### CI/CD

GitHub Actions / CI muss PostgreSQL als Service bereitstellen:

```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_DB: test_db
      POSTGRES_PASSWORD: test
    ports: ["5432:5432"]
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

## Konsequenzen

### Positiv
- Tests testen das echte System (PostgreSQL = Production)
- PostgreSQL-Features (RLS, JSON, Session-Vars) testbar
- Keine Workarounds, kein versteckter Code
- Bugs werden beim Entwickler gefunden, nicht in Production

### Negativ
- Lokale PostgreSQL-Installation erforderlich
- Minimal langsamere Tests (~1s Overhead für DB-Erstellung)
- CI braucht PostgreSQL-Service

### Betroffene Repos
- **coach-hub** ✅ (umgesetzt)
- **risk-hub** — TODO (Issue #6)
- **billing-hub** — TODO (Issue #2)
- **travel-beat** — TODO (Issue #20)
- **weltenhub** — TODO (Issue #6)
- **cad-hub** — TODO (Issue #5)
- **trading-hub** — TODO (Issue #1)
- **pptx-hub** — TODO (Issue #9)
- **ausschreibungs-hub** — TODO (Issue #51)
- **wedding-hub** — TODO (Issue #5)
- **137-hub** — TODO (Issue #47)
- **dev-hub** — TODO (Issue #12)
- **writing-hub** — TODO (Issue #5)
- **illustration-hub** — TODO (Issue #1)
- **research-hub** — TODO (Issue #3)
- **learn-hub** — TODO (Issue #1)

## Referenzen

- Django Docs: [Testing with PostgreSQL](https://docs.djangoproject.com/en/5.0/topics/testing/overview/#the-test-database)
- ADR-137: Tenant Lifecycle (RLS mit `SET app.tenant_id`)
- ADR-100: iil-testkit (shared test factories)
