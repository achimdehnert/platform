# Windsurf KI Prompt für Django 5.2 LTS + HTMX Projekt

## Version 1: Standard-Prompt (Django 5.2 LTS optimiert)

```
Ich möchte ein professionelles Django 5.2 LTS Projekt mit HTMX-Frontend für eine existierende SQLite-Datenbank erstellen.

**Projekt-Anforderungen:**

1. **Datenbank-Integration mit Django 5.2 Features:**
   - Verwende die existierende SQLite-Datenbank [DATEINAME.db]
   - Führe `inspectdb` aus, um Models aus allen nicht-Django-spezifischen Tabellen zu generieren
   - Nutze GeneratedField für berechnete Spalten wo sinnvoll
   - Implementiere db_default für Datenbank-seitige Standardwerte
   - Prüfe Möglichkeiten für CompositePrimaryKey bei zusammengesetzten Schlüsseln
   - Behalte die Original-Tabellenstruktur bei (managed=False)

2. **Django 5.2 LTS Backend:**
   - Python 3.12+ für beste Performance
   - Modulare App-Struktur mit automatischen Model-Imports in Shell
   - Vollständige Django-Admin-Integration mit Facet-Filtern
   - LoginRequiredMiddleware für globale Authentifizierung
   - Class-Based-Views (CBVs) mit async-Support wo sinnvoll
   - PostgreSQL Connection Pooling vorbereiten (für spätere Migration)

3. **HTMX-Frontend mit Django 5.2 Template Features:**
   - Nutze {% querystring %} Tag für URL-Parameter-Verwaltung
   - Implementiere Field Group Rendering (.as_field_group) für Formulare
   - Responsive Templates mit Tailwind CSS oder Bulma
   - HTMX-Attributes (hx-get, hx-post, hx-target, hx-swap, hx-indicator)
   - django-template-partials für Fragment-Rendering
   - Inline-Editing und Optimistic UI Updates

4. **Sicherheit & Best Practices:**
   - CSRF-Protection für alle HTMX-Requests (x-csrftoken Header)
   - Async-fähige Authentifizierung
   - aria-describedby für barrierefreie Formular-Fehler
   - Optimierte Queries mit GeneratedField für Performance

5. **Projekt-Struktur:**
   - UV als Package Manager (Django 5.2 kompatibel)
   - requirements.txt mit Django==5.2.*, django-htmx, django-template-partials
   - Settings für Development/Production getrennt
   - .env für sensible Daten mit python-decouple

Bitte generiere das komplette Projekt mit allen Django 5.2 LTS spezifischen Features und erkläre die Implementierung der neuen Funktionen.
```

## Version 2: Professional Enterprise-Prompt (Django 5.2 LTS fokussiert)

```
Erstelle ein produktionsreifes Django 5.2 LTS Projekt mit HTMX-Frontend für eine Legacy SQLite-Datenbank unter Nutzung aller neuen Django 5.2 Features.

**KONTEXT:**
- Existierende SQLite-Datenbank: [DATEINAME.db] mit [X] Tabellen
- Django 5.2 LTS für 3 Jahre Sicherheitssupport (bis April 2028)
- Python 3.12+ für optimale Performance
- Multi-User-System mit LoginRequiredMiddleware

**TECHNISCHER STACK - Django 5.2 optimiert:**
- Django 5.2 LTS mit allen neuen Features
- HTMX 2.x + Alpine.js für erweiterte Interaktivität
- django-htmx für optimale Integration
- django-template-partials für Fragment-Rendering
- UV Package Manager für schnelle Dependencies
- Gunicorn + Uvicorn (ASGI/WSGI Hybrid)
- PostgreSQL-Ready (Connection Pooling vorbereitet)

**DJANGO 5.2 SPEZIFISCHE FEATURES:**

1. **ADVANCED DATABASE LAYER:**
   ```python
   # Models mit Django 5.2 Features
   - GeneratedField für berechnete Spalten
   - db_default für DB-seitige Defaults (Now(), etc.)
   - CompositePrimaryKey für zusammengesetzte Schlüssel
   - CharField ohne max_length auf SQLite
   - Model._is_pk_set() für PK-Checks
   ```

2. **ENHANCED ADMIN INTERFACE:**
   ```python
   # Admin mit Django 5.2 Verbesserungen
   - Facet Filter mit show_facets Attribut
   - URLField als klickbare Links
   - extrabody Block für Custom Scripts
   - Verbesserte Accessibility (nav, footer Tags)
   - <details>/<summary> für Fieldsets
   ```

3. **MODERN FORM HANDLING:**
   ```python
   # Forms mit Django 5.2 Features
   - Field.as_field_group() für komplette Feld-Gruppen
   - Custom BoundField Classes
   - aria-describedby für Fehler-Accessibility
   - Script Asset Objects für Form Media
   - Verbesserte Error Rendering
   ```

4. **TEMPLATE ENHANCEMENTS:**
   ```django
   <!-- Django 5.2 Template Features -->
   {% querystring page=next_page category=current %}
   {{ form.email.as_field_group }}
   {% partialdef modal-content inline=True %}
   ```

5. **AUTHENTICATION & MIDDLEWARE:**
   ```python
   MIDDLEWARE = [
       # ...
       'django.contrib.auth.middleware.LoginRequiredMiddleware',
   ]

   # Views ohne Login-Requirement
   @login_not_required
   def public_view(request): ...

   # Async Authentication Backends
   class AsyncAuthBackend:
       async def aauthenticate(self, request, **kwargs): ...
   ```

6. **DEVELOPER EXPERIENCE:**
   ```bash
   # Auto-Import in Shell
   $ python manage.py shell --verbosity=2
   # 6 objects imported automatically

   # Neue Management Commands
   class Command(BaseCommand):
       autodetector = CustomAutodetector
       def get_check_kwargs(self): ...
   ```

7. **PERFORMANCE OPTIMIZATIONS:**
   - GeneratedField für DB-seitige Berechnungen
   - PostgreSQL Connection Pooling Support
   - Optimierte bulk_create für LogEntry
   - AlterConstraint ohne DROP/CREATE
   - response.text für Test-Vereinfachung

8. **HTMX IMPLEMENTATION mit Django 5.2:**
   - Nutze {% querystring %} für Pagination
   - Field Groups für HTMX-Forms
   - Partial Rendering mit neuem Template System
   - LoginRequiredMiddleware-kompatible HTMX-Endpoints
   - Async Views für WebSocket-ähnliche Features

9. **MIGRATION & COMPATIBILITY:**
   - Django 5.2 LTS bis April 2028
   - Python 3.10-3.13 Support
   - Vorbereitung für Django 6.0
   - Deprecation Warnings beachten

**OUTPUT-ERWARTUNGEN:**
1. Vollständige Projektstruktur mit Django 5.2 Best Practices
2. Beispiel-Implementierungen aller neuen Features
3. Migration von SQLite zu PostgreSQL vorbereitet
4. Performance-Benchmarks mit GeneratedFields
5. Deployment für Django 5.2 (ASGI/WSGI)
6. Upgrade-Pfad zu Django 6.0 dokumentiert

Implementiere das Projekt mit Production-Ready Code unter maximaler Nutzung der Django 5.2 LTS Features.
```

## Version 3: Minimal-Prompt (Quick Start Django 5.2)

```
Erstelle ein Django 5.2 LTS + HTMX Projekt für meine SQLite-Datenbank [DATEINAME.db]:

**Django 5.2 Features nutzen:**
1. Models mit GeneratedField für berechnete Spalten generieren (inspectdb)
2. Admin mit Facet-Filtern für alle Models
3. HTMX-Frontend mit Django 5.2 Features:
   - {% querystring %} für Pagination/Filter
   - {{ form.field.as_field_group }} für Forms
   - LoginRequiredMiddleware + @login_not_required
   - Partials mit django-template-partials

**Stack:** Django==5.2.*, Python 3.12+, HTMX 2.x, django-htmx, Tailwind
**Features:** Auto-Import Shell, db_default, aria-describedby, response.text

Generiere Production-Ready Code mit allen Django 5.2 LTS Vorteilen.
```

## Zusätzliche Django 5.2 spezifische Hinweise für Windsurf:

### 🎯 **Django 5.2 Feature-Checkliste**

```python
# 1. GeneratedField Beispiel für Ihre DB:
class Product(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=4, decimal_places=2)
    price_with_tax = models.GeneratedField(
        expression=F("price") * (1 + F("tax_rate")),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True
    )

# 2. db_default für Timestamps:
class AuditLog(models.Model):
    created_at = models.DateTimeField(db_default=Now())
    user_ip = models.GenericIPAddressField(db_default="0.0.0.0")

# 3. Composite Primary Keys (falls in Ihrer DB vorhanden):
class OrderItem(models.Model):
    pk = models.CompositePrimaryKey("order_id", "product_id")
    order_id = models.IntegerField()
    product_id = models.IntegerField()

# 4. Field Group in Templates:
"""
templates/forms/field_group.html:
<div class="field-wrapper">
    {{ field.label_tag }}
    {{ field }}
    {% if field.help_text %}
        <p class="help-text" id="{{ field.auto_id }}_helptext">
            {{ field.help_text|safe }}
        </p>
    {% endif %}
    {{ field.errors }}
</div>
"""

# 5. LoginRequiredMiddleware Setup:
MIDDLEWARE = [
    # ... andere middleware
    'django.contrib.auth.middleware.LoginRequiredMiddleware',
]

# Public views markieren:
from django.contrib.auth.decorators import login_not_required

@login_not_required
def landing_page(request):
    return render(request, 'landing.html')

# 6. Shell Auto-Imports anpassen:
# management/commands/shell.py
from django.core.management.commands.shell import Command as ShellCommand

class Command(ShellCommand):
    def get_imported_objects(self):
        imported_objects = super().get_imported_objects()
        # Zusätzliche Imports
        from django.db.models import Q, F
        imported_objects['Q'] = Q
        imported_objects['F'] = F
        return imported_objects
```

### 📋 **Migrations-Hinweise für Django 5.2**

```bash
# Nach inspectdb für GeneratedFields:
python manage.py makemigrations --name add_generated_fields

# Für Composite Primary Keys:
python manage.py makemigrations --name add_composite_pks
```

### 🔧 **HTMX + Django 5.2 Integration**

```django
<!-- Pagination mit querystring tag -->
<nav aria-label="Pagination">
    {% if page.has_previous %}
        <a href="{% querystring page=page.previous_page_number %}"
           hx-get="{% querystring page=page.previous_page_number %}"
           hx-target="#content">Previous</a>
    {% endif %}

    <span>Page {{ page.number }}</span>

    {% if page.has_next %}
        <a href="{% querystring page=page.next_page_number %}"
           hx-get="{% querystring page=page.next_page_number %}"
           hx-target="#content">Next</a>
    {% endif %}
</nav>

<!-- Form mit Field Groups -->
<form hx-post="{% url 'create_item' %}" hx-target="#items-list">
    {% csrf_token %}
    {{ form.name.as_field_group }}
    {{ form.description.as_field_group }}
    <button type="submit">Save</button>
</form>
```

Diese optimierten Prompts nutzen alle Vorteile von Django 5.2 LTS und garantieren, dass Ihr Projekt:
- 3 Jahre Sicherheitsupdates erhält
- Die neuesten Performance-Optimierungen nutzt
- Zukunftssicher für Django 6.0 ist
- Die beste Developer Experience bietet
