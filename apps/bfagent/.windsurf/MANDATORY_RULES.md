# MANDATORY RULES - ALWAYS ENFORCED

## 🚨 CRITICAL ENFORCEMENT RULES

### Rule Priority System
1. **MANDATORY** - Must be followed in every session
2. **ENFORCED** - Automatically checked and validated
3. **TRACKED** - Progress monitored and reported

### MANDATORY Rules (Session Start)
- **ALWAYS** read ALL @ prefixed files in memory-bank before ANY code generation
- **ALWAYS** validate project context from @project-context.md
- **ALWAYS** check @prevention-system.md for current focus areas
- **ALWAYS** run validation scripts before modifying working components
- **ALWAYS** update progress tracking after completing features

### ENFORCED Code Standards
- **Maximum function length**: 50 lines
- **Maximum file length**: 500 lines
- **Type hints required**: All functions and variables
- **Test coverage minimum**: 80%
- **Documentation required**: Google-style docstrings

### TRACKED Development Flow
- **Read context files** → **Validate understanding** → **Implement** → **Test** → **Document**
- **Never skip validation** for components marked as ✅ WORKING
- **Always use todo_list** for task planning and progress tracking
- **Update memory-bank** with architectural decisions

## 🛡️ PREVENTION SYSTEM INTEGRATION

### Before ANY Development Work
```bash
# 1. Validate core components
python validate_core.py

# 2. Check current focus from prevention system
cat memory-bank/@prevention-system.md

# 3. Verify no working components will be modified
grep -r "✅ WORKING" memory-bank/
```

### Session Initialization Checklist
- [ ] Read @project-context.md
- [ ] Read @prevention-system.md
- [ ] Read @architecture.md
- [ ] Check current sprint goals
- [ ] Validate core components
- [ ] Create todo_list for session

## 🎯 FOCUS DISCIPLINE

### Current Priority Areas (Auto-Updated)
- **Primary Focus**: Agent Management CRUD with st.data_editor
- **Secondary Focus**: Navigation button fixes
- **Blocked Areas**: Components marked as ✅ WORKING

### Anti-Patterns to Avoid
- Modifying working components without validation failure
- Working on multiple unrelated issues simultaneously
- Skipping context validation at session start
- Implementing without reading prevention rules

---
*This file is automatically loaded by Windsurf AI at session start*
*Last Updated: Auto-timestamp*
