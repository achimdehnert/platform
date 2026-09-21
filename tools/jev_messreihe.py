#!/usr/bin/env python3
"""jev_messreihe.py — alle zwei Tage: waechst der Lerndatensatz, und trennt er?

Hintergrund (platform#3337): Ein Handlauf am 2026-09-21 gegen acht PASS- und
acht WARN-Zeilen ergab fuer ein Entscheidungsmodell von der Stange eine AUC von
0,477 — kein Signal. **Das ist ein Anhaltspunkt, kein Urteil:** acht Faelle je
Klasse liegen unter der Schwelle, die dieses Werkzeug selbst verlangt (siehe
MINDESTENS_JE_KLASSE weiter unten), und was dort fuer andere gilt, gilt auch
fuer den eigenen Gruendungsbefund. Genau deshalb gibt es dieses Werkzeug: um
die Frage mit genug Faellen noch einmal zu stellen.

Die Arbeitsannahme dahinter: Was ein echter Befund ist, steht nicht in der
Meldung, sondern in unserer Vorgeschichte mit dem Melder. Die liegt allein in
unseren eigenen Urteilen vor.

Seit #3339 legt `befund_journal.py` zu jedem Urteil den beurteilten Meldetext
mit (`eingabe`). Dieses Werkzeug beobachtet zweierlei:

  1. **Datenlage** — waechst der Satz, ist er ausgewogen, wie viele Paare sind
     ueberhaupt brauchbar? Das ist die Kennzahl, die zuerst zaehlt: ohne Daten
     ist jede Trennschaerfe-Messung Rauschen.
  2. **Trennschaerfe** — erst ab `--mindestens` Paaren je Klasse wird gemessen.
     Darunter meldet das Werkzeug ehrlich `noch nicht messbar` und gibt KEINE
     Zahl aus. Eine AUC ueber vier Faelle ist schlimmer als keine, weil sie
     beruhigt.

Der Lauf haengt an einem erreichbaren kev-Dienst. Ist er weg, ist das ein
Befund ueber den Dienst, kein Messergebnis — auch dann wird nichts geraten.

Aufruf:
  python3 tools/jev_messreihe.py                 # Bericht, misst wenn moeglich
  python3 tools/jev_messreihe.py --nur-datenlage # ohne Modell, nur zaehlen
  python3 tools/jev_messreihe.py --json          # maschinenlesbar

stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

JOURNAL = Path.home() / ".claude" / "befund-journal.json"
MESSREIHE = Path.home() / ".claude" / "jev-messreihe.jsonl"

#: Unter dieser Zahl je Klasse wird NICHT gemessen. Zehn ist keine schoene
#: Stichprobe, aber unterhalb davon schwankt die AUC so stark, dass ein
#: Ausreisser wie ein Trend aussieht — und ein Trend wie ein Ergebnis.
MINDESTENS_JE_KLASSE = 10

#: Die Frage, gegen die gemessen wird. Absichtlich dieselbe Formulierung wie
#: beim Handlauf am 2026-09-21, sonst ist die Reihe nicht vergleichbar.
FRAGE = "Beschreibt dieser Text einen echten Befund, der Arbeit ausloest?"

#: Zugang zur GPU-Box: prod -> wg0-Peer -> WSL. Der kev-Dienst lauscht dort
#: nur auf 127.0.0.1, deshalb laeuft die Schleife AUF der Box statt hier.
HOP = "ssh -o BatchMode=yes achim@10.99.0.2"
WSL = "wsl -d Ubuntu -u root -e bash -c"
FERN_SKRIPT = Path(__file__).with_name("jev_frag_remote.py")


def _ssh(inneres: str, eingabe: str | None = None) -> subprocess.CompletedProcess:
    """Ein Befehl in der WSL der Box. Anfuehrungszeichen ueberleben cmd.exe
    nicht — deshalb nur einfache Befehle hier, alles andere per Datei."""
    return subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "hetzner-prod",
            f"{HOP} '{WSL} \"{inneres}\"'",
        ],
        input=eingabe,
        capture_output=True,
        text=True,
        timeout=600,
    )


def lade_paare() -> tuple[list[dict], dict[str, int]]:
    """Urteile MIT Eingabetext. Zweiter Rueckgabewert: die Maengel-Zaehlung."""
    if not JOURNAL.is_file():
        return [], {"journal_fehlt": 1}
    daten = json.loads(JOURNAL.read_text(encoding="utf-8"))
    urteile = daten.get("urteile", [])
    maengel = {"ohne_eingabe": 0, "leere_eingabe": 0, "dubletten": 0}
    gesehen: set[tuple[str, str]] = set()
    paare: list[dict] = []
    for u in urteile:
        text = u.get("eingabe")
        if text is None:
            maengel["ohne_eingabe"] += 1
            continue
        if not str(text).strip():
            maengel["leere_eingabe"] += 1
            continue
        schluessel = (str(text), u.get("urteil", ""))
        if schluessel in gesehen:
            maengel["dubletten"] += 1
            continue
        gesehen.add(schluessel)
        paare.append(
            {"text": str(text), "urteil": u.get("urteil"), "datum": u.get("datum")}
        )
    return paare, maengel


def frage_modell(texte: list[str]) -> list[float] | None:
    """Wahrscheinlichkeiten vom kev-Dienst. None, wenn etwas nicht traegt.

    Bewusst None statt eines Naeherungswerts: ein nicht erreichbarer Dienst ist
    ein Befund ueber den Dienst, kein Messergebnis.
    """
    if not FERN_SKRIPT.is_file():
        return None
    fragen = json.dumps(
        {"befund": {"type": "noul", "instructions": FRAGE}}, ensure_ascii=False
    )
    # Die Frageform wandert bei JEDEM Lauf mit, sonst misst eine spaetere
    # Messung womoeglich gegen eine alte Datei auf der Box.
    for inneres, inhalt in (
        ("cat > /root/jev_frag_remote.py", FERN_SKRIPT.read_text(encoding="utf-8")),
        ("cat > /root/messreihe_fragen.json", fragen),
        (
            "cat > /root/messreihe_texte.txt",
            "\n".join(t.replace("\n", " ") for t in texte) + "\n",
        ),
    ):
        if _ssh(inneres, inhalt).returncode != 0:
            return None

    lauf = _ssh(
        "python3 /root/jev_frag_remote.py /root/messreihe_texte.txt "
        "/root/messreihe_fragen.json --json"
    )
    if lauf.returncode != 0:
        return None
    werte: list[float] = []
    for zeile in lauf.stdout.splitlines():
        if not zeile.strip().startswith("{"):
            continue
        try:
            werte.append(float(json.loads(zeile)["answers"]["befund"]["noul"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
    return werte if len(werte) == len(texte) else None


def auc(positiv: list[float], negativ: list[float]) -> float:
    """Anteil der Paare, in denen ein Befund hoeher liegt als ein Nicht-Befund.

    0,5 ist Zufall. Bindungen zaehlen halb — sonst schoenen viele gleiche
    Werte das Ergebnis in die Richtung, in der zufaellig sortiert wurde.
    """
    paare = [(p, n) for p in positiv for n in negativ]
    if not paare:
        return 0.5
    besser = sum(p > n for p, n in paare) + 0.5 * sum(p == n for p, n in paare)
    return besser / len(paare)


def beste_trefferquote(positiv: list[float], negativ: list[float]) -> float:
    gesamt = len(positiv) + len(negativ)
    if not gesamt:
        return 0.0
    return max(
        (sum(p >= s for p in positiv) + sum(n < s for n in negativ)) / gesamt
        for s in sorted({*positiv, *negativ})
    )


def vorheriger_lauf() -> dict | None:
    if not MESSREIHE.is_file():
        return None
    zeilen = [
        z for z in MESSREIHE.read_text(encoding="utf-8").splitlines() if z.strip()
    ]
    return json.loads(zeilen[-1]) if zeilen else None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--nur-datenlage", action="store_true", help="nicht messen, nur zaehlen"
    )
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument("--mindestens", type=int, default=MINDESTENS_JE_KLASSE)
    p.add_argument(
        "--datei", type=Path, default=None, help="Messreihe woanders ablegen"
    )
    a = p.parse_args()
    satz, vorher, ziel = main_fuer_test(
        mindestens=a.mindestens, nur_datenlage=a.nur_datenlage, ziel=a.datei
    )
    maengel = satz["maengel"]

    if a.als_json:
        print(json.dumps(satz, ensure_ascii=False))
        return 0
    return _bericht(satz, vorher, maengel, ziel)


def main_fuer_test(
    mindestens: int = MINDESTENS_JE_KLASSE,
    nur_datenlage: bool = False,
    ziel: Path | None = None,
) -> tuple[dict, dict | None, Path]:
    """Der Kern ohne argparse.

    Existiert, damit die Drills die Entscheidung testen (messen oder nicht?)
    statt der Kommandozeile — und damit ein Test den Netzaufruf ersetzen kann,
    ohne die CLI nachzubauen.
    """
    ziel = ziel or MESSREIHE
    paare, maengel = lade_paare()
    echt = [x["text"] for x in paare if x["urteil"] == "echt"]
    falsch = [x["text"] for x in paare if x["urteil"] == "falsch"]

    satz: dict = {
        "datum": date.today().isoformat(),
        "paare": len(paare),
        "echt": len(echt),
        "falsch": len(falsch),
        "maengel": maengel,
        "auc": None,
        "beste_trefferquote": None,
        "status": None,
    }

    if len(echt) < mindestens or len(falsch) < mindestens:
        satz["status"] = (
            f"noch nicht messbar — {len(echt)}/{len(falsch)} je Klasse, "
            f"gebraucht {mindestens}"
        )
    elif nur_datenlage:
        satz["status"] = "nur Datenlage erhoben"
    else:
        werte_echt = frage_modell(echt)
        werte_falsch = frage_modell(falsch) if werte_echt is not None else None
        if werte_echt is None or werte_falsch is None:
            satz["status"] = "kev-Dienst nicht erreichbar — kein Messergebnis"
        else:
            satz["auc"] = round(auc(werte_echt, werte_falsch), 3)
            satz["beste_trefferquote"] = round(
                beste_trefferquote(werte_echt, werte_falsch), 3
            )
            satz["status"] = "gemessen"

    vorher = vorheriger_lauf()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with ziel.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(satz, ensure_ascii=False) + "\n")
    return satz, vorher, ziel


def _bericht(satz: dict, vorher: dict | None, maengel: dict, ziel: Path) -> int:
    print(f"Jev-Messreihe (#3337) — {satz['datum']}")
    zuwachs = ""
    if vorher:
        delta = satz["paare"] - vorher.get("paare", 0)
        zuwachs = f"  ({delta:+d} seit {vorher.get('datum')})"
    print(f"  Paare mit Eingabetext : {satz['paare']}{zuwachs}")
    print(f"  davon echt / falsch   : {satz['echt']} / {satz['falsch']}")
    if any(maengel.values()):
        teile = ", ".join(f"{k}: {v}" for k, v in maengel.items() if v)
        print(f"  Maengel               : {teile}")
    print(f"  Status                : {satz['status']}")
    if satz["auc"] is not None:
        print(f"  AUC (0,5 = Zufall)    : {satz['auc']:.3f}")
        print(f"  beste Trefferquote    : {satz['beste_trefferquote']:.3f}")
        if vorher and vorher.get("auc") is not None:
            print(f"  Vorlauf-AUC           : {vorher['auc']:.3f}")
    print(f"  Reihe                 : {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
