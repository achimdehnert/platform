#!/usr/bin/env python3
"""Regel-Interpreter für die Mail-Ablage (ADR-284 §7a, Regel-Lebenszyklus).

§7a legt fest, wie eine Ablage-Regel entsteht und wie sie korrigiert wird. Dieses
Modul ist die ausführbare Fassung davon — nicht mehr und nicht weniger:

  1. Eine Regel entsteht **nie still**. Jede neue Regel ist zuerst ein `vorschlag`
     und wirkt erst, wenn der Owner sie ausdrücklich aktiviert.
  2. Zwei Quellen, unterschiedlich stark: eine **Ansage** des Owners gilt sofort,
     eine **Beobachtung** erst ab zwei gleichgerichteten Bewegungen. Ein einzelnes
     Verschieben kann eine Ausnahme sein.
  3. Ein Vorschlag ohne **Rückwirkungs-Trockenlauf** und **Gegenprobe** ist keiner —
     `vorschlag_bauen()` wirft, wenn kein Bestand zum Prüfen übergeben wird.
  4. **Verschieben und Löschen sind nicht symmetrisch.** Aus einer Beobachtung wird
     nie eine Trash-Regel; Löschen ist mehrdeutig ("Rauschen" vs. "erledigt").
  5. Ein **Gegenbeispiel** setzt die Regel auf `strittig` und stoppt sie, statt sie
     automatisch zu verengen — der Widerspruch soll sichtbar bleiben.
  6. Zustände `vorschlag → aktiv → strittig → stillgelegt`; Regeln werden **nicht
     gelöscht**, damit nachvollziehbar bleibt, warum der Bestand so aussieht.
  7. **Jeder Lauf ist rücknehmbar**: protokolliert werden Nachricht, Quellordner,
     Zielordner und die auslösende Regel-ID.
  8. Kennzahl ist die **Restmenge** (was keine Regel traf), nicht die Trefferzahl.

Ablageort der Regeln: `~/.claude/mail-regeln.json` — sie enthalten Absenderadressen
und damit personenbezogene Daten und liegen deshalb **nie im Repo** (ADR-284 §7a).
Dieses Modul liegt versioniert und testbar in `tools/mail_agent/`.

Nachrichten-Form (bewusst entkoppelt von Graph/IMAP, damit prüfbar):
    {"id": str, "absender": str, "betreff": str, "datum": str, "ordner": str}
`aus_graph()` normalisiert eine Graph-Nachricht in diese Form.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REGELN_DATEI = Path.home() / ".claude" / "mail-regeln.json"
PROTOKOLL_DATEI = Path.home() / ".claude" / "mail-regeln-protokoll.jsonl"

ZUSTAENDE = ("vorschlag", "aktiv", "strittig", "stillgelegt")
QUELLEN = ("ansage", "beobachtung")

#: Aktionen, die aus einer Beobachtung abgeleitet werden dürfen. `loeschen` fehlt
#: hier absichtlich (§7a "Verschieben und Löschen sind nicht symmetrisch").
AKTIONEN_AUS_BEOBACHTUNG = ("verschieben", "markieren")
AKTIONEN = AKTIONEN_AUS_BEOBACHTUNG + ("loeschen",)

#: §7a: "nie aus einem Einzelfall; erst ab zwei gleichgerichteten Beobachtungen".
SCHWELLE_BEOBACHTUNG = 2

_WORT = re.compile(r"[a-zäöüß]{4,}")
_RAUSCHEN = frozenset(
    {
        "eine",
        "eines",
        "einer",
        "ihre",
        "ihren",
        "unser",
        "unsere",
        "oder",
        "und",
        "fuer",
        "für",
        "mit",
        "vom",
        "vom",
        "sehr",
        "geehrte",
        "hallo",
        "guten",
        "betreff",
        "info",
        "news",
        "newsletter",
        "nummer",
    }
)


class RegelFehler(ValueError):
    """Ein Schritt widerspricht dem Lebenszyklus aus ADR-284 §7a."""


@dataclass
class Regel:
    regel_id: str
    quelle: str
    aktion: str
    ziel: str
    kriterium: dict
    zustand: str = "vorschlag"
    belege: list = field(default_factory=list)
    historie: list = field(default_factory=list)
    notiz: str = ""

    def __post_init__(self) -> None:
        if self.quelle not in QUELLEN:
            raise RegelFehler(
                f"quelle '{self.quelle}' unbekannt (erlaubt: {', '.join(QUELLEN)})"
            )
        if self.aktion not in AKTIONEN:
            raise RegelFehler(
                f"aktion '{self.aktion}' unbekannt (erlaubt: {', '.join(AKTIONEN)})"
            )
        if self.zustand not in ZUSTAENDE:
            raise RegelFehler(
                f"zustand '{self.zustand}' unbekannt (erlaubt: {', '.join(ZUSTAENDE)})"
            )
        if not self.kriterium:
            raise RegelFehler(
                f"Regel '{self.regel_id}': leeres Kriterium träfe den ganzen Bestand"
            )
        # §7a: Löschen ist mehrdeutig — es kann "Rauschen" heißen oder "erledigt,
        # kann weg". Diese Bedeutungen sind von außen nicht unterscheidbar, also
        # entsteht eine Trash-Regel ausschließlich auf ausdrückliche Ansage.
        if self.aktion == "loeschen" and self.quelle != "ansage":
            raise RegelFehler(
                f"Regel '{self.regel_id}': aktion 'loeschen' nur mit quelle 'ansage' — "
                "aus einem beobachteten Löschvorgang wird nie automatisch eine "
                "Trash-Regel (ADR-284 §7a)."
            )
        if self.quelle == "beobachtung" and len(self.belege) < SCHWELLE_BEOBACHTUNG:
            raise RegelFehler(
                f"Regel '{self.regel_id}': aus Beobachtung abgeleitet, aber nur "
                f"{len(self.belege)} Beleg(e) — nötig sind {SCHWELLE_BEOBACHTUNG} "
                "gleichgerichtete (ADR-284 §7a). Ein Einzelfall kann eine Ausnahme sein."
            )

    def als_text(self) -> str:
        """Die Regel im Klartext — Teil 2 des Vorschlags (§7a)."""
        teile = []
        if v := self.kriterium.get("absender"):
            teile.append(f"Absender ist {v}")
        if v := self.kriterium.get("absender_domain"):
            teile.append(f"Absender-Domain ist {v}")
        if v := self.kriterium.get("betreff_enthaelt"):
            teile.append(f"Betreff enthält '{v}'")
        wenn = " und ".join(teile) or "(kein Kriterium)"
        was = {
            "verschieben": f"nach '{self.ziel}' verschieben",
            "markieren": f"mit '{self.ziel}' markieren",
            "loeschen": "in den Papierkorb",
        }[self.aktion]
        return f"Wenn {wenn}, dann {was}."


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def trifft(regel: Regel, nachricht: dict) -> bool:
    """Alle gesetzten Kriterien müssen passen (UND, nicht ODER)."""
    absender = (nachricht.get("absender") or "").lower()
    betreff = (nachricht.get("betreff") or "").lower()
    k = regel.kriterium
    if (v := k.get("absender")) and absender != v.lower():
        return False
    if (v := k.get("absender_domain")) and not absender.endswith("@" + v.lower()):
        return False
    if (v := k.get("betreff_enthaelt")) and v.lower() not in betreff:
        return False
    return True


# --- Beobachtung → Kandidat -------------------------------------------------


def kandidaten_aus_bewegungen(bewegungen: list[dict]) -> list[dict]:
    """Gleichgerichtete Handbewegungen zu Regel-Kandidaten verdichten.

    Eine Bewegung ist {"absender","betreff","ziel","id",...}. Gleichgerichtet
    heißt: dieselbe Absender-Domain in denselben Zielordner. Erst ab
    SCHWELLE_BEOBACHTUNG entsteht ein Kandidat — darunter bleibt es eine Ausnahme.
    """
    gruppen: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for b in bewegungen:
        absender = (b.get("absender") or "").lower()
        if "@" not in absender or not b.get("ziel"):
            continue
        gruppen[(absender.split("@", 1)[1], b["ziel"])].append(b)
    aus = []
    for (domain, ziel), belege in sorted(gruppen.items()):
        if len(belege) < SCHWELLE_BEOBACHTUNG:
            continue
        aus.append(
            {
                "kriterium": {"absender_domain": domain},
                "aktion": "verschieben",
                "ziel": ziel,
                "belege": belege,
            }
        )
    return aus


def _signatur(betreff: str) -> str:
    """Grobe Betreff-Signatur für die Gruppierung in der Gegenprobe."""
    woerter = [w for w in _WORT.findall((betreff or "").lower()) if w not in _RAUSCHEN]
    return " ".join(woerter[:3]) or "(ohne aussagekräftigen Betreff)"


def trockenlauf(regel: Regel, bestand: list[dict], stichprobe: int = 5) -> dict:
    """Teil 3 des Vorschlags: was die Regel im vorhandenen Bestand getroffen hätte."""
    treffer = [m for m in bestand if trifft(regel, m)]
    return {
        "geprueft": len(bestand),
        "treffer": len(treffer),
        "stichprobe": [
            {
                "betreff": m.get("betreff", ""),
                "absender": m.get("absender", ""),
                "ordner": m.get("ordner", ""),
            }
            for m in treffer[:stichprobe]
        ],
    }


def gegenprobe(regel: Regel, bestand: list[dict], belege: list[dict]) -> dict:
    """Teil 4 des Vorschlags: was die Regel **fälschlich** fangen könnte.

    Realfall 2026-07-27: eine Hoster-Regel hätte 52 Sicherheits- und
    Betriebshinweise im Rechnungsordner begraben — sichtbar wurde das erst durch
    die Stichprobe, nicht durch die Regelformulierung. Deshalb zeigt die
    Gegenprobe genau das, was die Regel trifft, ohne dass der Owner es je von
    Hand bewegt hat, gruppiert nach Betreff-Signatur.
    """
    beobachtet = {b.get("id") for b in belege if b.get("id")}
    treffer = [m for m in bestand if trifft(regel, m)]
    fremd = [m for m in treffer if m.get("id") not in beobachtet]
    gruppen: dict[str, list[dict]] = defaultdict(list)
    for m in fremd:
        gruppen[_signatur(m.get("betreff", ""))].append(m)
    sortiert = sorted(gruppen.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return {
        "treffer": len(treffer),
        "nicht_von_hand_bewegt": len(fremd),
        "anteil_fremd": round(len(fremd) / len(treffer), 3) if treffer else 0.0,
        "gruppen": [
            {"signatur": sig, "anzahl": len(ms), "beispiel": ms[0].get("betreff", "")}
            for sig, ms in sortiert[:5]
        ],
    }


def vorschlag_bauen(
    kandidat: dict,
    bestand: list[dict],
    *,
    regel_id: str,
    quelle: str = "beobachtung",
    notiz: str = "",
) -> dict:
    """Ein Vorschlag mit allen vier Pflichtteilen aus §7a.

    Wirft, wenn kein Bestand übergeben wird: "Ohne diesen Schritt kein Vorschlag."
    """
    if not bestand:
        raise RegelFehler(
            "Vorschlag ohne Rückwirkungs-Trockenlauf ist nach ADR-284 §7a keiner — "
            "Bestand zum Prüfen übergeben."
        )
    regel = Regel(
        regel_id=regel_id,
        quelle=quelle,
        aktion=kandidat["aktion"],
        ziel=kandidat["ziel"],
        kriterium=kandidat["kriterium"],
        zustand="vorschlag",
        belege=kandidat.get("belege", []),
        notiz=notiz,
        historie=[{"zeit": _jetzt(), "zustand": "vorschlag", "grund": "angelegt"}],
    )
    return {
        "regel": regel,
        "beobachtung": [
            {
                "betreff": b.get("betreff", ""),
                "absender": b.get("absender", ""),
                "ziel": b.get("ziel", ""),
                "zeit": b.get("zeit", ""),
            }
            for b in regel.belege
        ],
        "regel_text": regel.als_text(),
        "trockenlauf": trockenlauf(regel, bestand),
        "gegenprobe": gegenprobe(regel, bestand, regel.belege),
    }


# --- Lebenszyklus -----------------------------------------------------------


def _wechsel(regel: Regel, neu: str, grund: str) -> Regel:
    regel.zustand = neu
    regel.historie.append({"zeit": _jetzt(), "zustand": neu, "grund": grund})
    return regel


def aktivieren(regel: Regel, *, bestaetigt: bool) -> Regel:
    """`vorschlag → aktiv`. Nur mit ausdrücklicher Bestätigung des Owners."""
    if regel.zustand != "vorschlag":
        raise RegelFehler(
            f"Regel '{regel.regel_id}' steht auf '{regel.zustand}' — aktiviert wird "
            "nur aus 'vorschlag' (stillgelegte Regeln werden neu vorgeschlagen)."
        )
    if not bestaetigt:
        raise RegelFehler(
            f"Regel '{regel.regel_id}': Aktivierung ohne ausdrückliche Bestätigung. "
            "Es gibt keinen Pfad, auf dem eine Beobachtung unmittelbar zu einer "
            "wirkenden Regel wird (ADR-284 §7a)."
        )
    return _wechsel(regel, "aktiv", "vom Owner bestätigt")


def gegenbeispiel(regel: Regel, beleg: dict) -> Regel:
    """Owner bewegt eine Nachricht zurück oder anders → Regel wird `strittig`.

    Sie wirkt nicht weiter, bis entschieden ist. Eine automatische Verengung
    ("dann eben ohne diesen Absender") ist untersagt — sie ließe den Widerspruch
    verschwinden, statt ihn zu klären.
    """
    if regel.zustand == "stillgelegt":
        raise RegelFehler(
            f"Regel '{regel.regel_id}' ist stillgelegt — kein Gegenbeispiel nötig."
        )
    regel.belege.append({"art": "gegenbeispiel", **beleg})
    return _wechsel(
        regel, "strittig", f"Gegenbeispiel: {beleg.get('betreff', '')[:60]}"
    )


def stilllegen(regel: Regel, grund: str = "") -> Regel:
    return _wechsel(regel, "stillgelegt", grund or "stillgelegt")


def wirksam(regeln: list[Regel]) -> list[Regel]:
    """Nur `aktiv` wirkt. `vorschlag`, `strittig`, `stillgelegt` wirken nicht."""
    return [r for r in regeln if r.zustand == "aktiv"]


# --- Anwenden, Restmenge, Rücknahme ----------------------------------------


def plan(regeln: list[Regel], bestand: list[dict]) -> tuple[list[dict], list[dict]]:
    """(Bewegungen, Restmenge). Die erste treffende aktive Regel gewinnt."""
    aktive = wirksam(regeln)
    bewegungen, rest = [], []
    for m in bestand:
        for r in aktive:
            if trifft(r, m):
                bewegungen.append(
                    {
                        "id": m.get("id"),
                        "betreff": m.get("betreff", ""),
                        "quellordner": m.get("ordner", ""),
                        "zielordner": r.ziel,
                        "aktion": r.aktion,
                        "regel_id": r.regel_id,
                    }
                )
                break
        else:
            rest.append(m)
    return bewegungen, rest


def restmenge(regeln: list[Regel], bestand: list[dict]) -> dict:
    """Kennzahl nach §7a: gemessen wird, was **keine** Regel traf.

    Das ist der Arbeitsvorrat für neue Regeln und zugleich der Beleg, dass nichts
    stumm verschwunden ist. Die Trefferzahl ist ausdrücklich NICHT die Kennzahl.
    """
    bewegungen, rest = plan(regeln, bestand)
    return {
        "bestand": len(bestand),
        "restmenge": len(rest),
        "anteil_rest": round(len(rest) / len(bestand), 3) if bestand else 0.0,
        "von_regeln_getroffen": len(bewegungen),
        "top_absender_im_rest": [
            {"absender": a, "anzahl": n}
            for a, n in sorted(
                _zaehle(rest, "absender").items(), key=lambda kv: (-kv[1], kv[0])
            )[:10]
        ],
    }


def _zaehle(nachrichten: list[dict], feld: str) -> dict[str, int]:
    aus: dict[str, int] = defaultdict(int)
    for m in nachrichten:
        aus[(m.get(feld) or "").lower()] += 1
    return dict(aus)


def protokollieren(bewegungen: list[dict], pfad: Path, lauf_id: str) -> Path:
    """Ohne dieses Protokoll ist ein Rollback im Sinne von §7 nicht möglich."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as fh:
        for b in bewegungen:
            fh.write(
                json.dumps(
                    {"lauf_id": lauf_id, "zeit": _jetzt(), **b}, ensure_ascii=False
                )
                + "\n"
            )
    return pfad


def ruecknahme(pfad: Path, lauf_id: str) -> list[dict]:
    """Umgekehrter Plan zu einem protokollierten Lauf (Ziel ↔ Quelle getauscht)."""
    if not pfad.exists():
        raise RegelFehler(f"Protokoll fehlt: {pfad} — ohne Protokoll keine Rücknahme.")
    aus = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        e = json.loads(zeile)
        if e.get("lauf_id") != lauf_id:
            continue
        aus.append(
            {
                # Nur ein Hinweis, kein Zugriffsschlüssel: sowohl die IMAP-UID
                # als auch die Graph-messageId werden vom Umzug selbst
                # entwertet (gemessen 2026-08-19: ID vorher …AAvAxr8eAAA=,
                # danach …AAwtgyJyAAA=). Wer eine Nachricht zurückholen will,
                # muss sie am Zielort neu auflösen — über Betreff und Datum.
                "id": e.get("id"),
                "konto": e.get("konto"),
                "betreff": e.get("betreff", ""),
                "datum": e.get("datum", ""),
                "quellordner": e.get("zielordner", ""),
                "zielordner": e.get("quellordner", ""),
                "aktion": "verschieben",
                "regel_id": e.get("regel_id"),
                "grund": f"Rücknahme Lauf {lauf_id}",
            }
        )
    if not aus:
        raise RegelFehler(f"Kein Eintrag mit lauf_id '{lauf_id}' in {pfad}.")
    return aus


# --- Persistenz -------------------------------------------------------------


def laden(pfad: str | Path | None = None) -> list[Regel]:
    p = Path(pfad).expanduser() if pfad else REGELN_DATEI
    if not p.exists():
        return []
    daten = json.loads(p.read_text(encoding="utf-8"))
    return [Regel(**r) for r in daten.get("regeln", [])]


def speichern(regeln: list[Regel], pfad: str | Path | None = None) -> Path:
    p = Path(pfad).expanduser() if pfad else REGELN_DATEI
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            {"regeln": [asdict(r) for r in regeln]}, ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(p)
    return p


def aus_graph(m: dict, ordner: str = "") -> dict:
    """Graph-Nachricht → die entkoppelte Form dieses Moduls."""
    absender = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "")
    return {
        "id": m.get("id", ""),
        "absender": absender,
        "betreff": m.get("subject", "") or "",
        # Kopfzeilen-Datum vor Ankunftsstempel — INTERNALDATE/receivedDateTime
        # wird beim Umsortieren neu gesetzt (Lesson 2026-07-28).
        "datum": m.get("sentDateTime") or m.get("receivedDateTime") or "",
        "ordner": ordner,
    }


# --- CLI --------------------------------------------------------------------


def _lies_json(pfad: str) -> list[dict]:
    daten = json.loads(Path(pfad).expanduser().read_text(encoding="utf-8"))
    return daten if isinstance(daten, list) else daten.get("nachrichten", [])


def _zeige_vorschlag(v: dict) -> None:
    r: Regel = v["regel"]
    print(f"\n=== Vorschlag {r.regel_id} ({r.quelle}) ===")
    print(f"2) Regel     : {v['regel_text']}")
    print(f"1) Beobachtung ({len(v['beobachtung'])} Belege):")
    for b in v["beobachtung"][:5]:
        print(
            f'     - {b["zeit"] or "—"}  {b["absender"]}  „{b["betreff"][:50]}" → {b["ziel"]}'
        )
    t = v["trockenlauf"]
    print(f"3) Trockenlauf: {t['treffer']} von {t['geprueft']} Nachrichten getroffen")
    for s in t["stichprobe"]:
        print(f'     - {s["absender"]}  „{s["betreff"][:50]}"  [{s["ordner"]}]')
    g = v["gegenprobe"]
    print(
        f"4) Gegenprobe : {g['nicht_von_hand_bewegt']} Treffer wurden NIE von Hand "
        f"bewegt ({int(g['anteil_fremd'] * 100)} % der Treffer)"
    )
    for gr in g["gruppen"]:
        print(
            f'     - {gr["anzahl"]:4}x  {gr["signatur"]}   z.B. „{gr["beispiel"][:45]}"'
        )
    if g["anteil_fremd"] >= 0.5:
        print(
            "   ACHTUNG: die Mehrheit der Treffer hast du nie selbst bewegt — "
            "genau so hätte die Hoster-Regel 52 Sicherheitshinweise begraben."
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--regeln",
        default=None,
        help="Regel-Datei (Default: ~/.claude/mail-regeln.json)",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("liste", help="Regeln mit Zustand zeigen")

    p_v = sub.add_parser(
        "vorschlag",
        help="aus Handbewegungen Vorschläge bauen (speichert als 'vorschlag')",
    )
    p_v.add_argument(
        "--bewegungen", required=True, help="JSON mit beobachteten Handbewegungen"
    )
    p_v.add_argument(
        "--bestand", required=True, help="JSON mit dem vorhandenen Nachrichtenbestand"
    )
    p_v.add_argument(
        "--speichern",
        action="store_true",
        help="Vorschläge in die Regel-Datei schreiben",
    )

    p_a = sub.add_parser("aktivieren", help="Vorschlag → aktiv (nur mit --bestaetigt)")
    p_a.add_argument("regel_id")
    p_a.add_argument("--bestaetigt", action="store_true")

    p_g = sub.add_parser("gegenbeispiel", help="Regel auf 'strittig' setzen")
    p_g.add_argument("regel_id")
    p_g.add_argument("--betreff", default="")
    p_g.add_argument(
        "--ziel", default="", help="wohin der Owner stattdessen bewegt hat"
    )

    p_s = sub.add_parser("stilllegen", help="Regel stilllegen (wird nicht gelöscht)")
    p_s.add_argument("regel_id")
    p_s.add_argument("--grund", default="")

    p_r = sub.add_parser("restmenge", help="Kennzahl: was keine Regel traf")
    p_r.add_argument("--bestand", required=True)

    p_p = sub.add_parser(
        "plan", help="Bewegungsplan der aktiven Regeln (führt nichts aus)"
    )
    p_p.add_argument("--bestand", required=True)
    p_p.add_argument("--protokoll", default=None)
    p_p.add_argument(
        "--lauf-id", default=None, help="mit --protokoll: Plan protokollieren"
    )

    p_u = sub.add_parser("ruecknahme", help="umgekehrten Plan zu einem Lauf ausgeben")
    p_u.add_argument("--protokoll", default=None)
    p_u.add_argument("--lauf-id", required=True)

    args = ap.parse_args()
    try:
        regeln = laden(args.regeln)

        if args.cmd == "liste":
            if not regeln:
                print("keine Regeln (Datei fehlt oder ist leer)")
            for r in regeln:
                print(f"{r.zustand:12} {r.regel_id:24} {r.quelle:12} {r.als_text()}")

        elif args.cmd == "vorschlag":
            bewegungen = _lies_json(args.bewegungen)
            bestand = _lies_json(args.bestand)
            kandidaten = kandidaten_aus_bewegungen(bewegungen)
            if not kandidaten:
                print(
                    f"Kein Kandidat — keine {SCHWELLE_BEOBACHTUNG} gleichgerichteten "
                    "Beobachtungen. Ein Einzelfall kann eine Ausnahme sein (§7a)."
                )
                return
            bekannt = {r.regel_id for r in regeln}
            neu = []
            for i, k in enumerate(kandidaten, 1):
                rid = f"beob-{k['kriterium']['absender_domain']}-{k['ziel']}".replace(
                    " ", "_"
                ).lower()
                if rid in bekannt:
                    print(f"übersprungen: {rid} existiert bereits")
                    continue
                v = vorschlag_bauen(k, bestand, regel_id=rid)
                _zeige_vorschlag(v)
                neu.append(v["regel"])
            if args.speichern and neu:
                pfad = speichern(regeln + neu, args.regeln)
                print(
                    f"\n{len(neu)} Vorschlag/Vorschläge gespeichert in {pfad} — "
                    "sie wirken NICHT, bis du sie aktivierst."
                )
            elif neu:
                print("\n(nicht gespeichert — mit --speichern übernehmen)")

        elif args.cmd in ("aktivieren", "gegenbeispiel", "stilllegen"):
            treffer = [r for r in regeln if r.regel_id == args.regel_id]
            if not treffer:
                sys.exit(f"FEHLER: Regel '{args.regel_id}' nicht gefunden")
            r = treffer[0]
            if args.cmd == "aktivieren":
                aktivieren(r, bestaetigt=args.bestaetigt)
            elif args.cmd == "gegenbeispiel":
                gegenbeispiel(r, {"betreff": args.betreff, "ziel": args.ziel})
            else:
                stilllegen(r, args.grund)
            speichern(regeln, args.regeln)
            print(f"{r.regel_id}: {r.zustand} — {r.als_text()}")

        elif args.cmd == "restmenge":
            k = restmenge(regeln, _lies_json(args.bestand))
            print(f"Bestand           : {k['bestand']}")
            print(f"Von Regeln erfasst: {k['von_regeln_getroffen']}")
            print(
                f"RESTMENGE         : {k['restmenge']} ({int(k['anteil_rest'] * 100)} %)"
            )
            print("Arbeitsvorrat (häufigste Absender ohne Regel):")
            for e in k["top_absender_im_rest"]:
                print(f"  {e['anzahl']:5}x  {e['absender']}")

        elif args.cmd == "plan":
            bewegungen, rest = plan(regeln, _lies_json(args.bestand))
            for b in bewegungen[:50]:
                print(
                    f"{b['quellordner'] or '—':22} → {b['zielordner']:22} "
                    f'[{b["regel_id"]}]  „{b["betreff"][:40]}"'
                )
            print(
                f"\n{len(bewegungen)} Bewegung(en), Restmenge {len(rest)} — nichts ausgeführt."
            )
            if args.protokoll and args.lauf_id:
                p = protokollieren(
                    bewegungen, Path(args.protokoll).expanduser(), args.lauf_id
                )
                print(f"Protokoll geschrieben: {p} (Lauf {args.lauf_id})")

        elif args.cmd == "ruecknahme":
            pfad = (
                Path(args.protokoll).expanduser() if args.protokoll else PROTOKOLL_DATEI
            )
            for b in ruecknahme(pfad, args.lauf_id):
                print(
                    f'{b["quellordner"]:22} → {b["zielordner"]:22} „{b["betreff"][:40]}"'
                )

    except (RegelFehler, FileNotFoundError, json.JSONDecodeError) as e:
        sys.exit(f"FEHLER: {e}")


if __name__ == "__main__":
    main()
