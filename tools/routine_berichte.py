#!/usr/bin/env python3
"""Berichte der Cloud-Routinen lesen — neue Funde und verstummte Routinen (#3887).

Anlass: Sechs Cloud-Routinen schreiben taeglich Issue-Kommentare (#1472, #1261, …),
gelesen hat sie keine Sitzung. Am 2026-10-13 meldete der Fleet-Drift-Report zwei
archivierte Repos, die die Registry noch als aktiv fuehrte — angekommen war das nur
als Push-Nachricht, in keinem Artefakt.

Welche Routine wohin schreibt, steht in `registry/routine-berichte.json`, nicht hier.
Je Routine wird gelesen:

* **neu** — ein Bericht juenger als `neu_stunden`, der einen Fund meldet. Er kommt
  als Link in die Zeile. Ob er neu fuer die Sitzung ist, entscheidet das
  Befund-Journal des Runners (gleiche Zeile = bekannt, Delta `NEU` beim ersten Mal);
  einen zweiten Gesehen-Speicher gibt es bewusst nicht.
* **still** — kein Bericht seit `still_stunden`, obwohl die Routine immer schreibt.

Netz: eine Abfrage je Label plus eine fuer alle Kommentare des Zeitfensters
(`issues/comments?since=`), keine Abfrage je Issue.

    python3 tools/routine_berichte.py                 # live ueber gh, eine Zeile
    python3 tools/routine_berichte.py --eingabe x.json --jetzt 2026-10-13T08:00:00+00:00

Exit: 0 nichts Neues, 1 neue Funde oder Routine still, 2 nicht pruefbar.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATEI = Path(__file__).resolve().parents[1] / "registry" / "routine-berichte.json"


def lade_konfig(pfad: Path = DATEI) -> dict:
    """Liest die Routinen-Liste; leer oder kaputt ist ein Fehler, kein Default."""
    konfig = json.loads(pfad.read_text(encoding="utf-8"))
    if (
        not konfig.get("repo")
        or not konfig.get("routinen")
        or not konfig.get("neu_stunden")
    ):
        raise ValueError(f"{pfad}: 'repo', 'neu_stunden' oder 'routinen' fehlt")
    return konfig


def _zeit(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def fenster_stunden(konfig: dict) -> int:
    """So weit zurueck muss gelesen werden, damit neu und still beide entscheidbar sind."""
    stunden = [konfig["neu_stunden"]] + [
        r.get("still_stunden") or 0 for r in konfig["routinen"]
    ]
    return max(stunden)


def _gh_json(args: list[str]) -> list:
    # `--jq '.[]'` gibt je Element eine kompakte JSON-Zeile aus — auch ueber
    # Seitengrenzen von --paginate hinweg, ohne Listen aneinanderzukleben.
    roh = subprocess.run(
        ["gh", *args, "--jq", ".[]"],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout
    return [json.loads(z) for z in roh.splitlines() if z.strip()]


def lade_live(konfig: dict, jetzt: datetime) -> dict:
    repo = konfig["repo"]
    seit = (jetzt - timedelta(hours=fenster_stunden(konfig))).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    issues: dict[str, list] = {}
    for r in konfig["routinen"]:
        label = (r.get("ausgang") or {}).get("label")
        if label and label not in issues:
            issues[label] = _gh_json(
                [
                    "api",
                    "-X",
                    "GET",
                    f"repos/{repo}/issues",
                    "-f",
                    "state=open",
                    "-f",
                    f"labels={label}",
                    "-f",
                    "per_page=100",
                ]
            )
    kommentare = _gh_json(
        [
            "api",
            "--paginate",
            "-X",
            "GET",
            f"repos/{repo}/issues/comments",
            "-f",
            f"since={seit}",
            "-f",
            "per_page=100",
        ]
    )
    return {"issues": issues, "kommentare": kommentare}


def _issue_nummer(kommentar: dict) -> int:
    return int(kommentar["issue_url"].rstrip("/").rsplit("/", 1)[1])


def berichte(routine: dict, daten: dict) -> tuple[list[int], list[dict]]:
    """Ausgangs-Issues und Berichte (Kommentare und neu angelegte Issues) einer Routine."""
    ausgang = routine.get("ausgang") or {}
    if "issue" in ausgang:
        nummern, angelegt = [int(ausgang["issue"])], []
    else:
        offen = daten["issues"].get(ausgang.get("label"), [])
        nummern, angelegt = [i["number"] for i in offen], offen
    kopf = re.compile(routine["kopf_muster"]) if routine.get("kopf_muster") else None
    liste = [
        {
            "zeit": _zeit(i["created_at"]),
            "body": i.get("body") or "",
            "url": i["html_url"],
        }
        for i in angelegt
    ]
    liste += [
        {
            "zeit": _zeit(k["created_at"]),
            "body": k.get("body") or "",
            "url": k["html_url"],
        }
        for k in daten["kommentare"]
        if _issue_nummer(k) in nummern
    ]
    if kopf:
        liste = [b for b in liste if kopf.search(b["body"].split("\n", 1)[0])]
    return nummern, sorted(liste, key=lambda b: b["zeit"])


def bewerte(konfig: dict, daten: dict, jetzt: datetime) -> tuple[int, str]:
    neu_grenze = jetzt - timedelta(hours=konfig["neu_stunden"])
    funde: list[str] = []
    still: list[str] = []
    gelesen = 0
    for r in konfig["routinen"]:
        if not r.get("ausgang"):
            continue
        gelesen += 1
        nummern, liste = berichte(r, daten)
        if r.get("still_stunden") and nummern:
            grenze = jetzt - timedelta(hours=r["still_stunden"])
            if not liste or liste[-1]["zeit"] < grenze:
                still.append(f"{r['name']} still seit >{r['still_stunden']} h")
        if not r.get("befund"):
            continue
        ruhe = re.compile(r["ruhe_muster"]) if r.get("ruhe_muster") else None
        frisch = [
            b
            for b in liste
            if b["zeit"] >= neu_grenze and not (ruhe and ruhe.search(b["body"]))
        ]
        if frisch:
            funde.append(
                f"{r['name']} → {frisch[-1]['url']}"
                + (f" (+{len(frisch) - 1})" if len(frisch) > 1 else "")
            )
    if not funde and not still:
        return (
            0,
            f"keine neuen Routine-Berichte ({gelesen} Routinen gelesen, Fenster {konfig['neu_stunden']} h)",
        )
    teile = []
    if funde:
        teile.append(f"{len(funde)} neue Routine-Berichte: " + "; ".join(funde))
    if still:
        teile.append("; ".join(still))
    return 1, " · ".join(teile)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--konfig", type=Path, default=DATEI, help=argparse.SUPPRESS)
    p.add_argument(
        "--eingabe",
        type=Path,
        help="JSON {issues: {label: [...]}, kommentare: [...]} statt gh (Tests)",
    )
    p.add_argument("--jetzt", help="ISO-Zeit statt der Uhr (Tests)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    jetzt = (
        datetime.fromisoformat(args.jetzt) if args.jetzt else datetime.now(timezone.utc)
    )
    try:
        konfig = lade_konfig(args.konfig)
        daten = (
            json.loads(args.eingabe.read_text(encoding="utf-8"))
            if args.eingabe
            else lade_live(konfig, jetzt)
        )
    except (OSError, subprocess.SubprocessError, ValueError) as fehler:
        print(f"nicht pruefbar: {type(fehler).__name__}: {str(fehler)[:160]}")
        return 2
    rc, zeile = bewerte(konfig, daten, jetzt)
    print(zeile)
    return rc


if __name__ == "__main__":
    sys.exit(main())
