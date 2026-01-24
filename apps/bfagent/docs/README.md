# BF Agent Documentation

Dieses Verzeichnis enthält die Sphinx-basierte Dokumentation für BF Agent.

## Schnellstart

```bash
# Dependencies installieren
pip install -r requirements.txt

# HTML-Dokumentation erstellen
make html

# Live-Server mit Auto-Reload starten
make live
```

## Verzeichnisstruktur

```
docs/
├── Makefile              # Build-Kommandos
├── requirements.txt      # Python-Dependencies
├── source/
│   ├── conf.py          # Sphinx-Konfiguration
│   ├── index.rst        # Hauptseite
│   ├── _static/         # CSS, Bilder
│   ├── _templates/      # Custom Templates
│   ├── guides/          # Benutzerhandbücher
│   ├── domains/         # Domain-Dokumentation
│   ├── reference/       # API-Referenz
│   └── developer/       # Entwickler-Docs
└── build/               # Generierte Ausgabe
```

## Wichtige Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `make html` | HTML-Dokumentation erstellen |
| `make pdf` | PDF erstellen (benötigt LaTeX) |
| `make live` | Live-Server mit Auto-Reload |
| `make apidocs` | API-Docs aus Code generieren |
| `make linkcheck` | Links auf Gültigkeit prüfen |
| `make clean` | Build-Verzeichnis löschen |

## Dokumentation schreiben

### Markdown (empfohlen für Guides)

```markdown
# Mein Guide

Text mit **fett** und *kursiv*.

\`\`\`python
def hello():
    print("Hello!")
\`\`\`

\`\`\`{note}
Ein Hinweis mit MyST-Syntax.
\`\`\`
```

### reStructuredText (für API-Docs)

```rst
Meine Seite
===========

Text mit **fett** und *kursiv*.

.. code-block:: python

   def hello():
       print("Hello!")

.. note::
   Ein Hinweis.
```

### API-Dokumentation aus Docstrings

```rst
.. autoclass:: bf_agent.handlers.base.BaseHandler
   :members:
   :show-inheritance:
```

## Single Source of Truth

Die API-Dokumentation wird automatisch aus den Docstrings generiert.
Schreibe gute Docstrings im Google-Style:

```python
def process_data(input_data: dict, options: dict = None) -> dict:
    """
    Verarbeitet Eingabedaten.

    Args:
        input_data: Die zu verarbeitenden Daten.
        options: Optionale Verarbeitungsoptionen.

    Returns:
        Die verarbeiteten Daten.

    Raises:
        ValueError: Wenn input_data leer ist.

    Example:
        >>> result = process_data({"key": "value"})
    """
    pass
```

## Deployment

### GitHub Pages

```bash
make deploy-gh-pages
```

### ReadTheDocs

1. Repository mit ReadTheDocs verbinden
2. `.readthedocs.yaml` im Projekt-Root erstellen
3. Push triggert automatischen Build

### Lokaler Server

```bash
make deploy-local  # Kopiert nach /var/www/docs/bf-agent/
```

## Troubleshooting

### Sphinx findet Module nicht

Stelle sicher, dass der Pfad in `conf.py` korrekt ist:

```python
sys.path.insert(0, os.path.abspath('../..'))
```

### Django-Models werden nicht dokumentiert

Django muss vor dem Build initialisiert werden (bereits in `conf.py`):

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bf_agent.settings')
import django
django.setup()
```

### Mermaid-Diagramme werden nicht gerendert

Installiere die Mermaid-Extension:

```bash
pip install sphinxcontrib-mermaid
```

## Ressourcen

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [MyST Parser](https://myst-parser.readthedocs.io/)
- [Furo Theme](https://pradyunsg.me/furo/)
- [Google Docstring Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
