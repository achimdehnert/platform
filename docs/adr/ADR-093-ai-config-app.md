---
status: proposed
date: 2026-02-27
decision-makers: Achim Dehnert
---

# ADR-093: AI & LLM Configuration App in dev-hub

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-27 |
| **Author** | Achim Dehnert |
| **Related** | ADR-091 (Platform Operations Hub), ADR-044 (MCP-Hub Architecture) |

---

## Context

Das Control Center (control-center.iil.pet) enthält mehrere Feature-Bereiche:

1. **AI & LLM Konfiguration** - LLMs, Agents, MCP Hub
2. **Test Studio & Bug Management** - Bugs, Features, Kanban
3. **Developer Tools** - Model Check, Code Review, Migrations
4. **Initiativen & Features** - Konzepte, Feature Planning

**Analyse:**
- Test/Bug Management → GitHub Issues + Projects (bereits migriert)
- Developer Tools → GitHub Actions, ADRs, Platform Repo (bereits vorhanden)
- Initiativen/Features → GitHub Projects + Milestones (bereits migriert)
- **AI & LLM Konfiguration → Noch nicht in dev-hub**

## Decision

**Neubau einer minimalen `ai_config` App in dev-hub** statt Migration des alten Codes.

### Begründung

| Kriterium | Migration | Neubau |
|-----------|-----------|--------|
| Code-Qualität | Inkonsistenter Legacy-Code | Clean Architecture |
| Abhängigkeiten | Viele ungenutzte Models | Nur benötigte Features |
| Wartbarkeit | Schwer zu verstehen | Einfach und klar |
| Zeitaufwand | Ähnlich (Cleanup nötig) | Ähnlich (aber sauberer) |

### Scope

**In Scope:**
- LLM-Verwaltung (CRUD)
- LLM-Test (Quick-Test mit Prompt)
- Provider-Unterstützung (OpenAI, Anthropic, Azure, Ollama)
- API-Key-Management (verschlüsselt)

**Out of Scope (später):**
- Agent-Verwaltung (komplexer, aktuell 0 aktiv)
- MCP Hub (eigene App, siehe ADR-044)
- Usage-Tracking/Kosten (nice-to-have)

## Implementation

### App-Struktur

```
apps/ai_config/
├── __init__.py
├── admin.py           # Django Admin für LLMs
├── apps.py
├── models.py          # LLM, Provider
├── views.py           # Dashboard, CRUD Views
├── services.py        # LLM-Test, API-Calls
├── urls.py
├── forms.py
└── templates/
    └── ai_config/
        ├── dashboard.html
        ├── llm_list.html
        ├── llm_form.html
        └── llm_test.html
```

### Models

```python
class LLMProvider(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"
    AZURE = "azure", "Azure OpenAI"
    OLLAMA = "ollama", "Ollama (Local)"

class LLM(TenantAwareModel):
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=20, choices=LLMProvider.choices)
    model_id = models.CharField(max_length=100)  # e.g., gpt-4, claude-3-opus
    api_key = models.TextField(blank=True)  # encrypted
    api_endpoint = models.URLField(blank=True)  # for Azure/Ollama
    is_active = models.BooleanField(default=True)
    
    # Optional settings
    max_tokens = models.IntegerField(default=4096)
    temperature = models.FloatField(default=0.7)
    
    class Meta:
        db_table = "ai_config_llms"
```

### URLs

```
/ai-config/                    # Dashboard
/ai-config/llms/               # LLM Liste
/ai-config/llms/create/        # LLM erstellen
/ai-config/llms/<id>/          # LLM bearbeiten
/ai-config/llms/<id>/test/     # LLM testen
```

## Migration

### Daten-Export aus Control Center

```sql
SELECT name, provider, llm_name, api_key, api_endpoint, 
       max_tokens, temperature, is_active
FROM llms WHERE is_active = true;
```

### Import in dev-hub

Management Command: `python manage.py import_llms --file=llms.json`

## Consequences

### Positive
- Sauberer, wartbarer Code
- Keine Legacy-Abhängigkeiten
- Tenant-aware von Anfang an
- Einfache Erweiterbarkeit

### Negative
- Initiale Entwicklungszeit
- Daten müssen manuell migriert werden

### Neutral
- Control Center kann parallel weiterlaufen
- Schrittweise Ablösung möglich

## Timeline

| Phase | Aufgabe | Zeitrahmen |
|-------|---------|------------|
| 1 | Models + Admin | 1h |
| 2 | Views + Templates | 2h |
| 3 | LLM-Test Service | 1h |
| 4 | Daten-Migration | 30min |

---

## References

- [ADR-091: Platform Operations Hub](./ADR-091-platform-operations-hub.md)
- [ADR-044: MCP-Hub Architecture](./ADR-044-mcp-hub-architecture.md)
- [Control Center LLM Models](https://github.com/achimdehnert/bfagent/blob/main/apps/bfagent/models_main.py)
