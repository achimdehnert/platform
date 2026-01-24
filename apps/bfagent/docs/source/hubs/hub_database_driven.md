# Hub Database-Driven Navigation

## Overview

The Hub Management system is now fully database-driven, linking Hubs to NavigationSections for dynamic sidebar management.

## Architecture

```
Hub (core_hubs)
  └── OneToOne → NavigationSection (navigation_sections)
                    └── OneToMany → NavigationItem (navigation_items)
```

## Key Features

- **Dynamic Activation**: Setting `Hub.is_active = False` automatically hides the Hub's navigation section
- **Automatic Sync**: Hub activation status syncs to NavigationSection on save
- **Database-Driven**: All hub configuration stored in `core_hubs` table

## Models

### Hub Model (`apps/core/models/hub.py`)

| Field | Type | Description |
|-------|------|-------------|
| hub_id | CharField | Unique ID (e.g., 'writing_hub') |
| name | CharField | Display name |
| navigation_section | OneToOneField | Link to NavigationSection |
| is_active | BooleanField | Hub activation status |
| status | CharField | production/beta/development/deprecated |
| category | CharField | content/engineering/system/research |

### Navigation Filtering

The sidebar only shows NavigationSections where:
- `hub__isnull=True` (sections not linked to any Hub), OR
- `hub__is_active=True` (sections linked to an active Hub)

## Management Commands

### Initialize Hubs

```bash
python manage.py init_hubs
```

Creates/updates Hub records and links them to existing NavigationSections.

### Migrations

```bash
python manage.py migrate core
```

Migration `0003_hub_model.py` creates the `core_hubs` table.

## Admin Interface

Access Hub management at: `/admin/core/hub/`

Features:
- List display with status, category, activation
- Bulk activate/deactivate actions
- Filter by status, category, is_active

## Files Modified

| File | Purpose |
|------|---------|
| `apps/core/models/hub.py` | Hub model with NavigationSection FK |
| `apps/core/migrations/0003_hub_model.py` | Database migration |
| `apps/core/admin/hub_admin.py` | Admin interface |
| `apps/core/management/commands/init_hubs.py` | Seed command |
| `apps/control_center/context_processors_unified.py` | Hub-aware filtering |
| `apps/control_center/templatetags/navigation_tags.py` | Hub-aware navigation |

## Quick Start After Fresh Setup

```bash
# Apply migration
python manage.py migrate core

# Initialize hub data
python manage.py init_hubs

# Start server
python manage.py runserver
```

## Troubleshooting

### "relation core_hubs does not exist"

Run: `python manage.py migrate core`

### Navigation sections not showing

1. Check Hub is active: `Hub.objects.filter(is_active=True)`
2. Check NavigationSection is linked: `Hub.objects.filter(navigation_section__isnull=False)`
3. Run `init_hubs` to link sections
