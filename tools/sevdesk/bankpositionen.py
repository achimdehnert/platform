#!/usr/bin/env python3
"""Offene Bankpositionen aus sevdesk als Arbeitsliste — read-only.

Warum es das gibt: sevdesk zeigt unverbuchte Kontoumsätze, aber nicht, welche davon
überhaupt einen Lieferantenbeleg brauchen und auf welches Konto sie gehören. Diese
Liste beantwortet beides und ist die Grundlage für die spätere Verbuchung. Sie wird
**nie** selbst gebucht — Schreiben passiert nur nach ausdrücklicher Freigabe.

    python3 tools/sevdesk/bankpositionen.py            # Board neu erzeugen
    python3 tools/sevdesk/bankpositionen.py --jahr 2025

Ausgabe standardmäßig nach ``~/.claude/boards/sevdesk-bankpositionen.md``; von dort
liest der Loopback-Dienst sie unter ``http://localhost:8787/d/sevdesk-bankpositionen``.
Bewusst nicht nach ``~/shared`` (Secret-Übergabeschleuse) und nie als ``file://``-Link
weitergeben — der Browser des Owners läuft nicht auf diesem Rechner.

Die **Kontenzuordnung ist personenbezogen und liegt NICHT im Repo**, analog zur
Rollen-Registry: ``~/.claude/sevdesk-konten.json``. Vorlage:
``tools/sevdesk/sevdesk-konten.example.json``.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

#: `httpx` wird bewusst NICHT auf Modulebene importiert, sondern erst in `hole()`.
#: Die reinen Funktionen (Kontenzuordnung, Händler-Erkennung, Board-Rendering)
#: brauchen kein Netz. Ein Modul-Import macht sie in Umgebungen ohne httpx
#: untestbar — genau das passierte am 2026-07-29: die Tests liefen lokal, wurden
#: in CI still ÜBERSPRUNGEN (`No module named 'httpx'`) und deckten damit nichts ab.
#: Ein Test, der nur zu Hause läuft, ist kein Test.

API = "https://my.sevdesk.de/api/v1"
TOKEN_DATEI = Path.home() / ".secrets" / "sevdesk_api_token"
KONTEN_DATEI = Path.home() / ".claude" / "sevdesk-konten.json"
STANDARD_ZIEL = Path.home() / ".claude" / "boards" / "sevdesk-bankpositionen.md"

#: PayPal nennt den Händler im Verwendungszweck — anders als lange angenommen ist
#: dafür KEIN PayPal-Umsatzbericht nötig. Es gibt drei Schreibweisen, jede kostete
#: beim Bau einen Fehlversuch:
#:   1047470049958/PP.6820.PP/. Cleverbridge GmbH, Ihr Einkauf bei …
#:   1048171118267/.            Ionos SE, …            (ohne PP-Block)
#:   1049697671020 PP.1321.PP . Spotify AB, …          (Leerzeichen statt »/«)
#: Trefferquote am Bestand 2026: 28 von 28.
PP_MUSTER = re.compile(
    r"(?:PP\.[0-9]{4}\.PP)?\s*[/\s]\.\s*(.{3,45}?)(?:,|\s+Ihr Einkauf|$)"
)

#: Umsatz-Status 100 = unverbucht. 200 verknüpft, 400 verbucht.
STATUS_UNVERBUCHT = "100"


def token_lesen(pfad: Path = TOKEN_DATEI) -> str:
    """Token-Datei ist KEY=WERT, nicht der rohe Wert — die ganze Zeile als Header gibt 401."""
    roh = pfad.read_text(encoding="utf-8").strip()
    return roh.split("=", 1)[1].strip() if "=" in roh else roh


def hole(pfad: str, kopf: dict, **params) -> list[dict]:
    """Blättert vollständig durch — sevdesk liefert maximal 200 je Anfrage."""
    import httpx  # noqa: PLC0415 — bewusst lazy, s. Kommentar oben

    ergebnis: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(
            f"{API}/{pfad}",
            headers=kopf,
            params=dict(params, limit=200, offset=offset),
            timeout=60,
        )
        r.raise_for_status()
        seite = r.json().get("objects") or []
        ergebnis += seite
        if len(seite) < 200:
            return ergebnis
        offset += 200


def konten_laden(pfad: Path = KONTEN_DATEI) -> list[dict]:
    if not pfad.exists():
        sys.exit(
            f"Kontenzuordnung fehlt: {pfad}\n"
            f"Vorlage kopieren aus tools/sevdesk/sevdesk-konten.example.json"
        )
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    return daten.get("regeln", [])


def paypal_haendler(zweck: str) -> str:
    treffer = PP_MUSTER.search(zweck or "")
    return treffer.group(1).strip() if treffer else ""


def kurz(text: str, laenge: int) -> str:
    text = " ".join((text or "").split())
    return (text[: laenge - 1] + "…") if len(text) > laenge else text


def zuordnen(text: str, betrag: float, regeln: list[dict]) -> tuple[str, str, str]:
    """Erste passende Regel gewinnt. Rückgabe: (konto, bezeichnung, anmerkung)."""
    klein = text.lower()
    for regel in regeln:
        if not re.search(regel["muster"], klein):
            continue
        konto = regel["konto"]
        anmerkung = regel.get("anmerkung", "")
        # Eine Sammelüberweisung kann mehrere Zwecke bündeln. Beträge, die nicht
        # exakt zu den bekannten Einzelposten passen, NICHT stillschweigend ganz
        # zuordnen — sonst wandert ein Fremdposten unbemerkt auf das Lohnkonto.
        erwartet = regel.get("nur_betraege")
        if erwartet and round(abs(betrag), 2) not in erwartet:
            passende = [b for b in erwartet if b <= abs(betrag)]
            if passende:
                rest = round(abs(betrag) - max(passende), 2)
                anmerkung = f"NUR TEILWEISE — {rest:,.2f} € nicht abgedeckt"
            else:
                # Betrag kleiner als jeder bekannte Einzelposten — gar nichts passt.
                anmerkung = f"BETRAG UNBEKANNT — {abs(betrag):,.2f} € passt zu keinem Einzelposten"
        return konto, regel.get("bezeichnung", ""), anmerkung
    return "", "", ""


def board_schreiben(zeilen: list[dict], ziel: Path, jahr: int) -> dict[str, int]:
    zugeordnet = [z for z in zeilen if z["konto"] and z["konto"] != "KLÄRUNG"]
    klaerung = [z for z in zeilen if z["konto"] == "KLÄRUNG"]
    offen = [z for z in zeilen if not z["konto"]]

    def wer(z: dict) -> str:
        return f"PayPal → {z['haendler']}" if z["haendler"] else z["name"]

    ziel.parent.mkdir(parents=True, exist_ok=True)
    with ziel.open("w", encoding="utf-8") as f:
        f.write(f"# Offene Bankpositionen {jahr} — Einzelaufstellung je Position\n\n")
        f.write(
            f"{len(zeilen)} unverbuchte Positionen (Status {STATUS_UNVERBUCHT}), "
            f"read-only aus der sevdesk-API.\n"
        )
        f.write(
            f"**{len(zugeordnet)} zugeordnet** · **{len(klaerung)} in Klärung** · "
            f"**{len(offen)} offen**\n\n"
        )

        if offen:
            f.write(f"\n## Noch offen — Konto eintragen ({len(offen)} Positionen)\n\n")
            f.write("| # | Datum | Betrag € | Wer | Zweck | Konto | Umsatz-ID |\n")
            f.write("|---:|---|---:|---|---|---|---|\n")
            for z in offen:
                f.write(
                    f"| {z['nr']} | {z['datum']} | {z['betrag']:,.2f} | "
                    f"{kurz(wer(z), 34)} | {kurz(z['zweck'], 40)} | | `{z['id']}` |\n"
                )

        if klaerung:
            summe = sum(abs(z["betrag"]) for z in klaerung)
            f.write(f"\n## In Klärung ({len(klaerung)} Positionen, {summe:,.2f} €)\n\n")
            f.write(f"{klaerung[0]['anm']}\n\n")
            f.write(
                "| # | Datum | Betrag € | Zweck | Umsatz-ID |\n|---:|---|---:|---|---|\n"
            )
            for z in klaerung:
                f.write(
                    f"| {z['nr']} | {z['datum']} | {z['betrag']:,.2f} | "
                    f"{kurz(z['zweck'], 46)} | `{z['id']}` |\n"
                )

        f.write(f"\n## Zugeordnet ({len(zugeordnet)} Positionen)\n\n")
        f.write("| # | Datum | Betrag € | Wer | Konto | Bezeichnung | Umsatz-ID |\n")
        f.write("|---:|---|---:|---|---|---|---|\n")
        for z in zugeordnet:
            warnung = " ⚠" if "TEILWEISE" in (z["anm"] or "") else ""
            f.write(
                f"| {z['nr']} | {z['datum']} | {z['betrag']:,.2f} | {kurz(wer(z), 34)} | "
                f"**{z['konto']}**{warnung} | {z['bez']} | `{z['id']}` |\n"
            )

        teilweise = [z for z in zugeordnet if "TEILWEISE" in (z["anm"] or "")]
        if teilweise:
            f.write("\n**⚠ Nur teilweise zugeordnet:**\n\n")
            for z in teilweise:
                f.write(
                    f"- Nr. {z['nr']} ({z['datum']}, {z['betrag']:,.2f} €): {z['anm']}\n"
                )

    return {
        "zugeordnet": len(zugeordnet),
        "klaerung": len(klaerung),
        "offen": len(offen),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--jahr", type=int, default=2026)
    p.add_argument("--ziel", type=Path, default=STANDARD_ZIEL)
    p.add_argument("--konten", type=Path, default=KONTEN_DATEI)
    p.add_argument(
        "--schnappschuss",
        type=Path,
        default=None,
        help="Arbeitsstand als JSON einfrieren (Umsatz-ID → Konto). "
        "Eingabe für den Buchungsschritt und Beleg dafür, worauf "
        "sich eine Freigabe bezogen hat.",
    )
    p.add_argument(
        "--stand",
        default=None,
        help="Zeitstempel für den Schnappschuss (z. B. 2026-07-29T11:50). "
        "Bewusst als Argument statt aus der Systemuhr, damit ein "
        "Wiederholungslauf denselben Stand erzeugt.",
    )
    args = p.parse_args()

    kopf = {"Authorization": token_lesen(), "Accept": "application/json"}
    regeln = konten_laden(args.konten)

    alle = hole("CheckAccountTransaction", kopf)
    offen = sorted(
        [
            t
            for t in alle
            if (t.get("valueDate") or "")[:4] == str(args.jahr)
            and str(t.get("status")) == STATUS_UNVERBUCHT
        ],
        key=lambda t: t.get("valueDate") or "",
    )

    zeilen = []
    for nr, t in enumerate(offen, 1):
        betrag = float(t.get("amount", 0))
        name = t.get("payeePayerName") or ""
        zweck = t.get("paymtPurpose") or ""
        konto, bez, anm = zuordnen(f"{name} {zweck}", betrag, regeln)
        ist_paypal = "paypal" in f"{name} {zweck}".lower()
        zeilen.append(
            {
                "nr": nr,
                "id": t.get("id"),
                "datum": (t.get("valueDate") or "")[:10],
                "betrag": betrag,
                "name": kurz(name, 34) or "—",
                "zweck": kurz(zweck, 60) or "—",
                "konto": konto,
                "bez": bez,
                "anm": anm,
                "haendler": paypal_haendler(zweck) if ist_paypal else "",
            }
        )

    stand = board_schreiben(zeilen, args.ziel, args.jahr)

    # Eingefrorener Arbeitsstand. Das Board wird bei jedem Lauf neu aus der API
    # erzeugt — kommen Umsätze dazu oder wird etwas gebucht, ist es nicht mehr
    # derselbe Fall. Der Schnappschuss hält fest, worauf sich eine Freigabe bezog,
    # und ist zugleich die Eingabe für den Buchungsschritt: Umsatz-ID → Konto.
    if args.schnappschuss:
        args.schnappschuss.parent.mkdir(parents=True, exist_ok=True)
        args.schnappschuss.write_text(
            json.dumps(
                {
                    "erzeugt": args.stand or "(ohne Zeitstempel aufgerufen)",
                    "jahr": args.jahr,
                    "positionen_gesamt": len(zeilen),
                    "summe": stand,
                    "positionen": [
                        {
                            "umsatz_id": z["id"],
                            "datum": z["datum"],
                            "betrag": z["betrag"],
                            "wer": z["haendler"] or z["name"],
                            "konto": z["konto"],
                            "bezeichnung": z["bez"],
                            "anmerkung": z["anm"],
                        }
                        for z in zeilen
                    ],
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"Schnappschuss: {args.schnappschuss}")
    print(f"geschrieben: {args.ziel}")
    print(
        f"  {len(zeilen)} Positionen — {stand['zugeordnet']} zugeordnet, "
        f"{stand['klaerung']} in Klärung, {stand['offen']} offen\n"
    )
    for (konto, bez), n in collections.Counter(
        (z["konto"], z["bez"]) for z in zeilen if z["konto"]
    ).most_common():
        summe = sum(
            abs(z["betrag"]) for z in zeilen if z["konto"] == konto and z["bez"] == bez
        )
        print(f"  {konto:<8} {bez:<38} {n:>2} Pos.  {summe:>10,.2f} €")
    return 0


if __name__ == "__main__":
    sys.exit(main())
