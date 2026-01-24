# 🚨 ABSOLUTE PRIORITY: FIX TOOLS FIRST, NOT GENERATED CODE

## THE GOLDEN RULE
**NEVER fix generated code manually. ALWAYS fix the generator first.**

## MANDATORY WORKFLOW

### When Error in Generated File:
1. **STOP!** → Don't fix the file directly
2. **Find the generator** that created it
3. **Fix the generator FIRST** → Root cause solution
4. **Sichern**: Custom Code Blocks extrahieren (# CUSTOM_CODE_START/END)
5. **Löschen**: Generierte Dateien/Sections komplett entfernen
6. **Regenerieren**: Generator mit Fix neu ausführen
7. **Integrieren**: Custom Code in neue Dateien einfügen
8. **Testen**: Alle Funktionalität validieren

### ❌ NEVER DO THIS:
- Don't fix generated files directly (even with MultiEdit)
- Don't keep old buggy generated code
- Don't skip custom code extraction
- Don't regenerate before fixing generator

### ✅ CORRECT APPROACH:
**Fix Generator → Clean Slate → Regenerate → Re-integrate Custom**

## WHY THIS RULE EXISTS
- ✅ One generator fix → All future generations fixed
- ✅ Sustainable, scalable solution
- ✅ No recurring bugs
- ✅ Framework improves continuously
- ✅ Custom code preserved safely
- ❌ Manual fixes = Technical debt
- ❌ Same bug reappears next generation
- ❌ Inconsistency between generated files

## DETECTION TRIGGERS

### Immediate Generator Fix Required:
1. **File contains "AUTO-GENERATED" comment** → Fix generator!
2. **File created by `consistency_framework.py`** → Fix generator!
3. **Same error repeats** → Fix source tool!
4. **Import errors in views/forms/templates** → Fix ViewGenerator/FormGenerator/TemplateGenerator!
5. **Field name mismatches** → Fix FormGenerator field detection!
6. **URL pattern errors** → Fix URLPatternAnalyzer!

## EXAMPLES - WRONG APPROACH ❌

### Import Error Example:
```python
# ❌ WRONG: Manually fix apps/bfagent/views/main_views.py
from bfagent.models import Llms  # Fix this line manually
```

**Why wrong?** Next generation will have same error!

### Form Field Error Example:
```python
# ❌ WRONG: Manually fix apps/bfagent/forms.py
fields = ['llm_model']  # Change to 'llm_model_id' manually
```

**Why wrong?** FormGenerator will generate wrong field again!

## EXAMPLES - CORRECT APPROACH ✅

### Import Error Example:
```python
# ✅ CORRECT: Fix scripts/consistency_framework.py Line 584-585
# OLD:
from {analysis.app_name}.models import {model_name}

# NEW:
from ..models import {model_name}

# Then regenerate:
python scripts/consistency_framework.py generate Llms --components views
```

**Result:** All future view generations have correct imports!

### Form Field Error Example:
```python
# ✅ CORRECT: Fix FormGenerator field detection logic
# Add ForeignKey detection to automatically append '_id'
# Then regenerate:
python scripts/consistency_framework.py generate Llms --components forms
```

**Result:** All future form generations have correct field names!

## BF AGENT GENERATORS TO KNOW

### Location: `scripts/consistency_framework.py`

**Key Generators:**
- **FormGenerator** (Lines 430-555): Generates form mixins with field lists
- **ViewGenerator** (Lines 559-766): Generates CBVs (Create, Edit, Delete, List, Detail)
- **TemplateGenerator** (Lines 769-1100): Generates HTML templates
- **URLPatternAnalyzer** (Lines 250-322): Generates URL patterns
- **TestGenerator**: Generates test cases

### Common Generator Bugs:

1. **Import Paths** (Line 584-585)
   - Bug: Absolute imports (`from bfagent.models`)
   - Fix: Relative imports (`from ..models`)

2. **Field Names** (Line 480-520)
   - Bug: Missing ForeignKey `_id` suffix
   - Fix: Auto-detect ForeignKey and append `_id`

3. **Template Paths** (Line 591)
   - Bug: Wrong app name in template path
   - Fix: Use `analysis.app_name` correctly

4. **URL Patterns** (Line 647)
   - Bug: Inconsistent naming (dash vs underscore)
   - Fix: Use URLPattern enum consistently

## QUICK REFERENCE

### When you see error in:
- `apps/bfagent/views/main_views.py` → Fix **ViewGenerator** Line 559-766
- `apps/bfagent/utils/form_mixins.py` → Fix **FormGenerator** Line 430-555
- `apps/bfagent/templates/` → Fix **TemplateGenerator** Line 769-1100
- `apps/bfagent/urls.py` (generated patterns) → Fix **URLPatternAnalyzer** Line 250-322

### Generation Command:
```bash
python scripts/consistency_framework.py generate <ModelName> --components <type>

# Examples:
python scripts/consistency_framework.py generate Llms --components views
python scripts/consistency_framework.py generate Agents --components forms
python scripts/consistency_framework.py generate Llms --force  # Regenerate all
```

### Analysis Command:
```bash
python scripts/consistency_framework.py analyze <ModelName>
```

## USER'S DIRECT INSTRUCTION
> "Kannst du dir nicht merken, welche Fehler bereits vorkamen und diese dann automatisch im Generator vermeiden?"

**ANSWER: YES! That's exactly what this rule is about.**

## ENFORCEMENT
This rule is in:
1. ✅ `.windsurf/.windsurfrules` (Line 1-40)
2. ✅ `memory-bank/@ALWAYS_READ/@RULE_1_FIX_TOOLS_FIRST.md` (this file)
3. ✅ User-defined rules in settings

**This is MANDATORY, not optional.**

---

**Last Updated:** 2025-10-06
**Priority:** HIGHEST
**Status:** ACTIVE & ENFORCED
