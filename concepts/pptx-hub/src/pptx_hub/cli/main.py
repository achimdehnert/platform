"""
PPTX-Hub Command Line Interface.

A CLI tool for processing PowerPoint presentations.

Usage:
    pptx-hub extract presentation.pptx --output texts.json
    pptx-hub translate presentation.pptx --target de --output translated.pptx
    pptx-hub analyze presentation.pptx --format json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    raise ImportError(
        "CLI dependencies not installed. "
        "Install with: pip install pptx-hub[cli]"
    )

from pptx_hub import __version__
from pptx_hub.core.services import TextExtractor, Repackager, SlideAnalyzer

app = typer.Typer(
    name="pptx-hub",
    help="Production-ready PowerPoint processing platform.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"pptx-hub version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """PPTX-Hub: Production-ready PowerPoint processing platform."""
    pass


@app.command()
def extract(
    source: Path = typer.Argument(..., help="Path to PowerPoint file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file (default: stdout)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, text",
    ),
) -> None:
    """Extract text content from a PowerPoint presentation."""
    
    if not source.exists():
        console.print(f"[red]Error: File not found: {source}[/red]")
        raise typer.Exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Extracting text...", total=None)
        
        extractor = TextExtractor()
        result = extractor.extract(source)
    
    if not result.success:
        console.print(f"[red]Extraction failed:[/red]")
        for error in result.errors:
            console.print(f"  - {error}")
        raise typer.Exit(1)
    
    # Format output
    if format == "json":
        data = {
            "filename": result.presentation.filename,
            "slides": [
                {
                    "number": slide.number,
                    "title": slide.title,
                    "texts": [
                        {"content": t.content, "type": t.text_type.value}
                        for t in slide.texts
                    ],
                    "notes": slide.notes,
                }
                for slide in result.slides
            ],
            "statistics": {
                "total_slides": result.total_slides,
                "total_texts": result.total_texts,
                "total_characters": result.total_characters,
            },
        }
        output_text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        lines = []
        for slide in result.slides:
            lines.append(f"=== Slide {slide.number}: {slide.title or 'Untitled'} ===")
            for text in slide.texts:
                lines.append(f"  - {text.content}")
            lines.append("")
        output_text = "\n".join(lines)
    
    if output:
        output.write_text(output_text, encoding="utf-8")
        console.print(f"[green]Output written to: {output}[/green]")
    else:
        console.print(output_text)
    
    # Print summary
    console.print(f"\n[dim]Extracted {result.total_slides} slides, {result.total_texts} texts[/dim]")


@app.command()
def analyze(
    source: Path = typer.Argument(..., help="Path to PowerPoint file"),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
) -> None:
    """Analyze a PowerPoint presentation."""
    
    if not source.exists():
        console.print(f"[red]Error: File not found: {source}[/red]")
        raise typer.Exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing presentation...", total=None)
        
        analyzer = SlideAnalyzer()
        analysis = analyzer.analyze(source)
    
    if format == "json":
        data = {
            "filename": analysis.filename,
            "slide_count": analysis.slide_count,
            "total_words": analysis.total_word_count,
            "total_characters": analysis.total_character_count,
            "slides_with_images": analysis.slides_with_images,
            "slides_with_tables": analysis.slides_with_tables,
            "slides_with_charts": analysis.slides_with_charts,
            "layouts_used": analysis.layouts_used,
        }
        console.print(json.dumps(data, indent=2))
    else:
        # Summary table
        table = Table(title=f"Analysis: {analysis.filename}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Slides", str(analysis.slide_count))
        table.add_row("Total Words", str(analysis.total_word_count))
        table.add_row("Total Characters", str(analysis.total_character_count))
        table.add_row("Slides with Images", str(analysis.slides_with_images))
        table.add_row("Slides with Tables", str(analysis.slides_with_tables))
        table.add_row("Slides with Charts", str(analysis.slides_with_charts))
        table.add_row("Slides with Notes", str(analysis.slides_with_notes))
        
        console.print(table)
        
        # Layouts
        if analysis.layouts_used:
            console.print("\n[bold]Layouts Used:[/bold]")
            for layout, count in analysis.layouts_used.items():
                console.print(f"  - {layout}: {count}")


@app.command()
def repackage(
    source: Path = typer.Argument(..., help="Path to source PowerPoint file"),
    output: Path = typer.Argument(..., help="Path for output file"),
    replacements: Optional[Path] = typer.Option(
        None,
        "--replacements",
        "-r",
        help="JSON file with text replacements",
    ),
) -> None:
    """Repackage a PowerPoint with text modifications."""
    
    if not source.exists():
        console.print(f"[red]Error: File not found: {source}[/red]")
        raise typer.Exit(1)
    
    # Load replacements
    replacement_dict = {}
    if replacements:
        if not replacements.exists():
            console.print(f"[red]Error: Replacements file not found: {replacements}[/red]")
            raise typer.Exit(1)
        replacement_dict = json.loads(replacements.read_text(encoding="utf-8"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Repackaging presentation...", total=None)
        
        repackager = Repackager()
        stats = repackager.repackage(
            source=source,
            output=output,
            replacements=replacement_dict,
        )
    
    console.print(f"[green]Output written to: {output}[/green]")
    console.print(f"[dim]Processed {stats['slides_processed']} slides, {stats['texts_replaced']} replacements[/dim]")


if __name__ == "__main__":
    app()
