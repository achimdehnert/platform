# ADR-159: Shared Secrets Management — Single Source of Truth für API Keys

- **Status:** accepted
- **Date:** 2026-04-08
- **Deciders:** Achim Dehnert, Cascade
- **Scope:** platform-wide (all repos on 88.198.191.108)

## Context and Problem Statement

Am 2026-04-08 schlug die Outline-Generierung in writing-hub mit `AuthenticationError: Incorrect API key` fehl. Die Analyse ergab:

1. **Zwei verschiedene OpenAI Keys** auf dem Produktionsserver — einer davon abgelaufen
2. **Kein Single Source of Truth**: Jedes Repo hat eine eigene `.env.prod` mit potenziell unterschiedlichen API Keys
3. **Inkonsistente Quoting**: risk-hub nutzt `"sk-proj-..."`, writing-hub nutzt `sk-proj-...` (ohne Quotes)
4. **Inkonsistente Compose-Patterns**: Manche Repos nutzen `env_file`, andere `environment: ${VAR}`
5. **Manuelle Key-Rotation**: Bei N Repos müssen N Dateien aktualisiert werden

### Audit-Ergebnis (2026-04-08)

| Repo | Key-Variante | Quoting | Compose-Pattern |
|------|-------------|---------|-----------------|
| writing-hub | ENTj...WHQA (expired) | unquoted | env_file ✅ |
| travel-beat | ENTj...WHQA (expired) | unquoted | env_file + ${VAR} ⚠️ |
| weltenhub | ENTj...WHQA (expired) | unquoted | env_file ✅ |
| risk-hub | KCuA...E0A (valid) | quoted | env_file ✅ |
| pptx-hub | KCuA...E0A (valid) | quoted | env_file + ${VAR} ⚠️ |
| trading-hub | — | — | **27× ${VAR}** ❌ |
| coach-hub | — | — | env_file + ${VAR} ⚠️ |
| cad-hub | (leer) | — | env_file ✅ |

## Decision

### Shared Secrets File

```
/opt/shared-secrets/
  api-keys.env          # chmod 600, root-only
```

Enthält **ausschließlich** shared LLM/AI API Keys:

```env
# Shared LLM API Keys — Single Source of Truth
# Rotiert: nur HIER ändern, alle Repos erben automatisch
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GROQ_API_KEY=gsk_xxx
```

### Compose-Pattern (verbindlich)

```yaml
services:
  <app>_web:
    env_file:
      - /opt/shared-secrets/api-keys.env   # shared API keys (1. Priorität)
      - .env.prod                          # repo-spezifisch (überschreibt bei Bedarf)
    # KEIN environment: ${VAR} für Secrets!
```

**Reihenfolge wichtig**: Docker Compose lädt env_files sequenziell — bei Duplikaten gewinnt der **letzte** Eintrag. Shared-Secrets zuerst, repo-spezifische `.env.prod` kann bei Bedarf überschreiben.

### .env.prod Format (verbindlich)

```env
# IMMER ohne Anführungszeichen (Docker env_file Standard)
DJANGO_SECRET_KEY=abc123
DB_NAME=writing_hub

# NIE:
# DJANGO_SECRET_KEY="abc123"
# environment: SECRET_KEY=${SECRET_KEY}
```

### Settings-Pattern (verbindlich, bestätigt ADR-045)

```python
from decouple import config

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-key")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
```

**Verboten:**
- `os.environ.get("SECRET_KEY")` direkt in Settings
- `os.environ["OPENAI_API_KEY"]` ohne Default
- `_read_secret("/path/to/file")` Fallback-Pattern

### Key-Kategorisierung

| Kategorie | Beispiele | Verwaltung |
|-----------|-----------|------------|
| **Shared (LLM)** | OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY | `/opt/shared-secrets/api-keys.env` |
| **Repo-spezifisch** | DJANGO_SECRET_KEY, DB_PASSWORD, BINANCE_API_KEY | `.env.prod` im Repo |
| **Infra-intern** | REDIS_URL, CELERY_BROKER_URL | `environment:` im Compose (statische Werte) |

## Consequences

### Positiv

- **1 Stelle rotieren** statt N Dateien bei Key-Ablauf
- Konsistenter Zustand über alle Repos garantiert
- Klare Trennung: shared vs. repo-spezifisch
- Sofort-Fix bei Key-Problemen: nur `/opt/shared-secrets/api-keys.env` ändern + Container neustarten

### Negativ

- Absolute Pfade in docker-compose.prod.yml (`/opt/shared-secrets/`) — nur auf Production-Server gültig
- Lokale Entwicklung braucht eigene `.env` (kein shared-secrets Pfad)

### Migration

Alle 9 Repos auf 88.198.191.108 wurden am 2026-04-08 umgestellt:
- Shared-secrets env_file in alle docker-compose.prod.yml eingefügt
- OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY aus allen .env.prod kommentiert
- Backups: `.env.prod.bak.20260408`, `docker-compose.prod.yml.bak.20260408`

## Related

- **ADR-045**: `decouple.config()` statt `os.environ`
- **ADR-021**: docker-compose.prod.yml Konventionen
- **ADR-022**: Platform-weite Infrastruktur-Standards
