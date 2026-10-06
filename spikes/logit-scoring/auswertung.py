#!/usr/bin/env python3
"""Wertet rohdaten-*.jsonl aus messung.py aus (platform#3650): Treffer, Latenz, Stabilitaet.

python3 spikes/logit-scoring/auswertung.py spikes/logit-scoring/rohdaten-2026-09-30.jsonl
"""

from __future__ import annotations

import json
import statistics
import sys


def main(pfad: str) -> None:
    zeilen = [json.loads(z) for z in open(pfad, encoding="utf-8") if '"weg"' in z]
    print(
        "| Weg | Treffer | p50 ms | min ms | max ms | instabile Faelle | p(Gold) je Fall, Runde 1 |"
    )
    print("|---|---|---|---|---|---|---|")
    for weg in ("text", "logit", "kev"):
        r = [z for z in zeilen if z["weg"] == weg and "fehler" not in z]
        treffer = sum(z["label"] == z["gold"] for z in r)
        ms = [z["ms"] for z in r]
        je_fall: dict[int, set] = {}
        for z in r:
            je_fall.setdefault(z["fall"], set()).add(z["label"])
        instabil = [f for f, labels in je_fall.items() if len(labels) > 1]
        p_gold = (
            " ".join(f"{z['p'][z['gold']]:.2f}" for z in r if z["runde"] == 1)
            if weg != "text"
            else "—"
        )
        print(
            f"| {weg} | {treffer}/{len(r)} | {statistics.median(ms):.1f} | {min(ms):.1f} "
            f"| {max(ms):.1f} | {len(instabil)} | {p_gold} |"
        )
    fehler = sum("fehler" in z for z in zeilen)
    print(f"\nFehlerzeilen: {fehler}")


if __name__ == "__main__":
    main(sys.argv[1])
