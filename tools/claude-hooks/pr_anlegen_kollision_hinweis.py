#!/usr/bin/env python3
"""PreToolUse(Bash) Hinweis — zeigt beim `gh pr create` andere offene PRs mit Kollision.

GATE_HEADER (KONZ-038 D8):
  "slug": "parallel-session-pr-collision"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-10-05"
  "evidence": "tools/claude-hooks/tests/test_pr_anlegen_kollision_hinweis.py"

Hintergrund (platform#3722, Vorlage vorschlag-rueckfaellige-gates-2026-10-05, G5):
Die Liste offener PRs erscheint bisher nur beim `repo-session.sh start`. Beide
Kollisionen seit dem Umbau entstanden DANACH (zwei PR-Serien an derselben Datei,
zwei PRs zum selben Issue ohne Querverweis). Dieser Hook wiederholt den Blick im
Moment des Anlegens, beschraenkt auf zwei Merkmale:

  1. ein anderer offener PR nennt dieselbe Issue-/PR-Nummer (`#123`) in Titel/Text,
  2. ein anderer offener PR beruehrt dieselbe Datei wie der Branch gegen origin/main.

Nur Hinweis, nie Sperre: parallele Arbeit an einer Datei ist oft gewollt. Die
Vergleichslogik (`pr_paths`, Anzeige) kommt aus tools/repo_session_offene_prs.py.

FAIL-OPEN: Exit 0 in jedem Fall — kein JSON, anderes Kommando, kein gh, Drosselung,
Timeout, fehlendes Vergleichsmodul. Ein Fehler erzeugt hoechstens eine
Hinweiszeile "nicht pruefbar", nie ein deny.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "parallel-session-pr-collision"
GH_TIMEOUT = 15
GIT_TIMEOUT = 5
GH_FIELDS = "number,title,body,files,headRefName"
MAX_ZEILEN = 5

#: Dateien, die praktisch jeder PR beruehrt oder die erzeugt werden — ein Treffer
#: darauf sagt nichts ueber eine inhaltliche Kollision. (Vermutung: die Stand-Dateien
#: sind erzeugt/Sammeldateien; gemessen an der Aenderungshaeufigkeit seit 2026-09-01.)
AUSGENOMMENE_DATEIEN = frozenset(
    {
        "CHANGELOG.md",
        "AGENT_HANDOVER.md",
        "AGENT_HANDOVER_LOG.md",
        "AGENT_HANDOVER_ARCHIVE.md",
        "docs/governance/gate-registry.json",
        "docs/adr/INDEX.md",
        "docs/adr/index.json",
    }
)

_PR_CREATE = re.compile(r"(?:^|[;&|\n]|&&)\s*gh\s+pr\s+create\b")
_CD = re.compile(r"^\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)\s*&&")
_NUMMER = re.compile(r"(?<![\w/])#(\d{1,6})\b")


def ist_pr_create(kommando: str) -> bool:
    return bool(_PR_CREATE.search(kommando))


def _argumente(kommando: str) -> dict[str, str]:
    """Titel, Body, Body-Datei, Repo aus dem `gh pr create`-Teil (best effort)."""
    treffer = _PR_CREATE.search(kommando)
    if not treffer:
        return {}
    rest = kommando[treffer.end() :]
    rest = re.split(r"\s*(?:&&|\|\||;|\n|\|)\s*", rest, maxsplit=1)[0]
    try:
        teile = shlex.split(rest)
    except ValueError:
        teile = rest.split()
    aus: dict[str, str] = {}
    schluessel = {
        "--title": "title",
        "-t": "title",
        "--body": "body",
        "-b": "body",
        "--body-file": "body_file",
        "-F": "body_file",
        "--repo": "repo",
        "-R": "repo",
    }
    i = 0
    while i < len(teile):
        t = teile[i]
        if "=" in t and t.startswith("--"):
            k, _, v = t.partition("=")
            if k in schluessel:
                aus[schluessel[k]] = v
        elif t in schluessel and i + 1 < len(teile):
            aus[schluessel[t]] = teile[i + 1]
            i += 1
        i += 1
    return aus


def _arbeitsverzeichnis(kommando: str, cwd: str) -> str:
    m = _CD.match(kommando)
    if not m:
        return cwd
    ziel = os.path.expanduser(m.group(1).strip("\"'"))
    return ziel if os.path.isabs(ziel) else os.path.join(cwd, ziel)


def _git(args: list[str], cwd: str) -> str | None:
    try:
        p = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            cwd=cwd or None,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def eigene_dateien(cwd: str) -> list[str]:
    """Dateien des Branch gegen origin/main (leer, wenn nicht ermittelbar)."""
    aus = _git(["diff", "--name-only", "origin/main...HEAD"], cwd)
    return [z for z in (aus or "").splitlines() if z.strip()]


def genannte_nummern(*texte: str) -> set[str]:
    return {n for t in texte for n in _NUMMER.findall(t or "")}


def _lade_vergleich():
    """tools/repo_session_offene_prs.py importieren — neben dem Hook (Repo/Test) oder
    im Platform-Klon (verteilte Kopie unter ~/.claude/hooks, wo das Modul nicht liegt)."""
    kandidaten = [
        Path(__file__).resolve().parent.parent,
        Path(os.environ.get("PLATFORM_TOOLS_DIR", ""))
        if os.environ.get("PLATFORM_TOOLS_DIR")
        else None,
        Path.home() / "github" / "platform" / "tools",
    ]
    for k in kandidaten:
        if k and (k / "repo_session_offene_prs.py").is_file():
            sys.path.insert(0, str(k))
            try:
                import repo_session_offene_prs as modul

                return modul
            except Exception:  # noqa: BLE001 — fail-open
                return None
    return None


def offene_prs(repo: str | None, cwd: str) -> list[dict[str, Any]]:
    cmd = ["gh", "pr", "list", "--state", "open", "--json", GH_FIELDS, "--limit", "50"]
    if repo:
        cmd[3:3] = ["-R", repo]
    p = subprocess.run(
        cmd, capture_output=True, text=True, timeout=GH_TIMEOUT, cwd=cwd or None
    )
    if p.returncode != 0:
        raise RuntimeError("gh pr list fehlgeschlagen")
    daten = json.loads(p.stdout)
    if not isinstance(daten, list):
        raise RuntimeError("unerwartetes Antwortformat")
    return daten


def vergleiche(
    prs: list[dict[str, Any]],
    modul: Any,
    dateien: list[str],
    nummern: set[str],
    eigener_branch: str,
) -> list[str]:
    """Hinweiszeilen fuer fremde offene PRs mit gleicher Nummer oder Datei."""
    relevant = {d for d in dateien if d not in AUSGENOMMENE_DATEIEN}
    zeilen: list[str] = []
    for pr in prs:
        if eigener_branch and pr.get("headRefName") == eigener_branch:
            continue
        gruende = []
        geteilte = sorted(relevant & set(modul.pr_paths(pr)))
        if geteilte:
            mehr = f" +{len(geteilte) - 3}" if len(geteilte) > 3 else ""
            gruende.append("gleiche Datei: " + ", ".join(geteilte[:3]) + mehr)
        gleiche = sorted(
            nummern & genannte_nummern(pr.get("title", ""), pr.get("body", "")), key=int
        )
        if gleiche:
            gruende.append("nennt auch " + ", ".join(f"#{n}" for n in gleiche))
        if gruende:
            titel = modul.truncate_title(str(pr.get("title", "")))
            zeilen.append(
                f"  #{pr.get('number', '?')}  {titel}  — " + "; ".join(gruende)
            )
    return zeilen


def hinweis(daten: dict[str, Any]) -> str | None:
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not ist_pr_create(kommando):
        return None
    cwd = _arbeitsverzeichnis(kommando, daten.get("cwd") or os.getcwd())
    args = _argumente(kommando)
    modul = _lade_vergleich()
    if modul is None:
        return "PR-Kollisionshinweis: nicht pruefbar (Vergleichsmodul nicht gefunden)."
    repo = args.get("repo") or modul.default_repo(cwd)
    body = args.get("body", "")
    if args.get("body_file"):
        try:
            body += Path(os.path.expanduser(args["body_file"])).read_text(
                encoding="utf-8"
            )
        except OSError:
            pass
    nummern = genannte_nummern(args.get("title", ""), body)
    dateien = eigene_dateien(cwd)
    branch = (_git(["branch", "--show-current"], cwd) or "").strip()
    try:
        prs = offene_prs(repo, cwd)
    except Exception as exc:  # noqa: BLE001 — gh-Fehler/Drosselung/Timeout: fail-open
        return f"PR-Kollisionshinweis: nicht pruefbar ({type(exc).__name__})."
    zeilen = vergleiche(prs, modul, dateien, nummern, branch)
    if not zeilen:
        return None
    kopf = (
        "PR-Kollisionshinweis (nur Hinweis, keine Sperre): andere offene PRs im selben Repo "
        "nennen dieselbe Nummer oder beruehren dieselbe Datei — Querverweis oder Absprache pruefen:"
    )
    mehr = len(zeilen) - MAX_ZEILEN
    ausgabe = zeilen[:MAX_ZEILEN] + ([f"  … +{mehr} weitere"] if mehr > 0 else [])
    return "\n".join([kopf, *ausgabe])


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(daten, dict):
        return 0
    text = hinweis(daten)
    if not text:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "pr create hinweis",
            beleg=text[:200],
            session=daten.get("session_id", ""),
            modus="advisory",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": text,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


def main_sicher() -> int:
    """Hook-Vertrag: Exit 0 immer."""
    try:
        return main()
    except BaseException as exc:  # noqa: BLE001 — auch Timeout/Interrupt: nie blockieren
        print(
            f"pr_anlegen_kollision_hinweis: {type(exc).__name__}"[:200], file=sys.stderr
        )
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
