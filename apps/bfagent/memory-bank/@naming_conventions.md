# Naming Conventions - Consistent Naming Standards

## 🎯 CORE PRINCIPLE
**Regel**: Namen müssen selbsterklärend und eindeutig sein, um Verwirrung und Duplikation zu vermeiden

## 📋 DJANGO-SPECIFIC NAMING CONVENTIONS

### 1. **View Function Naming**
**Regel**: `{action}_{entity}_{context}` Pattern verwenden
```python
# ✅ RICHTIG: Selbsterklärende View-Namen
def create_book_wizard()          # Erstellt Buch über Wizard
def edit_book_content()           # Bearbeitet Buch-Content
def ai_agent_edit_content()       # AI-Agent bearbeitet Content
def ai_agent_execute_prompt()     # AI-Agent führt Prompt aus
def trigger_batch_agents()        # Triggert mehrere Agenten

# ❌ FALSCH: Verwirrende/generische Namen
def agent_edit_content()          # Welcher Agent? Welche Art von Edit?
def execute_with_prompt()         # Was wird ausgeführt?
def trigger_agent()               # Welcher Agent? Welche Aktion?
def update_content()              # Welcher Content? Wie?
```

### 2. **URL Pattern Naming**
**Regel**: RESTful + Hierarchisch + Eindeutig
```python
# ✅ RICHTIG: Klare URL-Hierarchie
urlpatterns = [
    # Book Management
    path('books/', book_list, name='book_list'),
    path('books/create/', book_create, name='book_create'),
    path('books/<int:pk>/', book_detail, name='book_detail'),
    path('books/<int:pk>/edit/', book_edit, name='book_edit'),

    # AI Agent Operations (nested under book)
    path('books/<int:book_id>/ai-agents/', ai_agent_dashboard, name='ai_agent_dashboard'),
    path('books/<int:book_id>/ai-agents/edit-content/', ai_agent_edit_content, name='ai_agent_edit_content'),
    path('books/<int:book_id>/ai-agents/execute-prompt/', ai_agent_execute_prompt, name='ai_agent_execute_prompt'),
    path('books/<int:book_id>/ai-agents/batch-execute/', ai_agent_batch_execute, name='ai_agent_batch_execute'),
]

# ❌ FALSCH: Verwirrende URL-Struktur
urlpatterns = [
    path('agent-edit/', agent_edit_content),      # Welches Buch? Welcher Agent?
    path('execute-with-prompt/', execute_with_prompt),  # Unklarer Kontext
    path('trigger/<str:agent>/', trigger_agent),  # Zu generisch
]
```

### 3. **Template Naming**
**Regel**: `{app}_{entity}_{action}.html` Pattern
```html
<!-- ✅ RICHTIG: Eindeutige Template-Namen -->
books/book_list.html
books/book_detail.html
books/book_edit.html
agents_ui/ai_agent_dashboard.html
agents_ui/ai_agent_edit_modal.html
agents_ui/ai_agent_result_partial.html

<!-- ❌ FALSCH: Generische Template-Namen -->
list.html
detail.html
agent_result.html
modal.html
```

### 4. **Package vs. File Naming - KRITISCHE REGEL**
**🚨 NIEMALS**: Package-Verzeichnis und .py Datei mit identischem Namen im selben Django App-Verzeichnis!
```python
# ❌ FATAL ERROR: Führt zu ImportError und Circular Import
agent_management/
├── services.py          # Datei
└── services/            # Package - KONFLIKT!
    ├── __init__.py
    └── llm_service.py

# Python lädt Package statt .py Datei → ImportError!
# from .services import AgentExecutionService  # FEHLER!

# ✅ RICHTIG: Eindeutige Namen verwenden
agent_management/
├── services.py          # Legacy Services
└── services_new/        # Neues Package - KEIN KONFLIKT
    ├── __init__.py
    └── llm_service.py

# Imports funktionieren korrekt:
# from .services import AgentExecutionService      # ✅ Datei
# from .services_new import llm_service           # ✅ Package
```

**Lesson Learned (05.08.2025)**: Dieser Konflikt führte zu stundenlanger Debugging-Session mit Circular Import Errors im Django Agent Management System. Die Lösung war das Umbenennen des Package von `services/` zu `services_new/`.

### 5. **Model Field Naming**
**Regel**: Beschreibend + Typ-spezifisch
```python
# ✅ RICHTIG: Klare Model-Felder
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ai_edited_at = models.DateTimeField(null=True, blank=True)
    ai_agent_last_used = models.CharField(max_length=50, blank=True)

# ❌ FALSCH: Unklare Felder
class Book(models.Model):
    data = models.JSONField()           # Was für Daten?
    status = models.CharField()         # Welcher Status?
    agent = models.CharField()          # Welcher Agent? Aktuell oder letzter?
```

### 5. **JavaScript Function Naming**
**Regel**: `{verb}{Entity}{Context}` (camelCase)
```javascript
// ✅ RICHTIG: Eindeutige JS-Funktionen
function openAiAgentEditModal(bookId, agentType) {}
function executeAiAgentWithPrompt(bookId, agentName, prompt) {}
function updateBookContentFromAi(bookId, newContent) {}
function validateAiAgentParameters(params) {}

// ❌ FALSCH: Verwirrende JS-Funktionen
function openModal() {}              // Welches Modal?
function executeAgent() {}           // Welcher Agent? Wie?
function updateContent() {}          // Welcher Content?
```

## 🔧 SPECIFIC CONVENTIONS

### API Parameter Naming
```python
# ✅ RICHTIG: Konsistente Parameter-Namen
{
    'book_id': 123,
    'ai_agent_type': 'concept_designer',
    'ai_prompt_text': 'Improve the storyline',
    'content_to_edit': 'Original content...',
    'editing_instructions': 'Make it more engaging'
}

# ❌ FALSCH: Inkonsistente Parameter
{
    'id': 123,                    # ID von was?
    'agent': 'concept_designer',  # Zu kurz
    'prompt': 'Improve...',       # Zu generisch
    'content': 'Original...',     # Welcher Content?
}
```

### CSS Class Naming (BEM-inspired)
```css
/* ✅ RICHTIG: Strukturierte CSS-Klassen */
.ai-agent-dashboard {}
.ai-agent-dashboard__header {}
.ai-agent-dashboard__agent-card {}
.ai-agent-dashboard__agent-card--active {}

.book-edit-modal {}
.book-edit-modal__content {}
.book-edit-modal__ai-section {}

/* ❌ FALSCH: Generische CSS-Klassen */
.dashboard {}
.card {}
.modal {}
.content {}
```

## 🚨 ANTI-PATTERNS (zu vermeiden)

### 1. **Duplicate Function Names**
```python
# ❌ PROBLEM: Identische Namen für verschiedene Zwecke
def agent_edit_content():     # Zeile 625
def agent_edit_content():     # Zeile 759 - Duplikat!
def agent_edit_content():     # Zeile 893 - Duplikat!

# ✅ LÖSUNG: Spezifische Namen
def ai_agent_edit_content_v1():
def ai_agent_edit_content_with_validation():
def ai_agent_execute_prompt():  # Andere Funktion, anderer Name
```

### 2. **Generic Route Names**
```python
# ❌ PROBLEM: Verwirrende Routen
path('edit/', edit_content),           # Edit was?
path('execute/', execute_something),   # Execute was?
path('agent/', agent_handler),         # Welcher Agent?

# ✅ LÖSUNG: Spezifische Routen
path('ai-agents/edit-content/', ai_agent_edit_content),
path('ai-agents/execute-prompt/', ai_agent_execute_prompt),
path('ai-agents/dashboard/', ai_agent_dashboard),
```

### 3. **Ambiguous Variable Names**
```python
# ❌ PROBLEM: Mehrdeutige Variablen
agent = request.POST.get('agent')        # Welcher Agent?
content = request.POST.get('content')    # Welcher Content?
result = process_data(content)           # Was für ein Result?

# ✅ LÖSUNG: Eindeutige Variablen
selected_ai_agent = request.POST.get('selected_agent')
content_to_edit = request.POST.get('current_content')
ai_edited_result = process_with_ai_agent(content_to_edit)
```

## 📋 NAMING CHECKLIST

### Before Creating Functions/Views:
- [ ] Name erklärt Zweck und Kontext
- [ ] Keine Duplikate mit ähnlichen Namen
- [ ] Konsistent mit bestehenden Patterns
- [ ] Eindeutig unterscheidbar von anderen Funktionen

### Before Creating Routes:
- [ ] RESTful und hierarchisch strukturiert
- [ ] Eindeutige URL-Namen
- [ ] Konsistent mit App-Namespace
- [ ] Keine Verwechslung mit anderen Routes möglich

### Before Creating Templates:
- [ ] App-Prefix + Entity + Action Pattern
- [ ] Eindeutig identifizierbar
- [ ] Konsistent mit Template-Struktur
- [ ] Keine Namenskonflikte

## 🎯 CURRENT CASE STUDY: Lesson Learned

### Problem:
```python
# Verwirrende Namen führten zu falschem Debugging
def agent_edit_content():      # Dachten, das wird verwendet
def execute_with_prompt():     # Tatsächlich verwendete Funktion
```

### Lösung:
```python
# Eindeutige Namen hätten Verwirrung vermieden
def ai_agent_edit_content_main():     # Hauptfunktion für AI-Editing
def ai_agent_execute_prompt_stage3():  # Stage 3 des 3-Stufen-Workflows
```

## 📈 BENEFITS

1. **Debugging-Effizienz**: Sofort klar, welche Funktion verwendet wird
2. **Code-Verständlichkeit**: Namen erklären Zweck und Kontext
3. **Duplikations-Vermeidung**: Eindeutige Namen verhindern Verwechslungen
4. **Team-Produktivität**: Konsistente Patterns für alle Entwickler
5. **Maintenance**: Einfachere Code-Navigation und -wartung

## 🚀 ENFORCEMENT

### Memory-Bank-Regel:
- **Jede neue Funktion/Route/Template** MUSS diese Naming Conventions befolgen
- **Code Review** prüft Naming-Konsistenz
- **Refactoring** bestehender Code nach diesen Standards

Diese Conventions hätten den "Missing required parameters" Bug durch klare Funktionsnamen sofort vermieden!
