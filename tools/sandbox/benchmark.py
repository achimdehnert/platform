#!/usr/bin/env python3
"""Benchmarks der Sandbox-Werkstatt (platform#3685, ADR-DRAFT sandbox-werkstatt §4.2).

Laeuft auf dem Host, nie im Container: Harness und Daten liegen ausserhalb der
Schreibreichweite der Sandbox, damit die bewertete Partei das Mass nicht
verschieben kann.

  B1  Owner-Belastung: absolute Wochenwerte aus dem Merge-Journal
  B2  Laeufe mit Status `fertig` ohne Eingriff, Quote und Dauer (status.json)
  B3  Uebernahmequote der Sandbox-Vorschlaege       — ausstehend, noch keine Upstream-PRs
  B4  Revert/Fix binnen 7 Tagen nach Uebernahme     — ausstehend, noch keine Upstream-PRs
  B5  Realfall-Replay: Gate-Drills gruen (gate_drill_check), muss 100 % bleiben
  B6  Kosten je Lauf (status.json)

B1 zaehlt je ISO-Woche absolute Mengen, keine Quote: Owner-Wort-Ereignisse,
verschiedene PRs mit Owner-Wort, Merges und Merge-Abbrueche mangels Mandat.
Eine Quote "PRs mit Owner-Wort je gemergtem PR" misst nichts, weil beide
Mengen fast disjunkt sind (Stand 2026-10-04: Schnitt 1 von 125 bzw. 317 PRs).
Saetze ohne Zeitstempel (Merge-Saetze vor dessen Einfuehrung) stehen getrennt
unter `ohne_zeitstempel`, statt geschaetzt einer Woche zugeschlagen zu werden.

Exit 3, wenn B5 gemessen wurde und unter 100 % liegt (harter Stopp, ADR §4.2);
sonst Exit 0. Ausgabe: JSON (--json) oder Markdown-Tabelle.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
MERGE_JOURNAL = Path.home() / ".claude" / "pr-merge-sa.jsonl"
#: Spiegel von ERGEBNIS_GEMERGT/ERGEBNIS_AUTO_MERGE in tools/pr_merge_sa.py
#: (Gleichheit per Test); kein Import, damit die Auswertung ohne dessen
#: Abhaengigkeiten laeuft.
MERGE_ERGEBNISSE = frozenset({"gemergt", "auto_merge"})
#: Spiegel von ERGEBNIS_BEREITS_GEMERGT: Ziel war schon erreicht, kein Abbruch.
BEREITS_GEMERGT = "bereits_gemergt"
LAEUFE = Path.home() / "sandbox-laeufe"
EXIT_REPLAY_ROT = 3


def _zeilen(pfad: Path):
    with pfad.open(encoding="utf-8") as f:
        for zeile in f:
            try:
                yield json.loads(zeile)
            except json.JSONDecodeError:
                continue


def _woche(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        jahr, woche, _ = datetime.fromisoformat(ts).isocalendar()
    except ValueError:
        return None
    return f"{jahr}-W{woche:02d}"


def b1_owner_belastung(journal: Path) -> dict:
    zaehler: dict[str, Counter] = defaultdict(Counter)
    prs_mit_wort: dict[str, set] = defaultdict(set)
    ohne_zeit: Counter = Counter(merges=0, abbrueche=0)
    for satz in _zeilen(journal):
        woche = _woche(satz.get("ts"))
        if "owner_wort" in satz:
            if satz["owner_wort"] and woche:
                zaehler[woche]["owner_wort_ereignisse"] += 1
                prs_mit_wort[woche].add((satz.get("repo"), satz.get("pr")))
            continue
        if satz.get("dry_run"):
            continue
        # Zeilen vor #3724 J1 tragen kein "ergebnis": dort bleibt "erlaubt" der Merge.
        # Erlaubt, aber nicht gemergt (von GitHub abgelehnt, UNKLAR kurz vor dem
        # Merge) ist weder Merge noch Abbruch mangels Mandat.
        if satz.get("erlaubt") and "ergebnis" in satz:
            if satz["ergebnis"] not in MERGE_ERGEBNISSE:
                continue
        if satz.get("ergebnis") == BEREITS_GEMERGT:
            continue
        art = "merges" if satz.get("erlaubt") else "abbrueche"
        ziel = zaehler[woche] if woche else ohne_zeit
        ziel[art] += 1
        # Derselbe Grund wie beim vorigen Versuch: Teilmenge der Abbrueche.
        if satz.get("wiederholung"):
            ziel["wiederholungen"] += 1
    wochen = {
        woche: {
            "owner_wort_ereignisse": zaehler[woche]["owner_wort_ereignisse"],
            "prs_mit_owner_wort": len(prs_mit_wort[woche]),
            "merges": zaehler[woche]["merges"],
            "abbrueche": zaehler[woche]["abbrueche"],
            "wiederholungen": zaehler[woche]["wiederholungen"],
        }
        for woche in sorted(zaehler)
    }
    return {"wochen": wochen, "ohne_zeitstempel": dict(ohne_zeit)}


def laeufe(wurzel: Path) -> list[dict]:
    ergebnis = []
    for status in sorted(wurzel.glob("*/ausgang/status.json")):
        try:
            daten = json.loads(status.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        daten["lauf"] = status.parent.parent.name
        ergebnis.append(daten)
    return ergebnis


def b2_durchlauf(laeufe_: list[dict]) -> dict:
    fertig = [lauf for lauf in laeufe_ if lauf.get("status") == "fertig"]
    dauern = sorted(lauf.get("dauer_min", 0) for lauf in fertig)
    return {
        "laeufe": len(laeufe_),
        "fertig": len(fertig),
        "quote_pct": round(100 * len(fertig) / len(laeufe_), 1) if laeufe_ else None,
        "median_dauer_min": dauern[len(dauern) // 2] if dauern else None,
    }


def b6_kosten(laeufe_: list[dict]) -> dict:
    kosten = [lauf.get("kosten_usd", 0.0) for lauf in laeufe_]
    return {
        "summe_usd": round(sum(kosten), 2),
        "je_lauf_usd": round(sum(kosten) / len(kosten), 2) if kosten else None,
    }


def b5_replay() -> dict:
    """Fuehrt die Gate-Drills echt aus — dieselbe Logik wie gate_drill_check.py."""
    sys.path.insert(0, str(TOOLS))
    import gate_drill_check as gdc  # noqa: E402 — erst nach dem Pfad-Einschub ladbar
    import gate_registry  # noqa: E402

    gates = gate_registry.laden(gdc.DEFAULT_REGISTRY).get("gates", [])
    rot: list[str] = []
    for gate in gates:
        if gdc.ist_fremd(gate):
            ok = not gdc.pruefe_fremd(gate)
        else:
            ok, _ = gdc.run_drill(gate.get("drill", ""))
        if not ok:
            rot.append(gate.get("slug", "?"))
    gruen = len(gates) - len(rot)
    return {
        "gates": len(gates),
        "gruen": gruen,
        "quote_pct": round(100 * gruen / len(gates), 1) if gates else None,
        "rot": rot,
    }


def messen(journal: Path, wurzel: Path, mit_replay: bool) -> dict:
    laeufe_ = laeufe(wurzel)
    return {
        "B1": b1_owner_belastung(journal),
        "B2": b2_durchlauf(laeufe_),
        "B3": {"ausstehend": "noch keine Upstream-PRs mit Sandbox-Beleg"},
        "B4": {"ausstehend": "noch keine Upstream-PRs mit Sandbox-Beleg"},
        "B5": b5_replay()
        if mit_replay
        else {"ausstehend": "ohne --mit-replay nicht gemessen"},
        "B6": b6_kosten(laeufe_),
    }


def als_markdown(ergebnis: dict) -> str:
    zeilen = ["| Benchmark | Wert |", "|---|---|"]
    for name, werte in ergebnis.items():
        if name == "B1":
            for woche, w in werte["wochen"].items():
                text = " · ".join(f"{k} {v}" for k, v in w.items())
                zeilen.append(f"| B1 {woche} | {text} |")
            werte = {"ohne_zeitstempel": werte["ohne_zeitstempel"]}
        text = " · ".join(f"{k} {v}" for k, v in werte.items())
        zeilen.append(f"| {name} | {text} |")
    return "\n".join(zeilen)


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmarks der Sandbox-Werkstatt messen")
    ap.add_argument("--journal", type=Path, default=MERGE_JOURNAL)
    ap.add_argument("--laeufe", type=Path, default=LAEUFE)
    ap.add_argument(
        "--mit-replay",
        action="store_true",
        help="B5: Gate-Drills ausfuehren (dauert Minuten)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ergebnis = messen(args.journal, args.laeufe, args.mit_replay)
    print(
        json.dumps(ergebnis, ensure_ascii=False, indent=2)
        if args.json
        else als_markdown(ergebnis)
    )
    b5 = ergebnis["B5"].get("quote_pct")
    return EXIT_REPLAY_ROT if b5 is not None and b5 < 100 else 0


if __name__ == "__main__":
    sys.exit(main())
