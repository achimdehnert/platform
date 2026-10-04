#!/usr/bin/env python3
"""Waechter der Sandbox (platform#3685) — startet den Agenten und haelt das Budget.

Laeuft nur im Sandbox-Container und nur nach bestandener Selbstpruefung
(start.sh). Das Budget ist Mechanik, nicht Text (autonomy-gates
„Budget-Deklaration“): der Waechter liest den stream-json-Ausgang von Claude
Code mit und beendet den Lauf, sobald eine Grenze erreicht ist:

  max_tokens   Ausgabe-Tokens des ganzen Laufs (Teilagenten eingeschlossen)
  max_agenten  gestartete Teilagenten (Agent-/Task-Aufrufe)
  max_stunden  Laufzeit
  max_usd      harte Kostengrenze, zusaetzlich von Claude Code selbst gehalten

Ein Lauf, der an einer Grenze endet, heisst `abgebrochen: Budget (<grenze>)`,
nie `fertig`. Ergebnis: <arbeit>/ausgang/status.json + bericht.md.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

AGENTEN_WERKZEUGE = {"Agent", "Task"}
REGELN = """Du arbeitest in einer Wegwerf-Sandbox (platform#3685). Arbeite den Auftrag unten
vollstaendig autonom ab, ohne Rueckfragen. Es gibt hier keinen Prod-Zugang und keine
echten Repos: Kopien liegen unter {arbeit}/eingang/repos, ohne Remote. Schreiben darfst
du nur im Arbeitsbereich {arbeit} und, falls GH_TOKEN gesetzt ist, in der GitHub-Org
{org}. Am Ende schreibst du {arbeit}/ausgang/bericht.md mit diesen Abschnitten:
## Auftrag · ## Ergebnis · ## Belege (Befehle + Ausgaben) · ## Hypothesen (ungeprueft) · ## Offene Punkte

# Auftrag

{auftrag}
"""


@dataclass
class Zaehler:
    max_tokens: int
    max_agenten: int
    tokens_je_nachricht: dict = field(default_factory=dict)
    agenten: set = field(default_factory=set)
    kosten_usd: float | None = None
    ergebnis: str | None = None
    ergebnis_art: str | None = None

    @property
    def tokens(self) -> int:
        return sum(self.tokens_je_nachricht.values())

    def verarbeite(self, zeile: str) -> str | None:
        """Eine stream-json-Zeile verbuchen; liefert die erreichte Grenze oder None."""
        try:
            ereignis = json.loads(zeile)
        except json.JSONDecodeError:
            return None
        if ereignis.get("type") == "assistant":
            nachricht = ereignis.get("message") or {}
            # Dieselbe Nachricht kommt je Inhaltsblock einmal — Usage je Nachricht nur einmal zaehlen.
            ausgabe = (nachricht.get("usage") or {}).get("output_tokens") or 0
            mid = nachricht.get("id") or id(nachricht)
            self.tokens_je_nachricht[mid] = max(self.tokens_je_nachricht.get(mid, 0), ausgabe)
            for block in nachricht.get("content") or []:
                if block.get("type") == "tool_use" and block.get("name") in AGENTEN_WERKZEUGE:
                    self.agenten.add(block.get("id"))
        elif ereignis.get("type") == "result":
            self.kosten_usd = ereignis.get("total_cost_usd")
            self.ergebnis = ereignis.get("result")
            self.ergebnis_art = ereignis.get("subtype")
        if self.tokens > self.max_tokens:
            return "max_tokens"
        if len(self.agenten) > self.max_agenten:
            return "max_agenten"
        return None


def status_von(zaehler: Zaehler, grenze: str | None, rc: int | None) -> str:
    if grenze:
        return f"abgebrochen: Budget ({grenze})"
    if zaehler.ergebnis_art and "budget" in zaehler.ergebnis_art:
        return "abgebrochen: Budget (max_usd)"
    if rc == 0 and zaehler.ergebnis_art == "success":
        return "fertig"
    return f"fehler (rc={rc}, {zaehler.ergebnis_art or 'kein Ergebnis'})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arbeit", default=os.environ.get("SANDBOX_ARBEIT", "/arbeit"))
    ap.add_argument("--max-tokens", type=int, default=1_000_000)
    ap.add_argument("--max-agenten", type=int, default=5)
    ap.add_argument("--max-stunden", type=float, default=4.0)
    ap.add_argument("--max-usd", type=float, default=50.0)
    ap.add_argument("--modell", default=os.environ.get("SANDBOX_MODELL", ""))
    ap.add_argument("--claude", default="claude")
    a = ap.parse_args()

    if os.environ.get("IIL_SANDBOX") != "1":
        print("Waechter: nur im Sandbox-Container (IIL_SANDBOX=1)", file=sys.stderr)
        return 1
    arbeit = Path(a.arbeit)
    ausgang = arbeit / "ausgang"
    ausgang.mkdir(parents=True, exist_ok=True)
    auftrag = (arbeit / "eingang" / "auftrag.md").read_text(encoding="utf-8")
    prompt = REGELN.format(arbeit=arbeit, org=os.environ.get("SANDBOX_ORG") or "(keine)", auftrag=auftrag)

    befehl = [a.claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
              "--dangerously-skip-permissions", "--max-budget-usd", str(a.max_usd)]
    if a.modell:
        befehl += ["--model", a.modell]
    zaehler = Zaehler(a.max_tokens, a.max_agenten)
    grenze = None
    start = time.monotonic()
    proc = subprocess.Popen(befehl, cwd=arbeit, stdout=subprocess.PIPE, text=True)

    def zeitgrenze():
        nonlocal grenze
        if proc.poll() is None:
            grenze = grenze or "max_stunden"
            proc.terminate()

    uhr = threading.Timer(a.max_stunden * 3600, zeitgrenze)
    uhr.start()
    with open(ausgang / "verlauf.jsonl", "w", encoding="utf-8") as verlauf:
        for zeile in proc.stdout:
            verlauf.write(zeile)
            treffer = zaehler.verarbeite(zeile)
            if treffer and not grenze:
                grenze = treffer
                proc.terminate()
    rc = proc.wait()
    uhr.cancel()

    status = status_von(zaehler, grenze, rc)
    bericht = ausgang / "bericht.md"
    if not bericht.exists():
        bericht.write_text(f"# Kein Bericht vom Agenten\n\nStatus: {status}\n\n{zaehler.ergebnis or ''}\n", encoding="utf-8")
    (ausgang / "status.json").write_text(json.dumps({
        "status": status,
        "ausgabe_tokens": zaehler.tokens,
        "teilagenten": len(zaehler.agenten),
        "kosten_usd": zaehler.kosten_usd,
        "dauer_min": round((time.monotonic() - start) / 60, 1),
        "grenzen": {"max_tokens": a.max_tokens, "max_agenten": a.max_agenten,
                    "max_stunden": a.max_stunden, "max_usd": a.max_usd},
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Waechter: {status}")
    return 0 if status == "fertig" else 2


if __name__ == "__main__":
    sys.exit(main())
