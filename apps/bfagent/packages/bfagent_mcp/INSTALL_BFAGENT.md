# BF Agent MCP - Installation in BF Agent

## 🎯 Übersicht

Diese Anleitung beschreibt die Integration des MCP Packages in dein BF Agent Projekt.

## 📁 Dateistruktur nach Installation

```
bfagent/
├── apps/
│   ├── core/           # Existiert bereits
│   ├── books/          # Existiert bereits
│   └── ...
├── packages/
│   └── bfagent_mcp/    # MCP Package
│       └── bfagent_mcp/
│           ├── __init__.py
│           ├── models.py           # Basis-Models (Domain, Handler, etc.)
│           ├── models_naming.py    # NEU: Naming Conventions
│           ├── models_mcp.py       # NEU: MCP-spezifische Models
│           ├── admin.py            # Basis-Admin
│           ├── admin_mcp.py        # NEU: MCP Admin
│           ├── data_loader.py      # Basis Data Loader
│           ├── data_loader_mcp.py  # NEU: MCP Data Loader
│           └── management/
│               └── commands/
│                   └── sync_mcp_data.py  # NEU
```

## 🚀 Installation

### Schritt 1: Package in BF Agent kopieren

```powershell
# Im BF Agent Projektverzeichnis
cd C:\path\to\bfagent

# MCP Package kopieren (falls noch nicht vorhanden)
# Option A: Als Submodule
git submodule add https://github.com/your-repo/bfagent-mcp packages/bfagent_mcp

# Option B: Direkt kopieren
cp -r path/to/bfagent-mcp-repo packages/bfagent_mcp
```

### Schritt 2: INSTALLED_APPS erweitern

```python
# config/settings/base.py

INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    # ...
    
    # BF Agent Apps
    'apps.core',
    'apps.books',
    # ...
    
    # MCP Package (NEU!)
    'bfagent_mcp',
]
```

### Schritt 3: Migrations erstellen und anwenden

```powershell
# Migrations für MCP erstellen
python manage.py makemigrations bfagent_mcp

# Alle Migrations anwenden
python manage.py migrate
```

### Schritt 4: Initial Data laden

```powershell
# Option A: Mit Management Command
python manage.py sync_mcp_data

# Option B: Manuell in Shell
python manage.py shell
>>> from bfagent_mcp.data_loader_mcp import sync_all_mcp_data
>>> import asyncio
>>> result = asyncio.run(sync_all_mcp_data())
>>> print(result)
```

## 📊 Was wird erstellt?

### Neue Tabellen (12 Stück)

```
NAMING SYSTEM
├── core_naming_convention     # Naming Rules pro App
└── core_model_registry        # Registrierte Models

MCP TABLES
├── mcp_component_type         # handler, service, model, etc.
├── mcp_risk_level            # critical, high, medium, low, minimal
├── mcp_protection_level      # absolute, warn, review
├── mcp_path_category         # mcp, config, security, etc.
├── mcp_domain_config         # Refactor Config pro Domain
├── mcp_domain_component      # M:N Domain <-> Component
├── mcp_protected_path        # Geschützte Pfade
├── mcp_refactor_session      # Session-Tracking
├── mcp_file_change           # Datei-Änderungen
└── mcp_config_history        # Config-Änderungen
```

### Initial Data

| Tabelle | Einträge |
|---------|----------|
| Naming Conventions | 8 (core, mcp, books, etc.) |
| Component Types | 10 (handler, service, model, etc.) |
| Risk Levels | 5 (critical → minimal) |
| Protection Levels | 3 (absolute, warn, review) |
| Path Categories | 6 (mcp, config, security, etc.) |
| Protected Paths | 15 (packages/bfagent_mcp/**, etc.) |
| Domain Configs | 8 (core, books, medtrans, etc.) |

## ✅ Verifizierung

```powershell
# Admin aufrufen
python manage.py runserver

# Browser: http://localhost:8000/admin/
# Neue Sections sollten sichtbar sein:
# - BFAGENT_MCP
#   - MCP: Component Types
#   - MCP: Risk Levels
#   - MCP: Domain Configs
#   - MCP: Protected Paths
#   - ...
```

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'bfagent_mcp'"

```python
# Prüfe sys.path in settings.py
import sys
sys.path.insert(0, str(BASE_DIR / 'packages'))
```

### "Table already exists"

```powershell
# Fake migration wenn Tabellen manuell erstellt wurden
python manage.py migrate bfagent_mcp --fake
```

### "Domain matching query does not exist"

```powershell
# Erst Basis-Domains laden
python manage.py sync_mcp_data --only naming
python manage.py sync_mcp_data --only components
# Dann Domain-Configs
python manage.py sync_mcp_data --only domains
```

## 🎯 Nächste Schritte

1. **MCP Server starten** (für Windsurf)
   ```powershell
   python -m bfagent_mcp.server
   ```

2. **Windsurf konfigurieren**
   - Settings → MCP Server URL → `http://localhost:8765`

3. **Testen**
   - In Windsurf: "Was sind die Conventions für das books Domain?"
