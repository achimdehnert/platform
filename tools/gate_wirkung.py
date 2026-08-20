#!/usr/bin/env python3
"""gate_wirkung.py — Rueckfall-Mass fuer gebaute Gates (Session-Loop, KONZ-platform-010).

## Warum es das gibt

Der Retro-Loop hatte bis hierhin drei Messpunkte und eine Luecke:

- `docs/governance/gate-registry.json` sagt, ein Gate ist **gebaut**.
- `tools/gate_drill_check.py` sagt, es **feuert** (Drill gruen).
- `tools/retro_kpis.py` zaehlt, wie oft ein Slug **insgesamt** wiederkehrt.

Keiner davon beantwortet die Frage, an der sich entscheidet, ob der Loop besser
wird: **wie oft ist der Befund aufgetreten, NACHDEM sein Gate gebaut war?**

Ohne diese Trennung ist ein Gate mit 16 Rueckfaellen seit dem Bau in jeder
Anzeige ununterscheidbar von einem, das gestern gebaut wurde und noch nie
gebraucht wurde. Genau das war der Zustand am 2026-08-20: `claim-before-cheapest-check`
stand bei ×47 Gesamt-Vorkommen, das blockierende Stop-Hook-Gate war seit
2026-08-02 gebaut, verdrahtet (`~/.claude/settings.json`, Stop-Event) und der
Drill gruen — und der Slug kehrte danach **16 weitere Male** wieder, zuletzt am
Tag dieser Messung. Der Retro-Report buchte ihn jedes Mal als N-te Wiederholung
desselben Befunds statt als Befund **ueber das Gate**.

Die Konsequenz ist keine Zahl, sondern eine Klasse: ein rueckfaelliges Gate
braucht Umbau, Ausweitung oder eine ehrliche Herabstufung — nicht das
N+1-te Memo mit demselben Slug.

## Ehrlichkeits-Sperre (bewusst, nicht optional)

Ein frisch gebautes Gate mit null Rueckfaellen ist **nicht** wirksam, sondern
ungeprueft. Wer das verwechselt, misst die Bauzeit statt die Wirkung und bekommt
eine Kennzahl, die durch blosses Neubauen steigt (Goodhart). Deshalb gilt jedes
Gate, hinter dessen Bau-Datum weniger als `MIN_FENSTER` Retros liegen, als
**zu frueh** — nicht als wirksam. Die Sperre ist der Grund, warum dieses Werkzeug
Retros zaehlt und nicht Tage: ein ruhiger Monat ohne Sitzungen ist keine Evidenz.

## Aufruf

    python3 tools/gate_wirkung.py            # voller Report
    python3 tools/gate_wirkung.py --kurz     # eine Zeile fuer den Session-Start-Runner
                                             #   (leere Ausgabe = kein Rueckfall)
    python3 tools/gate_wirkung.py --json     # maschinenlesbar
    python3 tools/gate_wirkung.py --dir <p>  # Retro-Verzeichnis(se) ueberschreiben

Exit-Code 0 immer — Report-Werkzeug, kein Enforcer (Hausform wie `retro_kpis.py`
und `gate_drill_check.py`). Das Urteil steht im Text; erzwungen wird es dort, wo
es hingehoert: im Retro-Skill als eigene Befund-Klasse.

stdlib-only, damit es in jeder Retro-Phase und im Runner ohne Setup laeuft.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

# Maschinenlesbarer Kopf (KONZ-038 D8) — steht im Modul, nicht nur in der Registry,
# damit `gate_drill_check.py` ihn gegen die Registry pruefen kann.
GATE_HEADER = {
    "slug": "gate-rueckfall-unbemerkt",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-20",
    "evidence": "tools/tests/test_gate_wirkung.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")

# Mindestzahl Retros NACH dem Bau-Datum, bevor ueber ein Gate geurteilt wird.
# 3 ist bewusst niedrig: es geht um den Unterschied "hatte ueberhaupt Gelegenheit"
# gegen "hatte keine", nicht um statistische Signifikanz.
MIN_FENSTER = 3

# Ab so vielen Rueckfaellen gilt ein Gate als rueckfaellig. 2 statt 1, weil ein
# einzelner Rueckfall auch der Lauf sein kann, in dem das Gate gebaut WURDE.
RUECKFALL_SCHWELLE = 2

_DATUM_AUS_NAME = re.compile(r"session-retro-(\d{4}-\d{2}-\d{2})-")
_INLINE = re.compile(r"^recurring_findings\s*:\s*\[(.*?)\]", re.S | re.M)
_BLOCK_START = re.compile(r"^recurring_findings\s*:\s*$")
_LISTEN_EINTRAG = re.compile(r"^\s*-\s*([a-z0-9][a-z0-9-]*)\s*$")


def standard_verzeichnisse() -> list[str]:
    """docs/retros/ (git-durabel) + ~/shared/ (Schreibpfad des Skills) — wie retro_kpis."""
    return [
        os.path.join(REPO_ROOT, "docs", "retros"),
        os.path.join(os.path.expanduser("~"), "shared"),
    ]


def lies_retros(verzeichnisse: list[str]) -> list[tuple[str, list[str], str]]:
    """(datum, slugs, dateiname) je Retro. Dedupliziert nach Dateiname.

    `-extern-`-Briefings sind Handoffs an fremde LLMs, keine Retros — sie tragen
    keine eigenen Befunde und wuerden sonst doppelt zaehlen.
    """
    gesehen: dict[str, tuple[str, list[str], str]] = {}
    for verzeichnis in verzeichnisse:
        for pfad in sorted(glob.glob(os.path.join(verzeichnis, "session-retro-*.md"))):
            name = os.path.basename(pfad)
            if "-extern-" in name or name in gesehen:
                continue
            treffer = _DATUM_AUS_NAME.match(name)
            if not treffer:
                continue
            try:
                text = open(pfad, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            gesehen[name] = (treffer.group(1), _slugs_aus_frontmatter(text), name)
    return sorted(gesehen.values())


def _slugs_aus_frontmatter(text: str) -> list[str]:
    """`recurring_findings` als Inline-Liste ODER als YAML-Block — beide Formen kommen vor."""
    if not text.startswith("---"):
        return []
    teile = text.split("---", 2)
    if len(teile) < 3:
        return []
    frontmatter = teile[1]

    inline = _INLINE.search(frontmatter)
    if inline:
        roh = inline.group(1).replace("\n", " ")
        return [s.strip() for s in roh.split(",") if s.strip()]

    slugs: list[str] = []
    im_block = False
    for zeile in frontmatter.splitlines():
        if _BLOCK_START.match(zeile):
            im_block = True
            continue
        if im_block:
            eintrag = _LISTEN_EINTRAG.match(zeile)
            if eintrag:
                slugs.append(eintrag.group(1))
            else:
                im_block = False
    return slugs


def bewerte(gates: list[dict], retros: list[tuple[str, list[str], str]]) -> list[dict]:
    """Je Gate: Vorkommen vor/nach Bau-Datum + Urteil.

    `vorher_messbar` ist der zweite Ehrlichkeits-Marker: liegt das Bau-Datum vor
    dem aeltesten vorliegenden Retro, dann ist "vorher = 0" kein Messwert, sondern
    das Ende des Datenfensters. Ohne diesen Marker liest sich ein Gate von 2026-06-01
    wie eines, das nie gebraucht wurde — obwohl der Zeitraum davor schlicht fehlt.
    """
    aeltestes = min((d for d, _, _ in retros), default="")
    ergebnis = []
    for gate in gates:
        slug = gate.get("slug", "")
        gebaut = gate.get("built") or ""
        vorkommen = sorted(d for d, slugs, _ in retros if slug in slugs)
        vorher = [d for d in vorkommen if gebaut and d < gebaut]
        nachher = [d for d in vorkommen if gebaut and d >= gebaut]
        fenster = len({d for d, _, _ in retros if gebaut and d >= gebaut})
        vorher_messbar = bool(gebaut) and bool(aeltestes) and gebaut > aeltestes

        if not gebaut:
            urteil = "ohne-datum"
        elif len(nachher) >= RUECKFALL_SCHWELLE:
            urteil = "RUECKFAELLIG"
        elif fenster < MIN_FENSTER:
            urteil = "zu-frueh"
        elif nachher:
            urteil = "beobachten"
        elif vorher:
            urteil = "wirksam"
        elif not vorher_messbar:
            # Kein Rueckfall, aber auch kein Vorher-Zeitraum in den Daten: darueber
            # laesst sich nichts sagen, und "unerprobt" waere schon zu viel Aussage.
            urteil = "kein-vorher-fenster"
        else:
            urteil = "unerprobt"

        ergebnis.append(
            {
                "slug": slug,
                "modus": gate.get("mode", "?"),
                "modul": gate.get("module"),
                "gebaut": gebaut,
                "ref": gate.get("ref"),
                "vorher": len(vorher),
                "vorher_messbar": vorher_messbar,
                "nachher": len(nachher),
                "letzter_rueckfall": nachher[-1] if nachher else None,
                "fenster_retros": fenster,
                "urteil": urteil,
            }
        )
    # Rueckfaellige zuerst, danach nach Zahl der Rueckfaelle.
    rang = {
        "RUECKFAELLIG": 0,
        "beobachten": 1,
        "zu-frueh": 2,
        "kein-vorher-fenster": 3,
        "unerprobt": 4,
        "wirksam": 5,
    }
    ergebnis.sort(key=lambda e: (rang.get(e["urteil"], 9), -e["nachher"], e["slug"]))
    return ergebnis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--dir", action="append", dest="dirs")
    parser.add_argument("--kurz", action="store_true", help="eine Zeile fuer den Runner")
    parser.add_argument("--json", action="store_true", dest="als_json")
    args = parser.parse_args()

    try:
        registry = json.load(open(args.registry, encoding="utf-8"))
        gates = registry.get("gates", [])
    except (OSError, ValueError) as fehler:
        # Fail-open: ein Melder, der den Sitzungsstart aufhaelt, wird abgeschaltet
        # und meldet danach gar nichts mehr.
        if not args.kurz:
            print(f"Registry nicht lesbar ({fehler}) — kein Urteil.", file=sys.stderr)
        return 0

    retros = lies_retros(args.dirs or standard_verzeichnisse())
    bewertet = bewerte(gates, retros)
    rueckfaellig = [e for e in bewertet if e["urteil"] == "RUECKFAELLIG"]

    if args.als_json:
        print(json.dumps({"retros": len(retros), "gates": bewertet}, ensure_ascii=False, indent=2))
        return 0

    if args.kurz:
        if rueckfaellig:
            spitze = rueckfaellig[0]
            weitere = f" (+{len(rueckfaellig) - 1} weitere)" if len(rueckfaellig) > 1 else ""
            print(
                f"{len(rueckfaellig)} Gate(s) rueckfaellig — "
                f"{spitze['slug']}: {spitze['nachher']}x seit Bau {spitze['gebaut']}, "
                f"zuletzt {spitze['letzter_rueckfall']}{weitere}"
            )
            for eintrag in rueckfaellig[1:]:
                print(
                    f"  · {eintrag['slug']} — {eintrag['nachher']}x seit {eintrag['gebaut']}, "
                    f"zuletzt {eintrag['letzter_rueckfall']}"
                )
        return 0

    daten = [d for d, _, _ in retros]
    spanne = f"{daten[0]} .. {daten[-1]}" if daten else "keine"
    print(f"# Gate-Wirkung ueber {len(retros)} Retro-Reports ({spanne})\n")
    kopf = f"{'slug':<46}{'gebaut':<12}{'modus':<10}{'vor':>4}{'NACH':>6}  {'urteil':<19}letzter Rueckfall"
    print(kopf)
    print("-" * len(kopf))
    for e in bewertet:
        marke = "🚨" if e["urteil"] == "RUECKFAELLIG" else "  "
        vor = f"{e['vorher']}" + ("" if e["vorher_messbar"] else "*")
        print(
            f"{marke}{e['slug']:<44}{e['gebaut']:<12}{e['modus']:<10}"
            f"{vor:>4}{e['nachher']:>6}  {e['urteil']:<19}{e['letzter_rueckfall'] or '—'}"
        )

    print()
    if rueckfaellig:
        print(
            f"→ {len(rueckfaellig)} Gate(s) RUECKFAELLIG: der Befund kam nach dem Bau des Gates "
            f"mindestens {RUECKFALL_SCHWELLE}x wieder."
        )
        print(
            "  Das ist ein Befund UEBER das Gate, nicht die N-te Wiederholung des Slugs. "
            "Drei ehrliche Antworten: Gate ausweiten (es sieht die Familie nicht), "
            "Gate umbauen (es feuert zu spaet), oder Modus herabstufen und in der "
            "declined-Liste begruenden."
        )
    else:
        print("→ Kein Gate rueckfaellig.")

    ohne_vorher = [e for e in bewertet if not e["vorher_messbar"]]
    if ohne_vorher:
        print(
            f"  (* {len(ohne_vorher)} Gate(s) aelter als das aelteste Retro — deren "
            "'vorher' ist das Ende des Datenfensters, kein Messwert.)"
        )

    zu_frueh = [e for e in bewertet if e["urteil"] == "zu-frueh"]
    if zu_frueh:
        print(
            f"  ({len(zu_frueh)} Gate(s) 'zu-frueh' — weniger als {MIN_FENSTER} Retros seit Bau. "
            "Kein Rueckfall ist hier KEIN Wirksamkeits-Beleg.)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
