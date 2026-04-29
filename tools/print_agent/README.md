# print_agent — IIL PDF Generator

Konvertiert Markdown-Dateien mit Design-Switcher zu professionellen PDFs.

## Usage

```bash
python3 print_agent.py <input.md> [output_dir] [--design meiki|iil|ttz]
```

## Unterstützte Code-Fences (MD → HTML → PDF)

| Fence | Beschreibung |
|-------|-------------|
| ` ```gantt ` | Gantt-Chart (Zeitplan) |
| ` ```flow ` | Dreistufiger Workflow (entry/s1/s2/s3/target) |
| ` ```tree ` | Dateibaum (eingerückt, `--` Kommentare) |
| ` ```arch ` | Komponentenarchitektur (title/row/split/left/right) |
| ` ```layer ` | Schichtenmodell (top/bridge/left/right) |

## SSoT-Pfade

| Datei | Zweck |
|-------|-------|
| `print_agent.py` | Haupt-Logik |
| `print_designs.yaml` | Design-Profile (meiki, iil, ttz) |
| `print_templates/base.css` | CSS für alle Designs |
| `print_templates/base.html.j2` | Jinja2-Template |

## Designs

Definiert in `print_designs.yaml` — jedes Design hat eigene Farbpalette, Schriften und LLM-Kontext.

## Dependencies

```
weasyprint, markdown, jinja2, litellm, pyyaml
```
