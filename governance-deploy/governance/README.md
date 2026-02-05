# DDL Governance App

**ADR-017: Domain Development Lifecycle**

Django app for managing Business Cases, Use Cases, ADRs, and the review workflow.

## Overview

This app implements the data layer for the Domain Development Lifecycle (DDL) system, providing:

- **Business Cases**: High-level feature/change requests
- **Use Cases**: Detailed user interaction specifications
- **ADRs**: Architecture Decision Records
- **Reviews**: Approval workflow
- **Conversations**: AI inception dialog tracking

## Models

### Lookup Tables (ADR-015 Compliant)

| Model | Table | Description |
|-------|-------|-------------|
| `LookupDomain` | `platform.lkp_domain` | Categories of choices |
| `LookupChoice` | `platform.lkp_choice` | Actual choice values |

### Domain Tables

| Model | Table | Description |
|-------|-------|-------------|
| `BusinessCase` | `platform.dom_business_case` | Business requirements |
| `UseCase` | `platform.dom_use_case` | User interaction specs |
| `ADR` | `platform.dom_adr` | Architecture decisions |
| `ADRUseCaseLink` | `platform.dom_adr_use_case` | ADR-UC relationships |
| `Conversation` | `platform.dom_conversation` | Inception dialogs |
| `ConversationTurn` | `platform.dom_conversation_turn` | Dialog turns |
| `Review` | `platform.dom_review` | Review records |
| `StatusHistory` | `platform.dom_status_history` | Audit trail |

## Key Design Principles

1. **No Hardcoded Enums**: All choices come from `lkp_choice` table
2. **Database-Driven**: Choices are configurable without code changes
3. **Audit Trail**: All status changes are tracked in `StatusHistory`
4. **Platform Schema**: All tables in `platform` schema

## Installation

1. Add to `INSTALLED_APPS`:
   ```python
   LOCAL_APPS = [
       ...
       "apps.governance",
       ...
   ]
   ```

2. Run migrations:
   ```bash
   python manage.py migrate governance
   ```

3. Load seed data:
   ```bash
   python manage.py loaddata seed_lookups
   ```

## Lookup Domains

| Domain Code | Purpose |
|-------------|---------|
| `bc_status` | Business Case status (draft, submitted, approved...) |
| `bc_category` | Business Case type (feature, enhancement, bugfix...) |
| `bc_priority` | Priority levels (critical, high, medium, low) |
| `uc_status` | Use Case status |
| `uc_priority` | Use Case priority |
| `uc_complexity` | Complexity estimation |
| `adr_status` | ADR status (draft, proposed, accepted...) |
| `adr_uc_relationship` | ADR-UC link type (implements, affects, references) |
| `conversation_status` | Inception dialog status |
| `conversation_role` | Message role (user, assistant, system) |
| `review_entity_type` | Type being reviewed |
| `review_decision` | Review outcome |

## Admin Interface

All models are registered in Django Admin with:
- Color-coded status badges
- Inline editing for related objects
- Search and filter capabilities
- Read-only audit fields

## Usage Example

```python
from apps.governance.models import (
    BusinessCase, UseCase, LookupDomain, LookupChoice
)

# Get status choice
draft_status = LookupChoice.objects.get(
    domain__code='bc_status',
    code='draft'
)
category = LookupChoice.objects.get(
    domain__code='bc_category',
    code='feature'
)

# Create Business Case
bc = BusinessCase.objects.create(
    code='BC-001',
    title='New Feature Request',
    category=category,
    status=draft_status,
    problem_statement='Users need X because Y'
)
```

## Files

```
apps/governance/
├── __init__.py
├── apps.py              # App configuration
├── models.py            # All Django models
├── admin.py             # Admin interface
├── fixtures/
│   ├── seed_lookups.json  # Django fixture
│   └── seed_lookups.sql   # Raw SQL (idempotent)
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py    # Initial migration
└── README.md
```

## Related ADRs

- **ADR-015**: Platform Governance System (lookup pattern)
- **ADR-017**: Domain Development Lifecycle (this system)

## Next Steps (P2+)

- P2: Inception Service (MCP Server)
- P3: Web UI (HTMX)
- P4: Export Service (Sphinx)
- P5: GitHub Actions Integration
