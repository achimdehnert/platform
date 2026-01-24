# Generic Prevention System - Project-Independent User Rules

## 🛡️ UNIVERSAL PROTECTION PROTOCOL

### Session Startup Rule
```bash
# ALWAYS run project validation first
python validate_core.py  # or project-specific validation script
```

### Component Protection Framework
**NEVER modify components marked as ✅ WORKING without validation failure:**
- Check project's `SOLUTION_STATUS.md` or equivalent documentation
- Run component-specific tests before any modifications
- Only proceed if validation explicitly fails

### Evidence-Based Development Pattern
1. **Check Status**: Review project documentation for working components
2. **Validate First**: Run validation scripts before touching code
3. **Focus Constraint**: Work only on verified broken/missing functionality
4. **Document Changes**: Update status documentation with test evidence

## 🧪 GENERIC VALIDATION PATTERN

### Project Structure Requirements
```
project-root/
├── validate_core.py           # Main validation script
├── SOLUTION_STATUS.md         # Component status documentation
├── debug_[component].py       # Component-specific tests
└── .windsurf/
    └── user-rules-prevention-system.md
```

### Validation Script Template
```python
#!/usr/bin/env python3
"""
🔒 Core Component Validation Script
Prevents re-solving already fixed issues
"""

def validate_component_a():
    """Validate Component A"""
    try:
        # Component-specific validation logic
        return {"status": "✅", "detail": "Working correctly"}
    except Exception as e:
        return {"status": "❌", "detail": f"Error: {e}"}

def main():
    components = {
        "Component A": validate_component_a,
        # Add more components as needed
    }

    results = {}
    all_working = True

    for name, validator in components.items():
        result = validator()
        results[name] = result
        print(f"{name}: {result['status']} {result['detail']}")

        if result['status'] == "❌":
            all_working = False

    if all_working:
        print("✅ ALL CORE COMPONENTS WORKING")
        return True
    else:
        print("❌ ISSUES FOUND - Fix these before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

## 🎯 FOCUS DISCIPLINE FRAMEWORK

### Current Issue Identification
- **Single Issue Focus**: Work on only ONE verified broken component
- **Root Cause Analysis**: Identify specific failure point
- **Test-Driven Fixes**: Validate fixes with automated tests

### Anti-Pattern Prevention
- ❌ Re-debugging working components
- ❌ Working on multiple issues simultaneously
- ❌ Modifying code without validation failure
- ❌ Ignoring existing documentation

## 📊 STATUS DOCUMENTATION TEMPLATE

```markdown
# Project Solution Status

## ✅ VERIFIED WORKING COMPONENTS
- **Component A**: Description of functionality
  - Test: `python test_component_a.py`
  - Evidence: Specific working behavior
  - Last Verified: Date

## 🎯 CURRENT FOCUS AREA
- **Issue**: Specific problem description
- **Location**: File/function where issue exists
- **Root Cause**: Technical explanation
- **Success Criteria**: How to verify fix

## 🚫 PROTECTION RULES
1. Run validation before ANY development
2. Never modify ✅ components without test failure
3. Focus only on verified broken functionality
4. Update documentation with evidence
```

## 🔧 IMPLEMENTATION CHECKLIST

### For New Projects
- [ ] Create `validate_core.py` with project-specific components
- [ ] Create `SOLUTION_STATUS.md` documentation
- [ ] Add component-specific debug scripts
- [ ] Set up `.windsurf/user-rules-prevention-system.md`
- [ ] Create memory-bank entry for prevention system

### For Existing Projects
- [ ] Audit working components and document status
- [ ] Create validation scripts for verified components
- [ ] Establish single-issue focus discipline
- [ ] Implement evidence-based development protocol

## 🚀 CROSS-PROJECT BENEFITS

- **Reduced Re-work**: Never re-solve already fixed issues
- **Faster Debugging**: Direct focus on actual problems
- **Stable Foundations**: Working components stay working
- **Clear Progress**: Visible advancement on real issues
- **Knowledge Transfer**: Reusable prevention patterns

This generic system can be adapted to any project by customizing the validation scripts and component definitions while maintaining the core protection principles.
