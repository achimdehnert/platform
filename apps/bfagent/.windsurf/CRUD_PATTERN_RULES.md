# MANDATORY CRUD Pattern Rules - BF Agent (Django)

## 🎯 Django CRUD Standardisierung mit Consistency Framework

### **RULE 1: Generator-First Development**
**MANDATORY**: Alle CRUD-Components MÜSSEN durch `consistency_framework.py` generiert werden:

```bash
# Analyze model first
python scripts/consistency_framework.py analyze ModelName

# Generate all components
python scripts/consistency_framework.py generate ModelName --force

# Generate specific components
python scripts/consistency_framework.py generate ModelName --components views forms
```

**NEVER manually create CRUD files!** Use the generator.

### **RULE 2: Metrics Row Pattern**
**MANDATORY**: 4-Spalten-Metriken am Anfang jeder Übersicht:

```python
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total", total_count)
col2.metric("Active", active_count)
col3.metric("Types", type_count)
col4.metric("Requests", request_count)
```

### **RULE 3: Data Editor Configuration**
**MANDATORY**: Typisierte Spalten mit einheitlicher Konfiguration:

```python
edited_df = st.data_editor(
    df,
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "name": st.column_config.TextColumn("Name", width="medium"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=[s.value for s in StatusEnum],
            width="small"
        ),
        "created": st.column_config.TextColumn("Created", disabled=True, width="small")
    },
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True
)
```

### **RULE 4: Action Buttons Layout**
**MANDATORY**: 3-Spalten-Layout für Hauptaktionen:

```python
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Save", type="primary", use_container_width=True):
        _process_changes(df, edited_df)

with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

with col3:
    if st.button("✏️ Edit Selected", use_container_width=True):
        _show_detailed_editor()
```

### **RULE 5: Quick Actions Pattern**
**MANDATORY**: 4-Spalten-Schnellerstellung + 3-Spalten-Bulk-Operationen:

```python
# Quick Create - 4 Columns
col1, col2, col3, col4 = st.columns(4)
with col1: name = st.text_input("Name")
with col2: type_select = st.selectbox("Type", options)
with col3: additional_field = st.selectbox("Field")
with col4: st.button("➕ Create", type="primary")

# Bulk Operations - 3 Columns
col1, col2, col3 = st.columns(3)
with col1: st.button("🔄 Activate All")
with col2: st.button("⏸️ Deactivate All")
with col3: st.button("🧹 Clean Unused")
```

### **RULE 6: Session State Management**
**MANDATORY**: Einheitliche Session State Patterns:

```python
# Modal-like Editor
if st.session_state.get('show_editor', False):
    _render_detailed_editor()

# Selected Item Context
st.session_state.selected_item_id = selected_id
st.session_state.show_editor = True
```

### **RULE 7: Error Handling Pattern**
**MANDATORY**: Konsistente Fehlerbehandlung:

```python
def _render_overview():
    try:
        items = Service.get_all_items()
        # ... render logic
    except Exception as e:
        render_error_message("Error loading items", e)

def _process_changes(original_df, edited_df):
    try:
        # ... processing logic
        render_success_message(f"Updated {changes_count} items")
        st.rerun()
    except Exception as e:
        render_error_message("Error saving changes", e)
```

### **RULE 8: Analytics Structure**
**MANDATORY**: 2-Spalten-Charts + Recent Activity:

```python
# Distribution Charts
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Status Distribution**")
    st.bar_chart(status_df.set_index("Status"), height=200)

with col2:
    st.markdown("**Type Distribution**")
    st.bar_chart(type_df.set_index("Type"), height=200)

# Recent Activity
st.markdown("**Recent Items**")
for item in recent_items[:5]:
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.write(f"**{item.name}**")
    col2.write(format_enum_display(item.type))
    col3.write(item.created_at.strftime('%d.%m.%y'))
```

## 🔧 Enforcement-Mechanismen

### **RULE 9: Mandatory Template Usage**
**ENFORCEMENT**: Alle neuen CRUD-Interfaces MÜSSEN das Template verwenden:

1. **Code Review Requirement**: PR-Ablehnung bei Nicht-Compliance
2. **Template Validation**: Automatische Checks auf Pattern-Einhaltung
3. **Documentation Requirement**: Abweichungen müssen begründet werden

### **RULE 10: Component Library Usage**
**MANDATORY**: Verwendung der standardisierten Komponenten:

```python
from app.components.crud_patterns import (
    render_standard_overview,
    render_quick_actions,
    render_analytics,
    process_data_editor_changes
)
```

### **RULE 11: Naming Conventions**
**MANDATORY**: Einheitliche Funktionsnamen:

- `_render_overview()` - Hauptübersicht mit Data Editor
- `_render_quick_actions()` - Schnellaktionen und Bulk-Operationen
- `_render_analytics()` - Charts und Metriken
- `_render_detailed_editor()` - Detaillierter Editor
- `_process_changes()` - Änderungsverarbeitung
- `_quick_create_item()` - Schnellerstellung
- `_bulk_operation()` - Massenoperationen

## 📋 Compliance Checklist

### **Vor jedem CRUD-Interface PR:**
- [ ] 3-Tab-Struktur implementiert
- [ ] 4-Spalten-Metriken vorhanden
- [ ] Data Editor mit typisierten Spalten
- [ ] 3-Spalten-Action-Buttons
- [ ] Quick Actions mit 4+3-Spalten-Layout
- [ ] Session State Management korrekt
- [ ] Error Handling mit Helper-Funktionen
- [ ] Analytics mit 2-Spalten-Charts
- [ ] Einheitliche Funktionsnamen
- [ ] Component Library verwendet

### **Konsequenzen bei Verstößen:**
- **PR-Ablehnung** ohne Diskussion
- **Refactoring-Anforderung** für bestehenden Code
- **Architecture Review** bei wiederholten Verstößen

## 🎯 Ziel

**Einheitliche, optimierte CRUD-Erfahrung** über alle BookFactory-Module hinweg mit:
- Konsistenter Benutzerführung
- Optimaler Performance
- Robuster Fehlerbehandlung
- Wartbarem Code
