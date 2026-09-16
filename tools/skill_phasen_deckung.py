#!/usr/bin/env python3
"""skill_phasen_deckung.py — jede Runner-Phase, die WARN sagen kann, braucht im
Skill eine Zeile, die sagt, was die WARN bedeutet.

## Anlass (2026-09-16)

Der Session-Start meldete `⚠️ 0.7.4 prio-referenzen — 2 Prio-Referenz(en) zeigen
auf Erledigtes — Prio nachziehen VOR Arbeitsbeginn`. Der Runner sagte also
selbst, dass vor Arbeitsbeginn etwas zu tun ist. Im Skill `session-start.md`
stand zu dieser Phase **nichts**: weder eine Zeile in der WARN-Deutungstabelle
noch in der Startklar-Checkliste. Gehandelt wurde nur, weil der Runner-Text es
mitlieferte — nicht, weil das Skill es verlangte.

Gemessen an dem Tag: 6 von 37 WARN-fähigen Start-Phasen ohne Deutungszeile
(`0.6`, `0.7.4`, `0.7.13`, `0.7.19`, `0.7.25`, `0.7.26`), 1 von 10 im Ende-Runner
(`E.10`). Drei davon meldeten an diesem Morgen tatsächlich WARN.

## Warum das eine eigene Prüfung braucht

`governance/melder-register.yaml` (Start-Phase 0.7.23) prüft, ob jeder Melder
einen **Leser** hat — eine Rolle, die ihn liest. Das ist eine andere Frage als
die hier: ob der **Text**, den dieser Leser zur Hand hat, die Phase überhaupt
erwähnt. 0.7.23 stand an dem Morgen auf PASS, während sechs Phasen ungedeutet
waren. Ein Melder ohne Deutung ist strukturell überspringbar: der Leser sieht
eine WARN, findet im Ablauf keinen Eintrag dazu und liest darüber hinweg —
dieselbe Ausführungstreue-Lücke, die schon `session-ende` 2026-07-15 traf.

## Was geprüft wird

Für jedes Paar (Runner-Skript, Skill-Dokument):

1. Phasen sammeln, die im Runner mit `record "<phase>" "WARN"` (bzw.
   `"JUDGMENT"`) belegt sind — also alles, was dem Leser je als Befund
   begegnen kann. Phasen, die nur PASS melden koennen, bleiben ausserhalb
   des Pruefbereichs — sie haben keinen Befund, der gedeutet werden muesste.
2. Prüfen, ob die Phasen-Kennung im Skill-Dokument vorkommt.
3. Fehlende auflisten. Exit 1, wenn eine fehlt.

Bewusste Grenze (kein Silent Cap): geprüft wird **Erwähnung**, nicht Güte. Ob
die Zeile die WARN brauchbar deutet, entscheidet ein Mensch — der Prüfer fängt
nur den Fall „steht überhaupt nicht da".

Aufruf:
  python3 tools/skill_phasen_deckung.py [--kurz]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

#: (Runner-Skript, Skill-Dokument) — beide relativ zur Repo-Wurzel.
PAARE = [
    ("tools/session_start_checks.sh", ".windsurf/workflows/session-start.md"),
    ("tools/session_ende_checks.sh", ".windsurf/workflows/session-ende.md"),
]

RECORD_RE = re.compile(r'record\s+"([^"]+?)"\s+"(WARN|JUDGMENT)"')


def warn_phasen(runner_text: str) -> list[str]:
    """Phasen-Kennungen, die der Runner als WARN/JUDGMENT melden kann."""
    return sorted({m.group(1).split()[0] for m in RECORD_RE.finditer(runner_text)})


def ungedeutet(runner_text: str, skill_text: str) -> list[str]:
    return [p for p in warn_phasen(runner_text) if p not in skill_text]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kurz", action="store_true", help="eine Zeile statt Bericht")
    a = p.parse_args(argv)

    wurzel = pathlib.Path(__file__).resolve().parent.parent
    befunde: list[tuple[str, str, list[str]]] = []
    geprueft = 0
    for runner, skill in PAARE:
        rp, sp = wurzel / runner, wurzel / skill
        if not rp.exists() or not sp.exists():
            print(f"⛔ fehlt: {runner if not rp.exists() else skill}", file=sys.stderr)
            return 2
        rt, st = rp.read_text(encoding="utf-8"), sp.read_text(encoding="utf-8")
        geprueft += len(warn_phasen(rt))
        fehlend = ungedeutet(rt, st)
        if fehlend:
            befunde.append((runner, skill, fehlend))

    offen = sum(len(f) for _, _, f in befunde)
    if a.kurz:
        if offen:
            namen = ", ".join(n for _, _, f in befunde for n in f)
            print(
                f"skill-deckung: {offen}/{geprueft} WARN-Phase(n) ungedeutet — {namen}"
            )
        else:
            print(f"skill-deckung: alle {geprueft} WARN-Phasen im Skill gedeutet")
        return 1 if offen else 0

    if not befunde:
        print(
            f"✅ alle {geprueft} WARN-fähigen Phasen sind im zugehörigen Skill erwähnt"
        )
        return 0

    print(f"⛔ {offen} von {geprueft} WARN-fähigen Phasen ohne Zeile im Skill:")
    for runner, skill, fehlend in befunde:
        print(f"\n  {runner} → {skill}")
        for name in fehlend:
            print(f"    - {name}")
    print(
        "\nEine WARN ohne Deutung im Ablauf wird überlesen: der Leser findet keinen\n"
        "Eintrag und geht weiter. Jede Phase braucht eine Zeile — entweder in der\n"
        "Deutungstabelle (was bedeutet die WARN, was ist kein Befund, welcher Zug)\n"
        "oder, wo das zu viel wäre, wenigstens eine Erwähnung im Ablauftext."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
