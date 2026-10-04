#!/usr/bin/env python3
"""Benchmarks der Sandbox-Werkstatt (platform#3685, ADR-DRAFT sandbox-werkstatt §4.2).

Laeuft auf dem Host, nie im Container: Harness und Daten liegen ausserhalb der
Schreibreichweite der Sandbox, damit die bewertete Partei das Mass nicht
verschieben kann.

  B1  Owner-Unterbrechungen: PRs mit Owner-Wort je gemergtem PR (Merge-Journal)
  B2  Laeufe mit Status `fertig` ohne Eingriff, Quote und Dauer (status.json)
  B3  Uebernahmequote der Sandbox-Vorschlaege       — ausstehend, noch keine Upstream-PRs
  B4  Revert/Fix binnen 7 Tagen nach Uebernahme     — ausstehend, noch keine Upstream-PRs
  B5  Realfall-Replay: Gate-Drills gruen (gate_drill_check), muss 100 % bleiben
  B6  Kosten je Lauf (status.json)

B1 zaehlt verschiedene PRs, nicht Ereignisse: Das Journal fuehrt Merge-Versuche
(ohne Zeitstempel) und Owner-Wort-Ereignisse (vom Hook, mit Zeitstempel) als
zwei Satzarten; ein PR mit drei Owner-Worten ist eine Unterbrechungsstelle,
nicht drei. Weil Merge-Saetze keinen Zeitstempel tragen, misst B1 den ganzen
Journal-Bestand; Wochenwerte entstehen als Differenz zweier Messungen.

Exit 3, wenn B5 gemessen wurde und unter 100 % liegt (harter Stopp, ADR §4.2);
sonst Exit 0. Ausgabe: JSON (--json) oder Markdown-Tabelle.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
MERGE_JOURNAL = Path.home() / ".claude" / "pr-merge-sa.jsonl"
LAEUFE = Path.home() / "sandbox-laeufe"
EXIT_REPLAY_ROT = 3


def _zeilen(pfad: Path):
    with pfad.open(encoding="utf-8") as f:
        for zeile in f:
            try:
                yield json.loads(zeile)
            except json.JSONDecodeError:
                continue


def b1_owner_unterbrechungen(journal: Path) -> dict:
    gemergt: set[tuple] = set()
    mit_wort: set[tuple] = set()
    for satz in _zeilen(journal):
        pr = (satz.get("repo"), satz.get("pr"))
        if "owner_wort" in satz:
            if satz["owner_wort"]:
                mit_wort.add(pr)
            continue
        if satz.get("dry_run") or not satz.get("erlaubt"):
            continue
        gemergt.add(pr)
    quote = round(100 * len(mit_wort) / len(gemergt), 1) if gemergt else None
    return {
        "prs_mit_owner_wort": len(mit_wort),
        "prs_gemergt": len(gemergt),
        "quote_pct": quote,
    }


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
        "B1": b1_owner_unterbrechungen(journal),
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
