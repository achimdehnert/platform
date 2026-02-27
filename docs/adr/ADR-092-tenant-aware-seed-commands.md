# ADR-092: Tenant-Aware Seed Commands

## Status

Proposed

## Context

Bei der Implementierung von ADR-091 (Platform Operations Hub) wurde ein kritischer Bug entdeckt:

**Problem:** Management Commands wie `seed_servers` legten Daten mit einem hardcoded `tenant_id` (`00000000-0000-0000-0000-000000000000`) an, während die Middleware den korrekten `tenant_id` aus der Datenbank ermittelt (`b52e944a-1e3f-4581-aa09-3930de6db91a` für DevHub).

**Symptom:** Seeded Daten waren im Frontend nicht sichtbar, obwohl sie in der Datenbank existierten.

**Root Cause:**
1. `TenantAwareModel` verwendet `tenant_id` als UUID-Feld
2. Die `SubdomainTenantMiddleware` setzt `request.tenant_id` basierend auf Subdomain/Organization
3. Seed Commands haben keinen Request-Kontext und verwendeten einen falschen Default

## Decision

### 1. Tenant-ID Auto-Detection in Seed Commands

Alle Seed Commands für `TenantAwareModel`-Daten MÜSSEN den `tenant_id` dynamisch ermitteln:

```python
def get_default_tenant_id():
    """Get tenant_id from existing records or first tenant."""
    from django.apps import apps
    from django.conf import settings
    
    # Option 1: Von existierenden Records
    existing = MyModel.objects.first()
    if existing:
        return existing.tenant_id
    
    # Option 2: Von TENANT_MODEL
    tenant_model_path = getattr(settings, "TENANT_MODEL", None)
    if tenant_model_path:
        app_label, model_name = tenant_model_path.split(".")
        TenantModel = apps.get_model(app_label, model_name)
        tenant = TenantModel.objects.first()
        if tenant and hasattr(tenant, "uuid"):
            return tenant.uuid
    
    # Fallback: Nil UUID (sollte nie verwendet werden)
    return uuid.UUID("00000000-0000-0000-0000-000000000000")
```

### 2. Explizites --tenant-id Argument

Alle Seed Commands MÜSSEN ein `--tenant-id` Argument unterstützen:

```python
def add_arguments(self, parser):
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="UUID of tenant (auto-detected if omitted)",
    )
```

### 3. TenantMixin ohne Hardcoded Fallback

Das `TenantMixin` in Views darf KEINEN hardcoded Fallback verwenden:

```python
class TenantMixin:
    def get_tenant_id(self):
        # Middleware setzt den korrekten Wert
        return getattr(self.request, "tenant_id", None)
```

### 4. Fixtures mit Platzhalter-Tenant

JSON-Fixtures sollten einen erkennbaren Platzhalter verwenden:

```json
{
  "tenant_id": "REPLACE_WITH_ACTUAL_TENANT_ID"
}
```

Ein `loaddata`-Wrapper ersetzt den Platzhalter vor dem Import.

## Consequences

### Positive

- **Korrekte Tenant-Isolation:** Seeded Daten sind im richtigen Tenant sichtbar
- **Deployment-Sicherheit:** Keine manuellen UUID-Anpassungen nötig
- **Multi-Tenant-Ready:** Funktioniert in allen Umgebungen

### Negative

- **Komplexität:** Seed Commands werden etwas komplexer
- **Abhängigkeit:** Commands müssen die Tenant-Struktur kennen

### Neutral

- Bestehende Fixtures müssen angepasst werden
- Dokumentation für Seed-Pattern erforderlich

## Implementation

### Phase 1: dev-hub (Done)

- [x] `seed_servers` Command mit Auto-Detection
- [x] `TenantMixin` ohne Fallback
- [x] Server-Daten auf korrekten Tenant aktualisiert

### Phase 2: Platform-weite Anwendung

1. **platform-context Package erweitern:**
   - `TenantAwareSeedCommand` Base-Klasse
   - `get_current_tenant_id()` Utility-Funktion

2. **Alle Repos prüfen:**
   - bfagent
   - cad-hub
   - travel-beat
   - Weitere Apps mit TenantAwareModel

3. **CI/CD Integration:**
   - Post-Migration Seed-Validierung
   - Tenant-ID Konsistenz-Check

## References

- ADR-050: Multi-Tenancy Architecture
- ADR-091: Platform Operations Hub Consolidation
- dev-hub Commit: `45d20f7` (fix: Auto-detect tenant_id)
