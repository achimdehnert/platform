# 🔄 Refactoring Summary: Hardcoded → Database

**Analyse:** 2024-12-06  
**Gefunden:** 32 hardcoded choices in 4 Apps

---

## 📊 Übersicht

| App | Choices | Priorität | Aufwand |
|-----|---------|-----------|---------|
| **bfagent** | 26 | 🔴 Hoch | 3-4 Tage |
| **medtrans** | 3 | 🟡 Mittel | 1 Tag |
| **genagent** | 2 | 🟡 Mittel | 0.5 Tag |
| **core** | 1 | 🟢 Niedrig | 0.5 Tag |

---

## 🎯 Top 3 Priorities

### 1. 🔴 Illustration System (BFAgent)
**Choices:** 7 (ArtStyle, ImageType, AIProvider, ImageStatus, ...)  
**Impact:** HOCH - Aktiv genutztes Feature  
**Aufwand:** 1-2 Tage  

**Vorteile:**
- Neue Art Styles ohne Code
- Beispielbilder pro Style
- Provider-Preise in DB
- Empfohlene Style-Type Kombinationen

---

### 2. 🟡 Review System (BFAgent)
**Choices:** 5 (STATUS, ROLE, TYPE, ...)  
**Impact:** MITTEL - Workflow Improvements  
**Aufwand:** 1 Tag  

**Vorteile:**
- Rollen-Permissions in DB
- UI-Styling konfigurierbar
- Workflow-Regeln anpassbar

---

### 3. 🟡 MedTrans Translation
**Choices:** 3 (STATUS, LANGUAGE, METHOD)  
**Impact:** MITTEL - Isoliertes System  
**Aufwand:** 1 Tag  

**Vorteile:**
- Neue Sprachen ohne Code
- Provider-Kosten tracking
- Progress % für UI

---

## ✅ Bereits Migriert

- ✅ Writing Hub Lookups (4 tables)
- ✅ Handler System Lookups (3 tables)

**Pattern etabliert in:**
- `apps/writing_hub/models_lookups.py`
- `apps/writing_hub/models_handler_lookups.py`

---

## 📋 Standard Pattern

```python
class ArtStyle(models.Model):
    # Required
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    
    # Optional metadata
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, default='primary')
    
    # Standard
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'illustration_art_styles'
        ordering = ['order', 'name']
```

---

## 🚀 Migration Steps

1. **Create** `models_lookups_{domain}.py`
2. **Run** `makemigrations`
3. **Create** seed SQL script
4. **Update** main models (ForeignKey)
5. **Update** forms (ModelChoiceField)
6. **Register** in admin
7. **Test** thoroughly

---

## 📈 Expected Results

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| Hardcoded Choices | 32 | 0 |
| Code changes für neue Optionen | Ja | Nein |
| Admin UI | Nein | Ja |
| API-ready | Nein | Ja |
| Metadaten | Begrenzt | Unbegrenzt |

---

## 🎯 Recommendation

**Start mit:** Illustration System (Woche 1)  
**Dann:** Review System (Woche 2)  
**Danach:** MedTrans (Woche 3)  
**Zuletzt:** Rest (bei Bedarf)

**Gesamt-Aufwand:** 4-5 Tage  
**ROI:** HOCH  

---

**Vollständige Analyse:** `docs/REFACTORING_HARDCODED_TO_DB.md`
