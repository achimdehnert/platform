# ✅ Phase 2b - Test Checklist

## 🎯 Ziel
Handler Normalisierung testen: `category` CharField → `category_fk` ForeignKey

---

## 📋 PRE-MIGRATION TESTS

### ✅ 1. Backup erstellen
```bash
# SQLite Backup
cp db.sqlite3 db.sqlite3.backup_phase2b

# Oder Export
python manage.py dumpdata core.Handler core.HandlerCategory > handlers_backup.json
```

### ✅ 2. Aktuelle Daten prüfen
```bash
python manage.py shell
```

```python
from apps.core.models import Handler, HandlerCategory

# Wie viele Handler gibt es?
print(f"Handlers: {Handler.objects.count()}")

# Welche Kategorien?
for cat in ['input', 'processing', 'output']:
    count = Handler.objects.filter(category=cat).count()
    print(f"{cat}: {count}")
```

---

## 🚀 MIGRATION AUSFÜHREN

### ✅ 3. HandlerCategories laden
```bash
python manage.py load_handler_categories
```

**Erwartete Ausgabe:**
```
✅ Created: Input Handler (input)
✅ Created: Processing Handler (processing)
✅ Created: Output Handler (output)
```

### ✅ 4. Migrations anwenden
```bash
python manage.py migrate core
```

**Erwartete Ausgabe:**
```
Running migrations:
  Applying core.0004_add_category_fk... OK
  Applying core.0005_migrate_category_data...
  ============================================================
    ✅ CATEGORY MIGRATION COMPLETE
  ============================================================
    Migrated: X
    Skipped: 0
  ============================================================
  OK
```

---

## 🧪 POST-MIGRATION TESTS

### ✅ 5. Automatische Tests
```bash
python test_phase_2b_migration.py
```

**Erwartete Ausgabe:**
```
🧪 PHASE 2B - HANDLER NORMALISIERUNG TEST SUITE
✅ PASSED: test_1_check_categories_exist
✅ PASSED: test_2_check_handlers_exist
✅ PASSED: test_3_check_migration_fields
✅ PASSED: test_4_check_data_migration
✅ PASSED: test_5_check_category_mapping
✅ PASSED: test_6_check_helper_properties
✅ PASSED: test_7_check_backwards_compatibility
✅ PASSED: test_8_check_database_schema
Results: 8/8 tests passed
🎉 ALL TESTS PASSED!
```

### ✅ 6. SQL Tests
```bash
sqlite3 db.sqlite3 < test_phase_2b_sql.sql
```

**Wichtige Checks:**
- [ ] HandlerCategories haben 3 Einträge
- [ ] Alle Handler haben `category_id` gesetzt (nicht NULL)
- [ ] Keine Mismatches: `category` = `category_fk.code`
- [ ] Foreign Key Constraint existiert

### ✅ 7. Django Shell Tests
```bash
python manage.py shell
```

```python
from apps.core.models import Handler, HandlerCategory

# Test 1: Kategorien zählen
for cat in HandlerCategory.objects.all():
    count = cat.handlers.count()
    print(f"{cat.name}: {count} handlers")

# Test 2: Ersten Handler prüfen
h = Handler.objects.first()
if h:
    print(f"\nHandler: {h.code}")
    print(f"  category (old): {h.category}")
    print(f"  category_fk (new): {h.category_fk}")
    print(f"  category_code: {h.category_code}")
    print(f"  category_name: {h.category_name}")
    print(f"  Match: {h.category == h.category_fk.code}")

# Test 3: Alle Handler durchgehen
mismatches = []
for h in Handler.objects.all():
    if h.category_fk is None:
        mismatches.append(f"{h.code}: category_fk is NULL")
    elif h.category != h.category_fk.code:
        mismatches.append(f"{h.code}: {h.category} != {h.category_fk.code}")

if mismatches:
    print("\n❌ Problems found:")
    for m in mismatches:
        print(f"  {m}")
else:
    print("\n✅ All handlers migrated correctly!")
```

---

## 🔍 BACKWARDS COMPATIBILITY TESTS

### ✅ 8. Code Kompatibilität
```python
from apps.core.models import Handler

h = Handler.objects.first()

# Diese sollten alle funktionieren:
print(h.category)           # ✅ CharField (deprecated)
print(h.category_fk)        # ✅ FK (new)
print(h.category_code)      # ✅ Property
print(h.category_name)      # ✅ Property

# Queries sollten funktionieren:
Handler.objects.filter(category='input')        # ✅ Old style
Handler.objects.filter(category_fk__code='input')  # ✅ New style
```

---

## 🎯 INTEGRATION TESTS

### ✅ 9. Admin Interface
```bash
python manage.py runserver
```

Öffne: `http://localhost:8000/admin/core/handler/`

**Prüfen:**
- [ ] Handler List View lädt
- [ ] Category wird korrekt angezeigt
- [ ] Handler Detail View lädt
- [ ] Handler kann editiert werden
- [ ] Keine Errors in Console

### ✅ 10. Handler Management View
Öffne: `http://localhost:8000/bfagent/handler-management/`

**Prüfen:**
- [ ] Dashboard lädt ohne Fehler
- [ ] Handler werden korrekt gruppiert nach Category
- [ ] Kategorie-Namen werden angezeigt
- [ ] Keine NoReverseMatch Errors

---

## 📊 PERFORMANCE TESTS

### ✅ 11. Query Performance
```python
from django.db import connection
from django.test.utils import override_settings
import time

# Test Query Performance
with override_settings(DEBUG=True):
    connection.queries_log.clear()
    
    # Old style (CharField)
    start = time.time()
    list(Handler.objects.filter(category='input'))
    old_time = time.time() - start
    old_queries = len(connection.queries)
    
    connection.queries_log.clear()
    
    # New style (FK)
    start = time.time()
    list(Handler.objects.filter(category_fk__code='input'))
    new_time = time.time() - start
    new_queries = len(connection.queries)
    
    print(f"Old (CharField): {old_time:.4f}s, {old_queries} queries")
    print(f"New (FK): {new_time:.4f}s, {new_queries} queries")
```

---

## ✅ ROLLBACK TEST (Optional)

### ✅ 12. Migration Rollback testen
```bash
# Backup first!
cp db.sqlite3 db.sqlite3.test_rollback

# Rollback
python manage.py migrate core 0003

# Verify
python manage.py shell -c "from apps.core.models import Handler; print([h.category for h in Handler.objects.all()[:3]])"

# Re-apply
python manage.py migrate core
```

---

## 🎉 SUCCESS CRITERIA

**Phase 2b ist erfolgreich wenn:**

- [x] **Alle 8 automatischen Tests bestehen**
- [x] **Keine NULL category_fk Werte** (alle migriert)
- [x] **Keine Mismatches** (category = category_fk.code)
- [x] **Admin Interface funktioniert**
- [x] **Handler Management View funktioniert**
- [x] **Backwards Compatibility gewährleistet**
- [x] **Performance OK** (FK Queries nicht langsamer)
- [x] **Rollback funktioniert** (falls nötig)

---

## 🚨 BEI PROBLEMEN

### Problem: Migration schlägt fehl
```bash
# Rollback
python manage.py migrate core 0003

# Logs prüfen
python manage.py migrate core --verbosity 3

# Datenbank prüfen
sqlite3 db.sqlite3 "SELECT * FROM handler_categories;"
```

### Problem: NULL category_fk Werte
```bash
# Re-run data migration
python manage.py migrate core 0005 --fake-initial
python manage.py migrate core 0005
```

### Problem: Mismatches
```python
from apps.core.models import Handler, HandlerCategory

# Fix manually
for h in Handler.objects.filter(category_fk__isnull=False):
    if h.category != h.category_fk.code:
        print(f"Fixing {h.code}: {h.category} → {h.category_fk.code}")
        h.category = h.category_fk.code
        h.save()
```

---

## 📝 NOTES

- Migration ist **NON-DESTRUCTIVE** (beide Felder existieren parallel)
- `category` CharField wird erst in Phase 2b.2 entfernt
- Rollback jederzeit möglich
- Performance-Impact minimal (Integer FK vs String)

---

**Status:** ✅ Bereit zum Testen  
**Erstellt:** 2025-12-08  
**Phase:** 2b - Handler Normalisierung
