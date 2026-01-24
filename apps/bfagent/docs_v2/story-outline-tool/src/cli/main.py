"""
CLI interface for Story Outline Tool.
Uses Typer for a modern, intuitive command-line experience.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models import ConflictLevel, EmotionalTone, Status, get_template, list_templates
from src.services import AnalysisService, NovelService, VisualizationService

# Initialize
app = typer.Typer(
    name="story-outline",
    help="📚 Story Outline Tool - Strukturiere deine Geschichten professionell",
    add_completion=False,
)
console = Console()

# Sub-apps
novel_app = typer.Typer(help="Roman-Verwaltung")
scene_app = typer.Typer(help="Szenen-Verwaltung")
character_app = typer.Typer(help="Charakter-Verwaltung")
plot_app = typer.Typer(help="Handlungsstrang-Verwaltung")
viz_app = typer.Typer(help="Visualisierungen")
template_app = typer.Typer(help="Template-Verwaltung")
analysis_app = typer.Typer(help="Analyse-Tools")

app.add_typer(novel_app, name="novel")
app.add_typer(scene_app, name="scene")
app.add_typer(character_app, name="character")
app.add_typer(plot_app, name="plot")
app.add_typer(viz_app, name="viz")
app.add_typer(template_app, name="template")
app.add_typer(analysis_app, name="analysis")

# Services
service = NovelService()
analysis = AnalysisService()
viz = VisualizationService()


# =============================================================================
# Novel Commands
# =============================================================================


@novel_app.command("create")
def create_novel(
    title: str = typer.Argument(..., help="Titel des Romans"),
    author: str = typer.Option("", "--author", "-a", help="Autor"),
    genre: str = typer.Option("", "--genre", "-g", help="Genre"),
    template: str = typer.Option(
        "", "--template", "-t", help="Template-ID (three-act, heros-journey, etc.)"
    ),
    words: int = typer.Option(80000, "--words", "-w", help="Ziel-Wortanzahl"),
):
    """Erstelle einen neuen Roman."""
    novel = service.create_novel(
        title=title,
        author=author,
        genre=genre,
        template_id=template if template else None,
        target_word_count=words,
    )

    console.print(
        Panel(
            f"[bold green]✓ Roman erstellt![/bold green]\n\n"
            f"[bold]ID:[/bold] {novel.id}\n"
            f"[bold]Titel:[/bold] {novel.title}\n"
            f"[bold]Template:[/bold] {template or 'keins'}\n"
            f"[bold]Akte:[/bold] {len(novel.acts)}",
            title="Neuer Roman",
        )
    )


@novel_app.command("list")
def list_novels():
    """Liste alle Romane auf."""
    novels = service.list_novels()

    if not novels:
        console.print("[yellow]Keine Romane gefunden.[/yellow]")
        return

    table = Table(title="📚 Deine Romane")
    table.add_column("ID", style="cyan")
    table.add_column("Titel", style="bold")
    table.add_column("Autor")
    table.add_column("Genre")
    table.add_column("Wörter")
    table.add_column("Aktualisiert")

    for n in novels:
        table.add_row(
            n["id"][:8],
            n["title"],
            n.get("author", ""),
            n.get("genre", ""),
            f"{n.get('word_count_target', 0):,}",
            n.get("updated_at", "")[:10] if n.get("updated_at") else "",
        )

    console.print(table)


@novel_app.command("show")
def show_novel(
    novel_id: str = typer.Argument(..., help="Roman-ID (oder Anfang davon)"),
    full: bool = typer.Option(False, "--full", "-f", help="Zeige alle Details"),
):
    """Zeige Roman-Details und Struktur."""
    # Find novel (partial ID match)
    novels = service.list_novels()
    matches = [n for n in novels if n["id"].startswith(novel_id)]

    if not matches:
        console.print(f"[red]Roman nicht gefunden: {novel_id}[/red]")
        raise typer.Exit(1)

    novel = service.get_novel(matches[0]["id"])
    if not novel:
        console.print(f"[red]Fehler beim Laden des Romans[/red]")
        raise typer.Exit(1)

    # Build tree view
    tree = Tree(f"📖 [bold]{novel.title}[/bold]")
    tree.add(f"[dim]ID: {novel.id}[/dim]")
    tree.add(f"Autor: {novel.author or 'nicht angegeben'}")
    tree.add(f"Genre: {novel.genre or 'nicht angegeben'}")
    tree.add(f"Ziel: {novel.target_word_count:,} Wörter")

    if novel.logline:
        tree.add(f"[italic]{novel.logline}[/italic]")

    # Structure
    structure = tree.add("📑 Struktur")
    for act in novel.acts:
        act_branch = structure.add(f"[bold]{act.title}[/bold]")
        for chapter in act.chapters:
            chap_branch = act_branch.add(f"📄 {chapter.title}")
            if full:
                for scene in chapter.scenes:
                    status_icons = {
                        "idea": "💡",
                        "outlined": "📝",
                        "drafted": "✍️",
                        "revised": "🔄",
                        "final": "✅",
                    }
                    icon = status_icons.get(scene.status.value, "")
                    chap_branch.add(f"{icon} {scene.title}")

    # Characters
    if novel.characters:
        chars = tree.add("👥 Charaktere")
        for char in novel.characters:
            chars.add(f"{char.name} ({char.role})")

    # Plot threads
    if novel.plot_threads:
        plots = tree.add("🧵 Handlungsstränge")
        for thread in novel.plot_threads:
            plots.add(f"{thread.name} ({thread.thread_type})")

    console.print(tree)


@novel_app.command("delete")
def delete_novel(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Keine Bestätigung"),
):
    """Lösche einen Roman."""
    if not force:
        confirm = typer.confirm(f"Roman {novel_id} wirklich löschen?")
        if not confirm:
            raise typer.Abort()

    if service.delete_novel(novel_id):
        console.print(f"[green]✓ Roman gelöscht[/green]")
    else:
        console.print(f"[red]Roman nicht gefunden[/red]")


# =============================================================================
# Template Commands
# =============================================================================


@template_app.command("list")
def list_all_templates():
    """Liste alle verfügbaren Templates."""
    templates = service.get_available_templates()

    table = Table(title="📋 Verfügbare Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Beschreibung")
    table.add_column("Genres")
    table.add_column("Akte")

    for t in templates:
        table.add_row(
            t["id"],
            t["name"],
            t["description"][:50] + "...",
            ", ".join(t["genres"][:3]),
            str(t["acts_count"]),
        )

    console.print(table)


@template_app.command("show")
def show_template(
    template_id: str = typer.Argument(..., help="Template-ID"),
):
    """Zeige Template-Details mit allen Beats."""
    template = get_template(template_id)

    if not template:
        console.print(f"[red]Template nicht gefunden: {template_id}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{template.name}[/bold]\n\n{template.description}",
            title=f"📋 Template: {template_id}",
        )
    )

    for act in template.acts:
        console.print(f"\n[bold cyan]## {act.name}[/bold cyan]")
        console.print(f"[dim]{act.description}[/dim]")
        console.print(f"Ziel: {act.target_percent}% der Wortanzahl\n")

        for beat in act.beats:
            console.print(
                f"  [yellow]●[/yellow] [bold]{beat.name}[/bold] ({beat.typical_position_percent}%)"
            )
            console.print(f"    {beat.description}")
            if beat.questions:
                for q in beat.questions:
                    console.print(f"    [dim]→ {q}[/dim]")


# =============================================================================
# Character Commands
# =============================================================================


@character_app.command("add")
def add_character(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
    name: str = typer.Argument(..., help="Charaktername"),
    role: str = typer.Option(
        "supporting", "--role", "-r", help="Rolle: protagonist, antagonist, supporting, minor"
    ),
    description: str = typer.Option("", "--desc", "-d", help="Beschreibung"),
):
    """Füge einen Charakter hinzu."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    char = service.add_character(novel, name, role, description)
    console.print(f"[green]✓ Charakter '{char.name}' hinzugefügt (ID: {char.id})[/green]")


@character_app.command("list")
def list_characters(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
):
    """Liste alle Charaktere eines Romans."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    if not novel.characters:
        console.print("[yellow]Keine Charaktere vorhanden[/yellow]")
        return

    table = Table(title=f"👥 Charaktere in '{novel.title}'")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Rolle")
    table.add_column("Szenen")
    table.add_column("Beschreibung")

    for char in novel.characters:
        scene_count = len(novel.get_scenes_by_character(char.id))
        table.add_row(
            char.id[:8],
            char.name,
            char.role,
            str(scene_count),
            char.description[:40] + "..." if len(char.description) > 40 else char.description,
        )

    console.print(table)


# =============================================================================
# Plot Thread Commands
# =============================================================================


@plot_app.command("add")
def add_plot_thread(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
    name: str = typer.Argument(..., help="Name des Handlungsstrangs"),
    thread_type: str = typer.Option(
        "subplot", "--type", "-t", help="Typ: main, subplot, background"
    ),
    description: str = typer.Option("", "--desc", "-d", help="Beschreibung"),
):
    """Füge einen Handlungsstrang hinzu."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    thread = service.add_plot_thread(novel, name, description, thread_type)
    console.print(f"[green]✓ Handlungsstrang '{thread.name}' hinzugefügt[/green]")


# =============================================================================
# Visualization Commands
# =============================================================================


@viz_app.command("structure")
def viz_structure(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ausgabedatei"),
):
    """Generiere Strukturdiagramm (Mermaid)."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    diagram = viz.generate_structure_diagram(novel)

    if output:
        output.write_text(diagram)
        console.print(f"[green]✓ Diagramm gespeichert: {output}[/green]")
    else:
        console.print(Markdown(diagram))


@viz_app.command("threads")
def viz_threads(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
):
    """Generiere Handlungsstrang-Diagramm."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    diagram = viz.generate_plot_threads_diagram(novel)
    console.print(Markdown(diagram))


@viz_app.command("matrix")
def viz_matrix(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
):
    """Generiere Charakter-Szenen-Matrix."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    matrix = viz.generate_character_scene_matrix(novel)
    console.print(Markdown(matrix))


@viz_app.command("export")
def export_novel(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
    format: str = typer.Option("md", "--format", "-f", help="Format: md, html"),
    output: Path = typer.Option(Path("./export"), "--output", "-o", help="Ausgabepfad"),
):
    """Exportiere Roman als Markdown oder HTML."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)

    if format == "md":
        content = viz.export_to_markdown(novel)
        filepath = output.with_suffix(".md")
    elif format == "html":
        content = viz.export_to_html(novel)
        filepath = output.with_suffix(".html")
    else:
        console.print(f"[red]Unbekanntes Format: {format}[/red]")
        raise typer.Exit(1)

    filepath.write_text(content, encoding="utf-8")
    console.print(f"[green]✓ Exportiert: {filepath}[/green]")


# =============================================================================
# Analysis Commands
# =============================================================================


@analysis_app.command("characters")
def analyze_characters(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
):
    """Analysiere Charakter-Präsenz."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    stats = analysis.analyze_character_presence(novel)

    table = Table(title="👥 Charakter-Analyse")
    table.add_column("Name", style="bold")
    table.add_column("Rolle")
    table.add_column("Szenen")
    table.add_column("POV-Szenen")
    table.add_column("Präsenz %")

    for char_id, data in stats.items():
        table.add_row(
            data["name"],
            data["role"],
            str(data["total_scenes"]),
            str(data["pov_scenes"]),
            f"{data['percentage']:.1f}%",
        )

    console.print(table)


@analysis_app.command("pacing")
def analyze_pacing(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
):
    """Analysiere Pacing und Konflikte."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    stats = analysis.analyze_pacing(novel)

    console.print(Panel("[bold]Pacing-Analyse[/bold]", title="📊"))

    table = Table(title="Konflikt-Verteilung")
    table.add_column("Level")
    table.add_column("Anzahl")
    table.add_column("Visualisierung")

    total = stats["total_scenes"]
    for level, count in stats["conflict_distribution"].items():
        bar = "█" * int((count / total * 30)) if total > 0 else ""
        table.add_row(level, str(count), bar)

    console.print(table)

    if stats["pacing_issues"]:
        console.print("\n[yellow]⚠️ Mögliche Probleme:[/yellow]")
        for issue in stats["pacing_issues"]:
            console.print(f"  • {issue}")
    else:
        console.print("\n[green]✓ Keine Pacing-Probleme erkannt[/green]")


@analysis_app.command("status")
def analyze_status(
    novel_id: str = typer.Argument(..., help="Roman-ID"),
):
    """Zeige Fortschritt nach Status."""
    novel = service.get_novel(novel_id)
    if not novel:
        console.print(f"[red]Roman nicht gefunden[/red]")
        raise typer.Exit(1)

    stats = analysis.get_status_summary(novel)

    console.print(
        Panel(f"[bold]Fortschritt: {stats['completion_percentage']:.1f}%[/bold]", title="📈 Status")
    )

    table = Table()
    table.add_column("Status")
    table.add_column("Anzahl")
    table.add_column("Fortschritt")

    status_colors = {
        "idea": "dim",
        "outlined": "yellow",
        "drafted": "blue",
        "revised": "cyan",
        "final": "green",
    }

    for status, count in stats["status_counts"].items():
        color = status_colors.get(status, "white")
        bar = "█" * count
        table.add_row(f"[{color}]{status}[/{color}]", str(count), bar)

    console.print(table)


# =============================================================================
# Main Entry Point
# =============================================================================


@app.callback()
def main():
    """📚 Story Outline Tool - Strukturiere deine Geschichten professionell."""
    pass


if __name__ == "__main__":
    app()
