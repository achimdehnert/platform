#!/usr/bin/env python3
"""Offene PRs des Tages anzeigen — Werkzeug fuer Gate `parallel-session-pr-collision`.

Anlass (Retro 2026-09-10): zwei Sitzungen bauten dieselbe Ursache im selben
Workflow (#3030 und #3033, acht Minuten auseinander), weil nichts VOR dem Start
einer Aufgabe die offenen PRs des Tages zeigt. `check_pr_collision()` in
tools/repo-session.sh blockt nur bei exaktem Task-Slug-Treffer im Branchnamen —
das reicht nicht, wenn zwei Sitzungen am selben Thema arbeiten, aber
unterschiedliche Slugs waehlen. Dieses Modul ist der billige Vorab-Blick:
offene PRs seit einem Datum, mit den beruehrten Dateien, optional markiert
gegen eine eigene Dateiliste.

Nur Python-Stdlib (kein `requests`, kein `gh`-Python-Wrapper) — `gh` selbst
wird als Subprozess aufgerufen, mit `--eingabe DATEI` als Ersatz fuer Tests
und Offline-Nutzung.

Fail-open: jeder Fehler beim Ermitteln der PRs (kein `gh`, kein Netz, kein
Repo bestimmbar, ungueltige Eingabedatei) fuehrt zu einer sichtbaren Zeile
"nicht pruefbar: <grund>" und Exit 0 — advisory, darf `repo-session.sh start`
nie blockieren.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from typing import Any

TITLE_WIDTH = 60
MAX_PATHS_SHOWN = 5
GH_FIELDS = "number,title,headRefName,author,createdAt,files"


class GhError(Exception):
    """gh war nicht nutzbar — Grund fuer die 'nicht pruefbar'-Zeile."""


def default_repo(cwd: str | None = None) -> str | None:
    """owner/repo aus `git remote get-url origin`, oder None."""
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    url = re.sub(r"\.git$", "", url)
    m = re.search(r"[:/]([^/]+/[^/]+)$", url)
    return m.group(1) if m else None


def fetch_via_gh(repo: str, seit: str, limit: int = 50) -> list[dict[str, Any]]:
    cmd = [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--search",
        f"created:>={seit}",
        "--json",
        GH_FIELDS,
        "--limit",
        str(limit),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as exc:
        raise GhError("gh nicht gefunden") from exc
    except subprocess.TimeoutExpired as exc:
        raise GhError("gh pr list Timeout") from exc
    if proc.returncode != 0:
        reason_src = (proc.stderr or proc.stdout or "").strip()
        reason = reason_src.splitlines()[0] if reason_src else "unbekannter Fehler"
        raise GhError(f"gh pr list fehlgeschlagen: {reason}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise GhError("ungültige JSON-Antwort von gh") from exc
    if not isinstance(data, list):
        raise GhError("unerwartetes Antwortformat von gh (keine Liste)")
    return data


def load_via_eingabe(pfad: str) -> list[dict[str, Any]]:
    with open(pfad, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("Eingabedatei muss eine JSON-Liste enthalten")
    return data


def author_str(pr: dict[str, Any]) -> str:
    a = pr.get("author")
    if isinstance(a, dict):
        return a.get("login") or a.get("name") or "?"
    if isinstance(a, str) and a:
        return a
    return "?"


def truncate_title(title: str, width: int = TITLE_WIDTH) -> str:
    if len(title) <= width:
        return title
    return title[: width - 1] + "…"


def pr_paths(pr: dict[str, Any]) -> list[str]:
    files = pr.get("files") or []
    return [f.get("path", "") for f in files if isinstance(f, dict) and f.get("path")]


def paths_display(pr: dict[str, Any], limit: int = MAX_PATHS_SHOWN) -> str:
    paths = pr_paths(pr)
    if not paths:
        return ""
    shown = paths[:limit]
    rest = len(paths) - len(shown)
    s = ", ".join(shown)
    if rest > 0:
        s += f" +{rest}"
    return s


def collides(pr: dict[str, Any], pfade: list[str]) -> bool:
    if not pfade:
        return False
    return bool(set(pr_paths(pr)) & set(pfade))


def format_line(pr: dict[str, Any], pfade: list[str]) -> str:
    number = pr.get("number", "?")
    title = truncate_title(str(pr.get("title", "")))
    line = f"#{number}  {title}  @{author_str(pr)}"
    paths = paths_display(pr)
    if paths:
        line += f"  {paths}"
    if collides(pr, pfade):
        line += "  ⚠ gleiche Datei"
    return line


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", help="owner/repo (Default: git remote get-url origin)")
    p.add_argument("--seit", help="YYYY-MM-DD (Default: heute)")
    p.add_argument(
        "--eingabe",
        help="JSON-Datei mit PR-Liste statt gh (für Tests / Offline-Nutzung)",
    )
    p.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    p.add_argument(
        "--pfade",
        help="Komma-getrennte Dateipfade — PRs mit Treffer werden markiert",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    seit = args.seit or date.today().isoformat()
    pfade = (
        [p.strip() for p in args.pfade.split(",") if p.strip()] if args.pfade else []
    )

    nicht_pruefbar: str | None = None
    prs: list[dict[str, Any]] = []
    repo = args.repo

    if args.eingabe:
        try:
            prs = load_via_eingabe(args.eingabe)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            nicht_pruefbar = f"Eingabedatei nicht lesbar: {exc}"
    else:
        if not repo:
            repo = default_repo()
        if not repo:
            nicht_pruefbar = "Repo nicht bestimmbar (kein --repo, kein origin-Remote)"
        else:
            try:
                prs = fetch_via_gh(repo, seit)
            except GhError as exc:
                nicht_pruefbar = str(exc)

    if args.json:
        out = {
            "repo": repo,
            "seit": seit,
            "n": None if nicht_pruefbar else len(prs),
            "nicht_pruefbar": nicht_pruefbar,
            "prs": [] if nicht_pruefbar else prs,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if nicht_pruefbar:
        print(f"nicht prüfbar: {nicht_pruefbar}")
        return 0

    n = len(prs)
    if n == 0:
        print(f"Offene PRs seit {seit}: 0 (keine — geprüft gegen gh)")
    else:
        print(f"Offene PRs seit {seit}: {n}")
        for pr in prs:
            print(format_line(pr, pfade))
    return 0


if __name__ == "__main__":
    sys.exit(main())
