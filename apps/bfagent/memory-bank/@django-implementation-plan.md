# @django-implementation-plan.md - Stufenweise Django 5.2 LTS Implementierung

## 🎯 Implementierungsstrategie

### Phase 1: Projekt-Setup und Datenbank-Analyse (Tag 1-2)

#### 1.1 Umgebung vorbereiten
```bash
# Python 3.12+ Virtual Environment
python -m venv django_env
django_env\Scripts\activate

# UV Package Manager Installation
pip install uv
uv pip install Django==5.2.*
```

#### 1.2 Datenbank-Inspektion (KRITISCH)
```bash
# Backup der existierenden Datenbank
copy db.sqlite3 db_backup_$(date +%Y%m%d).sqlite3

# Schema-Analyse
sqlite3 db.sqlite3 ".schema" > schema_analysis.sql
sqlite3 db.sqlite3 ".tables" > tables_list.txt

# Datenstruktur verstehen
sqlite3 db.sqlite3 "SELECT name, sql FROM sqlite_master WHERE type='table';"
```

#### 1.3 Django-Projekt initialisieren
```bash
django-admin startproject config .
cd config && mkdir settings
# Aufteilen in base.py, development.py, production.py
```

### Phase 2: Sichere Datenbank-Integration (Tag 3-4)

#### 2.1 Model-Generierung mit Sicherheitsnetz
```bash
# Schritt 1: Inspectdb in temporäre Datei
python manage.py inspectdb > temp_models.py

# Schritt 2: Models manuell überprüfen und anpassen
# - managed = False beibehalten für Sicherheit
# - Feldtypen validieren
# - Beziehungen prüfen
```

#### 2.2 Sichere Migration-Strategie
```python
# models.py - Erste Version (READ-ONLY)
class ExistingTable(models.Model):
    # Alle Felder aus inspectdb
    class Meta:
        managed = False  # WICHTIG: Keine DB-Änderungen
        db_table = 'existing_table'
```

#### 2.3 Test-Migration ohne Risiko
```bash
# Fake-Initial Migration (keine DB-Änderungen)
python manage.py makemigrations --empty your_app
python manage.py migrate --fake-initial

# Validierung: Daten lesbar?
python manage.py shell
>>> from your_app.models import ExistingTable
>>> ExistingTable.objects.count()  # Sollte funktionieren
```

### Phase 3: Django 5.2 Features schrittweise einführen (Tag 5-7)

#### 3.1 Admin-Interface (Risikoarm)
```python
# admin.py - Nur Lese-Zugriff zunächst
@admin.register(ExistingTable)
class ExistingTableAdmin(admin.ModelAdmin):
    list_display = ['field1', 'field2']
    list_filter = ['field1']
    search_fields = ['field2']

    # Django 5.2 Feature: Facet Filters
    show_facets = admin.ShowFacets.ALWAYS

    # Sicherheit: Nur Lesen
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
```

#### 3.2 Basis-Views implementieren
```python
# views.py - Nur Lese-Zugriff
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

class ExistingTableListView(LoginRequiredMixin, ListView):
    model = ExistingTable
    template_name = 'list.html'
    paginate_by = 20
```

### Phase 4: HTMX-Integration (Tag 8-10)

#### 4.1 Template-System aufbauen
```django
<!-- base.html mit Django 5.2 Features -->
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/htmx.org@2.0.0"></script>
</head>
<body>
    <nav>{% include 'partials/navigation.html' %}</nav>
    <main id="content">{% block content %}{% endblock %}</main>
</body>
</html>

<!-- list.html mit querystring tag -->
{% extends 'base.html' %}
{% block content %}
    <div hx-target="this">
        {% for item in object_list %}
            <div>{{ item }}</div>
        {% endfor %}

        <!-- Pagination mit Django 5.2 querystring -->
        {% if is_paginated %}
            <nav>
                {% if page_obj.has_previous %}
                    <a href="{% querystring page=page_obj.previous_page_number %}"
                       hx-get="{% querystring page=page_obj.previous_page_number %}">Previous</a>
                {% endif %}
            </nav>
        {% endif %}
    </div>
{% endblock %}
```

### Phase 5: Erweiterte Django 5.2 Features (Tag 11-14)

#### 5.1 GeneratedField sicher einführen
```python
# Neue Tabelle für Tests (nicht existierende Daten ändern!)
class CalculatedData(models.Model):
    base_value = models.DecimalField(max_digits=10, decimal_places=2)
    multiplier = models.DecimalField(max_digits=4, decimal_places=2)

    # Django 5.2 GeneratedField
    calculated_result = models.GeneratedField(
        expression=F("base_value") * F("multiplier"),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True
    )

    class Meta:
        managed = True  # Neue Tabelle, sicher zu verwalten
```

#### 5.2 LoginRequiredMiddleware aktivieren
```python
# settings/base.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.LoginRequiredMiddleware',  # Django 5.2
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Öffentliche Views markieren
from django.contrib.auth.decorators import login_not_required

@login_not_required
def public_api_view(request):
    return JsonResponse({'status': 'public'})
```

## 🛡️ Datenbank-Migrations-Sicherheitsstrategie

### Backup-Strategie (KRITISCH)
```bash
# Automatisches Backup vor jeder Migration
#!/bin/bash
# backup_before_migrate.sh
BACKUP_DIR="db_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sqlite3"

mkdir -p $BACKUP_DIR
cp db.sqlite3 $BACKUP_FILE
echo "Backup erstellt: $BACKUP_FILE"

# Migration ausführen
python manage.py migrate

# Validierung
python manage.py check --database default
```

### Rollback-Strategie
```bash
# Rollback-Script
#!/bin/bash
# rollback_migration.sh
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./rollback_migration.sh backup_file.sqlite3"
    exit 1
fi

# Service stoppen (falls läuft)
pkill -f "manage.py runserver"

# Datenbank ersetzen
cp $BACKUP_FILE db.sqlite3

# Validierung
python manage.py check --database default
echo "Rollback abgeschlossen"
```

### Migration-Validierung
```python
# management/commands/validate_migration.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Tabellen-Integrität prüfen
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

        if result[0] != 'ok':
            self.stdout.write(self.style.ERROR('Database integrity check failed!'))
            return

        # Daten-Konsistenz prüfen
        from your_app.models import ExistingTable
        count_before = self.get_record_count_from_backup()
        count_after = ExistingTable.objects.count()

        if count_before != count_after:
            self.stdout.write(self.style.ERROR(f'Record count mismatch: {count_before} vs {count_after}'))
            return

        self.stdout.write(self.style.SUCCESS('Migration validation successful'))
```

### Schrittweise managed=True Aktivierung
```python
# Phase 1: managed=False (nur lesen)
class ExistingTable(models.Model):
    class Meta:
        managed = False
        db_table = 'existing_table'

# Phase 2: managed=True für neue Felder (nach Tests)
class ExistingTable(models.Model):
    # Existierende Felder
    new_field = models.CharField(max_length=100, null=True)  # Sicher hinzufügbar

    class Meta:
        managed = True  # Nur nach erfolgreichen Tests
        db_table = 'existing_table'
```

## 📋 Checkpoint-System

### Validierung nach jeder Phase
```bash
# Checkpoint-Script
#!/bin/bash
# checkpoint_validation.sh

echo "=== Checkpoint Validation ==="
echo "1. Database integrity..."
python manage.py validate_migration

echo "2. Django checks..."
python manage.py check --deploy

echo "3. Test suite..."
python manage.py test --keepdb

echo "4. Admin access..."
python manage.py shell -c "from django.contrib.auth.models import User; print(f'Users: {User.objects.count()}')"

echo "5. Model access..."
python manage.py shell -c "from your_app.models import ExistingTable; print(f'Records: {ExistingTable.objects.count()}')"

echo "=== Checkpoint Complete ==="
```

### Rollback-Punkte definieren
- **Checkpoint 1**: Nach Projekt-Setup (vor DB-Integration)
- **Checkpoint 2**: Nach erfolgreicher inspectdb (vor managed=True)
- **Checkpoint 3**: Nach Admin-Setup (vor HTMX)
- **Checkpoint 4**: Nach HTMX-Integration (vor erweiterte Features)

Diese Strategie gewährleistet maximale Sicherheit bei der Datenbank-Migration und ermöglicht schnelle Rollbacks bei Problemen.
