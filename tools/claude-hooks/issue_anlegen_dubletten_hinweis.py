#!/usr/bin/env python3
"""PreToolUse(Bash) Hinweis — zeigt beim `gh issue create` moegliche Dubletten im Zielrepo.

GATE_HEADER (KONZ-038 D8):
  "slug": "issue-ohne-dublettensuche"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-10-14"
  "evidence": "tools/claude-hooks/tests/test_issue_anlegen_dubletten_hinweis.py"

Hintergrund (Retro ec3416 Befund 11, Owner-Wort „R6 go" 2026-10-14 21:01Z):
iilgmbh/shared-ci#113 (15:17Z) wurde zum selben 0-Jobs-Lauf angelegt wie #112 (14:43Z,
andere Sitzung) — ohne Querverweis, mit konkurrierender Hypothese; meiki-hub#630 hatte das
Event-Muster schon 13:04Z benannt. Zwei Issues zu einem Lauf loest niemand auf.

Der Hook wiederholt im Moment des Anlegens die Suche, die vorher fehlte:

  1. exakte Marker aus Titel/Text (Run-IDs mit >= 9 Ziffern, `#123`, `owner/repo#123`),
  2. sonst die laengsten Woerter des Titels als UND-Suche

per `gh issue list -R <repo> --state all --search …`. Treffer werden gezeigt, mehr nicht:
die Entscheidung Kommentar-statt-Issue bleibt beim Agenten. Enthaelt dasselbe Kommando
schon ein `gh issue list`/`gh search issues`, schweigt der Hook — die Suche ist dann getan.

FAIL-OPEN: Exit 0 in jedem Fall — kein JSON, anderes Kommando, kein gh, Drosselung,
Timeout. Ein Fehler erzeugt hoechstens eine Hinweiszeile "nicht pruefbar", nie ein deny.
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

SLUG = "issue-ohne-dublettensuche"
GH_TIMEOUT = 8
GIT_TIMEOUT = 3
MAX_TREFFER = 5
#: Woerter unter dieser Laenge tragen in einer Issue-Suche nichts (Artikel, Praepositionen).
MIN_WORTLAENGE = 5
MAX_SUCHWOERTER = 3
#: GitHub-Run-IDs haben derzeit 11 Ziffern; ab 9 gilt eine Zahl als Lauf- oder Objekt-ID.
MIN_ID_ZIFFERN = 9

_ISSUE_CREATE = re.compile(r"(?:^|[;&|\n]|&&)\s*gh\s+issue\s+create\b")
_SUCHE_IM_KOMMANDO = re.compile(r"\bgh\s+(?:issue\s+list|search\s+issues)\b")
_RUN_ID = re.compile(r"(?<!\d)\d{%d,}(?!\d)" % MIN_ID_ZIFFERN)
_ISSUE_REF = re.compile(r"(?<![\w/])(?:[\w.-]+/[\w.-]+)?#(\d{1,6})\b")
_WORT = re.compile(r"[A-Za-zÄÖÜäöüß][\w-]{%d,}" % (MIN_WORTLAENGE - 1))
_REMOTE = re.compile(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$")
#: Woerter, die in fast jedem Issue-Titel stehen und darum nichts eingrenzen.
STOPPWOERTER = frozenset(
    {
        "closes",
        "fixes",
        "issue",
        "nicht",
        "ohne",
        "nach",
        "wegen",
        "durch",
        "einer",
        "einem",
        "eines",
        "beim",
        "when",
        "with",
        "from",
        "after",
        "before",
        "should",
    }
)


def ist_issue_create(kommando: str) -> bool:
    return bool(_ISSUE_CREATE.search(kommando))


def suche_schon_im_kommando(kommando: str) -> bool:
    treffer = _ISSUE_CREATE.search(kommando)
    vorher = kommando[: treffer.start()] if treffer else kommando
    return bool(_SUCHE_IM_KOMMANDO.search(vorher))


def _argumente(kommando: str) -> dict[str, str]:
    """Titel, Body, Body-Datei, Repo aus dem `gh issue create`-Teil (best effort)."""
    treffer = _ISSUE_CREATE.search(kommando)
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


def default_repo(cwd: str) -> str | None:
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    m = _REMOTE.search(res.stdout.strip())
    return m.group(1) if m else None


def suchbegriffe(titel: str, body: str) -> list[str]:
    """Exakte Marker zuerst (Run-IDs, Issue-Nummern), sonst die laengsten Titelwoerter."""
    text = f"{titel}\n{body}"
    marker: list[str] = []
    for m in _RUN_ID.finditer(text):
        if m.group(0) not in marker:
            marker.append(m.group(0))
    for m in _ISSUE_REF.finditer(text):
        nummer = f"#{m.group(1)}"
        if nummer not in marker:
            marker.append(nummer)
    if marker:
        return marker[:MAX_SUCHWOERTER]
    woerter = [w for w in _WORT.findall(titel) if w.lower() not in STOPPWOERTER]
    woerter.sort(key=len, reverse=True)
    gewaehlt: list[str] = []
    for w in woerter:
        if w.lower() not in {g.lower() for g in gewaehlt}:
            gewaehlt.append(w)
        if len(gewaehlt) == MAX_SUCHWOERTER:
            break
    return gewaehlt


def issues_suchen(repo: str, begriffe: list[str]) -> list[dict[str, Any]]:
    """`gh issue list --search` — Marker einzeln (ODER), Woerter gemeinsam (UND)."""
    if not begriffe:
        return []
    exakt = all(b.startswith("#") or b.isdigit() for b in begriffe)
    anfragen = (
        [f'"{b.lstrip("#")}"' for b in begriffe] if exakt else [" ".join(begriffe)]
    )
    treffer: dict[int, dict[str, Any]] = {}
    for anfrage in anfragen:
        res = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "-R",
                repo,
                "--state",
                "all",
                "--search",
                anfrage,
                "--limit",
                str(MAX_TREFFER),
                "--json",
                "number,title,state,updatedAt",
            ],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
            check=True,
        )
        for eintrag in json.loads(res.stdout or "[]"):
            try:
                treffer.setdefault(int(eintrag["number"]), eintrag)
            except (KeyError, TypeError, ValueError):
                continue
    return [treffer[n] for n in sorted(treffer, reverse=True)][:MAX_TREFFER]


def hinweis(daten: dict[str, Any]) -> str | None:
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not ist_issue_create(kommando) or suche_schon_im_kommando(kommando):
        return None
    cwd = daten.get("cwd") or os.getcwd()
    args = _argumente(kommando)
    repo = args.get("repo") or default_repo(cwd)
    if not repo:
        return None
    body = args.get("body", "")
    if args.get("body_file"):
        try:
            body += Path(os.path.expanduser(args["body_file"])).read_text(
                encoding="utf-8"
            )
        except OSError:
            pass
    begriffe = suchbegriffe(args.get("title", ""), body)
    if not begriffe:
        return None
    try:
        treffer = issues_suchen(repo, begriffe)
    except Exception as exc:  # noqa: BLE001 — gh-Fehler/Drosselung/Timeout: fail-open
        return f"Dubletten-Hinweis ({SLUG}): nicht pruefbar ({type(exc).__name__})."
    if not treffer:
        return None
    zeilen = [
        f"Dubletten-Hinweis ({SLUG}, nur Hinweis): {repo} hat zu "
        + ", ".join(begriffe)
        + " schon Issues — Kommentar mit Querverweis statt neues Issue pruefen:"
    ]
    for t in treffer:
        zeilen.append(
            f"  #{t.get('number', '?')} [{str(t.get('state', '')).lower()}] "
            f"{str(t.get('title', ''))[:80]} · {str(t.get('updatedAt', ''))[:10]}"
        )
    if repo.endswith("/shared-ci"):
        zeilen.append(
            "  shared-ci: Konsumenten-Repos sahen das Symptom frueher (Retro ec3416: meiki-hub#630) — dort ebenfalls suchen."
        )
    return "\n".join(zeilen)


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
            "issue create hinweis",
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
            f"issue_anlegen_dubletten_hinweis: {type(exc).__name__}"[:200],
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
