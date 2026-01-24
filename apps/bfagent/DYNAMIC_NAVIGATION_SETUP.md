# Dynamische Navigation - 100% Datenbankgesteuert

## ✅ Wiederhergestellte Dateien

### 1. Context Processors
- `apps/control_center/context_processors_unified.py` - Lädt Navigation aus DB
- `apps/control_center/context_processors.py` - Dual-Mode Support

### 2. Template Tags  
- `apps/control_center/templatetags/navigation_tags.py` - Rendering-Helfer

### 3. Navigation Helpers
- `apps/control_center/navigation_helpers.py` - Dual-Schema-Support

### 4. Templates
- `apps/control_center/templates/control_center/partials/unified_sidebar.html` - Sidebar-Template

### 5. Models
- `apps/control_center/models_navigation.py` - NavigationSection, NavigationItem
- `apps/control_center/models_workflow_domains.py` - WorkflowDomain, ProjectType

### 6. Views
- `apps/hub/views_domain_dashboards.py` - Domain-Dashboards mit Sections & Items

## ⚙️ Konfiguration

In `config/settings.py`:

```python
# TEMPLATES context_processors
"apps.control_center.context_processors_unified.unified_navigation",

# Navigation Settings
USE_UNIFIED_NAVIGATION = True  # Enable 100% DB-driven navigation

NAVIGATION_FEATURES = {
    'USE_NEW_SCHEMA': True,  # Use NavigationSection/NavigationItem
    'DEBUG_NAVIGATION': False,  # Debug output
}
```

## 📋 Befehle zum Ausführen

```powershell
# 1. Migrationen anwenden
python manage.py migrate

# 2. Slugs für Sections populieren  
python manage.py populate_navigation_domains --skip-domain

# 3. Data Management Section erstellen
python manage.py create_data_management_navigation

# 4. Server starten
python manage.py runserver
```

## 🎯 Wie es funktioniert

1. **Context Processor** lädt alle Domains aus `domain_arts` Tabelle
2. Für jede Domain lädt er Sections aus `navigation_sections` WHERE `domain_id=domain.id`
3. Für jede Section lädt er Items aus `navigation_items` WHERE `section_id=section.id`
4. Template (`unified_sidebar.html`) rendert die komplette Hierarchie

## 🔧 Template Verwendung

In deinem Base-Template:

```django
{% load navigation_tags %}

<!-- Sidebar mit dynamischer Navigation -->
{% include 'control_center/partials/unified_sidebar.html' %}
```

## 📊 Datenbank-Struktur

```
domain_arts (Domains)
  ├─ navigation_sections (Sections für Domain)
      ├─ navigation_items (Items für Section)
```

### Beispiel:

```
CONTROL_CENTER (Domain)
  ├─ Data Management (Section)
      ├─ Domain Arts (Item)
      ├─ Domain Types (Item)
      ├─ Agents (Item)
      └─ LLM Models (Item)
  └─ Workflow Engine (Section)
      └─ ...
```

## ✨ Features

- ✅ 100% datenbankgesteuert - KEINE hardcodierten Links
- ✅ Multi-Domain Support
- ✅ Collapsible Sections
- ✅ User Preferences (collapsed states)
- ✅ Permission-basierte Sichtbarkeit
- ✅ Badge Support (NEW, BETA, etc.)
- ✅ Icons pro Section & Item
- ✅ Dynamische URL-Generierung

## 🔄 Nächste Schritte

1. Domains in `domain_arts` Tabelle erstellen
2. Sections zu Domains zuweisen
3. Items zu Sections hinzufügen
4. Optional: Custom Management Commands für Seed-Daten
