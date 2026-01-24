# BF Agent Dokumentationssystem - Bewertung & Implementierungsvorschlag

**Datum:** 15.01.2026  
**Status:** Analyse abgeschlossen

---

## 1. Bewertung des aktuellen Systems

### ✅ Stärken

| Aspekt | Bewertung | Details |
|--------|-----------|---------|
| **Sphinx-Framework** | ⭐⭐⭐⭐⭐ | Industriestandard, ausgereift, erweiterbar |
| **Furo Theme** | ⭐⭐⭐⭐⭐ | Modern, Dark Mode, responsive |
| **MyST Parser** | ⭐⭐⭐⭐⭐ | Markdown + RST flexibel kombinierbar |
| **Struktur** | ⭐⭐⭐⭐ | Logisch: guides/, domains/, reference/, developer/ |
| **Makefile** | ⭐⭐⭐⭐⭐ | Vollständig mit live, apidocs, linkcheck, deploy |
| **conf.py** | ⭐⭐⭐⭐⭐ | Django-ready, Intersphinx, Napoleon-Docstrings |
| **SSOT-Ansatz** | ⭐⭐⭐⭐⭐ | autodoc aus Docstrings = Single Source of Truth |

### ⚠️ Verbesserungspotential

| Aspekt | Problem | Lösung |
|--------|---------|--------|
| **Pfade in conf.py** | `bf_agent` statt `apps` | Korrigieren zu `apps.*` |
| **Viele Stub-Dateien** | 80% der Docs = Platzhalter | Auto-Generation + Templates |
| **Kein CI/CD** | Manuelle Builds | GitHub Actions hinzufügen |
| **Keine Versionierung** | Keine Multi-Version-Docs | sphinx-multiversion |
| **Cascade-Integration** | Keine automatische Update-Hooks | MCP-Tool erstellen |

---

## 2. Implementierungsvorschlag

### Phase 1: Foundation Fix (1-2 Stunden)

#### 1.1 Pfade korrigieren in conf.py

```python
# VORHER (falsch):
sys.path.insert(0, os.path.abspath('../../bf_agent'))

# NACHHER (korrekt für BF Agent Projekt):
sys.path.insert(0, os.path.abspath('../../../../'))  # Projekt-Root
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
```

#### 1.2 Verzeichnisstruktur verschieben

```
VORHER:                          NACHHER:
docs_v2/doku-system/docs/        docs/                (Projekt-Root)
                                 ├── source/
                                 ├── Makefile
                                 └── requirements.txt
```

**Begründung:** Standard-Sphinx-Position, einfacher für CI/CD

---

### Phase 2: Auto-Documentation (2-3 Stunden)

#### 2.1 Django-Apps dokumentieren

Erstelle `docs/source/reference/apps/` mit auto-generierten Docs:

```rst
.. autosummary::
   :toctree: generated
   :recursive:

   apps.writing_hub
   apps.control_center
   apps.cad_hub
   apps.expert_hub
   apps.core
```

#### 2.2 Handler auto-discovery

```python
# docs/scripts/generate_handler_docs.py
"""Generiert Handler-Dokumentation aus HandlerRegistry."""

from apps.core.models import Handler

def generate():
    handlers = Handler.objects.filter(is_active=True)
    for h in handlers:
        # RST-Datei pro Handler generieren
        ...
```

---

### Phase 3: Cascade-Integration (3-4 Stunden)

#### 3.1 MCP-Tool für Dokumentations-Updates

```python
# packages/bfagent_mcp/tools/doc_updater.py

@tool
def update_handler_docs(handler_code: str):
    """
    Aktualisiert die Dokumentation eines Handlers.
    Wird automatisch bei Handler-Änderungen aufgerufen.
    """
    # 1. Handler-Docstrings extrahieren
    # 2. RST/MD Datei aktualisieren
    # 3. Sphinx-Build triggern (optional)
```

#### 3.2 Post-Commit Hook

```yaml
# .github/workflows/docs.yml
name: Documentation

on:
  push:
    paths:
      - 'apps/**/handlers/**'
      - 'apps/**/models.py'
      - 'docs/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docs
        run: |
          pip install -r docs/requirements.txt
          cd docs && make html
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
```

---

### Phase 4: Content Templates (2 Stunden)

#### 4.1 Handler-Dokumentations-Template

```markdown
# {handler_name}

**Domain:** {domain}  
**Category:** {category}  
**AI-Enabled:** {ai_enabled}

## Übersicht

{description}

## Input Schema

```python
{input_schema}
```

## Output Schema

```python
{output_schema}
```

## Beispiel

```python
from apps.{domain}.handlers import {handler_class}

handler = {handler_class}()
result = await handler.execute(context)
```

## Konfiguration

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
{config_table}

## Changelog

{changelog}
```

#### 4.2 Domain-Dokumentations-Template

```markdown
# {domain_name} Domain

**Status:** {status}  
**Handler:** {handler_count}  
**AI-Coverage:** {ai_coverage}%

## Übersicht

{description}

## Handler

{handler_list}

## Models

{model_list}

## Workflows

{workflow_diagrams}
```

---

### Phase 5: Automatische Updates bei Änderungen

#### 5.1 Docstring-Standards durchsetzen

```python
# apps/core/handlers/base.py

class BaseHandler:
    """
    Basis-Handler für alle BF Agent Handler.
    
    Jeder Handler MUSS diese Docstring-Struktur haben:
    
    Attributes:
        input_schema: Pydantic-Schema für Eingabedaten
        output_schema: Pydantic-Schema für Ausgabedaten
        domain: Domain-Zugehörigkeit
        
    Example:
        >>> handler = MyHandler()
        >>> result = await handler.execute({"key": "value"})
        
    Note:
        Handler werden automatisch dokumentiert.
        Docstrings sind die EINZIGE Quelle der Wahrheit.
    """
```

#### 5.2 Pre-Commit Hook für Docstring-Check

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/pydocstyle
    rev: 6.3.0
    hooks:
      - id: pydocstyle
        args: ['--convention=google']
        files: 'apps/.*/handlers/.*\.py$'
```

---

## 3. Prioritäten-Matrix

| Phase | Aufwand | Impact | Priorität |
|-------|---------|--------|-----------|
| **1. Foundation Fix** | 1-2h | Hoch | 🔴 KRITISCH |
| **2. Auto-Documentation** | 2-3h | Sehr Hoch | 🔴 KRITISCH |
| **3. Cascade-Integration** | 3-4h | Hoch | 🟡 WICHTIG |
| **4. Content Templates** | 2h | Mittel | 🟢 NICE-TO-HAVE |
| **5. Automatische Updates** | 3h | Sehr Hoch | 🟡 WICHTIG |

---

## 4. Empfohlene Reihenfolge

```
Woche 1:
├── Phase 1: Foundation Fix (Tag 1)
├── Phase 2: Auto-Documentation (Tag 2-3)
└── Erste funktionierende Docs live

Woche 2:
├── Phase 3: Cascade-Integration (Tag 1-2)
├── Phase 5: Pre-Commit Hooks (Tag 3)
└── CI/CD Pipeline läuft

Woche 3+:
├── Phase 4: Content Templates
├── Bestehende Handler dokumentieren
└── Kontinuierliche Pflege
```

---

## 5. Quick-Start Befehle

```bash
# 1. Dependencies installieren
cd docs_v2/doku-system/docs
pip install -r requirements.txt

# 2. Docs bauen
make html

# 3. Live-Server starten
make live

# 4. API-Docs generieren
make apidocs
```

---

## 6. Nächste Schritte

1. **Sofort:** Phase 1 (Foundation Fix) durchführen
2. **Diese Woche:** Phase 2 (Auto-Documentation) implementieren
3. **Entscheidung:** Docs nach `docs/` verschieben oder in `docs_v2/` belassen?
4. **Langfristig:** Cascade-MCP-Tool für automatische Updates

---

## 7. Offene Fragen

- [ ] Soll die Dokumentation auf GitHub Pages oder eigenem Server gehostet werden?
- [ ] Sollen die Docs auf Deutsch oder Englisch sein? (aktuell: gemischt)
- [ ] Multi-Version-Support gewünscht? (v1.x, v2.x parallel)
- [ ] API-Key-Dokumentation: Wie mit sensiblen Infos umgehen?

---

**Fazit:** Das Dokumentationssystem ist **ausgezeichnet konzipiert** (Sphinx + Furo + MyST + autodoc). Die Hauptarbeit liegt in:
1. Pfad-Korrekturen für das BF Agent Projekt
2. Befüllen der Stub-Dateien mit echtem Content
3. CI/CD-Integration für automatische Updates
