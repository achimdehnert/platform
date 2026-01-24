# Hub-Übersicht

BF Agent ist in spezialisierte **Hubs** organisiert - jeder Hub ist eine eigenständige Anwendung für einen bestimmten Anwendungsbereich.

## Verfügbare Hubs

```{list-table}
:header-rows: 1
:widths: 20 15 65

* - Hub
  - Status
  - Beschreibung
* - [Writing Hub](writing-hub.md)
  - ✅ Production
  - AI-gestützte Bucherstellung mit Charakteren, Welten, Kapiteln
* - [CAD Hub](cad-hub.md)
  - ✅ Production
  - IFC/DWG Analyse, GAEB Export, Raumbuch
* - [Control Center](control-center.md)
  - ✅ Production
  - Systemverwaltung, Navigation, Feature Planning
* - [Research Hub](research-hub.md)
  - ✅ Production
  - Deep Research mit Quellenanalyse
* - [MCP Hub](mcp-hub.md)
  - ✅ Production
  - MCP-Server Verwaltung und Monitoring
* - [Expert Hub](expert-hub.md)
  - 🟡 Beta
  - Explosionsschutz-Dokumentation
```

## Hub-Architektur

Jeder Hub folgt einer einheitlichen Struktur:

```
apps/{hub_name}/
├── models.py          # Django Models
├── views.py           # Views & API Endpoints
├── handlers/          # Business Logic Handler
├── templates/         # HTML Templates
├── urls.py            # URL Routing
└── admin.py           # Admin Interface
```

## Navigation

Die Hub-Navigation wird dynamisch aus der Datenbank geladen:

```python
from apps.control_center.models import NavigationSection, NavigationItem

# Navigation für einen Hub abrufen
section = NavigationSection.objects.get(domain='writing_hub')
items = section.items.filter(is_active=True).order_by('order')
```

