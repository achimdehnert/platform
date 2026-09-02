#!/usr/bin/env python3
"""gate_drill_check.py — Fenster-Prüflauf der Gate-Drills (KONZ-038 D8).

Liest docs/governance/gate-registry.json und führt jeden Drill ECHT aus
(pytest je Drill-Datei). Ein Gate mit rotem oder fehlendem Drill wird
K4-konform als NICHT GEBAUT gemeldet — der wiederkehrende Lauf beantwortet
M-8 dauerhaft: ein toter Hook wird binnen eines Fensters entdeckt, nicht 2028.

Verdrahtet im regel-ritual-Workflow (2.+16.); Ausgabe landet im Kommentar auf
dem Tracking-Issue. Exit 0 immer (Report-Tool, kein Gate-Enforcer — das Urteil
steht im Text). stdlib-only.

Aufruf: python3 tools/gate_drill_check.py [--registry <pfad>]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")


def pruefe_header(gate: dict) -> list[str]:
    """Befunde zum maschinenlesbaren Kopf des Gate-Moduls (KONZ-038 D8).

    D8 verlangt, dass JEDES Gate einen Kopf mit slug/mode/owner/last_drill_pass
    im Modul selbst traegt — nicht nur in der Registry. Ohne diese Pruefung
    verrottet der Kopf still: `last_drill_pass` wurde bis 2026-08-06 von
    keiner Zeile Code gelesen, und zwei der sieben Gates trugen ueberhaupt
    keinen Kopf. Der echte Drill-Lauf unten ist der staerkere Mechanismus und
    bleibt das Urteil; diese Pruefung deckt nur auf, wo Kopf und Registry
    auseinanderlaufen.

    Gibt eine Liste von Befund-Texten zurueck; leer = in Ordnung.
    """
    modul = gate.get("module", "")
    if not modul:
        # `meta`-Gates sind absichtlich modul-los: sie drillen quer ueber ALLE
        # registrierten Module (z.B. Executable-Bit + Shebang) und haben deshalb
        # kein eigenes. Kein Befund — aber auch nicht stillschweigend uebergehen.
        if gate.get("mode") == "meta":
            return []
        return ["kein `module` in der Registry — Kopf nicht pruefbar"]
    voll = os.path.join(REPO_ROOT, modul)
    if not os.path.isfile(voll):
        return [f"Modul fehlt: {modul}"]
    try:
        with open(voll, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return [f"Modul nicht lesbar: {exc}"]

    if "GATE_HEADER" not in text:
        return [
            "kein GATE_HEADER im Modul (D8 verlangt ihn dort, nicht nur in der Registry)"
        ]

    befunde = []
    for feld in ("slug", "mode", "owner", "last_drill_pass"):
        if f'"{feld}"' not in text:
            befunde.append(f"GATE_HEADER ohne `{feld}`")
    # Der Slug ist der Schluessel zwischen Kopf und Registry — laufen sie
    # auseinander, zeigt der Report auf ein anderes Gate als der Drill prueft.
    if gate.get("slug") and f'"{gate["slug"]}"' not in text:
        befunde.append(f"Slug im Kopf != Registry-Slug `{gate['slug']}`")
    return befunde


#: Das Repo, dessen Pfade dieser Pruefer wirklich ausfuehren kann.
EIGENES_REPO = "platform"


def ist_fremd(gate: dict) -> bool:
    """Lebt das Gate in einem anderen Repo als platform?

    **Warum es diesen Fall gibt** (platform#2429): Die Klassen dieser Flotte
    entstehen in den Hub-Repos, und ihr natuerliches Gate ist ein Test in
    ebendiesem Repo -- er laeuft dort in der CI und blockt dort den Merge. Bis
    hierhin konnte die Registry das nicht abbilden: `module`/`drill` sind
    platform-relative Pfade, die dieser Pruefer selbst ausfuehrt. Ein Eintrag
    mit fremdem Pfad wurde folgerichtig als "NICHT GEBAUT" zurueckgestuft --
    eine Aussage ueber die *Ausfuehrbarkeit hier*, die als Aussage ueber die
    *Wirksamkeit dort* gelesen wurde.

    Realfall: `built-but-never-called` bekam am 2026-08-29 ein Gate in
    `iilgmbh/ausschreibungs-hub` (tests/test_adapterfelder_werden_gelesen.py,
    blocking in dessen CI). Der Registry-Eintrag wurde wieder zurueckgenommen,
    weil er den Pruefer zum Luegen gebracht haette -- und damit fuehrte
    `retro_kpis.py` den Slug weiter unter "ohne registriertes Gate", obwohl
    eines existiert und greift.
    """
    repo = (gate.get("repo") or EIGENES_REPO).strip()
    return repo != EIGENES_REPO


def pruefe_fremd(gate: dict) -> list[str]:
    """Was ein fremd verankertes Gate stattdessen belegen muss.

    Der Pruefer kann den Drill nicht fahren -- also muss der Eintrag sagen, wo
    er faehrt und woran man das nachliest. Ohne diese beiden Angaben waere
    `repo` bloss ein Weg, sich der Pruefung zu entziehen.
    """
    befunde = []
    if not (gate.get("ref") or "").strip():
        befunde.append(
            "fremd verankert ohne `ref` — kein Beleg, dass das Gate existiert"
        )
    if not (gate.get("drill") or "").strip():
        befunde.append("fremd verankert ohne `drill` — der Pfad im Ziel-Repo fehlt")
    return befunde


def run_drill(drill_path: str) -> tuple[bool, str]:
    """True = Drill grün. Fehlende Datei = rot (K4: nicht belegbar = nicht gebaut)."""
    full = os.path.join(REPO_ROOT, drill_path)
    if not os.path.isfile(full):
        return False, "Drill-Datei fehlt"
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", full, "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=REPO_ROOT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Drill-Lauf fehlgeschlagen: {exc}"
    tail = (out.stdout.strip().splitlines() or ["(keine Ausgabe)"])[-1]
    return out.returncode == 0, tail


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate-Drills echt ausführen (KONZ-038 D8)")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = ap.parse_args()

    try:
        registry = json.load(open(args.registry, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"⚠ Gate-Registry nicht lesbar ({exc}) — Prüflauf NICHT bewertbar.")
        return 0

    gates = registry.get("gates", [])
    print(f"## Gate-Drill-Prüflauf ({len(gates)} registrierte Gates)")
    dead = 0
    kopf_befunde: list[str] = []
    fremd = 0
    for g in gates:
        if ist_fremd(g):
            maengel = pruefe_fremd(g)
            if maengel:
                dead += 1
                print(f"  ✗ {g['slug']} ({g.get('mode', '?')}) — {'; '.join(maengel)}")
            else:
                fremd += 1
                print(
                    f"  ⌁ {g['slug']} ({g.get('mode', '?')}) — fremd verankert in "
                    f"{g['repo']}: {g['drill']} (Beleg: {g['ref']})"
                )
            # Kein Kopf-Check: das Modul liegt nicht in diesem Arbeitsbaum.
            continue

        ok, detail = run_drill(g.get("drill", ""))
        if ok:
            print(f"  ✓ {g['slug']} ({g.get('mode', '?')}) — {detail}")
        else:
            dead += 1
            print(
                f"  ✗ {g['slug']} ({g.get('mode', '?')}) — K4: NICHT GEBAUT — {detail}"
            )
        for b in pruefe_header(g):
            kopf_befunde.append(f"{g.get('slug', '?')}: {b}")

    if kopf_befunde:
        print(f"\n### Kopf-Konsistenz ({len(kopf_befunde)} Befund(e))")
        for b in kopf_befunde:
            print(f"  ⚠ {b}")
        print(
            "  → Der Drill oben ist das Urteil; ein fehlender Kopf macht ein Gate "
            "nicht wirkungslos. Er nimmt ihm aber die Selbstauskunft — genau die, "
            "die D8 verlangt."
        )
    else:
        print("\n### Kopf-Konsistenz — alle Gates tragen einen vollstaendigen Kopf.")

    if dead:
        print(
            f"\n→ {dead} Gate(s) K4-zurückgestuft: Drill reparieren oder Gate aus der "
            "Registry nehmen — beides per PR, nicht stillschweigend."
        )
    else:
        print("\n→ alle registrierten Gates Drill-frisch.")

    if fremd:
        print(
            f"  ⌁ davon {fremd} fremd verankert (Drill laeuft in der CI des Ziel-Repos, "
            "nicht hier) — der Beleg ist die genannte `ref`, nicht ein Lauf dieses Pruefers."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
