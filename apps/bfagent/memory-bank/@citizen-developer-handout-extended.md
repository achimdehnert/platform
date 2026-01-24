# Citizen Developer Handout - BookFactory MVP
*Erweiterte Version 0.3.0 mit AI-Features und Automatisierung*

## 🎯 Überblick

BookFactory MVP ist eine intelligente Plattform für Buchentwicklung, die traditionelle Projektmanagement-Tools mit modernster KI-Technologie kombiniert. Diese Anleitung richtet sich an Citizen Developer, die das System verstehen, erweitern oder anpassen möchten.

## 🏗️ System-Architektur

### Core-Komponenten

```
BookFactory MVP v0.3.0
├── 📊 Datenbank Layer (SQLModel + SQLite)
│   ├── Projekte, Charaktere, Kapitel
│   ├── AI-Agenten und LLM-Konfigurationen
│   └── AI-Empfehlungen und Metadaten
├── 🔧 Service Layer
│   ├── CRUD-Services mit Session-Management
│   ├── AI-Integration Services
│   └── Empfehlungs-Management
├── 🤖 AI Agent Layer (NEU in v0.3.0)
│   ├── Plot Agent mit Automatisierung
│   ├── Multi-Provider LLM Support
│   └── Intelligente Batch-Verarbeitung
└── 🖥️ UI Layer (Streamlit)
    ├── Responsive Multi-Page Interface
    ├── Real-time AI-Integration
    └── Advanced Workflow Management
```

### Neue AI-Features in v0.3.0

#### 1. AI Agent Management System
- **Multi-Agent Architecture**: Spezialisierte Agenten für verschiedene Schreibaspekte
- **LLM Provider Integration**: OpenAI, Anthropic, Azure, Groq, Together, Mistral, Local
- **Dynamic Agent Assignment**: Flexible Zuordnung von Agenten zu LLMs
- **Real-time Testing**: Sofortige Validierung von Agent-Konfigurationen

#### 2. Plot Agent Automation
- **Batch Processing**: Automatische Analyse aller Plot-Aspekte
- **Intelligent Prompting**: Kontextbewusste Prompt-Generierung
- **Progress Tracking**: Real-time Fortschrittsanzeige
- **Auto-Save Integration**: Automatisches Speichern von Empfehlungen

#### 3. AI Recommendations System
- **Structured Storage**: Empfehlungen mit Metadaten und Status-Tracking
- **Priority Management**: 5-stufiges Prioritätssystem
- **Workflow Integration**: Intelligente nächste Schritte
- **Batch Operations**: Massenbearbeitung von Empfehlungen

## 🛠️ Technische Implementation

### Session Management Pattern (Kritisch!)

**Problem**: Streamlit + SQLAlchemy DetachedInstanceError
**Lösung**: Object Expunging Pattern

```python
def create_object(data: Dict[str, Any], session: Optional[Session] = None) -> Object:
    def _create_object(session: Session) -> Object:
        obj = Object(**data)
        session.add(obj)
        session.commit()

        # Force load all attributes to avoid lazy loading
        _ = (obj.id, obj.name, obj.created_at, obj.updated_at)

        # Expunge to detach from session
        session.expunge(obj)
        return obj

    if session:
        return _create_object(session)
    else:
        with get_session() as session:
            return _create_object(session)
```

### AI Integration Architecture

#### LLM Client Factory Pattern

```python
class LLMClientFactory:
    @staticmethod
    def create_client(llm: LLM) -> BaseLLMClient:
        if llm.provider == LLMProvider.OPENAI:
            return OpenAIClient(llm)
        elif llm.provider == LLMProvider.ANTHROPIC:
            return AnthropicClient(llm)
        # ... weitere Provider
```

#### Agent Service Pattern

```python
class AgentService:
    @staticmethod
    def execute_agent(agent_id: int, prompt: str, context: Dict) -> AgentResponse:
        # 1. Load Agent und LLM
        # 2. Generate enhanced prompt
        # 3. Execute LLM call
        # 4. Parse and structure response
        # 5. Return with metadata
```

### Automatisierung Framework

#### Batch Processing Engine

```python
class PlotAgentAutomation:
    @staticmethod
    def process_aspects(project_id: int, aspects: List[str]) -> BatchResult:
        results = []
        for aspect in aspects:
            try:
                # Generate context-aware prompt
                prompt = generate_aspect_prompt(project_id, aspect)

                # Execute agent
                response = AgentService.execute_agent(agent_id, prompt, context)

                # Store result
                results.append({
                    'aspect': aspect,
                    'response': response,
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'aspect': aspect,
                    'error': str(e),
                    'status': 'error'
                })

        return BatchResult(results)
```

## 🔧 Entwicklungsrichtlinien

### Code-Qualität Standards

#### 1. Session Management
- **IMMER** Object Expunging in Service-Methoden
- **NIEMALS** ORM-Objekte nach Session-Schließung verwenden
- **SOFORT** Attribute nach Service-Calls extrahieren

#### 2. Streamlit Best Practices
- **Unique Keys**: Alle Buttons brauchen eindeutige Keys
- **Session State**: Für komplexe UI-Zustände nutzen
- **Form Management**: Proper form clearing nach Submit

#### 3. AI Integration
- **Error Handling**: Robuste Fehlerbehandlung für API-Calls
- **Rate Limiting**: Respektierung von Provider-Limits
- **Cost Tracking**: Token-Usage und Kosten-Monitoring

### Erweiterungsrichtlinien

#### Neue AI-Agenten hinzufügen

1. **Agent-Typ definieren**:
```python
class AgentType(str, Enum):
    PLOT = "plot"
    CHARACTER = "character"
    STYLE = "style"
    DIALOGUE = "dialogue"
    WORLD_BUILDING = "world_building"
    RESEARCH = "research"
    # NEU: Ihr Agent-Typ
    NEW_AGENT = "new_agent"
```

2. **Service-Methoden erweitern**:
```python
def execute_new_agent(project_id: int, prompt: str) -> AgentResponse:
    # Spezifische Logik für neuen Agent
    pass
```

3. **UI-Komponente erstellen**:
```python
def show_new_agent_interface(project_id: int):
    # Streamlit Interface für neuen Agent
    pass
```

#### Neue LLM Provider integrieren

1. **Provider Enum erweitern**:
```python
class LLMProvider(str, Enum):
    # ... existing providers
    NEW_PROVIDER = "new_provider"
```

2. **Client implementieren**:
```python
class NewProviderClient(BaseLLMClient):
    def generate_response(self, prompt: str) -> LLMResponse:
        # Provider-spezifische Implementation
        pass
```

3. **Factory erweitern**:
```python
# In LLMClientFactory.create_client()
elif llm.provider == LLMProvider.NEW_PROVIDER:
    return NewProviderClient(llm)
```

## 📊 Datenbank Schema

### Neue Tabellen in v0.3.0

#### agent_recommendations
```sql
CREATE TABLE agent_recommendations (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES book_projects(id),
    agent_id INTEGER REFERENCES agents(id),
    recommendation_type VARCHAR(50),
    title VARCHAR(200),
    content TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 3,
    user_notes TEXT,
    implementation_notes TEXT,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Erweiterte agents Tabelle
```sql
-- Neue Felder in agents
ALTER TABLE agents ADD COLUMN system_prompt TEXT;
ALTER TABLE agents ADD COLUMN llm_id INTEGER REFERENCES llms(id);
ALTER TABLE agents ADD COLUMN is_active BOOLEAN DEFAULT true;
```

### Datenbank-Migrationen

Für Schema-Updates:

```python
def upgrade_to_v03():
    """Upgrade database schema to version 0.3.0"""
    # 1. Create agent_recommendations table
    # 2. Add new columns to existing tables
    # 3. Migrate existing data if needed
    # 4. Update version info
```

## 🚀 Deployment und Konfiguration

### Environment Setup

#### .env Configuration
```bash
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key

# Database
DATABASE_URL=sqlite:///bookfactory.db

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

#### Requirements Management
```bash
# Core dependencies
streamlit>=1.28.0
sqlmodel>=0.0.14
openai>=1.3.0
anthropic>=0.7.0
python-dotenv>=1.0.0

# Development dependencies
pytest>=7.4.0
black>=23.0.0
isort>=5.12.0
```

### Production Deployment

#### Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Health Checks
```python
def health_check():
    """System health validation"""
    checks = {
        'database': check_database_connection(),
        'llm_providers': check_llm_providers(),
        'agents': check_agent_configuration(),
        'session_management': check_session_patterns()
    }
    return all(checks.values())
```

## 🧪 Testing Framework

### Test Categories

#### 1. Unit Tests
- Service Layer Funktionen
- Session Management Patterns
- AI Integration Components

#### 2. Integration Tests
- Database Operations
- LLM Provider Connections
- Agent Execution Workflows

#### 3. UI Tests
- Streamlit Component Rendering
- Form Submissions
- Navigation Flows

### Test Implementation

```python
def test_agent_recommendation_creation():
    """Test AI recommendation storage and retrieval"""
    # Setup
    project = create_test_project()
    agent = create_test_agent()

    # Execute
    recommendation = RecommendationService.create_recommendation(
        project_id=project.id,
        agent_id=agent.id,
        recommendation_type=RecommendationType.PLOT_STRUCTURE,
        title="Test Recommendation",
        content="Test content"
    )

    # Verify
    assert recommendation.id is not None
    assert recommendation.status == RecommendationStatus.PENDING
    assert recommendation.priority == 3
```

## 🔍 Monitoring und Debugging

### Logging Framework

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bookfactory.log'),
        logging.StreamHandler()
    ]
)

# Usage in components
logger = logging.getLogger(__name__)
logger.info("Agent execution started", extra={
    'agent_id': agent.id,
    'project_id': project.id,
    'aspect': aspect
})
```

### Performance Monitoring

```python
def monitor_llm_usage():
    """Track LLM usage and costs"""
    metrics = {
        'total_requests': count_llm_requests(),
        'total_tokens': sum_token_usage(),
        'total_cost': calculate_total_cost(),
        'avg_response_time': calculate_avg_response_time()
    }
    return metrics
```

## 🔐 Sicherheit und Best Practices

### API Key Management
- **Niemals** API Keys im Code hardcoden
- **Immer** Environment Variables nutzen
- **Regelmäßig** Keys rotieren
- **Monitoring** für ungewöhnliche Usage

### Data Privacy
- **Lokale Datenbank** für sensible Projektdaten
- **Opt-in** für Cloud-basierte Features
- **Transparenz** über Datennutzung
- **Löschfunktionen** für Benutzerdaten

### Error Handling
```python
def safe_llm_call(client: BaseLLMClient, prompt: str) -> Optional[LLMResponse]:
    """Safe LLM call with comprehensive error handling"""
    try:
        return client.generate_response(prompt)
    except RateLimitError:
        logger.warning("Rate limit exceeded, implementing backoff")
        time.sleep(60)
        return None
    except APIError as e:
        logger.error(f"LLM API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in LLM call: {e}")
        return None
```

## 📈 Performance Optimierung

### Database Optimization
- **Indexing**: Auf häufig abgefragte Felder
- **Connection Pooling**: Für bessere Performance
- **Query Optimization**: Vermeidung von N+1 Problemen

### UI Performance
- **Caching**: Für teure Operationen
- **Lazy Loading**: Für große Datensätze
- **Progressive Enhancement**: Schrittweise Feature-Aktivierung

### AI Integration Optimization
- **Prompt Caching**: Für wiederkehrende Patterns
- **Batch Processing**: Für Multiple Requests
- **Response Streaming**: Für bessere UX

## 🔄 Continuous Integration

### Git Workflow
```bash
# Feature Development
git checkout -b feature/new-agent-type
# ... development work
git commit -m "feat: add new agent type with automation support"
git push origin feature/new-agent-type
# ... PR and review process
```

### Automated Testing
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v
```

## 📚 Weiterführende Ressourcen

### Dokumentation
- **API Documentation**: Automatisch generiert aus Code
- **User Guides**: Schritt-für-Schritt Anleitungen
- **Developer Docs**: Technische Implementierungsdetails
- **Changelog**: Versionshistorie und Breaking Changes

### Community und Support
- **GitHub Issues**: Bug Reports und Feature Requests
- **Discussions**: Community-getriebene Hilfe
- **Wiki**: Sammlung von Best Practices
- **Examples**: Beispiel-Implementierungen

## 🎯 Roadmap und Zukunft

### Version 0.4.0 (Geplant)
- **Multi-Agent Workflows**: Koordinierte Agent-Zusammenarbeit
- **Advanced Analytics**: Detaillierte Projekt-Metriken
- **Export Features**: PDF/EPUB Generation
- **Collaboration Tools**: Multi-User Support

### Langfristige Vision
- **AI Model Training**: Custom Models für spezifische Genres
- **Advanced Automation**: Vollständige Buchgenerierung
- **Publishing Integration**: Direkte Verbindung zu Verlagen
- **Mobile Apps**: Native iOS/Android Unterstützung

---

## 🔧 Praktische Tipps für Citizen Developer

### Häufige Entwicklungspatterns

#### 1. Neue UI-Komponente hinzufügen
```python
# 1. Komponente erstellen
def show_new_component(project_id: int):
    st.subheader("Neue Komponente")
    # ... UI Logic

# 2. In main page integrieren
if selected_tab == "Neue Komponente":
    show_new_component(project.id)
```

#### 2. Service-Methode erweitern
```python
# 1. Service-Methode definieren
@staticmethod
def new_service_method(param: str, session: Optional[Session] = None) -> Result:
    def _execute(session: Session) -> Result:
        # ... business logic
        session.expunge(result)  # WICHTIG!
        return result

    return _execute(session) if session else with_session(_execute)

# 2. In UI verwenden
result = Service.new_service_method(param)
result_name = result.name  # Sofort extrahieren!
```

#### 3. AI-Integration erweitern
```python
# 1. Prompt-Template definieren
PROMPT_TEMPLATE = """
Analysiere folgendes Projekt:
{project_context}

Fokus auf: {analysis_focus}
"""

# 2. Agent-Logik implementieren
def analyze_project_aspect(project_id: int, aspect: str) -> str:
    context = build_project_context(project_id)
    prompt = PROMPT_TEMPLATE.format(
        project_context=context,
        analysis_focus=aspect
    )
    return execute_llm_call(prompt)
```

### Debugging-Strategien

#### 1. Session-Probleme debuggen
```python
# Logging hinzufügen
logger.info(f"Object state before expunge: {obj.__dict__}")
session.expunge(obj)
logger.info(f"Object state after expunge: {obj.__dict__}")
```

#### 2. UI-State debuggen
```python
# Session State inspizieren
st.sidebar.write("Debug Info:")
st.sidebar.json(dict(st.session_state))
```

#### 3. AI-Calls debuggen
```python
# Request/Response logging
logger.info(f"LLM Request: {prompt[:100]}...")
response = client.generate_response(prompt)
logger.info(f"LLM Response: {response.content[:100]}...")
```

### Code-Review Checkliste

- [ ] Session Management korrekt implementiert?
- [ ] Streamlit Keys eindeutig?
- [ ] Error Handling vorhanden?
- [ ] Logging implementiert?
- [ ] Tests geschrieben?
- [ ] Dokumentation aktualisiert?
- [ ] Performance berücksichtigt?
- [ ] Security-Aspekte beachtet?

---

*BookFactory MVP v0.3.0 - Entwickelt für die Zukunft des intelligenten Schreibens*
