#!/usr/bin/env python3
"""gate_namensdeckung.py — beruehrt der Drill den Fall, der im Slug-Namen steht?

Ein Gate kann vollstaendig gebaut sein — Registry-Eintrag, gruener Drill, aktive
Verdrahtung — und trotzdem die Sache verfehlen, die sein Name benennt. Realfall
2026-08-23: `lint-failure-no-local-gate` steht als `blocking` in der Registry,
heisst "lint" und fuehrt `ruff format --check` aus. Das prueft Layout, nicht
Linter-Regeln; ein Import nach einer Zuweisung auf Modulebene (E402) war dafuer
seit dem Bau am 2026-08-04 unsichtbar. Drei Messpunkte des Loops standen auf
gruen und keiner stellte diese Frage.

**Was dieser Pruefer misst — und was nicht.** Er misst, ob der Drill den
namensgebenden Fall ueberhaupt BERUEHRT: die Registry nennt je Gate die Faelle,
gegen die es schuetzt (`faengt`), jeder Fall traegt eine `probe`, und die probe
muss im Drill vorkommen. Er misst NICHT, ob der Test den Fall wirklich abfaengt —
dafuer braeuchte es einen Mutationstest. Die Grenze steht hier, damit niemand aus
einem gruenen Lauf mehr liest, als drinsteht; genau dieser Fehler hat den Realfall
oben erst moeglich gemacht.

Drei Zustaende, und der mittlere ist der wichtigste:
  gedeckt     — jede probe im Drill gefunden
  luecke      — mindestens eine probe fehlt: der Fall ist benannt und ungedrillt
  ungeprueft  — kein `faengt`-Feld. Das ist KEIN gruen: die Frage wurde nie
                gestellt. Ein SKIP, der als PASS verbucht wird, beendet das Suchen
                (KONZ-platform-050).

Usage: gate_namensdeckung.py [--kurz] [--registry <pfad>] [--repo <pfad>]
Exit 0 immer — ein Melder, der den Sitzungsstart aufhaelt, wird abgeschaltet.

Slug: `gate-modul-prueft-weniger-als-sein-name` (platform#2234, Owner-Auftrag
2026-08-23 nach dem Widerruf des Verzichts auf `gate-matches-spelling-not-substance`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

GATE_HEADER = {
    "slug": "gate-modul-prueft-weniger-als-sein-name",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-23",
    "evidence": "tools/tests/test_gate_namensdeckung.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")


def _lies(repo: str, rel: str) -> str:
    """Dateiinhalt oder "" — ein fehlender Drill ist eine Luecke, kein Absturz."""
    if not rel:
        return ""
    pfad = rel if os.path.isabs(rel) else os.path.join(repo, rel)
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def pruefe_gate(gate: dict, repo: str = REPO_ROOT) -> dict:
    """→ {slug, zustand, gedeckt: [...], fehlend: [...], dateien: n}"""
    faelle = gate.get("faengt")
    slug = gate.get("slug", "?")
    if not faelle:
        return {"slug": slug, "zustand": "ungeprueft", "gedeckt": [], "fehlend": [], "dateien": 0}

    quellen = [gate.get("drill", "")] + list(gate.get("drill_extra") or [])
    text = "\n".join(_lies(repo, q) for q in quellen).lower()
    gelesen = sum(1 for q in quellen if _lies(repo, q))

    gedeckt, fehlend = [], []
    for fall in faelle:
        probe = (fall.get("probe") or "").strip().lower()
        beschreibung = fall.get("fall", probe)
        if probe and probe in text:
            gedeckt.append(beschreibung)
        else:
            fehlend.append(beschreibung)
    return {
        "slug": slug,
        "zustand": "luecke" if fehlend else "gedeckt",
        "gedeckt": gedeckt,
        "fehlend": fehlend,
        "dateien": gelesen,
    }


def bericht(staende: list[dict], kurz: bool) -> str:
    luecken = [s for s in staende if s["zustand"] == "luecke"]
    ungeprueft = [s for s in staende if s["zustand"] == "ungeprueft"]
    gedeckt = [s for s in staende if s["zustand"] == "gedeckt"]

    if kurz:
        if not luecken:
            return ""
        spitze = luecken[0]
        zeilen = [
            f"{len(luecken)} Gate(s) nennen einen Fall, den ihr Drill nicht beruehrt — "
            f"{spitze['slug']}: {', '.join(spitze['fehlend'][:2])}"
            + (f" (+{len(luecken) - 1} weitere)" if len(luecken) > 1 else "")
        ]
        for s in luecken[1:]:
            zeilen.append(f"  · {s['slug']} — {', '.join(s['fehlend'][:2])}")
        return "\n".join(zeilen)

    zeilen = [
        f"# Namensdeckung ueber {len(staende)} registrierte Gates",
        "",
        f"  gedeckt    : {len(gedeckt)}",
        f"  LUECKE     : {len(luecken)}",
        f"  ungeprueft : {len(ungeprueft)}  (kein `faengt`-Feld — die Frage wurde nie gestellt)",
        "",
    ]
    for s in luecken:
        zeilen.append(f"🚨 {s['slug']}")
        for f in s["fehlend"]:
            zeilen.append(f"     nicht im Drill: {f}")
    if luecken:
        zeilen.append("")
    for s in gedeckt:
        zeilen.append(f"  ✓ {s['slug']} — {len(s['gedeckt'])} Fall/Faelle gedrillt")
    if ungeprueft:
        zeilen.append("")
        zeilen.append("  ungeprueft (Reihenfolge = Registry): " + ", ".join(s["slug"] for s in ungeprueft))
        zeilen.append(
            "  → `faengt: [{fall, probe}]` je Gate nachtragen. Das ist Bestandsarbeit,"
        )
        zeilen.append(
            "    kein Fehler des Gates — aber solange es fehlt, ist ueber seine Deckung nichts gesagt."
        )
    zeilen.append("")
    zeilen.append(
        "Gemessen wird, ob der Drill den benannten Fall BERUEHRT — nicht, ob er ihn abfaengt."
    )
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--repo", default=REPO_ROOT)
    ap.add_argument("--kurz", action="store_true", help="eine Zeile fuer den Runner")
    ap.add_argument("--json", action="store_true", dest="als_json")
    args = ap.parse_args(argv)

    try:
        with open(args.registry, encoding="utf-8") as f:
            gates = json.load(f).get("gates", [])
    except (OSError, ValueError) as fehler:
        if not args.kurz:
            print(f"Registry nicht lesbar ({fehler}) — kein Urteil.", file=sys.stderr)
        return 0

    staende = [pruefe_gate(g, args.repo) for g in gates]
    if args.als_json:
        print(json.dumps({"gates": staende}, ensure_ascii=False, indent=2))
        return 0
    text = bericht(staende, args.kurz)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
