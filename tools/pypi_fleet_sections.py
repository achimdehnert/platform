#!/usr/bin/env python3
"""Sektionierte Updates fuer DAS EINE PyPI-Fleet-Tracking-Issue (KONZ-052 V5).

Vorher pflegten drei Workflows drei eigene Rolling-Issues mit 0 Kommentaren
(#968 pypi-fleet-health, #373 adr-226-adoption, #752 publish-gate-backlog,
Befund F9/KONZ-platform-052). KONZ-018 §5.4 verbietet einen weiteren Meter/
ein weiteres Rolling-Issue — die erlaubte Richtung ist Konsolidierung.

Diese Datei ist die EINE Update-Funktion, die alle drei Melder importieren
(pypi-fleet-health.yml per CLI, pypi-ci-adoption-gate.yml +
tools/publish_gate_meter.py per Import): jeder Melder schreibt nur seinen
eigenen `<!-- section:NAME -->`-Block in #968, andere Sektionen bleiben
unberuehrt. Idempotent — PATCH nur bei tatsaechlicher Aenderung (kein
taegliches No-Op-Rauschen).

CLI (fuer Bash-Workflow-Schritte ohne eigenen Python-Kontext):
    GH_TOKEN=... python3 tools/pypi_fleet_sections.py \\
        --owner achimdehnert --repo platform --section health \\
        --heading "Fleet-Health (ADR-266 K1-K7)" --body-file report.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ISSUE_LABEL = "pypi-fleet-health"
ISSUE_TITLE = "PyPI-Fleet-Health: offene Findings (ADR-266 K1–K7)"

_SECTION_START = "<!-- section:{name} -->"
_SECTION_END = "<!-- /section:{name} -->"


# --------------------------------------------------------------------------
# Pure functions (getestet in tools/tests/test_pypi_fleet_sections.py)
# --------------------------------------------------------------------------


def render_section(name: str, heading: str, body: str) -> str:
    """Ein einzelner markierter Abschnitt — der idempotente Baustein."""
    return (
        f"{_SECTION_START.format(name=name)}\n"
        f"## {heading}\n\n"
        f"{body.rstrip()}\n"
        f"{_SECTION_END.format(name=name)}"
    )


def merge_section(existing_body: str, name: str, rendered: str) -> str:
    """Ersetzt NUR den Abschnitt `name` in `existing_body`; haengt ihn an,
    falls er noch nicht existiert. Andere Sektionen bleiben unveraendert."""
    existing_body = existing_body or ""
    start = _SECTION_START.format(name=name)
    end = _SECTION_END.format(name=name)
    if start in existing_body and end in existing_body:
        pre, rest = existing_body.split(start, 1)
        _, post = rest.split(end, 1)
        return f"{pre}{rendered}{post}"
    sep = "\n\n" if existing_body.strip() else ""
    return f"{existing_body.rstrip()}{sep}{rendered}\n"


def issue_needs_update(existing: dict, title: str, body: str) -> bool:
    """True, wenn Titel/Body abweichen — sonst kein PATCH (kein Rauschen)."""
    return existing.get("title") != title or (existing.get("body") or "") != body


# --------------------------------------------------------------------------
# gh-API-Schreibpfad (REST direkt, kein `gh`-Binary-Requirement)
# --------------------------------------------------------------------------


def _api(path: str, token: str, raw: bool = False, method: str = "GET", data=None):
    req = urllib.request.Request(f"https://api.github.com{path}", method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header(
        "Accept", "application/vnd.github.raw" if raw else "application/vnd.github+json"
    )
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        body = r.read().decode()
    return body if raw else json.loads(body)


def fetch_issue(owner: str, repo: str, token: str, label: str = ISSUE_LABEL) -> dict | None:
    issues = _api(f"/repos/{owner}/{repo}/issues?state=open&labels={label}", token)
    return issues[0] if issues else None


def upsert_section(
    owner: str,
    repo: str,
    token: str,
    section_name: str,
    heading: str,
    body: str,
    *,
    label: str = ISSUE_LABEL,
    title: str = ISSUE_TITLE,
    dry_run: bool = False,
) -> str:
    """Aktualisiert NUR den eigenen Abschnitt im EINEN Flotten-Issue.

    Legt das Issue an, falls es noch nicht existiert (erster Aufrufer
    gewinnt); danach PATCHt jeder Aufrufer nur seine eigene Sektion.

    `dry_run` liest bestmoeglich mit (fuer eine realistische Vorschau,
    z.B. "Issue #968 aktualisiert" statt nur "wuerde anlegen"), scheitert
    aber NIE an einem fehlenden/rate-gelimiteten Token — reine Lesefehler
    fallen im Dry-Run auf die generische Vorschau zurueck.
    """
    rendered = render_section(section_name, heading, body)
    if dry_run:
        try:
            existing = fetch_issue(owner, repo, token, label)
        except (urllib.error.HTTPError, urllib.error.URLError):
            existing = None
        if existing:
            return f"DRY-RUN: wuerde #{existing['number']} aktualisieren (Sektion {section_name})"
        return f"DRY-RUN: wuerde neues Fleet-Issue anlegen (Sektion {section_name})"

    existing = fetch_issue(owner, repo, token, label)
    if existing:
        new_body = merge_section(existing.get("body") or "", section_name, rendered)
        if issue_needs_update(existing, title, new_body):
            _api(
                f"/repos/{owner}/{repo}/issues/{existing['number']}",
                token,
                method="PATCH",
                data={"title": title, "body": new_body},
            )
        return existing["html_url"]
    created = _api(
        f"/repos/{owner}/{repo}/issues",
        token,
        method="POST",
        data={"title": title, "body": rendered, "labels": [label]},
    )
    return created["html_url"]


# --------------------------------------------------------------------------
# CLI — fuer Bash-Workflow-Schritte (health-Sektion), Import fuer Python-
# Aufrufer (adoption-gate-Heredoc, publish_gate_meter.py)
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--section", required=True, help="Sektionsname, z.B. health")
    ap.add_argument("--heading", required=True)
    ap.add_argument("--body-file", type=argparse.FileType("r"), required=True)
    ap.add_argument("--label", default=ISSUE_LABEL)
    ap.add_argument("--title", default=ISSUE_TITLE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    if not token and not args.dry_run:
        print("FEHLER: GH_TOKEN/GITHUB_TOKEN noetig (oder --dry-run).", file=sys.stderr)
        return 2

    body = args.body_file.read()
    url = upsert_section(
        args.owner,
        args.repo,
        token,
        section_name=args.section,
        heading=args.heading,
        body=body,
        label=args.label,
        title=args.title,
        dry_run=args.dry_run,
    )
    print(f"Fleet-Issue (Sektion {args.section}): {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
