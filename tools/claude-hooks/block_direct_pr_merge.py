#!/usr/bin/env python3
"""PreToolUse(Bash) gate — `gh pr merge` nur über `pr_merge_sa.py` oder mit Owner-Wort.

GATE_HEADER (KONZ-038 D8):
  "slug": "direct-gh-pr-merge-bypasses-sa-m"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-23"
  "evidence": "tools/claude-hooks/tests/test_block_direct_pr_merge.py"

Hintergrund: drei Vorkommen über Retros (50d29a 2026-09-17, f1d54f F18
2026-09-21, 2c4009 #5 2026-09-23). Jedes Mal lief `gh pr merge` direkt aus der
Sitzung statt über `tools/pr_merge_sa.py` — ohne Zustandsprüfung, ohne Mandat,
ohne Journal. Realfälle: platform#3343 (Merge-Kommando 72 Min nach dem Owner-
Merge) und shared-ci#89 (`--admin` 3 Min nach dem Owner-Merge); dazu eine ganze
Bump-Welle per `gh pr merge --admin` in einer Schleife.

Verhalten:
  1. Kein `gh pr merge` im Befehlstext → durchlassen. `python3 tools/pr_merge_sa.py`
     enthält den Text nicht (es ruft `gh` per subprocess, am Hook vorbei) und
     ist der sanktionierte Weg.
  2. `gh pr merge` OHNE Marker `OWNER_WORT=<id>` → deny, Verweis auf
     `python3 tools/pr_merge_sa.py <nr> [owner/repo]`. Auch in Schleifen/Ketten.
  3. MIT Marker (`OWNER_WORT=69 gh pr merge …` oder `export OWNER_WORT=69 && …`):
     je Merge-Aufruf muss die PR-Nummer literal sein (Zahl oder PR-URL). Der Hook
     liest `gh pr view <nr> [-R repo] --json state,url` und lässt nur `OPEN`
     durch. Jeder Aufruf mit Marker (erlaubt oder nicht) bekommt eine Zeile im
     Journal von `pr_merge_sa.py` (`~/.claude/pr-merge-sa.jsonl`,
     `"quelle": "hook:owner-wort"`).

FAIL-CLOSED im Marker-Pfad, bewusst wie `pr_merge_sa.py` („Abwesenheit von Beweis
ist nie Beweis"): `gh` fehlt, Netz weg, Antwort unlesbar, PR-Nummer nicht literal
(Variable, Branch-Name, keine Angabe) → deny. Das kostet nichts: ohne erreichbares
`gh` scheitert der Merge ohnehin, und `pr_merge_sa.py` bleibt immer offen. Auch
ein unerwarteter Hook-Fehler endet in deny — gesperrt wird dabei nur der direkte
Merge, nie der sanktionierte Weg.

GRENZEN (benannt statt behauptet):
  - Der Hook liest den BEFEHLSTEXT: `grep "gh pr merge" datei` oder ein Commit-
    Text mit der Zeichenfolge wird ebenfalls geblockt (wie bei
    `block_bare_stash_pop.py`). Ausweg: Body/Message per Datei übergeben.
  - Nicht gefangen: Merge über die REST-API (`gh api …/merge`), über das
    GitHub-MCP-Werkzeug oder ein Skript, das `gh pr merge` intern ruft.
  - Der Marker belegt nicht, dass es das Owner-Wort gibt — er macht die Behauptung
    durabel (Journal) und prüfbar. Die Wahrheit prüft die Retro am Journal.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "direct-gh-pr-merge-bypasses-sa-m"
SA_WEG = "python3 tools/pr_merge_sa.py <nr> [owner/repo]"
GH_TIMEOUT = 10

_MERGE = re.compile(r"\bgh\s+pr\s+merge\b")
_MARKER = re.compile(
    r"(?<![\w$])(?:export\s+)?OWNER_WORT=(\"|')?([A-Za-z0-9][\w.:#/-]*)\1?(?=[\s;&|)]|$)"
)
_TRENNER = re.compile(r"&&|\|\||;|\n|\||\)")
_PR_URL = re.compile(r"^https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)/?$")
_CD = re.compile(r"(?:^|[;&|(\s])cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|)]+)")
#: Optionen von `gh pr merge`, die einen Wert tragen (ohne `=`: nächstes Token).
_WERT_OPTIONEN = {
    "-R",
    "--repo",
    "-b",
    "--body",
    "-F",
    "--body-file",
    "-t",
    "--subject",
    "-A",
    "--author-email",
    "--match-head-commit",
}


def journal_pfad() -> Path:
    """Dasselbe Journal wie `pr_merge_sa.JOURNAL` — eine Zählung, nicht zwei."""
    return Path.home() / ".claude" / "pr-merge-sa.jsonl"


def owner_wort(kommando: str) -> str | None:
    treffer = _MARKER.search(kommando)
    return treffer.group(2) if treffer else None


def merge_aufrufe(kommando: str) -> list[tuple[int, str]]:
    """(Startposition, Text bis zum nächsten Trenner) je `gh pr merge`."""
    aufrufe = []
    for treffer in _MERGE.finditer(kommando):
        rest = kommando[treffer.end() :]
        ende = _TRENNER.search(rest)
        aufrufe.append((treffer.start(), rest[: ende.start()] if ende else rest))
    return aufrufe


def ziel(argumente: str) -> tuple[str | None, str | None]:
    """(PR-Nummer, owner/repo) aus den Argumenten eines `gh pr merge` — None, wenn
    nicht literal bestimmbar."""
    try:
        tokens = shlex.split(argumente)
    except ValueError:
        tokens = argumente.split()
    repo = None
    auswahl = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("-"):
            name, gleich, wert = tok.partition("=")
            if name in ("-R", "--repo"):
                repo = (
                    wert if gleich else (tokens[i + 1] if i + 1 < len(tokens) else None)
                )
            if name in _WERT_OPTIONEN and not gleich:
                i += 1
        elif auswahl is None:
            auswahl = tok
        i += 1
    if repo is not None and not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        repo = None
    if auswahl is None:
        return None, repo
    if re.fullmatch(r"\d+", auswahl):
        return auswahl, repo
    url = _PR_URL.match(auswahl)
    if url:
        return url.group(2), repo or url.group(1)
    return None, repo


def arbeitsverzeichnis(kommando: str, start: int, cwd: str) -> str:
    """Letztes `cd <dir>` vor dem Merge, sonst das cwd der Sitzung."""
    ziel_dir = None
    for treffer in _CD.finditer(kommando[:start]):
        ziel_dir = treffer.group(1).strip("\"'")
    if ziel_dir:
        pfad = os.path.expanduser(ziel_dir)
        if not os.path.isabs(pfad):
            pfad = os.path.join(cwd, pfad)
        if os.path.isdir(pfad):
            return pfad
    return cwd


def pr_zustand(
    nr: str, repo: str | None, cwd: str
) -> tuple[str | None, str | None, str]:
    """(state, owner/repo, Fehler) — Fehler nicht leer heißt: unklar."""
    befehl = ["gh", "pr", "view", nr, "--json", "state,url"]
    if repo:
        befehl += ["-R", repo]
    try:
        fertig = subprocess.run(
            befehl, capture_output=True, text=True, timeout=GH_TIMEOUT, cwd=cwd
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, repo, f"`gh` nicht erreichbar ({type(exc).__name__})"
    if fertig.returncode != 0:
        return (
            None,
            repo,
            f"`gh pr view {nr}` scheiterte: {fertig.stderr.strip()[:160]}",
        )
    try:
        daten = json.loads(fertig.stdout)
    except (json.JSONDecodeError, ValueError):
        return None, repo, "Antwort von `gh pr view` unlesbar"
    state = daten.get("state")
    url = _PR_URL.match(str(daten.get("url") or ""))
    return state, repo or (url.group(1) if url else None), "" if state else "kein state"


def journal(zeile: dict) -> None:
    try:
        pfad = journal_pfad()
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("a") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass  # ein blindes Journal verhindert nichts — das Urteil steht schon


def entscheide(kommando: str, cwd: str, session: str = "") -> str | None:
    """Grund für ein deny oder None (durchlassen)."""
    aufrufe = merge_aufrufe(kommando)
    if not aufrufe:
        return None
    wort = owner_wort(kommando)
    if wort is None:
        return (
            "`gh pr merge` direkt aus der Sitzung umgeht SA-M (Zustand, Mandat, Journal). "
            f"Sanktionierter Weg: `{SA_WEG}`. Liegt ein Owner-Wort für GENAU diesen "
            "Merge vor, den Marker voranstellen: `OWNER_WORT=<id> gh pr merge <nr> -R "
            "<owner/repo> …` — dann prüft der Hook den PR-Zustand und schreibt ins Journal."
        )
    grund = None
    for start, argumente in aufrufe:
        nr, repo = ziel(argumente)
        zeit = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if nr is None:
            grund = (
                "Owner-Wort-Pfad verlangt je `gh pr merge` eine LITERALE PR-Nummer (Zahl "
                "oder PR-URL) — Schleifen über Variablen, Branch-Namen oder die "
                "implizite Aktuell-Branch-Auswahl sind nicht vorprüfbar (fail-closed). "
                f"Je PR einzeln aufrufen oder `{SA_WEG}`."
            )
            state, repo_echt = None, repo
        else:
            state, repo_echt, fehler = pr_zustand(
                nr, repo, arbeitsverzeichnis(kommando, start, cwd)
            )
            if fehler:
                grund = (
                    f"PR-Zustand von #{nr} nicht lesbar ({fehler}) — ohne gelesenen "
                    f"Zustand kein direkter Merge (fail-closed wie pr_merge_sa.py). `{SA_WEG}`."
                )
            elif state != "OPEN":
                grund = (
                    f"PR #{nr} ({repo_echt or '?'}) ist {state}, nicht OPEN — ein Merge-"
                    "Kommando darauf ist blind (Realfall platform#3343: 72 Min nach dem "
                    "Owner-Merge). Erst den Live-Zustand lesen, nicht nachmergen."
                )
        journal(
            {
                "ts": zeit,
                "quelle": "hook:owner-wort",
                "repo": repo_echt,
                "pr": int(nr) if nr else None,
                "owner_wort": wort,
                "state": state,
                "erlaubt": grund is None,
                "grund": grund or "Owner-Wort-Marker, Zustand OPEN",
                "session": session,
            }
        )
        if grund:
            return grund
    return None


def _deny(grund: str, kommando: str, session: str) -> None:
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG, "gh pr merge", beleg=kommando[:200], session=session, modus="blocking"
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"⛔ Merge-Guard (SA-M, #2234): {grund}",
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not _MERGE.search(kommando):
        return 0
    session = str(daten.get("session_id") or "")
    try:
        grund = entscheide(kommando, str(daten.get("cwd") or os.getcwd()), session)
    except Exception as exc:  # noqa: BLE001 — fail-closed: nur der direkte Merge ist zu
        grund = f"Hook-Fehler ({type(exc).__name__}) — fail-closed. `{SA_WEG}`."
    if grund is not None:
        _deny(grund, kommando, session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
