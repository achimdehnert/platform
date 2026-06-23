#!/usr/bin/env python3
"""Deploy-Failure-Monitor — Gate gegen `deploy-failures-no-fix` (session-retro 2026-06-22).

Problem: Ein main-Deploy kann tagelang rot bleiben, ohne dass es jemand bemerkt — das
einzige Signal ist eine per-Run-Discord-Nachricht (fire-and-forget). Realfall: illustration-hub
deployte 13 Tage / 13 Runs nicht, unbemerkt; der Slug `deploy-failures-no-fix` ist über
Retros ≥2 → Gate-Pflicht.

Dieser Monitor (scheduled, platform-zentral, opt-in via Registry) scannt je django-Repo die
jüngste main-Deploy-Historie, zählt **konsekutive** Fehlschläge von oben und eskaliert ab
`--threshold` (Default 2) zu einem dedup-ten Tracking-Issue IM Ziel-Repo (statt nur Discord).

Trennung wie tools/backup_meter.py: pure, testbare Logik (count_leading_failures /
evaluate_repo / render_issue_body) getrennt von I/O (gh-CLI in main()).
Stdlib + PyYAML, kein Setup.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

# Conclusions, die als „Deploy kaputt" zählen. `cancelled`/`skipped`/`None` (in_progress)
# zählen NICHT und brechen die Serie auch nicht (uninformativ); `success` bricht sie.
FAILURE_CONCLUSIONS = {"failure", "startup_failure", "timed_out"}
SKIP_CONCLUSIONS = {
    "cancelled",
    "skipped",
    None,
    "",
    "action_required",
    "neutral",
    "stale",
}

ISSUE_LABEL = "deploy-failure-escalation"


def count_leading_failures(runs: list[dict]) -> int:
    """Konsekutive Deploy-Fehlschläge vom jüngsten Run abwärts.

    runs: most-recent-first, je {conclusion: str|None, ...}. In-progress/cancelled/skipped
    werden übersprungen (zählen nicht, brechen nicht); `success` bricht die Serie.
    """
    count = 0
    for run in runs:
        c = run.get("conclusion")
        if c in FAILURE_CONCLUSIONS:
            count += 1
        elif c in SKIP_CONCLUSIONS:
            continue
        else:  # success o. unbekanntes Ergebnis = Serie zu Ende
            break
    return count


def evaluate_repo(repo: str, runs: list[dict], threshold: int) -> dict:
    """Wertet einen Repo-Lauf aus → {repo, consecutive, escalate, runs}."""
    consecutive = count_leading_failures(runs)
    return {
        "repo": repo,
        "consecutive": consecutive,
        "escalate": consecutive >= threshold,
        "runs": runs[:consecutive] if consecutive else [],
    }


def render_issue_body(result: dict, org: str) -> str:
    repo = result["repo"]
    n = result["consecutive"]
    lines = [
        f"**{n}× konsekutiv** rotes `Deploy` auf `main` — automatisch erkannt vom",
        "platform Deploy-Failure-Monitor (Gate gegen `deploy-failures-no-fix`).",
        "",
        "> Hintergrund: ein lange rotes Deploy-Gate sammelt unbemerkt prod-brechende",
        "> Config an; der erste wieder-grüne Deploy ist dann riskant (Incident-Muster",
        "> illustration-hub 2026-06-22, session-retro).",
        "",
        "## Betroffene Runs (jüngste zuerst)",
    ]
    for run in result["runs"]:
        url = run.get("url", "")
        sha = (run.get("headSha") or "")[:7]
        created = (run.get("createdAt") or "")[:16]
        lines.append(f"- {run.get('conclusion')} · `{sha}` · {created} · {url}")
    lines += [
        "",
        "## Billigster Check",
        f"`gh run list --repo {org}/{repo} --workflow Deploy --branch main --limit 5`",
        "→ den jüngsten roten Run öffnen, den failenden Step lesen, fixen ODER Deploy bewusst pausieren.",
        "",
        "_Dieses Issue wird vom Monitor aktualisiert, solange die Serie anhält, und sollte",
        "nach dem Fix (erster grüner Deploy) manuell geschlossen werden._",
    ]
    return "\n".join(lines)


# ── I/O ─────────────────────────────────────────────────────────────────────


def load_deploy_repos(registry_path: Path) -> list[str]:
    """django-Repos (deployen) aus der Registry-SSoT, ohne archivierte."""
    data = yaml.safe_load(registry_path.read_text())
    repos = data.get("repos", {})
    out = []
    for name, cfg in sorted(repos.items()):
        cfg = cfg or {}
        if cfg.get("type") == "django" and not cfg.get("archived"):
            out.append(name)
    return out


class FetchError(RuntimeError):
    """gh konnte die Deploy-Runs eines Repos NICHT lesen (Auth/Scope/Repo-Zugriff).

    Wichtig: NICHT als leere Liste (= 'grün') behandeln — sonst meldet der Monitor
    genau die Ausfälle still grün, die er fangen soll (Realfall 2026-06-22: der
    Actions-Lauf mit PLATFORM_GITHUB_TOKEN meldete weltenhub/research-hub grün,
    obwohl sie 10× rot waren, weil `gh` sie nicht lesen konnte → return []).
    """


class NoDeployWorkflow(RuntimeError):
    """Repo hat keinen Workflow namens 'Deploy' → nichts zu überwachen (N/A, KEIN Fehler).

    Abzugrenzen von FetchError (Auth/Scope = echter blinder Fleck, rot): ein Repo ohne
    Deploy-Workflow ist legitim N/A und darf den Monitor-Lauf nicht rot färben
    (Realfall 2026-06-22: onboarding-hub, `gh: could not find any workflows named Deploy`).
    """


def fetch_runs(org: str, repo: str, limit: int) -> list[dict]:
    """gh run list für den Deploy-Workflow auf main (most-recent-first).

    Raises FetchError, wenn `gh` non-zero zurückgibt oder die Ausgabe kein valides
    JSON ist — der Aufrufer MUSS 'nicht lesbar' von 'leer/grün' unterscheiden.
    Eine genuine leere Liste (returncode 0, '[]') ist legitim grün.
    """
    cmd = [
        "gh",
        "run",
        "list",
        "--repo",
        f"{org}/{repo}",
        "--workflow",
        "Deploy",
        "--branch",
        "main",
        "--limit",
        str(limit),
        "--json",
        "conclusion,status,databaseId,headSha,createdAt,url",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        stderr = (res.stderr or "").strip()
        if "could not find any workflows" in stderr.lower():
            raise NoDeployWorkflow(f"{org}/{repo}: kein 'Deploy'-Workflow")
        raise FetchError(f"{org}/{repo}: gh exit {res.returncode}: {stderr[:200]}")
    try:
        return json.loads(res.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise FetchError(f"{org}/{repo}: ungültiges JSON von gh: {exc}") from exc


def escalate_issue(org: str, repo: str, result: dict, dry_run: bool) -> str:
    """Dedup-tes Tracking-Issue im Ziel-Repo anlegen/aktualisieren. Gibt Aktion zurück."""
    n = result["consecutive"]
    title = f"[deploy-gate] main Deploy {n}× konsekutiv rot"
    body = render_issue_body(result, org)
    if dry_run:
        return f"DRY-RUN would escalate {repo} ({n}×)"

    # Label sicherstellen (idempotent)
    subprocess.run(
        [
            "gh",
            "label",
            "create",
            ISSUE_LABEL,
            "--repo",
            f"{org}/{repo}",
            "--color",
            "B60205",
            "--description",
            "Auto: konsekutive Deploy-Fehler",
            "--force",
        ],
        capture_output=True,
        text=True,
    )
    # offenes Issue mit dem Label suchen
    found = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            f"{org}/{repo}",
            "--state",
            "open",
            "--label",
            ISSUE_LABEL,
            "--json",
            "number",
            "--jq",
            ".[0].number",
        ],
        capture_output=True,
        text=True,
    )
    existing = (found.stdout or "").strip()
    if existing:
        subprocess.run(
            [
                "gh",
                "issue",
                "comment",
                existing,
                "--repo",
                f"{org}/{repo}",
                "--body",
                f"Serie hält an: jetzt **{n}×** konsekutiv rot.\n\n{body}",
            ],
            capture_output=True,
            text=True,
        )
        return f"updated #{existing} ({repo}, {n}×)"
    created = subprocess.run(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            f"{org}/{repo}",
            "--title",
            title,
            "--label",
            ISSUE_LABEL,
            "--body",
            body,
        ],
        capture_output=True,
        text=True,
    )
    return f"created ({repo}, {n}×): {(created.stdout or '').strip()}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="scripts/repo-registry.yaml")
    parser.add_argument("--org", default="achimdehnert")
    parser.add_argument("--threshold", type=int, default=2)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="Nur dieses eine Repo prüfen (Debug)")
    args = parser.parse_args()

    repos = load_deploy_repos(Path(args.registry))
    if args.only:
        repos = [args.only]
    escalations = 0
    unreadable: list[str] = []
    print(
        f"Deploy-Failure-Monitor: {len(repos)} Repo(s), Schwelle {args.threshold}× "
        f"{'(DRY-RUN)' if args.dry_run else ''}"
    )
    na = 0
    for repo in repos:
        try:
            runs = fetch_runs(args.org, repo, args.limit)
        except NoDeployWorkflow:
            # Legitim N/A: kein Deploy-Workflow → nichts zu überwachen, KEIN Fehler/rot.
            na += 1
            print(f"  ℹ️  {repo}: kein Deploy-Workflow (N/A)")
            continue
        except FetchError as exc:
            # NICHT als grün durchwinken — laut melden; ein nicht lesbares Repo ist ein
            # blinder Fleck, kein gesundes Deploy (Realfall 2026-06-22 PLATFORM_GITHUB_TOKEN).
            unreadable.append(repo)
            print(f"  ⚠️  {repo}: NICHT LESBAR — {exc}")
            continue
        result = evaluate_repo(repo, runs, args.threshold)
        if result["escalate"]:
            escalations += 1
            print(
                f"  🔴 {repo}: {result['consecutive']}× → {escalate_issue(args.org, repo, result, args.dry_run)}"
            )
        elif result["consecutive"]:
            print(f"  🟡 {repo}: {result['consecutive']}× (unter Schwelle)")
        else:
            print(f"  ✅ {repo}: grün")
    print(f"→ {escalations} Eskalation(en); {na} N/A; {len(unreadable)} nicht lesbar.")
    if unreadable:
        # Non-zero exit → der scheduled Actions-Run wird ROT (sichtbar), statt still grün
        # blinde Flecken zu verstecken. Ursache i.d.R.: Token-Scope (actions:read/repo).
        print(
            f"❌ {len(unreadable)} Repo(s) nicht lesbar: {', '.join(unreadable)} — Token-Scope (actions:read/repo) prüfen."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
