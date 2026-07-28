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


def stapel_auswerten(
    antwort: dict, posten: list[tuple[str, str]]
) -> tuple[int, list[tuple[str, str]], list[str]]:
    """(erfolge, erneut_versuchen, endgueltige_fehler).

    Graph liefert die Teilantworten **in beliebiger Reihenfolge** zurueck — sie
    werden ueber die mitgesendete id zugeordnet, nie ueber die Position. Wer hier
    positionsweise liest, ordnet Ergebnisse den falschen Nachrichten zu.
    """
    erfolge = 0
    erneut: list[tuple[str, str]] = []
    fehler: list[str] = []
    gesehen: set[str] = set()

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
        else:
            fehler.append(f"HTTP {status} fuer {eintrag[0][:24]}…")

    # Eine Teilantwort, die gar nicht kam, ist offen — nicht stillschweigend ok.
    for i, eintrag in enumerate(posten):
        if str(i) not in gesehen:
            erneut.append(eintrag)

    return erfolge, erneut, fehler


def verschiebe_stapel(
    tok: str, posten: list[tuple[str, str]], runden: int = 4
) -> tuple[int, list[str]]:
    """Verschiebt bis zu BATCH_GROESSE Nachrichten je Anfrage."""
    offen = list(posten)
    erfolge = 0
    fehler: list[str] = []
    for runde in range(runden):
        if not offen:
            break
        if runde:
            time.sleep(min(2**runde, 30))
        naechste: list[tuple[str, str]] = []
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
                continue
            try:
                daten = json.loads(r.text)
            except ValueError:
                naechste.extend(block)
                continue
            ok, erneut, schlecht = stapel_auswerten(daten, block)
            erfolge += ok
            naechste.extend(erneut)
            fehler.extend(schlecht)
        offen = naechste
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
    args = ap.parse_args()

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
