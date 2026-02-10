# ADR-022 Repo Checker

Das **repo_checker** Tool (`platform/tools/repo_checker.py`) prueft alle
5 Repositories automatisch auf ADR-022 Compliance.

## Uebersicht

- **Typ**: CLI Tool + MCP Tool (`check_repos` in orchestrator_mcp)
- **Abhaengigkeiten**: Keine (Python stdlib only)
- **Pruefpunkte**: 88 (Stand 2026-02-10)
- **Severity-Level**: OK, Warning, Error, Info, Skip

## Usage

### CLI

```bash
# Alle 5 Repos pruefen
python3 tools/repo_checker.py

# Einzelnes Repo
python3 tools/repo_checker.py /path/to/repo

# JSON-Output fuer Automation
python3 tools/repo_checker.py --json

# Ohne Farben (CI/CD)
python3 tools/repo_checker.py --no-color
```

### MCP Tool

Verfuegbar als `check_repos` im **orchestrator_mcp**:

```json
{
  "tool": "check_repos",
  "arguments": {
    "repo": "all",
    "format": "text"
  }
}
```

Parameter:

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|-------------|
| `repo` | string | `all` | Repo-Name oder `all` |
| `format` | string | `text` | `text` oder `json` |

## Pruefkategorien

### compose — Docker Compose

- `docker-compose.prod.yml` existiert
- `IMAGE_TAG` standardisiert (kein App-Prefix)
- Healthcheck: `127.0.0.1` (nicht `localhost`)
- Healthcheck: `/livez/` Endpoint
- `env_file: .env.prod` vorhanden
- Healthcheck: `python urllib` (nicht `curl`)

### dockerfile — Dockerfile

- OCI Labels (`org.opencontainers.image.*`)
- `HEALTHCHECK` Direktive mit `127.0.0.1` und `/livez/`
- Multi-line HEALTHCHECK Continuation wird korrekt geparst
- Non-root `USER` Direktive

### cicd — CI/CD Workflows

- Platform Reusable Workflows (`achimdehnert/platform@v1`)
- `health_url` nutzt `/livez/` Endpoint

### health — Health Endpoints

- `healthz.py` oder Health-Views existieren
- `HEALTH_PATHS` frozenset definiert
- `@csrf_exempt` Dekorator
- `@require_GET` Dekorator

### deploy — Deployment Scripts

- `deployment/scripts/deploy-remote.sh` existiert
- Script nutzt standardisiertes `IMAGE_TAG`

### config — Django Configuration

- `manage.py` nutzt `config.settings`
- `config/wsgi.py` existiert (auch unter `src/config/`)
- `config/urls.py` enthaelt `/livez/` Route

## Architektur

```text
repo_checker.py
├── REPO_CONFIGS          # Per-Repo Konfiguration
├── CheckResult           # Dataclass (category, check, severity, message, file)
├── Severity              # Enum (OK, WARNING, ERROR, INFO, SKIP)
├── grep_lines()          # Regex-Suche in Dateiinhalt
├── _get_continuation_block()  # Multi-line Dockerfile Parsing
├── check_compose()       # Docker Compose Checks
├── check_dockerfile()    # Dockerfile Checks
├── check_cicd()          # CI/CD Workflow Checks
├── check_health()        # Health Endpoint Checks
├── check_deploy_script() # Deploy Script Checks
├── check_django_config() # Django Config Checks
├── run_all_checks()      # Orchestrierung
├── run_check()           # MCP Entry Point
└── main()                # CLI Entry Point
```

## Konfiguration

Jedes Repo hat eine Config in `REPO_CONFIGS`:

```python
REPO_CONFIGS = {
    "bfagent": {
        "compose": "docker-compose.prod.yml",
        "dockerfile": "Dockerfile",
        "health_module": "apps/core/views.py",
        "exempt_non_root": True,  # Python 3.11
    },
    # ...
}
```

## Erweiterung

Neue Checks hinzufuegen:

1. Neue `check_*()` Funktion in `repo_checker.py`
2. `CheckResult` mit passender `Severity` zurueckgeben
3. In `run_all_checks()` einhaengen
4. Testen: `python3 tools/repo_checker.py --no-color`
