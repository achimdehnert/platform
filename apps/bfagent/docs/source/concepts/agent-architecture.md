# Agent-Architektur

**Status:** 🟢 Konzept finalisiert  
**Version:** 1.0  
**Letzte Aktualisierung:** Januar 2026

---

## Übersicht

BF Agent nutzt eine **dreischichtige Agent-Architektur**, die spezialisierte AI-Agents für verschiedene Aufgabenbereiche bereitstellt. Diese Agents können von Cascade (Claude) orchestriert werden, um komplexe Aufgaben effizient zu delegieren.

```{mermaid}
flowchart TB
    subgraph Orchestrator
        C[Cascade/Claude]
    end
    
    subgraph "Infrastructure Agents"
        SQL[SQLAgent]
        DJ[DjangoAgent]
        DOC[DocAgent]
        TEST[TestAgent]
    end
    
    subgraph "Domain Agents"
        CHAR[CharacterAgent]
        WORLD[WorldAgent]
        RES[ResearchAgent]
        CAD[CADAgent]
    end
    
    subgraph Foundation
        LLM[LLMAgent]
        MCP[MCP Tools]
    end
    
    C --> SQL
    C --> DJ
    C --> DOC
    C --> TEST
    C --> CHAR
    C --> WORLD
    C --> RES
    C --> CAD
    
    SQL --> LLM
    DJ --> LLM
    DOC --> LLM
    TEST --> LLM
    CHAR --> LLM
    WORLD --> LLM
    RES --> LLM
    CAD --> LLM
    
    SQL --> MCP
    DJ --> MCP
    DOC --> MCP
    TEST --> MCP
```

---

## Schichten

### Schicht 1: Foundation

Die Basis-Infrastruktur für alle AI-Operationen.

| Komponente | Beschreibung | Port |
|------------|--------------|------|
| **LLMAgent** | Zentraler Agent für LLM-Aufrufe mit Routing, Caching, Fallback | - |
| **LLM MCP Gateway** | HTTP API für Provider-Abstraktion | 8100 |
| **MCP Tools** | Spezialisierte Tools für DB, Code, etc. | - |

**Datei:** `apps/bfagent/services/llm_agent.py`

```python
from apps.bfagent.services.llm_agent import LLMAgent, ModelPreference

agent = LLMAgent()
response = agent.generate(
    prompt="Analysiere diesen Code...",
    preferences=ModelPreference(quality="balanced")
)
```

### Schicht 2: Spezialisierte Agents

#### Infrastructure Agents

Agents für System-Level Aufgaben.

| Agent | Zweck | MCP Tools |
|-------|-------|-----------|
| **SQLAgent** | Datenbank-Analyse, Query-Optimierung | `mcp1_db_*` |
| **DjangoAgent** | CRUD, Views, Templates, Migrations | `mcp0_bfagent_*` |
| **DocAgent** | Dokumentation aus Code generieren | `mcp0_bfagent_scan_hub_docs` |
| **TestAgent** | Test-Generierung und -Ausführung | `mcp13_*` |
| **CodeQualityAgent** | Code-Analyse, Refactoring | `mcp4_*` |

#### Domain Agents

Agents für fachliche Aufgaben.

| Agent | Domain | Zweck |
|-------|--------|-------|
| **CharacterAgent** | Writing Hub | Charaktererstellung für Bücher |
| **WorldAgent** | Writing Hub | Weltenbau mit Locations, Regeln |
| **ResearchAgent** | Research Hub | Recherche und Synthese |
| **CADAgent** | CAD Hub | Technische Zeichnungsanalyse |
| **TranslationAgent** | MedTrans | Medizinische Übersetzung |

### Schicht 3: Orchestrator

Cascade (Claude) als intelligenter Orchestrator, der:
- User Intent versteht
- Aufgaben in Teilschritte zerlegt
- An spezialisierte Agents delegiert
- Ergebnisse validiert und zusammenführt

---

## Infrastructure Agents im Detail

### SQLAgent

Spezialist für Datenbankoperationen.

**Capabilities:**
- Query-Performance-Analyse (EXPLAIN ANALYZE)
- Schema Discovery
- Data Exploration
- Migration Status Prüfung

**MCP Tools:**

| Tool | Funktion |
|------|----------|
| `mcp1_db_analyze_query` | Query-Performance analysieren |
| `mcp1_db_describe_table` | Tabellenstruktur anzeigen |
| `mcp1_db_list_tables` | Alle Tabellen auflisten |
| `mcp1_db_execute_query` | SELECT Queries ausführen |
| `mcp1_db_migration_status` | Django Migrations prüfen |
| `mcp1_db_django_models` | Django Models auflisten |

**Beispiel:**

```python
class SQLAgent:
    """Agent für Datenbank-Operationen."""
    
    def __init__(self):
        self.llm = LLMAgent()
    
    async def analyze_slow_query(self, sql: str) -> dict:
        # 1. EXPLAIN ANALYZE via MCP Tool
        plan = await self.mcp.call("mcp1_db_analyze_query", {"sql": sql})
        
        # 2. LLM interpretiert den Plan
        analysis = self.llm.generate(
            prompt=f"Analysiere diesen Query-Plan und gib Optimierungsvorschläge:\n{plan}",
            system_prompt="Du bist ein PostgreSQL Performance-Experte.",
            preferences=ModelPreference(quality="best")
        )
        
        return {
            "plan": plan,
            "analysis": analysis.content,
            "recommendations": self._extract_recommendations(analysis.content)
        }
```

---

### DjangoAgent

Spezialist für Django Code-Generierung.

**Capabilities:**
- Model-Generierung aus Beschreibung
- CRUD Views erstellen
- Templates (Bootstrap/HTMX) generieren
- Admin-Interface registrieren
- URL-Routing konfigurieren
- Migrations erstellen

**MCP Tools:**

| Tool | Funktion |
|------|----------|
| `mcp0_bfagent_generate_handler` | Handler-Code generieren |
| `mcp0_bfagent_scaffold_domain` | Komplette Domain erstellen |
| `mcp0_bfagent_get_naming_convention` | Namenskonventionen abrufen |
| `mcp0_bfagent_validate_handler` | Handler validieren |
| `mcp4_analyze_python_file` | Code-Qualität prüfen |

**Beispiel:**

```python
class DjangoAgent:
    """Agent für Django Code-Generierung."""
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.llm = LLMAgent()
    
    async def create_model(self, name: str, description: str, fields: list) -> str:
        # 1. Namenskonventionen abrufen
        conventions = await self.mcp.call(
            "mcp0_bfagent_get_naming_convention",
            {"app_label": self.app_name}
        )
        
        # 2. Model generieren
        model_code = self.llm.generate(
            prompt=f"""
            Erstelle ein Django Model:
            Name: {name}
            Beschreibung: {description}
            Felder: {fields}
            
            Konventionen: {conventions}
            """,
            system_prompt=DJANGO_MODEL_SYSTEM_PROMPT,
            response_format="python"
        )
        
        return model_code.content
    
    async def create_crud_views(self, model_name: str) -> dict:
        """Generiert ListView, DetailView, CreateView, UpdateView, DeleteView."""
        # Implementation...
```

---

### DocAgent

Spezialist für Dokumentation.

**Capabilities:**
- Docstrings aus Code extrahieren
- Dokumentation übersetzen (EN → DE)
- API-Referenz generieren
- Dokumentations-Coverage prüfen

**MCP Tools:**

| Tool | Funktion |
|------|----------|
| `mcp0_bfagent_scan_hub_docs` | Hub auf Docstrings scannen |
| `mcp0_bfagent_update_hub_docs` | Dokumentation aktualisieren |
| `mcp0_bfagent_list_undocumented` | Undokumentierte Items finden |

**Beispiel:**

```python
class DocAgent:
    """Agent für Dokumentation."""
    
    GLOSSARY = {
        "Handler": "Handler",  # Nicht übersetzen
        "Agent": "Agent",
        "State": "State",
        "LLM": "LLM",
    }
    
    async def translate_docstring(self, docstring: str, target_lang: str = "de") -> str:
        # Technische Begriffe schützen
        protected = self._protect_glossary_terms(docstring)
        
        # Übersetzen
        translated = self.llm.generate(
            prompt=f"Übersetze ins Deutsche:\n{protected}",
            system_prompt="Behalte technische Begriffe wie Handler, Agent, etc. bei.",
        )
        
        return self._restore_glossary_terms(translated.content)
```

---

### TestAgent

Spezialist für Testing.

**Capabilities:**
- Tests aus Code generieren
- Test Coverage analysieren
- Test-Failures analysieren
- Regressionstests vorschlagen

**MCP Tools:**

| Tool | Funktion |
|------|----------|
| `mcp13_generate_tests` | Tests generieren |
| `mcp13_run_tests` | Tests ausführen |
| `mcp13_analyze_test_failures` | Failures analysieren |
| `mcp13_suggest_tests_for_coverage` | Coverage-Lücken finden |

---

## Domain Agents im Detail

### WorldAgent

Spezialist für Weltenbau im Writing Hub.

**Capabilities:**
- Weltgrundlagen generieren
- Locations erstellen
- Weltregeln definieren
- Konsistenz prüfen

**Handler:**

| Handler | Funktion |
|---------|----------|
| `WorldGeneratorHandler` | Weltbeschreibung, Geographie, Kultur |
| `WorldExpanderHandler` | Aspekte erweitern (Magie, Politik) |
| `LocationGeneratorHandler` | Orte generieren |
| `WorldRuleGeneratorHandler` | Regeln pro Kategorie |
| `WorldConsistencyCheckerHandler` | Widersprüche finden |

**Beispiel:**

```python
class WorldAgent:
    """Agent für Weltenbau."""
    
    async def create_complete_world(self, seed: str, language: str = "de") -> World:
        # 1. Grundlagen generieren
        world = await self.mcp.call("bfagent_create_world", {
            "seed_idea": seed,
            "language": language
        })
        
        # 2. Orte hinzufügen
        for loc_type in ["continent", "city", "landmark"]:
            await self.mcp.call("bfagent_generate_locations", {
                "world_id": world.id,
                "location_type": loc_type
            })
        
        # 3. Regeln etablieren
        for category in ["magic", "politics", "economy"]:
            await self.mcp.call("bfagent_generate_rules", {
                "world_id": world.id,
                "category": category
            })
        
        # 4. Konsistenz prüfen
        await self.mcp.call("bfagent_check_consistency", {
            "world_id": world.id
        })
        
        return world
```

---

### CharacterAgent

Spezialist für Charaktererstellung.

**Capabilities:**
- Charakterprofile generieren
- Beziehungen definieren
- Charakter-Entwicklung planen
- Dialog-Stil festlegen

---

### ResearchAgent

Spezialist für Recherche.

**Capabilities:**
- Web-Recherche durchführen
- Quellen analysieren
- Synthese erstellen
- Fakten verifizieren

---

## Cascade Integration

Cascade (Claude) nutzt die Agents über MCP Tool-Aufrufe:

```python
# Cascade delegiert an DjangoAgent
result = await mcp.call("django_agent_create_hub", {
    "hub_name": "invoicing",
    "models": ["Invoice", "LineItem", "Payment"],
    "include_admin": True,
    "include_tests": True
})

# Cascade delegiert an SQLAgent
analysis = await mcp.call("sql_agent_analyze_query", {
    "sql": "SELECT * FROM large_table WHERE ...",
    "suggest_indexes": True
})

# Cascade delegiert an DocAgent
await mcp.call("doc_agent_update_hub_docs", {
    "hub_name": "writing_hub",
    "translate_to": "de"
})
```

---

## Best Practices

### Agent-Entwicklung

1. **Single Responsibility:** Jeder Agent hat einen klaren Fokus
2. **LLMAgent nutzen:** Immer über LLMAgent, nie direkt LLM aufrufen
3. **MCP Tools nutzen:** Für DB, Files, externe Services
4. **Keine DB in Agents:** Agents sind pure Functions (State → State)
5. **Handler für Persistenz:** DB-Operationen gehören in Handler

### Prompt Engineering

```python
SYSTEM_PROMPTS = {
    "django": """
    Du bist ein Django-Experte. Generiere Code der:
    - PEP 8 folgt
    - Django Best Practices nutzt
    - BF Agent Konventionen einhält
    - Vollständig dokumentiert ist
    """,
    
    "sql": """
    Du bist ein PostgreSQL-Experte. Analysiere Queries und:
    - Erkenne Performance-Probleme
    - Schlage Indexes vor
    - Empfehle Query-Rewrites
    """
}
```

---

## Roadmap

### Phase 1: Foundation ✅
- [x] LLMAgent implementiert
- [x] LLM MCP Gateway aktiv
- [x] MCP Tools verfügbar

### Phase 2: Infrastructure Agents 🔄
- [ ] SQLAgent
- [ ] DjangoAgent
- [ ] DocAgent
- [ ] TestAgent

### Phase 3: Domain Agents 📋
- [ ] WorldAgent (Writing Hub)
- [ ] CharacterAgent (Writing Hub)
- [ ] ResearchAgent (Research Hub)
- [ ] CADAgent (CAD Hub)

### Phase 4: Cascade Integration 📋
- [ ] Agent MCP Tools für Cascade
- [ ] Orchestration Patterns
- [ ] Error Handling

---

## Siehe auch

- {doc}`/reference/handlers` - Handler API-Referenz
- {doc}`/guides/llm-integration` - LLM Integration Guide
- {doc}`/hubs/writing-hub` - Writing Hub Dokumentation
