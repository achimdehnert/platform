# @session-checklist.md - Session Initialization Protocol

## 🔄 SESSION START CHECKLIST

### Phase 1: Context Loading (MANDATORY)
- [ ] Read @project-context.md - Project overview and current phase
- [ ] Read @current-focus.md - Active development priorities
- [ ] Read @prevention-system.md - Protected components and focus areas
- [ ] Read @architecture.md - Technical architecture overview

### Phase 2: Rule Activation (ENFORCED)
- [ ] Load MANDATORY_RULES.md - Core enforcement rules
- [ ] Activate code quality standards (max 50 lines/function, 500 lines/file)
- [ ] Enable type hint requirements
- [ ] Set test coverage minimum (80%)

### Phase 3: Validation (TRACKED)
- [ ] Verify no ✅ WORKING components will be modified
- [ ] Confirm current focus area alignment
- [ ] Check for any blocking issues
- [ ] Validate development environment

### Phase 4: Planning (REQUIRED)
- [ ] Create todo_list for session objectives
- [ ] Break down tasks into manageable chunks
- [ ] Set priority levels (high/medium/low)
- [ ] Estimate completion status

## 🎯 FOCUS VALIDATION

### Current Priority Check
```
Primary Focus: [Auto-populated from @current-focus.md]
Secondary Focus: [Auto-populated from @current-focus.md]
Blocked Areas: [Auto-populated from @prevention-system.md]
```

### Anti-Pattern Prevention
- ❌ No work on multiple unrelated issues
- ❌ No modification of ✅ WORKING components without validation failure
- ❌ No code generation without context validation
- ❌ No skipping of session initialization protocol

## 📊 SESSION SUCCESS CRITERIA

### Must Complete
- [ ] All context files read and understood
- [ ] Todo_list created and maintained
- [ ] Progress tracked and updated
- [ ] Rules consistently applied

### Quality Gates
- [ ] Function length ≤ 50 lines
- [ ] File length ≤ 500 lines
- [ ] Type hints on all functions
- [ ] Documentation for public APIs

### Session End Protocol
- [ ] Update @current-focus.md with progress
- [ ] Mark completed todos
- [ ] Document any architectural decisions
- [ ] Archive completed work if needed

---
*This checklist ensures consistent session initialization and rule application*
*Auto-loaded at every session start*
