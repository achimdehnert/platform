# ADR-019: Weltenhub UI, Templates, Views & APIs für weltenforger.com

| Metadata | Value |
|----------|-------|
| **Status** | Accepted |
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
class DashboardView(LoginRequiredMixin, TenantMixin, TemplateView):
    template_name = "dashboard/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        context["worlds"] = World.objects.filter(tenant=tenant)[:5]
        context["characters"] = Character.objects.filter(tenant=tenant)[:5]
        context["stories"] = Story.objects.filter(tenant=tenant)[:5]
        return context
```

### 4.3 Phase 3: Entity CRUD

```python
# Zero-Hardcoding Pattern aus BFAgent übernehmen
class WorldCRUDView(CRUDConfigMixin, TenantMixin, View):
    model = World
    
    class CRUDConfig:
        list_display = ["name", "genre", "created_at"]
        form_layout = {
            "Basis": ["name", "description", "genre"],
            "Details": ["rules", "setting_details"]
        }
        htmx_config = {"auto_save": True}
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
