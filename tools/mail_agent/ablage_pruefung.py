#!/usr/bin/env python3
"""Prueft die Jahrgangs-Ablage eines Postfachs — read-only, IMAP und Graph.

Gegenstueck zu ``archiv_einsortieren.py``: der Einsortierer schreibt, dieses
Werkzeug beurteilt. Bewusst getrennt, damit die Pruefung nicht dieselbe Annahme
benutzt wie der Bau (zirkulaere Selbstverifikation).

**Warum die Kopfzeile und nicht der Ankunftsstempel.** Ein frueherer Entwurf
beurteilte die Ablage ueber ``INTERNALDATE`` bzw. ``receivedDateTime``. Das ist
der Zeitpunkt, zu dem eine Nachricht *in diesem Ordner* ankam — nicht ihr Datum.
Realfall 2026-07-28: eine Nachricht vom 10. Mai 2017 trug in einem Archivordner
den Stempel ``28-Jul-2026``, weil sie am selben Morgen umsortiert worden war. Sie
wurde dadurch als fehlsortiert gemeldet und waere um ein Haar aus einem korrekten
Archiv gerissen worden. Massgeblich ist die ``Date``-Kopfzeile; der Ankunfts-
stempel wird nur noch als **Divergenz-Signal** gefuehrt (Befund F).

**Warum Jahresgrenzen ein eigener Befund sind.** ``Date: Wed, 31 Dec 2025 23:30
+0200`` ist in UTC bereits 2025-12-31 21:30 — dieselbe Nachricht kann je nach
Bezugszeitzone in zwei Jahrgaenge fallen. Solche Faelle sind **mehrdeutig, nicht
falsch**; sie werden getrennt ausgewiesen, damit ein Aufraeumlauf sie nicht als
Fehler verschiebt und dabei mit jedem Durchlauf hin- und herschiebt.

Befundklassen:

===  ==================  =================================================
A    Fehlablage          weder Kopfzeile noch Ankunft passen zum Ordner
B    Nicht archiviert    Vorjahrespost in einem laufenden Ordner
C    Fehlender Ordner    Jahr im Bestand, aber kein Jahrgangsordner
D    Grenzfall           Jahr haengt an der Zeitzone — mehrdeutig
E    Datumslos           keine oder unlesbare Date-Kopfzeile
F    Stempel-Divergenz   Ablage folgt der Kopfzeile, Ankunft wurde neu gesetzt
G    Datum unglaubwuerdig Ablage folgt der Ankunft, Kopfzeile faellt heraus
===  ==================  =================================================

**Warum A und G getrennt sind.** Ein erster Entwurf meldete jede Abweichung
zwischen Kopfzeile und Ordner als Fehlablage. Von 12 so gemeldeten Faellen waren
11 Spam mit **gefaelschter** ``Date``-Kopfzeile — teils Monate in der Zukunft,
einer auf 1988 datiert. Einsortiert worden waren sie korrekt nach Ankunft. Ein
Aufraeumlauf haette daraus einen Ordner ``Archiv/1988`` verlangt und Spam quer
durch das Archiv geschoben. Deshalb gilt: Passt die **Ankunft** zum Ordner und
nur die Kopfzeile nicht, ist die Kopfzeile der Verdaechtige, nicht die Ablage.

Exit-Code: 0 sauber · 1 Befunde der Klasse A/B/C · 2 Werkzeug-/Zugriffsfehler.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOOL_VERSION = "ablage_pruefung.py/1"

#: Ordner, deren Name einen Jahrgang traegt: 'Archiv/2024', 'Sent-Archiv/2019-und-aelter'
JAHRGANG = re.compile(r"^(?P<baum>.+)/(?P<jahr>\d{4})(?P<sammel>-und-(ae|ä)lter)?$")

#: Ordner, in denen laufende Post erwartet wird (Vorjahrespost = Befund B).
LAUFEND = re.compile(
    r"^(INBOX|Posteingang|Gesendete (Objekte|Elemente)|Sent Items|Entw(ü|ue)rfe|Drafts)$",
    re.I,
)

#: Ordner ohne Mail-Inhalt. Termine, Aufgaben und Kontakte tragen keine
#: ``Date``-Kopfzeile — ohne diesen Ausschluss meldete ein Lauf gegen ein echtes
#: Postfach 565 „datumslose" Nachrichten, die schlicht keine Nachrichten sind.
#: Ein Befund, der zu 97 % aus Nicht-Befunden besteht, wird nicht gelesen.
NICHT_MAIL = re.compile(
    r"^(Kalender|Calendar|Aufgaben|Tasks|Kontakte|Contacts|Notizen|Notes|Journal"
    r"|Synchronisierungsprobleme|Sync Issues|RSS)",
    re.I,
)


# ---------- reine Logik ----------


def jahr_und_grenzfall(date_kopf: str | None) -> tuple[int | None, bool]:
    """(Jahr laut Kopfzeile, ist_Grenzfall).

    Grenzfall = das Jahr haengt davon ab, ob man die Ortszeit der Nachricht oder
    UTC zugrunde legt. Genau diese Faelle darf ein Aufraeumlauf nicht als Fehler
    behandeln, sonst schiebt er sie bei jedem Durchlauf erneut.
    """
    if not date_kopf:
        return None, False
    roh = date_kopf.strip()
    try:
        # Graph liefert ISO-8601 ('2017-05-10T07:28:11Z'), IMAP die RFC-5322-Kopfzeile.
        dt = (
            datetime.fromisoformat(roh.replace("Z", "+00:00"))
            if re.match(r"^\d{4}-\d{2}-\d{2}T", roh)
            else parsedate_to_datetime(roh)
        )
    except (TypeError, ValueError, IndexError):
        return None, False
    if dt is None:
        return None, False
    if dt.tzinfo is None:
        return dt.year, False
    return dt.year, dt.year != dt.astimezone(timezone.utc).year


def jahrgang_des_ordners(ordner: str) -> tuple[int, bool] | None:
    """(Jahr, ist_Sammelordner) oder None, wenn der Name keinen Jahrgang traegt."""
    m = JAHRGANG.match(ordner)
    if not m:
        return None
    return int(m.group("jahr")), bool(m.group("sammel"))


def ist_laufender_ordner(ordner: str) -> bool:
    return bool(LAUFEND.match(ordner.split("/")[-1]))


def ist_mail_ordner(ordner: str) -> bool:
    return not any(NICHT_MAIL.match(teil) for teil in ordner.split("/"))


def jahr_ist_abgedeckt(jahr: int, jahrgaenge: set[int], sammel_bis: int | None) -> bool:
    """Gibt es einen Zielordner fuer dieses Jahr?

    Ein Sammelordner ('2019-und-aelter') deckt **alle** Jahre bis zu seiner Zahl ab.
    Ohne diese Regel meldete ein Lauf 13 Nachrichten von 2017 als 'kein
    Jahrgangsordner vorhanden', obwohl genau dafuer einer existiert.
    """
    return jahr in jahrgaenge or (sammel_bis is not None and jahr <= sammel_bis)


def beurteile(
    ordner: str,
    kopf_jahr: int | None,
    grenzfall: bool,
    stempel_jahr: int | None,
    aktuelles_jahr: int,
    bekannte_jahrgaenge: set[int],
    sammel_bis: int | None = None,
) -> list[str]:
    """Alle zutreffenden Befundklassen — eine Nachricht kann mehrere tragen."""
    befunde: list[str] = []

    if kopf_jahr is None:
        return ["E"]

    abweichend = stempel_jahr is not None and stempel_jahr != kopf_jahr

    jg = jahrgang_des_ordners(ordner)
    if jg is not None:
        jahr, sammel = jg
        passt = kopf_jahr <= jahr if sammel else kopf_jahr == jahr
        stempel_passt = stempel_jahr is not None and (
            stempel_jahr <= jahr if sammel else stempel_jahr == jahr
        )
        if passt:
            if abweichend:
                befunde.append("F")
        elif stempel_passt:
            # Die Ablage folgt dem Ankunftsdatum, und nur die Kopfzeile fällt aus
            # der Reihe. Realfall 2026-07-28: 11 von 12 vermeintlichen Fehlablagen
            # waren Spam mit gefaelschtem Date — teils Monate in der Zukunft. Als
            # Fehlablage gemeldet, haette ein Aufraeumlauf Ordner wie 'Archiv/1988'
            # verlangt und Spam quer durch das Archiv geschoben.
            befunde.append("G")
        else:
            befunde.append("D" if grenzfall else "A")
        return befunde

    if abweichend:
        befunde.append("F")
    if ist_laufender_ordner(ordner) and kopf_jahr < aktuelles_jahr:
        befunde.append("D" if grenzfall else "B")
        if not jahr_ist_abgedeckt(kopf_jahr, bekannte_jahrgaenge, sammel_bis):
            befunde.append("C")

    return befunde


# ---------- Transporte ----------


_LIST = re.compile(rb'^\([^)]*\)\s+(?:"[^"]*"|NIL)\s+(?:"(?P<q>[^"]*)"|(?P<u>\S+))\s*$')
_UID = re.compile(rb"UID (\d+)")
_INTDATE = re.compile(rb'INTERNALDATE "\d{2}-\w{3}-(\d{4})')
_MESSAGES = re.compile(rb"MESSAGES\s+(\d+)")


class ImapQuelle:
    """IMAP. UID wird ausdruecklich mit angefordert — Exchange liefert sie sonst
    nicht mit, und ein darauf aufbauender Filter gibt still eine leere Menge
    zurueck (error_pattern platform:20260728-exchange-uid)."""

    def __init__(self, konto: str):
        from read_mail import _resolve_config, connect
        from send_mail import parse_env

        self.imap = connect(parse_env(_resolve_config(None, konto)))
        self.name = f"IMAP {konto}"

    def ordner(self) -> list[str]:
        typ, res = self.imap.list()
        aus = []
        if typ == "OK":
            for z in res or []:
                m = _LIST.match(z) if z else None
                if m:
                    roh = m.group("q") if m.group("q") is not None else m.group("u")
                    aus.append(roh.decode("utf-8", "replace"))
        return aus

    def laut_server(self, ordner: str) -> int | None:
        try:
            typ, res = self.imap.status(f'"{ordner}"', "(MESSAGES)")
        except Exception:
            return None
        m = _MESSAGES.search(res[0]) if typ == "OK" and res and res[0] else None
        return int(m.group(1)) if m else None

    def nachrichten(self, ordner: str):
        """[(kennung, date_kopf, stempel_jahr)]"""
        try:
            typ, res = self.imap.select(f'"{ordner}"', readonly=True)
        except Exception:
            return []
        if typ != "OK":
            return []
        anzahl = int(res[0])
        aus = []
        for start in range(1, anzahl + 1, 500):
            ende = min(start + 499, anzahl)
            try:
                typ, daten = self.imap.fetch(
                    f"{start}:{ende}",
                    "(UID INTERNALDATE BODY.PEEK[HEADER.FIELDS (DATE)])",
                )
            except Exception:
                continue
            if typ != "OK":
                continue
            for teil in daten or []:
                if not isinstance(teil, tuple) or len(teil) < 2:
                    continue
                kopfteil, rumpf = teil[0], teil[1]
                uid = _UID.search(kopfteil or b"")
                stempel = _INTDATE.search(kopfteil or b"")
                zeile = (rumpf or b"").decode("utf-8", "replace").strip()
                datum = zeile[5:].strip() if zeile.lower().startswith("date:") else None
                aus.append(
                    (
                        uid.group(1).decode() if uid else "?",
                        datum,
                        int(stempel.group(1)) if stempel else None,
                    )
                )
        return aus

    def schliessen(self):
        try:
            self.imap.logout()
        except Exception:
            pass


class GraphQuelle:
    def __init__(self):
        from graph_mail import GRAPH, _auth, _http, load_cfg, token

        self._G, self._auth, self._http = GRAPH, _auth, _http
        cfg = load_cfg()
        self.konto = cfg["accounts"][0]
        self.tok = token(cfg, self.konto)
        if not self.tok:
            raise SystemExit("kein gueltiges Token — graph_mail.py --login <konto>")
        self.name = f"Graph {self.konto}"
        self._idx: dict[str, tuple[str, int]] = {}

    def _laden(self):
        if self._idx:
            return

        def walk(pid, prefix):
            url = (
                f"{self._G}/me/mailFolders"
                if pid is None
                else f"{self._G}/me/mailFolders/{pid}/childFolders"
            )
            url += "?$top=100&$select=id,displayName,childFolderCount,totalItemCount"
            while url:
                r = self._http("GET", url, headers=self._auth(self.tok)).json()
                for f in r.get("value", []):
                    p = (
                        f["displayName"]
                        if not prefix
                        else f"{prefix}/{f['displayName']}"
                    )
                    self._idx[p] = (f["id"], f.get("totalItemCount", 0))
                    if f.get("childFolderCount", 0):
                        walk(f["id"], p)
                url = r.get("@odata.nextLink")

        walk(None, "")

    def ordner(self) -> list[str]:
        self._laden()
        return list(self._idx)

    def laut_server(self, ordner: str) -> int | None:
        self._laden()
        eintrag = self._idx.get(ordner)
        return eintrag[1] if eintrag else None

    def nachrichten(self, ordner: str):
        self._laden()
        eintrag = self._idx.get(ordner)
        if not eintrag:
            return []
        # `sentDateTime` statt `internetMessageHeaders`: letzteres ist ein schweres
        # Feld — ein Lauf ueber 40.000 Nachrichten lief damit in die Zeitgrenze.
        # `sentDateTime` traegt dieselbe Aussage wie die Date-Kopfzeile; an einer
        # Stichprobe von 24 Nachrichten mit Date-Kopf stimmten 24 ueberein, 0 wichen
        # ab. `receivedDateTime` bleibt der Ankunftsstempel (Divergenz-Signal).
        url = (
            f"{self._G}/me/mailFolders/{eintrag[0]}/messages"
            "?$top=999&$select=id,sentDateTime,receivedDateTime"
        )
        aus = []
        while url:
            r = self._http("GET", url, headers=self._auth(self.tok)).json()
            for m in r.get("value", []):
                empfangen = (m.get("receivedDateTime") or "")[:4]
                aus.append(
                    (
                        # Graph-Kennungen teilen sich einen langen Praefix — ein
                        # Kopf-Ausschnitt sieht bei allen gleich aus und macht die
                        # Beispiele im Bericht unbrauchbar. Das Ende unterscheidet.
                        m["id"][-20:],
                        m.get("sentDateTime"),
                        int(empfangen) if empfangen.isdigit() else None,
                    )
                )
            url = r.get("@odata.nextLink")
        return aus

    def schliessen(self):
        pass


# ---------- Bericht ----------

TEXTE = {
    "A": "Fehlablage — weder Kopfzeile noch Ankunft passen zum Ordner",
    "B": "nicht archiviert — Vorjahrespost in laufendem Ordner",
    "C": "fehlender Jahrgangsordner fuer dieses Jahr",
    "D": "Grenzfall — Jahr haengt an der Zeitzone, mehrdeutig",
    "E": "datumslos — keine oder unlesbare Date-Kopfzeile",
    "F": "Stempel-Divergenz — Ablage folgt der Kopfzeile, Ankunft neu gesetzt",
    "G": "Datum unglaubwuerdig — Ablage folgt der Ankunft, Kopfzeile faellt heraus",
}
HART = ("A", "B", "C")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--imap-konto", dest="imap_konto", help="IMAP-Kontokuerzel")
    ap.add_argument("--graph", action="store_true", help="Microsoft-365-Konto")
    ap.add_argument("--ordner", action="append", help="nur diese Ordner (mehrfach)")
    ap.add_argument("--details", type=int, default=5, help="Beispiele je Befund")
    args = ap.parse_args()

    if bool(args.imap_konto) == bool(args.graph):
        sys.exit("genau eines von --imap-konto / --graph angeben")

    quelle = ImapQuelle(args.imap_konto) if args.imap_konto else GraphQuelle()
    alle = quelle.ordner()
    gewaehlt = [o for o in alle if not args.ordner or o in args.ordner]
    zu_pruefen = [o for o in gewaehlt if ist_mail_ordner(o)]
    uebersprungen = [o for o in gewaehlt if not ist_mail_ordner(o)]
    jahrgaenge, sammel_bis = set(), None
    for o in alle:
        if (jg := jahrgang_des_ordners(o)) is not None:
            jahrgaenge.add(jg[0])
            if jg[1]:
                sammel_bis = max(sammel_bis or 0, jg[0])
    aktuelles_jahr = datetime.now(timezone.utc).year

    print(f"=== Ablage-Pruefung · {quelle.name} · {TOOL_VERSION} ===")
    print(
        f"    {len(zu_pruefen)} von {len(alle)} Ordner(n) geprueft, "
        f"{len(uebersprungen)} ohne Mail-Inhalt uebersprungen"
    )
    print(
        f"    Jahrgaenge {min(jahrgaenge, default='-')}–"
        f"{max(jahrgaenge, default='-')}"
        f"{f' (Sammelordner bis {sammel_bis})' if sammel_bis else ''}, "
        f"laufendes Jahr {aktuelles_jahr}\n"
    )

    zaehler: Counter = Counter()
    beispiele: dict[str, list[str]] = defaultdict(list)
    gelesen = laut_server = 0
    ungleich: list[str] = []

    for o in sorted(zu_pruefen):
        posten = quelle.nachrichten(o)
        gelesen += len(posten)
        n = quelle.laut_server(o)
        if n is not None:
            laut_server += n
            if n != len(posten):
                ungleich.append(f"{o}: Server {n}, gelesen {len(posten)}")
        for kennung, datum, stempel in posten:
            jahr, grenze = jahr_und_grenzfall(datum)
            for b in beurteile(
                o, jahr, grenze, stempel, aktuelles_jahr, jahrgaenge, sammel_bis
            ):
                zaehler[b] += 1
                if len(beispiele[b]) < args.details:
                    beispiele[b].append(f"{o} · {kennung} · {datum or '(ohne Datum)'}")

    print(f"    gelesen {gelesen}, laut Server {laut_server}")
    if ungleich:
        print(f"    ⚠ Nenner uneinig in {len(ungleich)} Ordner(n):")
        for z in ungleich[:10]:
            print(f"        {z}")
    print()

    if not zaehler:
        print("  ✓ keine Befunde")
    for b in sorted(zaehler):
        marke = "✗" if b in HART else "·"
        print(f"  {marke} {b}  {zaehler[b]:>6}  {TEXTE[b]}")
        for z in beispiele[b]:
            print(f"            {z}")

    quelle.schliessen()
    sys.exit(1 if any(zaehler[b] for b in HART) else 0)


if __name__ == "__main__":
    main()
