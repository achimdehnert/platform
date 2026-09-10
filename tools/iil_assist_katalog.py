#!/usr/bin/env python3
"""iil-assist Katalog — Pruefung, Briefing, naechster Schritt, vier Bahnen (platform#3011).

Die Wahrheit liegt in ``docs/konzepte/KONZ-platform-058/iil-assist.yaml``. Dieses
Werkzeug liest sie, prueft sie gegen das Schema (Kriterium 6), erzeugt ein
Briefing, das ein fremdes Modell ohne Chat-Verlauf verstehen kann, leitet den
naechsten Schritt deterministisch aus dem Zustand ab und fuehrt die vier Bahnen
des Regelkreises (Kriterium 7), die ihre Laeufe in dieselbe Datei schreiben.

    validate            Schema + Invarianten (>=10 Dienste, 5 MVPs ueber >=3 Repos, ...)
    briefing            Selbstbeschreibung fuer ein frisches Modell (stdout)
    naechster-schritt   Was jetzt zu tun ist und wer — aus dem Zustand, nicht aus dem Verlauf
    bahn verbesserung   Inventar-Delta + Kennzahlen je Dienst (--inventar <json>)
    bahn wartung        Was kippt als naechstes (Betriebsstatus, Commit-Alter, Lebenszyklus)
    bahn diabolus       Briefing nach ~/shared; Antwortdatei wird eingetragen, wenn sie liegt
    bahn ootb           wie diabolus, Frage: welcher Dienst fehlt

Bahnen schreiben nur mit ``--apply``; ohne Flag zeigen sie den Lauf und lassen die
Datei unangetastet. Datum kommt aus ``--datum`` (Default heute), damit ein Lauf
reproduzierbar ist.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

HIER = Path(__file__).resolve().parent
PLATFORM = HIER.parent
sys.path.insert(0, str(HIER))
import registry_api as reg  # noqa: E402

KATALOG = PLATFORM / "docs" / "konzepte" / "KONZ-platform-058" / "iil-assist.yaml"
PORTS = PLATFORM / "infra" / "ports.yaml"
GITHUB_DIR = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
SHARED = Path.home() / "shared"

REIFEGRAD = {"vorhanden", "teilweise", "neu"}
DATENKLASSE = {"oeffentlich", "intern", "personenbezogen", "mandant"}
CHAT = {"ja", "raum-gebunden", "nein"}
GATE = {"keins", "raum-bindung", "entwurf-freigabe", "budget"}
AUFWAND = {"S", "M", "L"}
STATUS = {"vorgeschlagen", "gewaehlt", "gebaut", "staging", "prod", "ruhend", "eigener-auftrag"}
PHASEN = ["konzept", "auswahl", "bau", "staging", "bilanz"]
BAHNEN = ("verbesserung", "wartung", "diabolus", "ootb")
PFLICHT = ("id", "name", "repo", "reifegrad", "basis", "datenklasse", "chat_eignung",
           "gate", "aufwand", "prio", "mvp", "status", "begruendung")


def lade(pfad: Path = KATALOG) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def speichere(daten: dict, pfad: Path = KATALOG) -> None:
    kopf = []
    for z in pfad.read_text(encoding="utf-8").splitlines():
        if not z.startswith("#"):
            break
        kopf.append(z)
    text = yaml.safe_dump(daten, allow_unicode=True, sort_keys=False, width=100)
    pfad.write_text("\n".join(kopf) + "\n" + text, encoding="utf-8")


# ── validate ────────────────────────────────────────────────────────────────

def pruefe(d: dict) -> list[str]:
    f: list[str] = []
    if d.get("schema") != "iil-assist/1":
        f.append("schema muss iil-assist/1 sein")
    if d.get("phase") not in PHASEN:
        f.append(f"phase muss eine von {PHASEN} sein")
    for k in ("auftrag", "konzept", "name", "architektur", "dienste", "top3", "offen", "proben", "bahnen"):
        if k not in d:
            f.append(f"Feld fehlt: {k}")
    dienste = d.get("dienste") or []
    ids = [x.get("id") for x in dienste]
    if len(set(ids)) != len(ids):
        f.append("Dienst-IDs nicht eindeutig")
    if len(dienste) < 10:
        f.append(f"mindestens 10 Dienste, gefunden {len(dienste)}")
    for x in dienste:
        for k in PFLICHT:
            if k not in x:
                f.append(f"{x.get('id', '?')}: Feld fehlt: {k}")
        for k, menge in (("reifegrad", REIFEGRAD), ("datenklasse", DATENKLASSE), ("chat_eignung", CHAT),
                         ("gate", GATE), ("aufwand", AUFWAND), ("status", STATUS)):
            if x.get(k) not in menge:
                f.append(f"{x.get('id', '?')}: {k}={x.get(k)!r} nicht in {sorted(menge)}")
        if x.get("datenklasse") in ("personenbezogen", "mandant") and x.get("chat_eignung") == "ja":
            f.append(f"{x['id']}: personenbezogen/mandant darf im Chat nicht 'ja' sein (Charta Art. 2)")
        if x.get("datenklasse") in ("personenbezogen", "mandant") and x.get("gate") == "keins":
            f.append(f"{x['id']}: personenbezogen/mandant braucht ein Gate")
        if not isinstance(x.get("prio"), int) or not 1 <= x["prio"] <= 4:
            f.append(f"{x.get('id', '?')}: prio 1..4")
    mvps = [x for x in dienste if x.get("mvp")]
    if len(mvps) != 5:
        f.append(f"genau 5 MVPs, gefunden {len(mvps)}")
    if len({x["repo"] for x in mvps}) < 3:
        f.append("MVPs muessen mindestens 3 Repos decken")
    if not any("iil-assist-core" in " ".join(map(str, x.get("basis", []))) for x in mvps):
        f.append("mindestens ein MVP auf Basis von iil-assist-core")
    top3 = d.get("top3") or []
    if len(top3) != 3 or any(t not in ids for t in top3):
        f.append("top3 muss drei bekannte Dienst-IDs nennen")
    for b in BAHNEN:
        e = (d.get("bahnen") or {}).get(b) or {}
        for k in ("takt", "kommando", "frage", "laeufe"):
            if k not in e:
                f.append(f"bahnen.{b}.{k} fehlt")
    for o in d.get("offen") or []:
        if o.get("wer") not in ("owner", "ich", "ci"):
            f.append(f"offen {o.get('id')}: wer muss owner|ich|ci sein")
    return f


def cmd_validate(args: argparse.Namespace) -> int:
    fehler = pruefe(lade(args.katalog))
    if fehler:
        print("iil-assist: UNGUELTIG")
        for x in fehler:
            print(f"  - {x}")
        return 1
    d = lade(args.katalog)
    print(f"iil-assist: gueltig — {len(d['dienste'])} Dienste, "
          f"{sum(1 for x in d['dienste'] if x['mvp'])} MVPs, Phase {d['phase']}")
    return 0


# ── briefing / naechster Schritt ─────────────────────────────────────────────

def mvp_reihenfolge(d: dict) -> list[dict]:
    """MVPs nach Prio, dann Top-3-Rang, dann ID — dieselbe Reihenfolge fuer Bau und Briefing."""
    top3 = d.get("top3") or []
    rang = {t: i for i, t in enumerate(top3)}
    return sorted((x for x in d["dienste"] if x["mvp"]),
                  key=lambda x: (x["prio"], rang.get(x["id"], len(top3)), x["id"]))


def naechster_schritt(d: dict) -> tuple[str, str]:
    """(wer, was) — deterministisch aus dem Zustand."""
    offen_owner = [o for o in d.get("offen") or [] if o.get("wer") == "owner"]
    if d["phase"] == "konzept":
        return "owner", "Konzept-PR pruefen und die fuenf MVPs bestaetigen oder kippen (offen O1)"
    if offen_owner and d["phase"] == "auswahl":
        return "owner", offen_owner[0]["frage"]
    for x in mvp_reihenfolge(d):
        if x["status"] in ("vorgeschlagen", "gewaehlt"):
            return "ich", f"MVP bauen: {x['name']} ({x['repo']}) — Vertrag, beide Zugaenge, Test je Zugang"
        if x["status"] == "gebaut":
            return "ich", f"MVP auf Staging bringen: {x['name']} ({x['repo']})"
    if d["phase"] != "bilanz":
        return "ich", "Bilanz ziehen: Kennzahlen je MVP, Kill-Gate pruefen, Phase auf bilanz setzen"
    return "owner", "Prod-Freigabe je Dienst (Out of Scope des Auftrags)"


def briefing(d: dict) -> str:
    z = [f"# iil-assist — Briefing (Stand {d['stand']}, Phase {d['phase']})", "",
         f"Auftrag: {d['auftrag']} · Konzept: {d['konzept']}", "",
         "## Was gebaut wird", d["architektur"]["kern"].strip(), "",
         "## Entscheide"]
    for e in d["architektur"]["entscheide"]:
        z.append(f"- {e['id']} [{e['status']}]: {e['text']}")
    z += ["", "## Top 3"]
    for t in d["top3"]:
        x = next(x for x in d["dienste"] if x["id"] == t)
        z.append(f"- {x['name']} ({x['repo']}, {x['datenklasse']}, Gate {x['gate']}): {x['begruendung']}")
    z += ["", "## Die fuenf MVPs"]
    for x in mvp_reihenfolge(d):
        z.append(f"- {x['id']} — {x['name']} ({x['repo']}), Status {x['status']}")
    z += ["", "## Offen"]
    for o in d.get("offen") or []:
        z.append(f"- {o['id']} ({o['wer']}): {o['frage']}")
    wer, was = naechster_schritt(d)
    z += ["", f"## Naechster Schritt ({wer})", was, "",
          "## Name", f"Produkt {d['name']['produkt']} · Repo {d['name']['repo']} · Kern {d['name']['kern']} · "
          f"Alias {d['name']['alias_route']} ({d['name']['alias_status']})"]
    return "\n".join(z) + "\n"


def cmd_briefing(args: argparse.Namespace) -> int:
    print(briefing(lade(args.katalog)), end="")
    return 0


def cmd_naechster(args: argparse.Namespace) -> int:
    wer, was = naechster_schritt(lade(args.katalog))
    print(f"{wer}: {was}")
    return 0


# ── Bahnen ───────────────────────────────────────────────────────────────────

def _commit_alter_tage(repo: str, heute: dt.date) -> int | None:
    wurzel = GITHUB_DIR / repo
    if not (wurzel / ".git").exists():
        return None
    try:
        out = subprocess.run(["git", "-C", str(wurzel), "log", "-1", "--format=%cs"],
                             capture_output=True, text=True, timeout=20, check=True).stdout.strip()
        return (heute - dt.date.fromisoformat(out)).days
    except (subprocess.SubprocessError, ValueError):
        return None


def _betriebsstatus() -> dict[str, str]:
    if not PORTS.exists():
        return {}
    d = yaml.safe_load(PORTS.read_text(encoding="utf-8")) or {}
    return {n: (e or {}).get("betriebsstatus") or "-" for n, e in (d.get("services") or {}).items()}


def bahn_wartung(d: dict, heute: dt.date) -> dict:
    status = _betriebsstatus()
    zeilen = []
    for x in d["dienste"]:
        if x["status"] in ("ruhend", "eigener-auftrag"):
            continue
        e = reg.repo(x["repo"]) or {}
        alter = _commit_alter_tage(x["repo"], heute)
        punkte = 0
        gruende = []
        if status.get(x["repo"]) in ("blockiert", "stillgelegt", "ruhend"):
            punkte += 3
            gruende.append(f"betriebsstatus={status[x['repo']]}")
        if e.get("lifecycle") in ("frozen", "experimental"):
            punkte += 2
            gruende.append(f"lifecycle={e['lifecycle']}")
        if alter is None:
            punkte += 1
            gruende.append("kein Klon")
        elif alter > 60:
            punkte += 2
            gruende.append(f"letzter Commit vor {alter} d")
        zeilen.append({"dienst": x["id"], "punkte": punkte, "gruende": gruende})
    zeilen.sort(key=lambda z: (-z["punkte"], z["dienst"]))
    return {"datum": heute.isoformat(), "kippt_als_naechstes": zeilen[:3], "gemessen": len(zeilen)}


def bahn_verbesserung(d: dict, heute: dt.date, inventar: Path | None) -> dict:
    inv = json.loads(inventar.read_text(encoding="utf-8")) if inventar and inventar.exists() else None
    zeilen = []
    for x in d["dienste"]:
        k = x.get("kennzahlen") or {}
        fund = None
        if inv:
            fund = sum(1 for f in inv["funde"] if f["repo"] == x["repo"])
        zeilen.append({"dienst": x["id"], "status": x["status"], "fundstellen_repo": fund,
                       "test_app": k.get("test_app"), "test_chat": k.get("test_chat"),
                       "antwortzeit_s": k.get("antwortzeit_s"), "nutzungen_30d": k.get("nutzungen_30d")})
    return {"datum": heute.isoformat(), "inventar": str(inventar) if inventar else None, "dienste": zeilen}


def bahn_extern(d: dict, heute: dt.date, bahn: str) -> dict:
    frage = d["bahnen"][bahn]["frage"]
    brief = SHARED / f"iil-assist-{bahn}-{heute.isoformat()}.md"
    antwort = brief.with_name(brief.stem + "-response.md")
    text = (f"# iil-assist — Bahn {bahn} ({heute.isoformat()})\n\n"
            f"Aufgabe: {frage}\n\nAntworte als nummerierte Liste, je Punkt: Befund, Beleg, Konsequenz.\n"
            f"Kandidaten fuer neue Dienste bitte als Zeile `- kandidat: <name> | <repo> | <datenklasse>`.\n\n---\n\n"
            + briefing(d))
    return {"datum": heute.isoformat(), "briefing": str(brief), "briefing_text": text,
            "antwort": str(antwort) if antwort.exists() else None,
            "antwort_kopf": antwort.read_text(encoding="utf-8").splitlines()[0][:160] if antwort.exists() else None}


def cmd_bahn(args: argparse.Namespace) -> int:
    d = lade(args.katalog)
    heute = dt.date.fromisoformat(args.datum) if args.datum else dt.date.today()
    if args.bahn == "wartung":
        lauf = bahn_wartung(d, heute)
    elif args.bahn == "verbesserung":
        lauf = bahn_verbesserung(d, heute, args.inventar)
    else:
        lauf = bahn_extern(d, heute, args.bahn)
    text = lauf.pop("briefing_text", None)
    print(json.dumps(lauf, ensure_ascii=False, indent=1))
    if not args.apply:
        print(f"(Trockenlauf — mit --apply wird der Lauf in {args.katalog.name} eingetragen)", file=sys.stderr)
        return 0
    if text:
        SHARED.mkdir(parents=True, exist_ok=True)
        Path(lauf["briefing"]).write_text(text, encoding="utf-8")
    laeufe = d["bahnen"][args.bahn].setdefault("laeufe", [])
    laeufe[:] = [x for x in laeufe if x.get("datum") != lauf["datum"]] + [lauf]
    d["stand"] = heute.isoformat()
    speichere(d, args.katalog)
    print(f"eingetragen: bahnen.{args.bahn} ({lauf['datum']})", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--katalog", type=Path, default=KATALOG)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("briefing").set_defaults(fn=cmd_briefing)
    sub.add_parser("naechster-schritt").set_defaults(fn=cmd_naechster)
    b = sub.add_parser("bahn")
    b.add_argument("bahn", choices=BAHNEN)
    b.add_argument("--datum", help="YYYY-MM-DD (Default heute)")
    b.add_argument("--inventar", type=Path, help="JSON aus dienst_inventar.py (Bahn verbesserung)")
    b.add_argument("--apply", action="store_true", help="Lauf in die Katalog-Datei schreiben")
    b.set_defaults(fn=cmd_bahn)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
