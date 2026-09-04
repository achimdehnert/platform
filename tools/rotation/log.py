"""Lauf-Protokoll ``infra/rotation-log.jsonl`` und der Ausgabefilter.

Eine Zeile je Lauf, append-only, im Git neben dem Inventar (AD-2: eine zweite
Wahrheit in einer Datenbank waere schlimmer als keine). Kein Feld traegt einen
Wert; was ein Lauf ueber den Wert sagt, ist der Fingerabdruck.

Der **Filter** ist die eigentliche Sicherung. Er laeuft vor jedem Schreiben und
vor jeder Ausgabe, nicht als Review-Regel: die Klasse "jemand hat den Wert in
eine Fehlermeldung gehaengt" ist genau die, die kein Mensch im Diff sieht.
``ol_api_`` steht bewusst mit in der Liste, obwohl gitleaks es NICHT kennt — das
Outline-Token war der Anlass fuer platform#2353.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

LOG_PFAD = Path(__file__).resolve().parent.parent.parent / "infra" / "rotation-log.jsonl"

#: (Name, Muster). Der Name wandert in die Fehlermeldung, das Treffer-Material
#: NIE — sonst schriebe der Filter selbst den Wert ins Transkript.
MUSTER: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("outline-api-token", re.compile(r"ol_api_")),
    ("github-pat-klassisch", re.compile(r"ghp_")),
    ("github-pat-fein", re.compile(r"github_pat_")),
    ("github-app-token", re.compile(r"ghs_")),
    ("pem-privatschluessel", re.compile(r"-----BEGIN")),
)


class WertGefunden(RuntimeError):
    """Ein Token-Muster steht in etwas, das geschrieben oder ausgegeben werden soll."""


def treffer(text: str) -> list[str]:
    """Namen der greifenden Muster. Nie das gefundene Material."""
    return [name for name, muster in MUSTER if muster.search(text)]


def filtere(text: str, wo: str = "Ausgabe") -> str:
    """Gibt ``text`` zurueck — oder wirft, wenn ein Muster greift.

    Bewusst kein stilles Schwaerzen: eine geschwaerzte Zeile im Log sieht aus
    wie ein sauberer Lauf, und der Wert waere trotzdem einmal durch den Prozess
    gelaufen. Der Lauf muss laut abbrechen.
    """
    gefunden = treffer(text)
    if gefunden:
        raise WertGefunden(
            f"{wo}: Token-Muster erkannt ({', '.join(gefunden)}). "
            "Nichts geschrieben, nichts ausgegeben — der Wert gehoert weder ins "
            "Log noch in eine Meldung."
        )
    return text


def _als_text(daten: Any) -> str:
    return json.dumps(daten, ensure_ascii=False, sort_keys=True)


def pruefe_zeile(zeile: dict[str, Any]) -> None:
    filtere(_als_text(zeile), wo="Log-Zeile")


def schreibe(zeile: dict[str, Any], pfad: Path | None = None) -> None:
    """Haengt eine geprueft wertfreie Zeile an. Append-only, kein Rewrite."""
    pfad = pfad or LOG_PFAD
    pruefe_zeile(zeile)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        datei.write(json.dumps(zeile, ensure_ascii=False, sort_keys=True) + "\n")


def lies(pfad: Path | None = None) -> list[dict[str, Any]]:
    pfad = pfad or LOG_PFAD
    if not pfad.is_file():
        return []
    raus = []
    for nr, roh in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        roh = roh.strip()
        if not roh:
            continue
        try:
            raus.append(json.loads(roh))
        except json.JSONDecodeError as fehler:
            raise ValueError(f"{pfad}:{nr} ist kein JSON: {fehler.msg}") from fehler
    return raus


def pruefe_datei(pfad: Path | None = None) -> list[str]:
    """Befunde als Textzeilen; leer = sauber. Leser: der PR-Check."""
    pfad = pfad or LOG_PFAD
    if not pfad.is_file():
        return []
    befunde = []
    for nr, roh in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        gefunden = treffer(roh)
        if gefunden:
            befunde.append(f"{pfad.name}:{nr} — {', '.join(gefunden)}")
    return befunde


def letzter_lauf(secret: str, eintraege: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """Juengster Lauf zu diesem Secret — auch ein `offen` gebliebener zaehlt.

    Absicht: ein gescheiterter Lauf darf die Faelligkeit NICHT zuruecksetzen.
    Deshalb liefert diese Funktion die Zeile, und die Faelligkeit fragt danach
    nach ``status``; ein `offen` gilt dort wie "nie gelaufen".
    """
    passend = [e for e in eintraege if e.get("secret") == secret]
    if not passend:
        return None
    return max(passend, key=lambda e: e.get("gestartet") or "")


def naechste_lauf_id(secret: str, eintraege: Iterable[dict[str, Any]], heute: str) -> str:
    """``<secret>-<YYYY-MM-DD>-<n>`` — lesbar und im Log eindeutig."""
    praefix = f"{secret}-{heute}"
    belegt = sum(1 for e in eintraege if str(e.get("lauf_id", "")).startswith(praefix))
    return f"{praefix}-{belegt + 1}"
