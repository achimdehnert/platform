# RLS-Rollout Template für Django-Hub-Repos

> **Referenz:** ADR-137 Phase 4.4 · Getestet mit risk-hub (65 Tabellen, Prod+Staging)

## Voraussetzungen

| Komponente | Requirement |
|------------|-------------|
| **django-tenancy** | `>= 0.2.0` in `packages/` oder via pip |
| **PostgreSQL** | >= 16 (RLS seit PG 9.5, empfohlen 16+) |
| **TenantManager** | Alle Models mit `tenant_id` nutzen `TenantManager` |
| **tenant_id Feld** | `UUIDField` oder `BigIntegerField` auf allen tenant-aware Models |

---

## Schritt-für-Schritt Rollout

### 1. Dual-DATABASE_URL konfigurieren

```env
# .env.prod
DATABASE_URL=postgresql://<app_user>:<app_pw>@<db_host>:5432/<db_name>
DATABASE_URL_MIGRATE=postgresql://<owner_user>:<owner_pw>@<db_host>:5432/<db_name>
```

| Variable | Rolle | RLS |
|----------|-------|-----|
| `DATABASE_URL` | App-User (gunicorn, worker) | **enforced** |
| `DATABASE_URL_MIGRATE` | Table-Owner (migrate, seed) | **exempt** |

### 2. Entrypoint anpassen

```sh
#!/bin/sh
MIGRATE_URL="${DATABASE_URL_MIGRATE:-$DATABASE_URL}"

# Migrations mit Owner-Rolle (RLS-exempt)
DATABASE_URL="$MIGRATE_URL" python manage.py migrate --noinput

# Web-Server mit App-User (RLS enforced)
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 3. RLS-Rollen erstellen

```bash
# Dry-Run
python manage.py setup_rls_roles --dry-run

# Ausführen
python manage.py setup_rls_roles

# Oder direkt per SQL (wenn Management Command Bug hat):
docker exec <db_container> psql -U <owner> -d <db> -c "
DO \$\$ BEGIN
IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '<db>_app') THEN
  CREATE ROLE <db>_app LOGIN PASSWORD '<strong_password>';
END IF;
END \$\$;
GRANT CONNECT ON DATABASE <db> TO <db>_app;
GRANT USAGE ON SCHEMA public TO <db>_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO <db>_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO <db>_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO <db>_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO <db>_app;
"
```

### 4. RLS-Policies aktivieren

```bash
# Dry-Run — zeigt alle SQL-Statements
python manage.py enable_rls --dry-run

# Ausführen
python manage.py enable_rls

# Verifizieren
docker exec <db_container> psql -U <owner> -d <db> -c "
SELECT COUNT(*) as policies FROM pg_policies;
SELECT COUNT(*) as rls_tables FROM pg_tables WHERE schemaname='public' AND rowsecurity=true;
"
```

### 5. Passwort via Secret Management

```python
# config/secrets.py — read_secret() Priority:
# 1. /run/secrets/<key>  (CI/CD SOPS)
# 2. os.environ[KEY]     (docker env_file)
# 3. .env file           (local dev)

# Starkes Passwort generieren:
python3 -c "import secrets; print(secrets.token_hex(24))"
```

### 6. Verifizierung

```bash
# 1. Health-Check
curl -sf https://<domain>/healthz/

# 2. RLS-Isolation testen
docker exec <db_container> psql -U <app_user> -d <db> -c "
-- Ohne tenant_id: alle Rows sichtbar (Admin-Modus)
SELECT COUNT(*) FROM <table>;

-- Mit tenant_id: nur eigene Rows
SET app.tenant_id = '<uuid>';
SELECT COUNT(*) FROM <table>;

-- Reset
RESET app.tenant_id;
"

# 3. Policy-Count
docker exec <db_container> psql -U <owner> -d <db> -c "
SELECT COUNT(*) FROM pg_policies;
"
```

---

## Bekannte Fallstricke

| Problem | Ursache | Fix |
|---------|---------|-----|
| `enable_rls` meldet Erfolg aber 0 Policies | Alter Code: `;`-Split filtert `--`-Kommentare | django-tenancy >= 0.2.1 nutzen |
| `setup_rls_roles` SQL-Fehler `END IF` | Alter Code: `DO $$` Block durch `;`-Split zerstört | django-tenancy >= 0.2.1 nutzen |
| App-User kann nicht verbinden | `pg_hba.conf` blockiert Netzwerk-Auth | Password-Auth für Docker-Netzwerk prüfen |
| Migrations scheitern mit App-User | App-User hat kein DDL (CREATE/ALTER TABLE) | `DATABASE_URL_MIGRATE` nutzen |
| Worker healthcheck unhealthy | Prüft HTTP aber Worker ist kein Webserver | `pgrep -f 'outbox.publisher'` nutzen |

---

## RLS-Policy Struktur

Jede Tabelle bekommt eine Policy der Form:

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_<table> ON <table>
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::<cast>
        OR current_setting('app.tenant_id', true) IS NULL
        OR current_setting('app.tenant_id', true) = ''
    );
```

**Cast-Types:**
- `UUIDField` → `::uuid`
- `BigIntegerField` / `IntegerField` → `::bigint`

**Verhalten:**
- `app.tenant_id` nicht gesetzt → alle Rows sichtbar (Admin/Shell)
- `app.tenant_id` gesetzt → nur Rows mit passendem `tenant_id`
- Table-Owner (Migrations-User) → RLS-exempt (kein `FORCE ROW LEVEL SECURITY`)

---

## Rollout-Checkliste

- [ ] `django-tenancy >= 0.2.1` installiert
- [ ] Alle Models mit `tenant_id` nutzen `TenantManager`
- [ ] `.env.prod` + `.env.staging` mit Dual-DATABASE_URL
- [ ] Entrypoint mit `DATABASE_URL_MIGRATE` für migrate/seed
- [ ] `setup_rls_roles` ausgeführt (starkes Passwort)
- [ ] `enable_rls` ausgeführt
- [ ] `pg_policies` Count == Anzahl tenant-aware Tabellen
- [ ] Health-Check nach Restart OK
- [ ] RLS-Isolation manuell getestet (SET app.tenant_id)
- [ ] ADR-137 Evidence aktualisiert
