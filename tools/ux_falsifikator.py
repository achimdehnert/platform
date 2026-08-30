#!/usr/bin/env python3
"""Falsifikator-Gegenpart fuer /ux-review (KONZ-platform-051 Stufe 1b, E13-E17).

Prueft **einen fertigen Befund** eines ux-review-Laufs und faellt einen Spruch:
`bestaetigt` / `widerlegt` / `unklar`. Er eroeffnet keinen eigenen Befund (E13).

Warum ueberhaupt: die belegte Schwaeche des Laufs ist der Fehlbefund
(writing-hub#760, "Feld fehlt" aus leerem DOM), nicht Befundmangel. K2 des
Kill-Gates ist die Fehlbefund-Quote.

Rung T1a nach der llm-routing-Policy — der Ertrag ist die **andere
Trainingsfamilie** als der Produzent, nicht die Rung (E14).

E16 (haerteste Regel hier): der Spruch **filtert nicht**. Ein `widerlegt`
unterdrueckt kein Issue; K1/K2 zaehlen weiter den ungefilterten Lauf. Deshalb
gibt dieses Werkzeug auch bei `widerlegt` Exit 0 zurueck — wer es als Gate
verdrahtet, verletzt E16.

E17: keine Bilder, keine Echtdaten. Screenshots werden nicht uebergeben; ein
Lauf gegen echte Daten wird mit --echtdaten uebersprungen statt gefragt.

R9 (gemessen 2026-08-30, platform#2489): derselbe Befund bekommt beim
gleichen Modell nicht immer denselben Spruch — zwei von elf Datensaetzen
kippten ueber drei Laeufe, obwohl `temperature: 0` gesetzt war. Deshalb fragt
dieses Werkzeug **dreimal** und legt die Streuung offen (Option B): `spruch`
ist die Mehrheit, `einig` sagt, ob sie einstimmig war. Ein Aufruf ist kein
Urteil, sondern ein Wurf — wer nur `spruch` liest, liest die Mehrheit.

Aufruf:
    python3 tools/ux_falsifikator.py --datei befund.json
    python3 tools/ux_falsifikator.py < befund.json
    python3 tools/ux_falsifikator.py --datei befund.json --laeufe 1   # nur fuer Tests

Eingabe (JSON): klasse, severity, symptom, station, antwortkoerper,
gegenprobe, referenz, bekannt (bool).
Ausgabe (JSON): spruch, begruendung, modell, geprueft_am, laeufe, einig,
sprueche.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

SCHLUESSEL_DATEI = pathlib.Path.home() / ".secrets" / "groq_api_key"
ENDPUNKT = "https://api.groq.com/openai/v1/chat/completions"
MODELL = "openai/gpt-oss-120b"  # T1a, andere Familie als der Produzent (E14)
SPRUECHE = ("bestaetigt", "widerlegt", "unklar")
LAEUFE = 3  # R9: ein Aufruf ist ein Wurf, kein Urteil (platform#2489)

# Pflicht, kein Schmuck: vor Groq steht Cloudflare, und die urllib-Vorgabe
# ("Python-urllib/3.x") faellt in dessen Bot-Regel — die Antwort ist dann
# `HTTP 403 error code: 1010`, was wie ein ungueltiger Schluessel aussieht.
# Gemessen 2026-08-30: derselbe Schluessel, nur mit dieser Kennung, liefert 200.
KENNUNG = "iil-ux-falsifikator/1.0"

# Felder, die nie an einen externen Anbieter gehen (E17).
VERBOTENE_FELDER = ("screenshot", "screenshot_pfad", "bild", "bild_base64")

SYSTEM = """Du pruefst einen einzelnen UX-Befund eines Browser-Durchlaufs.

Du bist Pruefer, nicht Autor: du eroeffnest keinen eigenen Befund und schlaegst
keine Loesung vor. Du urteilst NICHT darueber, ob die Software gut ist — nur
darueber, ob der Befund durch die **mitgelieferte** Evidenz gedeckt ist. Nutze
kein Weltwissen ueber das Projekt; was nicht im Befund steht, existiert fuer
dich nicht.

Regeln, in dieser Reihenfolge:
1. Der Befund behauptet eine Absenz ("fehlt", "kein", "nicht vorhanden") und
   das Feld gegenprobe ist leer oder fehlt -> widerlegt.
2. Der Befund behauptet eine Absenz und die gegenprobe meldet Treffer
   -> widerlegt (es ist eine Rendering-Bedingung, keine Absenz).
3. severity ist "optimierung" und referenz ist leer -> widerlegt.
4. bekannt ist true -> widerlegt (bekannte Befunde bekommen kein neues Issue).
5. Das Symptom wird vom Feld antwortkoerper nicht gedeckt, oder antwortkoerper
   ist leer, obwohl das Symptom einen Fehler der Anwendung behauptet -> unklar.
6. Sonst -> bestaetigt.

Antworte ausschliesslich als JSON-Objekt:
{"spruch": "bestaetigt|widerlegt|unklar", "begruendung": "<ein vollstaendiger deutscher Satz: welche Regel greift, mit Nummer, und woran im Befund du das siehst>"}"""


def evidenz_block(befund: dict) -> str:
    """Baut den Nutzer-Prompt — nur Textfelder, nie ein Bild (E17)."""
    felder = [
        ("klasse", befund.get("klasse", "")),
        ("severity", befund.get("severity", "")),
        ("station", befund.get("station", "")),
        ("symptom", befund.get("symptom", "")),
        ("antwortkoerper", befund.get("antwortkoerper", "")),
        ("gegenprobe", befund.get("gegenprobe", "")),
        ("referenz", befund.get("referenz", "")),
        ("bekannt", "true" if befund.get("bekannt") else "false"),
    ]
    return "\n".join(f"{name}: {wert}" for name, wert in felder)


def pruefe_eingabe(befund: dict) -> None:
    """E17 — Bilder und Bildzeiger gehen nicht raus."""
    treffer = [f for f in VERBOTENE_FELDER if befund.get(f)]
    if treffer:
        raise SystemExit(
            f"E17 verletzt: Feld(er) {', '.join(treffer)} duerfen nicht an den "
            f"Gegenpart gehen. Befund ohne Bildfeld uebergeben."
        )


def frage(befund: dict, schluessel: str, timeout: int = 60) -> dict:
    rumpf = json.dumps(
        {
            "model": MODELL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": evidenz_block(befund)},
            ],
        }
    ).encode("utf-8")
    anfrage = urllib.request.Request(
        ENDPUNKT,
        data=rumpf,
        headers={
            "Authorization": f"Bearer {schluessel}",
            "Content-Type": "application/json",
            "User-Agent": KENNUNG,
        },
    )
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
        return json.loads(antwort.read().decode("utf-8"))


def lies_spruch(antwort: dict) -> dict:
    """Zieht den Spruch aus der Anbieter-Antwort — unbekannter Wert ist `unklar`.

    Ein Anbieterfehler darf nie wie ein Urteil aussehen.
    """
    inhalt = antwort["choices"][0]["message"]["content"]
    geparst = json.loads(inhalt)
    spruch = str(geparst.get("spruch", "")).strip().lower()
    if spruch not in SPRUECHE:
        return {
            "spruch": "unklar",
            "begruendung": f"Gegenpart lieferte keinen gueltigen Spruch: {inhalt[:200]!r}",
        }
    return {"spruch": spruch, "begruendung": str(geparst.get("begruendung", ""))[:400]}


def schluessel_lesen() -> str:
    """Env vor Datei — der Wert wird nie ausgegeben, nur benutzt."""
    aus_env = os.environ.get("GROQ_API_KEY", "")
    if aus_env:
        return aus_env
    if SCHLUESSEL_DATEI.exists():
        return SCHLUESSEL_DATEI.read_text("utf-8").strip()
    return ""


def mehrheit(sprueche: list[dict]) -> dict:
    """Fasst mehrere Laeufe zusammen — Mehrheit, und ob sie einstimmig war.

    Ohne Mehrheit (drei verschiedene Sprueche) ist das Ergebnis `unklar`: der
    Gegenpart hat sich nicht entschieden, und das darf nicht wie eine
    Entscheidung aussehen.
    """
    werte = [s["spruch"] for s in sprueche]
    zaehler = {w: werte.count(w) for w in set(werte)}
    spitze = max(zaehler.values())
    gewinner = sorted(w for w, n in zaehler.items() if n == spitze)
    einig = len(zaehler) == 1

    if len(gewinner) > 1:
        return {
            "spruch": "unklar",
            "begruendung": (
                f"Keine Mehrheit ueber {len(werte)} Laeufe: {', '.join(werte)}. "
                "Der Gegenpart hat sich nicht entschieden (R9)."
            ),
            "laeufe": len(werte),
            "einig": False,
            "sprueche": werte,
        }

    erster = next(s for s in sprueche if s["spruch"] == gewinner[0])
    return {
        "spruch": gewinner[0],
        "begruendung": erster.get("begruendung", ""),
        "laeufe": len(werte),
        "einig": einig,
        "sprueche": werte,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--datei", help="Befund als JSON-Datei (sonst stdin)")
    p.add_argument(
        "--laeufe",
        type=int,
        default=LAEUFE,
        help=f"Anzahl Aufrufe je Befund (Vorgabe {LAEUFE}, R9 — weniger verschweigt die Streuung)",
    )
    p.add_argument(
        "--echtdaten",
        action="store_true",
        help="Der Lauf lief gegen echte Daten — dann wird NICHT gefragt (E17)",
    )
    args = p.parse_args(argv)

    roh = pathlib.Path(args.datei).read_text("utf-8") if args.datei else sys.stdin.read()
    befund = json.loads(roh)
    pruefe_eingabe(befund)

    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def raus(satz: dict) -> int:
        satz.setdefault("modell", MODELL)
        satz["geprueft_am"] = jetzt
        print(json.dumps(satz, ensure_ascii=False))
        return 0  # E16: der Spruch ist nie ein Gate

    if args.echtdaten:
        return raus({"spruch": "uebersprungen", "begruendung": "Echtdaten-Lauf (E17)"})

    schluessel = schluessel_lesen()
    if not schluessel:
        return raus(
            {
                "spruch": "uebersprungen",
                "begruendung": "Kein Schluessel — Zeiger fehlt und GROQ_API_KEY ist leer",
            }
        )

    einzeln = []
    for _ in range(max(1, args.laeufe)):
        try:
            antwort = frage(befund, schluessel)
        except (urllib.error.URLError, TimeoutError, OSError) as fehler:
            einzeln.append({"spruch": "unklar", "begruendung": f"Anbieter nicht erreichbar: {fehler}"})
            continue
        except (KeyError, ValueError) as fehler:
            einzeln.append({"spruch": "unklar", "begruendung": f"Antwort unlesbar: {fehler}"})
            continue
        einzeln.append(lies_spruch(antwort))

    return raus(mehrheit(einzeln))


if __name__ == "__main__":
    raise SystemExit(main())
