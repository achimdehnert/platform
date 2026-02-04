# ADR-019: Weltenhub UI, Templates, Views & APIs für weltenforger.com

| Metadata | Value |
|----------|-------|
| **Status** | ✅ Accepted (Reviewed 2026-02-04) |
| **Date** | 2026-02-04 |
| **Author** | Achim Dehnert |
| **Scope** | weltenhub |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-018 (Weltenhub Architecture), ADR-015 (Platform Governance) |

---

## 1. Executive Summary

Dieses ADR definiert die **vollständige UI-Architektur** für Weltenhub/Weltenforger.com:

- **Public Pages** - Landing, Impressum, Datenschutz (IIL GmbH)
- **Dashboard** - Multi-Tenant Übersicht für Welten, Characters, Stories
- **CRUD Views** - Erstellen/Bearbeiten aller Entitäten
- **API Endpoints** - RESTful API für Frontend-Integration
- **Templates** - Bootstrap 5 + HTMX basiertes Template-System

**Ziel:** Production-ready UI für https://weltenforger.com mit vollständiger DSGVO-Compliance.

---

## 2. Context

### 2.1 Ausgangssituation

| Aspekt | Status vor ADR | Ziel nach ADR |
|--------|----------------|---------------|
| Landingpage | Keine | Moderne Landing mit CTA |
| Legal Pages | Keine | Impressum + Datenschutz (IIL GmbH) |
| Dashboard | Keine | Tenant-basierte Übersicht |
| Entity CRUD | Nur API | Full HTMX UI |
| Mobile | Keine | Responsive Bootstrap 5 |

### 2.2 Anforderungen

| ID | Anforderung | Priorität | Status |
|----|-------------|-----------|--------|
| R1 | Landingpage mit Hero, Features, CTA | CRITICAL | ✅ Done |
| R2 | Impressum (§5 TMG) mit IIL GmbH Daten | CRITICAL | ✅ Done |
| R3 | Datenschutzerklärung (DSGVO) | CRITICAL | ✅ Done |
| R4 | Footer mit Links zu Legal Pages | HIGH | ✅ Done |
| R5 | Dashboard für eingeloggte User | HIGH | Pending |
| R6 | World CRUD Views | HIGH | Pending |
| R7 | Character CRUD Views | HIGH | Pending |
| R8 | Scene CRUD Views | MEDIUM | Pending |
| R9 | Story CRUD Views | MEDIUM | Pending |

---

## 3. Decision

### 3.0 Architektur-Prinzipien (Produktionsreife)

| Prinzip | Umsetzung | Status |
|---------|-----------|--------|
| **Tenant-Isolation** | `TenantRequiredMixin` in `apps/core/mixins.py` | ✅ Implementiert |
| **Database-First** | Alle Choices aus `lkp_*` Tables | ✅ Implementiert |
| **FK-Strategie** | UUID für Tenant-Models, Integer für Lookups | ✅ Definiert |
| **Separation of Concerns** | Models → Services → Views → Templates | 🔜 Phase 2+ |
| **HTMX-First** | Alle interaktiven Views via HTMX | 🔜 Phase 2 |
| **Type Hints** | Alle Python-Dateien mit Type Hints | ⚠️ Nachzuholen |

### 3.1 App-Struktur

```
weltenhub/
├── apps/
│   ├── public/           # ✅ Implementiert
│   │   ├── __init__.py
│   │   ├── views.py      # LandingView, ImpressumView, DatenschutzView
│   │   └── urls.py       # /, /impressum/, /datenschutz/
│   │
│   ├── dashboard/        # 🔜 Nächster Schritt
│   │   ├── views.py      # TenantDashboardView, WorldListView
│   │   └── urls.py       # /dashboard/
│   │
│   └── [entity_apps]/    # Bestehende Apps (worlds, characters, etc.)
│       └── views.py      # Erweitern um Template-Views
│
├── templates/
│   ├── base.html         # ✅ Bootstrap 5 + Icons
│   ├── public/           # ✅ Landing, Impressum, Datenschutz
│   ├── dashboard/        # 🔜 Tenant Dashboard
│   └── [entity]/         # 🔜 CRUD Templates
│
└── static/
    ├── css/
    └── js/
```

### 3.2 Template-Architektur

```
base.html
├── Navigation (Navbar mit Login/Logout)
├── {% block content %}
└── Footer (Impressum, Datenschutz, Copyright IIL GmbH)

public/landing.html
├── Hero Section (Gradient, CTA)
├── Features Section (3 Cards)
└── CTA Section

public/impressum.html
└── IIL GmbH Angaben (§5 TMG)

public/datenschutz.html
└── DSGVO-konforme Datenschutzerklärung
```

### 3.2.1 Layer-Architektur (Separation of Concerns)

```
apps/[entity]/
├── models.py          # Data Layer - Django Models
├── services.py        # Business Logic - MANDATORY für Phase 2+
├── views.py           # HTTP Layer (dünn, delegiert an Services)
├── serializers.py     # API Transformation (DRF)
├── permissions.py     # Access Control
├── admin.py           # Admin UI
└── urls.py            # Routing
```

**Service-Pattern (obligatorisch):**

```python
# apps/worlds/services.py
from typing import Optional, List
from django.db.models import QuerySet
from apps.tenants.models import Tenant
from .models import World


class WorldService:
    """Business logic for World operations."""
    
    @staticmethod
    def create_world(
        tenant: Tenant,
        name: str,
        genre_id: Optional[int] = None,
        **kwargs
    ) -> World:
        """Create a new world with validation."""
        return World.objects.create(
            tenant=tenant,
            name=name,
            genre_id=genre_id,
            **kwargs
        )
    
    @staticmethod
    def get_worlds_for_tenant(tenant: Tenant) -> QuerySet[World]:
        """Get all worlds for a tenant."""
        return World.objects.filter(tenant=tenant)
```

### 3.3 Design System

| Element | Wert |
|---------|------|
| **Primary Color** | `#6366f1` (Indigo) |
| **Secondary Color** | `#8b5cf6` (Purple) |
| **Accent Color** | `#ec4899` (Pink) |
| **Dark Color** | `#1e1b4b` (Footer) |
| **Framework** | Bootstrap 5.3.2 |
| **Icons** | Bootstrap Icons 1.11.1 |
| **Interactivity** | HTMX 2.0 |

### 3.4 URL-Struktur

| URL | View | Template | Status |
|-----|------|----------|--------|
| `/` | `LandingView` | `public/landing.html` | ✅ |
| `/impressum/` | `ImpressumView` | `public/impressum.html` | ✅ |
| `/datenschutz/` | `DatenschutzView` | `public/datenschutz.html` | ✅ |
| `/admin/` | Django Admin | — | ✅ |
| `/dashboard/` | `DashboardView` | `dashboard/index.html` | 🔜 |
| `/worlds/` | `WorldListView` | `worlds/list.html` | 🔜 |
| `/worlds/<uuid>/` | `WorldDetailView` | `worlds/detail.html` | 🔜 |
| `/characters/` | `CharacterListView` | `characters/list.html` | 🔜 |
| `/api/v1/...` | DRF ViewSets | — | ✅ |

### 3.5 Legal Compliance (IIL GmbH)

#### Impressum (§5 TMG)
```
IIL – Privates Institut für Informationslogistik GmbH
Edison Allee 5-7
89231 Neu-Ulm
Deutschland

Geschäftsführerin: Sabine Dehnert
Telefon: 0171-5376151
E-Mail: info@weltenforger.com

Registergericht: Amtsgericht Memmingen
Registernummer: HRB 12191
USt-IdNr: DE236928454
```

#### Datenschutz (DSGVO)
- Verantwortliche Stelle: IIL GmbH
- Hosting: Hetzner Online GmbH
- Cookies: Session-Cookies für Authentifizierung
- Server-Logs: IP, Browser, Timestamp
- Rechte: Auskunft, Löschung, Widerspruch

---

## 4. Implementation

### 4.1 Phase 1: Public Pages ✅

**Erledigt am 2026-02-04:**

1. **App erstellt:** `apps/public/`
2. **Views:** `LandingView`, `ImpressumView`, `DatenschutzView`
3. **Templates:** `base.html`, `public/*.html`
4. **URLs:** Root-Path konfiguriert
5. **Deployment:** Live auf https://weltenforger.com

### 4.2 Phase 2: Dashboard (Nächster Schritt)

```python
# apps/dashboard/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.core.mixins import TenantRequiredMixin
from apps.core.middleware.tenant import get_current_tenant


class DashboardView(LoginRequiredMixin, TenantRequiredMixin, TemplateView):
    """Tenant-isolated dashboard showing recent entities."""
    
    template_name = "dashboard/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = get_current_tenant()  # Thread-local tenant
        context["worlds"] = World.objects.filter(tenant=tenant)[:5]
        context["characters"] = Character.objects.filter(tenant=tenant)[:5]
        context["stories"] = Story.objects.filter(tenant=tenant)[:5]
        return context
```

### 4.3 Phase 3: Entity CRUD

```python
# apps/core/mixins.py - TenantRequiredMixin (MANDATORY)
from django.core.exceptions import PermissionDenied
from apps.core.middleware.tenant import get_current_tenant


class TenantRequiredMixin:
    """Mixin das Tenant-Context erzwingt."""
    
    def dispatch(self, request, *args, **kwargs):
        tenant = get_current_tenant()
        if not tenant:
            raise PermissionDenied("Tenant context required")
        return super().dispatch(request, *args, **kwargs)
```

```python
# Zero-Hardcoding Pattern aus BFAgent übernehmen
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import TenantRequiredMixin


class WorldCRUDView(LoginRequiredMixin, TenantRequiredMixin, CRUDConfigMixin, View):
    model = World
    
    class CRUDConfig:
        list_display = ["name", "genre", "created_at"]
        form_layout = {
            "Basis": ["name", "description", "genre"],
            "Details": ["rules", "setting_details"]
        }
        htmx_config = {"auto_save": True}
```

### 4.4 Vollständige UI-Roadmap

| Phase | Sprint | Entität | Views | Templates | API-Integration | Tenant |
|-------|--------|---------|-------|-----------|-----------------|--------|
| 1 | ✅ Done | Public | 3 | 3 | — | Nein |
| 2 | S1 | Dashboard | 1 | 1 | Lookups, Stats | ✅ Ja |
| 3 | S1 | World | 4 (CRUD) | 4 | WorldViewSet | ✅ Ja |
| 4 | S2 | Location | 4 (CRUD) | 4 | LocationViewSet | ✅ Ja |
| 5 | S2 | Character | 4 (CRUD) | 4 | CharacterViewSet | ✅ Ja |
| 6 | S3 | Scene | 4 (CRUD) | 4 | SceneViewSet | ✅ Ja |
| 7 | S3 | Story | 4 (CRUD) | 4 | StoryViewSet | ✅ Ja |

**Total: 24 Views, 24 Templates, 6 Sprints**

### 4.5 Normalisierungs-Korrekturen (Database-First)

**Aktuell hardcoded (zu migrieren):**

| Model | Hardcoded Choice | Neue Lookup-Table | Migration |
|-------|------------------|-------------------|-----------|
| `WorldRule` | `Category` | `lkp_rule_category` | S1 |
| `WorldRule` | `Importance` | `lkp_rule_importance` | S1 |
| `TenantUser` | `Role` | `lkp_tenant_role` | S2 |

```sql
-- Migration: Lookup-Tables für hardcoded Choices
CREATE TABLE IF NOT EXISTS lkp_rule_category (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_de VARCHAR(100),
    description TEXT,
    "order" INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO lkp_rule_category (code, name, name_de, "order") VALUES
    ('physics', 'Physics', 'Physik', 10),
    ('magic', 'Magic', 'Magie', 20),
    ('social', 'Society', 'Gesellschaft', 30),
    ('technology', 'Technology', 'Technologie', 40),
    ('biology', 'Biology', 'Biologie', 50),
    ('economy', 'Economy', 'Wirtschaft', 60);
```

---

## 5. Deployment

### 5.1 Aktuelle Konfiguration

| Komponente | Wert |
|------------|------|
| **Primary URL** | https://weltenforger.com |
| **Alt URLs** | weltenforger.de, www.* |
| **Server** | 88.198.191.108 (Hetzner) |
| **Container** | weltenhub_web |
| **Port** | 8081 → Nginx → 443 |
| **SSL** | Let's Encrypt (bis 2026-05) |

### 5.2 Deploy-Workflow

```bash
# 1. Lokale Änderungen committen
cd ~/github/platform/weltenhub
git add -A && git commit -m "feat: ..." && git push

# 2. Auf Server kopieren
rsync -avz --exclude '.git' ~/github/platform/weltenhub/ \
  root@88.198.191.108:/opt/weltenhub/repo/

# 3. Image bauen + Container neu starten
ssh root@88.198.191.108 'cd /opt/weltenhub && \
  docker build -t ghcr.io/achimdehnert/weltenhub:latest repo/ && \
  docker compose -f docker-compose.prod.yml down && \
  docker compose -f docker-compose.prod.yml up -d'
```

---

### 5.3 HTMX Integration (KRITISCH für Phase 2+)

```html
<!-- templates/base.html - VOR </body> ergänzen -->

<!-- HTMX 2.0 -->
<script src="https://unpkg.com/htmx.org@2.0.0"></script>
<script>
    // CSRF Token für HTMX
    document.body.addEventListener('htmx:configRequest', function(evt) {
        evt.detail.headers['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
            || '{{ csrf_token }}';
    });
    
    // Error Handling
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX Error:', evt.detail);
    });
</script>
```

### 5.4 Produktions-Checkliste

| Komponente | Status | Priorität | Verantwortlich |
|------------|--------|-----------|----------------|
| ✅ Landingpage | Live | P1 | Done |
| ✅ Impressum | Live | P1 | Done |
| ✅ Datenschutz | Live | P1 | Done |
| ❌ HTMX einbinden | Fehlt | P1 | Sprint 1 |
| ❌ TenantRequiredMixin | Fehlt | P1 | Sprint 1 |
| ❌ Custom Error Pages | Fehlt | P2 | Sprint 1 |
| ❌ Type Hints ergänzen | Fehlt | P2 | Sprint 1 |
| ❌ Services Layer | Fehlt | P2 | Sprint 2 |
| ⚠️ DB_PASSWORD auf Server | Warning | P1 | Sofort |

---

## 6. Consequences

### 6.1 Positive

| Benefit | Impact |
|---------|--------|
| Production-ready Landing | Sofort nutzbar für Marketing |
| DSGVO-Compliance | Rechtssicherheit für DE |
| Wiederverwendbare Templates | Schnelle UI-Entwicklung |
| Bootstrap 5 | Modern, Responsive, Accessible |
| HTMX-ready | SPA-ähnliche UX ohne JS-Framework |

### 6.2 Negative/Risiken

| Risk | Mitigation |
|------|------------|
| Template-Duplikation | Partials + Includes nutzen |
| Styling-Inkonsistenz | Design System dokumentieren |
| Performance | Static Files cachen, CDN nutzen |

---

## 7. References

- [ADR-018: Weltenhub Architecture](./ADR-018-weltenhub-architecture.md)
- [ADR-015: Platform Governance](./ADR-015-platform-governance-system.md)
- [Bootstrap 5 Docs](https://getbootstrap.com/docs/5.3/)
- [HTMX Docs](https://htmx.org/docs/)
- [DSGVO Compliance](https://dsgvo-gesetz.de/)

---

## Appendix A: Erstellte Dateien

| Datei | Beschreibung |
|-------|--------------|
| `apps/public/__init__.py` | App-Initialisierung |
| `apps/public/views.py` | Landing, Impressum, Datenschutz Views |
| `apps/public/urls.py` | URL-Routing |
| `templates/base.html` | Bootstrap 5 Base Template |
| `templates/public/landing.html` | Hero + Features + CTA |
| `templates/public/impressum.html` | IIL GmbH Impressum |
| `templates/public/datenschutz.html` | DSGVO Datenschutzerklärung |

## Appendix B: Verifizierung

```bash
# Alle Seiten geben HTTP 200 zurück
curl -s -o /dev/null -w '%{http_code}' https://weltenforger.com/           # 200
curl -s -o /dev/null -w '%{http_code}' https://weltenforger.com/impressum/ # 200
curl -s -o /dev/null -w '%{http_code}' https://weltenforger.com/datenschutz/ # 200
```
