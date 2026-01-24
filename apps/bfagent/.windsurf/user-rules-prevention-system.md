# PowerPoint Translation Pipeline - User Rules for Prevention System

## 🔒 MANDATORY VALIDATION PROTOCOL

### Session Startup Rule
```bash
# ALWAYS run this first in every session
python validate_core.py
```

### Component Protection Rule
**NEVER modify these components without validation failure:**
- `core/translation_providers.py` (DeepL API) ✅ WORKING
- `core/analysis_database.py` (Database) ✅ WORKING
- `core/slide_analysis_engine.py` (Analysis) ✅ WORKING
- `core/advanced_shape_handlers.py` (Shape extraction) ✅ WORKING

### Evidence-Based Development Rule
1. Check `SOLUTION_STATUS.md` before ANY modification
2. Run component test before touching code
3. Only proceed if test fails
4. Document changes with test evidence

## 🎯 CURRENT FOCUS CONSTRAINT

**ONLY work on:** Formatting preservation in translated PPTX
**Specific issue:** Blue color and bold lost on "max. 5%", "max. 40,9%"
**Root cause:** Phase 3 of `mcp_self_healing_pipeline.py` clears formatting
**Test command:** Check output PPTX for preserved blue/bold formatting

## 🧪 VALIDATION COMMANDS

```bash
python validate_core.py          # All components
python debug_translation.py     # DeepL API only
python debug_database_shapes.py # Database only
python quick_analysis_test.py   # Analysis only
```

## 🚫 FORBIDDEN ACTIONS

- Re-debugging DeepL API (already working)
- Re-fixing database connections (already working)
- Re-solving shape extraction (already working)
- Working on multiple issues simultaneously
- Modifying working components without validation failure

## ✅ SUCCESS CRITERIA

Pipeline produces translated PPTX with:
- German text → English text ✅ (working)
- Blue color preserved on percentages 🎯 (focus area)
- Bold formatting preserved on percentages 🎯 (focus area)

This user rule system prevents re-solving already fixed issues and maintains focus on the actual remaining problem.
