"""Docs Agent CLI — audit and report on documentation quality."""

from __future__ import annotations

import asyncio
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
    refine: bool = typer.Option(
        False,
        "--refine",
        help="Use LLM to refine low-confidence DIATAXIS classifications.",
    ),
    llm_url: str = typer.Option(
        "http://localhost:8100", # noqa: hardcode
        "--llm-url",
        help="URL of the llm_mcp HTTP gateway (for --refine).",
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
        _audit_diataxis(
            repo_path, output=output,
            refine=refine, llm_url=llm_url,
        )

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

    for module in sorted(
        coverage.modules, key=lambda m: m.coverage_pct
    ):
        rel_path = str(
            module.file_path.relative_to(repo_path)
        )
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
            rel = str(
                item.file_path.relative_to(repo_path)
            )
            console.print(
                f"  {item.kind.value:8s} "
                f"[cyan]{rel}[/]:{item.line} "
                f"[bold]{item.name}[/]"
            )
        if len(undoc) > 15:
            console.print(
                f"  ... and {len(undoc) - 15} more"
            )

    return 0


def _audit_diataxis(
    repo_path: Path,
    *,
    output: str = "table",
    refine: bool = False,
    llm_url: str = "http://localhost:8100", # noqa: hardcode
) -> None:
    """Run DIATAXIS classification audit."""
    console.print("\n[bold]DIATAXIS Classification[/]\n")
    results = classify_repo(repo_path)

    if refine and results:
        from docs_agent.analyzer.llm_classifier import (
            reclassify_low_confidence,
        )
        from docs_agent.llm_client import LLMConfig

        low = sum(1 for r in results if r.confidence < 0.7)
        if low:
            console.print(
                f"[yellow]Refining {low} low-confidence"
                f" classifications via LLM...[/]\n"
            )
            config = LLMConfig(gateway_url=llm_url)
            results = asyncio.run(
                reclassify_low_confidence(
                    results, config=config
                )
            )

    if not results:
        console.print("[yellow]No documentation files found.[/]")
        return

    if output == "json":
        import json

        data = [
            {
                "file": str(
                    r.file_path.relative_to(repo_path)
                ),
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
        color = quadrant_colors.get(
            result.quadrant, "white"
        )
        conf_style = (
            "green" if result.confidence >= 0.7
            else "yellow" if result.confidence >= 0.4
            else "red"
        )
        table.add_row(
            rel,
            f"[{color}]{result.quadrant.value}[/{color}]",
            f"[{conf_style}]{result.confidence:.0%}"
            f"[/{conf_style}]",
        )

    console.print(table)

    # Summary by quadrant
    counts: dict[DiaxisQuadrant, int] = {}
    for r in results:
        counts[r.quadrant] = counts.get(r.quadrant, 0) + 1

    low_confidence = sum(
        1 for r in results if r.confidence < 0.7
    )

    console.print("\n[bold]Distribution:[/]")
    for q, count in sorted(
        counts.items(), key=lambda x: -x[1]
    ):
        color = quadrant_colors.get(q, "white")
        console.print(
            f"  [{color}]{q.value:12s}[/{color}] {count}"
        )

    if low_confidence:
        console.print(
            f"\n[yellow]{low_confidence} files with"
            f" confidence < 70%"
            f" (candidates for LLM reclassification)[/]"
        )


@app.command()
def generate(
    repo_path: Path = typer.Argument(
        ...,
        help="Path to the repository root.",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    apps_only: bool = typer.Option(
        False,
        "--apps-only",
        help="Only scan apps/ directory.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Preview changes (default) or apply them.",
    ),
    max_items: int = typer.Option(
        20,
        "--max-items",
        help="Maximum items to generate docstrings for.",
    ),
    gateway_url: str = typer.Option(
        "http://localhost:8100", # noqa: hardcode
        "--llm-url",
        help="URL of the llm_mcp HTTP gateway.",
    ),
    model: str = typer.Option(
        "gpt-4o-mini",
        "--model",
        help="LLM model name.",
    ),
) -> None:
    """Generate docstrings for undocumented code items via LLM."""
    from docs_agent.generator.code_inserter import insert_docstrings
    from docs_agent.generator.docstring_gen import generate_docstrings
    from docs_agent.llm_client import LLMConfig

    repo_path = repo_path.resolve()
    mode = "[yellow]DRY RUN[/]" if dry_run else "[red]APPLY[/]"
    console.print(
        f"\n[bold blue]docs-agent generate[/] \u2014 {repo_path.name}"
        f" ({mode})\n"
    )

    # 1. Scan for undocumented items
    coverage = scan_repo(repo_path, apps_only=apps_only)
    undoc = []
    for m in coverage.modules:
        undoc.extend(m.undocumented)

    if not undoc:
        console.print("[green]All items are documented![/]")
        return

    console.print(
        f"Found [bold]{len(undoc)}[/] undocumented items."
    )
    items = undoc[:max_items]
    console.print(
        f"Generating docstrings for [bold]{len(items)}[/] items...\n"
    )

    # 2. Generate via LLM
    config = LLMConfig(
        gateway_url=gateway_url,
        model=model,
    )

    results = asyncio.run(
        generate_docstrings(items, config=config)
    )

    if not results:
        console.print(
            "[red]No docstrings generated."
            " Check LLM connection.[/]"
        )
        raise typer.Exit(code=1)

    console.print(
        f"Generated [bold green]{len(results)}[/] docstrings.\n"
    )

    # 3. Show / apply via libcst
    by_file: dict[Path, dict[str, str]] = {}
    for gen in results:
        by_file.setdefault(gen.item.file_path, {})[
            gen.item.name
        ] = gen.docstring

    total_inserted = 0
    for file_path, docstrings_map in by_file.items():
        rel = str(file_path.relative_to(repo_path))
        result = insert_docstrings(
            file_path, docstrings_map, dry_run=dry_run
        )
        total_inserted += result.items_inserted

        if result.changed:
            action = "would insert" if dry_run else "inserted"
            console.print(
                f"  [cyan]{rel}[/]: {action}"
                f" {result.items_inserted} docstrings"
            )

            if dry_run:
                _show_diff_preview(
                    result.original_source,
                    result.modified_source,
                    rel,
                )

    console.print(
        f"\n[bold]Total:[/] {total_inserted} docstrings"
        f" {'would be ' if dry_run else ''}inserted."
    )
    if dry_run:
        console.print(
            "\n[yellow]Run with --apply to write changes.[/]"
        )


@app.command()
def reference(
    repo_path: Path = typer.Argument(
        ...,
        help="Path to the repository root.",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    doc_type: str = typer.Option(
        "all",
        "--type",
        help="Which reference doc: models, api, config, or all.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--commit",
        help="Preview changes (default) or write files.",
    ),
    output_dir: str = typer.Option(
        "docs/reference",
        "--output-dir",
        help="Output directory relative to repo root.",
    ),
    apps_only: bool = typer.Option(
        True,
        "--apps-only/--all-dirs",
        help="Only scan apps/ directory (default).",
    ),
) -> None:
    """Generate reference documentation (models, API, config) from code introspection."""
    from docs_agent.extractors.models_extractor import (
        extract_models_from_repo,
        render_models_markdown,
    )
    from docs_agent.extractors.settings_extractor import (
        extract_config_from_repo,
        render_config_markdown,
    )
    from docs_agent.extractors.urls_extractor import (
        extract_urls_from_repo,
        render_urls_markdown,
    )
    from docs_agent.git_utils import write_if_changed

    repo_path = repo_path.resolve()
    repo_name = repo_path.name
    out = repo_path / output_dir
    mode = "[yellow]DRY RUN[/]" if dry_run else "[red]COMMIT[/]"
    console.print(
        f"\n[bold blue]docs-agent reference[/] — {repo_name} ({mode})\n"
    )

    results = []

    if doc_type in ("models", "all"):
        console.print("[bold]Extracting models...[/]")
        models = extract_models_from_repo(repo_path, apps_only=apps_only)
        console.print(f"  Found {len(models)} models.")
        md = render_models_markdown(models, repo_name=repo_name)
        result = write_if_changed(out / "models.md", md, dry_run=dry_run)
        results.append(("models.md", result))

    if doc_type in ("api", "all"):
        console.print("[bold]Extracting URL patterns...[/]")
        modules = extract_urls_from_repo(repo_path, apps_only=apps_only)
        total_urls = sum(len(m.patterns) for m in modules)
        console.print(f"  Found {total_urls} endpoints in {len(modules)} modules.")
        md = render_urls_markdown(modules, repo_name=repo_name)
        result = write_if_changed(out / "api.md", md, dry_run=dry_run)
        results.append(("api.md", result))

    if doc_type in ("config", "all"):
        console.print("[bold]Extracting configuration...[/]")
        profile = extract_config_from_repo(repo_path)
        console.print(
            f"  Found {len(profile.settings)} settings, "
            f"{len(profile.env_vars)} env vars."
        )
        md = render_config_markdown(profile, repo_name=repo_name)
        result = write_if_changed(out / "config.md", md, dry_run=dry_run)
        results.append(("config.md", result))

    # Summary
    console.print("\n[bold]Results:[/]")
    changed = 0
    for name, result in results:
        if result.changed:
            changed += 1
            action = "would write" if dry_run else "written"
            console.print(f"  [green]✓[/] {name}: {action} ({len(result.diff_lines)} diff lines)")
            # Show first few diff lines
            for line in result.diff_lines[:10]:
                if line.startswith("+") and not line.startswith("+++"):
                    console.print(f"    [green]{line}[/]")
                elif line.startswith("-") and not line.startswith("---"):
                    console.print(f"    [red]{line}[/]")
            if len(result.diff_lines) > 10:
                console.print(f"    ... ({len(result.diff_lines) - 10} more)")
        else:
            console.print(f"  [dim]—[/] {name}: no changes")

    if dry_run and changed:
        console.print(
            f"\n[yellow]{changed} file(s) would change. "
            f"Run with --commit to write.[/]"
        )
    elif not dry_run and changed:
        console.print(
            f"\n[green]{changed} file(s) written to {output_dir}/[/]"
        )
    else:
        console.print("\n[dim]Everything up to date.[/]")


def _show_diff_preview(
    original: str,
    modified: str,
    filename: str,
) -> None:
    """Show a unified diff preview."""
    import difflib

    diff = difflib.unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    diff_lines = list(diff)
    if diff_lines:
        for line in diff_lines[:30]:
            if line.startswith("+") and not line.startswith("+++"):
                console.print(f"  [green]{line}[/]")
            elif line.startswith("-") and not line.startswith("---"):
                console.print(f"  [red]{line}[/]")
            else:
                console.print(f"  {line}")
        if len(diff_lines) > 30:
            console.print(
                f"  ... ({len(diff_lines) - 30} more lines)"
            )
