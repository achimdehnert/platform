#!/usr/bin/env python3
"""policy_frische.py — sind die ausgelieferten Policies noch die aus `origin/main`?

Der Pin-Mechanismus hat eine stille Bremse: `refresh_pinned_policies.sh` ueberspringt
den Refresh, wenn `~/github/platform-pinned` DIRTY ist. Danach altern
`~/.claude/policies/*.md` unbemerkt weiter, waehrend `inject_policies.py` sie bei
JEDEM Prompt injiziert — der Injektor prueft keine Frische. Gemessen am 2026-07-31:
ein von einer fremden Sitzung gesetzter Pin lag 17 Commits zurueck, darunter PR #1601,
der genau zwei der betroffenen Policies aenderte. Der Hinweis dazu erscheint einmal
beim Sitzungsstart und verschwindet; injiziert wird stundenlang weiter.

Geurteilt wird am INHALT gegen `origin/main`, nicht an der mtime: die ausgelieferten
Dateien tragen das Datum ihrer letzten Aenderung, nicht das ihrer letzten Pruefung —
16 von 16 trugen am 2026-08-23 den 3. August und waren trotzdem aktuell.

Slug: `platform-pinned-perma-dirty-loop` (3x in den Retros, bis hierhin ohne Gate).

Usage: policy_frische.py [--kurz] [--policies <dir>] [--repo <dir>]
Exit 0 immer — ein Melder, der den Start aufhaelt, wird abgeschaltet.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

GATE_HEADER = {
    "slug": "platform-pinned-perma-dirty-loop",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-23",
    "evidence": "tools/tests/test_policy_frische.py",
}

STANDARD_POLICIES = Path.home() / ".claude" / "policies"
STANDARD_REPO = Path(os.environ.get("GITHUB_DIR", Path.home() / "github")) / "platform"
PIN_WORKTREE = Path(os.environ.get("GITHUB_DIR", Path.home() / "github")) / "platform-pinned"


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return p.returncode, p.stdout


def kanonisch(repo: Path, name: str, ref: str = "origin/main") -> str | None:
    """Inhalt einer Policy aus `ref` — None, wenn es sie dort nicht gibt."""
    rc, out = _git(repo, "show", f"{ref}:policies/{name}")
    return out if rc == 0 else None


def pin_dirty(pin: Path = PIN_WORKTREE) -> bool | None:
    """True/False ob der Pin-Worktree dirty ist; None wenn es ihn nicht gibt.

    Das ist die URSACHE, nicht der Befund: ein dirty Pin friert den Refresh ein.
    Sie wird mitgemeldet, damit die Meldung sagt, was zu tun ist.
    """
    if not (pin / ".git").exists():
        return None
    rc, out = _git(pin, "status", "--porcelain")
    if rc != 0:
        return None
    return bool(out.strip())


def vergleiche(policies: Path, repo: Path, ref: str = "origin/main") -> dict:
    """→ {'geprueft': n, 'abweichend': [...], 'unbekannt': [...]}"""
    abweichend: list[str] = []
    unbekannt: list[str] = []
    geprueft = 0
    if not policies.is_dir():
        return {"geprueft": 0, "abweichend": [], "unbekannt": [], "kein_verzeichnis": True}
    for datei in sorted(policies.glob("*.md")):
        quelle = kanonisch(repo, datei.name, ref)
        if quelle is None:
            unbekannt.append(datei.name)
            continue
        geprueft += 1
        try:
            live = datei.read_text(encoding="utf-8")
        except OSError:
            abweichend.append(datei.name)
            continue
        if live.rstrip("\n") != quelle.rstrip("\n"):
            abweichend.append(datei.name)
    return {"geprueft": geprueft, "abweichend": abweichend, "unbekannt": unbekannt}


def bericht(stand: dict, dirty: bool | None, kurz: bool) -> str:
    if stand.get("kein_verzeichnis"):
        return "" if kurz else "Kein Policy-Verzeichnis — nichts geprueft."
    if not stand["abweichend"]:
        if kurz:
            return ""
        return (
            f"{stand['geprueft']} Policy-Datei(en) inhaltsgleich mit origin/main."
            + (f" ({len(stand['unbekannt'])} nicht in main: "
               f"{', '.join(stand['unbekannt'])})" if stand["unbekannt"] else "")
        )
    ursache = ""
    if dirty is True:
        ursache = (
            " — Ursache: ~/github/platform-pinned ist DIRTY, der Refresh wird "
            "uebersprungen (sichern/verwerfen, dann naechster Start refresht)"
        )
    elif dirty is False:
        ursache = " — Pin ist clean; Refresh lief, Auslieferung trotzdem abweichend"
    return (
        f"{len(stand['abweichend'])} von {stand['geprueft']} Policy-Datei(en) weichen "
        f"von origin/main ab: {', '.join(stand['abweichend'][:4])}"
        + (" …" if len(stand["abweichend"]) > 4 else "")
        + ursache
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kurz", action="store_true", help="eine Zeile fuer den Runner")
    ap.add_argument("--policies", default=str(STANDARD_POLICIES))
    ap.add_argument("--repo", default=str(STANDARD_REPO))
    ap.add_argument("--pin", default=str(PIN_WORKTREE))
    ap.add_argument("--ref", default="origin/main")
    args = ap.parse_args(argv)

    stand = vergleiche(Path(args.policies), Path(args.repo), args.ref)
    text = bericht(stand, pin_dirty(Path(args.pin)), args.kurz)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
