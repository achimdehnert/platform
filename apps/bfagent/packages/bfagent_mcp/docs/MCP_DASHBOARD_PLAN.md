# 🎯 MCP Dashboard - Implementierungsplan

**Status:** 📋 PLANNING  
**Ziel:** MCP Refactoring Tools als Dashboard im Control Center

---

## 🎨 UI Konzept (Approved)

### Dashboard Layout
```
┌─────────────────────────────────────────────────────────────────────────┐
│  BF Agent MCP Dashboard                                    [Sync Data] │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           │
│  │ 📊 8 Domains    │ │ 🔒 15 Protected │ │ 📝 12 Sessions  │           │
│  │ 7 Ready         │ │ Paths           │ │ Last: 2h ago    │           │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘           │
│                                                                         │
│  ┌─ REFACTOR QUEUE ─────────────────────────────────────────────────┐  │
│  │ Order │ Domain    │ Risk   │ Components │ Status      │ Actions  │  │
│  │   1   │ core      │ 🟠 HIGH│ H S R M T  │ ✓ Ready     │ [Start]  │  │
│  │  10   │ books     │ 🟡 MED │ H S M T V  │ ✓ Ready     │ [Start]  │  │
│  └───────┴───────────┴────────┴────────────┴─────────────┴──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Dateistruktur

### Django App: `apps/control_center/`
```
apps/control_center/
├── views_mcp.py                    # MCP Dashboard Views (NEW)
├── urls.py                         # +MCP URLs
├── templates/control_center/
│   └── mcp/
│       ├── dashboard.html          # Main Dashboard
│       ├── domain_detail.html      # Domain Detail
│       ├── protected_paths.html    # Protected Paths
│       ├── sessions.html           # Sessions List
│       ├── session_detail.html     # Session Detail
│       └── conventions.html        # Naming Conventions
└── static/control_center/
    └── mcp/
        ├── dashboard.js            # Dashboard Logic
        └── dashboard.css           # MCP Styles
```

---

## 🛠️ Views Implementation

### 1. Dashboard View (`views_mcp.py`)

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from bfagent_mcp.models_mcp import (
    MCPDomainConfig, MCPProtectedPath, MCPRefactorSession,
    MCPRiskLevel, MCPComponentType
)

@login_required
def mcp_dashboard(request):
    """
    MCP Dashboard - Hauptübersicht
    """
    # Stats Cards
    stats = {
        'total_domains': MCPDomainConfig.objects.filter(is_active=True).count(),
        'ready_domains': MCPDomainConfig.objects.filter(
            is_active=True, 
            allows_refactoring=True
        ).count(),
        'protected_paths': MCPProtectedPath.objects.filter(is_active=True).count(),
        'total_sessions': MCPRefactorSession.objects.count(),
        'active_sessions': MCPRefactorSession.objects.filter(
            status='in_progress'
        ).count(),
        'last_session': MCPRefactorSession.objects.order_by('-started_at').first(),
    }
    
    # Refactor Queue (Domains sorted by risk + order)
    refactor_queue = MCPDomainConfig.objects.filter(
        is_active=True,
        allows_refactoring=True
    ).select_related(
        'domain', 'risk_level'
    ).prefetch_related(
        'components__component_type'
    ).annotate(
        component_count=Count('components')
    ).order_by(
        '-risk_level__severity_score',  # High risk first
        'domain__name'
    )
    
    # Recent Sessions (Last 10)
    recent_sessions = MCPRefactorSession.objects.select_related(
        'domain_config__domain'
    ).order_by('-started_at')[:10]
    
    context = {
        'stats': stats,
        'refactor_queue': refactor_queue,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'control_center/mcp/dashboard.html', context)


@login_required
def mcp_domain_detail(request, domain_id):
    """
    Domain Detail - Komponenten, Dependencies, Config
    """
    from bfagent_mcp.models import Domain
    
    domain = get_object_or_404(Domain, id=domain_id)
    
    try:
        config = MCPDomainConfig.objects.select_related(
            'risk_level'
        ).prefetch_related(
            'components__component_type',
            'depends_on'
        ).get(domain=domain)
    except MCPDomainConfig.DoesNotExist:
        config = None
    
    # Protected Paths für diese Domain
    if config:
        base_path = config.base_path
        protected_paths = MCPProtectedPath.objects.filter(
            is_active=True,
            path_pattern__startswith=base_path
        ).select_related('protection_level', 'category')
    else:
        protected_paths = []
    
    # Recent Sessions
    sessions = MCPRefactorSession.objects.filter(
        domain_config=config
    ).order_by('-started_at')[:5] if config else []
    
    context = {
        'domain': domain,
        'config': config,
        'protected_paths': protected_paths,
        'recent_sessions': sessions,
    }
    
    return render(request, 'control_center/mcp/domain_detail.html', context)


@login_required
def mcp_protected_paths(request):
    """
    Protected Paths - Übersicht und Management
    """
    paths = MCPProtectedPath.objects.filter(
        is_active=True
    ).select_related(
        'protection_level', 'category'
    ).order_by('category__order', 'path_pattern')
    
    # Group by category
    categories = {}
    for path in paths:
        cat_name = path.category.name
        if cat_name not in categories:
            categories[cat_name] = {
                'category': path.category,
                'paths': []
            }
        categories[cat_name]['paths'].append(path)
    
    context = {
        'categories': categories,
        'total_paths': paths.count(),
    }
    
    return render(request, 'control_center/mcp/protected_paths.html', context)


@login_required
def mcp_sessions(request):
    """
    Sessions - History und Status
    """
    # Filter options
    status_filter = request.GET.get('status', 'all')
    domain_filter = request.GET.get('domain', 'all')
    
    sessions = MCPRefactorSession.objects.select_related(
        'domain_config__domain'
    )
    
    if status_filter != 'all':
        sessions = sessions.filter(status=status_filter)
    
    if domain_filter != 'all':
        sessions = sessions.filter(domain_config__domain__domain_id=domain_filter)
    
    sessions = sessions.order_by('-started_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats
    stats = {
        'total': MCPRefactorSession.objects.count(),
        'completed': MCPRefactorSession.objects.filter(status='completed').count(),
        'in_progress': MCPRefactorSession.objects.filter(status='in_progress').count(),
        'failed': MCPRefactorSession.objects.filter(status='failed').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'domain_filter': domain_filter,
    }
    
    return render(request, 'control_center/mcp/sessions.html', context)


@login_required
def mcp_session_detail(request, session_id):
    """
    Session Detail - File Changes, Stats, Timeline
    """
    session = get_object_or_404(
        MCPRefactorSession.objects.select_related(
            'domain_config__domain', 
            'domain_config__risk_level'
        ).prefetch_related('file_changes'),
        id=session_id
    )
    
    # File Changes
    file_changes = session.file_changes.all().order_by('file_path')
    
    # Stats
    stats = {
        'files_changed': session.files_changed,
        'lines_added': session.lines_added,
        'lines_removed': session.lines_removed,
        'duration': (session.ended_at - session.started_at) if session.ended_at else None,
    }
    
    context = {
        'session': session,
        'file_changes': file_changes,
        'stats': stats,
    }
    
    return render(request, 'control_center/mcp/session_detail.html', context)


@login_required
def mcp_conventions(request):
    """
    Naming Conventions - Übersicht und Management
    """
    from bfagent_mcp.models_naming import TableNamingConvention
    
    conventions = TableNamingConvention.objects.filter(
        is_active=True
    ).order_by('app_label')
    
    # Group by enforce
    strict = conventions.filter(enforce_convention=True)
    flexible = conventions.filter(enforce_convention=False)
    
    context = {
        'strict_conventions': strict,
        'flexible_conventions': flexible,
        'total': conventions.count(),
    }
    
    return render(request, 'control_center/mcp/conventions.html', context)
```

---

## 🔗 URLs Configuration

### `apps/control_center/urls.py`

```python
from django.urls import path
from . import views_mcp

app_name = 'control_center'

urlpatterns = [
    # ... existing URLs ...
    
    # =====================================================================
    # MCP DASHBOARD
    # =====================================================================
    path('mcp/', views_mcp.mcp_dashboard, name='mcp-dashboard'),
    path('mcp/domain/<int:domain_id>/', views_mcp.mcp_domain_detail, name='mcp-domain-detail'),
    path('mcp/protected/', views_mcp.mcp_protected_paths, name='mcp-protected-paths'),
    path('mcp/sessions/', views_mcp.mcp_sessions, name='mcp-sessions'),
    path('mcp/session/<int:session_id>/', views_mcp.mcp_session_detail, name='mcp-session-detail'),
    path('mcp/conventions/', views_mcp.mcp_conventions, name='mcp-conventions'),
]
```

---

## 🎨 Template Structure

### Dashboard Template (`dashboard.html`)

```django
{% extends "control_center/base.html" %}
{% load static %}

{% block title %}MCP Dashboard - BF Agent{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'control_center/mcp/dashboard.css' %}">
{% endblock %}

{% block content %}
<div class="container-fluid mcp-dashboard">
    
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>🎯 MCP Dashboard</h1>
        <button class="btn btn-primary" id="sync-data">
            <i class="bi bi-arrow-clockwise"></i> Sync Data
        </button>
    </div>
    
    <!-- Stats Cards -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card mcp-stat-card">
                <div class="card-body">
                    <h6 class="card-subtitle mb-2 text-muted">Domains</h6>
                    <h2>📊 {{ stats.total_domains }}</h2>
                    <p class="mb-0">{{ stats.ready_domains }} Ready for Refactoring</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card mcp-stat-card">
                <div class="card-body">
                    <h6 class="card-subtitle mb-2 text-muted">Protected Paths</h6>
                    <h2>🔒 {{ stats.protected_paths }}</h2>
                    <p class="mb-0">Critical Files Protected</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card mcp-stat-card">
                <div class="card-body">
                    <h6 class="card-subtitle mb-2 text-muted">Sessions</h6>
                    <h2>📝 {{ stats.total_sessions }}</h2>
                    <p class="mb-0">
                        {% if stats.last_session %}
                            Last: {{ stats.last_session.started_at|timesince }} ago
                        {% else %}
                            No sessions yet
                        {% endif %}
                    </p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Refactor Queue -->
    <div class="card mb-4">
        <div class="card-header">
            <h5>🔧 Refactor Queue</h5>
        </div>
        <div class="card-body p-0">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Order</th>
                        <th>Domain</th>
                        <th>Risk</th>
                        <th>Components</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for config in refactor_queue %}
                    <tr>
                        <td>{{ forloop.counter0|stringformat:"02d" }}</td>
                        <td>
                            <a href="{% url 'control_center:mcp-domain-detail' config.domain.id %}">
                                {{ config.domain.display_name }}
                            </a>
                        </td>
                        <td>
                            {% if config.risk_level.severity_score >= 75 %}
                                <span class="badge bg-danger">🔴 {{ config.risk_level.name|upper }}</span>
                            {% elif config.risk_level.severity_score >= 50 %}
                                <span class="badge bg-warning">🟡 {{ config.risk_level.name|upper }}</span>
                            {% else %}
                                <span class="badge bg-success">🟢 {{ config.risk_level.name|upper }}</span>
                            {% endif %}
                        </td>
                        <td>
                            {% for component in config.components.all|slice:":5" %}
                                <span class="badge bg-secondary" title="{{ component.component_type.display_name }}">
                                    {{ component.component_type.icon }}
                                </span>
                            {% endfor %}
                            {% if config.component_count > 5 %}
                                <span class="badge bg-light text-dark">+{{ config.component_count|add:"-5" }}</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if config.allows_refactoring %}
                                <span class="badge bg-success">✓ Ready</span>
                            {% else %}
                                <span class="badge bg-danger">🔒 Protected</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if config.allows_refactoring %}
                                <button class="btn btn-sm btn-primary start-refactor" 
                                        data-domain="{{ config.domain.domain_id }}">
                                    Start
                                </button>
                            {% else %}
                                <a href="{% url 'control_center:mcp-domain-detail' config.domain.id %}" 
                                   class="btn btn-sm btn-secondary">
                                    View
                                </a>
                            {% endif %}
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="6" class="text-center text-muted">
                            No domains configured for refactoring yet.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Recent Sessions -->
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5>📋 Recent Sessions</h5>
            <a href="{% url 'control_center:mcp-sessions' %}" class="btn btn-sm btn-outline-primary">
                View All
            </a>
        </div>
        <div class="card-body p-0">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Domain</th>
                        <th>Started</th>
                        <th>Status</th>
                        <th>Files</th>
                        <th>+/-</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {% for session in recent_sessions %}
                    <tr>
                        <td>{{ session.domain_config.domain.display_name }}</td>
                        <td>{{ session.started_at|timesince }} ago</td>
                        <td>
                            {% if session.status == 'completed' %}
                                <span class="badge bg-success">✓ Done</span>
                            {% elif session.status == 'in_progress' %}
                                <span class="badge bg-primary">⏳ In Progress</span>
                            {% else %}
                                <span class="badge bg-danger">❌ Failed</span>
                            {% endif %}
                        </td>
                        <td>{{ session.files_changed }}</td>
                        <td>
                            <span class="text-success">+{{ session.lines_added }}</span> / 
                            <span class="text-danger">-{{ session.lines_removed }}</span>
                        </td>
                        <td>
                            <a href="{% url 'control_center:mcp-session-detail' session.id %}" 
                               class="btn btn-sm btn-outline-secondary">
                                View
                            </a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="6" class="text-center text-muted">
                            No sessions yet.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'control_center/mcp/dashboard.js' %}"></script>
{% endblock %}
```

---

## 🎯 JavaScript Logic

### `dashboard.js`

```javascript
// MCP Dashboard Logic
document.addEventListener('DOMContentLoaded', function() {
    
    // Sync Data Button
    const syncBtn = document.getElementById('sync-data');
    if (syncBtn) {
        syncBtn.addEventListener('click', async function() {
            const originalText = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Syncing...';
            
            try {
                const response = await fetch('/control-center/mcp/api/sync/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                    }
                });
                
                if (response.ok) {
                    showToast('✅ Data synced successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast('❌ Sync failed!', 'error');
                }
            } catch (error) {
                showToast('❌ Network error!', 'error');
            } finally {
                this.disabled = false;
                this.innerHTML = originalText;
            }
        });
    }
    
    // Start Refactor Buttons
    const startButtons = document.querySelectorAll('.start-refactor');
    startButtons.forEach(btn => {
        btn.addEventListener('click', async function() {
            const domainId = this.dataset.domain;
            
            if (!confirm(`Start refactoring session for ${domainId}?`)) {
                return;
            }
            
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Starting...';
            
            try {
                const response = await fetch('/control-center/mcp/api/start-session/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        domain_id: domainId,
                        components: ['handler', 'service', 'model']
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    showToast(`✅ Session ${data.session_id} started!`, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    const error = await response.json();
                    showToast(`❌ Error: ${error.message}`, 'error');
                    this.disabled = false;
                    this.innerHTML = 'Start';
                }
            } catch (error) {
                showToast('❌ Network error!', 'error');
                this.disabled = false;
                this.innerHTML = 'Start';
            }
        });
    });
    
});

// Helper Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'info') {
    // Bootstrap Toast or simple alert
    alert(message);
}
```

---

## 🔌 API Endpoints (Optional)

### AJAX Actions für Live-Updates

```python
# views_mcp_api.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import asyncio

@login_required
@require_POST
def api_sync_data(request):
    """Sync MCP data from database"""
    # Trigger data refresh
    # ...
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def api_start_session(request):
    """Start refactoring session"""
    import json
    data = json.loads(request.body)
    
    domain_id = data.get('domain_id')
    components = data.get('components', [])
    
    # Call MCP Service
    from bfagent_mcp.refactor_service import MCPRefactorService
    service = MCPRefactorService()
    
    result = asyncio.run(service.start_refactor_session(
        domain_id=domain_id,
        components=components,
        triggered_by='web_dashboard'
    ))
    
    return JsonResponse({'status': 'success', 'session_id': result})
```

---

## 📊 Integration ins Control Center

### 1. Navigation hinzufügen
```python
# Management Command oder Admin
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

### 2. Permissions
```python
# Optional: Permission-basiert
from django.contrib.auth.models import Permission

# Create permission
permission = Permission.objects.create(
    codename='view_mcp_dashboard',
    name='Can view MCP Dashboard',
    content_type=ContentType.objects.get_for_model(MCPDomainConfig)
)

# In View
@permission_required('bfagent_mcp.view_mcp_dashboard')
def mcp_dashboard(request):
    # ...
```

---

## 🎯 Implementation Steps

### Phase 1: Basic Dashboard (2-3 hours)
1. ✅ Create `views_mcp.py` with dashboard view
2. ✅ Create basic template `dashboard.html`
3. ✅ Add URLs to `urls.py`
4. ✅ Add navigation item
5. ✅ Test with existing data

### Phase 2: Detail Views (2-3 hours)
1. ✅ Domain Detail view
2. ✅ Protected Paths view
3. ✅ Sessions List view
4. ✅ Session Detail view
5. ✅ Conventions view

### Phase 3: Actions & AJAX (2-3 hours)
1. ✅ Sync Data endpoint
2. ✅ Start Session endpoint
3. ✅ JavaScript logic
4. ✅ Real-time updates

### Phase 4: Polish & Testing (1-2 hours)
1. ✅ Responsive design
2. ✅ Loading states
3. ✅ Error handling
4. ✅ User feedback (toasts)

**Total Estimated Time:** 8-12 hours

---

## ✅ Benefits

### For Users
- 👁️ **Visual Overview** statt Shell-Commands
- 🎯 **One-Click Actions** für Sessions
- 📊 **Live Stats** und Monitoring
- 🔍 **Easy Navigation** durch Domains/Sessions

### For Developers
- 🏗️ **Centralized Management** aller MCP Features
- 📝 **Audit Trail** durch Session History
- 🔒 **Protected Paths** einfach verwalten
- ⚙️ **Domain Configuration** per UI

### For System
- 📈 **Better Adoption** durch bessere UX
- 🎨 **Consistent Design** mit Control Center
- 🔐 **Access Control** durch Django Auth
- 🚀 **Scalable** für neue Features

---

## 🚀 Next Steps

1. **Review & Approve** diesen Plan
2. **Create Feature Branch** `feature/mcp-dashboard`
3. **Phase 1 Implementation** - Basic Dashboard
4. **Testing** mit echten Daten
5. **Iteration** basierend auf Feedback

---

**Status:** 📋 READY TO IMPLEMENT  
**Priority:** 🔥 HIGH (Bessere UX für MCP Tools)  
**Estimated:** 8-12 hours development time
