# Refactoring Rules - Separation of Concerns & Code Quality

## 🎯 CORE PRINCIPLES

### 1. **DRY (Don't Repeat Yourself)**
**Regel**: Eine Funktion existiert nur EINMAL im gesamten Codebase
```python
# ❌ FALSCH: Mehrfache identische Funktionen
def agent_edit_content(request, book_id):  # Zeile 625
def agent_edit_content(request, book_id):  # Zeile 759
def agent_edit_content(request, book_id):  # Zeile 893 ← Python nutzt nur diese!

# ✅ RICHTIG: Eine einzige, gut strukturierte Funktion
def agent_edit_content(request, book_id):
    """Single source of truth für Agent-Content-Editing"""
```

### 2. **Single Responsibility Principle (SRP)**
**Regel**: Jede Funktion hat genau EINE Verantwortlichkeit
```python
# ❌ FALSCH: Monolithische Funktion
def agent_edit_content(request, book_id):
    # Parameter validation
    # Agent configuration
    # OpenAI API calls
    # Content processing
    # Database updates
    # Response formatting
    # Error handling
    # ... (200+ Zeilen)

# ✅ RICHTIG: Aufgeteilte Verantwortlichkeiten
def agent_edit_content(request, book_id):
    """Main orchestrator - delegates to specialized functions"""
    params = validate_edit_parameters(request)
    agent_config = get_agent_configuration(params['selected_agent'])
    processed_content = process_content_with_ai(params, agent_config)
    update_book_content(book_id, processed_content)
    return format_success_response(processed_content)

def validate_edit_parameters(request):
    """Dedicated parameter validation"""

def get_agent_configuration(agent_type):
    """Dedicated agent config retrieval"""

def process_content_with_ai(params, config):
    """Dedicated AI processing"""
```

## 🔍 REFACTORING PATTERNS

### Pattern 1: **Function Extraction**
```python
# Vor Refactoring: Monolithische Funktion
def large_function():
    # 50 Zeilen Parameter-Validierung
    # 30 Zeilen Business Logic
    # 20 Zeilen Error Handling

# Nach Refactoring: Aufgeteilte Funktionen
def large_function():
    params = validate_parameters()
    result = execute_business_logic(params)
    return handle_response(result)
```

### Pattern 2: **Configuration Extraction**
```python
# ❌ FALSCH: Hardcoded Konfiguration in Funktion
def agent_edit_content():
    agent_configs = {
        'concept_designer': 'Refine and enhance...',
        'writer': 'Improve the writing style...',
        # ... 50 Zeilen Config
    }

# ✅ RICHTIG: Separate Konfigurationsdatei
# agents_config.py
AGENT_CONFIGURATIONS = {
    'concept_designer': {
        'description': 'Refine and enhance story concepts',
        'temperature': 0.7,
        'max_tokens': 2000
    }
}

# views.py
from .agents_config import AGENT_CONFIGURATIONS
```

### Pattern 3: **Error Handling Extraction**
```python
# ❌ FALSCH: Duplizierte Error-Handling-Logik
def function_a():
    try:
        # logic
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def function_b():
    try:
        # logic
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ✅ RICHTIG: Zentralisiertes Error Handling
def handle_api_error(func):
    """Decorator für einheitliches Error Handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=500)
    return wrapper

@handle_api_error
def function_a():
    # Nur Business Logic, kein Error Handling
```

## 🚨 ANTI-PATTERNS (zu vermeiden)

### 1. **Copy-Paste Programming**
```python
# ❌ Identische Funktionen an verschiedenen Stellen
# agents_ui/views.py:625 - def agent_edit_content()
# agents_ui/views.py:759 - def agent_edit_content()
# agents_ui/views.py:893 - def agent_edit_content()
```

### 2. **God Functions**
```python
# ❌ Eine Funktion macht alles (200+ Zeilen)
def do_everything():
    # Parameter validation
    # Database queries
    # API calls
    # File operations
    # Email sending
    # Logging
    # Response formatting
```

### 3. **Magic Numbers/Strings**
```python
# ❌ FALSCH: Hardcoded Values
if agent_type == "concept_designer":
    temperature = 0.7
    max_tokens = 2000

# ✅ RICHTIG: Named Constants
AGENT_TEMPERATURE = {
    'concept_designer': 0.7,
    'writer': 0.8
}
```

## 🔧 REFACTORING CHECKLIST

### Before Refactoring:
- [ ] Identifiziere duplizierte Funktionen
- [ ] Analysiere Funktionslänge (>50 Zeilen = Refactoring-Kandidat)
- [ ] Prüfe Cyclomatic Complexity (>10 = zu komplex)
- [ ] Suche nach Copy-Paste-Code

### During Refactoring:
- [ ] Extrahiere kleinere, fokussierte Funktionen
- [ ] Verschiebe Konfiguration in separate Dateien
- [ ] Implementiere einheitliches Error Handling
- [ ] Verwende aussagekräftige Funktionsnamen

### After Refactoring:
- [ ] Teste alle betroffenen Funktionen
- [ ] Aktualisiere Dokumentation
- [ ] Überprüfe Performance-Impact
- [ ] Code Review durchführen

## 🎯 CURRENT CASE STUDY: agent_edit_content

### Problem:
```python
# agents_ui/views.py hat 3 identische Funktionen:
def agent_edit_content(request, book_id):  # Zeile 625 - veraltet
def agent_edit_content(request, book_id):  # Zeile 759 - veraltet
def agent_edit_content(request, book_id):  # Zeile 893 - aktiv
```

### Lösung:
1. **Entferne** die ersten beiden Funktionen (Zeilen 625-758, 759-892)
2. **Behalte** nur die letzte, aktuellste Version (Zeile 893+)
3. **Implementiere** Parameter-Validierung in der aktiven Funktion
4. **Extrahiere** AI-Processing in separate Funktion

## 📋 ENFORCEMENT RULES

### Memory-Bank-Regeln:
1. **Eine Funktion = Ein Ort**: Keine duplizierten Funktionsdefinitionen
2. **Maximale Funktionslänge**: 50 Zeilen
3. **Single Responsibility**: Eine Funktion, eine Aufgabe
4. **DRY Principle**: Code-Duplikation vermeiden
5. **Configuration Separation**: Configs in separate Dateien

### Code Review Checklist:
- [ ] Keine duplizierten Funktionen
- [ ] Funktionen unter 50 Zeilen
- [ ] Aussagekräftige Namen
- [ ] Einheitliches Error Handling
- [ ] Konfiguration externalisiert
