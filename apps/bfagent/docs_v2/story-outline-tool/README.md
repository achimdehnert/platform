# 📚 Story Outline Tool

Ein professionelles Python-Tool zum Strukturieren von Romanen und Geschichten.

## Features

- **Hierarchische Struktur**: Roman → Akt → Kapitel → Szene → Beat
- **Templates**: Drei-Akt-Struktur, Heldenreise, Save the Cat, Kishōtenketsu, 7-Point
- **Charakter-Management**: Verfolge Präsenz und POV-Szenen
- **Handlungsstränge**: Verwalte parallele Storylines
- **Szenen-Verbindungen**: Foreshadowing, Callbacks, Kontraste
- **Zeitleisten**: Story-Zeit vs. Erzähl-Zeit
- **Visualisierungen**: Mermaid-Diagramme, Markdown/HTML-Export
- **Analyse**: Pacing, Charakter-Präsenz, Fortschritt

## Installation

```bash
# Repository klonen
git clone <repo-url>
cd story-outline-tool

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Installieren
pip install -e .
```

## Schnellstart

### Neuen Roman erstellen

```bash
# Mit Template
story-outline novel create "Mein Thriller" --template three-act --genre thriller --words 90000

# Ohne Template
story-outline novel create "Mein Roman" --author "Max Mustermann"
```

### Verfügbare Templates anzeigen

```bash
story-outline template list
story-outline template show three-act
```

### Roman-Struktur anzeigen

```bash
story-outline novel list
story-outline novel show <novel-id> --full
```

### Charaktere hinzufügen

```bash
story-outline character add <novel-id> "Anna Schmidt" --role protagonist --desc "30-jährige Journalistin"
story-outline character add <novel-id> "Viktor Schwarz" --role antagonist
story-outline character list <novel-id>
```

### Handlungsstränge

```bash
story-outline plot add <novel-id> "Liebesgeschichte" --type subplot
story-outline plot add <novel-id> "Familiengeheimnis" --type background
```

### Visualisierungen

```bash
# Strukturdiagramm (Mermaid)
story-outline viz structure <novel-id>

# Handlungsstrang-Fluss
story-outline viz threads <novel-id>

# Charakter-Szenen-Matrix
story-outline viz matrix <novel-id>

# Export als Markdown oder HTML
story-outline viz export <novel-id> --format md --output ./mein-roman
story-outline viz export <novel-id> --format html --output ./mein-roman
```

### Analyse

```bash
# Charakter-Präsenz
story-outline analysis characters <novel-id>

# Pacing-Analyse
story-outline analysis pacing <novel-id>

# Fortschritt
story-outline analysis status <novel-id>
```

## Datenmodell

```
Novel
├── metadata (title, author, genre, logline, synopsis)
├── Acts[]
│   └── Chapters[]
│       └── Scenes[]
│           ├── pov_character
│           ├── characters[]
│           ├── location
│           ├── story_datetime / story_date_description
│           ├── plot_threads[]
│           ├── emotional_arc (start → end)
│           ├── conflict_level
│           ├── beats[]
│           └── goal / disaster
├── Characters[]
├── Locations[]
├── PlotThreads[]
├── SceneConnections[]
└── TimelineEvents[]
```

## Verfügbare Templates

| ID | Name | Beschreibung |
|---|---|---|
| `three-act` | Drei-Akt-Struktur | Setup, Konfrontation, Auflösung |
| `heros-journey` | Heldenreise | 12 Stationen nach Campbell/Vogler |
| `save-the-cat` | Save the Cat | 15 präzise Beats nach Blake Snyder |
| `kishotenketsu` | Kishōtenketsu | Japanische 4-Akt-Struktur ohne Konflikt |
| `seven-point` | 7-Point Structure | Hook → Resolution mit Midpoint |

## Python API Nutzung

```python
from src.services import NovelService, AnalysisService, VisualizationService
from src.models import Scene, Character, Status

# Services initialisieren
service = NovelService()
analysis = AnalysisService()
viz = VisualizationService()

# Roman erstellen
novel = service.create_novel(
    title="Der verlorene Schlüssel",
    author="Maria Beispiel",
    genre="Mystery",
    template_id="three-act",
    target_word_count=75000
)

# Charakter hinzufügen
detective = service.add_character(
    novel, 
    name="Kommissar Weber",
    role="protagonist",
    description="Erfahrener Ermittler mit Vergangenheit"
)

# Handlungsstrang
main_plot = service.add_plot_thread(
    novel,
    name="Der Mordfall",
    thread_type="main"
)

# Analyse
char_stats = analysis.analyze_character_presence(novel)
pacing = analysis.analyze_pacing(novel)

# Visualisierung
diagram = viz.generate_structure_diagram(novel)
html = viz.export_to_html(novel)
```

## Speicherort

Alle Daten werden standardmäßig in `~/.story-outline/` gespeichert:

```
~/.story-outline/
├── novels/
│   ├── <novel-id>.json
│   └── ...
└── backups/
    ├── <novel-id>_<timestamp>.json
    └── ...
```

## Roadmap

- [ ] Web-Interface (FastAPI + React)
- [ ] Obsidian-Integration
- [ ] Scrivener Import/Export
- [ ] KI-gestützte Vorschläge
- [ ] Kollaboration (Multi-User)

## Lizenz

MIT License
