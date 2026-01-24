# 🔗 MetaPrompter Integration ins MCP Dashboard

**Ziel:** MCP Dashboard mit MetaPrompter Gateway erweitern für sichere Operationen

---

## 📋 Integration Steps

### 1. Dashboard Safe Actions Service

```python
# apps/control_center/services/safe_actions.py

from bfagent_mcp.metaprompter import UniversalGateway
from bfagent_mcp.metaprompter.gateway import Strategy, GatewayResult

class SafeActionsService:
    """
    Wrapper für alle Dashboard-Aktionen die Daten modifizieren.
    Nutzt MetaPrompter für Bestätigung.
    """
    
    def __init__(self):
        self.gateway = UniversalGateway(strategy=Strategy.CLARIFY)
    
    async def delete_navigation_items(self, items: List[NavigationItem]) -> GatewayResult:
        """
        Sichere Löschung mit Bestätigung.
        """
        request = f"Delete {len(items)} navigation items: {[i.name for i in items]}"
        result = await self.gateway.process(request)
        
        if result.needs_input:
            # Frontend zeigt Bestätigung
            return result
        
        if result.success:
            # Erst NACH Bestätigung löschen
            for item in items:
                item.delete()
        
        return result
```

### 2. Django View Integration

```python
# apps/control_center/views_mcp.py

from .services.safe_actions import SafeActionsService

class MCPDashboardView(MCPDashboardMixin, TemplateView):
    
    async def delete_items(self, request):
        """Mit Confirmation Dialog"""
        
        items = NavigationItem.objects.filter(id__in=request.POST.getlist('ids'))
        
        safe_actions = SafeActionsService()
        result = await safe_actions.delete_navigation_items(items)
        
        if result.needs_input:
            # HTMX Modal mit Bestätigung
            return render(request, 'control_center/mcp/confirm_modal.html', {
                'prompt': result.prompt,
                'items': items,
                'assumptions': result.assumptions,
            })
        
        if result.success:
            return self.render_with_toast(
                'partials/success.html',
                {},
                message=f'✅ {len(items)} items deleted',
                level='success'
            )
```

### 3. HTMX Frontend

```html
<!-- templates/control_center/mcp/confirm_modal.html -->

<div class="modal" id="confirm-modal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5>⚠️ Bestätigung erforderlich</h5>
            </div>
            <div class="modal-body">
                {{ prompt|safe }}
                
                {% if assumptions %}
                <div class="alert alert-info">
                    <strong>ℹ️ Erkannte Annahmen:</strong>
                    <ul>
                        {% for a in assumptions %}
                        <li>{{ a }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" 
                        hx-get="{% url 'control_center:mcp-dashboard' %}"
                        hx-target="body">
                    Abbrechen
                </button>
                <button class="btn btn-danger"
                        hx-post="{% url 'control_center:mcp-confirm-delete' %}"
                        hx-vals='{"confirmed": true}'
                        hx-target="body">
                    ✓ Ja, löschen
                </button>
            </div>
        </div>
    </div>
</div>
```

---

## 🛡️ Safety Rules

### Regel 1: Destructive Operations → CLARIFY Strategy

```python
DESTRUCTIVE_OPERATIONS = {
    'delete': Strategy.CLARIFY,  # IMMER nachfragen
    'truncate': Strategy.CLARIFY,
    'drop': Strategy.CLARIFY,
    'bulk_update': Strategy.HYBRID,  # Nachfragen wenn >10 items
    'sync': Strategy.AUTO,  # Safe - kein Löschen
}
```

### Regel 2: Confidence Thresholds

```python
class SafetyLevel:
    CRITICAL = 0.95  # Nur wenn 95% sicher
    HIGH = 0.80
    MEDIUM = 0.60
    LOW = 0.40

# Bei DELETE: Nur ausführen wenn CRITICAL
if operation == 'delete' and confidence < SafetyLevel.CRITICAL:
    return generate_clarification()
```

### Regel 3: Dry-Run Mode

```python
async def safe_execute(operation, items, dry_run=True):
    """
    Erste Ausführung = Dry Run
    Zeigt was WÜRDE passieren
    """
    if dry_run:
        return {
            'would_delete': len(items),
            'affected_sections': [i.section.name for i in items],
            'cascade_effects': check_cascade_deletes(items),
        }
    
    # Erst nach Bestätigung wirklich ausführen
    return execute_real(items)
```

---

## 📊 Benefits

| Feature | Vorher | Mit MetaPrompter |
|---------|--------|------------------|
| **Delete ohne Fragen** | ❌ Möglich | ✅ Unmöglich |
| **Destructive Ops** | ❌ Direkt | ✅ Mit Confirmation |
| **User Feedback** | ❌ Nach Error | ✅ Vor Ausführung |
| **Undo Option** | ❌ Komplex | ✅ Dry-Run first |
| **Audit Trail** | ❌ Manual | ✅ Automatisch |

---

## 🎯 Quick Win: Sofort nutzbar

### Minimal Integration:

```python
# config/settings.py
METAPROMPTER_ENABLED = True
METAPROMPTER_STRATEGY = 'hybrid'  # auto | clarify | hybrid

# Für Production: CLARIFY
# Für Development: HYBRID
```

```python
# apps/control_center/mixins.py

class SafeOperationMixin:
    """
    Mixin für alle Views die Daten modifizieren.
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Check if operation is destructive
        if request.method in ['DELETE', 'POST'] and self.is_destructive():
            # Route through MetaPrompter
            if not request.POST.get('confirmed'):
                return self.require_confirmation()
        
        return super().dispatch(request, *args, **kwargs)
```

---

## 🔮 Future Enhancements

### 1. Audit Trail
```python
from bfagent_mcp.metaprompter import AuditLogger

audit = AuditLogger()
audit.log_operation(
    operation='delete_navigation',
    user=request.user,
    items=[i.id for i in items],
    confidence=result.confidence,
    confirmed=True,
)
```

### 2. Rollback System
```python
from bfagent_mcp.services.rollback import RollbackManager

rollback = RollbackManager()
rollback.create_checkpoint('before_delete')
# ... operation ...
if error:
    rollback.restore('before_delete')
```

### 3. AI Validation
```python
from bfagent_mcp.metaprompter.validator import AIValidator

validator = AIValidator()
risk_score = validator.assess_risk(operation='delete', count=16)

if risk_score > 0.7:
    require_admin_confirmation()
```

---

## ✅ Implementation Checklist

- [ ] MetaPrompter in Django integrieren
- [ ] SafeActionsService erstellen
- [ ] HTMX Confirmation Modals
- [ ] Dry-Run Mode implementieren
- [ ] Audit Trail aktivieren
- [ ] Rollback System (optional)
- [ ] Tests schreiben
- [ ] Documentation

---

**Ergebnis:** Keine unbeabsichtigten Löschungen mehr! 🎉
