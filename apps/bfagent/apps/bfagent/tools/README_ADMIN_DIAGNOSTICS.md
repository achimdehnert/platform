# Admin Diagnostics Tools

**Location:** `apps/bfagent/tools/admin_diagnostic_tools.py`  
**Service:** `apps/bfagent/services/admin_diagnostics.py`  
**Command:** `apps/bfagent/management/commands/admin_diagnostics.py`

---

## 🎯 Quick Start

### Via Management Command (Empfohlen)

```bash
# Complete Health Check
python manage.py admin_diagnostics health-check --app writing_hub

# Mit Auto-Fix
python manage.py admin_diagnostics health-check --app writing_hub --fix
```

### Via Python API

```python
from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics

service = get_admin_diagnostics()
results = service.diagnose_schema_errors('writing_hub')
```

### Via Tool Functions

```python
from apps.bfagent.tools.admin_diagnostic_tools import (
    diagnose_db_errors,
    fix_all_views,
    test_admin_urls,
    admin_health_check
)

# Use directly
results = admin_health_check('writing_hub', auto_fix=True)
```

---

## 📦 Verfügbare Tools

### 1. diagnose_db_errors
Findet Schema-Mismatches zwischen Django Models und Datenbank.

### 2. fix_table_references
Erstellt VIEWs für fehlende Tabellen automatisch.

### 3. fix_all_views
Fixt alle bekannten VIEW-Mappings (book_chapters, book_projects, characters).

### 4. test_admin_urls
Testet alle Admin-Seiten auf Fehler, mit optionalem Auto-Fix.

### 5. find_unused_tables
Findet ungenutzte Datenbank-Tabellen.

### 6. admin_health_check
Führt alle Tools aus und erstellt umfassenden Report.

---

## 🚀 Command Line Usage

```bash
# Alle verfügbaren Actions
python manage.py admin_diagnostics <action> [options]

# Actions:
#   diagnose      - Schema diagnostizieren
#   fix-tables    - Tabellen-Referenzen fixen
#   fix-views     - Alle VIEWs fixen
#   test-admin    - Admin URLs testen
#   find-unused   - Ungenutzte Tabellen finden
#   health-check  - Kompletter Health Check

# Options:
#   --app <app>   - Auf App fokussieren
#   --fix         - Auto-Fix aktivieren
#   --json        - JSON Output
```

---

## ✅ Verification

```bash
# Test auf writing_hub
python manage.py admin_diagnostics health-check --app writing_hub
```

**Expected Output:**
```
================================================================================
💊 ADMIN HEALTH CHECK
================================================================================

📊 Schema Status:
  Missing tables: 0
  Missing columns: 0

🌐 Admin Status:
  Tested: 16
  Errors: 0

🗑️  Database Cleanup:
  Unused tables: 144
  Unused rows: 1,214

================================================================================
✅ ALL CHECKS PASSED!
================================================================================
```

---

## 📚 Full Documentation

Siehe: `docs/ADMIN_DIAGNOSTICS_TOOLS.md`

---

## 🎊 Integration Status

✅ **Service Layer** - AdminDiagnosticsService  
✅ **Tool Functions** - 6 standalone functions  
✅ **Management Command** - Unified CLI  
✅ **Documentation** - Complete  
✅ **Testing** - Verified on writing_hub  

**Status:** Production Ready
