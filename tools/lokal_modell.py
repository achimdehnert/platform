"""Lokales Sprachmodell (GX10) fuer vertraulich markierte Kundeninhalte.

Anlass platform#4049: Seit dem Gate `vertrauliches-verlaesst-ablage` (#4048)
duerfen markierte Inhalte nicht mehr zu fremden Modellen. Zusammenfassen und
Einordnen, das die Routing-Regel sonst an Billiganbieter gibt, laeuft fuer
diese Inhalte hier: ueber einen SSH-Tunnel auf localhost zu Ollama.

Das Werkzeug kennt nur Loopback. Ist das Geraet aus oder der Tunnel weg, endet
es mit Exit 3 und einer klaren Meldung — es gibt KEINE Ausweichroute nach
aussen. Ein stiller Rueckfall auf einen fremden Anbieter waere genau der
Abfluss, den das Gate verhindert.

Sprung-Host, Zieladresse und Port stehen NICHT hier (Repo oeffentlich), sondern
in `~/.claude/lokal_modell.json` (Env `LOKAL_MODELL_KONFIG`), Muster:
`tools/lokal_modell.beispiel.json`.

Jeder Aufruf begrenzt `num_predict`, setzt `think: false` und `keep_alive: 0`:
ein unbegrenzter Aufruf blockierte am 2026-09-24 die geteilte GX10, und ein
geladenes Modell belegt Speicher, den andere Dienste dort brauchen.

Exit-Codes: 0 ok · 2 Konfiguration/Aufruf abgelehnt · 3 nicht erreichbar ·
4 Modell fehlt · 5 Generierung fehlgeschlagen.

    python3 tools/lokal_modell.py --pruefen
    python3 tools/lokal_modell.py --datei ~/vertraulich/<kunde>/mail.txt
    echo "Text" | python3 tools/lokal_modell.py --anweisung "Ordne ein: ..."
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

KONFIG_ENV = "LOKAL_MODELL_KONFIG"
KONFIG_STANDARD = "~/.claude/lokal_modell.json"
LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
PRUEF_TIMEOUT_S = 5
TUNNEL_WARTEN_S = 15

OK, ABGELEHNT, NICHT_ERREICHBAR, MODELL_FEHLT, GENERIERUNG = 0, 2, 3, 4, 5


class Fehler(Exception):
    def __init__(self, code: int, text: str) -> None:
        super().__init__(text)
        self.code = code


class Konfig:
    PFLICHT = (
        "basis_url",
        "modell",
        "num_predict",
        "timeout_s",
        "max_zeichen",
        "standard_anweisung",
        "verbotene_modelle",
    )

    def __init__(self, roh: dict) -> None:
        fehlt = [k for k in self.PFLICHT if k not in roh]
        if fehlt:
            raise Fehler(
                ABGELEHNT, f"Konfiguration unvollstaendig, fehlt: {', '.join(fehlt)}"
            )
        self.basis_url = str(roh["basis_url"]).rstrip("/")
        self.modell = str(roh["modell"])
        self.num_predict = int(roh["num_predict"])
        self.timeout_s = float(roh["timeout_s"])
        self.max_zeichen = int(roh["max_zeichen"])
        self.standard_anweisung = str(roh["standard_anweisung"])
        self.verbotene_modelle = [str(v).lower() for v in roh["verbotene_modelle"]]
        self.tunnel = roh.get("tunnel") or None
        if urlparse(self.basis_url).hostname not in LOOPBACK:
            raise Fehler(
                ABGELEHNT,
                "basis_url zeigt nicht auf localhost — das Werkzeug geht nie direkt nach aussen.",
            )
        if self.num_predict <= 0:
            raise Fehler(ABGELEHNT, "num_predict muss begrenzt sein (> 0).")
        pruefe_modell_erlaubt(self.modell, self.verbotene_modelle)


def konfig_pfad() -> Path:
    return Path(os.path.expanduser(os.environ.get(KONFIG_ENV) or KONFIG_STANDARD))


def lade_konfig(pfad: Path) -> Konfig:
    if not pfad.exists():
        raise Fehler(
            ABGELEHNT,
            f"Konfiguration `{pfad}` fehlt — Muster: tools/lokal_modell.beispiel.json.",
        )
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Fehler(
            ABGELEHNT, f"Konfiguration `{pfad}` nicht lesbar ({type(exc).__name__})."
        ) from exc
    return Konfig(roh)


def pruefe_modell_erlaubt(modell: str, verboten: list[str]) -> None:
    treffer = [v for v in verboten if v in modell.lower()]
    if treffer:
        raise Fehler(
            ABGELEHNT,
            f"Modell `{modell}` ist fuer Kundenarbeit gesperrt ({treffer[0]}).",
        )


def _hole(url: str, timeout: float, nutzlast: dict | None = None) -> dict:
    daten = None if nutzlast is None else json.dumps(nutzlast).encode("utf-8")
    anfrage = urllib.request.Request(
        url, data=daten, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:  # noqa: S310 — nur Loopback (Konfig)
        return json.loads(antwort.read().decode("utf-8"))


def verfuegbare_modelle(k: Konfig) -> list[str] | None:
    """Modellnamen am Endpunkt, oder None, wenn er nicht antwortet."""
    try:
        return [
            m.get("name", "")
            for m in _hole(f"{k.basis_url}/api/tags", PRUEF_TIMEOUT_S).get("models", [])
        ]
    except (OSError, ValueError, urllib.error.URLError):
        return None


def tunnel_befehl(k: Konfig) -> list[str]:
    t = k.tunnel or {}
    if not t.get("sprung") or not t.get("ziel"):
        raise Fehler(
            NICHT_ERREICHBAR, "Kein Tunnel konfiguriert (tunnel.sprung, tunnel.ziel)."
        )
    teile = urlparse(k.basis_url)
    return [
        "ssh",
        "-f",
        "-N",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-L",
        f"{teile.hostname}:{teile.port}:{t['ziel']}",
        str(t["sprung"]),
    ]


def erreiche(k: Konfig, tunnel_oeffnen: bool = True) -> list[str]:
    """Modelle am Endpunkt; oeffnet bei Bedarf den Tunnel. Sonst Exit 3."""
    modelle = verfuegbare_modelle(k)
    if modelle is None and tunnel_oeffnen and k.tunnel:
        lauf = subprocess.run(
            tunnel_befehl(k), capture_output=True, text=True, timeout=30
        )
        if lauf.returncode == 0:
            ende = time.monotonic() + TUNNEL_WARTEN_S
            while modelle is None and time.monotonic() < ende:
                time.sleep(1)
                modelle = verfuegbare_modelle(k)
    if modelle is None:
        raise Fehler(
            NICHT_ERREICHBAR,
            "GX10 nicht erreichbar: Geraet aus, Tunnel weg oder Ollama gestoppt. "
            "Kein Ausweichen nach aussen — Aufgabe liegen lassen oder Owner fragen.",
        )
    if k.modell not in modelle:
        raise Fehler(
            MODELL_FEHLT, f"Modell `{k.modell}` ist auf der GX10 nicht vorhanden."
        )
    return modelle


def nutzlast(k: Konfig, anweisung: str, text: str) -> dict:
    return {
        "model": k.modell,
        "prompt": f"{anweisung}\n\n{text}",
        "stream": False,
        "think": False,
        "keep_alive": 0,
        "options": {"num_predict": k.num_predict},
    }


def generiere(k: Konfig, anweisung: str, text: str) -> dict:
    if len(text) > k.max_zeichen:
        raise Fehler(
            ABGELEHNT,
            f"Text hat {len(text)} Zeichen, Grenze {k.max_zeichen} — teilen statt kuerzen.",
        )
    try:
        antwort = _hole(
            f"{k.basis_url}/api/generate", k.timeout_s, nutzlast(k, anweisung, text)
        )
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise Fehler(
            GENERIERUNG, f"Generierung fehlgeschlagen ({type(exc).__name__})."
        ) from exc
    if antwort.get("error") or not str(antwort.get("response") or "").strip():
        raise Fehler(
            GENERIERUNG,
            f"Leere oder fehlerhafte Antwort: {str(antwort.get('error') or 'leer')[:200]}",
        )
    return antwort


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--datei", help="Eingabetext aus Datei (sonst stdin)")
    p.add_argument(
        "--anweisung", help="Anweisung vor dem Text (Standard aus der Konfiguration)"
    )
    p.add_argument(
        "--pruefen", action="store_true", help="nur Erreichbarkeit und Modell pruefen"
    )
    p.add_argument("--ohne-tunnel", action="store_true", help="keinen Tunnel oeffnen")
    args = p.parse_args(argv)
    try:
        k = lade_konfig(konfig_pfad())
        erreiche(k, tunnel_oeffnen=not args.ohne_tunnel)
        if args.pruefen:
            print(f"GX10 erreichbar, Modell {k.modell} vorhanden.")
            return OK
        text = (
            Path(args.datei).expanduser().read_text(encoding="utf-8")
            if args.datei
            else sys.stdin.read()
        )
        antwort = generiere(k, args.anweisung or k.standard_anweisung, text)
    except Fehler as f:
        print(f"lokal_modell: {f}", file=sys.stderr)
        return f.code
    print(str(antwort["response"]).strip())
    print(
        f"lokal_modell: {k.modell}, {antwort.get('eval_count')} Token, "
        f"{(antwort.get('total_duration') or 0) / 1e9:.1f} s, lokal",
        file=sys.stderr,
    )
    return OK


if __name__ == "__main__":
    sys.exit(main())
