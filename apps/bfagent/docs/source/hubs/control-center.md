# Control Center

**Status:** ✅ Production  
**Domain:** `control_center`  
**URL:** `/control-center/`

---

## Übersicht

Das Control Center ist die zentrale Verwaltung für das BF Agent System. Hier werden Navigation, Features, AI-Konfiguration und Systemeinstellungen verwaltet.

## Features

- **Navigation:** Dynamische Sidebar-Navigation aus der Datenbank
- **Feature Planning:** Initiative und Requirement Management
- **Test Studio:** Bug-Tracking und Akzeptanzkriterien
- **AI Config:** LLM und Agent Konfiguration
- **MCP Config:** MCP-Server Verwaltung

## Models

### NavigationSection

Navigationsabschnitte (z.B. "Writing Hub", "CAD Hub").

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `name` | CharField | Anzeigename |
| `code` | CharField | Eindeutiger Code |
| `domain` | CharField | Zugehörige Domain |
| `icon` | CharField | Bootstrap Icon |
| `order` | IntegerField | Sortierreihenfolge |
| `is_active` | BooleanField | Aktiv/Inaktiv |

### NavigationItem

Navigationseinträge innerhalb einer Section.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `section` | ForeignKey | Zugehörige Section |
| `name` | CharField | Anzeigename |
| `code` | CharField | Eindeutiger Code |
| `url_name` | CharField | Django URL Name |
| `icon` | CharField | Bootstrap Icon |
| `order` | IntegerField | Sortierreihenfolge |

### Initiative

Feature-Initiativen für Planning.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `title` | CharField | Titel |
| `description` | TextField | Beschreibung |
| `status` | CharField | Status |
| `priority` | CharField | Priorität |
| `domain` | CharField | Zugehörige Domain |

### TestRequirement

Bug-Reports und Akzeptanzkriterien.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `initiative` | ForeignKey | Zugehörige Initiative |
| `title` | CharField | Titel |
| `description` | TextField | Beschreibung |
| `category` | CharField | Kategorie (bug_fix, feature, etc.) |
| `status` | CharField | Status |

## Views & URLs

| URL | View | Beschreibung |
|-----|------|--------------|
| `/control-center/` | `dashboard` | Dashboard |
| `/control-center/features/` | `feature_list` | Feature Planning |
| `/control-center/test-studio/` | `test_studio` | Test Studio |
| `/control-center/ai-config/` | `ai_config` | AI Konfiguration |

## Navigation Management

### Navigation erstellen

```python
from apps.control_center.models import NavigationSection, NavigationItem

# Section erstellen
section = NavigationSection.objects.create(
    name="Mein Hub",
    code="MY_HUB",
    domain="my_hub",
    icon="bi-star",
    order=100
)

# Items hinzufügen
NavigationItem.objects.create(
    section=section,
    name="Dashboard",
    code="my_hub_dashboard",
    url_name="my_hub:dashboard",
    icon="bi-house",
    order=10
)
```

### Management Command

```bash
python manage.py setup_writing_hub_navigation
```
