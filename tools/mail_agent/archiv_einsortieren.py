#!/usr/bin/env python3
"""Sortiert einen flachen Archiv-Ordner nach Jahrgaengen (Microsoft Graph).

Anlass (gemessen 2026-07-28): Der IIL-Ordner 'Archiv' hielt 22.623 Nachrichten aus
den Jahren 2016-2026, waehrend die Jahrgangsordner nahezu leer danebenlagen. Die
Archivierungskonvention (laufendes Jahr live, Vorjahre in den Jahrgang) war damit
faktisch nicht umgesetzt. `graph_mail.py --move` filtert nach Absender und Betreff,
nicht nach Datum — fuer diesen Fall gab es kein Werkzeug.

Sicherheitseigenschaften, bewusst so gewaehlt:

* **Trockenlauf ist der Standard.** Verschoben wird nur mit ``--apply``.
* **Kein Ordner wird angelegt.** Fehlt der Zielordner, wird die Nachricht
  uebersprungen und der Grund genannt — ein Werkzeug, das im selben Lauf Ordner
  erfindet und befuellt, macht einen Tippfehler im Quellpfad unbemerkbar.
* **Das laufende Jahr bleibt unberuehrt**, ebenso alles nach ``--bis``.
* **Erst lesen, dann schreiben.** Die vollstaendige Liste wird vorab geholt; wer
  waehrend des Blaetterns verschiebt, verschiebt den Seitenversatz mit und
  ueberspringt stillschweigend Nachrichten.
* **Wiederaufnehmbar.** Eine verschobene Nachricht liegt nicht mehr in der Quelle;
  ein zweiter Lauf setzt fort, statt doppelt zu arbeiten.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph_mail import GRAPH, _auth, _http, load_cfg, token  # noqa: E402

TOOL_VERSION = "archiv_einsortieren.py/1"


# ---------- reine Logik (ohne Graph, damit testbar) ----------


def jahr_aus(iso_datum: str | None) -> str | None:
    """'2021-03-04T…' -> '2021'. Ohne verwertbares Datum: None."""
    if not iso_datum or len(iso_datum) < 4:
        return None
    kopf = iso_datum[:4]
    return kopf if kopf.isdigit() else None


def entscheide(
    jahr: str | None,
    bis: int,
    aktuelles_jahr: int,
    vorhandene_jahrgaenge: set[str],
) -> tuple[str | None, str]:
    """(Zieljahr oder None, Begruendung) — die Begruendung wird immer ausgegeben.

    Ein uebersprungener Posten ohne genannten Grund ist der stille Rest, den
    dieses Werkzeug gerade vermeiden soll.
    """
    if jahr is None:
        return None, "kein verwertbares Empfangsdatum"
    n = int(jahr)
    if n >= aktuelles_jahr:
        return None, f"laufendes Jahr {jahr} — bleibt liegen"
    if n > bis:
        return None, f"{jahr} liegt nach --bis {bis}"
    if jahr not in vorhandene_jahrgaenge:
        return None, f"Jahrgangsordner fuer {jahr} fehlt — nicht angelegt"
    return jahr, "einsortieren"


# ---------- IMAP (zweiter Transport) ----------

_LIST_ZEILE = re.compile(
    rb'^\([^)]*\)\s+(?:"[^"]*"|NIL)\s+(?:"(?P<q>[^"]*)"|(?P<u>\S+))\s*$'
)
_UID = re.compile(rb"UID (\d+)")
_INTERNALDATE = re.compile(rb'INTERNALDATE "\d{2}-\w{3}-(\d{4})')


def imap_ordner(imap) -> list[str]:
    typ, res = imap.list()
    if typ != "OK":
        return []
    namen = []
    for zeile in res or []:
        m = _LIST_ZEILE.match(zeile) if zeile else None
        if not m:
            continue
        roh = m.group("q") if m.group("q") is not None else m.group("u")
        namen.append(roh.decode("utf-8", "replace"))
    return namen


def imap_posten(imap, ordner: str) -> list[tuple[bytes, str | None]]:
    """[(uid, jahr)] eines Ordners.

    UID wird ausdruecklich mit angefordert: Exchange liefert sie sonst nicht mit,
    und ein darauf aufbauender Filter gibt still eine leere Menge zurueck
    (error_pattern platform:20260728-exchange-uid).
    """
    typ, res = imap.select(f'"{ordner}"', readonly=True)
    if typ != "OK":
        return []
    anzahl = int(res[0])
    if anzahl == 0:
        return []
    aus: list[tuple[bytes, str | None]] = []
    for start in range(1, anzahl + 1, 2000):
        typ, daten = imap.fetch(
            f"{start}:{min(start + 1999, anzahl)}", "(UID INTERNALDATE)"
        )
        if typ != "OK":
            continue
        for teil in daten or []:
            roh = teil if isinstance(teil, bytes) else (teil[0] if teil else b"")
            u = _UID.search(roh or b"")
            d = _INTERNALDATE.search(roh or b"")
            if u:
                aus.append((u.group(1), d.group(1).decode() if d else None))
    return aus


def imap_kann_move(imap) -> bool:
    """MOVE (RFC 6851) verschiebt atomar. Ohne die Erweiterung braucht es
    COPY + \\Deleted + UID EXPUNGE — und UID EXPUNGE (UIDPLUS, RFC 4315) ist
    Pflicht: ein blankes EXPUNGE loescht ALLE als geloescht markierten
    Nachrichten des Ordners, auch fremd markierte."""
    return "MOVE" in _faehigkeiten(imap)


def _faehigkeiten(imap) -> set[str]:
    """imaplib liefert Faehigkeiten als str-Tupel, nicht als bytes."""
    return {
        (c.decode() if isinstance(c, bytes) else str(c)).upper()
        for c in imap.capabilities
    }


def imap_kann_uid_expunge(imap) -> bool:
    return "UIDPLUS" in _faehigkeiten(imap)


def imap_verschiebe(imap, ordner: str, uids: list[bytes], ziel: str) -> tuple[int, str]:
    """(verschoben, fehlermeldung). Schreibzugriff — Ordner NICHT readonly oeffnen."""
    if not uids:
        return 0, ""
    typ, _ = imap.select(f'"{ordner}"', readonly=False)
    if typ != "OK":
        return 0, f"Ordner '{ordner}' nicht schreibend zu oeffnen"
    menge = b",".join(uids).decode()

    if imap_kann_move(imap):
        typ, res = imap.uid("MOVE", menge, f'"{ziel}"')
        return (len(uids), "") if typ == "OK" else (0, f"MOVE fehlgeschlagen: {res}")

    if not imap_kann_uid_expunge(imap):
        return 0, (
            "Server kann weder MOVE noch UID EXPUNGE — ein blankes EXPUNGE wuerde "
            "fremd markierte Nachrichten mitloeschen, deshalb kein Fallback"
        )
    typ, res = imap.uid("COPY", menge, f'"{ziel}"')
    if typ != "OK":
        return 0, f"COPY fehlgeschlagen: {res}"
    typ, res = imap.uid("STORE", menge, "+FLAGS", "(\\Deleted)")
    if typ != "OK":
        return 0, f"STORE fehlgeschlagen (Kopie liegt bereits im Ziel): {res}"
    typ, res = imap.uid("EXPUNGE", menge)
    if typ != "OK":
        return 0, f"UID EXPUNGE fehlgeschlagen: {res}"
    return len(uids), ""


# ---------- Graph ----------


def ordner_index(tok: str) -> dict[str, str]:
    aus: dict[str, str] = {}

    def walk(pid, prefix):
        url = (
            f"{GRAPH}/me/mailFolders"
            if pid is None
            else f"{GRAPH}/me/mailFolders/{pid}/childFolders"
        )
        url += "?$top=100&$select=id,displayName,childFolderCount"
        while url:
            r = _http("GET", url, headers=_auth(tok)).json()
            for f in r.get("value", []):
                p = f["displayName"] if not prefix else f"{prefix}/{f['displayName']}"
                aus[p] = f["id"]
                if f.get("childFolderCount", 0):
                    walk(f["id"], p)
            url = r.get("@odata.nextLink")

    walk(None, "")
    return aus


def nachrichten(tok: str, fid: str) -> list[tuple[str, str | None]]:
    """(id, receivedDateTime) — vollstaendig VOR dem ersten Schreibzugriff."""
    url = f"{GRAPH}/me/mailFolders/{fid}/messages?$top=999&$select=id,receivedDateTime"
    aus: list[tuple[str, str | None]] = []
    while url:
        r = _http("GET", url, headers=_auth(tok)).json()
        for m in r.get("value", []):
            aus.append((m["id"], m.get("receivedDateTime")))
        url = r.get("@odata.nextLink")
    return aus


BATCH_GROESSE = 20  # Graph-Obergrenze fuer /$batch
WIEDERHOLBAR = {429, 503, 504}  # Drosselung/Ueberlast — kein Datenfehler


def stapel_anfrage(posten: list[tuple[str, str]]) -> dict:
    """Baut den /$batch-Rumpf. Rein, damit die Form ohne Netz pruefbar ist."""
    return {
        "requests": [
            {
                "id": str(i),
                "method": "POST",
                "url": f"/me/messages/{mid}/move",
                "headers": {"Content-Type": "application/json"},
                "body": {"destinationId": ziel_id},
            }
            for i, (mid, ziel_id) in enumerate(posten)
        ]
    }


def _retry_after(teil: dict) -> int:
    """Wartezeit aus den Teilantwort-Kopfzeilen, 0 wenn keine genannt ist.

    `_Resp` traegt keine Kopfzeilen, wohl aber jede Teilantwort im /$batch-Rumpf —
    das ist die einzige Stelle, an der Graph uns sagt, wie lange er gedrosselt hat.
    """
    kopf = {k.lower(): v for k, v in (teil.get("headers") or {}).items()}
    wert = kopf.get("retry-after")
    try:
        return max(0, int(str(wert).strip()))
    except (TypeError, ValueError):
        return 0


def stapel_auswerten(
    antwort: dict, posten: list[tuple[str, str]]
) -> tuple[int, list[tuple[str, str]], list[str], int]:
    """(erfolge, erneut_versuchen, endgueltige_fehler, empfohlene_wartezeit).

    Graph liefert die Teilantworten **in beliebiger Reihenfolge** zurueck — sie
    werden ueber die mitgesendete id zugeordnet, nie ueber die Position. Wer hier
    positionsweise liest, ordnet Ergebnisse den falschen Nachrichten zu.
    """
    erfolge = 0
    erneut: list[tuple[str, str]] = []
    fehler: list[str] = []
    gesehen: set[str] = set()
    warten = 0

    for teil in antwort.get("responses", []):
        kennung = str(teil.get("id", ""))
        gesehen.add(kennung)
        if not kennung.isdigit() or int(kennung) >= len(posten):
            fehler.append(f"unbekannte Teilantwort id={kennung!r}")
            continue
        status = int(teil.get("status", 0))
        eintrag = posten[int(kennung)]
        if status in (200, 201, 204):
            erfolge += 1
        elif status in WIEDERHOLBAR:
            erneut.append(eintrag)
            warten = max(warten, _retry_after(teil))
        else:
            fehler.append(f"HTTP {status} fuer {eintrag[0][:24]}…")

    # Eine Teilantwort, die gar nicht kam, ist offen — nicht stillschweigend ok.
    for i, eintrag in enumerate(posten):
        if str(i) not in gesehen:
            erneut.append(eintrag)

    return erfolge, erneut, fehler, warten


#: Wartezeit, wenn Graph drosselt ohne Retry-After zu nennen. Gemessen 2026-07-28:
#: nach rund 10.000 Verschiebungen drosselt das Postfach, und die Sperre haelt
#: Minuten an — die frueheren 2/4/8 Sekunden waren um Groessenordnungen zu kurz und
#: brannten 12.000 Posten als "Fehler" ab, die schlicht haetten warten muessen.
DROSSEL_WARTEN = 90
DROSSEL_RUNDEN = 12


def verschiebe_stapel(
    tok: str, posten: list[tuple[str, str]], runden: int = DROSSEL_RUNDEN
) -> tuple[int, list[str]]:
    """Verschiebt bis zu BATCH_GROESSE Nachrichten je Anfrage."""
    offen = list(posten)
    erfolge = 0
    fehler: list[str] = []
    for runde in range(runden):
        if not offen:
            break
        naechste: list[tuple[str, str]] = []
        warten = 0
        for i in range(0, len(offen), BATCH_GROESSE):
            block = offen[i : i + BATCH_GROESSE]
            r = _http(
                "POST",
                f"{GRAPH}/$batch",
                headers=_auth(tok),
                json_body=stapel_anfrage(block),
                timeout=120,
            )
            if r.status_code != 200:
                naechste.extend(block)
                warten = max(warten, DROSSEL_WARTEN)
                continue
            try:
                daten = json.loads(r.text)
            except ValueError:
                naechste.extend(block)
                warten = max(warten, DROSSEL_WARTEN)
                continue
            ok, erneut, schlecht, vorschlag = stapel_auswerten(daten, block)
            erfolge += ok
            naechste.extend(erneut)
            fehler.extend(schlecht)
            if erneut:
                warten = max(warten, vorschlag or DROSSEL_WARTEN)
        offen = naechste
        if offen and runde + 1 < runden:
            # Laut melden, nicht erst in der Schlussbilanz — ein Lauf, der still
            # 12.000 Fehler sammelt, sieht bis zum Ende gesund aus.
            print(
                f"    ⏸ gedrosselt: {len(offen)} offen, warte {warten}s "
                f"(Runde {runde + 1}/{runden})",
                flush=True,
            )
            time.sleep(warten)
    fehler.extend(f"nach {runden} Runden offen: {mid[:24]}…" for mid, _ in offen)
    return erfolge, fehler


def verschiebe(tok: str, mid: str, ziel_id: str) -> bool:
    r = _http(
        "POST",
        f"{GRAPH}/me/messages/{mid}/move",
        headers=_auth(tok),
        json_body={"destinationId": ziel_id},
    )
    if r.status_code not in (200, 201):
        print(f"  ! HTTP {r.status_code} — {r.text[:120]}", file=sys.stderr)
        return False
    return True


def lauf_imap(args) -> None:
    """IMAP-Variante: gleiche Entscheidungslogik, anderer Transport."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from read_mail import _resolve_config, connect
    from send_mail import parse_env

    imap = connect(parse_env(_resolve_config(None, args.imap_konto)))
    alle = imap_ordner(imap)
    if args.quelle not in alle:
        sys.exit(f"Quellordner '{args.quelle}' nicht gefunden")
    jahrgaenge = {
        p.split("/")[-1]
        for p in alle
        if p.startswith(f"{args.ziel_wurzel}/") and p.split("/")[-1].isdigit()
    }
    aktuelles_jahr = datetime.now(timezone.utc).year

    posten = imap_posten(imap, args.quelle)
    modus = "AUSFUEHRUNG" if args.apply else "TROCKENLAUF"
    print(f"=== {modus} · IMAP {args.imap_konto} · {args.quelle} → "
          f"{args.ziel_wurzel}/<Jahr> ===")
    print(f"    {TOOL_VERSION} · bis {args.bis} · laufendes Jahr {aktuelles_jahr}")
    print(f"    MOVE={imap_kann_move(imap)} UIDPLUS={imap_kann_uid_expunge(imap)}")
    print(f"    {len(posten)} Nachricht(en) gelesen, "
          f"{len(jahrgaenge)} Jahrgangsordner vorhanden\n")

    plan: dict[str, list[bytes]] = {}
    uebersprungen: Counter = Counter()
    for uid, jahr in posten:
        ziel, grund = entscheide(jahr, args.bis, aktuelles_jahr, jahrgaenge)
        if ziel is None or (args.nur_jahr and ziel != args.nur_jahr):
            uebersprungen[grund if ziel is None else f"nicht --nur-jahr {args.nur_jahr}"] += 1
            continue
        plan.setdefault(ziel, []).append(uid)

    for jahr, uids in sorted(plan.items()):
        print(f"  {len(uids):>6}  → {args.ziel_wurzel}/{jahr}")
    print(f"  {sum(len(u) for u in plan.values()):>6}  gesamt einzusortieren")
    if uebersprungen:
        print("\n  uebersprungen:")
        for grund, n in sorted(uebersprungen.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>6}  {grund}")

    if not args.apply:
        print("\n  Trockenlauf — nichts veraendert. Mit --apply ausfuehren.")
        return

    ok = 0
    fehler: list[str] = []
    for jahr, uids in sorted(plan.items()):
        if args.limit:
            uids = uids[: args.limit]
        ziel = f"{args.ziel_wurzel}/{jahr}"
        for i in range(0, len(uids), 200):
            n, meldung = imap_verschiebe(imap, args.quelle, uids[i : i + 200], ziel)
            ok += n
            if meldung:
                fehler.append(f"{ziel}: {meldung}")
        print(f"    … {ziel}: {ok} gesamt verschoben", flush=True)
    imap.logout()

    print(f"\n  verschoben {ok}, fehlgeschlagen {len(fehler)}")
    for zeile in fehler[:20]:
        print(f"    ! {zeile}")
    if fehler:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quelle", default="Archiv", help="flacher Quellordner")
    ap.add_argument("--ziel-wurzel", default="Archiv", help="Wurzel der Jahrgaenge")
    ap.add_argument(
        "--bis", type=int, default=2024, help="hoechstes einzusortierendes Jahr"
    )
    ap.add_argument("--nur-jahr", help="nur diesen Jahrgang bearbeiten")
    ap.add_argument("--limit", type=int, help="hoechstens so viele verschieben")
    ap.add_argument(
        "--apply", action="store_true", help="wirklich verschieben (sonst Trockenlauf)"
    )
    ap.add_argument(
        "--einzeln",
        action="store_true",
        help="ein Aufruf je Nachricht statt Stapel (langsam, aber eindeutig)",
    )
    ap.add_argument(
        "--imap-konto",
        dest="imap_konto",
        help="statt Graph ueber IMAP arbeiten (Kontokuerzel, z.B. hnu)",
    )
    args = ap.parse_args()

    if args.imap_konto:
        lauf_imap(args)
        return

    cfg = load_cfg()
    konto = cfg["accounts"][0]
    tok = token(cfg, konto)
    if not tok:
        sys.exit("kein gueltiges Token — graph_mail.py --login <konto>")

    idx = ordner_index(tok)
    if args.quelle not in idx:
        sys.exit(f"Quellordner '{args.quelle}' nicht gefunden")

    jahrgaenge = {
        p.split("/")[-1]: i
        for p, i in idx.items()
        if p.startswith(f"{args.ziel_wurzel}/") and p.split("/")[-1].isdigit()
    }
    aktuelles_jahr = datetime.now(timezone.utc).year

    posten = nachrichten(tok, idx[args.quelle])
    modus = "AUSFUEHRUNG" if args.apply else "TROCKENLAUF"
    print(f"=== {modus} · {konto} · {args.quelle} → {args.ziel_wurzel}/<Jahr> ===")
    print(f"    {TOOL_VERSION} · bis {args.bis} · laufendes Jahr {aktuelles_jahr}")
    print(f"    {len(posten)} Nachricht(en) gelesen, "
          f"{len(jahrgaenge)} Jahrgangsordner vorhanden\n")

    plan: Counter = Counter()
    uebersprungen: Counter = Counter()
    zu_tun: list[tuple[str, str]] = []
    for mid, dt in posten:
        ziel, grund = entscheide(
            jahr_aus(dt), args.bis, aktuelles_jahr, set(jahrgaenge)
        )
        if ziel is None:
            uebersprungen[grund] += 1
            continue
        if args.nur_jahr and ziel != args.nur_jahr:
            uebersprungen[f"nicht --nur-jahr {args.nur_jahr}"] += 1
            continue
        plan[ziel] += 1
        zu_tun.append((mid, jahrgaenge[ziel]))

    for jahr, n in sorted(plan.items()):
        print(f"  {n:>6}  → {args.ziel_wurzel}/{jahr}")
    print(f"  {sum(plan.values()):>6}  gesamt einzusortieren")
    if uebersprungen:
        print("\n  uebersprungen:")
        for grund, n in sorted(uebersprungen.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>6}  {grund}")

    if not args.apply:
        print("\n  Trockenlauf — nichts veraendert. Mit --apply ausfuehren.")
        return

    if args.limit:
        zu_tun = zu_tun[: args.limit]

    if args.einzeln:
        ok = schlecht = 0
        for i, (mid, ziel_id) in enumerate(zu_tun, 1):
            if verschiebe(tok, mid, ziel_id):
                ok += 1
            else:
                schlecht += 1
            if i % 250 == 0:
                print(f"    … {i}/{len(zu_tun)} (ok {ok}, Fehler {schlecht})", flush=True)
        fehler = [f"{schlecht} Einzelfehler"] if schlecht else []
    else:
        ok = 0
        fehler = []
        schritt = BATCH_GROESSE * 25  # ~500 je Fortschrittszeile
        for i in range(0, len(zu_tun), schritt):
            teil_ok, teil_fehler = verschiebe_stapel(tok, zu_tun[i : i + schritt])
            ok += teil_ok
            fehler.extend(teil_fehler)
            print(
                f"    … {min(i + schritt, len(zu_tun))}/{len(zu_tun)} "
                f"(ok {ok}, Fehler {len(fehler)})",
                flush=True,
            )

    print(f"\n  verschoben {ok}, fehlgeschlagen {len(fehler)}")
    for zeile in fehler[:20]:
        print(f"    ! {zeile}")
    if len(fehler) > 20:
        print(f"    … und {len(fehler) - 20} weitere")
    if fehler:
        sys.exit(1)


if __name__ == "__main__":
    main()
