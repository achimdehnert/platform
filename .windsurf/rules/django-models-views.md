---
trigger: always_on
---

# Django Models & Views — Rules

> Glob-Activated: `*/models.py`, `*/views.py`
> ADR-009, ADR-043 — Service Layer + Database-First

## Service Layer (CRITICAL — NEVER bypass)

```python
# CORRECT — views.py
def trip_list(request):
    trips = trip_service.get_user_trips(request.user)
    return render(request, "trips/trip_list.html", {"trips": trips})

# BANNED in views.py — SL-001 CRITICAL:
# Trip.objects.filter(...)     <- ORM in view
# trip.save()                   <- ORM in view
# Trip.objects.create(...)      <- ORM in view
```

## Models — Database-First

```python
# CORRECT
class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)

# BANNED — DB-001 CRITICAL:
# UUIDField(primary_key=True)       <- integer PKs only
# JSONField() for structured data   <- use lookup tables
# EmailField() without unique=True  <- DB constraint required
```

## Naming

- Model: singular PascalCase (`Trip`, not `Trips`)
- Table: auto `{app}_{model}` snake_case (never override `db_table`)
- URL names: `trip_list`, `trip_detail`, `trip_create`, `trip_edit`, `trip_delete`
- Service functions: `get_`, `create_`, `update_`, `delete_` prefix

## Multi-Tenancy (if applicable — check project-facts.md)

```python
# CORRECT (multi-tenant repos: weltenhub, risk-hub)
class Document(models.Model):
    tenant_id = models.UUIDField(db_index=True)  # MANDATORY

# ALL queries must filter by tenant_id:
Document.objects.filter(tenant_id=request.tenant_id, ...)
```
