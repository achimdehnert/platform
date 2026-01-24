# Multi-Phase CrewAI Develop/Stable Workflow Rules

## 🚨 **CRITICAL WORKFLOW RULES**


### **Development Phase Rules**
1. **ALL changes in `develop/` ONLY**
3. **Environment auto-detected from folder path**
4. **Clean production-ready naming from start**
5. **No "experimental" terminology in code**

### **Transition Process**
```bash
# When USER says "we are stable now":
1. Copy: develop/ → mcp_tools_stable/
2. Environment automatically switches to "production"
3. No code changes needed - folder path handles everything
4. Production app (Port 8501) uses stable version
```

### **Code Architecture**
```

### **Environment Behavior Differences**
| Feature | Development | Production |
|---------|-------------|------------|
| Logging | `[DEV]` prefix | `[PROD]` prefix |
| Verbosity | Verbose mode ON | Quiet mode |
| Agent Context | "(Development)" suffix | Clean names |
| Testing | Full debug output | Minimal output |
| Error Handling | Detailed errors | Clean errors |

### **File Naming Convention**
- ✅ `CrewAIMCPHealingTeam` - Clean, production-ready
- ✅ `heal_before_download()` - Professional method names
- ✅ `MCPHealingTool` - No environment suffixes
- ❌ `CrewAIMCPDevelopmentTeam` - Environment in name
- ❌ `experimental_heal_method()` - Environment in method

### **Streamlit Integration**


## 🎯 **Key Benefits**

- **Zero Refactoring** - Copy files when ready
- **Automatic Environment Detection** - Folder path determines behavior
- **Clean Production Code** - No development artifacts
- **Safe Development** - Production never touched during development
- **Seamless Integration** - Same API surface in both environments
- **Multi-Phase Intelligence** - Specialized agents for each translation phase
- **Complete Pipeline Orchestration** - Analysis → Translation → Healing
