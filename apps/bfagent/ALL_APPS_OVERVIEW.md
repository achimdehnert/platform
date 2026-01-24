# 📱 BF Agent - Alle Apps Übersicht

**Stand:** 6. Dezember 2025

---

## 🟢 AKTIVE APPS (in INSTALLED_APPS)

### Core System (7)
| # | App | Path | Status | Beschreibung |
|---|-----|------|--------|--------------|
| 1 | **hub** | `apps/hub/` | ✅ ACTIVE | Central Hub - Domain Dashboard |
| 2 | **bfagent** | `apps/bfagent/` | ✅ ACTIVE | Hauptapp - Books, Agents, Handlers, Domains |
| 3 | **core** | `apps/core/` | 🔵 INSTALLED* | Core System Models (Domain, Handler, Phase) |
| 4 | **control_center** | `apps/control_center/` | ✅ ACTIVE | Control Center - Navigation, Workflows, V2 |
| 5 | **genagent** | `apps/genagent/` | ✅ ACTIVE | GenAgent Framework - General Agent System |
| 6 | **medtrans** | `apps/medtrans/` | ✅ ACTIVE | Medical Translation CRM - Proof of Concept |
| 7 | **presentation_studio** | `apps/presentation_studio/` | ✅ ACTIVE | PowerPoint Enhancement System |

**📦 Package:**
| # | Package | Status | Beschreibung |
|---|---------|--------|--------------|
| 8 | **bfagent_mcp** | ✅ ACTIVE | MCP Server Integration (Refactoring Tools) |

> *`apps.core` ist nicht explizit in INSTALLED_APPS, wird aber von anderen Apps verwendet

---

## 🟡 GEPLANTE APPS (Verzeichnis vorhanden, noch nicht aktiv)

### Hubs & Workflows (6)
| # | App | Path | Status | Zweck |
|---|-----|------|--------|-------|
| 9 | **writing_hub** | `apps/writing_hub/` | 🟡 PLANNED | Writing Hub - Bücher, Kapitel, Charaktere |
| 10 | **expert_hub** | `apps/expert_hub/` | 🟡 PLANNED | Expert Hub - Explosionsschutz, Fachexpertisen |
| 11 | **research** | `apps/research/` | 🟡 PLANNED | Research Hub |
| 12 | **support_hub** | `apps/support_hub/` | 🟡 PLANNED | Support Hub |
| 13 | **format_hub** | `apps/format_hub/` | 🟡 PLANNED | Format Hub |
| 14 | **workflow_system** | `apps/workflow_system/` | 🟡 PLANNED | Workflow Orchestration System |

### Specialized (6)
| # | App | Path | Status | Zweck |
|---|-----|------|--------|-------|
| 15 | **image_generation** | `apps/image_generation/` | 🟡 PLANNED | Image Generation Service |
| 16 | **cad_analysis** | `apps/cad_analysis/` | 🟡 PLANNED | CAD Analysis Domain |
| 17 | **checklist_system** | `apps/checklist_system/` | 🟡 PLANNED | Checklist System für Projektphasen |
| 18 | **compliance_core** | `apps/compliance_core/` | 🟡 PLANNED | Compliance Framework Core |
| 19 | **dsb** | `apps/dsb/` | 🟡 PLANNED | DSGVO Hub / Datenschutzbeauftragter |
| 20 | **api** | `apps/api/` | 🟡 PLANNED | REST API Framework |

---

## 📊 Statistik

### Nach Status
- **🟢 Aktiv:** 8 Apps (7 Django Apps + 1 Package)
- **🟡 Geplant:** 12 Apps (Verzeichnis vorhanden)
- **📋 Total:** 20 Apps

### Nach Kategorie
- **Core System:** 7 Apps (hub, bfagent, core, control_center, genagent, medtrans, presentation_studio)
- **Hubs & Workflows:** 6 Apps (writing_hub, expert_hub, research, support_hub, format_hub, workflow_system)
- **Specialized:** 6 Apps (image_generation, cad_analysis, checklist_system, compliance_core, dsb, api)
- **Package:** 1 Package (bfagent_mcp)

### Nach Implementation
- **Mit Models:** 7 Apps (bfagent, control_center, core, genagent, hub, medtrans, presentation_studio)
- **Mit Views:** 4 Apps (control_center, hub, medtrans, presentation_studio)
- **Leer/Placeholder:** 12 Apps

---

## 🎯 Naming Conventions Status

### ✅ Convention definiert (17)
Alle Naming Conventions sind in `core_naming_convention` integriert:

| App | Table Prefix | Class Prefix | Enforce |
|-----|--------------|--------------|---------|
| `api` | `api_` | `API` | - |
| `bfagent` | - | - | - |
| `bfagent_mcp` | `mcp_` | `MCP` | ✅ |
| `cad_analysis` | `cad_` | `CAD` | ✅ |
| `checklist_system` | `checklist_` | `Checklist` | ✅ |
| `compliance_core` | `compliance_` | `Compliance` | ✅ |
| `control_center` | - | - | - |
| `core` | `core_` | `Core` | ✅ |
| `dsb` | `dsb_` | `DSB` | ✅ |
| `expert_hub` | `expert_` | `Expert` | - |
| `genagent` | `genagent_` | `GenAgent` | ✅ |
| `hub` | `hub_` | `Hub` | - |
| `image_generation` | `image_` | `Image` | - |
| `medtrans` | `medtrans_` | `MedTrans` | ✅ |
| `presentation_studio` | `presentation_studio_` | `PresentationStudio` | ✅ |
| `workflow_system` | `workflow_` | `Workflow` | ✅ |
| `writing_hub` | `writing_` | `Writing` | - |

### ❌ Convention fehlt (3)
| App | Status | Note |
|-----|--------|------|
| `research` | 🟡 PLANNED | Noch keine Convention definiert |
| `support_hub` | 🟡 PLANNED | Noch keine Convention definiert |
| `format_hub` | 🟡 PLANNED | Noch keine Convention definiert |

---

## 📁 Verzeichnis-Details

### Größte Apps (nach Dateianzahl)
1. **bfagent** - 550 items (Models, Views, Handlers, Domains)
2. **genagent** - 75 items (GenAgent Framework)
3. **presentation_studio** - 54 items (PowerPoint Enhancement)
4. **control_center** - 53 items (Control Center V2)
5. **hub** - 44 items (Central Hub)

### Leere Apps (0 items)
- api, cad_analysis, checklist_system, compliance_core, dsb
- expert_hub, format_hub, research, support_hub
- workflow_system, writing_hub

> Diese Apps haben Verzeichnisse, aber noch keine Implementation

---

## 🚀 Aktivierung geplanter Apps

### Quick Start Template
```python
# 1. Convention in DB eintragen (falls noch nicht vorhanden)
# Siehe: INSERT_NAMING_CONVENTIONS.sql

# 2. App zu INSTALLED_APPS hinzufügen
# config/settings/base.py:
LOCAL_APPS = [
    # ... existing apps
    "apps.writing_hub",  # Writing Hub - Bücher, Kapitel, Charaktere
]

# 3. Models erstellen
# apps/writing_hub/models.py

# 4. Migrations
python manage.py makemigrations writing_hub
python manage.py migrate

# 5. Admin registrieren
# apps/writing_hub/admin.py

# 6. URLs einbinden
# config/urls.py
```

---

## 🎓 App-Kategorien erklärt

### Core System
Apps die für den Grundbetrieb notwendig sind:
- **hub** - Zentrale Navigation
- **bfagent** - Hauptfunktionalität
- **core** - Basis-Models
- **control_center** - Administration

### Hubs
Domain-spezifische Hubs für verschiedene Anwendungsfälle:
- **writing_hub** - Buchprojekte
- **expert_hub** - Fachexpertisen
- **research** - Forschung
- **support_hub** - Support
- **format_hub** - Format-Management

### Specialized
Spezialisierte Funktions-Apps:
- **genagent** - Agent Framework
- **medtrans** - Medizinische Übersetzungen
- **presentation_studio** - PowerPoint
- **image_generation** - Bildgenerierung
- **cad_analysis** - CAD Analyse
- **checklist_system** - Checklisten
- **compliance_core** - Compliance Framework
- **dsb** - Datenschutz
- **api** - REST API
- **workflow_system** - Workflows

---

## 🔗 Integration mit MCP Tools

Alle Apps sind über die MCP Refactoring Tools verfügbar:

```python
# Naming Convention abrufen
from bfagent_mcp.refactor_service import MCPRefactorService
import asyncio

service = MCPRefactorService()

# Für aktive Apps
result = asyncio.run(service.get_naming_convention('genagent'))
print(result)

# Für geplante Apps
result = asyncio.run(service.get_naming_convention('writing_hub'))
print(result)
```

---

**Letzte Aktualisierung:** 6. Dezember 2025  
**Version:** 1.0.0
