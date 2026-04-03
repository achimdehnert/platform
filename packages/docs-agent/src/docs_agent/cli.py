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


# ---------------------------------------------------------------------------
# Reference-doc generation: single repo + batch
# ---------------------------------------------------------------------------


def _generate_reference_for_repo(
    repo_path: Path,
    *,
    doc_type: str = "all",
    dry_run: bool = True,
    output_dir: str = "docs/reference",
    apps_only: bool = True,
    verbose: bool = True,
) -> dict:
    """Core logic: generate reference docs for one repo. Returns summary dict."""
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

    repo_name = repo_path.name
    out = repo_path / output_dir
    results = []
    stats = {"models": 0, "endpoints": 0, "settings": 0, "env_vars": 0}

    if doc_type in ("models", "all"):
        if verbose:
            console.print("[bold]Extracting models...[/]")
        models = extract_models_from_repo(repo_path, apps_only=apps_only)
        stats["models"] = len(models)
        if verbose:
            console.print(f"  Found {len(models)} models.")
        md = render_models_markdown(models, repo_name=repo_name)
        result = write_if_changed(out / "models.md", md, dry_run=dry_run)
        results.append(("models.md", result))

    if doc_type in ("api", "all"):
        if verbose:
            console.print("[bold]Extracting URL patterns...[/]")
        modules = extract_urls_from_repo(repo_path, apps_only=apps_only)
        total_urls = sum(len(m.patterns) for m in modules)
        stats["endpoints"] = total_urls
        if verbose:
            console.print(f"  Found {total_urls} endpoints in {len(modules)} modules.")
        md = render_urls_markdown(modules, repo_name=repo_name)
        result = write_if_changed(out / "api.md", md, dry_run=dry_run)
        results.append(("api.md", result))

    if doc_type in ("config", "all"):
        if verbose:
            console.print("[bold]Extracting configuration...[/]")
        profile = extract_config_from_repo(repo_path)
        stats["settings"] = len(profile.settings)
        stats["env_vars"] = len(profile.env_vars)
        if verbose:
            console.print(
                f"  Found {len(profile.settings)} settings, "
                f"{len(profile.env_vars)} env vars."
            )
        md = render_config_markdown(profile, repo_name=repo_name)
        result = write_if_changed(out / "config.md", md, dry_run=dry_run)
        results.append(("config.md", result))

    changed = sum(1 for _, r in results if r.changed)
    return {
        "repo": repo_name,
        "results": results,
        "changed": changed,
        "stats": stats,
    }


def _print_repo_results(
    summary: dict, *, dry_run: bool, output_dir: str, verbose: bool = True
) -> None:
    """Print results for a single repo."""
    if not verbose:
        return
    console.print(f"\n[bold]Results for {summary['repo']}:[/]")
    for name, result in summary["results"]:
        if result.changed:
            action = "would write" if dry_run else "written"
            console.print(
                f"  [green]✓[/] {name}: {action} "
                f"({len(result.diff_lines)} diff lines)"
            )
            for line in result.diff_lines[:10]:
                if line.startswith("+") and not line.startswith("+++"):
                    console.print(f"    [green]{line}[/]")
                elif line.startswith("-") and not line.startswith("---"):
                    console.print(f"    [red]{line}[/]")
            if len(result.diff_lines) > 10:
                console.print(
                    f"    ... ({len(result.diff_lines) - 10} more)"
                )
        else:
            console.print(f"  [dim]—[/] {name}: no changes")


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
    """Generate reference documentation for a SINGLE repo."""
    repo_path = repo_path.resolve()
    mode = "[yellow]DRY RUN[/]" if dry_run else "[red]COMMIT[/]"
    console.print(
        f"\n[bold blue]docs-agent reference[/] — {repo_path.name} ({mode})\n"
    )

    summary = _generate_reference_for_repo(
        repo_path,
        doc_type=doc_type,
        dry_run=dry_run,
        output_dir=output_dir,
        apps_only=apps_only,
    )
    _print_repo_results(summary, dry_run=dry_run, output_dir=output_dir)

    changed = summary["changed"]
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


@app.command("reference-all")
def reference_all(
    base_dir: Path = typer.Argument(
        ...,
        help="Parent directory containing all repos (e.g. ~/github).",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--commit",
        help="Preview changes (default) or write files.",
    ),
    output_dir: str = typer.Option(
        "docs/reference",
        "--output-dir",
        help="Output directory relative to each repo root.",
    ),
    registry: Optional[Path] = typer.Option(
        None,
        "--registry",
        help="Path to repos.yaml (auto-detected from platform/registry/).",
    ),
    skip: Optional[str] = typer.Option(
        None,
        "--skip",
        help="Comma-separated repo names to skip.",
    ),
    only_django: bool = typer.Option(
        False,
        "--only-django",
        help="Only process repos with apps/ or manage.py (Django projects).",
    ),
    output: str = typer.Option(
        "table",
        help="Output format: table or json.",
    ),
) -> None:
    """Generate reference docs for ALL repos under a base directory.

    Discovers repos via registry/repos.yaml (if found) or by scanning
    subdirectories. Skips non-Python and non-existent repos automatically.

    Examples:
        docs-agent reference-all ~/github --dry-run
        docs-agent reference-all ~/github --commit
        docs-agent reference-all ~/github --only-django --commit
        docs-agent reference-all ~/github --skip odoo-hub,testkit
    """
    base_dir = base_dir.resolve()
    mode = "[yellow]DRY RUN[/]" if dry_run else "[red]COMMIT[/]"
    console.print(
        f"\n[bold blue]docs-agent reference-all[/] — {base_dir} ({mode})\n"
    )

    skip_set = set()
    if skip:
        skip_set = {s.strip() for s in skip.split(",")}

    # --- Discover repos ---
    repo_dirs = _discover_repos(
        base_dir,
        registry=registry,
        skip=skip_set,
        only_django=only_django,
    )

    if not repo_dirs:
        console.print("[red]No repos found.[/]")
        raise typer.Exit(code=1)

    console.print(f"Found [bold]{len(repo_dirs)}[/] repos to process.\n")

    # --- Process each repo ---
    summaries = []
    for repo_path in repo_dirs:
        console.print(
            f"[bold cyan]━━━ {repo_path.name} ━━━[/]"
        )
        try:
            summary = _generate_reference_for_repo(
                repo_path,
                dry_run=dry_run,
                output_dir=output_dir,
                verbose=False,
            )
            summaries.append(summary)
            s = summary["stats"]
            tag = (
                f"[green]✓ {summary['changed']} changed[/]"
                if summary["changed"]
                else "[dim]— up to date[/]"
            )
            console.print(
                f"  {s['models']} models, {s['endpoints']} endpoints, "
                f"{s['settings']} settings, {s['env_vars']} env vars → {tag}"
            )
        except Exception as exc:
            console.print(f"  [red]ERROR: {exc}[/]")
            summaries.append(
                {"repo": repo_path.name, "changed": 0, "error": str(exc),
                 "stats": {}, "results": []}
            )

    # --- Final summary ---
    console.print("\n" + "═" * 60)
    total_repos = len(summaries)
    total_changed = sum(s["changed"] for s in summaries)
    total_errors = sum(1 for s in summaries if "error" in s)
    total_models = sum(s["stats"].get("models", 0) for s in summaries)
    total_endpoints = sum(s["stats"].get("endpoints", 0) for s in summaries)
    repos_with_changes = sum(
        1 for s in summaries if s["changed"] > 0
    )

    if output == "json":
        import json

        data = {
            "base_dir": str(base_dir),
            "dry_run": dry_run,
            "repos_scanned": total_repos,
            "repos_changed": repos_with_changes,
            "files_changed": total_changed,
            "total_models": total_models,
            "total_endpoints": total_endpoints,
            "errors": total_errors,
            "details": [
                {
                    "repo": s["repo"],
                    "changed": s["changed"],
                    "error": s.get("error"),
                    **s.get("stats", {}),
                }
                for s in summaries
            ],
        }
        console.print_json(json.dumps(data, default=str))
        return

    # Table summary
    table = Table(
        title=f"Reference Docs — {'DRY RUN' if dry_run else 'COMMITTED'}"
    )
    table.add_column("Repo", style="cyan", no_wrap=True)
    table.add_column("Models", justify="right")
    table.add_column("Endpoints", justify="right")
    table.add_column("Settings", justify="right")
    table.add_column("Files Changed", justify="right")
    table.add_column("Status")

    for s in summaries:
        if "error" in s:
            table.add_row(
                s["repo"], "—", "—", "—", "—",
                "[red]ERROR[/]"
            )
        else:
            st = s["stats"]
            status = (
                f"[green]{s['changed']} updated[/]"
                if s["changed"]
                else "[dim]up to date[/]"
            )
            table.add_row(
                s["repo"],
                str(st.get("models", 0)),
                str(st.get("endpoints", 0)),
                str(st.get("settings", 0)),
                str(s["changed"]),
                status,
            )

    console.print(table)
    console.print(
        f"\n[bold]{total_repos}[/] repos scanned, "
        f"[bold]{total_models}[/] models, "
        f"[bold]{total_endpoints}[/] endpoints"
    )
    if total_errors:
        console.print(f"[red]{total_errors} repo(s) with errors.[/]")

    if dry_run and total_changed:
        console.print(
            f"\n[yellow]{repos_with_changes} repo(s) with {total_changed} "
            f"file(s) would change. Run with --commit to write.[/]"
        )
    elif not dry_run and total_changed:
        console.print(
            f"\n[green]{total_changed} file(s) written across "
            f"{repos_with_changes} repo(s).[/]"
        )
    else:
        console.print("\n[dim]All repos up to date.[/]")


def _discover_repos(
    base_dir: Path,
    *,
    registry: Optional[Path] = None,
    skip: set[str] | None = None,
    only_django: bool = False,
) -> list[Path]:
    """Discover repos from registry/repos.yaml or filesystem scan."""
    skip = skip or set()
    repo_names: list[str] = []

    # Try repos.yaml first
    if registry and registry.exists():
        repo_names = _read_repos_yaml(registry)
    else:
        # Auto-detect: look for platform/registry/repos.yaml
        candidates = [
            base_dir / "platform" / "registry" / "repos.yaml",
            base_dir.parent / "platform" / "registry" / "repos.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                console.print(
                    f"[dim]Using registry: {candidate}[/]"
                )
                repo_names = _read_repos_yaml(candidate)
                break

    if not repo_names:
        # Fallback: scan subdirectories
        console.print(
            "[dim]No repos.yaml found — scanning directories...[/]"
        )
        repo_names = sorted(
            d.name
            for d in base_dir.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and not d.name.endswith(".code-workspace")
        )

    # Resolve to paths and filter
    result = []
    for name in repo_names:
        if name in skip:
            console.print(f"  [dim]Skip: {name}[/]")
            continue
        repo_path = base_dir / name
        if not repo_path.is_dir():
            console.print(f"  [dim]Not found: {name}[/]")
            continue
        # Check for Python content
        has_python = (
            list(repo_path.glob("*.py"))
            or (repo_path / "apps").is_dir()
            or (repo_path / "src").is_dir()
            or (repo_path / "setup.py").exists()
            or (repo_path / "pyproject.toml").exists()
        )
        if not has_python:
            console.print(f"  [dim]No Python: {name}[/]")
            continue
        if only_django:
            is_django = (
                (repo_path / "apps").is_dir()
                or (repo_path / "manage.py").exists()
            )
            if not is_django:
                console.print(f"  [dim]Not Django: {name}[/]")
                continue
        result.append(repo_path)

    return sorted(result, key=lambda p: p.name)


def _read_repos_yaml(path: Path) -> list[str]:
    """Extract repo names from registry/repos.yaml."""
    try:
        import yaml
    except ImportError:
        console.print(
            "[yellow]PyYAML not installed — "
            "falling back to directory scan.[/]"
        )
        return []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        console.print(f"[yellow]Cannot read {path}: {exc}[/]")
        return []

    names = []
    for domain in data.get("domains", []):
        for system in domain.get("systems", []):
            repo = system.get("repo")
            if repo:
                names.append(repo)
    return names


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
