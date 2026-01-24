# Django Template-Context Variable Management & Best Practices

## Proaktive Template-Context-Entwicklung

### Entwicklungsansatz: Prevention over Debugging
Anstatt Template-Context-Probleme zu debuggen, sollten sie bereits bei der Erstellung vermieden werden durch:
- **Konsistente Namenskonventionen** von Anfang an
- **Template-First Development** - Template-Variablen zuerst definieren
- **Context-Contract Definition** - Klare Vereinbarungen zwischen Frontend und Backend

### Häufiges Problem Identifiziert
**TEMPLATE ERWARTET `configurations`, BACKEND LIEFERT `configs`**

#### Symptome (wenn nicht proaktiv verhindert)
- Backend erstellt erfolgreich LLM-Konfigurationen
- Erfolgs-Nachrichten werden angezeigt
- Template zeigt "No configurations found" obwohl Daten vorhanden sind
- Empty-State wird angezeigt statt der erstellten Konfigurationen

### Root Cause Analysis
```python
# Backend Context (llm_views.py)
context = {
    'providers': providers,
    'configs': configs,  # ❌ Backend liefert 'configs'
    'available_models': available_models,
}

# Template Erwartung (llm_model_management.html)
{% if configurations %}  # ❌ Template erwartet 'configurations'
    {% for config in configurations %}
        <!-- Konfigurationen anzeigen -->
    {% endfor %}
{% else %}
    <div class="empty-state">No configurations found</div>  # ✅ Wird angezeigt
{% endif %}
```

### Lösung
```python
# Backend Context korrigiert
context = {
    'providers': providers,
    'configs': configs,
    'configurations': configs,  # ✅ Template-Variable hinzugefügt
    'available_models': available_models,
}
```

## Proaktive Entwicklungsmethodik

### 1. Template-First Development
```html
<!-- SCHRITT 1: Template-Variablen zuerst definieren -->
{% if configurations %}
    {% for config in configurations %}
        <div class="config-item">{{ config.display_name }}</div>
    {% endfor %}
{% else %}
    <div class="empty-state">No configurations found</div>
{% endif %}
```

### 2. Context-Contract Definition
```python
# SCHRITT 2: Backend-Context nach Template-Anforderungen erstellen
class LLMModelManagementView(View):
    """
    Template Contract:
    - configurations: List[LLMConfiguration] - Alle Konfigurationen
    - providers: List[LLMProvider] - Alle Provider
    - available_models: List[str] - Verfügbare Modelle
    """
    def get(self, request):
        context = {
            'configurations': LLMConfiguration.objects.all(),  # Template-Variable
            'providers': LLMProvider.objects.all(),
            'available_models': self.get_available_models(),
        }
        return render(request, 'llm_model_management.html', context)
```

### 3. Konsistente Namenskonventionen
```python
# ✅ RICHTIG: Konsistente Plural-Forms
context = {
    'configurations': configs,  # Plural für Listen
    'providers': providers,     # Plural für Listen
    'selected_config': config,  # Singular für Einzelobjekte
}

# ❌ FALSCH: Inkonsistente Namensgebung
context = {
    'configs': configs,         # Inkonsistent mit Template
    'provider_list': providers, # Unnötig kompliziert
    'config': config,          # Mehrdeutig
}
```

## Debugging-Methodik (Falls erforderlich)

### 1. Template-Variable Identifizierung
```bash
# Suche nach Template-Variablen
grep -n "configurations" template.html
grep -n "{% if" template.html
grep -n "{% for" template.html
```

### 2. Backend-Context Analyse
```python
# View-Methode prüfen
def get(self, request):
    context = {
        # Alle Context-Variablen auflisten
    }
    return render(request, 'template.html', context)
```

### 3. Variable-Mismatch Identifizierung
- Template-Variablen vs. Backend-Context vergleichen
- Konsistenz der Namenskonvention prüfen
- Typos und Case-Sensitivity beachten

### 4. Schnelle Lösung
```python
# Beide Variablen im Context bereitstellen
context = {
    'configs': configs,           # Backend-Konsistenz
    'configurations': configs,    # Template-Kompatibilität
}
```

## Best Practices

### Konsistente Namenskonvention
- **Template und Backend:** Gleiche Variable-Namen verwenden
- **Plural-Forms:** Konsistent verwenden (`config` vs. `configs` vs. `configurations`)
- **Naming Convention:** Snake_case für Backend, gleiche Namen für Template

### Context-Dokumentation
```python
def get(self, request):
    """
    Context Variables:
    - providers: List[LLMProvider] - Alle verfügbaren Provider
    - configurations: List[LLMConfiguration] - Alle Konfigurationen
    - available_models: List[str] - Verfügbare Model-Namen
    """
    context = {
        'providers': providers,
        'configurations': configs,  # Dokumentierte Variable
    }
```

### Template-Tests
```python
def test_template_context(self):
    """Test Template-Rendering mit korrekten Context-Variablen"""
    response = self.client.get('/llm-management/')
    self.assertContains(response, 'configurations')
    self.assertIn('configurations', response.context)
```

## Häufige Template-Context-Probleme

### 1. Variable-Name-Mismatch
```python
# ❌ Falsch
context = {'items': data}
# Template: {% for item in objects %}

# ✅ Richtig
context = {'objects': data}
# Template: {% for item in objects %}
```

### 2. Plural/Singular Inkonsistenz
```python
# ❌ Falsch
context = {'config': configs_list}
# Template: {% for config in configs %}

# ✅ Richtig
context = {'configs': configs_list}
# Template: {% for config in configs %}
```

### 3. Case-Sensitivity
```python
# ❌ Falsch
context = {'Configurations': configs}
# Template: {% for config in configurations %}

# ✅ Richtig
context = {'configurations': configs}
# Template: {% for config in configurations %}
```

## Debugging-Tools

### Django Debug Toolbar
```python
# Context-Variablen in Debug-Panel anzeigen
INSTALLED_APPS = [
    'debug_toolbar',
]
```

### Template-Debug
```html
<!-- Template-Debug: Context-Variablen anzeigen -->
{% load debug %}
{% debug %}

<!-- Oder spezifische Variable prüfen -->
{{ configurations|length }}
{{ configurations|default:"No configurations found" }}
```

### Backend-Debug
```python
import logging
logger = logging.getLogger(__name__)

def get(self, request):
    context = {'configurations': configs}
    logger.debug(f"Context keys: {context.keys()}")
    logger.debug(f"Configurations count: {len(configs)}")
    return render(request, 'template.html', context)
```

## Lessons Learned

### Template-Context-Probleme sind schwer zu debuggen
- **Keine Fehler:** Django wirft keine Exceptions bei fehlenden Variablen
- **Silent Failure:** Template zeigt Empty-State statt Fehler
- **Debugging-Aufwand:** Systematische Prüfung erforderlich

### Systematische Herangehensweise erforderlich
1. **Template-Variablen identifizieren**
2. **Backend-Context analysieren**
3. **Variable-Mismatch finden**
4. **Konsistenz sicherstellen**

### Präventive Maßnahmen
- **Code-Reviews:** Template und Backend gemeinsam reviewen
- **Naming Conventions:** Projekt-weite Standards definieren
- **Template-Tests:** Automatisierte Tests für Template-Rendering

## Session Details
- **Datum:** 05.08.2025
- **Kontext:** LiteLLM Multi-Provider Integration
- **Betroffene Dateien:**
  - `agent_management/services_new/llm_views.py`
  - `agent_management/templates/agent_management/llm_model_management.html`
- **Problem-ID:** Template-Context-Variable-Mismatch
- **Lösung:** Beide Variablen (`configs` und `configurations`) im Context bereitstellen

## Verwandte Probleme
- Django Template Variable Scoping
- Context Processor Issues
- Template Inheritance Variable Passing
- Form Context Variable Naming

---
*Dokumentiert als Teil der Django Development Standards für zukünftige Referenz und Debugging.*
