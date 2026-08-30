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

Aufruf:
    python3 tools/ux_falsifikator.py --datei befund.json
    python3 tools/ux_falsifikator.py < befund.json

Eingabe (JSON): klasse, severity, symptom, station, antwortkoerper,
gegenprobe, referenz, bekannt (bool).
Ausgabe (JSON): spruch, begruendung, modell, geprueft_am.
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--datei", help="Befund als JSON-Datei (sonst stdin)")
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

    try:
        antwort = frage(befund, schluessel)
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        return raus({"spruch": "unklar", "begruendung": f"Anbieter nicht erreichbar: {fehler}"})
    except (KeyError, ValueError) as fehler:
        return raus({"spruch": "unklar", "begruendung": f"Antwort unlesbar: {fehler}"})

    return raus(lies_spruch(antwort))


if __name__ == "__main__":
    raise SystemExit(main())
