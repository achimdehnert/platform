#!/usr/bin/env python3
"""sitzungs_branches.py — welche Branches gehoeren zu EINER Claude-Sitzung?

WARUM (platform#2234, Retro platform#3543 Befunde #2 und #4)
-----------------------------------------------------------
Zwei Gates am Sitzungsende fielen am 2026-09-24 zurueck, und beide aus
demselben Grund: kein Werkzeug konnte die PRs einer Sitzung von denen
paralleler Sitzungen desselben GitHub-Kontos trennen.

- E.10 (`issue-offen-nach-gemergtem-fix`): `session_abgleich.py` holt alle PRs
  des Kontos seit heute. Der Live-Lauf ergab `RESULT: BEFUND 35`; die Runner-
  Zelle zeigte davon genau eine abgeschnittene Zeile. Das eigene offene Issue
  #3469 (aus #3489, `Refs #3469`) blieb unsichtbar.
- E.3 (`handover-stale-vor-merge`): im Fragment-Modus wurde E.3 gruen, sobald
  irgendein eigenes Fragment auf main lag. Sitzung e911bf49 schrieb ihr Fragment
  13:01Z und arbeitete danach drei Stunden weiter, ohne neues Fragment.

Die Leases von `repo-session.sh` tragen `session_id` — das ist die LEASE-ID, nicht
die Claude-Sitzung. Seit platform#2234 schreibt `start` zusaetzlich
`claude_session` = $CLAUDE_CODE_SESSION_ID. Dieses Modul liest aktive,
geschlossene (`.json.closed`) und archivierte Leases (`leases-archive/`) und
ordnet sie ueber die ersten acht Zeichen der Claude-Sitzungs-ID zu — dieselbe
Kurzform, die Handover-Fragmente im Dateinamen tragen.

WAS ES NICHT SIEHT
------------------
- Arbeit ohne Lease (direkt im Haupt-Tree) hat keinen Branch in dieser Liste.
- Alt-Leases ohne `claude_session` sind NICHT ZUORDENBAR. Sie werden gezaehlt
  und genannt, nie still ausgeschlossen: ergibt die Zuordnung keinen einzigen
  Branch, ist das Ergebnis "nicht zuordenbar", nicht "sauber".

Aufrufe:
  sitzungs_branches.py branches --sitzung <id> [--lease-dir DIR]
      JSON: branches, repos, paare, ohne_feld, grund.
  sitzungs_branches.py nachlauf --sitzung <id> --owner O --fragment-zeit ISO
                                [--fragment-muster RE] [--lease-dir DIR] [--eingabe F]
      PRs der Sitzungs-Branches, die NACH dem juengsten eigenen Fragment angelegt
      wurden (E.3). Je (Repo, Branch) EIN `gh pr list --head` — genau, ohne
      Deckel auf die Trefferzahl. RESULT: NACHLAUF n | OK | NICHT_ZUORDENBAR | FEHLER.
      Exit 0 = OK/nicht zuordenbar · 1 = Nachlauf · 2 = Werkzeugfehler.

stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Kurzform der Claude-Sitzungs-ID — so steht sie in Fragment-Dateinamen und
# im `--session-id` des Ende-Runners.
PRAEFIX_LAENGE = 8
ARCHIV_NAME = "leases-archive"
LEASE_MUSTER = ("*.json", "*.json.closed")
PR_FELDER = "number,headRefName,state,createdAt,mergedAt,files"


def standard_lease_dir() -> Path:
    if os.environ.get("LEASE_DIR"):
        return Path(os.environ["LEASE_DIR"])
    root = os.environ.get("REPO_SESSION_DIR") or str(Path.home() / ".repo-session")
    return Path(root) / "leases"


# ─────────────────────────────── rein ───────────────────────────────────────


def sitzungs_schluessel(sitzung: str | None) -> str | None:
    """Die ersten acht Zeichen, klein; None, wenn die ID dafuer zu kurz ist."""
    s = (sitzung or "").strip().lower()
    return s[:PRAEFIX_LAENGE] if len(s) >= PRAEFIX_LAENGE else None


def zuordnen(leases: list[dict], sitzung: str | None) -> dict:
    """Leases → Branches/Repos der Sitzung. Rein ueber einer Liste von Lease-dicts."""
    schluessel = sitzungs_schluessel(sitzung)
    ohne_feld = 0
    paare: set[tuple[str, str]] = set()
    for lease in leases:
        cs = str(lease.get("claude_session") or "").strip().lower()
        if not cs:
            ohne_feld += 1
            continue
        if schluessel and cs[:PRAEFIX_LAENGE] == schluessel:
            branch = str(lease.get("branch") or "")
            if branch:
                paare.add((str(lease.get("repo") or ""), branch))
    grund = None
    if schluessel is None:
        grund = f"Sitzungs-ID '{sitzung or ''}' kuerzer als {PRAEFIX_LAENGE} Zeichen"
    elif not paare:
        grund = (
            f"kein Lease traegt claude_session={schluessel}… "
            f"({ohne_feld} Alt-Lease(s) ohne Feld, nicht zuordenbar)"
        )
    return {
        "sitzung": sitzung or "",
        "schluessel": schluessel or "",
        "paare": sorted(paare),
        "branches": sorted({b for _, b in paare}),
        "repos": sorted({r for r, _ in paare if r}),
        "ohne_feld": ohne_feld,
        "grund": grund,
    }


def _zeit(wert) -> datetime | None:
    if not wert:
        return None
    try:
        return datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except ValueError:
        return None


def prs_nach_fragment(
    prs: list[dict],
    branches: list[str] | set[str],
    fragment_zeit: str,
    fragment_muster: str | None = None,
) -> list[dict]:
    """PRs der Sitzungs-Branches, die NACH dem juengsten eigenen Fragment angelegt wurden.

    Massgeblich ist `createdAt`, nicht `mergedAt`: ein PR, der vor dem Fragment
    angelegt und danach gemergt wurde, ist dem Fragment bekannt. Ein PR, der das
    eigene Fragment selbst traegt, zaehlt nie. Unbekanntes `createdAt` zaehlt als
    Nachlauf — ein Datum, das fehlt, ist keine Entwarnung.
    """
    grenze = _zeit(fragment_zeit)
    if grenze is None:
        raise ValueError(f"fragment_zeit ist kein ISO-Zeitstempel: {fragment_zeit!r}")
    muster = re.compile(fragment_muster) if fragment_muster else None
    erlaubt = set(branches)
    treffer = []
    for pr in prs or []:
        if str(pr.get("headRefName") or "") not in erlaubt:
            continue
        pfade = [str(f.get("path") or "") for f in pr.get("files") or []]
        if muster and any(muster.search(p) for p in pfade):
            continue
        angelegt = _zeit(pr.get("createdAt"))
        if angelegt is None or angelegt > grenze:
            treffer.append(pr)
    return treffer


# ───────────────────────────── Datei/gh ─────────────────────────────────────


def lade_leases(lease_dir: Path) -> list[dict]:
    """Aktive + geschlossene Leases in `lease_dir`, dazu alles unter `leases-archive/`."""
    dateien: list[Path] = []
    if lease_dir.is_dir():
        for m in LEASE_MUSTER:
            dateien += sorted(lease_dir.glob(m))
    archiv = lease_dir.parent / ARCHIV_NAME
    if archiv.is_dir():
        for m in LEASE_MUSTER:
            dateien += sorted(archiv.rglob(m))
    leases = []
    for pfad in dateien:
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(daten, dict):
            leases.append(daten)
    return leases


class GhFehler(RuntimeError):
    pass


def gh_prs_des_branches(repo_voll: str, branch: str) -> list[dict]:
    try:
        lauf = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo_voll,
                "--head",
                branch,
                "--state",
                "all",
                "--limit",
                "50",
                "--json",
                PR_FELDER,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GhFehler(f"gh pr list {repo_voll}: {exc}") from exc
    if lauf.returncode != 0:
        raise GhFehler(
            f"gh pr list {repo_voll} rc={lauf.returncode}: {lauf.stderr.strip()[:120]}"
        )
    try:
        daten = json.loads(lauf.stdout or "[]")
    except ValueError as exc:
        raise GhFehler(f"gh pr list {repo_voll} lieferte kein JSON") from exc
    for pr in daten:
        pr["repo"] = repo_voll
    return daten


# ──────────────────────────────── CLI ───────────────────────────────────────


def _lauf_nachlauf(args, zuordnung: dict) -> int:
    if zuordnung["grund"]:
        print(f"RESULT: NICHT_ZUORDENBAR {zuordnung['grund']}")
        return 0
    prs: list[dict] = []
    fehler: list[str] = []
    if args.eingabe:
        try:
            roh = json.loads(Path(args.eingabe).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"RESULT: FEHLER Eingabe nicht lesbar: {exc}")
            return 2
        for repo, liste in (roh or {}).items():
            for pr in liste:
                pr.setdefault("repo", repo)
                prs.append(pr)
    else:
        for repo, branch in zuordnung["paare"]:
            repo_voll = f"{args.owner}/{repo}"
            try:
                prs += gh_prs_des_branches(repo_voll, branch)
            except GhFehler as exc:
                fehler.append(str(exc))
    try:
        treffer = prs_nach_fragment(
            prs, zuordnung["branches"], args.fragment_zeit, args.fragment_muster
        )
    except (ValueError, re.error) as exc:
        print(f"RESULT: FEHLER {exc}")
        return 2
    for pr in treffer:
        zustand = str(pr.get("state") or "?").upper()
        print(
            f"   ⚠ {pr.get('repo', '?')}#{pr.get('number')} {zustand} "
            f"angelegt {pr.get('createdAt') or '?'} (Branch {pr.get('headRefName')})"
        )
    for f in fehler:
        print(f"   ◌ nicht abrufbar: {f}")
    if treffer:
        refs = " ".join(
            f"{str(p.get('repo', '')).split('/')[-1]}#{p.get('number')}"
            for p in treffer
        )
        print(f"RESULT: NACHLAUF {len(treffer)} {refs}")
        return 1
    if fehler:
        print(f"RESULT: FEHLER {len(fehler)} Abruf(e) gescheitert — keine Entwarnung")
        return 2
    print(
        f"RESULT: OK {len(zuordnung['branches'])} Branch(es) ohne PR nach dem Fragment"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Branches einer Claude-Sitzung aus den Leases"
    )
    unter = ap.add_subparsers(dest="befehl", required=True)
    for name in ("branches", "nachlauf"):
        p = unter.add_parser(name)
        p.add_argument(
            "--sitzung", required=True, help="Claude-Sitzungs-ID (>= 8 Zeichen)"
        )
        p.add_argument(
            "--lease-dir",
            default=None,
            help="Default: $LEASE_DIR bzw. ~/.repo-session/leases",
        )
    nl = unter.choices["nachlauf"]
    nl.add_argument("--owner", default="", help="GitHub-Owner der Lease-Repos")
    nl.add_argument(
        "--fragment-zeit",
        required=True,
        help="erstellt: des juengsten eigenen Fragments (ISO)",
    )
    nl.add_argument(
        "--fragment-muster", default=None, help="Regex auf Pfade eigener Fragmente"
    )
    nl.add_argument("--eingabe", default=None, help="JSON {repo: [prs]} statt gh-Abruf")
    args = ap.parse_args(argv)

    lease_dir = Path(args.lease_dir) if args.lease_dir else standard_lease_dir()
    zuordnung = zuordnen(lade_leases(lease_dir), args.sitzung)
    if args.befehl == "branches":
        print(json.dumps(zuordnung, ensure_ascii=False))
        return 0
    return _lauf_nachlauf(args, zuordnung)


if __name__ == "__main__":
    sys.exit(main())
