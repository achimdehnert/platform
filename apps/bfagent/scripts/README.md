# 📜 Scripts Directory

This directory contains utility scripts for development, maintenance, and automation tasks.

---

## 🎯 Quick Start

### Creating a New Script

1. **Copy the template:**
   ```bash
   cp scripts/_SCRIPT_TEMPLATE.py scripts/your_new_script.py
   ```

2. **Fill in the details:**
   - Script name and description
   - Usage instructions
   - Your imports and logic

3. **The template includes:**
   - ✅ UTF-8 encoding fix (required for Windows)
   - ✅ Proper error handling
   - ✅ Clean structure
   - ✅ Documentation

---

## 🔧 UTF-8 Encoding (CRITICAL!)

**ALL scripts must include this UTF-8 fix at the top:**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

# UTF-8 ENCODING FIX (REQUIRED FOR WINDOWS)
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass  # Silently fail if not supported
```

**Why?** Windows defaults to CP1252 encoding, which causes errors with:
- German umlauts (ä, ö, ü, ß)
- Unicode characters
- Emoji in output
- International characters

---

## 📂 Script Categories

### **Development Tools** (`scripts/tools/`)
- `model_consistency_checker.py` - Check model/view/form consistency
- `url_template_consistency_checker.py` - Validate URL patterns
- `visual_model_explorer.py` - Generate model visualizations
- `phase_agent_template_manager.py` - Manage Phase-Agent mappings

### **Database & Migrations**
- `validate_migrations.py` - Validate and fix migrations
- `register_missing_features_simple.py` - Register features in database

### **Analysis & Documentation**
- `screen_documentation_framework.py` - Generate screen documentation
- `template_url_validator.py` - Validate template URLs

---

## 🚀 Running Scripts

### **Standalone Scripts:**
```bash
python scripts/your_script.py
```

### **Django Shell Scripts:**
```bash
# Method 1: Direct execution
python manage.py shell
>>> exec(open('scripts/your_script.py', encoding='utf-8').read())

# Method 2: Pipe (Windows)
type scripts\your_script.py | python manage.py shell

# Method 3: Pipe (Linux/Mac)
cat scripts/your_script.py | python manage.py shell
```

---

## 📋 Script Structure Guidelines

### **1. Header Section**
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script Name - Brief Description

Purpose: What it does
Usage: How to run it
Requirements: Dependencies
"""
```

### **2. UTF-8 Fix (ALWAYS!)**
Include the UTF-8 encoding fix shown above.

### **3. Imports**
```python
import os
import sys
from pathlib import Path

# Django setup (if needed)
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models import YourModel
```

### **4. Configuration**
```python
# Constants
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
```

### **5. Main Logic**
```python
def main():
    """Main script logic"""
    print("=" * 80)
    print("SCRIPT NAME")
    print("=" * 80)
    
    try:
        # Your logic here
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 🎨 Output Formatting

Use these patterns for consistent output:

```python
# Section headers
print("=" * 80)
print("SECTION NAME")
print("=" * 80)

# Success messages
print(f"✅ {message}")

# Warnings
print(f"⚠️  {warning}")

# Errors
print(f"❌ {error}")

# Info
print(f"ℹ️  {info}")

# Progress
print(f"🔄 {progress}...")

# Skip
print(f"⏭️  SKIP: {reason}")
```

---

## 📖 File Operations

**ALWAYS use UTF-8 encoding for file operations:**

```python
# Reading
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Writing
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Using pathlib
from pathlib import Path
content = Path(file_path).read_text(encoding='utf-8')
Path(file_path).write_text(content, encoding='utf-8')
```

---

## 🧪 Testing Scripts

Before committing:

1. **Test on Windows** (if possible)
2. **Test with Unicode characters**
3. **Test error handling**
4. **Check output formatting**
5. **Verify cleanup (no leftover files)**

---

## 📚 Common Patterns

### **Database Operations**
```python
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models import ComponentRegistry

# Query
features = ComponentRegistry.objects.filter(status='proposed')

# Create
feature = ComponentRegistry.objects.create(
    name="FeatureName",
    # ... fields
)

# Update
feature.status = 'in_progress'
feature.save()
```

### **File Discovery**
```python
from pathlib import Path

# Find all Python files
python_files = list(Path('apps').rglob('*.py'))

# Find all templates
templates = list(Path('templates').rglob('*.html'))

# Filter files
md_files = [f for f in Path('docs').rglob('*.md') 
            if not f.name.startswith('_')]
```

### **Progress Tracking**
```python
from tqdm import tqdm

for item in tqdm(items, desc="Processing"):
    process(item)
```

---

## ⚠️ Common Pitfalls

### **1. Encoding Issues**
❌ **DON'T:**
```python
with open(file_path, 'r') as f:  # Uses system default (CP1252 on Windows)
```

✅ **DO:**
```python
with open(file_path, 'r', encoding='utf-8') as f:
```

### **2. Path Handling**
❌ **DON'T:**
```python
path = 'apps\\bfagent\\models.py'  # Breaks on Linux
```

✅ **DO:**
```python
from pathlib import Path
path = Path('apps') / 'bfagent' / 'models.py'
```

### **3. Error Handling**
❌ **DON'T:**
```python
def main():
    # No try/except
    risky_operation()
```

✅ **DO:**
```python
def main():
    try:
        risky_operation()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

---

## 📝 Documentation

Every script should have:

1. **Docstring** - What it does, how to use it
2. **Comments** - Explain complex logic
3. **Type hints** - For function parameters (optional but recommended)
4. **Examples** - In the docstring if needed

---

## 🔗 Related Documentation

- **Makefile:** `docs/MAKEFILE_DOCUMENTATION.md`
- **Development Process:** `docs/DEVELOPMENT_PROCESS_INDEX.md`
- **Architecture:** `docs/ARCHITECTURE_ROADMAP.md`

---

## 📞 Support

If you encounter issues:
1. Check the `_SCRIPT_TEMPLATE.py` for the latest pattern
2. Review existing scripts in `scripts/tools/`
3. Ensure UTF-8 encoding is properly configured
4. Test with sample data first

---

**Last Updated:** 2025-10-30
**Maintained by:** Development Team
