# BF Agent Dokumentations-Konzept

**Datum:** 15.01.2026  
**Prinzip:** Nur dokumentieren, was existiert und funktioniert

---

## 1. Analyse: Existierende Apps & Status

### ✅ Production-Ready (Voll dokumentieren)

| App | Models | Views | Handlers | Priorität |
|-----|--------|-------|----------|-----------|
| **writing_hub** | ✅ | 8 | 5 | 🔴 HOCH |
| **cad_hub** | ✅ | 7 | 5 | 🔴 HOCH |
| **control_center** | ✅ | 6 | - | 🟡 MITTEL |
| **research** | ✅ | ✅ | ✅ | 🟡 MITTEL |
| **medtrans** | ✅ | ✅ | 4 | 🟡 MITTEL |
| **mcp_hub** | ✅ | ✅ | - | 🟡 MITTEL |

### 🟡 Beta (Basis-Dokumentation)

| App | Models | Views | Handlers | Priorität |
|-----|--------|-------|----------|-----------|
| **expert_hub** | - | ✅ | ✅ | 🟢 NIEDRIG |
| **presentation_studio** | ✅ | ✅ | ✅ | 🟢 NIEDRIG |
| **dlm_hub** | ✅ | ✅ | - | 🟢 NIEDRIG |

### 🔴 Nicht dokumentieren (noch nicht realisiert)

- `comic` Domain (nur geplant)
- `graph_core` (intern)
- `genagent` (experimentell)
- `image_generation` (Hilfsfunktion)

---

## 2. Dokumentationsstruktur (Neu)

```
docs/source/
├── index.rst                    # Landing Page
├── guides/
│   ├── quickstart.md           ✅ BEHALTEN
│   ├── installation.md         ✅ BEHALTEN  
│   ├── configuration.md        ✅ BEHALTEN
│   └── ai-integration.md       ✅ BEHALTEN
│
├── hubs/                        # NEU: Pro Hub eine Seite
│   ├── index.md                # Hub-Übersicht
│   ├── writing-hub.md          # Writing Hub komplett
│   ├── cad-hub.md              # CAD Hub komplett
│   ├── control-center.md       # Control Center
│   ├── research-hub.md         # Research Hub
│   ├── mcp-hub.md              # MCP Hub
│   └── expert-hub.md           # Expert Hub (Beta)
│
├── reference/                   # API-Referenz
│   ├── handlers.rst            # Handler-Übersicht (autodoc)
│   ├── models.rst              # Model-Übersicht (autodoc)
│   └── schemas.rst             # Pydantic Schemas
│
├── developer/
│   ├── architecture.md         ✅ BEHALTEN
│   ├── handler-development.md  # Erweitern
│   └── contributing.md         ✅ BEHALTEN
│
└── changelog.md                ✅ BEHALTEN
```

### Entfernen (nicht realisiert):
- `domains/comics.md` ❌
- `domains/exschutz.md` ❌ (→ expert-hub.md)
- `guides/workflows.md` ❌ (→ in Hub-Docs integrieren)
- `guides/django-admin.md` ❌ (→ control-center.md)

---

## 3. Auto-Documentation Strategie

### Phase 2A: Autodoc für existierende Module

```python
# In handlers.rst - NUR existierende Handler
.. automodule:: apps.writing_hub.handlers
   :members:
   :show-inheritance:

.. automodule:: apps.cad_hub.handlers
   :members:
   :show-inheritance:

.. automodule:: apps.research.handlers
   :members:
   :show-inheritance:
```

### Phase 2B: Model-Dokumentation

```python
# In models.rst - NUR existierende Models
.. automodule:: apps.writing_hub.models
   :members:
   :show-inheritance:

.. automodule:: apps.cad_hub.models
   :members:
   :show-inheritance:

.. automodule:: apps.control_center.models
   :members:
   :show-inheritance:
```

---

## 4. Cascade-Integration (Phase 3)

### MCP-Tool: `bfagent_update_documentation`

```python
@tool
def update_documentation(
    app_name: str,
    doc_type: str = "handler"  # handler | model | view
):
    """
    Aktualisiert die Dokumentation für eine App.
    
    Workflow:
    1. Scanne App für Handler/Models/Views
    2. Extrahiere Docstrings
    3. Generiere/Update RST-Datei
    4. Sphinx-Build triggern (optional)
    """
```

### Automatische Trigger

| Event | Aktion |
|-------|--------|
| Handler erstellt/geändert | → `update_documentation(app, "handler")` |
| Model geändert | → `update_documentation(app, "model")` |
| Bugfix abgeschlossen | → Changelog-Eintrag hinzufügen |

---

## 5. Implementierungsplan

### Woche 1: Struktur aufräumen

1. **Nicht-existierende Docs entfernen:**
   - `domains/comics.md`
   - `domains/exschutz.md`
   - `guides/workflows.md`

2. **Hub-Dokumentation erstellen:**
   - `hubs/writing-hub.md` (aus domains/books.md + guides)
   - `hubs/cad-hub.md` (aus domains/cad-analysis.md)

### Woche 2: Autodoc aktivieren

1. **Django im Build initialisieren**
2. **Autodoc für:**
   - `apps.writing_hub.handlers`
   - `apps.writing_hub.models`
   - `apps.cad_hub.models`
   - `apps.control_center.models`

### Woche 3: MCP-Integration

1. **MCP-Tool erstellen:** `bfagent_update_documentation`
2. **Pre-Commit Hook:** Docstring-Validierung
3. **CI/CD:** Automatischer Doc-Build

---

## 6. Docstring-Standard (Pflicht für Dokumentation)

```python
class OutlineHandler(BaseHandler):
    """
    Generiert Buchoutlines basierend auf Story-Strukturen.
    
    Unterstützt Save the Cat, Hero's Journey, Three-Act Structure.
    
    Attributes:
        input_schema: OutlineInput - Projekt-ID und Struktur-Typ
        output_schema: OutlineOutput - Generiertes Outline
        domain: writing_hub
        
    Example:
        >>> handler = OutlineHandler()
        >>> result = await handler.execute({
        ...     "project_id": 123,
        ...     "structure": "save_the_cat"
        ... })
        >>> print(result.beats)
        
    Note:
        Benötigt konfiguriertes LLM für AI-gestützte Generierung.
        
    See Also:
        - :class:`ChapterWriterHandler` - Schreibt Kapitel basierend auf Outline
        - :doc:`/hubs/writing-hub` - Writing Hub Dokumentation
    """
```

---

## 7. Entscheidungsmatrix

| Feature | Existiert? | Funktioniert? | Dokumentieren? |
|---------|------------|---------------|----------------|
| Writing Hub | ✅ | ✅ | ✅ JA |
| CAD Hub | ✅ | ✅ | ✅ JA |
| Control Center | ✅ | ✅ | ✅ JA |
| Research Hub | ✅ | ✅ | ✅ JA |
| MedTrans | ✅ | ✅ | ✅ JA |
| MCP Hub | ✅ | ✅ | ✅ JA |
| Expert Hub | ✅ | 🟡 | 🟡 Basis |
| Comic Domain | ❌ | ❌ | ❌ NEIN |
| ExSchutz | 🟡 | 🟡 | 🟡 Basis |

---

## 8. Nächste Schritte

**Sofort:**
1. Nicht-existierende Docs entfernen
2. `hubs/` Verzeichnis erstellen
3. Writing Hub komplett dokumentieren

**Diese Woche:**
4. Autodoc für reale Module aktivieren
5. MCP-Tool Prototyp

**Entscheidung erforderlich:**
- [ ] Docs auf Deutsch oder Englisch?
- [ ] Docs nach `docs/` verschieben oder in `docs_v2/` belassen?
