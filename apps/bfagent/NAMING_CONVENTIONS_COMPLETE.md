# ✅ BF Agent - Naming Conventions Integration KOMPLETT

**Status:** 🟢 PRODUCTION READY  
**Datum:** 6. Dezember 2025  
**Integration:** 17 Apps erfolgreich integriert

---

## 📊 Übersicht

### Core & Base Apps (3)
| App | Display Name | Table Prefix | Class Prefix | Enforce |
|-----|--------------|--------------|--------------|---------|
| `core` | Core System | `core_` | `Core` | ✅ |
| `bfagent` | BF Agent | - | - | - |
| `bfagent_mcp` | BF Agent MCP | `mcp_` | `MCP` | ✅ |

### Hub Apps (4)
| App | Display Name | Table Prefix | Class Prefix | Enforce |
|-----|--------------|--------------|--------------|---------|
| `genagent` | GenAgent | `genagent_` | `GenAgent` | ✅ |
| `writing_hub` | Writing Hub | `writing_` | `Writing` | - |
| `control_center` | Control Center | - | - | - |
| `hub` | Hub | `hub_` | `Hub` | - |

### Specialized Apps (10)
| App | Display Name | Table Prefix | Class Prefix | Enforce |
|-----|--------------|--------------|--------------|---------|
| `medtrans` | Medical Translation | `medtrans_` | `MedTrans` | ✅ |
| `presentation_studio` | Presentation Studio | `presentation_studio_` | `PresentationStudio` | ✅ |
| `cad_analysis` | CAD Analysis | `cad_` | `CAD` | ✅ |
| `expert_hub` | Expert Hub | `expert_` | `Expert` | - |
| `checklist_system` | Checklist System | `checklist_` | `Checklist` | ✅ |
| `compliance_core` | Compliance Core | `compliance_` | `Compliance` | ✅ |
| `dsb` | DSGVO Hub | `dsb_` | `DSB` | ✅ |
| `api` | API | `api_` | `API` | - |
| `workflow_system` | Workflow System | `workflow_` | `Workflow` | ✅ |
| `image_generation` | Image Generation | `image_` | `Image` | - |

---

## 🛠️ Anwendung in MCP Tools

### 1. Alle Conventions auflisten
```python
# In Windsurf:
"Welche Naming Conventions gibt es?"
→ bfagent_list_naming_conventions()
```

**Output:**
```markdown
| App | Display Name | Table Prefix | Class Prefix |
|-----|--------------|--------------|--------------|
| api | API | api_ | API |
| bfagent | BF Agent | (none) | (none) |
| genagent | GenAgent | genagent_ | GenAgent |
...
```

### 2. Spezifische Convention abfragen
```python
# In Windsurf:
"Naming Convention für genagent?"
→ bfagent_get_naming_convention(app_label='genagent')
```

**Output:**
```markdown
# Naming Convention: GenAgent

**App Label:** genagent

## Prefixes
| Type | Prefix | Pattern |
|------|--------|---------|
| Table | genagent_ | genagent_{name} |
| Class | GenAgent | GenAgent{Name} |

## Examples
**Tables:** genagent_phases, genagent_actions
**Classes:** GenAgentPhase, GenAgentAction
```

### 3. Vor Refactoring prüfen
```python
# Automatisch in allen Refactoring Tools:
bfagent_start_refactor_session()
→ Prüft automatisch Naming Convention der Domain
→ Warnt bei Verstößen gegen enforce_convention
```

---

## 📝 Convention Patterns

### Strenge Conventions (enforce_convention = True)
Apps mit **strikter** Naming Convention, die **immer** befolgt werden muss:

- ✅ `core` → `core_*` / `Core*`
- ✅ `bfagent_mcp` → `mcp_*` / `MCP*`
- ✅ `genagent` → `genagent_*` / `GenAgent*`
- ✅ `medtrans` → `medtrans_*` / `MedTrans*`
- ✅ `presentation_studio` → `presentation_studio_*` / `PresentationStudio*`
- ✅ `cad_analysis` → `cad_*` / `CAD*`
- ✅ `checklist_system` → `checklist_*` / `Checklist*`
- ✅ `compliance_core` → `compliance_*` / `Compliance*`
- ✅ `dsb` → `dsb_*` / `DSB*`
- ✅ `workflow_system` → `workflow_*` / `Workflow*`

### Flexible Conventions (enforce_convention = False)
Apps mit **flexibler** Convention, Präfix optional:

- 🔵 `bfagent` → Keine Präfixe (Legacy-App)
- 🔵 `control_center` → Mixed (navigation_, workflow_, project_types, etc.)
- 🔵 `writing_hub` → `writing_*` optional
- 🔵 `expert_hub` → `expert_*` optional
- 🔵 `hub` → `hub_*` optional
- 🔵 `api` → `api_*` optional
- 🔵 `image_generation` → `image_*` optional

---

## 🎯 Best Practices

### Bei neuen Models:
1. **Prüfe Convention:**
   ```python
   result = bfagent_get_naming_convention(app_label='deine_app')
   ```

2. **Befolge Pattern:**
   - Table: `{prefix}{name}` (z.B. `mcp_domain_config`)
   - Class: `{Prefix}{Name}` (z.B. `MCPDomainConfig`)
   - File: Siehe `file_pattern` in Convention

3. **Enforce beachten:**
   - Bei `enforce_convention=True`: **MUSS** befolgt werden
   - Bei `enforce_convention=False`: **SOLLTE** befolgt werden

### Bei Refactoring:
1. **Vor Änderungen:**
   ```python
   bfagent_start_refactor_session(domain_id='genagent', components=['model'])
   ```

2. **Session trackt automatisch:**
   - Convention Violations
   - Naming Pattern Abweichungen
   - Protected Path Checks

3. **Nach Änderungen:**
   ```python
   bfagent_end_refactor_session(session_id=42)
   ```

---

## 📦 Dateien

### Erstellung
- `INSERT_NAMING_CONVENTIONS.sql` - SQL Inserts für alle 17 Apps
- `apply_naming_conventions.py` - Python Script zum Anwenden

### Anwendung
```bash
# Conventions in DB schreiben:
python apply_naming_conventions.py

# Testen:
python test_refactor_tools_quick.py
```

### Datenbank
- **Tabelle:** `core_naming_convention`
- **Location:** `bfagent.db`
- **Rows:** 17 (Stand: 2025-12-06)

---

## 🚀 Integration Status

| Komponente | Status | Details |
|-----------|--------|---------|
| **SQL Script** | ✅ READY | 17 Apps dokumentiert |
| **Python Applicator** | ✅ READY | Anwendung erfolgreich |
| **Database** | ✅ READY | 17 Rows in `core_naming_convention` |
| **MCP Tools** | ✅ WORKING | `list_naming_conventions()` ✓ |
| **MCP Tools** | ✅ WORKING | `get_naming_convention()` ✓ |
| **Documentation** | ✅ COMPLETE | README, Examples, Usage |

---

## 🎓 Beispiele

### Beispiel 1: GenAgent Model erstellen
```python
# Convention prüfen:
→ Table Prefix: genagent_
→ Class Prefix: GenAgent

# Korrekt:
class GenAgentWorkflow(models.Model):
    class Meta:
        db_table = 'genagent_workflows'  # ✅ Pattern befolgt

# Falsch:
class Workflow(models.Model):
    class Meta:
        db_table = 'workflows'  # ❌ Prefix fehlt!
```

### Beispiel 2: MCP Model erstellen
```python
# Convention: mcp_ / MCP (strict!)
# Korrekt:
class MCPDomainConfig(models.Model):
    class Meta:
        db_table = 'mcp_domain_config'  # ✅

# Falsch:
class DomainConfig(models.Model):
    class Meta:
        db_table = 'domain_config'  # ❌ MCP Präfix fehlt!
```

### Beispiel 3: BFAgent Model (flexible)
```python
# Convention: Kein Präfix (Legacy-App)
# Beides OK:
class BookProject(models.Model):
    class Meta:
        db_table = 'book_projects'  # ✅

class Agent(models.Model):
    class Meta:
        db_table = 'agents'  # ✅
```

---

## 💡 Nächste Schritte

1. **MCP Server starten:**
   ```bash
   python -m bfagent_mcp.server --debug
   ```

2. **In Windsurf verwenden:**
   ```
   "Zeige mir die Naming Convention für medtrans"
   → bfagent_get_naming_convention(app_label='medtrans')
   ```

3. **Bei neuem Model:**
   ```
   "Welche Convention gilt für meine neue App xyz?"
   → Prüft automatisch ob Convention existiert
   → Falls nicht: Legt nahe, eine anzulegen
   ```

---

**Erstellt:** 6. Dezember 2025  
**Status:** ✅ PRODUCTION READY  
**Version:** 1.0.0
