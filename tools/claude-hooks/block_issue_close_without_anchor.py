#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt `gh issue close`, solange im Issue ein Aufschub ohne Anker steht.

GATE_HEADER (KONZ-038 D8):
  "slug": "aufschub-anker"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-30"
  "evidence": "tools/claude-hooks/tests/test_block_issue_close_without_anchor.py"

Hintergrund: Retro `session-retro-2026-09-30-platform-97a9a1.md` Befund #1, #3169.
Ein Issue in einem Ziel-Repo wurde per `gh issue close` geschlossen. In einem
seiner Kommentare stand Folgearbeit, die auf ein Issue ohne Nummer verwies. Das
Gate aufschub-anker lief dort nicht: es sitzt als Workflow nur in platform, und
es prueft PRs, keine Issues, die von Hand geschlossen werden. Das Folge-Issue
entstand erst in der Retro.

Der Hook sitzt deshalb am Moment des Schliessens, und zwar in jedem Repo: er
liest Body und Kommentare des Issues mit derselben Regel wie
`tools/deferral_anchor_check.py` (Wendungsliste, Ankerfenster).

Gedeckt ist ein Fund, wenn
  * die Stelle selbst einen Anker traegt (die Regel des Werkzeugs), oder
  * der Schliess-Kommentar (`--comment`/`-c`) einen Anker nennt (#3169), also
    `Folgearbeit: #N` oder eine Issue-URL. Ohne diese Regel liesse sich ein Issue
    mit einem alten, unverankerten Kommentar nie mehr schliessen, ohne fremde
    Kommentare umzuschreiben. Grenze, bewusst: ein Anker deckt dann alle Funde.
    Der Hook erzwingt den Blick auf die Folgearbeit, nicht ein Issue je Punkt
    (entschieden in #3169).

FAIL-OPEN: kein JSON, kein `gh issue close`, Werkzeug nicht auffindbar, Repo
nicht bestimmbar, `gh` scheitert oder braucht zu lange → exit 0.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "aufschub-anker"
GH_TIMEOUT = 15

_CLOSE = re.compile(r"\bgh\s+issue\s+close\b")
_ISSUE_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")
_TRENNER = {"&&", "||", ";", "|", "&"}


def _werkzeug_pfade() -> list[Path]:
    """Checkout-Nachbar zuerst (Tests, Quelle), dann der platform-Klon (verteilte Kopie)."""
    basis = Path(os.environ.get("GITHUB_DIR") or Path.home() / "github")
    return [
        Path(__file__).resolve().parent.parent / "deferral_anchor_check.py",
        basis / "platform" / "tools" / "deferral_anchor_check.py",
    ]


def lade_werkzeug():
    """Das Pruefmodul aus platform/tools, oder None."""
    for pfad in _werkzeug_pfade():
        if not pfad.is_file():
            continue
        sys.path.insert(0, str(pfad.parent))
        spec = importlib.util.spec_from_file_location("deferral_anchor_check", pfad)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul
    return None


def zerlege(kommando: str) -> dict | None:
    """Ziel, Repo und Schliess-Kommentar des ersten `gh issue close` im Befehl."""
    treffer = _CLOSE.search(kommando)
    if not treffer:
        return None
    try:
        woerter = shlex.split(kommando[treffer.end() :])
    except ValueError:
        return None
    ziel = repo = None
    kommentar = ""
    i = 0
    while i < len(woerter):
        wort = woerter[i]
        if wort in _TRENNER:
            break
        wert = woerter[i + 1] if i + 1 < len(woerter) else ""
        if wort in ("-R", "--repo"):
            repo, i = wert, i + 2
            continue
        if wort in ("-c", "--comment"):
            kommentar, i = wert, i + 2
            continue
        if wort.startswith("--repo="):
            repo = wort.split("=", 1)[1]
        elif wort.startswith("--comment="):
            kommentar = wort.split("=", 1)[1]
        elif wort in ("-r", "--reason"):
            i += 2
            continue
        elif not wort.startswith("-") and ziel is None:
            ziel = wort
        i += 1
    if ziel is None:
        return None
    url = _ISSUE_URL.match(ziel)
    if url:
        repo, nummer = url.group(1), int(url.group(2))
    elif ziel.lstrip("#").isdigit():
        nummer = int(ziel.lstrip("#"))
    else:
        return None
    return {"nummer": nummer, "repo": repo, "kommentar": kommentar}


def _gh(args: list[str], cwd: str | None = None) -> str:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=GH_TIMEOUT,
        cwd=cwd or None,
    ).stdout


def repo_aus_cwd(cwd: str | None) -> str | None:
    try:
        return (
            _gh(
                ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd
            ).strip()
            or None
        )
    except (OSError, subprocess.SubprocessError):
        return None


def issue_stoff(werkzeug, nummer: int, repo: str) -> tuple[str, list[dict]]:
    body = json.loads(_gh(["api", f"repos/{repo}/issues/{nummer}"])).get("body") or ""
    kommentare = werkzeug._parse_verkettete_json_arrays(
        _gh(["api", f"repos/{repo}/issues/{nummer}/comments", "--paginate"])
    )
    return body, kommentare


def funde(
    werkzeug, body: str, kommentare: list[dict], schliess_kommentar: str
) -> list[str]:
    """Unverankerte Aufschub-Stellen; leer, wenn der Schliess-Kommentar einen Anker nennt."""
    if schliess_kommentar and werkzeug.ANKER.search(
        werkzeug.ohne_pr_referenzen(schliess_kommentar)
    ):
        return []
    stellen = [f"Issue-Body: {z}" for _, z in werkzeug.finde_ankerlose_stellen(body)]
    for k in kommentare:
        ort = k.get("html_url") or f"Kommentar {k.get('id', '?')}"
        stellen += [
            f"{ort}: {z}"
            for _, z in werkzeug.finde_ankerlose_stellen(k.get("body") or "")
        ]
    stellen += [
        f"Schliess-Kommentar: {z}"
        for _, z in werkzeug.finde_ankerlose_stellen(schliess_kommentar)
    ]
    return stellen


def entscheide(daten: dict, werkzeug=None, stoff=None) -> str | None:
    """Ablehnungsgrund oder None. `werkzeug`/`stoff` sind fuer Tests injizierbar."""
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    ziel = zerlege(kommando)
    if ziel is None:
        return None
    werkzeug = werkzeug or lade_werkzeug()
    if werkzeug is None:
        return None
    repo = ziel["repo"] or repo_aus_cwd(daten.get("cwd"))
    if not repo:
        return None
    try:
        body, kommentare = (stoff or issue_stoff)(werkzeug, ziel["nummer"], repo)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None
    stellen = funde(werkzeug, body, kommentare, ziel["kommentar"])
    if not stellen:
        return None
    liste = "\n".join(f"  - {s[:160]}" for s in stellen[:5])
    return (
        f"Aufschub-Anker (Retro 97a9a1 #1, #3169): {repo}#{ziel['nummer']} enthaelt "
        f"{len(stellen)} Stelle(n) mit angekuendigter Folgearbeit ohne Issue-Nummer:\n{liste}\n"
        "Folge-Issue anlegen und im Schliess-Kommentar nennen "
        '(`--comment "… Folgearbeit: #N"`), oder die Stelle ist erledigt: dann das im '
        "Schliess-Kommentar mit Verweis belegen."
    )


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    grund = entscheide(daten)
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "gh issue close",
            beleg=((daten.get("tool_input") or {}).get("command") or "")[:200],
            session=daten.get("session_id", ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": grund,
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — Hook darf nie die Sitzung blockieren
        sys.exit(0)
