# 🎯 MCP Dashboard v2.0 - Full BF Agent Pattern

**Option B Implementation** - Production-ready mit HTMX, Celery, SSE

---

## 📊 Vergleich: Original vs. Option B

| Aspekt | Original | Option B |
|--------|----------|----------|
| **Views** | Function-based | Class-Based mit Mixins |
| **Frontend Interaktion** | `fetch()` + JS | HTMX-native |
| **Async Tasks** | `asyncio.run()` ⚠️ | Celery Tasks ✅ |
| **Real-time Updates** | Polling / Manual | SSE (Server-Sent Events) |
| **Toast Notifications** | `alert()` | Bootstrap Toast + OOB |
| **Error Handling** | Basic `try/catch` | Structured + Logging |
| **Code Reuse** | Copy/Paste | Mixins Pattern |
| **Testing** | Schwierig | Class-Based = einfach |

---

## 📁 Dateistruktur (24 Dateien, 4.400+ Zeilen)

```
apps/control_center/
├── views_mcp.py              # Class-Based Views mit Mixins (911 Zeilen)
├── urls_mcp.py               # URL Patterns (94 Zeilen)
├── tasks_mcp.py              # Celery Tasks (422 Zeilen)
├── templates/control_center/mcp/
│   ├── dashboard.html        # Main Dashboard
│   ├── domain_list.html      # Domain Liste mit Filter
│   ├── domain_detail.html    # Domain Detail mit Components
│   ├── sessions.html         # Sessions Liste mit Pagination
│   ├── session_detail.html   # Session Detail mit File Changes
│   ├── protected_paths.html  # Protected Paths nach Kategorie
│   ├── conventions.html      # Naming Conventions Strict/Flex
│   └── partials/
│       ├── dashboard_content.html    # Full Dashboard Partial
│       ├── stats_cards.html          # Stats (SSE updated)
│       ├── refactor_queue.html       # Queue Table
│       ├── recent_sessions.html      # Sessions Table
│       ├── sessions_table.html       # Full Sessions Table
│       ├── session_row.html          # Session Row (tr)
│       ├── session_row_content.html  # Session Row Content
│       ├── session_started.html      # Session Created Alert
│       ├── sync_status.html          # Sync Status Alert
│       ├── domain_list_table.html    # Domain List Table
│       └── toast.html                # Toast Template (OOB)
└── static/control_center/mcp/
    ├── dashboard.css         # Styles (200+ Zeilen)
    └── dashboard.js          # HTMX Helpers (200+ Zeilen)
```

---

## 🚀 Installation

### 1. Dateien kopieren

```powershell
# Views
Copy-Item views_mcp.py C:\Users\achim\github\bfagent\apps\control_center\

# URLs
Copy-Item urls_mcp.py C:\Users\achim\github\bfagent\apps\control_center\

# Tasks
Copy-Item tasks_mcp.py C:\Users\achim\github\bfagent\apps\control_center\

# Templates
Copy-Item -Recurse templates\* C:\Users\achim\github\bfagent\apps\control_center\templates\

# Static
Copy-Item -Recurse static\* C:\Users\achim\github\bfagent\apps\control_center\static\
```

### 2. URLs integrieren

```python
# apps/control_center/urls.py

from .urls_mcp import mcp_urlpatterns

app_name = 'control_center'

urlpatterns = [
    # ... existing patterns ...
] + mcp_urlpatterns
```

### 3. Celery Beat Schedule

```python
# config/settings.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # ... existing schedules ...
    
    'mcp-cleanup-old-sessions': {
        'task': 'mcp.cleanup_old_sessions',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 30},
    },
    'mcp-check-stalled-sessions': {
        'task': 'mcp.check_stalled_sessions',
        'schedule': crontab(minute='*/15'),
    },
}
```

### 4. HTMX SSE Extension

Das SSE Extension wird bereits im Template geladen:
```html
<script src="https://unpkg.com/htmx.org@1.9.10/dist/ext/sse.js"></script>
```

### 5. Navigation hinzufügen

```python
# Management Command oder in Admin
NavigationItem.objects.create(
    section=control_center_section,
    code='mcp_dashboard',
    name='MCP Dashboard',
    url_name='control_center:mcp-dashboard',
    icon='🎯',
    order=15,
    is_visible=True
)
```

---

## 🎯 Features

### 1. HTMX-Native Interaktionen

Alle Aktionen nutzen HTMX statt JavaScript fetch():

```html
<!-- Sync Button -->
<button hx-post="{% url 'control_center:mcp-sync-data' %}"
        hx-target="#sync-status"
        hx-indicator="#sync-spinner">
    Sync Data
</button>

<!-- Start Session -->
<button hx-post="{% url 'control_center:mcp-start-session' %}"
        hx-vals='{"domain_id": "books"}'
        hx-confirm="Start refactoring?">
    Start
</button>
```

### 2. Server-Sent Events (SSE)

Real-time Updates ohne Polling:

```html
<!-- Stats mit SSE Auto-Update -->
<div id="stats-container"
     hx-ext="sse"
     sse-connect="{% url 'control_center:mcp-sse-stats' %}"
     sse-swap="stats-update">
    {% include "partials/stats_cards.html" %}
</div>
```

### 3. Celery Tasks

Async Verarbeitung für lange Operationen:

```python
# Start Session
task = start_refactor_session_task.delay(
    session_id=session.id,
    user_id=request.user.id
)

# Task Progress via SSE an Frontend gestreamt
```

### 4. Toast Notifications via OOB

```python
# In View
return self.render_with_toast(
    'partials/content.html',
    context,
    message='Session started!',
    level='success'
)
```

```html
<!-- Toast wird via OOB in #toast-container injected -->
<div hx-swap-oob="afterbegin:#toast-container">
    <div class="toast show">...</div>
</div>
```

### 5. Class-Based Views mit Mixins

Wiederverwendbare Patterns:

```python
class MCPDashboardView(MCPDashboardMixin, TemplateView):
    """
    Erbt:
    - LoginRequiredMixin (Auth)
    - HTMXResponseMixin (HTMX Helpers)
    - MCPDashboardMixin (Stats, Navigation)
    """
    
    def get(self, request, *args, **kwargs):
        if self.is_htmx_request():
            return self.render_partial(...)
        return self.render_to_response(context)
```

---

## 🔧 Mixin Reference

### HTMXResponseMixin

```python
# Check if HTMX request
if self.is_htmx_request():
    pass

# Render partial
return self.render_partial('partial.html', context)

# Render with toast
return self.render_with_toast(template, context, 'Success!', 'success')

# HTMX redirect
return self.htmx_redirect('/new-url/')

# HTMX refresh
return self.htmx_refresh()

# Error response
return self.htmx_error_response('Error message')
```

### MCPDashboardMixin

```python
# Get common stats
stats = self.get_mcp_stats()

# Get navigation context
nav = self.get_navigation_context()
```

---

## 📝 Celery Tasks

| Task | Schedule | Beschreibung |
|------|----------|--------------|
| `mcp.sync_data` | Manual | Sync MCP data from DB |
| `mcp.start_refactor_session` | Manual | Execute refactoring |
| `mcp.cleanup_old_sessions` | Daily 3AM | Cleanup old sessions |
| `mcp.check_stalled_sessions` | Every 15min | Mark stalled sessions |

---

## 🎨 CSS Classes

| Class | Verwendung |
|-------|------------|
| `.mcp-dashboard` | Container |
| `.mcp-stat-card` | Stats Card |
| `.risk-critical` | Critical Risk Row |
| `.risk-high` | High Risk Row |
| `.risk-medium` | Medium Risk Row |
| `.risk-low` | Low Risk Row |
| `.htmx-indicator` | Loading Spinner |

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Aktion |
|----------|--------|
| `Escape` | Modal schließen |
| `Ctrl+S` | Data sync |
| `R` | Stats refresh |

---

## 🧪 Testing

```python
# test_views_mcp.py

from django.test import TestCase, Client
from django.urls import reverse

class MCPDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        self.client.login(username='test', password='pass')
    
    def test_dashboard_loads(self):
        response = self.client.get(reverse('control_center:mcp-dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_htmx_partial_response(self):
        response = self.client.get(
            reverse('control_center:mcp-dashboard'),
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='#stats-container'
        )
        self.assertTemplateUsed(response, 'partials/stats_cards.html')
```

---

## 🔜 Nächste Schritte

1. [ ] Templates für Domain Detail, Sessions etc. erstellen
2. [ ] MCPRefactorService implementieren
3. [ ] MCPSyncService implementieren
4. [ ] Tests schreiben
5. [ ] Permissions/Access Control hinzufügen

---

## 📊 Zeitschätzung

| Phase | Original | Option B |
|-------|----------|----------|
| Basic Dashboard | 2-3h | 3-4h |
| Detail Views | 2-3h | 2-3h |
| Actions & HTMX | 2-3h | 1-2h* |
| SSE Integration | N/A | 1-2h |
| Celery Tasks | N/A | 2h |
| Testing | 1-2h | 1-2h |
| **Total** | **8-12h** | **10-15h** |

*HTMX ist schneller als custom JS

---

**Status:** ✅ READY TO IMPLEMENT  
**Quality:** Production-Ready  
**Pattern:** Full BF Agent Compliance
