#!/usr/bin/env python3
"""Egress-Allowlist der Sandbox (platform#3685, ADR-308 §4.3) — einziger Weg nach aussen.

Der Sandbox-Container haengt an einem internen Docker-Netz ohne Gateway; nach
aussen kommt er nur ueber diesen Proxy. Erlaubt ist ausschliesslich CONNECT auf
Port 443 zu Modell-API und GitHub, alles andere bekommt 403. Jede Entscheidung
geht als JSON-Zeile auf stdout; sandbox.sh legt sie ausserhalb der
Agenten-Reichweite ab (Zaehlung B5b).

Nur Standardbibliothek, laeuft aus demselben Bild in einem eigenen Container.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
from datetime import datetime, timezone

ERLAUBTE_ZIELE = frozenset(
    {
        "api.anthropic.com",
        "github.com",
        "api.github.com",
        "codeload.github.com",
        "uploads.github.com",
    }
)
ERLAUBTER_PORT = 443
PUFFER = 65536


def ziel_erlaubt(
    host: str, port: int, erlaubt: frozenset[str] = ERLAUBTE_ZIELE
) -> bool:
    return port == ERLAUBTER_PORT and host.lower().rstrip(".") in erlaubt


def lies_anfrage(verbindung: socket.socket) -> tuple[str, str]:
    """Liefert (Methode, Ziel) der ersten Anfragezeile; Kopfzeilen werden verworfen."""
    daten = b""
    while b"\r\n\r\n" not in daten and len(daten) < PUFFER:
        teil = verbindung.recv(4096)
        if not teil:
            break
        daten += teil
    zeile = daten.split(b"\r\n", 1)[0].decode("latin-1")
    teile = zeile.split()
    return (teile[0].upper(), teile[1]) if len(teile) >= 2 else ("", "")


def zerlege_ziel(ziel: str) -> tuple[str, int] | None:
    host, _, port = ziel.rpartition(":")
    if not host or not port.isdigit():
        return None
    return host.strip("[]"), int(port)


def protokolliere(**zeile) -> None:
    zeile = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **zeile}
    print(json.dumps(zeile), flush=True)


def weiterleiten(von: socket.socket, nach: socket.socket) -> None:
    try:
        while daten := von.recv(PUFFER):
            nach.sendall(daten)
    except OSError:
        pass
    finally:
        for s in (von, nach):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def bediene(verbindung: socket.socket, erlaubt: frozenset[str]) -> None:
    with verbindung:
        methode, ziel = lies_anfrage(verbindung)
        zerlegt = zerlege_ziel(ziel) if methode == "CONNECT" else None
        if zerlegt is None or not ziel_erlaubt(*zerlegt, erlaubt=erlaubt):
            protokolliere(entscheidung="verweigert", methode=methode, ziel=ziel)
            verbindung.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            return
        try:
            gegenstelle = socket.create_connection(zerlegt, timeout=30)
        except OSError as fehler:
            protokolliere(entscheidung="unerreichbar", ziel=ziel, fehler=str(fehler))
            verbindung.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            return
        protokolliere(entscheidung="erlaubt", ziel=ziel)
        gegenstelle.settimeout(None)
        verbindung.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        rueck = threading.Thread(
            target=weiterleiten, args=(gegenstelle, verbindung), daemon=True
        )
        rueck.start()
        weiterleiten(verbindung, gegenstelle)
        rueck.join()
        gegenstelle.close()


def starte(
    adresse: tuple[str, int], erlaubt: frozenset[str] = ERLAUBTE_ZIELE
) -> socket.socket:
    server = socket.create_server(adresse, reuse_port=False)
    server.listen(64)

    def annehmen() -> None:
        while True:
            try:
                verbindung, _ = server.accept()
            except OSError:
                return
            threading.Thread(
                target=bediene, args=(verbindung, erlaubt), daemon=True
            ).start()

    threading.Thread(target=annehmen, daemon=True).start()
    return server


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3128
    starte(("0.0.0.0", port))
    protokolliere(entscheidung="bereit", port=port, ziele=sorted(ERLAUBTE_ZIELE))
    threading.Event().wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
