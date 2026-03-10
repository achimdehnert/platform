#!/usr/bin/env bash
# grafana/scripts/setup_grafana_ro_user.sh
#
# Erstellt den Read-Only PostgreSQL-User für Grafana (ADR-115, K-01 Fix)
#
# Voraussetzungen:
#   - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD gesetzt
#   - GRAFANA_DB_PASSWORD gesetzt
#
# Aufruf:
#   ./setup_grafana_ro_user.sh
#   oder via Docker:
#   docker exec -e GRAFANA_DB_PASSWORD=xxx postgres_container bash setup_grafana_ro_user.sh

set -euo pipefail

: "${POSTGRES_HOST:?POSTGRES_HOST nicht gesetzt}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:?POSTGRES_DB nicht gesetzt}"
: "${POSTGRES_USER:?POSTGRES_USER nicht gesetzt}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD nicht gesetzt}"
: "${GRAFANA_DB_PASSWORD:?GRAFANA_DB_PASSWORD nicht gesetzt}"

RO_USER="grafana_ro"

echo "[INFO] Erstelle Read-Only User '${RO_USER}' für Grafana..."

PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h "${POSTGRES_HOST}" \
  -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  --no-password \
  <<SQL

-- Idempotent: User nur erstellen wenn noch nicht vorhanden
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '${RO_USER}') THEN
    CREATE USER ${RO_USER} WITH PASSWORD '${GRAFANA_DB_PASSWORD}';
    RAISE NOTICE 'User ${RO_USER} erstellt.';
  ELSE
    -- Passwort aktualisieren (falls geändert)
    ALTER USER ${RO_USER} WITH PASSWORD '${GRAFANA_DB_PASSWORD}';
    RAISE NOTICE 'User ${RO_USER} bereits vorhanden — Passwort aktualisiert.';
  END IF;
END
\$\$;

-- Verbindungsrecht
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${RO_USER};

-- Schema-Zugriff
GRANT USAGE ON SCHEMA public TO ${RO_USER};

-- SELECT auf relevante Tabellen
GRANT SELECT ON llm_calls TO ${RO_USER};
GRANT SELECT ON llm_model_pricing TO ${RO_USER};

-- Zukünftige Tabellen automatisch mit SELECT berechtigen
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO ${RO_USER};

-- Sequences: kein Zugriff für RO-User nötig (kein NEXTVAL)
-- REVOKE ALL ON ALL SEQUENCES ist Default

SELECT 'Setup abgeschlossen für User: ${RO_USER}' AS status;
SQL

echo "[OK] Grafana Read-Only User '${RO_USER}' erfolgreich konfiguriert."
echo "[INFO] Verbindungstest:"
PGPASSWORD="${GRAFANA_DB_PASSWORD}" psql \
  -h "${POSTGRES_HOST}" \
  -p "${POSTGRES_PORT}" \
  -U "${RO_USER}" \
  -d "${POSTGRES_DB}" \
  -c "SELECT COUNT(*) AS llm_calls_total FROM llm_calls;" \
  --no-password

echo "[OK] Read-Only-Zugriff verifiziert."
