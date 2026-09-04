#!/usr/bin/env python3
"""Aufrufer-Concurrency je Ziel-Umgebung trennen (platform#2229).

## Warum

Am 2026-08-23 raeumte ein Handover-Push auf `main` einen sieben Minuten vorher
gestarteten Produktions-Dispatch von risk-hub ab. Beide Laeufe teilten sich die
Gruppe des **Aufrufers**::

    concurrency:
      group: deploy-<app>-${{ github.ref_name }}
      cancel-in-progress: true

Der Prod-Lauf endete als ``cancelled`` — weder gruen noch rot, in keinem Melder
ein Fehlschlag; Prod blieb zurueck, der Push deployte weiter nach Staging, und
die Lage sah gesund aus. Dieselbe Mechanik kostete tax-hub sieben Tage (#2148).

Die aufgerufene ``_deploy-unified.yml`` trennt ihre Jobs laengst korrekt
(``deploy-<app>-staging`` mit cancel-in-progress, ``deploy-<app>-production``
ohne). Die Trennung lief ins Leere, weil die aeussere Gruppe den ganzen Lauf
abbricht, bevor die innere greift.

## Was dieses Werkzeug NICHT tut

Es erfindet keine Gruppe, wo keine steht, und es fasst kein Repo an, dessen
Workflow gar kein ``target_environment`` kennt: dort waere der Ausdruck immer
``staging``, der Umbau also Zierrat ohne Wirkung. Beides wird als uebersprungen
mit Grund gemeldet, nicht stillschweigend ausgelassen.

Trockenlauf ist die Vorgabe; ``--apply`` schreibt.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

#: Der Ist-Zustand, wie er in 20 Repos steht — bewusst streng gematcht.
#: Ein loser Treffer wuerde eine schon umgebaute oder handgepflegte Gruppe
#: ueberschreiben, und das waere schlimmer als ein uebersprungenes Repo.
ALT = re.compile(
    r"^concurrency:\n"
    r"(?P<i>[ \t]+)group:[ \t]+(?P<g>deploy-[\w.-]+)-\$\{\{[ \t]*github\.ref_name[ \t]*\}\}\n"
    r"(?P=i)cancel-in-progress:[ \t]+true\n",
    re.M,
)

#: Ohne diese Eingabe ist der Umbau wirkungslos (s. Modul-Doku).
BRAUCHT = re.compile(r"^\s+target_environment:", re.M)

NEU = """concurrency:
{i}# Je ZIEL-UMGEBUNG, nicht je Branch (platform#2229): ein Staging-Push darf
{i}# einen laufenden Produktions-Deploy nicht abraeumen. Realfall 2026-08-23
{i}# bei risk-hub — der Prod-Lauf endete als `cancelled`, also weder gruen noch
{i}# rot, und fiel damit durch jeden Melder.
{i}#
{i}# `inputs.target_environment` ist bei `push` leer und faellt auf `staging`:
{i}# zwei Staging-Laeufe kuerzen sich weiterhin gegenseitig ab. Prod bekommt eine
{i}# eigene Gruppe und wird nicht abgebrochen — dieselbe Wahl, die
{i}# `_deploy-unified.yml` fuer ihren Produktions-Job trifft.
{i}group: {g}-${{{{ github.ref_name }}}}-${{{{ inputs.target_environment || 'staging' }}}}
{i}cancel-in-progress: ${{{{ (inputs.target_environment || 'staging') != 'production' }}}}
"""


#: Ein Repo ohne Gruppe kann seinen Prod-Lauf nicht ueber eine Gruppe verlieren.
KEINE_GRUPPE = re.compile(r"^concurrency:", re.M)
#: `cancel-in-progress: false` loest dasselbe Problem anders herum: Laeufe stauen
#: sich, statt sich abzuschiessen. Andere Abwaegung, kein Defekt — trading-hub
#: hat sie mit Begruendung getroffen (dortiges Issue #170).
NIE_ABBRECHEN = re.compile(
    r"^concurrency:\n[ \t]+group:[^\n]*\n(?:[ \t]*#[^\n]*\n)*[ \t]+cancel-in-progress:[ \t]+false",
    re.M,
)


def umbau(text: str) -> tuple[str, str]:
    """(neuer Text, Befund). Befund leer = umgebaut.

    Jeder Grund fuers Ueberspringen wird BENANNT. „Passt nicht" als
    Sammelantwort wuerde drei verschiedene Lagen verschmelzen — sichere,
    unbetroffene und tatsaechlich uebersehene Repos —, und genau daraus
    entstehen die Absence-Claims, die spaeter niemand nachpruefen kann.
    """
    m = ALT.search(text)
    if not m:
        if "-${{ inputs.target_environment" in text:
            return text, "bereits je Umgebung getrennt"
        if not KEINE_GRUPPE.search(text):
            return text, "keine Concurrency-Gruppe — nicht betroffen"
        if NIE_ABBRECHEN.search(text):
            return text, "cancel-in-progress: false — anders geloest, kein Defekt"
        return text, "Gruppe in unbekannter Form — von Hand ansehen"
    if not BRAUCHT.search(text):
        return text, "kein target_environment-Eingang — Umbau waere wirkungslos"
    ersatz = NEU.format(i=m.group("i"), g=m.group("g"))
    return text[: m.start()] + ersatz + text[m.end() :], ""


def repos(wurzel: Path) -> list[Path]:
    return sorted(
        p for p in wurzel.glob("*/.github/workflows/deploy.yml") if p.is_file()
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--wurzel", default=os.environ.get("GITHUB_DIR", str(Path.home() / "github"))
    )
    ap.add_argument("--repo", help="nur dieses Repo")
    ap.add_argument("--apply", action="store_true", help="schreiben statt nur zeigen")
    ap.add_argument(
        "--mit-ruhenden",
        action="store_true",
        help="auch eingefrorene/archivierte Repos umbauen (Vorgabe: nein)",
    )
    args = ap.parse_args(argv)

    #: Eingefrorene Repos bleiben unberuehrt — es gibt eine Hausregel, sie aus
    #: automatischen Warteschlangen herauszuhalten, und ein Repo, das nicht
    #: deployt, kann seinen Prod-Lauf auch nicht verlieren.
    ruhend: set[str] = set()
    if not args.mit_ruhenden:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from deploy_wirkung import repo_lifecycle

            ruhend = {
                n for n, lc in repo_lifecycle().items() if lc in ("archived", "frozen")
            }
        except Exception as exc:  # noqa: BLE001 — lieber ohne Filter als gar nicht
            print(
                f"HINWEIS: Lifecycle nicht lesbar ({exc}) — kein Ruhend-Filter",
                file=sys.stderr,
            )

    gefunden = repos(Path(args.wurzel))
    if not gefunden:
        print(
            f"FEHLER: keine deploy.yml unter {args.wurzel} — Zugriffs-, kein Befund",
            file=sys.stderr,
        )
        return 2

    umgebaut, uebersprungen = [], []
    for pfad in gefunden:
        name = pfad.parents[2].name
        if args.repo and name != args.repo:
            continue
        if name in ruhend:
            uebersprungen.append(
                (name, "ruhend (frozen/archived) — bewusst unberuehrt")
            )
            continue
        text = pfad.read_text(encoding="utf-8")
        neu, befund = umbau(text)
        if befund:
            uebersprungen.append((name, befund))
            continue
        umgebaut.append(name)
        if args.apply:
            pfad.write_text(neu, encoding="utf-8")

    print(
        f"# Aufrufer-Concurrency je Umgebung — {'ANGEWENDET' if args.apply else 'Trockenlauf'}\n"
    )
    print(f"umzubauen ({len(umgebaut)}): {', '.join(umgebaut) or '—'}\n")
    if uebersprungen:
        print(f"uebersprungen ({len(uebersprungen)}), je mit Grund:")
        for n, b in sorted(uebersprungen):
            print(f"  {n:22s} {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
