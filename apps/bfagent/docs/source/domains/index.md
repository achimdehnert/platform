# Domains Übersicht

BF Agent unterstützt mehrere spezialisierte Domains, die jeweils eigene
Handler, Models und Workflows mitbringen.

## Verfügbare Domains

```{list-table}
:header-rows: 1
:widths: 20 40 20 20

* - Domain
  - Beschreibung
  - Handler
  - Status
* - 📚 [Books](books)
  - Automatisierte Bucherstellung mit KI
  - 12
  - ✅ Produktiv
* - 🎨 [Comics](comics)
  - Comic-Generierung mit Bild-KI
  - 8
  - ✅ Produktiv
* - 📐 [CAD Analysis](cad-analysis)
  - Technische Zeichnungsanalyse
  - 10
  - 🔄 Beta
* - ⚠️ [ExSchutz](exschutz)
  - Explosionsschutz-Dokumentation
  - 8
  - 🔄 Beta
```

## Architektur

Jede Domain folgt der gleichen Grundstruktur:

```
domains/
└── <domain_name>/
    ├── models.py       # Django Models
    ├── handlers/       # Domain-spezifische Handler
    │   ├── __init__.py
    │   ├── input.py    # Input Handler
    │   ├── process.py  # Processing Handler
    │   └── output.py   # Output Handler
    ├── schemas.py      # Pydantic Schemas
    ├── admin.py        # Django Admin Konfiguration
    └── api.py          # REST/GraphQL Endpoints
```

## Domain hinzufügen

Neue Domains können über das Template-System erstellt werden:

```bash
python manage.py create_domain --name medtrans --verbose-name "Medical Translation"
```

Dies generiert automatisch:

- Basis-Models
- Handler-Stubs
- Admin-Konfiguration
- Test-Fixtures

```{seealso}
- {doc}`/developer/handler-development` - Handler-Entwicklung
- {doc}`/reference/handlers` - Handler API-Referenz
```

## Domain-Konfiguration

Domains werden über die Datenbank konfiguriert (Zero-Hardcoding):

```python
# Admin: Domains → Domain Configuration

DomainConfig.objects.create(
    name="comics",
    verbose_name="Comic Creator",
    enabled=True,
    ai_provider="openai",
    default_model="gpt-4",
    rate_limit=100,
    config={
        "image_provider": "dalle3",
        "max_pages": 32,
        "default_style": "marvel"
    }
)
```

```{toctree}
:maxdepth: 2
:hidden:

books
comics
cad-analysis
exschutz
```
