#!/usr/bin/env python3
"""Handover-Fragmente je Sitzung — render-on-read (KONZ-platform-027, #1944 K6).

Jede Sitzung schreibt genau EINE eigene Datei unter ``docs/handover.d/``.
Keine Sitzung editiert eine geteilte Region; der Stand wird beim Lesen aus
allen aktiven Fragmenten zusammengesetzt und nie committet (KONZ-027 L7).

Mini-Spec v1
------------
Dateiname  ``<YYYY-MM-DDTHH-MM-SSZ>-<session-id>.md`` (UTC).
Kopf       YAML-Frontmatter mit ``session_id``, ``erstellt`` (UTC, ISO-8601),
           ``titel``; optional ``ziel``.
Rumpf      drei Abschnitte, jeder darf fehlen:
             ``## Erledigt`` — Aufzählungspunkte
             ``## Offen``    — Aufzählungspunkte, jeder mit genau einer
                               GitHub-Issue/PR-URL (sonst Lint-Fehler)
             ``## Log``      — Prosa (ersetzt den Eintrag in AGENT_HANDOVER_LOG.md)
Unveränderlich: ein Fragment, das auf ``main`` liegt, wird nie mehr geändert
(L9). Korrektur = neues Fragment.

Aktiv (= im gerenderten Stand) ist ein Fragment, wenn es jünger als
``AKTIV_TAGE`` ist ODER mindestens einen Offen-Punkt hat, dessen Issue/PR
noch offen ist. Unbekannter Zustand zählt als offen — lieber einmal zu viel
zeigen als Arbeit still verlieren (L6).

Aufruf
------
  fragments.py neu --session-id ID --titel TEXT [--ziel TEXT]
  fragments.py render [--out PFAD] [--offline] [--heute YYYY-MM-DD]
  fragments.py pruefen [--basis origin/main]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

FRAGMENT_DIR = Path("docs/handover.d")
AKTIV_TAGE = 7
NAME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)-([A-Za-z0-9][A-Za-z0-9._-]*)\.md$"
)
URL_RE = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)/(issues|pull)/(\d+)")
PFLICHT_FELDER = ("session_id", "erstellt", "titel")
ABSCHNITTE = ("Erledigt", "Offen", "Log")

# Zustand eines Issues/PRs: "offen", "zu" oder "unbekannt".
ZustandLeser = Callable[[str, str, int], str]


@dataclass
class Fragment:
    pfad: Path
    kopf: dict
    abschnitte: dict = field(default_factory=dict)

    @property
    def erstellt(self) -> dt.datetime:
        return dt.datetime.fromisoformat(
            str(self.kopf["erstellt"]).replace("Z", "+00:00")
        )

    def punkte(self, abschnitt: str) -> list[str]:
        zeilen = self.abschnitte.get(abschnitt, "").splitlines()
        return [z[2:].strip() for z in zeilen if z.startswith(("- ", "* "))]


def _kopf_lesen(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    ende = text.find("\n---\n", 4)
    if ende < 0:
        return {}, text
    kopf = {}
    for zeile in text[4:ende].splitlines():
        if ":" in zeile and not zeile.startswith((" ", "#")):
            k, v = zeile.split(":", 1)
            kopf[k.strip()] = v.strip().strip('"')
    return kopf, text[ende + 5 :]


def lesen(pfad: Path) -> Fragment:
    kopf, rumpf = _kopf_lesen(pfad.read_text(encoding="utf-8"))
    abschnitte: dict[str, str] = {}
    aktuell = None
    for zeile in rumpf.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", zeile)
        if m:
            aktuell = m.group(1)
            abschnitte[aktuell] = ""
        elif aktuell is not None:
            abschnitte[aktuell] += zeile + "\n"
    return Fragment(pfad, kopf, {k: v.strip() for k, v in abschnitte.items()})


def alle(wurzel: Path) -> list[Fragment]:
    ordner = wurzel / FRAGMENT_DIR
    if not ordner.is_dir():
        return []
    return [lesen(p) for p in sorted(ordner.glob("*.md")) if NAME_RE.match(p.name)]


def fehler(fr: Fragment) -> list[str]:
    """Lint eines einzelnen Fragments; leere Liste = in Ordnung."""
    out = []
    m = NAME_RE.match(fr.pfad.name)
    if not m:
        out.append("Dateiname passt nicht zu <UTC-Zeitstempel>-<session-id>.md")
    for f in PFLICHT_FELDER:
        if not fr.kopf.get(f):
            out.append(f"Frontmatter-Feld fehlt: {f}")
    if (
        m
        and fr.kopf.get("session_id")
        and not m.group(2).startswith(fr.kopf["session_id"])
    ):
        out.append("session_id im Kopf passt nicht zum Dateinamen")
    try:
        fr.erstellt
    except (KeyError, ValueError):
        out.append("erstellt ist kein ISO-Zeitstempel")
    for name in fr.abschnitte:
        if name not in ABSCHNITTE:
            out.append(f"unbekannter Abschnitt: {name}")
    for p in fr.punkte("Offen"):
        if len(URL_RE.findall(p)) != 1:
            out.append(f"Offen-Punkt braucht genau eine Issue/PR-URL: {p[:60]}")
    return out


def gh_zustand(owner: str, repo: str, nummer: int) -> str:
    try:
        r = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/issues/{nummer}", "--jq", ".state"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unbekannt"
    state = r.stdout.strip()
    return (
        {"open": "offen", "closed": "zu"}.get(state, "unbekannt")
        if r.returncode == 0
        else "unbekannt"
    )


def offline_zustand(owner: str, repo: str, nummer: int) -> str:
    return "unbekannt"


def offene_punkte(fr: Fragment, zustand: ZustandLeser) -> list[tuple[str, str]]:
    """(Punkt, URL) aller Offen-Punkte, deren Issue/PR nicht nachweislich zu ist."""
    out = []
    for p in fr.punkte("Offen"):
        m = URL_RE.search(p)
        if m and zustand(m.group(1), m.group(2), int(m.group(4))) != "zu":
            out.append((p, m.group(0)))
    return out


def render(fragmente: list[Fragment], heute: dt.date, zustand: ZustandLeser) -> str:
    grenze = heute - dt.timedelta(days=AKTIV_TAGE)
    aktiv = []
    for fr in fragmente:
        offen = offene_punkte(fr, zustand)
        if fr.erstellt.date() > grenze or offen:
            aktiv.append((fr, offen))
    aktiv.sort(key=lambda t: (t[0].erstellt, t[0].pfad.name), reverse=True)

    neuestes = aktiv[0][0].pfad.name if aktiv else "—"
    zeilen = [
        "<!-- HANDOVER:NARRATIVE — beim Lesen gerendert (render-on-read), nie committen -->",
        f"_Gerendert {heute.isoformat()} · aktive Fragmente {len(aktiv)} von {len(fragmente)}"
        f" · neuestes {neuestes}_",
        "",
        "## Offene Fäden aus Sitzungen",
        "",
    ]
    gesehen = set()
    for fr, offen in aktiv:
        for punkt, url in offen:
            if url not in gesehen:
                gesehen.add(url)
                zeilen.append(f"- {punkt} _(Sitzung {fr.kopf.get('session_id')})_")
    if not gesehen:
        zeilen.append("- keine")
    for fr, _ in aktiv:
        k = fr.kopf
        zeilen += [
            "",
            f"## ⚡ Stand {fr.erstellt:%Y-%m-%d %H:%M} UTC — {k.get('titel')} (Sitzung {k.get('session_id')})",
            "",
        ]
        if k.get("ziel"):
            zeilen.append(f"**Ziel:** {k['ziel']}")
            zeilen.append("")
        for name in ABSCHNITTE:
            # Offen steht einmal gesammelt oben, nicht noch einmal je Sitzung.
            if name != "Offen" and fr.abschnitte.get(name):
                zeilen += [f"**{name}:**", "", fr.abschnitte[name], ""]
    return "\n".join(zeilen).rstrip() + "\n"


def neu(
    wurzel: Path, session_id: str, titel: str, ziel: Optional[str], jetzt: dt.datetime
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", session_id):
        raise ValueError("session-id darf nur Buchstaben, Ziffern, . _ - enthalten")
    ordner = wurzel / FRAGMENT_DIR
    ordner.mkdir(parents=True, exist_ok=True)
    stamm = f"{jetzt:%Y-%m-%dT%H-%M-%SZ}-{session_id}"
    pfad, n = ordner / f"{stamm}.md", 2
    while (
        pfad.exists()
    ):  # zweiter Schreibvorgang derselben Sitzung: Suffix, nie Overwrite (L9)
        pfad, n = ordner / f"{stamm}-{n}.md", n + 1
    kopf = [
        "---",
        f"session_id: {session_id}",
        f"erstellt: {jetzt:%Y-%m-%dT%H:%M:%SZ}",
        f"titel: {json.dumps(titel, ensure_ascii=False)}",
    ]
    if ziel:
        kopf.append(f"ziel: {json.dumps(ziel, ensure_ascii=False)}")
    kopf += ["---", "", "## Erledigt", "", "## Offen", "", "## Log", ""]
    pfad.write_text("\n".join(kopf), encoding="utf-8")
    return pfad


def geaenderte_bestandsfragmente(wurzel: Path, basis: str) -> list[str]:
    """Fragmente, die auf der Basis schon existieren und im Branch geändert wurden (L9)."""
    r = subprocess.run(
        [
            "git",
            "-C",
            str(wurzel),
            "diff",
            "--name-status",
            f"{basis}...HEAD",
            "--",
            str(FRAGMENT_DIR),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git diff fehlgeschlagen")
    out = []
    for zeile in r.stdout.splitlines():
        teile = zeile.split("\t")
        if teile and teile[0][:1] in ("M", "D", "R"):
            out.append(teile[-1] if teile[0][:1] != "R" else teile[1])
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--wurzel", default=".", type=Path)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("neu")
    a.add_argument("--session-id", required=True)
    a.add_argument("--titel", required=True)
    a.add_argument("--ziel")
    b = sub.add_parser("render")
    b.add_argument("--out", type=Path)
    b.add_argument("--offline", action="store_true")
    b.add_argument("--heute")
    c = sub.add_parser("pruefen")
    c.add_argument("--basis", default="origin/main")
    args = ap.parse_args(argv)

    if args.cmd == "neu":
        pfad = neu(
            args.wurzel,
            args.session_id,
            args.titel,
            args.ziel,
            dt.datetime.now(dt.timezone.utc),
        )
        print(pfad)
        return 0
    if args.cmd == "render":
        heute = (
            dt.date.fromisoformat(args.heute)
            if args.heute
            else dt.datetime.now(dt.timezone.utc).date()
        )
        text = render(
            alle(args.wurzel), heute, offline_zustand if args.offline else gh_zustand
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    rc = 0
    for fr in alle(args.wurzel):
        for f in fehler(fr):
            print(f"{fr.pfad.name}: {f}")
            rc = 1
    ordner = args.wurzel / FRAGMENT_DIR
    if ordner.is_dir():
        for p in ordner.glob("*.md"):
            if not NAME_RE.match(p.name) and p.name != "README.md":
                print(
                    f"{p.name}: Dateiname passt nicht zu <UTC-Zeitstempel>-<session-id>.md"
                )
                rc = 1
    try:
        for p in geaenderte_bestandsfragmente(args.wurzel, args.basis):
            print(
                f"{p}: Fragment liegt schon auf {args.basis} und ist unveraenderlich — neues Fragment anlegen"
            )
            rc = 1
    except RuntimeError as e:
        print(f"Unveraenderlichkeit nicht pruefbar: {e}")
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
