# 🎯 LIVING RULE: Model Extension Process

**Status:** Active & Continuously Improving  
**Version:** 1.0.0  
**Last Updated:** 2025-10-08  
**Type:** Mandatory Development Process

---

## 🔥 CRITICAL: ALWAYS FOLLOW THIS PROCESS!

Diese Checkliste ist **MANDATORY** für jede Model-Erweiterung und wird kontinuierlich optimiert basierend auf Erfahrungen.

---

## 🚨 META-REGEL: ROOT CAUSE OVER QUICK FIX! (MANDATORY!)

**NIEMALS Quick Fixes - IMMER Probleme lösen!**

### **Philosophie:**
```
Fehler passiert → Root Cause analysieren
Root Cause → Tool-Gap identifizieren
Tool-Gap → Tool erweitern/erstellen
Tool erweitert → Fehler zukünftig verhindert

→ PREVENTION statt REACTION!
```

### **Bei JEDEM Fehler fragen:**

1. **❓ Ist das ein Tool-Problem?**
   ```
   Fehler: Field fehlt in Form
   Tool-Gap: Model Consistency Checker erkennt es nicht
   Solution: Tool erweitern um form_layout Validation
   → Tool verbessert, Fehler zukünftig automatisch erkannt!
   ```

2. **❓ Können wir das automatisieren?**
   ```
   Fehler: Vergessene Migration
   Tool-Gap: Keine Pre-Check vor Generator
   Solution: Migration Validator in Workflow integrieren
   → Automatisch geprüft, Fehler unmöglich!
   ```

3. **❓ Ist das ein Prozess-Problem?**
   ```
   Fehler: ForeignKey Reihenfolge falsch
   Tool-Gap: Keine automatische Dependency-Erkennung
   Solution: Model Dependency Analyzer erstellen
   → Tool schlägt korrekte Reihenfolge vor!
   ```

### **MANDATORY Workflow:**
```python
if error_occurs:
    # SCHRITT 1: Root Cause Analysis
    root_cause = analyze_why_it_happened()
    
    # SCHRITT 2: Tool Gap Analysis
    if can_be_prevented_by_tool():
        # SCHRITT 3: Tool Enhancement
        enhance_or_create_tool()
        
        # SCHRITT 4: Process Update
        add_tool_to_checklist()
        version_bump_process()
        
        # SCHRITT 5: Documentation
        document_tool_enhancement()
        
        return "Problem solved - won't happen again!"
    
    else:
        # SCHRITT 3: Process Improvement
        add_to_checklist()
        update_quick_reference()
        
        return "Process improved - better awareness!"
```

### **Beispiele aus der Praxis:**

#### **❌ FALSCH - Quick Fix:**
```
Problem: Field fehlt in Form
Quick Fix: Manuell hinzufügen
Result: Nächstes Mal wieder vergessen!
```

#### **✅ RICHTIG - Problem Lösung:**
```
Problem: Field fehlt in Form
Root Cause: Keine automatische Validation
Tool Enhancement: Model Consistency Checker V3 erstellt
Result: Tool erkennt missing fields automatisch!
Prevention: Kann nie wieder passieren!
```

### **Tool Enhancement Pipeline:**

```
Fehler erkannt
    ↓
Root Cause Analysis
    ↓
Tool Gap identifiziert
    ↓
Tool Enhancement Proposal
    ↓
Implementation Priority
    ↓
Tool erweitert/erstellt
    ↓
Process Integration
    ↓
Documentation Update
    ↓
Problem gelöst - Prevention aktiviert!
```

---

## ⚡ QUICK CHECKLIST (Print & Pin!)

```
PRE-FLIGHT VALIDATION: ⚠️ MANDATORY FIRST!
□ TOOL: System Health Check → python manage.py control (Status Check)
□ TOOL: Check Migration History → ls migrations/ | grep model_name
□ TOOL: Check Database State → python manage.py dbshell
□ TOOL: Check Model Exists → grep "class ModelName" models.py
□ TOOL: Verify Tools Available:
  □ Model Consistency Checker V3 - exists?
  □ Migration Fixer - works?
  □ Auto Compliance Fixer - ready?
  □ Control Panel - accessible?

PRE-IMPLEMENTATION:
□ Use Case definiert
□ Datenmodell skizziert
□ Dependencies identifiziert (Reihenfolge!)
□ Migration Strategy geplant
□ **PRE-FLIGHT VALIDATION PASSED** ← MANDATORY!

IMPLEMENTATION:
□ Models.py: Korrekte Position (nach Dependencies)
□ ForeignKeys: String/Direct korrekt
□ Meta Class: managed=True, db_table, ordering
□ __str__: Implementiert
□ CRUDConfig: VOLLSTÄNDIG
  □ list_display (5-7 Felder)
  □ list_filters
  □ search_fields  
  □ form_layout (ALLE Felder! ← KRITISCH)
  □ field_config (textarea, readonly)
□ crud_config.yaml: Eintrag hinzugefügt
□ Imports: Alle vorhanden

PRE-VALIDATION:
□ TOOL: Syntax Check → python -m py_compile models.py
□ TOOL: Model Consistency → model_consistency_checker_v3.py
□ Dry Run: makemigrations --dry-run

MIGRATION:
□ Migration erstellt
□ TOOL: Migration Validate → fix_migrations.py diagnose
□ Migration applied
□ TOOL: Migration Verify → fix_migrations.py verify
□ Rollback Test

CRUD GENERATION:
□ TOOL: Auto Compliance Fixer → python manage.py control → 8
□ Generated Files reviewed
□ TOOL: Final Validation → Control Panel Status Check

TESTING:
□ Server startet ohne Errors
□ List/Create/Detail/Update/Delete funktionieren
□ Relations funktionieren

DOCUMENTATION:
□ Code documented
□ Feature docs erstellt
□ Memory updated

COMMIT:
□ make qcp MSG="..."
```

## 🛠️ TOOL-FIRST APPROACH (MANDATORY!)

**IMMER zuerst Tools nutzen, dann manuell!**

### **Enterprise Tools die wir haben:**
1. ✅ **Auto Compliance Fixer** - CRUD Generation (`python manage.py control → 8`)
2. ✅ **Migration Fixer** - Migration Validation (`make check-migrations`)
3. ✅ **Model Consistency Checker** - Model Validation (`make check-models`)
4. ✅ **Control Panel** - Tool Orchestration (`python manage.py control`)
5. ✅ **Code Formatter** - Pre-commit Fixes (`scripts/code_formatter.py precommit`)

### **Workflow Integration:**
```
1. Model definieren → models.py
2. TOOL: Syntax Check → python -m py_compile
3. TOOL: Consistency Check → model_consistency_checker_v3.py
4. Migration → makemigrations
5. TOOL: Migration Validate → fix_migrations.py diagnose
6. TOOL: Generator → Auto Compliance Fixer
7. TOOL: Final Check → Control Panel
```

---

## 🎯 DIE 5 GOLDENEN REGELN (IMMER!)

### 1️⃣ MODEL ORDER MATTERS
```python
# ✅ RICHTIG: Dependency zuerst
class Agents(models.Model):
    pass

class PromptTemplate(models.Model):
    agent = models.ForeignKey(Agents, ...)  # OK - Agents existiert

# ❌ FALSCH: Reihenfolge verkehrt
class PromptTemplate(models.Model):
    agent = models.ForeignKey(Agents, ...)  # ERROR - Agents noch nicht definiert
```

### 2️⃣ FORWARD REFERENCES = STRING
```python
# Model kommt SPÄTER → String!
active_prompt = models.ForeignKey("PromptTemplate", ...)

# Model kommt VORHER → Direct!
agent = models.ForeignKey(Agents, ...)
```

### 3️⃣ CIRCULAR DEPENDENCIES = NULLABLE
```python
# BEIDE Seiten müssen nullable sein!
class Agents(models.Model):
    active_prompt = models.ForeignKey(
        "PromptTemplate",
        null=True,      # ← REQUIRED!
        blank=True      # ← REQUIRED!
    )
```

### 4️⃣ FORM_LAYOUT = ALL FIELDS
```python
# ❌ KRITISCHER FEHLER: Vergessenes Field
form_layout = {
    "Basic": ["name"]
    # FEHLT: "agent", "active_prompt" → Form zeigt Felder nicht!
}

# ✅ RICHTIG: Alle Felder
form_layout = {
    "Basic": ["name"],
    "Relations": ["agent", "active_prompt"]  # Alle da!
}
```

### 5️⃣ TOOLS VERWENDEN (MANDATORY!)
```bash
# ✅ Model Consistency Check
python scripts/model_consistency_checker_v3.py

# ✅ Migration Validation
python scripts/fix_migrations.py diagnose --app bfagent
python scripts/fix_migrations.py verify --app bfagent

# ✅ CRUD Generator (AUTO!)
python manage.py control → Option 8: Run Generator

# ✅ Control Panel Status Check
python manage.py control → System Health Check

# ✅ Pre-commit Fixes
python scripts/code_formatter.py precommit

# ✅ Quick Commit
make qcp MSG="Add: PromptTemplate model"
```

**NIEMALS manuell erstellen was Tools können!**

---

## 🚨 HÄUFIGSTE FEHLER & FIXES

| Fehler | Symptom | Fix |
|--------|---------|-----|
| **Falsche Model Reihenfolge** | `NameError: 'Model' not defined` | Model nach oben OR String Reference |
| **Field fehlt in Form** | Field nicht in UI | Add to `form_layout` in CRUDConfig |
| **Circular Dependency** | Migration Error | Beide FKs: `null=True, blank=True` |
| **Falsches crud_config.yaml** | Generator ignoriert Model | Exakter Model Name (PascalCase) |
| **Generator überschreibt** | Custom Code weg | `custom_code: true` + Markers |

---

## 📊 PROCESS IMPROVEMENT LOG

### Version 1.0.0 (2025-10-08)
**Created from:** PromptTemplate Implementation Experience

**Key Learnings:**
1. ✅ Migration existierte bereits - Check vor Erstellung
2. ✅ form_layout MUSS alle Felder haben - Kritisch!
3. ✅ Circular Dependencies: Beide Seiten nullable
4. ✅ String References für Forward Declarations

**Improvements Added:**
- Quick Reference als 1-Seite PDF
- Fill-In Template für Tracking
- Error Decoder für häufige Probleme
- Tool Commands Reference

---

## 🔄 CONTINUOUS IMPROVEMENT PROCESS

### Nach JEDER Model-Erweiterung:

1. **Template ausfüllen:**
```
docs/templates/NEW_MODEL_TEMPLATE.md
→ Dokumentiere Probleme & Lösungen
```

2. **Lessons Learned reviewen:**
```
Was lief schief?
Warum passierte es?
Wie verhindere ich es?
Welcher Checklist-Punkt fehlt?
```

3. **Process updaten:**
```
Wenn Fehler auftritt:
→ Add to "Häufigste Fehler"
→ Add to Checklist wenn nötig
→ Update Quick Reference
→ Version bump
```

4. **Memory aktualisieren:**
```
memory-bank/@ALWAYS_READ/@MODEL_EXTENSION_PROCESS.md
→ Immer aktuell halten!
```

---

## 📈 SUCCESS METRICS

**Track diese Metriken:**
- ⚠️ **Error Rate**: Fehler pro Feature
- ⏱️ **Time to Deploy**: Konzept → Production
- 🔄 **Rollback Rate**: Fehlgeschlagene Deployments
- ✅ **First-Time Success**: Features ohne Nachbesserung

**Target nach 10 Features:**
- Error Rate: < 10%
- Time to Deploy: < 2h
- Rollback Rate: 0%
- First-Time Success: > 80%

---

## 🎓 WHEN TO UPDATE THIS PROCESS

### **SOFORT updaten wenn:**
- ❌ Ein Fehler auftritt, der NICHT in der Liste ist
- ❌ Ein Checklist-Punkt unklar oder missverständlich war
- ❌ Ein wichtiger Schritt fehlte
- ❌ Eine bessere Lösung gefunden wurde

### **REVIEW alle 5 Features:**
- Sind alle Fehler dokumentiert?
- Ist die Checkliste vollständig?
- Können Schritte vereinfacht werden?
- Gibt es neue Best Practices?

### **MAJOR UPDATE bei:**
- Django Upgrade
- Neues Tool im Stack
- Architektur-Änderung
- Generator-Update

---

## 📚 RELATED DOCUMENTS

**Für Details siehe:**
- `docs/MODEL_EXTENSION_CHECKLIST.md` - Vollständige Checkliste (10 Phasen)
- `docs/QUICK_REFERENCE_MODEL_EXTENSION.md` - 1-Seite Quick Ref
- `docs/templates/NEW_MODEL_TEMPLATE.md` - Fill-In Template
- `docs/DEVELOPMENT_PROCESS_INDEX.md` - Navigation Hub

---

## 🔥 ENFORCEMENT

**Diese Regel ist MANDATORY:**
- ✅ Muss bei JEDEM Model-Change befolgt werden
- ✅ Pull Requests ohne Checklist-Completion werden REJECTED
- ✅ Fehler gegen diese Regel = Prozess-Update REQUIRED
- ✅ Team Lead reviewed Process Updates

---

## 💡 KONTINUIERLICHE VERBESSERUNG

**Philosophie:**
```
Fehler passieren → Dokumentieren
Dokumentieren → Lernen
Lernen → Prozess verbessern
Prozess verbessern → Weniger Fehler

→ Continuous Improvement Loop!
```

**Ziel:**
```
Jedes Feature macht uns besser!
Jeder Fehler verbessert den Prozess!
→ Weg zu 100% Success Rate!
```

---

**Version History:**
- **v1.0.0** (2025-10-08): Initial Release - PromptTemplate Erfahrungen
- **v1.0.1** (TBD): First real-world refinements
- **v2.0.0** (TBD): Major process improvement after 10 features

---

**🎯 STATUS: ACTIVE & MANDATORY**

**Nächstes Review:** Nach 5 Features oder bei kritischem Fehler

**Maintainer:** BF Agent Development Team  
**Feedback:** Immer willkommen! Continuous Improvement!
