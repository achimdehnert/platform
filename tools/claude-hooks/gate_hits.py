#!/usr/bin/env python3
"""Treffer der Gate-Scanner mitschreiben — damit die FP-Kalibrierung Daten hat.

Warum es das gibt: KONZ-038 fuehrt neue Musterfamilien **advisory-first** ein und
verlangt vor dem Scharfschalten ein Fenster mit 0 Fehlalarmen (D2). Genau diese
Auswertung war am 2026-08-10 nicht moeglich — die drei Scanner schreiben ihre
Meldung in den Sitzungs-Kontext und **nichts** auf Platte. Nach dem Turn ist der
Treffer weg. Wie oft ein Gate gefeuert hat und wie oft zu Unrecht, liess sich
darum weder zaehlen noch bestreiten.

Dasselbe Muster steckt in zwei weiteren Befunden desselben Tages: der Megatest
meldet reduzierbare Budgets in einen Kanal, den niemand liest (#1865), und der
Hygiene-Melder zaehlt Leases, die das empfohlene Werkzeug nicht abraeumen kann
(#1866). Ein Mechanismus, dessen Ergebnis niemanden erreicht, ist kein
Mechanismus — er ist eine Behauptung.

Bewusst klein gehalten:

- **Eine Zeile JSON je Treffer**, angehaengt. Kein Zustand, keine Rotation, kein
  Schema-Zwang — ein kaputter Schreibvorgang darf den Hook nie stoeren.
- **Nur lokal** (`~/.claude/hooks/gate-hits.jsonl`). Die Zeile traegt einen
  Ausschnitt des eigenen Turns; der gehoert nie in ein Repo (Charta Art. 2).
- **Kontext begrenzt** auf das Noetigste, um spaeter „berechtigt oder Fehlalarm?"
  zu beantworten: der ausloesende Marker plus ein schmales Fenster darum.
- **Nie werfend.** Ein Scanner, der am Protokoll scheitert, waere schlimmer als
  gar kein Protokoll. Jeder Fehler wird geschluckt.

- **Kein Schreiben aus pytest heraus** (siehe `notiere`). Die Drills fahren die
  Scanner mit Fixture-Saetzen durch; ohne diese Sperre landet jeder Testlauf im
  Protokoll des Entwicklers und die FP-Auswertung urteilt ueber sich selbst.

Das Urteil selbst (`bewertung`) traegt die Zeile nicht — es entsteht beim
Ritual-Lauf, von Hand, und wird dort nachgetragen. `--bericht` weist vorher aus,
wie viele Zeilen **keine** session_id tragen, also nicht aus einer Sitzung kamen:
Herkunft vor Urteil.

Kommandos:
  --bericht [--seit YYYY-MM-DD]   Treffer je Gate zaehlen
  --zeilen  [--slug SLUG]         Treffer einzeln zeigen (zum Bewerten)
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

#: Nur lokal — die Zeilen tragen Ausschnitte eigener Turns (Charta Art. 2).
HITS = Path(
    os.environ.get(
        "GATE_HITS_DATEI", Path.home() / ".claude" / "hooks" / "gate-hits.jsonl"
    )
)

#: Zeichen links und rechts des Markers. Genug, um das Urteil zu faellen, zu wenig,
#: um den Turn zu rekonstruieren.
KONTEXT = 120


def _unter_test() -> bool:
    """Laeuft dieser Aufruf gerade in pytest?

    pytest setzt `PYTEST_CURRENT_TEST` je Test; ausserhalb ist die Variable nicht
    gesetzt. Der Hook-Pfad ist davon nie betroffen.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _ausschnitt(text: str, marker: str) -> str:
    if not text:
        # Ohne Turn-Text bleibt nur der Marker — das ist KEIN Beleg, und genau
        # dieser Fall hat das Kalibrierfenster wertlos gemacht (s. notiere()).
        return marker[: KONTEXT * 2] if marker else ""
    if not marker:
        return text[: KONTEXT * 2].replace("\n", " ").strip()
    stelle = text.find(marker)
    if stelle < 0:
        # Marker ist ein Label (`kinds=...`), kein Zitat: dann lieber den Anfang
        # des Turns als gar nichts — beurteilen kann man nur, was dasteht.
        return text[: KONTEXT * 2].replace("\n", " ").strip()
    start = max(0, stelle - KONTEXT)
    ende = min(len(text), stelle + len(marker) + KONTEXT)
    return text[start:ende].replace("\n", " ").strip()


def notiere(
    slug: str,
    marker: str,
    *,
    turn: str = "",
    beleg: str = "",
    session: str = "",
    modus: str = "advisory",
    pfad: Path | None = None,
) -> bool:
    """Einen Treffer anhaengen. Rueckgabe sagt nur, ob es geklappt hat.

    Wirft nie: ein Scanner, der am Protokoll stirbt, richtet mehr Schaden an als
    ein fehlender Datenpunkt.

    **Schreibt unter pytest nicht in das echte Protokoll.** Die Scanner-Drills
    fahren `scanner.main()` mit Fixture-Saetzen durch, und `main()` ruft diese
    Funktion ohne `pfad` — die Treffer landeten damit im Protokoll des Entwicklers.
    Realfall 2026-08-15: alle 212 protokollierten Treffer des Fensters 10.-13.08.
    stammten aus `pytest`, kein einziger aus einer echten Sitzung (`session` war
    durchgaengig leer). Die FP-Auswertung nach KONZ-038 D2 haette auf Rauschen
    geurteilt, das wie Datengrundlage aussah. Wer bewusst aus einem Test heraus
    schreiben will, gibt `pfad` an — dann greift die Sperre nicht.
    """
    if pfad is None and _unter_test():
        return False
    ziel = pfad or HITS
    zeile = {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "slug": slug,
        "modus": modus,
        "marker": marker[:200],
        "ausschnitt": _ausschnitt(turn, beleg or marker),
        "session": session[:64],
    }
    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with ziel.open("a", encoding="utf-8") as datei:
            datei.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def lies(pfad: Path | None = None) -> list[dict]:
    """Alle Treffer lesen. Kaputte Zeilen werden uebersprungen, nicht geworfen."""
    ziel = pfad or HITS
    if not ziel.exists():
        return []
    treffer: list[dict] = []
    for zeile in ziel.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            treffer.append(json.loads(zeile))
        except json.JSONDecodeError:
            continue
    return treffer


def bericht(treffer: list[dict], seit: str = "") -> str:
    gefiltert = [t for t in treffer if not seit or t.get("zeit", "") >= seit]
    if not gefiltert:
        return (
            "Keine Treffer protokolliert"
            + (f" seit {seit}" if seit else "")
            + ".\nDas ist KEIN Beleg fuer 0 Fehlalarme — es kann auch heissen, dass"
            " nie ein Gate gefeuert hat oder das Protokoll erst kurz laeuft."
        )
    je_slug = Counter(t.get("slug", "?") for t in gefiltert)
    tage = sorted({t.get("zeit", "")[:10] for t in gefiltert})
    zeilen = [
        f"Treffer gesamt: {len(gefiltert)}"
        + (f" seit {seit}" if seit else "")
        + f" · Fenster {tage[0]} … {tage[-1]} ({len(tage)} Tag(e) mit Treffern)",
        "",
    ]
    for slug, anzahl in je_slug.most_common():
        modi = {t.get("modus", "?") for t in gefiltert if t.get("slug") == slug}
        zeilen.append(f"  {anzahl:4d}  {slug}  ({'/'.join(sorted(modi))})")

    # Herkunft VOR Urteil. Ein echter Hook-Lauf traegt die session_id des Events;
    # eine Zeile ohne sie kam nicht aus einer Sitzung, sondern aus einem Direkt-
    # oder Testaufruf. Ohne diese Trennung liest sich Rauschen wie Datengrundlage
    # (Realfall 2026-08-15: 212 von 212 Zeilen stammten aus pytest).
    ohne_session = [t for t in gefiltert if not t.get("session")]
    zeilen.append("")
    if ohne_session:
        zeilen += [
            f"⚠ {len(ohne_session)} von {len(gefiltert)} Zeile(n) ohne session_id —",
            "  NICHT aus einer Sitzung, also kein Beleg fuer irgendeine FP-Quote.",
            "  Vor dem Urteil aussortieren (Direkt-/Testaufrufe, Protokoll-Reste).",
        ]
    else:
        zeilen.append(
            f"Herkunft: alle {len(gefiltert)} Zeile(n) tragen eine session_id."
        )

    zeilen += [
        "",
        "Fehlalarm-Quote: NICHT ableitbar aus dieser Zahl — jede Zeile muss von",
        "Hand beurteilt werden (--zeilen). Die Datei traegt bewusst kein Urteil.",
    ]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bericht", action="store_true", help="Treffer je Gate zaehlen"
    )
    parser.add_argument("--zeilen", action="store_true", help="Treffer einzeln zeigen")
    parser.add_argument(
        "--slug", default="", help="zu --zeilen: auf ein Gate begrenzen"
    )
    parser.add_argument("--seit", default="", help="nur ab diesem Datum (YYYY-MM-DD)")
    parser.add_argument("--datei", default="", help="anderes Protokoll")
    args = parser.parse_args(argv)

    pfad = Path(args.datei) if args.datei else None
    treffer = lies(pfad)

    if args.zeilen:
        for t in treffer:
            if args.slug and t.get("slug") != args.slug:
                continue
            if args.seit and t.get("zeit", "") < args.seit:
                continue
            print(f"{t.get('zeit')}  {t.get('slug')}  Marker: {t.get('marker')!r}")
            if t.get("ausschnitt"):
                print(f"    … {t['ausschnitt']} …")
        return 0

    print(bericht(treffer, args.seit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
