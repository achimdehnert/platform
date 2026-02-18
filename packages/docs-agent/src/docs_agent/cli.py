"""Docs Agent CLI — audit and report on documentation quality."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from docs_agent.analyzer.ast_scanner import scan_repo
from docs_agent.analyzer.diataxis_classifier import classify_repo
from docs_agent.models import DiaxisQuadrant

app = typer.Typer(
    name="docs-agent",
    help="AI-assisted documentation quality agent.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def audit(
    repo_path: Path = typer.Argument(
        ...,
        help="Path to the repository root.",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    scope: str = typer.Option(
        "all",
        help="Audit scope: docstrings, diataxis, or all.",
    ),
    apps_only: bool = typer.Option(
        False,
        "--apps-only",
        help="Only scan apps/ directory for docstrings.",
    ),
    min_coverage: Optional[float] = typer.Option(
        None,
        "--min-coverage",
        help="Fail if docstring coverage is below this %.",
    ),
    output: str = typer.Option(
        "table",
        help="Output format: table or json.",
    ),
) -> None:
    """Audit a repository for documentation quality."""
    repo_path = repo_path.resolve()
    console.print(
        f"\n[bold blue]docs-agent audit[/] \u2014 {repo_path.name}\n"
    )

    exit_code = 0

    if scope in ("docstrings", "all"):
        exit_code |= _audit_docstrings(
            repo_path, apps_only=apps_only, output=output
        )

    if scope in ("diataxis", "all"):
        _audit_diataxis(repo_path, output=output)

    if min_coverage is not None and scope in ("docstrings", "all"):
        coverage = scan_repo(repo_path, apps_only=apps_only)
        if coverage.coverage_pct < min_coverage:
            console.print(
                f"\n[red bold]FAIL:[/] Coverage {coverage.coverage_pct:.1f}%"
                f" < minimum {min_coverage:.1f}%"
            )
            raise typer.Exit(code=1)

    if exit_code:
        raise typer.Exit(code=exit_code)


def _audit_docstrings(
    repo_path: Path,
    *,
    apps_only: bool = False,
    output: str = "table",
) -> int:
    """Run docstring coverage audit."""
    console.print("[bold]Docstring Coverage[/]\n")
    coverage = scan_repo(repo_path, apps_only=apps_only)

    if not coverage.modules:
        console.print("[yellow]No Python modules found.[/]")
        return 0

    if output == "json":
        import json

        data = {
            "repo": str(coverage.repo_path),
            "total_items": coverage.total_items,
            "documented": coverage.documented_items,
            "coverage_pct": round(coverage.coverage_pct, 1),
            "modules": [
                {
                    "file": str(m.file_path.relative_to(repo_path)),
                    "total": m.total_items,
                    "documented": m.documented_items,
                    "coverage_pct": round(m.coverage_pct, 1),
                }
                for m in coverage.modules
            ],
        }
        console.print_json(json.dumps(data))
        return 0

    # Table output
    table = Table(title="Module Coverage")
    table.add_column("Module", style="cyan", no_wrap=True)
    table.add_column("Items", justify="right")
    table.add_column("Documented", justify="right")
    table.add_column("Coverage", justify="right")

    for module in sorted(coverage.modules, key=lambda m: m.coverage_pct):
        rel_path = str(module.file_path.relative_to(repo_path))
        pct = module.coverage_pct
        style = (
            "green" if pct >= 80
            else "yellow" if pct >= 50
            else "red"
        )
        table.add_row(
            rel_path,
            str(module.total_items),
            str(module.documented_items),
            f"[{style}]{pct:.0f}%[/{style}]",
        )

    console.print(table)

    # Summary
    console.print(
        f"\n[bold]Total:[/] {coverage.documented_items}"
        f"/{coverage.total_items} items documented"
        f" ([bold]{coverage.coverage_pct:.1f}%[/])"
    )

    # Top undocumented items
    undoc = []
    for m in coverage.modules:
        for item in m.undocumented:
            undoc.append(item)

    if undoc:
        console.print(
            f"\n[bold yellow]Top undocumented items"
            f" ({len(undoc)} total):[/]\n"
        )
        for item in undoc[:15]:
            rel = str(item.file_path.relative_to(repo_path))
            console.print(
                f"  {item.kind.value:8s} "
                f"[cyan]{rel}[/]:{item.line} "
                f"[bold]{item.name}[/]"
            )
        if len(undoc) > 15:
            console.print(f"  ... and {len(undoc) - 15} more")

    return 0


def _audit_diataxis(
    repo_path: Path,
    *,
    output: str = "table",
) -> None:
    """Run DIATAXIS classification audit."""
    console.print("\n[bold]DIATAXIS Classification[/]\n")
    results = classify_repo(repo_path)

    if not results:
        console.print("[yellow]No documentation files found.[/]")
        return

    if output == "json":
        import json

        data = [
            {
                "file": str(r.file_path.relative_to(repo_path)),
                "quadrant": r.quadrant.value,
                "confidence": r.confidence,
            }
            for r in results
        ]
        console.print_json(json.dumps(data))
        return

    # Table output
    table = Table(title="DIATAXIS Classification")
    table.add_column("Document", style="cyan")
    table.add_column("Quadrant", justify="center")
    table.add_column("Confidence", justify="right")

    quadrant_colors = {
        DiaxisQuadrant.TUTORIAL: "blue",
        DiaxisQuadrant.GUIDE: "green",
        DiaxisQuadrant.REFERENCE: "magenta",
        DiaxisQuadrant.EXPLANATION: "yellow",
        DiaxisQuadrant.UNKNOWN: "red",
    }

    for result in results:
        rel = str(result.file_path.relative_to(repo_path))
        color = quadrant_colors.get(result.quadrant, "white")
        conf_style = (
            "green" if result.confidence >= 0.7
            else "yellow" if result.confidence >= 0.4
            else "red"
        )
        table.add_row(
            rel,
            f"[{color}]{result.quadrant.value}[/{color}]",
            f"[{conf_style}]{result.confidence:.0%}[/{conf_style}]",
        )

    console.print(table)

    # Summary by quadrant
    counts: dict[DiaxisQuadrant, int] = {}
    for r in results:
        counts[r.quadrant] = counts.get(r.quadrant, 0) + 1

    low_confidence = sum(1 for r in results if r.confidence < 0.7)

    console.print("\n[bold]Distribution:[/]")
    for q, count in sorted(counts.items(), key=lambda x: -x[1]):
        color = quadrant_colors.get(q, "white")
        console.print(f"  [{color}]{q.value:12s}[/{color}] {count}")

    if low_confidence:
        console.print(
            f"\n[yellow]{low_confidence} files with"
            f" confidence < 70%"
            f" (candidates for LLM reclassification)[/]"
        )
