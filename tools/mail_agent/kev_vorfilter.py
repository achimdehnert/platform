#!/usr/bin/env python3
"""kev-Vorfilter fuer Rechnungsmails (platform#3337) — READ-ONLY.

Die Rechnungsstrecke (`rechnungsstrecke.py`) findet Rechnungsmails heute per
Stichwortliste (Rechnung, Invoice, receipt, Beleg, Quittung). Ein Handlauf
(https://github.com/achimdehnert/platform/issues/3337#issuecomment-5792571756)
zeigte: das lokale Entscheidungsmodell kev-4b erkennt sie treffsicherer —
bei Schwelle 0,7 Praezision 1,0, waehrend die Stichwortliste 19 Fehlalarme
produzierte. Dieses Werkzeug liefert dem Owner eine Kandidatenliste, es
VERSCHIEBT, BUCHT und SENDET NICHTS.

kev laeuft als Nutzerdienst auf der gx10 und lauscht NUR auf 127.0.0.1:8009
dort — erreichbar per SSH ueber den Prod-Hop, genau wie in jev_messreihe.py.
Ein kleines Remote-Skript wird je Lauf per stdin abgelegt (umask 077),
bekommt die Mails als JSONL per stdin, liefert die kev-Antworten per stdout
zurueck und wird danach wieder geloescht — es bleibt nichts auf der gx10.

Aufruf:
  python3 tools/mail_agent/kev_vorfilter.py
  python3 tools/mail_agent/kev_vorfilter.py --ordner Posteingang --tage 60 --schwelle 0.7
  python3 tools/mail_agent/kev_vorfilter.py --json

Fehlerfaelle (gx10/kev nicht erreichbar, Ordner unbekannt, Graph-Zugriff
verweigert) brechen laut mit Exit-Code != 0 ab — NIE eine leere Liste als
Erfolg (siehe `_daten` in graph_mail.py: Nichtzugriff ist nicht Nichts).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph_mail import _auth, _basis, _daten, _http, find_folder, load_cfg, token  # noqa: E402

# Der Hop zur gx10 (hetzner-prod -> 10.99.0.4) UND der `_ssh`-Transport werden
# aus jev_messreihe.py wiederverwendet statt ein zweites Mal hartkodiert zu
# werden — beide Werkzeuge sprechen denselben Knoten (#3337).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev_messreihe import HEIM, _ssh  # noqa: E402

#: Ordner-Aliasse, die den well-known-Ordner "inbox" meinen (wie
#: rausch_kandidaten.POSTEINGANG_PRAEFIXE).
POSTEINGANG_ALIASSE = ("posteingang", "inbox", "")

ORDNER_STANDARD = "Posteingang"
TAGE_STANDARD = 60
SCHWELLE_STANDARD = 0.7

#: kev-Modell und Frage exakt wie im Handlauf gemessen — eine andere
#: Formulierung waere ein anderes Messergebnis.
KEV_MODELL = "kev-latest"
FRAGE_SCHLUESSEL = "rechnung"
FRAGE_INSTRUKTION = (
    "Diese E-Mail übermittelt dem Empfänger eine Rechnung, Quittung oder "
    "einen Zahlungsbeleg, der verbucht werden muss."
)

#: Name der Datei, die je Lauf auf der gx10 abgelegt und danach wieder
#: geloescht wird (kein Datei-Ueberbleibsel wie bei jev_messreihe).
REMOTE_SKRIPT_NAME = "kev_vorfilter_remote.py"

#: Winziges, stdlib-only Remote-Skript: liest JSONL von stdin
#: ({"id": ..., "body": {...}}), ruft kev lokal (127.0.0.1:8009) auf und
#: gibt je Zeile ein Ergebnis als JSONL auf stdout zurueck.
_REMOTE_SKRIPT = '''#!/usr/bin/env python3
"""Von kev_vorfilter.py auf der gx10 abgelegt, ausgefuehrt und geloescht."""
import json
import sys
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8009/v1/systemone"

for zeile in sys.stdin:
    zeile = zeile.strip()
    if not zeile:
        continue
    eingabe = json.loads(zeile)
    ausgabe = {"id": eingabe.get("id")}
    try:
        daten = json.dumps(eingabe["body"]).encode("utf-8")
        anfrage = urllib.request.Request(
            URL, data=daten, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            ausgabe["antwort"] = json.loads(antwort.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        ausgabe["fehler"] = str(exc)
    print(json.dumps(ausgabe, ensure_ascii=False))
    sys.stdout.flush()
'''


def zustandstext(name: str, adresse: str, betreff: str, anhang: bool, text: str) -> str:
    """Baut den Zustandstext, gegen den kev gemessen wurde — Format ist fix.

    `text` (Graph `bodyPreview`) kommt mit eingebetteten Zeilenumbruechen und
    doppelten Leerzeichen — die werden zu einfachen Leerzeichen eingedampft,
    damit der Zustandstext genau vier Zeilen hat.
    """
    einzeilig = " ".join((text or "").split())
    return (
        f"Absender: {name} {adresse}\n"
        f"Betreff: {betreff}\n"
        f"Anhang: {'ja' if anhang else 'nein'}\n"
        f"Text: {einzeilig}"
    )


def kev_body(text: str) -> dict:
    """Der POST-Koerper fuer kev — Frageform exakt wie im Handlauf gemessen."""
    return {
        "state": text,
        "model": KEV_MODELL,
        "questions": {
            FRAGE_SCHLUESSEL: {"type": "noul", "instructions": FRAGE_INSTRUKTION}
        },
    }


def mails_holen(tok: str, ordner_id: str, tage: int) -> list[dict]:
    """Mails eines Ordners der letzten `tage` Tage, mit @odata.nextLink verfolgt."""
    seit = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(time.time() - tage * 86400))
    url = (
        f"{_basis()}/mailFolders/{ordner_id}/messages?$top=100"
        "&$select=id,subject,from,bodyPreview,hasAttachments,receivedDateTime"
        f"&$filter=receivedDateTime ge {seit}"
    )
    mails: list[dict] = []
    while url:
        r = _http("GET", url, headers=_auth(tok))
        j = _daten(r, "Mails fuer kev-Vorfilter laden")
        mails.extend(j.get("value", []))
        url = j.get("@odata.nextLink")
    return mails


def frage_kev(anfragen: list[tuple[str, dict]]) -> list[dict] | None:
    """Schickt <id, body>-Paare an kev auf der gx10, liest die Antworten zurueck.

    None, wenn irgendein Schritt nicht traegt: Ablage des Remote-Skripts,
    der Lauf selbst, eine abweichende Zeilenzahl oder eine Antwort ohne
    Ergebnis. Ein nicht erreichbarer Dienst ist ein Befund ueber den Dienst,
    kein Teilergebnis — dieselbe Haltung wie `jev_messreihe.frage_modell`.
    """
    if not anfragen:
        return []
    pfad = f"{HEIM}/{REMOTE_SKRIPT_NAME}"
    try:
        ablage = _ssh(f"umask 077 && cat > {pfad}", eingabe=_REMOTE_SKRIPT)
        if ablage.returncode != 0:
            return None
        eingabe = (
            "\n".join(
                json.dumps({"id": mid, "body": body}, ensure_ascii=False)
                for mid, body in anfragen
            )
            + "\n"
        )
        lauf = _ssh(f"python3 {pfad}", eingabe=eingabe)
    finally:
        _ssh(f"rm -f {pfad}")  # Aufraeumen unabhaengig vom Ausgang des Laufs
    if lauf.returncode != 0:
        return None
    zeilen = [z for z in lauf.stdout.splitlines() if z.strip()]
    if len(zeilen) != len(anfragen):
        return None
    ergebnisse = []
    for z in zeilen:
        try:
            geparst = json.loads(z)
        except json.JSONDecodeError:
            return None
        if "antwort" not in geparst:
            return None
        ergebnisse.append(geparst)
    return ergebnisse


def werte_extrahieren(
    ergebnisse: list[dict],
) -> tuple[dict[str, float], list[float]] | None:
    """kev-Antworten -> {id: Wert} + Liste der Latenzen. None bei jeder Luecke."""
    werte: dict[str, float] = {}
    latenzen: list[float] = []
    for e in ergebnisse:
        try:
            wert = float(e["antwort"]["answers"][FRAGE_SCHLUESSEL]["noul"])
        except (KeyError, TypeError, ValueError):
            return None
        werte[e["id"]] = wert
        latenz = e["antwort"].get("latency_ms")
        if isinstance(latenz, int | float):
            latenzen.append(float(latenz))
    return werte, latenzen


def vorfilter_lauf(tok: str, ordner: str, tage: int, schwelle: float) -> dict:
    """Kernlogik ohne argparse: Mails holen, kev fragen, Kandidaten bauen.

    `sys.exit` bei jedem Fehlerfall (Ordner unbekannt, kev nicht erreichbar,
    Antwort unvollstaendig) — kein Rueckgabewert deutet einen Fehler als
    Erfolg um.
    """
    ordner_id = (
        "inbox"
        if ordner.strip().lower() in POSTEINGANG_ALIASSE
        else find_folder(tok, ordner)
    )
    if not ordner_id:
        sys.exit(f"FEHLER: Ordner '{ordner}' nicht gefunden.")

    mails = mails_holen(tok, ordner_id, tage)
    if not mails:
        return {
            "kandidaten": [],
            "nur_link": [],
            "geprueft": 0,
            "median_latenz_ms": None,
        }

    anfragen: list[tuple[str, dict]] = []
    metadaten: dict[str, dict] = {}
    for m in mails:
        em = (m.get("from") or {}).get("emailAddress") or {}
        text = zustandstext(
            em.get("name", ""),
            em.get("address", ""),
            m.get("subject") or "",
            bool(m.get("hasAttachments")),
            m.get("bodyPreview") or "",
        )
        mid = m["id"]
        anfragen.append((mid, kev_body(text)))
        metadaten[mid] = {
            "datum": m.get("receivedDateTime", ""),
            "absenderadresse": em.get("address", ""),
            "betreff": m.get("subject") or "",
            "anhang": bool(m.get("hasAttachments")),
        }

    ergebnisse = frage_kev(anfragen)
    if ergebnisse is None:
        sys.exit(
            "FEHLER: kev nicht erreichbar (gx10 ueber den Prod-Hop) — "
            "kein Ergebnis, keine Kandidatenliste."
        )
    extrahiert = werte_extrahieren(ergebnisse)
    if extrahiert is None:
        sys.exit("FEHLER: kev-Antwort unvollstaendig/unerwartet — kein Ergebnis.")
    werte, latenzen = extrahiert

    treffer = [
        {"wert": round(w, 3), **metadaten[mid], "id": mid}
        for mid, w in werte.items()
        if w >= schwelle
    ]
    treffer.sort(key=lambda k: k["wert"], reverse=True)
    # Owner-Regel 2026-09-23: „Rechnung ist IMMER eigenes PDF". Eine Mail ohne
    # Anhang ist keine Rechnung, sondern ein Hinweis darauf — sie landet in
    # `nur_link` (PDF beim Anbieter holen), nicht in der Kandidatenliste.
    # Nachgemessen am Testsatz aus #3337: kev >= 0,7 allein 9 Fehlalarme,
    # zusammen mit der Anhang-Bedingung 0.
    kandidaten = [k for k in treffer if k["anhang"]]
    nur_link = [k for k in treffer if not k["anhang"]]
    median_latenz = statistics.median(latenzen) if latenzen else None
    return {
        "kandidaten": kandidaten,
        "nur_link": nur_link,
        "geprueft": len(mails),
        "median_latenz_ms": median_latenz,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ordner", default=ORDNER_STANDARD)
    p.add_argument("--tage", type=int, default=TAGE_STANDARD)
    p.add_argument("--schwelle", type=float, default=SCHWELLE_STANDARD)
    p.add_argument("--json", action="store_true", dest="als_json")
    a = p.parse_args(argv)

    cfg = load_cfg()
    acc = cfg["accounts"][0]
    tok = token(cfg, acc)
    if not tok:
        sys.exit(
            f"FEHLER: {acc} nicht fuer Mail angemeldet — erst: graph_mail.py --login {acc}"
        )

    ergebnis = vorfilter_lauf(tok, a.ordner, a.tage, a.schwelle)

    if a.als_json:
        print(
            json.dumps(
                {
                    "kandidaten": ergebnis["kandidaten"],
                    "nur_link": ergebnis["nur_link"],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not ergebnis["kandidaten"]:
        print(
            f"Keine Kandidaten >= {a.schwelle:.2f} in '{a.ordner}' "
            f"(letzte {a.tage} Tage, {ergebnis['geprueft']} geprueft)."
        )
    else:
        print(
            f"Kandidaten >= {a.schwelle:.2f} in '{a.ordner}' "
            f"(letzte {a.tage} Tage), absteigend:"
        )
        for k in ergebnis["kandidaten"]:
            print(
                f"  {k['wert']:.2f}  {k['datum'][:16]:<16}  "
                f"{k['absenderadresse']:<38}  {k['betreff'][:60]}"
            )
            print(f"    id: {k['id']}")

    if ergebnis["nur_link"]:
        print("Rechnung nur als Link, ohne PDF-Anhang — PDF beim Anbieter holen:")
        for k in ergebnis["nur_link"]:
            print(
                f"  {k['wert']:.2f}  {k['datum'][:16]:<16}  "
                f"{k['absenderadresse']:<38}  {k['betreff'][:60]}"
            )
            print(f"    id: {k['id']}")

    median = ergebnis["median_latenz_ms"]
    median_text = f"{median:.0f} ms" if median is not None else "n/a"
    print(
        f"{ergebnis['geprueft']} Mails geprueft, {len(ergebnis['kandidaten'])} "
        f"Kandidaten mit PDF, {len(ergebnis['nur_link'])} nur Link, "
        f"Median-Latenz {median_text}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
