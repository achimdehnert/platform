# StreamDeck XL - Batch Setup Guide

**Ziel:** Alle 32 Buttons in 10 Minuten konfigurieren

---

## 🚀 Schnellste Methode: Copy-Paste

### **Schritt 1: Master Button erstellen**

1. **Wähle ersten Button** (z.B. Row 1, Col 1)
2. **Ziehe "Super Macro" darauf**
3. **Konfiguriere:**
   - Titel: `Feature\nRequest`
   - ✅ "Load macros from files"
   - Short-Press File: `C:\Users\achim\github\bfagent\streamdeck\macros\01_feature_request.txt`
4. **Speichern**

### **Schritt 2: Kopieren & Anpassen**

1. **Rechtsklick auf Button** → Copy (oder CTRL+C)
2. **Klick auf nächsten Button** → Paste (oder CTRL+V)
3. **Nur ändern:**
   - Titel
   - File-Pfad (z.B. `02_quick_task.txt`)
4. **Wiederholen für alle 32 Buttons**

**Zeit pro Button:** 15 Sekunden = **8 Minuten total!**

---

## 📋 Button Mapping (32 Buttons, 8x4)

### **ROW 1: Templates (8 Buttons)**

| Col | Titel | File | Farbe |
|-----|-------|------|-------|
| 1 | Feature\nRequest | 01_feature_request.txt | #4CAF50 |
| 2 | Quick\nTask | 02_quick_task.txt | #FF9800 |
| 3 | Bug\nFix | 03_bug_fix.txt | #F44336 |
| 4 | Refactor | 04_refactoring.txt | #2196F3 |
| 5 | Minimal\nRequest | 05_minimal_request.txt | #607D8B |
| 6 | Context\nRequest | 06_context_request.txt | #00BCD4 |
| 7 | Plan\nRequest | 07_plan_request.txt | #3F51B5 |
| 8 | Check\npoint | 08_checkpoint.txt | #9C27B0 |

### **ROW 2: BFAgent MCP Tools (8 Buttons)**

| Col | Titel | File | Farbe |
|-----|-------|------|-------|
| 1 | BFAgent\nBest | 09_best_practices.txt | #8BC34A |
| 2 | Protected\nPaths | 10_protected_paths.txt | #FF5722 |
| 3 | Naming\nConv | 11_naming_convention.txt | #009688 |
| 4 | Domain\nInfo | 12_domain_info.txt | #673AB7 |
| 5 | Search\nHandlers | 13_search_handlers.txt | #795548 |
| 6 | Refactor\nOptions | 14_refactor_options.txt | #FF6F00 |
| 7 | Get\nDomain | 15_get_domain.txt | #1976D2 |
| 8 | Validate\nHandler | 16_validate_handler.txt | #7B1FA2 |

### **ROW 3: Workflows & Creation (8 Buttons)**

| Col | Titel | File | Farbe |
|-----|-------|------|-------|
| 1 | Create\nDomain | 17_create_domain.txt | #00897B |
| 2 | Create\nHandler | 18_create_handler.txt | #5E35B1 |
| 3 | Create\nView | 19_create_view.txt | #C2185B |
| 4 | Create\nModel | 20_create_model.txt | #F57C00 |
| 5 | Create\nTest | 21_create_test.txt | #558B2F |
| 6 | Golden\nRules | 22_golden_rules.txt | #FFC107 |
| 7 | (Leer) | - | - |
| 8 | (Leer) | - | - |

### **ROW 4: Session Management (8 Buttons)**

| Col | Titel | File | Farbe |
|-----|-------|------|-------|
| 1 | Continue\nTask | 23_continue_task.txt | #43A047 |
| 2 | Pause\nTask | 24_pause_task.txt | #FB8C00 |
| 3 | Start\nSession | 25_start_session.txt | #66BB6A |
| 4 | Complete\nSession | 26_complete_session.txt | #26A69A |
| 5 | Snapshot\nStatus | 27_snapshot_status.txt | #5C6BC0 |
| 6 | (Leer) | - | - |
| 7 | Save\nState | 28_save_state.txt | #AB47BC |
| 8 | (Leer) | - | - |

**Hinweis:** Buttons 7+8 in Row 3 und Button 6 in Row 4 können für eigene Actions genutzt werden (z.B. "Open Docs", "Open Monitor")

---

## 🎨 Farben setzen (Optional)

**Für jedes Button:**
1. **Rechtsklick** auf Button
2. **Appearance** → Title Color
3. **Hex-Code eingeben** (z.B. `#FF9800`)

**Zeit:** +2 Minuten für alle Farben

---

## ⚡ Pro-Tipps

### **Tipp 1: Batch Edit**
- Konfiguriere ALLE Dateien zuerst
- Dann alle Farben in einem Durchgang

### **Tipp 2: Gruppen erstellen**
- Alle Templates = Grüntöne
- Alle MCP Tools = Blautöne
- Workflows = Lilatöne
- Session = Grüntöne

### **Tipp 3: Testen**
- Nach jedem 4. Button kurz testen
- Verhindert Fehler-Kaskaden

---

## ✅ Checkliste

- [ ] Alle 28 Macro-Dateien vorhanden (01-28)
- [ ] Button 1 konfiguriert (Master)
- [ ] Buttons 2-8 (Row 1) kopiert & angepasst
- [ ] Buttons 9-16 (Row 2) kopiert & angepasst
- [ ] Buttons 17-22 (Row 3) kopiert & angepasst
- [ ] Buttons 23-28 (Row 4) kopiert & angepasst
- [ ] Alle Buttons getestet
- [ ] Farben gesetzt (optional)

---

## 🎯 Finale Zeiten

| Methode | Zeit |
|---------|------|
| **Nur Files** | 8 Min |
| **Files + Titel** | 10 Min |
| **Files + Titel + Farben** | 12 Min |

**Empfohlen:** Files + Titel = **10 Minuten für perfektes Setup!** 🚀

---

## 📁 Alle Macro Files Location

```
C:\Users\achim\github\bfagent\streamdeck\macros\
```

**Alle 28 Dateien bereit!** ✅
