#!/usr/bin/env python3
"""gate_kontrolllauf.py — einen Hook von Hand pruefen, ohne das echte Gate-Log zu fuellen.

Positivkontrollen und Selbstproben rufen einen Hook ausserhalb von pytest auf.
`gate_hits.notiere` sperrt nur unter pytest; ein Handaufruf ohne
`GATE_HITS_DATEI` schreibt deshalb ins echte `~/.claude/hooks/gate-hits.jsonl`.
Realfall Retro 835f30 Befund 1: Die Positivkontrolle zu #4048 und eine
Skript-Probe hinterliessen dort 7 Zeilen ohne Session, die jede
Fehlalarm-Auswertung mitzaehlt (platform#4061).

Dieses Werkzeug setzt `GATE_HITS_DATEI` immer auf eine Wegwerf-Datei, auch wenn
der Aufrufer schon eine gesetzt hat, und gibt aus, was der Hook dort notiert hat.

Aufruf:
  gate_kontrolllauf.py <hook> [--eingabe datei.json]   (sonst stdin)

Ausgabe: die Hook-Ausgabe, danach eine Zeile `protokoll: N Zeilen` und je Zeile
`slug marker modus`. Ausschnitte werden nicht gezeigt.
Exit: der des Hooks.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENV_PROTOKOLL = "GATE_HITS_DATEI"


def kontrolllauf(
    hook: Path, eingabe: str
) -> tuple[subprocess.CompletedProcess, list[dict]]:
    befehl = [sys.executable, str(hook)] if hook.suffix == ".py" else [str(hook)]
    with tempfile.TemporaryDirectory(prefix="gate-kontrolllauf-") as ordner:
        protokoll = Path(ordner) / "gate-hits.jsonl"
        lauf = subprocess.run(
            befehl,
            input=eingabe,
            capture_output=True,
            text=True,
            env={**os.environ, ENV_PROTOKOLL: str(protokoll)},
        )
        zeilen = []
        if protokoll.exists():
            for roh in protokoll.read_text(encoding="utf-8").splitlines():
                try:
                    zeilen.append(json.loads(roh))
                except json.JSONDecodeError:
                    zeilen.append({"marker": "unlesbar"})
    return lauf, zeilen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("hook", type=Path)
    ap.add_argument(
        "--eingabe", type=Path, help="Hook-Eingabe als JSON-Datei (sonst stdin)"
    )
    a = ap.parse_args(argv)

    eingabe = a.eingabe.read_text(encoding="utf-8") if a.eingabe else sys.stdin.read()
    lauf, zeilen = kontrolllauf(a.hook, eingabe)
    sys.stdout.write(lauf.stdout)
    sys.stderr.write(lauf.stderr)
    print(f"protokoll: {len(zeilen)} Zeilen")
    for z in zeilen:
        print(f"  {z.get('slug', '?')} {z.get('marker', '?')} {z.get('modus', '?')}")
    return lauf.returncode


if __name__ == "__main__":
    sys.exit(main())
