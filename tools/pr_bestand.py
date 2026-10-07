#!/usr/bin/env python3
"""PR-Bestand ueber alle Orgs messen — Alter, Quelle, Trend (#3812 K4).

Anlass: Am 2026-10-06 lagen 177 offene PRs in den vier Orgs. Den Abbau hat eine
Sitzung von Hand inventarisiert (Skripte im Scratchpad, danach weg). Dieses
Modul macht die Messung wiederholbar, damit die naechste Sitzung nicht wieder
bei null anfaengt und ein neuer Stau sichtbar wird, **bevor** er 177 erreicht.

Gemessen wird nur, was `gh search prs` liefert (eine Abfrage je Org, keine
Einzelabfrage je PR): Anzahl, Alter, Quelle. Die Quelle ordnet jeden PR einem
Erzeuger zu, damit der Trend auf den Erzeuger zeigt, nicht nur auf die Summe.
CI-Stand und Mandat je PR bleiben bei `pr_merge_sa.py --dry-run`.

Jeder Lauf haengt einen Schnappschuss an das Journal an (`--journal`). Aus dem
aeltesten Schnappschuss der letzten 28 Tage und dem aktuellen entsteht der
Trend je Woche. Unter 7 Tagen Abstand gibt es keinen Trend, sondern die Zeile
`SAMMELPHASE` — ungemessen ist keine Entwarnung.

    python3 tools/pr_bestand.py                      # alle Orgs, Journal schreiben
    python3 tools/pr_bestand.py --kein-journal       # nur anzeigen
    python3 tools/pr_bestand.py --eingabe prs.json   # Fixture statt gh (Tests)
    python3 tools/pr_bestand.py --lesen              # nur Journal lesen, eine Zeile

Ausgabe: eine Tabelle je Erzeuger, danach genau eine Bewertungszeile
`OK|WARN|SAMMELPHASE: ...`. Exit immer 0 — der Melder ist advisory; fehlt `gh`
oder das Netz, steht `nicht pruefbar: <grund>` da.

Gemessen wird woechentlich vom Timer `pr-bestand.timer` (#3823 K1). Der
Sitzungsstart misst nicht selbst, sondern liest mit `--lesen` den juengsten
Schnappschuss aus dem Journal, ohne Netzzugriff (#3823 K2). Exit bei `--lesen`:
0 OK oder SAMMELPHASE, 1 WARN, 2 kein frischer Schnappschuss (Timer steht).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ORGS = ("achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra")
JOURNAL = Path.home() / ".claude" / "pr-bestand-journal.jsonl"
ALT_TAGE = 30
# Ab so vielen PRs ueber ALT_TAGE wird gewarnt: gemessen 2026-10-06 nach dem
# Abbau 39 von 105, jeder mit Grund im Ledger von #3812. Mehr heisst neuer Stau.
SCHWELLE_ALT = 40
TREND_FENSTER_TAGE = 28
TREND_MIN_TAGE = 7
# Der Timer misst woechentlich; ein Tag Spielraum fuer einen verpassten Lauf.
LESEN_MAX_ALTER_TAGE = 8
FELDER = "number,title,author,createdAt,updatedAt,repository,isDraft,url"

PROJECT_FACTS = re.compile(r"project[-_ ]facts", re.I)


def erzeuger(pr: dict) -> str:
    """Ordnet einen PR seiner Quelle zu; die Reihenfolge der Regeln zaehlt."""
    login = (pr.get("author") or {}).get("login", "").lower()
    titel = pr.get("title", "")
    if PROJECT_FACTS.search(titel):
        return "project-facts"
    if "dependabot" in login:
        return "dependabot"
    if "renovate" in login:
        return "renovate"
    if (pr.get("author") or {}).get("is_bot") or login.endswith("[bot]") or login.startswith("app/"):
        return "bot-sonstige"
    return "mensch"


def alter_tage(pr: dict, jetzt: datetime) -> int:
    erstellt = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
    return (jetzt - erstellt).days


def lade_live(orgs: tuple[str, ...]) -> list[dict]:
    prs: list[dict] = []
    for org in orgs:
        roh = subprocess.run(
            ["gh", "search", "prs", "--owner", org, "--state", "open", "--archived=false",
             "--limit", "1000", "--json", FELDER],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
        prs += json.loads(roh or "[]")
    return prs


def schnappschuss(prs: list[dict], jetzt: datetime) -> dict:
    je: dict[str, Counter] = {}
    for pr in prs:
        c = je.setdefault(erzeuger(pr), Counter())
        c["offen"] += 1
        if alter_tage(pr, jetzt) > ALT_TAGE:
            c["alt"] += 1
    return {
        "zeit": jetzt.isoformat(timespec="seconds"),
        "offen": len(prs),
        "alt": sum(c["alt"] for c in je.values()),
        "je_erzeuger": {k: dict(v) for k, v in sorted(je.items())},
    }


def lies_journal(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    zeilen = []
    for z in pfad.read_text(encoding="utf-8").splitlines():
        try:
            zeilen.append(json.loads(z))
        except json.JSONDecodeError:
            continue
    return zeilen


def bewertung(aktuell: dict, frueher: list[dict]) -> str:
    jetzt = datetime.fromisoformat(aktuell["zeit"])
    fenster = [s for s in frueher
               if timedelta(days=TREND_MIN_TAGE) <= jetzt - datetime.fromisoformat(s["zeit"])
               <= timedelta(days=TREND_FENSTER_TAGE)]
    alt_teil = f"{aktuell['alt']} PRs aelter als {ALT_TAGE} Tage (Schwelle {SCHWELLE_ALT})"
    if not fenster:
        stufe = "WARN" if aktuell["alt"] > SCHWELLE_ALT else "SAMMELPHASE"
        return f"{stufe}: {alt_teil}; Trend erst ab {TREND_MIN_TAGE} Tagen Journal"
    basis = min(fenster, key=lambda s: s["zeit"])
    tage = (jetzt - datetime.fromisoformat(basis["zeit"])).total_seconds() / 86400
    je_woche = (aktuell["offen"] - basis["offen"]) / tage * 7
    treiber = []
    for name, werte in aktuell["je_erzeuger"].items():
        vorher = basis.get("je_erzeuger", {}).get(name, {}).get("offen", 0)
        if werte.get("offen", 0) > vorher:
            treiber.append(f"{name} +{werte['offen'] - vorher}")
    trend = f"Bestand {je_woche:+.1f}/Woche seit {basis['zeit'][:10]}"
    if treiber:
        trend += " (" + ", ".join(treiber) + ")"
    stufe = "WARN" if je_woche > 0 or aktuell["alt"] > SCHWELLE_ALT else "OK"
    return f"{stufe}: {alt_teil}; {trend}"


def zeile_lesen(journal: list[dict], jetzt: datetime) -> tuple[int, str]:
    """Juengsten Schnappschuss gegen die frueheren bewerten — eine Zeile, kein Netz."""
    if not journal:
        return 2, "kein Journal (pr-bestand.timer installiert? README host-maintenance)"
    letzter = journal[-1]
    gemessen = datetime.fromisoformat(letzter["zeit"])
    if jetzt - gemessen > timedelta(days=LESEN_MAX_ALTER_TAGE):
        return 2, f"Journal veraltet (letzter Schnappschuss {letzter['zeit'][:10]}), Timer steht"
    text = bewertung(letzter, journal[:-1])
    return (1 if text.startswith("WARN") else 0), f"{text} · gemessen {letzter['zeit'][:10]}"


def tabelle(s: dict) -> str:
    zeilen = ["| Erzeuger | offen | aelter als %d Tage |" % ALT_TAGE, "|---|---|---|"]
    for name, werte in s["je_erzeuger"].items():
        zeilen.append(f"| {name} | {werte.get('offen', 0)} | {werte.get('alt', 0)} |")
    zeilen.append(f"| **Summe** | **{s['offen']}** | **{s['alt']}** |")
    return "\n".join(zeilen)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--org", action="append", help="Org (mehrfach); Default: alle vier")
    p.add_argument("--eingabe", type=Path, help="JSON-Liste im Format von gh search prs")
    p.add_argument("--journal", type=Path, default=JOURNAL)
    p.add_argument("--kein-journal", action="store_true")
    p.add_argument("--jetzt", help="ISO-Zeit statt der Uhr (Tests)")
    p.add_argument("--lesen", action="store_true", help="nur Journal lesen, eine Zeile (Sitzungsstart)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    jetzt = datetime.fromisoformat(args.jetzt) if args.jetzt else datetime.now(timezone.utc)
    if args.lesen:
        rc, text = zeile_lesen(lies_journal(args.journal), jetzt)
        print(text)
        return rc
    try:
        if args.eingabe:
            prs = json.loads(args.eingabe.read_text(encoding="utf-8"))
        else:
            prs = lade_live(tuple(args.org) if args.org else ORGS)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
        print(f"nicht pruefbar: {type(fehler).__name__}: {fehler}")
        return 0
    aktuell = schnappschuss(prs, jetzt)
    frueher = [] if args.kein_journal else lies_journal(args.journal)
    print(tabelle(aktuell))
    print(bewertung(aktuell, frueher))
    if not args.kein_journal:
        args.journal.parent.mkdir(parents=True, exist_ok=True)
        with args.journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(aktuell, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
