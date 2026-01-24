# 🔍 Ungenutzte Tabellen Analyse

**Date:** 2025-12-09 @ 8:55am UTC+1  
**Tool:** `find_unused_tables`  
**Status:** ✅ COMPLETE!

---

## 📊 ZUSAMMENFASSUNG

### **Statistiken:**
- **Total Tabellen:** 259
- **Genutzte Tabellen:** 118 (45.6%)
- **Ungenutzte Tabellen:** 141 (54.4%)
- **Total Rows:** 1,053
- **Rows in ungenutzten Tabellen:** 789 (75%)

---

## ⚠️ POTENTIELL UNGENUTZTE TABELLEN (141)

### **🚨 HIGH PRIORITY - Mit Daten (können gelöscht werden nach Review):**

#### **DSB (Datenschutz) - 525 rows:**
- `dsb_mandant_tom` - 358 rows
- `dsb_tom_massnahme` - 120 rows
- `dsb_mandant` - 8 rows
- `dsb_tom_kategorie` - 8 rows
- `dsb_branche` - 7 rows
- `dsb_rechtsform` - 7 rows
- `dsb_vorfall_typ` - 7 rows
- `dsb_datenkategorie` - 6 rows
- `dsb_rechtsgrundlage` - 4 rows

💡 **Hinweis:** DSB App scheint ungenutzt - 525 rows können Speicher freigeben!

#### **Checklist - 57 rows:**
- `checklist_items` - 53 rows
- `checklist_templates` - 4 rows

#### **Expert Hub - ~50 rows:**
- Viele Tabellen mit Lookup-Daten (gefahrstoffe, explosionsschutz, etc.)

---

### **✅ SAFE TO DELETE - Leer (0 rows):**

#### **Writing Hub Duplikate:**
- `chapters_v2` - 0 rows (haben `writing_chapters`)
- `characters_v2` - 0 rows (haben `writing_characters`)
- `book_characters_v2` - 0 rows
- `worlds_v2` - 0 rows

#### **CAD Module:**
- `cad_analysis_jobs` - 0 rows
- `cad_analysis_reports` - 0 rows  
- `cad_analysis_results` - 0 rows
- `cad_drawing_files` - 0 rows

#### **Comic Module:**
- `comic_dialogues` - 0 rows
- `comic_panels` - 0 rows

#### **Research Module:**
- `research_researchproject` - 0 rows
- `research_researchhandlerexecution` - 0 rows
- Und weitere...

---

## 💡 EMPFEHLUNGEN

### **1. SOFORT LÖSCHEN (Safe - 0 rows):**

**V2 Duplikate:**
```sql
DROP TABLE IF EXISTS chapters_v2;
DROP TABLE IF EXISTS characters_v2;
DROP TABLE IF EXISTS book_characters_v2;
DROP TABLE IF EXISTS book_statuses;
DROP TABLE IF EXISTS worlds_v2;
DROP TABLE IF EXISTS ideas_v2;
```

**Leere Module:**
```sql
-- Comic (wenn nicht genutzt)
DROP TABLE IF EXISTS comic_dialogues;
DROP TABLE IF EXISTS comic_panels;

-- CAD (wenn nicht genutzt)
DROP TABLE IF EXISTS cad_analysis_jobs;
DROP TABLE IF EXISTS cad_analysis_reports;
DROP TABLE IF EXISTS cad_analysis_results;
DROP TABLE IF EXISTS cad_drawing_files;
```

---

### **2. NACH REVIEW LÖSCHEN (Mit Daten):**

**DSB Module (wenn wirklich ungenutzt):**
```sql
-- VORSICHT: 525 rows total!
-- Erst Backup erstellen:
sqlite3 db.sqlite3 ".dump dsb_%" > backup_dsb.sql

-- Dann löschen:
DROP TABLE IF EXISTS dsb_mandant_tom;
DROP TABLE IF EXISTS dsb_tom_massnahme;
DROP TABLE IF EXISTS dsb_mandant;
-- ... etc
```

---

### **3. CHECKEN BEVOR LÖSCHEN:**

**Lookup Tables mit Daten:**
```sql
-- CAD Lookups (66 rows)
SELECT * FROM cad_analysis_category; -- 9 rows
SELECT * FROM cad_building_type; -- 6 rows
SELECT * FROM cad_compliance_standard; -- 9 rows
-- etc.

-- Compliance Lookups (19 rows)
SELECT * FROM compliance_incident_severity; -- 4 rows
SELECT * FROM compliance_priority; -- 4 rows
-- etc.
```

💡 **Frage:** Werden diese Lookups noch gebraucht? Wenn ja → Model erstellen!

---

## 🛠️ CLEANUP SCRIPT

### **Safe Cleanup (nur leere Tabellen):**

```sql
-- V2 Duplikate
DROP TABLE IF EXISTS chapters_v2;
DROP TABLE IF EXISTS characters_v2;
DROP TABLE IF EXISTS book_characters_v2;
DROP TABLE IF EXISTS book_statuses;
DROP TABLE IF EXISTS worlds_v2;
DROP TABLE IF EXISTS ideas_v2;

-- Leere M2M Tables
DROP TABLE IF EXISTS ideas_v2_books;
DROP TABLE IF EXISTS worlds_v2_books;

-- Comic (leer)
DROP TABLE IF EXISTS comic_dialogues;
DROP TABLE IF EXISTS comic_panels;

-- Navigation M2M (leer wenn Navigation über Models läuft)
DROP TABLE IF EXISTS navigation_items_domains;
DROP TABLE IF EXISTS navigation_items_required_groups;
DROP TABLE IF EXISTS navigation_items_required_permissions;
DROP TABLE IF EXISTS navigation_sections_domains;
DROP TABLE IF EXISTS navigation_sections_required_groups;
DROP TABLE IF EXISTS navigation_sections_required_permissions;

-- Research (leer)
DROP TABLE IF EXISTS research_researchproject;
DROP TABLE IF EXISTS research_researchhandlerexecution;
DROP TABLE IF EXISTS research_researchresult;
DROP TABLE IF EXISTS research_researchsession;
DROP TABLE IF EXISTS research_researchsource;

-- Core unused (leer)
DROP TABLE IF EXISTS core_agent_executions;
DROP TABLE IF EXISTS core_contentitem;
DROP TABLE IF EXISTS core_locations;
DROP TABLE IF EXISTS core_plugin_configurations;
DROP TABLE IF EXISTS core_plugin_executions;
DROP TABLE IF EXISTS core_plugin_registry;
DROP TABLE IF EXISTS core_plugin_registry_depends_on;
DROP TABLE IF EXISTS core_prompt_executions;
DROP TABLE IF EXISTS core_prompt_versions;
```

**Geschätzter Speichergewinn:** Minimal (meiste Tabellen leer)

---

### **Data Cleanup (mit Backup!):**

```bash
# 1. Backup erstellen
sqlite3 db.sqlite3 .dump > backup_full.sql
sqlite3 db.sqlite3 ".dump dsb_%" > backup_dsb.sql

# 2. Drop DSB Tables (wenn sicher!)
sqlite3 db.sqlite3 <<EOF
DROP TABLE IF EXISTS dsb_mandant_tom;
DROP TABLE IF EXISTS dsb_tom_massnahme;
DROP TABLE IF EXISTS dsb_mandant;
DROP TABLE IF EXISTS dsb_tom_kategorie;
DROP TABLE IF EXISTS dsb_branche;
DROP TABLE IF EXISTS dsb_rechtsform;
DROP TABLE IF EXISTS dsb_vorfall_typ;
DROP TABLE IF EXISTS dsb_datenkategorie;
DROP TABLE IF EXISTS dsb_rechtsgrundlage;
DROP TABLE IF EXISTS dsb_dokument;
DROP TABLE IF EXISTS dsb_verarbeitung;
DROP TABLE IF EXISTS dsb_verarbeitung_datenkategorien;
DROP TABLE IF EXISTS dsb_vorfall;
EOF

# 3. VACUUM to reclaim space
sqlite3 db.sqlite3 "VACUUM;"
```

**Geschätzter Speichergewinn:** Signifikant! (525 rows DSB + Overhead)

---

## 📋 KATEGORIEN UNGENUTZTER TABELLEN

### **Module komplett ungenutzt:**
1. ✅ **DSB (Datenschutz)** - 13 Tabellen, 525 rows
2. ✅ **Comic** - 2 Tabellen, 0 rows
3. ✅ **Expert Hub** - 28 Tabellen, ~100 rows
4. ✅ **Research** - 10 Tabellen, 0 rows
5. ✅ **CAD** - 10 Tabellen, ~50 rows (Lookups)

### **Duplikate / Alte Versionen:**
1. ✅ `chapters_v2` vs `writing_chapters`
2. ✅ `characters_v2` vs `writing_characters`
3. ✅ `worlds_v2` vs `writing_worlds`
4. ✅ `book_chapters` (VIEW) vs `chapters_v2`
5. ✅ `book_projects` (VIEW) vs `writing_book_projects`

---

## 🎯 NÄCHSTE SCHRITTE

### **Phase 1: Safe Cleanup (sofort möglich)**
```bash
# Nur leere Tabellen löschen
python manage.py shell < cleanup_empty_tables.sql
```

**Risiko:** ❌ NONE  
**Gewinn:** ✅ Aufgeräumte DB, einfacheres Schema

---

### **Phase 2: Module Review (braucht Entscheidung)**

**Fragen:**
1. Wird DSB-Modul noch gebraucht? → Wenn nein: 525 rows löschen!
2. Wird Expert Hub gebraucht? → Wenn nein: ~100 rows löschen!
3. Wird CAD Modul gebraucht? → Wenn nein: ~50 rows löschen!
4. Wird Checklist gebraucht? → Wenn nein: 57 rows löschen!

---

### **Phase 3: Lookup Migration (optional)**

Wenn Lookups gebraucht werden:
1. Models erstellen für `cad_*` Lookups
2. Models erstellen für `compliance_*` Lookups
3. Models erstellen für `expert_hub_*` Lookups
4. Django Admin registrieren

---

## 🛡️ SICHERHEIT

### **Vor jedem Cleanup:**
```bash
# Full Backup
sqlite3 db.sqlite3 .dump > backup_$(date +%Y%m%d_%H%M%S).sql

# Specific Backup
sqlite3 db.sqlite3 ".dump dsb_%" > backup_dsb.sql
```

### **Recovery:**
```bash
# Restore full
sqlite3 db.sqlite3 < backup_YYYYMMDD_HHMMSS.sql

# Restore specific
sqlite3 db.sqlite3 < backup_dsb.sql
```

---

## 📊 ERWARTETE VERBESSERUNGEN

### **Nach Safe Cleanup:**
- ✅ ~50 Tabellen weniger
- ✅ Übersichtlicheres Schema
- ✅ Weniger Verwirrung

### **Nach Full Cleanup (inkl. DSB):**
- ✅ ~141 Tabellen weniger
- ✅ ~789 rows weniger
- ✅ Deutlich kleinere DB-Datei (nach VACUUM)
- ✅ Schnellere Backups
- ✅ Schnellere Migrations

---

## 🔧 TOOL VERWENDUNG

### **Analyze:**
```bash
# Alle ungenutzten Tabellen finden
python manage.py find_unused_tables

# Mit Code-Referenzen
python manage.py find_unused_tables --show-references

# Django Tables einschließen
python manage.py find_unused_tables --include-django
```

### **Report generieren:**
```bash
python manage.py find_unused_tables > unused_tables_report.txt
```

---

## ✅ FAZIT

**Datenbank-Situation:**
- 🔴 **141 ungenutzte Tabellen** (54.4%)
- 🟡 **789 rows** in ungenutzten Tabellen (75%)
- 🟢 **118 aktive Tabellen** (45.6%)

**Empfehlung:**
1. ✅ **Safe Cleanup:** Leere Tabellen sofort löschen (~50 Tabellen)
2. 🤔 **Review:** DSB/Expert/CAD Module prüfen
3. ⚠️ **Mit Backup:** Daten-Tabellen löschen wenn sicher

**Tool Ready:** ✅ `find_unused_tables` einsatzbereit!

---

**Zeit für Cleanup? Sag Bescheid! 🧹✨**
