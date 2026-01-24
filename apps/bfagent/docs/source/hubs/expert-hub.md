# Expert Hub

<!-- Cache-Bust: 2026-01-21T17:40 -->
**Status:** 🟢 Production  
**Domain:** `expert_hub`  
**URL:** `/expert-hub/`

---

## Übersicht

Der Expert Hub unterstützt bei der Erstellung von Explosionsschutz-Dokumenten nach BetrSichV und ATEX.
Er bietet einen geführten Workflow durch alle 13 Phasen eines Ex-Schutz-Dokuments mit KI-Unterstützung.

## Features

### Kern-Funktionen
- **13-Phasen-Workflow:** Vollständiger Workflow für Ex-Schutz-Dokumente
- **Zoneneinteilung:** ATEX-konforme Zonen-Klassifizierung mit Berechnungs-Tools
- **Dokument-Management:** PDF-Upload mit automatischer SDB-Extraktion
- **Corporate Design:** Template-Upload für einheitliches Dokumenten-Design
- **DOCX-Export:** Generierung professioneller Word-Dokumente

### KI-Integration (Neu!)
- **HTMX-basierte Generierung:** Asynchrone KI-Inhaltsgenerierung mit Live-Feedback
- **LLM Gateway:** Integration über MCP HTTP Gateway (`http://localhost:8100`)
- **Modell:** GPT-4o-mini (konfigurierbar)
- **Spinner-Feedback:** Visueller Ladezustand während der Generierung
- **Smart Content Merger:** Intelligentes Zusammenführen von KI- und manuellem Inhalt

### Services
- **PDF Extractor:** Extraktion von Stoffdaten aus Sicherheitsdatenblättern
- **Content Merger:** Diff-basiertes Merging von Inhalten
- **LLM Client:** Synchroner HTTP-Client für LLM-Anfragen

## Architektur

```{mermaid}
flowchart TB
    subgraph Frontend
        A[Phase Detail View] --> B[HTMX Button]
        B --> C[Spinner Loading]
    end
    
    subgraph Backend
        D[api_ai_generate View] --> E[generate_phase_content_ai]
        E --> F[LLM Client]
        F --> G[LLM Gateway :8100]
    end
    
    B -->|POST| D
    D -->|HTML Response| C
    G -->|GPT-4o| F
```

## Workflow

```{mermaid}
flowchart LR
    A[Session erstellen] --> B[Dokumente hochladen]
    B --> C[Phase auswählen]
    C --> D[KI-Inhalt generieren]
    D --> E[Inhalt bearbeiten]
    E --> F[Speichern]
    F --> G[Nächste Phase]
    G --> C
    F --> H[DOCX exportieren]
```

## API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/expert-hub/` | GET | Dashboard |
| `/expert-hub/sessions/` | GET | Session-Liste |
| `/expert-hub/sessions/<id>/` | GET | Session-Detail |
| `/expert-hub/sessions/<id>/phase/<id>/` | GET/POST | Phase bearbeiten |
| `/expert-hub/api/sessions/<id>/phase/<id>/ai-generate/` | POST | KI-Generierung (HTMX) |
| `/expert-hub/sessions/<id>/document/preview/` | GET | Dokument-Vorschau |
| `/expert-hub/sessions/<id>/document/export/` | GET | DOCX-Export |

## Konfiguration

### LLM Gateway
```python
# settings.py oder Environment
LLM_GATEWAY_URL = "http://127.0.0.1:8100"
LLM_GATEWAY_TIMEOUT = 120.0
DEFAULT_LLM_MODEL = "gpt-4o-mini"
```

### Services starten
```bash
# LLM Gateway (MCP Hub)
cd mcp-hub && python -m llm_mcp.http_gateway

# Oder via start_services.sh
./start_services.sh
```

## Verwendung

### KI-Inhalt generieren
1. Session erstellen oder öffnen
2. Phase in der Dokumentstruktur auswählen
3. Button **"Inhalt generieren"** klicken
4. Spinner zeigt Ladezustand (10-30 Sek.)
5. Generierter Inhalt erscheint in der Karte
6. **"Übernehmen"** klickt Content in Textarea
7. Bei Bedarf bearbeiten und speichern

### Corporate Design
1. In Session-Detail → Corporate Design Karte
2. Word-Vorlage (.docx) hochladen
3. Optional: Firmenlogo hochladen
4. Export nutzt automatisch das Template

## Siehe auch

- {doc}`research-hub` - Research Hub mit ExSchutz-Recherche
- {doc}`/mcp/bfagent_mcp` - BF Agent MCP Tools
- {doc}`/guides/session_handling_controlling` - Session Management
