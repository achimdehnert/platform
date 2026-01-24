# Brandschutz-Experte: Datenbankgetriebene Architektur

## Erstellte Dateien

### Migrations (Alembic)

```
migrations/
├── 001_fp_lookup_norms.py      # Lookup-Tabelle + Normen
├── 002_fp_requirements.py      # Anforderungen mit JSONB
├── 003_fp_checklists.py        # Checklisten + Items
├── 004_fp_recommendations.py   # Empfehlungs-Templates
├── 005_fp_prompts_analyzers.py # Prompts + Analyzer-Config
└── README.md
```

### Seeds (Datenbank-Initialisierung)

```
seeds/
├── seed_01_lookups.py          # Kategorien, Severity, Priority, etc.
├── seed_02_norms.py            # MBO, ASR, DIN, VdS
├── seed_03a_mbo_requirements.py    # MBO-Anforderungen (§14, §33, §35, etc.)
├── seed_03b_asr_requirements.py    # ASR A2.3-Anforderungen
├── seed_04_checklists.py       # Checklisten-Definitionen
├── seed_05a_check_items_konzept.py # Check-Items (Allgemein, Rettungswege)
├── seed_05b_check_items_konzept.py # Check-Items (Brandabschnitt, Technik, Org)
├── seed_06_prompts.py          # LLM Prompt-Templates
├── seed_07_analyzer_config.py  # Patterns, Mappings, Parser-Config
└── seed_master.py              # Master-Script für alle Seeds
```

### Repositories (Datenbankzugriff)

```
repositories/
├── __init__.py                 # Package Exports
├── models.py                   # SQLAlchemy ORM Models
├── norm_repository.py          # Normen + Anforderungen
├── checklist_repository.py     # Checklisten + Items
├── additional_repositories.py  # Prompt, Analyzer, Recommendation, Lookup
└── unit_of_work.py             # Unit of Work + DB Factory
```

### Handlers (Analyse-Logik)

```
handlers/
├── __init__.py                 # Package Exports
├── base_handler.py             # Basis-Handler mit DB-Integration
├── dynamic_analyzer.py         # Pattern-Matcher, Check-Runner (aus DB)
├── concept_analyzer.py         # Handler für Konzept-Analyse (PDF/DOCX)
└── cad_analyzer.py             # Handler für CAD-Analyse (DXF/DWG)
```

---

## Architektur-Prinzip

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NICHTS HARDCODED                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────────┐│
│  │  PostgreSQL  │   │   Handler    │   │        Output                ││
│  │              │   │              │   │                              ││
│  │ • Patterns   │──▶│ • Lädt aus   │──▶│ • Findings                   ││
│  │ • Checklists │   │   DB         │   │ • Recommendations            ││
│  │ • Prompts    │   │ • Führt aus  │   │ • Scores                     ││
│  │ • Normen     │   │ • Generiert  │   │                              ││
│  └──────────────┘   └──────────────┘   └──────────────────────────────┘│
│                                                                         │
│  Python Code = NUR Infrastruktur (Laden, Ausführen, Speichern)         │
│  Fachlogik   = ALLES in Datenbank (Patterns, Regeln, Schwellwerte)     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Was in der Datenbank liegt

| Tabelle | Inhalt | Beispiele |
|---------|--------|-----------|
| `fire_protection_lookup` | Kategorien, Enums | severity: critical/high/medium/low |
| `fire_protection_norm` | Normen | MBO, ASR A2.3, DIN 14096 |
| `fire_protection_requirement` | Anforderungen | §33: Rettungsweglänge ≤35m |
| `fire_protection_checklist` | Prüflisten | Standard-Konzeptprüfung |
| `fire_protection_check_item` | Prüfpunkte | "Zwei Rettungswege vorhanden?" |
| `fire_protection_recommendation_template` | Empfehlungen | "Rettungsweg verkürzen auf..." |
| `fire_protection_prompt_template` | LLM Prompts | Konzept-Analyse-Prompt |
| `fire_protection_analyzer_config` | Parser-Config | Regex-Patterns, Layer-Mappings |

---

## Auto-Check Beispiel (aus DB)

```json
{
  "enabled": true,
  "method": "check_threshold",
  "params": {
    "max_value": 35,
    "unit": "m"
  },
  "data_source": "extracted.escape_routes.max_length"
}
```

Der Handler lädt diese Config aus der DB und führt sie aus - **ohne eigene Logik**.

---

## Verwendung

### 1. Migration ausführen

```bash
alembic upgrade head
```

### 2. Seeds einspielen

```bash
# Als SQL exportieren
python seeds/seed_master.py --sql seed_all.sql

# SQL ausführen
psql -d your_database -f seed_all.sql
```

### 3. Handler verwenden

```python
from handlers.concept_analyzer import ConceptAnalyzerHandler, ConceptAnalysisInput

# Unit of Work erstellen (DB-Session)
async with get_session() as session:
    uow = FireProtectionUnitOfWork(session)
    
    # Handler initialisieren
    handler = ConceptAnalyzerHandler(uow)
    
    # Analyse durchführen
    result = await handler.process(ConceptAnalysisInput(
        file_path="konzept.pdf",
        building_class="GK4"
    ))
    
    if result.success:
        print(f"Vollständigkeit: {result.data['completeness_score']}%")
        print(f"Risiko-Score: {result.data['risk_score']}")
        print(f"Findings: {len(result.data['findings'])}")
```

---

## Erweiterung

### Neue Norm hinzufügen

```sql
INSERT INTO fire_protection_norm (id, code, name, category, ...)
VALUES (uuid_generate_v4(), 'LBO_NRW', 'Landesbauordnung NRW', 'baurecht', ...);
```

### Neuen Prüfpunkt hinzufügen

```sql
INSERT INTO fire_protection_check_item (id, checklist_id, code, question, auto_check, ...)
VALUES (
    uuid_generate_v4(),
    (SELECT id FROM fire_protection_checklist WHERE code = 'standard_brandschutz_konzept'),
    'RW-010',
    'Ist eine Anleiterungsfläche vorhanden?',
    '{"enabled": true, "method": "check_keyword_exists", "params": {"keywords": ["anleiterung", "leiterweg"]}}'::jsonb,
    ...
);
```

### Neues Pattern hinzufügen

```sql
UPDATE fire_protection_analyzer_config
SET extraction_patterns = extraction_patterns || 
    '{"anleiterung": {"type": "regex", "patterns": ["anleiterung.*?(\\d+)\\s*m"]}}'::jsonb
WHERE code = 'concept_extractor_v1';
```

**Kein Code-Deployment nötig!**

---

## Statistiken

| Kategorie | Anzahl |
|-----------|--------|
| Lookup-Werte | ~30 |
| Normen | 10 |
| Anforderungen | ~25 (MBO + ASR) |
| Checklisten | 3 |
| Check-Items | ~25 |
| Prompt-Templates | 4 |
| Analyzer-Configs | 3 |

---

## Nächste Schritte

1. **CAD-Analyzer Handler** → für DXF/DWG/IFC
2. **Report-Generator** → PDF/DOCX Berichte
3. **Web-API** → FastAPI Endpoints
4. **Admin-UI** → CRUD für Normen/Checklisten
