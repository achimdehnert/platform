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

Die Registry wird über `tools/registry_api.py` gelesen (sanktionierter Accessor,
ADR-234 §11.1 — die View-Dateien sind generiert, Direkt-Lesen ist ein hartes Gate).

GRENZE (bewusst): Der Meter sieht nur, was in der kanonischen Registry steht
(Default: type=library). PyPI-Publisher, die NICHT registriert sind (z.B.
iil-adrfw, iil-codeguard — Stand 2026-06-30), sind unsichtbar — wie auch für den
ADR-226-Adoption-Gate. Fix gehört in die Registry, nicht hierher. `--all-types`
weitet auf alle Registry-Typen, ersetzt aber keine fehlenden Einträge.

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


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_HERE = pathlib.Path(__file__).resolve().parent
cpg = _load("check_publish_gate")
# Registry NUR über den sanktionierten Accessor lesen (ADR-234 §11.1 REC-4 —
# die View-Dateien sind generiert; Direkt-Lesen ist ein hartes Gate).
registry_api = _load("registry_api")

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


def build_backlog(results: dict, owners: dict) -> str:
    """results = {repo: [ {file, job}, ... ]} → Markdown-Body des Tracking-Issues.

    `owners` = {repo: github_owner} — per-Repo statt fester Fleet-Org (FUNC-3,
    #1202): `--all-types` zieht auch iilgmbh-/meiki-lra-/ttz-lif-Repos rein,
    die nicht unter dem achimdehnert-Fallback erreichbar sind.
    """
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
            lines.append(f"| {owners.get(repo, repo)}/{repo} | `{o['file']}` | `{o['job']}` |")
    lines.append("")
    lines.append("**Fix:** Test- oder Secret-Scan-Gate vor den Upload ziehen. "
                 "Lokal prüfbar: `python3 tools/check_publish_gate.py <repo-pfad>`.")
    return "\n".join(lines)


def registry_repos(repos: dict, all_types: bool) -> list:
    """repos = {name: {type, ...}} (z.B. registry_api.flat()['repos']) → gefilterte Namen."""
    out = []
    for name, meta in (repos or {}).items():
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


def issue_needs_update(existing: dict, title: str, body: str) -> bool:
    """True, wenn Titel/Body abweichen — sonst kein PATCH (vermeidet tägliches No-Op-Rauschen)."""
    return existing.get("title") != title or (existing.get("body") or "") != body


def upsert_issue(owner: str, repo: str, token: str, title: str, body: str) -> str:
    """Findet offenes Issue mit MARKER_LABEL, PATCHt es NUR bei Änderung, sonst neu. Returns URL."""
    issues = _api(f"/repos/{owner}/{repo}/issues?state=open&labels={MARKER_LABEL}", token)
    if issues:
        existing = issues[0]
        if issue_needs_update(existing, title, body):
            _api(f"/repos/{owner}/{repo}/issues/{existing['number']}", token, method="PATCH",
                 data={"title": title, "body": body})
        return existing["html_url"]
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

    default_owner = os.environ.get("OWNER", "achimdehnert")
    canon = registry_api.flat()
    repos = registry_repos(canon.get("repos", {}), args.all_types)

    # FUNC-3 (#1202): per-Repo statt fester `owner`-Fallback — mit --all-types
    # kommen iilgmbh-/meiki-lra-/ttz-lif-Repos rein, die unter dem
    # achimdehnert-Default falsch/leer gescannt würden (404 gegen fremde Org).
    owners = {r: (registry_api.owner(r, canon) or default_owner) for r in repos}

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")

    results = {}
    if args.local:
        root = pathlib.Path(args.local).expanduser()
        for r in repos:
            results[r] = scan_files(fetch_repo_workflows_local(root, r))
    else:
        if not token:
            print("FEHLER: GH_TOKEN/GITHUB_TOKEN nötig (oder --local nutzen).", file=sys.stderr)
            return 2
        for r in repos:
            results[r] = scan_files(fetch_repo_workflows_api(owners[r], r, token))

    body = build_backlog(results, owners)
    total = sum(len(v) for v in results.values())
    print(body)

    if not args.dry_run:
        # Guard gilt für BEIDE Pfade: --local ohne Token + ohne --dry-run darf hier nicht
        # mit KeyError sterben (Retro-Increment 2026-06-30 F4). token vorher gehoben.
        if not token:
            print("FEHLER: Issue-Upsert braucht GH_TOKEN/GITHUB_TOKEN (oder --dry-run nutzen).", file=sys.stderr)
            return 2
        # Tracking-Issue lebt IMMER in achimdehnert/platform (SSoT-Repo für den
        # Meter selbst), unabhängig vom Owner der gescannten Repos.
        url = upsert_issue(default_owner, "platform", token, ISSUE_TITLE, body)
        print(f"\nTracking-Issue: {url}", file=sys.stderr)

    if args.fail_on_backlog and total:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
