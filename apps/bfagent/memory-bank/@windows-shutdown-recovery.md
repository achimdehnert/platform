# @windows-shutdown-recovery.md - Safe Restart Protocol

## 🔄 Post-Windows-Shutdown Recovery Protocol

### Immediate Actions After System Restart

#### 1. Environment Validation
```powershell
# Navigate to project root
cd C:\Users\achim\github\crime-noir

# Check git repository status
git status
git log --oneline -5

# Verify critical files exist
ls .windsurf\MANDATORY_RULES.md
ls memory-bank\@ALWAYS_READ\
```

#### 2. Rule System Activation
- **Auto-load**: MANDATORY_RULES.md should load automatically
- **Verify**: AUTO_LOAD_RULES.md enforcement active
- **Check**: @ALWAYS_READ folder accessibility
- **Validate**: Session initialization protocol

#### 3. Memory Bank Integrity Check
```text
Required Files:
✓ memory-bank/@ALWAYS_READ/@current-focus.md
✓ memory-bank/@ALWAYS_READ/@session-checklist.md
✓ memory-bank/@project-context.md
✓ memory-bank/@architecture.md
✓ .windsurf/MANDATORY_RULES.md
✓ .windsurf/AUTO_LOAD_RULES.md
```

#### 4. Development Environment Recovery
```powershell
# Test database integrity
ls bookfactory.db*

# Verify Streamlit functionality
cd develop
python -m streamlit run app/main.py --server.port 8501

# Test Agent Management access
python -m streamlit run run_agents.py --server.port 8502
```

#### 5. Session State Restoration
- Load current focus priorities from @current-focus.md
- Review active tasks and blocked components
- Verify working components marked as ✅ WORKING
- Check for any interrupted development work

### Recovery Validation Checklist

#### Critical Systems
- [ ] Git repository intact and accessible
- [ ] Database files present and uncorrupted
- [ ] Streamlit applications launch successfully
- [ ] Agent Management system functional
- [ ] Memory bank hierarchy preserved

#### Rule Enforcement
- [ ] MANDATORY_RULES.md auto-loaded
- [ ] Session initialization protocol active
- [ ] Focus discipline system operational
- [ ] Code quality gates functional
- [ ] Prevention system active

#### Data Integrity
- [ ] No missing critical files
- [ ] No corrupted configuration files
- [ ] Session state recoverable
- [ ] Development context preserved
- [ ] Working components protected

### Emergency Recovery Commands

```powershell
# If Streamlit fails to start
pip install --upgrade streamlit
pip install -r develop/requirements.txt

# If database issues
copy bookfactory.db.backup bookfactory.db

# If git issues
git fsck
git status --porcelain

# If memory bank corruption
git checkout HEAD -- memory-bank/
```

### Success Criteria
✅ All mandatory rules loaded and enforced
✅ Memory bank structure intact
✅ Development environment functional
✅ Agent Management system accessible
✅ No data loss or corruption detected
✅ Session context fully restored

### Post-Recovery Actions
1. Update @current-focus.md with any new priorities
2. Mark recovery completion in session log
3. Resume development from last known good state
4. Validate all working components still functional
