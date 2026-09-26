#!/usr/bin/env python3
"""PreToolUse(Bash) gate — `git push` auf einen bereits gemergten PR-Branch.

GATE_HEADER (KONZ-038 D8):
  "slug": "push-to-merged-branch-silently-lost"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-24"
  "evidence": "tools/claude-hooks/tests/test_block_push_to_merged_branch.py"

Hintergrund (platform#2234, Memory
`feedback_push_auf_gemergten_branch_geht_verloren.md`): ein `git push` auf einen
Branch, dessen PR schon gemergt ist, meldet Erfolg und aendert NICHTS an `main` —
der Commit landet auf dem toten Branch. Drei Vorkommen: platform#3416→#3439
(2026-09-23, Cherry-pick nach Stunden gefunden), platform#3488→#3514
(2026-09-24, vier Stunden bis zum Fund) und cad-hub#81→#82 (2026-09-24, Minuten
spaeter). Kein Fehlerbild des Kommandos selbst — `git push` laeuft exit 0.

Verhalten:
  1. Kein `git push` (auch `git -C <pfad> push`) im Befehlstext → durchlassen,
     stumm.
  2. Repo-Verzeichnis (explizites `-C`, sonst letztes `cd`/`pushd` vor dem Push,
     sonst `cwd` der Sitzung) und Ziel-Branch (explizites Refspec, sonst
     aktueller Branch dort) werden bestimmt. Ist beides nicht bestimmbar, oder
     ist der Ziel-Branch der Default-Branch (`main`/`master`/...), oder liest
     sich die Remote-URL nicht als `owner/repo` auf github.com → ALLOW,
     eine Zeile stderr.
  3. Sonst: `gh pr list --repo <owner/repo> --head <branch> --state merged
     --json number --limit 1` (Timeout 8s). Treffer → DENY mit Hinweis auf
     Cherry-Pick in einen neuen Branch. Kein Treffer, `gh` fehlt, Netzfehler
     oder Timeout → ALLOW, eine Zeile stderr.

FAIL-OPEN durchgaengig, bewusst anders als `block_direct_pr_merge.py`: ein
`git push` ist reversibel (der Branch existiert weiter, ein Cherry-Pick holt
den Commit nach), ein blindes DENY bei jedem Werkzeugausfall waere teurer als
der seltene falsch-negative Fall.

GRENZEN (benannt statt behauptet):
  - Der Hook liest den BEFEHLSTEXT: ein `echo "git push ..."` oder ein Kommando
    in einer Datei wird ebenfalls ausgewertet (wie bei `block_bare_stash_pop.py`).
  - Nicht gefangen: Push ueber die REST-API, ein Skript, das `git push` intern
    per `subprocess`/Library ruft, oder ein Remote-Name ausserhalb von
    `github.com` (z.B. GitHub Enterprise) — die Remote-URL-Form wird bewusst
    eng gehalten, damit `owner/repo` nicht geraten wird.
  - Mehrdeutige Refspecs (Push-Optionen mit Leerzeichen-getrenntem Wert wie
    `--push-option <wert>`) koennen den Ziel-Branch falsch lesen; das ist
    FAIL-OPEN-seitig folgenlos (schlimmstenfalls ALLOW statt DENY).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "push-to-merged-branch-silently-lost"
GH_TIMEOUT = 8

_PUSH = re.compile(r"\bgit\s+(?:-C\s+(\"[^\"]+\"|'[^']+'|[^\s]+)\s+)?push\b(?!\.)")
_TRENNER = re.compile(r"&&|\|\||;|\n|\||\)")
_CD = re.compile(r"(?:^|[;&|(\s])(?:cd|pushd)\s+(\"[^\"]+\"|'[^']+'|[^\s;&|)]+)")
_REMOTE_URL = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?/?$"
)


def push_aufrufe(kommando: str) -> list[tuple[int, str | None, str]]:
    """(Startposition, -C-Pfad oder None, Argumenttext bis zum naechsten Trenner)
    je `git push` im Befehlstext."""
    aufrufe = []
    for treffer in _PUSH.finditer(kommando):
        c_pfad = treffer.group(1)
        if c_pfad:
            c_pfad = c_pfad.strip("\"'")
        rest = kommando[treffer.end() :]
        ende = _TRENNER.search(rest)
        aufrufe.append(
            (treffer.start(), c_pfad, rest[: ende.start()] if ende else rest)
        )
    return aufrufe


def verzeichnis(kommando: str, start: int, c_pfad: str | None, cwd: str) -> str:
    """`-C <pfad>` hat Vorrang, sonst das letzte `cd`/`pushd` vor dem Push,
    sonst das `cwd` der Sitzung — dieselbe Reihenfolge wie
    `block_unformatted_push.sh`."""
    ziel_dir = c_pfad
    if not ziel_dir:
        for treffer in _CD.finditer(kommando[:start]):
            ziel_dir = treffer.group(1).strip("\"'")
    if not ziel_dir:
        return cwd
    pfad = os.path.expanduser(ziel_dir)
    if not os.path.isabs(pfad):
        pfad = os.path.join(cwd, pfad)
    return pfad


def git_root(pfad: str) -> str | None:
    try:
        fertig = subprocess.run(
            ["git", "-C", pfad, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if fertig.returncode != 0:
        return None
    return fertig.stdout.strip() or None


def push_ziel(argumente: str) -> tuple[str | None, str | None]:
    """(Remote-Name oder None, Refspec oder None) aus den Argumenten eines
    `git push` — Optionen (alles ab `-`) werden ignoriert, nicht ausgewertet."""
    try:
        tokens = shlex.split(argumente)
    except ValueError:
        tokens = argumente.split()
    frei = [t for t in tokens if not t.startswith("-")]
    remote = frei[0] if frei else None
    refspec = frei[1] if len(frei) > 1 else None
    return remote, refspec


def aktueller_branch(root: str) -> str | None:
    try:
        fertig = subprocess.run(
            ["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    zweig = fertig.stdout.strip()
    if fertig.returncode != 0 or not zweig or zweig == "HEAD":
        return None
    return zweig


def default_branch(root: str, remote: str) -> str:
    try:
        fertig = subprocess.run(
            [
                "git",
                "-C",
                root,
                "symbolic-ref",
                "--short",
                f"refs/remotes/{remote}/HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        fertig = None
    if fertig and fertig.returncode == 0 and fertig.stdout.strip():
        return fertig.stdout.strip().split("/")[-1]
    return "main"


def ziel_branch(root: str, remote: str, refspec: str | None) -> str | None:
    """Ziel-Branch auf dem Remote — None, wenn nicht bestimmbar."""
    if refspec is None:
        return aktueller_branch(root)
    spec = refspec
    if ":" in spec:
        lokal, _, entfernt = spec.partition(":")
        spec = entfernt or lokal
    spec = spec.lstrip("+")
    if spec in ("", "HEAD"):
        return aktueller_branch(root)
    if spec.startswith("refs/heads/"):
        spec = spec[len("refs/heads/") :]
    return spec or None


def remote_repo(root: str, remote: str) -> str | None:
    try:
        fertig = subprocess.run(
            ["git", "-C", root, "remote", "get-url", remote],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if fertig.returncode != 0:
        return None
    treffer = _REMOTE_URL.match(fertig.stdout.strip())
    return treffer.group(1) if treffer else None


def gemergter_pr(repo: str, branch: str, root: str) -> tuple[int | None, str | None]:
    """(PR-Nummer oder None, Fehlertext oder None). Kein Treffer -> (None, None)."""
    befehl = [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--head",
        branch,
        "--state",
        "merged",
        "--json",
        "number",
        "--limit",
        "1",
    ]
    try:
        fertig = subprocess.run(
            befehl, capture_output=True, text=True, timeout=GH_TIMEOUT, cwd=root
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"`gh` nicht erreichbar ({type(exc).__name__})"
    if fertig.returncode != 0:
        return None, f"`gh pr list` scheiterte: {fertig.stderr.strip()[:160]}"
    try:
        daten = json.loads(fertig.stdout)
    except (json.JSONDecodeError, ValueError):
        return None, "Antwort von `gh pr list` unlesbar"
    if not daten:
        return None, None
    nr = daten[0].get("number")
    return (int(nr) if nr is not None else None), None


def entscheide(kommando: str, cwd: str) -> tuple[str | None, list[str]]:
    """(Grund fuer ein deny oder None, Liste von stderr-Hinweiszeilen)."""
    aufrufe = push_aufrufe(kommando)
    if not aufrufe:
        return None, []
    hinweise: list[str] = []
    for start, c_pfad, argumente in aufrufe:
        pfad = verzeichnis(kommando, start, c_pfad, cwd)
        root = git_root(pfad)
        if root is None:
            hinweise.append(
                f"{SLUG}: `{pfad}` kein git-Repo oder git nicht erreichbar — fail-open (allow)"
            )
            continue
        remote, refspec = push_ziel(argumente)
        remote = remote or "origin"
        branch = ziel_branch(root, remote, refspec)
        if not branch:
            hinweise.append(
                f"{SLUG}: Ziel-Branch von `git push{argumente}` nicht bestimmbar "
                "(z.B. detached HEAD) — fail-open (allow)"
            )
            continue
        default = default_branch(root, remote)
        if branch == default:
            hinweise.append(
                f"{SLUG}: Ziel-Branch `{branch}` ist der Default-Branch — allow"
            )
            continue
        repo = remote_repo(root, remote)
        if not repo:
            hinweise.append(
                f"{SLUG}: Remote `{remote}` liest sich nicht als github.com "
                f"owner/repo (Branch `{branch}`) — fail-open (allow)"
            )
            continue
        nr, fehler = gemergter_pr(repo, branch, root)
        if fehler:
            hinweise.append(
                f"{SLUG}: PR-Zustand fuer `{branch}` in {repo} nicht lesbar "
                f"({fehler}) — fail-open (allow)"
            )
            continue
        if nr is None:
            hinweise.append(
                f"{SLUG}: kein gemergter PR mit head `{branch}` in {repo} — allow"
            )
            continue
        return (
            f"PR #{nr} ({repo}) ist gemergt — dieser Push erreicht `{default}` "
            f"nicht mehr (Realfaelle platform#3488→#3514, cad-hub#81→#82). "
            f"Neuer Branch von origin/{default} + `git cherry-pick`, statt "
            f"weiter auf `{branch}` zu pushen.",
            hinweise,
        )
    return None, hinweise


def _deny(grund: str, kommando: str, session: str) -> None:
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG, "git push", beleg=kommando[:200], session=session, modus="blocking"
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"⛔ Push-Guard ({SLUG}, #2234): {grund}",
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not _PUSH.search(kommando):
        return 0
    session = str(daten.get("session_id") or "")
    try:
        grund, hinweise = entscheide(kommando, str(daten.get("cwd") or os.getcwd()))
    except Exception as exc:  # noqa: BLE001 — fail-open: ein Hook-Fehler blockt hier nichts
        print(
            f"{SLUG}: Hook-Fehler ({type(exc).__name__}) — fail-open (allow)",
            file=sys.stderr,
        )
        return 0
    for zeile in hinweise:
        print(zeile, file=sys.stderr)
    if grund is not None:
        _deny(grund, kommando, session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
