#!/usr/bin/env python3
"""zeitplan_wach.py — findet Workflows, die GitHub still abgeschaltet hat.

## Warum es das gibt

Am 2026-08-20 stellte sich heraus, dass in `achimdehnert/infra-deploy` seit dem
**2026-07-30 kein Datenbank-Backup mehr lief** — drei Wochen lang. Nicht weil es
scheiterte, sondern weil GitHub die beiden `schedule`-Workflows in den Zustand
`disabled_inactivity` versetzt hatte: **Zeitplaene werden nach 60 Tagen ohne
Repo-Aktivitaet automatisch abgeschaltet.** Letzter Push dort war der 2026-05-30,
sechzig Tage spaeter ist der 29./30.07. — auf den Tag genau der Zeitpunkt, an dem
die Laeufe aufhoerten.

Das offene Issue dazu (platform#2114) hatte eine andere Ursache vermutet („das
Label nimmt kein Runner an"). Die war widerlegbar: der Runner war online, und ein
Workflow mit demselben Label lief am selben Tag gruen. Niemand hatte den
**Workflow-Zustand** angesehen, weil kein Werkzeug ihn abfragt.

## Die Fehlerklasse

Ein abgeschalteter Zeitplan **meldet nichts und sieht dabei aus wie Ruhe**. Er ist
damit die stillste Variante von `melder-ohne-leser`: kein roter Lauf, keine
Fehlermail, keine Warnung — nur eine Lueckenreihe in der Lauf-Historie, die man
sehen muesste, um sie zu bemerken.

Besonders betroffen sind Repos, die **ausschliesslich Zeitplaene fahren** und
sonst keine Commits bekommen. Die schalten sich zwangslaeufig selbst ab: je
verlaesslicher der Automatismus, desto weniger Grund gibt es, ins Repo zu pushen.
`infra-deploy` ist genau so gebaut.

## Was gemeldet wird

- `disabled_inactivity` — von GitHub abgeschaltet. **Immer ein Befund.**
- `disabled_manually` — von einem Menschen abgeschaltet. Meist Absicht (Realfall
  trading-hub, bewusst wegen eines GHCR-Rechts), deshalb nur als Hinweis. Das
  Werkzeug kann Absicht nicht von Vergessen unterscheiden — der Mensch schon.

Repos ohne `schedule`-Trigger sind uninteressant und erscheinen nicht.

## Aufruf

    python3 tools/zeitplan_wach.py            # voller Report
    python3 tools/zeitplan_wach.py --kurz     # eine Zeile fuer den Session-Start
    python3 tools/zeitplan_wach.py --json
    python3 tools/zeitplan_wach.py --repo achimdehnert/infra-deploy   # gezielt

Braucht `gh` mit Leserecht auf die Repos (lokaler PAT). Bewusst **kein**
GitHub-Action-Nightly: die vorhandene Reconciler-App traegt `metadata`/`issues`/
`pull_requests`, aber **nicht** `actions: read` — ein Nightly waere dort still
blind, also genau der Fehler, den dieses Werkzeug meldet.

Exit-Code 0 immer (Report-Werkzeug). stdlib-only ausser `gh` und PyYAML.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

GATE_HEADER = {
    "slug": "zeitplan-still-abgeschaltet",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-20",
    "evidence": "tools/tests/test_zeitplan_wach.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO_ROOT, "registry", "canonical.yaml")

STILL_ABGESCHALTET = "disabled_inactivity"
VON_HAND = "disabled_manually"


ORGS = ("achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra")


def repos_aus_orgs(orgs: tuple[str, ...] = ORGS) -> list[str]:
    """Alle Repos der vier Orgs — die Registry allein reicht NICHT.

    Beim ersten Vollflotten-Lauf am 2026-08-20 meldete dieses Werkzeug **null**
    abgeschaltete Zeitplaene, obwohl `achimdehnert/infra-deploy` seit drei Wochen
    zwei davon hatte: das Repo traegt in der Registry kein `rich.github`-Feld und
    fiel damit aus der Liste. Ein Flotten-Melder, dessen Repo-Liste ausgerechnet
    den betroffenen Fall nicht kennt, meldet eine Null, die nur sein Filter ist
    (🌀 measurement-tool-zero-is-not-absence). Deshalb: Orgs aufzaehlen, Registry
    nur ergaenzend dazunehmen.
    """
    namen: list[str] = []
    for org in orgs:
        ergebnis = subprocess.run(
            ["gh", "repo", "list", org, "--limit", "300", "--json", "nameWithOwner"],
            capture_output=True,
            text=True,
        )
        if ergebnis.returncode != 0:
            continue
        try:
            namen.extend(e["nameWithOwner"] for e in json.loads(ergebnis.stdout))
        except (ValueError, KeyError, TypeError):
            continue
    return namen


def repos_aus_registry(pfad: str = REGISTRY) -> list[str]:
    """`owner/repo` aus `rich.github` — die einzige Stelle mit der echten Org.

    Nicht aus dem Repo-Namen raten: 16 Repos liegen in `iilgmbh`, und die
    GitHub-API leitet von der falschen Org still um (🌀 github-redirect).
    """
    try:
        import yaml
    except ImportError:
        return []
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = yaml.safe_load(fh)
    except OSError:
        return []
    repos = daten.get("repos", daten)
    namen = []
    for eintrag in repos.values():
        if not isinstance(eintrag, dict):
            continue
        voll = (eintrag.get("rich") or {}).get("github")
        if voll and "/" in voll:
            namen.append(voll)
    return sorted(set(namen))


def workflows(voll_name: str) -> list[dict] | None:
    """None = nicht abfragbar (fehlendes Recht, Repo weg) — NIE als 'alles gut'.

    Ein Abfragefehler ist kein gruener Zustand (🌀 fetch-failure-is-not-green).
    """
    ergebnis = subprocess.run(
        ["gh", "api", f"repos/{voll_name}/actions/workflows", "--paginate"],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        return None
    try:
        daten = json.loads(ergebnis.stdout)
    except ValueError:
        return None
    return daten.get("workflows", [])


def pruefe(namen: list[str], nebenlaeufig: int = 8) -> dict:
    still, von_hand, blind = [], [], []
    # Nebenlaeufig, damit die Vollflotte im Session-Start tragbar bleibt: 78 Repos
    # sequenziell sind ~27s, mit acht Faeden ~5s. Die Reihenfolge der Ergebnisse
    # spielt keine Rolle, sie werden ohnehin sortiert ausgegeben.
    with ThreadPoolExecutor(max_workers=nebenlaeufig) as pool:
        paare = list(zip(namen, pool.map(workflows, namen)))
    for voll, wfs in paare:
        if wfs is None:
            blind.append(voll)
            continue
        for wf in wfs:
            zustand = wf.get("state", "")
            eintrag = {"repo": voll, "workflow": wf.get("name"), "zustand": zustand}
            if zustand == STILL_ABGESCHALTET:
                still.append(eintrag)
            elif zustand == VON_HAND:
                von_hand.append(eintrag)
    still.sort(key=lambda e: (e["repo"], e["workflow"] or ""))
    von_hand.sort(key=lambda e: (e["repo"], e["workflow"] or ""))
    return {
        "geprueft": len(namen) - len(blind),
        "still_abgeschaltet": still,
        "von_hand_abgeschaltet": von_hand,
        "nicht_abfragbar": blind,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", action="append", dest="repos")
    parser.add_argument("--kurz", action="store_true")
    parser.add_argument("--json", action="store_true", dest="als_json")
    args = parser.parse_args()

    namen = args.repos or sorted(set(repos_aus_orgs()) | set(repos_aus_registry()))
    if not namen:
        if not args.kurz:
            print(
                "Keine Repos ermittelbar (Registry unlesbar?) — kein Urteil.",
                file=sys.stderr,
            )
        return 0

    ergebnis = pruefe(namen)
    still = ergebnis["still_abgeschaltet"]

    if args.als_json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 0

    if args.kurz:
        if still:
            spitze = still[0]
            weitere = f" (+{len(still) - 1} weitere)" if len(still) > 1 else ""
            print(
                f"{len(still)} Workflow(s) von GitHub still abgeschaltet — "
                f"{spitze['repo']}: {spitze['workflow']}{weitere}"
            )
            for e in still[1:5]:
                print(f"  · {e['repo']}: {e['workflow']}")
        elif ergebnis["nicht_abfragbar"]:
            # Abdeckungsluecke sichtbar halten, auch wenn nichts gefunden wurde.
            print(
                f"◌ {len(ergebnis['nicht_abfragbar'])} Repo(s) NICHT abfragbar — keine Aussage"
            )
        return 0

    print(f"# Zeitplan-Wache ueber {ergebnis['geprueft']} Repos\n")
    if still:
        print(f"🚨 {len(still)} Workflow(s) im Zustand `{STILL_ABGESCHALTET}`:\n")
        for e in still:
            print(f"  {e['repo']:<34} {e['workflow']}")
        print(
            "\n→ GitHub schaltet Zeitplaene nach 60 Tagen ohne Repo-Aktivitaet ab.\n"
            '  Reaktivieren: gh workflow enable "<Name>" -R <owner/repo>\n'
            "  Danach VERIFIZIEREN: ein Lauf muss erscheinen — ein reaktivierter\n"
            "  Zeitplan feuert nicht rueckwirkend.\n"
            "  Repos, die NUR Zeitplaene fahren, schalten sich zwangslaeufig wieder ab."
        )
    else:
        print("→ Kein Workflow still abgeschaltet.")

    if ergebnis["von_hand_abgeschaltet"]:
        print(
            f"\n  {len(ergebnis['von_hand_abgeschaltet'])} von HAND abgeschaltet (meist Absicht):"
        )
        for e in ergebnis["von_hand_abgeschaltet"]:
            print(f"    {e['repo']:<34} {e['workflow']}")

    if ergebnis["nicht_abfragbar"]:
        print(
            f"\n  ◌ {len(ergebnis['nicht_abfragbar'])} Repo(s) nicht abfragbar "
            f"(Recht/weg) — darueber sagt dieser Lauf NICHTS: "
            f"{', '.join(ergebnis['nicht_abfragbar'][:5])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
