# 🔄 BF Agent - Parallel Apps Root Strategy
## Zero-Downtime Migration mit paralleler Struktur

**Version:** 1.0  
**Datum:** 2025-11-05  
**Status:** ⭐ Recommended Approach

---

## 🎯 Executive Summary

**Problem:** Migration zur neuen Architektur ist riskant und könnte Produktionsbetrieb stören.

**Lösung:** Parallele `apps/` (alt) und `apps_v2/` (neu) Struktur für schrittweise, risikolose Migration.

**Ergebnis:** 
- ✅ Zero Downtime
- ✅ Easy Rollback  
- ✅ Gradual Testing
- ✅ Team kann parallel arbeiten

---

## 📊 Vorteile der Parallel-Strategie

| Vorteil | Beschreibung |
|---------|--------------|
| **Zero Risk** | Alte Apps bleiben 100% funktionsfähig |
| **Zero Downtime** | Keine Sekunde Produktionsausfall |
| **Gradual Migration** | App für App migrieren und testen |
| **Easy Rollback** | Environment Variable = instant Rollback |
| **A/B Testing** | Neue Struktur mit echten Usern testen |
| **Team Onboarding** | Parallel arbeiten in beiden Versionen |

**Fazit:** Diese Strategie ist der professionelle Standard für große Migrations-Projekte! ✅

---

## 📁 Ziel-Struktur

```
bfagent/
│
├── apps/                          # ❌ OLD (funktioniert weiter)
│   ├── books/
│   ├── features/
│   └── bugs/
│
├── apps_v2/                       # ✅ NEW (neue Architektur)
│   ├── core/                      # Framework
│   ├── domains/                   # Domain Apps
│   │   ├── books/
│   │   ├── science/
│   │   └── forensics/
│   └── shared/                    # Shared Components
│
├── config/                        # SHARED (beide nutzen)
│   └── settings/
│       └── base.py                # Beide App-Roots konfiguriert
│
└── management/                    # Migration Tools
    └── commands/
        └── migrate_to_v2.py
```

---

## 🚀 Quick Start

### Step 1: Structure erstellen

```bash
# Create apps_v2
mkdir -p apps_v2/{core,domains,shared}
mkdir -p apps_v2/core/{handlers,workflows,llm,events,features}
mkdir -p apps_v2/domains/{books,science,forensics}
mkdir -p apps_v2/shared/{handlers,templates,static}

# Create __init__.py files
find apps_v2 -type d -exec touch {}/__init__.py \;

echo "✅ apps_v2 structure created"
```

### Step 2: Django Settings anpassen

```python
# config/settings/base.py

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Add both app roots
sys.path.insert(0, str(BASE_DIR / 'apps'))      # Old
sys.path.insert(0, str(BASE_DIR / 'apps_v2'))   # New

INSTALLED_APPS = [
    'django.contrib.admin',
    # ...
    
    # OLD APPS
    'apps.books',
    'apps.features',
    
    # NEW APPS (parallel)
    'apps_v2.core',
    'apps_v2.domains.books',
    'apps_v2.shared',
]

# Feature flag
USE_V2_BOOKS = os.environ.get('USE_V2_BOOKS', 'false').lower() == 'true'
```

### Step 3: URL Routing

```python
# config/urls.py

from django.conf import settings

if settings.USE_V2_BOOKS:
    urlpatterns += [
        path('books/', include('apps_v2.domains.books.urls')),
    ]
else:
    urlpatterns += [
        path('books/', include('apps.books.urls')),
    ]
```

---

## 📋 Migration Workflow

### Phase 1: Core Framework (Woche 1)

```python
# apps_v2/core/handlers/base.py

from abc import ABC, abstractmethod

class BaseHandler(ABC):
    @abstractmethod
    def process(self, input_data, config):
        pass
    
    def handle(self, input_data, config):
        return self.process(input_data, config)
```

### Phase 2: Erste Domain (Woche 2)

```bash
# Migration command
python manage.py migrate_to_v2 books --dry-run
python manage.py migrate_to_v2 books

# Verify
tree apps_v2/domains/books/
pytest apps_v2/domains/books/tests/
```

### Phase 3: Testing (Woche 3)

```bash
# Compare outputs
python manage.py compare_outputs SaveTheCatOutlineHandler

# Load testing
locust -f tests/load/books_test.py
```

### Phase 4: Deployment (Woche 4)

```bash
# Gradual rollout
export USE_V2_BOOKS=true  # 10% traffic
# Monitor
# Increase to 100%
```

---

## 🔄 Rollback Strategy

```bash
# If anything goes wrong:
export USE_V2_BOOKS=false
systemctl restart bfagent

# Instant rollback to v1 ✅
```

---

## 📊 Success Metrics

```yaml
Technical:
  - Tests passing: >95%
  - Performance: ±5% vs v1
  - Zero downtime: ✅

Business:
  - User complaints: <2%
  - Time per domain: 1-2 weeks
```

---

## ✅ Empfehlung

**Definitiv JA zur Parallel Apps Root Strategie!**

### Next Steps:

1. Lies [CONVENTIONS_AND_STRUCTURE.md](CONVENTIONS_AND_STRUCTURE.md)
2. Erstelle `apps_v2/` Struktur
3. Migriere `core/` Framework
4. Migriere erste Domain (`books`)
5. Test & Deploy
6. Wiederhole für weitere Domains

**Viel Erfolg! 🚀**
