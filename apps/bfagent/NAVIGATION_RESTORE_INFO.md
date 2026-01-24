# Dynamische Navigation Wiederherstellung

## Quelle (AKTUELL - VOR RAILWAY)
**Commit:** `fe9fd95` - "Abschluß reorganmisation NAvigation"
**Datum:** 18. Nov 2025 (vor ca. 2 Tagen, vor Railway)

## Alte Quelle
**Commit:** `2dd1d23` - "Ende navigationsleiste"
**Datum:** ~30 Tage vor heute

## Datenbank-Tabellen (aus Screenshot)
- `navigation_items`
- `navigation_items_domains`
- `navigation_items_required_groups`
- `navigation_sections`
- `navigation_sections_domains`
- `navigation_section_configs`
- `navigation_sections_required_groups`
- `navigation_sections_required_permissions`

## Wiederherstellung Befehle (Commit fe9fd95)

### 1. Hauptdateien wiederherstellen
```powershell
# Models (Datenbank-Struktur)
git show fe9fd95:apps/control_center/models_navigation.py > apps/control_center/models_navigation.py

# Navigation Helpers
git show fe9fd95:apps/control_center/navigation_helpers.py > apps/control_center/navigation_helpers.py

# Domain Navigation Views
git show fe9fd95:apps/control_center/views_domain_navigation.py > apps/control_center/views_domain_navigation.py
```

### 2. Management Commands
```powershell
git show fe9fd95:apps/control_center/management/commands/populate_navigation_domains.py > apps/control_center/management/commands/populate_navigation_domains.py
```

### 3. Migrationen
```powershell
git show fe9fd95:apps/control_center/migrations/0001_add_domain_id_to_navigation.py > apps/control_center/migrations/0001_add_domain_id_to_navigation.py
```

### 4. Templates (Domain Navigation)
```powershell
git show fe9fd95:apps/control_center/templates/control_center/domain_navigation/configurator.html > apps/control_center/templates/control_center/domain_navigation/configurator.html
```

### 5. Datenbank Migrationen anwenden
```powershell
python manage.py makemigrations control_center
python manage.py migrate
python manage.py populate_navigation_domains
```

## Nächste Schritte
1. Dateien wiederherstellen
2. URLs in `control_center/urls.py` aktivieren
3. Migrationen durchführen
4. Templates anpassen
