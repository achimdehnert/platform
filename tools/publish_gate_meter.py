#!/usr/bin/env python3
"""Publish-Gate-Meter — fleet-weiter, informativer Backlog ungegateter PyPI-Uploads.

Phase 2a des Recurrence-Guards (ADR-226). Spiegelt das Muster des
ADR-226-Adoption-Gate: zählt die Registry-Repos auf, prüft per GitHub-API ihre
Default-Branch-Workflows mit `tools/check_publish_gate.py` (Invariante (c):
Test- ODER Secret-Scan-Gate vor dem Upload) und pflegt EIN Tracking-Issue,
dessen Body der schrumpfende Backlog ist.

BEWUSST informativ — bricht NIE eine CI (sonst wird der Meter selbst zum Rauschen,
das man abschaltet). Per-Repo-Blocking ist eine spätere Phase (2b), erst nachdem
dieser Meter 0 False Positives über die Flotte gezeigt und der Backlog gedrained ist.

Schreibrecht: nur EIN Issue im platform-Repo (issues:write), read-only gegen alle
anderen Repos. `--dry-run` schreibt kein Issue (nur Report) — für Dry-Run-in-CI.

GRENZE (bewusst): Der Meter sieht nur, was in `scripts/repo-registry.yaml` steht
(Default: type=library). PyPI-Publisher, die NICHT in der Registry registriert
sind (z.B. iil-adrfw, iil-codeguard — Stand 2026-06-30), sind unsichtbar — wie
auch für den ADR-226-Adoption-Gate. Fix gehört in die Registry, nicht hierher.
`--all-types` weitet auf alle Registry-Typen, ersetzt aber keine fehlenden Einträge.

Usage:
    python3 tools/publish_gate_meter.py [--dry-run] [--all-types] [--fail-on-backlog]
    python3 tools/publish_gate_meter.py --local ~/github --dry-run   # offline gegen lokale Klone
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

import yaml

_HERE = pathlib.Path(__file__).resolve().parent
_GUARD = importlib.util.spec_from_file_location("check_publish_gate", _HERE / "check_publish_gate.py")
cpg = importlib.util.module_from_spec(_GUARD)
_GUARD.loader.exec_module(cpg)

REGISTRY = "scripts/repo-registry.yaml"
MARKER_LABEL = "publish-gate-backlog"
ISSUE_TITLE = "Publish-Gate-Backlog: ungegatete PyPI-Uploads"


# ---------------------------------------------------------------- pure logic --
def scan_files(files: dict) -> list:
    """files = {workflow_filename: yaml_content} → Liste {file, job} ungegateter Uploads."""
    offenders = []
    for name, content in sorted(files.items()):
        for job in cpg.analyze_workflow(content)["offenders"]:
            offenders.append({"file": name, "job": job})
    return offenders


def build_backlog(results: dict, owner: str) -> str:
    """results = {repo: [ {file, job}, ... ]} → Markdown-Body des Tracking-Issues."""
    offenders = {r: v for r, v in results.items() if v}
    total_jobs = sum(len(v) for v in offenders.values())
    lines = [
        "_Automatisch gepflegt vom Publish-Gate-Meter (`tools/publish_gate_meter.py`)._",
        "",
        "Invariante (c) — jeder PyPI-Upload-Job braucht unmittelbar davor (self- oder "
        "transitiv per `needs:`) **mindestens einen** bindenden Gate: Test (`pytest`) "
        "ODER Secret-Scan (`gitleaks`). Quelle: ADR-226.",
        "",
    ]
    if not offenders:
        lines.append("✅ **Backlog leer** — alle geprüften Upload-Workflows sind gegated.")
        return "\n".join(lines)
    lines.append(f"⛔ **{total_jobs} ungegatete Upload-Job(s) in {len(offenders)} Repo(s):**")
    lines.append("")
    lines.append("| Repo | Workflow | Job |")
    lines.append("|---|---|---|")
    for repo in sorted(offenders):
        for o in offenders[repo]:
            lines.append(f"| {owner}/{repo} | `{o['file']}` | `{o['job']}` |")
    lines.append("")
    lines.append("**Fix:** Test- oder Secret-Scan-Gate vor den Upload ziehen. "
                 "Lokal prüfbar: `python3 tools/check_publish_gate.py <repo-pfad>`.")
    return "\n".join(lines)


def registry_repos(text: str, all_types: bool) -> list:
    reg = yaml.safe_load(text)
    repos = reg.get("repos", {}) or {}
    out = []
    for name, meta in repos.items():
        if not isinstance(meta, dict):
            continue
        if all_types or meta.get("type") == "library":
            out.append(name)
    return sorted(out)


# --------------------------------------------------------------- API helpers --
def _api(path: str, token: str, raw: bool = False, method: str = "GET", data=None):
    req = urllib.request.Request(f"https://api.github.com{path}", method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.raw" if raw else "application/vnd.github+json")
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        body = r.read().decode()
    return body if raw else json.loads(body)


def fetch_repo_workflows_api(owner: str, repo: str, token: str) -> dict:
    """{filename: content} aller .github/workflows/*.y*ml des Default-Branch (read-only)."""
    try:
        listing = _api(f"/repos/{owner}/{repo}/contents/.github/workflows", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise
    files = {}
    for item in listing:
        name = item.get("name", "")
        if name.endswith((".yml", ".yaml")) and item.get("type") == "file":
            files[name] = _api(
                f"/repos/{owner}/{repo}/contents/.github/workflows/{name}", token, raw=True
            )
    return files


def fetch_repo_workflows_local(root: pathlib.Path, repo: str) -> dict:
    wf = root / repo / ".github" / "workflows"
    if not wf.is_dir():
        return {}
    return {
        f.name: f.read_text(encoding="utf-8")
        for f in wf.iterdir()
        if f.suffix in (".yml", ".yaml")
    }


def upsert_issue(owner: str, repo: str, token: str, title: str, body: str) -> str:
    """Findet offenes Issue mit MARKER_LABEL und aktualisiert es, sonst neu. Returns URL."""
    issues = _api(f"/repos/{owner}/{repo}/issues?state=open&labels={MARKER_LABEL}", token)
    if issues:
        num = issues[0]["number"]
        _api(f"/repos/{owner}/{repo}/issues/{num}", token, method="PATCH",
             data={"title": title, "body": body})
        return issues[0]["html_url"]
    created = _api(f"/repos/{owner}/{repo}/issues", token, method="POST",
                   data={"title": title, "body": body, "labels": [MARKER_LABEL]})
    return created["html_url"]


# --------------------------------------------------------------------- main ---
def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Publish-Gate-Meter")
    ap.add_argument("--dry-run", action="store_true", help="kein Issue schreiben, nur Report")
    ap.add_argument("--all-types", action="store_true", help="alle Repo-Typen statt nur library")
    ap.add_argument("--fail-on-backlog", action="store_true", help="Exit 1 wenn Backlog > 0")
    ap.add_argument("--local", metavar="ROOT", help="offline gegen lokale Klone unter ROOT")
    args = ap.parse_args(argv)

    owner = os.environ.get("OWNER", "achimdehnert")
    repos = registry_repos(pathlib.Path(REGISTRY).read_text(), args.all_types)

    results = {}
    if args.local:
        root = pathlib.Path(args.local).expanduser()
        for r in repos:
            results[r] = scan_files(fetch_repo_workflows_local(root, r))
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print("FEHLER: GH_TOKEN/GITHUB_TOKEN nötig (oder --local nutzen).", file=sys.stderr)
            return 2
        for r in repos:
            results[r] = scan_files(fetch_repo_workflows_api(owner, r, token))

    body = build_backlog(results, owner)
    total = sum(len(v) for v in results.values())
    print(body)

    if not args.dry_run:
        url = upsert_issue(owner, "platform", os.environ["GH_TOKEN"], ISSUE_TITLE, body)
        print(f"\nTracking-Issue: {url}", file=sys.stderr)

    if args.fail_on_backlog and total:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
