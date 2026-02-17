"""BF Agent Platform — Deploy CLI.

Usage:
    bf deploy travel-beat          # Deploy single app
    bf deploy travel-beat bfagent  # Deploy multiple apps
    bf deploy --all                # Deploy all apps
    bf status                      # Show deploy status
    bf rollback <app> <sha-tag>    # Rollback to specific image
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click

from .config import APPS, DEBOUNCE_SECONDS, PROD_HOST, PROD_USER
from .debounce import is_debounced, mark_triggered
from .github_api import get_latest_run, trigger_workflow


def _get_token() -> str:
    """Read GitHub token from environment or ~/.bf-deploy/token."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    token_file = Path.home() / ".bf-deploy" / "token"
    if token_file.exists():
        return token_file.read_text().strip()
    click.echo(
        "Error: Set GITHUB_TOKEN or create ~/.bf-deploy/token",
        err=True,
    )
    sys.exit(1)


@click.group()
def cli() -> None:
    """BF Agent Platform — Deploy CLI."""


@cli.command()
@click.argument("apps", nargs=-1)
@click.option("--all", "deploy_all", is_flag=True, help="Deploy all apps")
@click.option("--force", is_flag=True, help="Ignore debounce window")
def deploy(
    apps: tuple[str, ...],
    deploy_all: bool,
    force: bool,
) -> None:
    """Trigger async deployment for one or more apps."""
    token = _get_token()

    targets = list(APPS.keys()) if deploy_all else list(apps)
    if not targets:
        click.echo("Usage: bf deploy <app> [<app>...] or bf deploy --all")
        sys.exit(1)

    for app in targets:
        if app not in APPS:
            click.echo(
                f"Unknown app: {app}. Available: {', '.join(APPS)}"
            )
            continue

        if not force and is_debounced(app):
            click.echo(
                f"\u23f3 {app}: debounced "
                f"(triggered <{DEBOUNCE_SECONDS}s ago, "
                f"use --force to override)"
            )
            continue

        cfg = APPS[app]
        status_code = trigger_workflow(
            cfg["repo"], token, workflow=cfg["workflow"],
        )
        if status_code == 204:
            mark_triggered(app)
            click.echo(f"\U0001f680 {app}: deploy triggered (async)")
        else:
            click.echo(
                f"\u274c {app}: trigger failed (HTTP {status_code})"
            )


@cli.command()
def status() -> None:
    """Show recent deploy status for all apps."""
    token = _get_token()
    emoji_map = {
        "success": "\u2705",
        "failure": "\u274c",
        "in_progress": "\U0001f504",
    }
    for app, cfg in APPS.items():
        run = get_latest_run(cfg["repo"], token)
        if run:
            conclusion = run.get("conclusion") or run.get("status")
            sha = run["head_sha"][:7]
            emoji = emoji_map.get(conclusion, "\u2753")
            click.echo(
                f"  {emoji} {app:15s} {conclusion:12s} ({sha})"
            )
        else:
            click.echo(f"  \u2753 {app:15s} no runs found")


@cli.command()
@click.argument("app")
@click.argument("sha_tag")
def rollback(app: str, sha_tag: str) -> None:
    """Rollback an app to a specific image tag.

    Usage: bf rollback travel-beat sha-abc1234
    """
    if app not in APPS:
        click.echo(
            f"Unknown app: {app}. Available: {', '.join(APPS)}"
        )
        sys.exit(1)

    cfg = APPS[app]
    image = f"ghcr.io/{cfg['repo']}:{sha_tag}"
    click.echo(f"Rolling back {app} to {image}...")

    # SSH to PROD: pull specific tag, retag as latest, restart
    ssh_cmd = (
        f"cd /opt/{app} && "
        f"docker pull {image} && "
        f"docker tag {image} ghcr.io/{cfg['repo']}:latest && "
        f"docker compose up -d --force-recreate"
    )
    result = subprocess.run(
        [
            "ssh", "-o", "BatchMode=yes",
            f"{PROD_USER}@{PROD_HOST}",
            ssh_cmd,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        click.echo(
            f"\u2705 Rollback {app} -> {sha_tag} complete."
        )
    else:
        click.echo(
            f"\u274c Rollback failed: {result.stderr}",
            err=True,
        )
        sys.exit(1)
