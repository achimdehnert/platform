# Model Splitting Migration Guide

## 🎯 Goal
Refactor monolithic `models.py` (4000+ lines) into modular structure

## 📋 Prerequisites
- ✅ Git repository (for rollback)
- ✅ Virtual environment activated
- ✅ All tests passing
- ✅ Database backup

---

## 🚀 Step-by-Step Migration

### Step 1: Backup Everything (2 min)
```bash
# Create backup branch
git checkout -b feature/split-models
git add .
git commit -m "Pre-split backup"

# Backup database
python manage.py dumpdata > backup_before_split.json
```

### Step 2: Run Automated Split (5 min)
```bash
# Run the splitter script
python split_models.py apps/bfagent/models.py

# You should see:
# ✅ Created apps/bfagent/models/base.py with 2 models
# ✅ Created apps/bfagent/models/books.py with 5 models
# ... etc
```

### Step 3: Verify Structure (2 min)
```bash
# Check new structure
tree apps/bfagent/models/

# Expected output:
# apps/bfagent/models/
# ├── __init__.py
# ├── base.py
# ├── books.py
# ├── characters.py
# ├── agents.py
# ├── prompts.py
# ├── workflows.py
# ├── fields.py
# ├── enrichment.py
# ├── llms.py
# ├── monitoring.py
# ├── master_data.py
# ├── illustration.py
# └── story_engine.py
```

### Step 4: Handle Missing Models (10 min)

The script might not catch all models. Check for missing ones:

```bash
# Find models not in MODEL_GROUPS
grep "^class.*models.Model" apps/bfagent/models.py.backup | \
  awk '{print $2}' | \
  sed 's/(.*//g' | \
  sort > all_models.txt

# Compare with split models
grep "^class" apps/bfagent/models/*.py | \
  awk -F: '{print $2}' | \
  awk '{print $2}' | \
  sed 's/(.*//g' | \
  sort > split_models.txt

# Show difference
comm -23 all_models.txt split_models.txt
```

If models are missing, manually add them to appropriate files.

### Step 5: Fix Import Paths (5 min)

Some models might have imports from existing separate files:

```python
# apps/bfagent/models/handlers.py
"""
Handler System Models
Re-imported from existing models_handlers.py for compatibility
"""

from ..models_handlers import (
    Handler,
    ActionHandler,
    HandlerExecution,
)

__all__ = ['Handler', 'ActionHandler', 'HandlerExecution']
```

### Step 6: Update Admin (5 min)

If admin.py imports models directly:

```python
# Before (admin.py)
from .models import BookProjects, BookChapters

# After (no change needed if using from .models import *)
from .models import BookProjects, BookChapters  # Still works!
```

### Step 7: Verify No Breaking Changes (5 min)

Django should detect this as "no changes":

```bash
# This should output "No changes detected"
python manage.py makemigrations

# If it detects changes, something went wrong!
# Rollback and investigate
```

### Step 8: Run Tests (10 min)
```bash
# Run all tests
python manage.py test apps.bfagent

# Check imports in shell
python manage.py shell
>>> from apps.bfagent.models import BookProjects
>>> print(BookProjects._meta.db_table)
'book_projects'  # Should still be same table name
```

### Step 9: Test Imports Everywhere (5 min)

Check views, serializers, etc.:

```bash
# Search for direct imports
grep -r "from apps.bfagent.models import" apps/

# All should still work because models/__init__.py exports everything
```

### Step 10: Cleanup (2 min)

If everything works:

```bash
# Delete backup
rm apps/bfagent/models.py.backup

# Commit
git add .
git commit -m "Refactor: Split monolithic models.py into modular structure

- Created models/ directory with 13 domain-specific files
- All imports remain backward compatible
- No database migrations needed
- All tests passing"

# Merge to main
git checkout main
git merge feature/split-models
```

---

## 🐛 Troubleshooting

### Issue: "No module named models.base"
**Solution:**
```python
# Check models/__init__.py has proper imports
from .base import CRUDConfigBase, CRUDConfigMixin
```

### Issue: Circular import errors
**Solution:**
```python
# Use TYPE_CHECKING for forward references
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .books import BookProjects

class Character(models.Model):
    project: 'BookProjects' = models.ForeignKey('BookProjects', ...)
```

### Issue: Admin not finding models
**Solution:**
```python
# admin.py
from .models import BookProjects  # This should work!

# If not, try:
from .models.books import BookProjects
```

---

## 📊 Success Metrics

✅ **Zero database migrations** (models just moved, not changed)
✅ **All imports still work** (backward compatibility via __init__.py)
✅ **All tests passing**
✅ **Code is now 13 files instead of 1**

---

## 🎯 Next Steps (Optional)

### Option A: Keep as-is
You're done! Much more maintainable now.

### Option B: Further split into separate apps (Future)

If you want to go further:

```bash
# Move story_engine to separate app
python manage.py startapp story_engine

# Move models/story_engine.py → story_engine/models.py
mv apps/bfagent/models/story_engine.py apps/story_engine/models.py

# Update settings.py
INSTALLED_APPS = [
    ...
    'apps.bfagent',
    'apps.story_engine',  # New app!
]
```

---

## 📚 References

- [Django Best Practices - Model Organization](https://docs.djangoproject.com/en/5.0/topics/db/models/#organizing-models-in-a-package)
- [Real Python - Django Models](https://realpython.com/django-model-package/)
- [Two Scoops of Django - Chapter 5: Models](https://www.feldroy.com/books/two-scoops-of-django-3-x)

---

## ⏱️ Total Time: ~1 hour

Most of it is verification and testing. The actual split takes 5 minutes!
