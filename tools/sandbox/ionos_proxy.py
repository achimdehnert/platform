#!/usr/bin/env python3
"""IONOS-Steuer-Proxy der Sandbox (ADR-308) — einziger Weg des Agenten zur IONOS Cloud API.

Der Agent haelt keinen IONOS-Zugang. Er spricht HTTP mit diesem Proxy; der Proxy
meldet sich per Basic-Auth als Agenten-Nutzer an (kein Token, also kein Ablauf und
kein verzoegerter Widerruf) und laesst nur eine Allowlist durch:

    GET  /zustand        Server, Volume, sichtbare Snapshots, letzte Aktionen
    POST /neustart       Neustart des einen Servers
    POST /start          Start des einen Servers
    POST /konsole        Konsolen-URL des einen Servers
    POST /snapshot       Snapshot des Root-Volumes; aelteste eigene vorher weg (Kostendeckel)
    POST /zurueckspielen {"snapshot": "<id>"} — nur eigene oder geschuetzte Snapshots

Alles andere bekommt 403. Server anlegen oder loeschen ist hier nicht moeglich, obwohl
der Agenten-Nutzer es bei IONOS duerfte (Negativtest 2026-10-17). Jede Entscheidung geht
als JSON-Zeile auf stdout und in die Aktionsliste von /zustand (Aufsetzpunkt fuer das
naechste Modell). Ziele und Grenzen stehen in einer Konfigurationsdatei ausserhalb des
Repos (Beispiel: ionos_proxy.beispiel.json).

Nur Standardbibliothek.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

API = "https://api.ionos.com/cloudapi/v6"
KONFIG_STANDARD = Path.home() / ".config" / "iil" / "ionos-proxy.json"
PFLICHTFELDER = (
    "datacenter",
    "server",
    "volume",
    "benutzer",
    "passwort_datei",
    "snapshot_praefix",
    "max_eigene_snapshots",
    "geschuetzte_snapshots",
    "mindestabstand_s",
)
AKTIONEN = {
    ("GET", "/zustand"),
    ("POST", "/neustart"),
    ("POST", "/start"),
    ("POST", "/konsole"),
    ("POST", "/snapshot"),
    ("POST", "/zurueckspielen"),
}
VERLAUF_LAENGE = 50


class Verweigert(Exception):
    def __init__(self, status: int, grund: str):
        super().__init__(grund)
        self.status, self.grund = status, grund


def lade_konfig(pfad: Path) -> dict:
    konfig = json.loads(pfad.read_text())
    fehlend = [f for f in PFLICHTFELDER if f not in konfig]
    if fehlend:
        raise ValueError(f"Konfiguration {pfad}: es fehlen {', '.join(fehlend)}")
    return konfig


def aktion_erlaubt(methode: str, pfad: str) -> bool:
    return (methode, pfad.split("?", 1)[0].rstrip("/") or "/") in AKTIONEN


def eigene_snapshots(snapshots: list[dict], praefix: str) -> list[dict]:
    """Vom Proxy angelegte Snapshots, aelteste zuerst."""
    eigene = [s for s in snapshots if s["name"].startswith(praefix)]
    return sorted(eigene, key=lambda s: s["angelegt"])


def zu_loeschen(snapshots: list[dict], konfig: dict) -> list[dict]:
    """Eigene Snapshots, die vor einem neuen weg muessen, damit der Deckel haelt."""
    eigene = [
        s
        for s in eigene_snapshots(snapshots, konfig["snapshot_praefix"])
        if s["id"] not in konfig["geschuetzte_snapshots"]
    ]
    ueberzahl = len(eigene) - konfig["max_eigene_snapshots"] + 1
    return eigene[: max(ueberzahl, 0)]


def zurueckspielen_erlaubt(snapshot_id: str, snapshots: list[dict], konfig: dict) -> bool:
    if snapshot_id in konfig["geschuetzte_snapshots"]:
        return True
    return any(
        s["id"] == snapshot_id for s in eigene_snapshots(snapshots, konfig["snapshot_praefix"])
    )


class IonosKlient:
    """Duenne Huelle um die Cloud API v6 mit Basic-Auth des Agenten-Nutzers."""

    def __init__(self, benutzer: str, passwort: str, api: str = API):
        paar = f"{benutzer}:{passwort}".encode()
        self._auth = "Basic " + base64.b64encode(paar).decode()
        self._api = api

    def anfrage(self, methode: str, pfad: str, form: dict | None = None) -> tuple[int, dict]:
        daten, kopf = None, {"Authorization": self._auth}
        if form is not None:
            daten = urllib.parse.urlencode(form).encode()
            kopf["Content-Type"] = "application/x-www-form-urlencoded"
        anfrage = urllib.request.Request(self._api + pfad, data=daten, method=methode, headers=kopf)
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                text = antwort.read().decode()
                return antwort.status, (json.loads(text) if text else {})
        except urllib.error.HTTPError as fehler:
            return fehler.code, {}


class Proxy:
    def __init__(self, konfig: dict, klient, uhr=time.monotonic):
        self.konfig, self.klient, self.uhr = konfig, klient, uhr
        self.verlauf: deque[dict] = deque(maxlen=VERLAUF_LAENGE)
        self._letzte: dict[str, float] = {}
        self._sperre = threading.Lock()

    def _server_pfad(self, suffix: str = "") -> str:
        k = self.konfig
        return f"/datacenters/{k['datacenter']}/servers/{k['server']}{suffix}"

    def _volume_pfad(self, suffix: str = "") -> str:
        k = self.konfig
        return f"/datacenters/{k['datacenter']}/volumes/{k['volume']}{suffix}"

    def _pruefe_abstand(self, aktion: str) -> None:
        jetzt, vorher = self.uhr(), self._letzte.get(aktion)
        abstand = self.konfig["mindestabstand_s"].get(aktion, 0)
        if vorher is not None and jetzt - vorher < abstand:
            raise Verweigert(429, f"{aktion}: Mindestabstand {abstand}s nicht erreicht")
        self._letzte[aktion] = jetzt

    def _ionos(self, methode: str, pfad: str, form: dict | None = None) -> dict:
        status, daten = self.klient.anfrage(methode, pfad, form)
        if status >= 400:
            raise Verweigert(502, f"IONOS antwortet {status} auf {methode} {pfad.split('?')[0]}")
        return daten

    def snapshots(self) -> list[dict]:
        daten = self._ionos("GET", "/snapshots?depth=1")
        return [
            {
                "id": s["id"],
                "name": s["properties"].get("name", ""),
                "angelegt": s["metadata"].get("createdDate", ""),
                "groesse_gb": s["properties"].get("size"),
                "status": s["metadata"].get("state"),
            }
            for s in daten.get("items", [])
        ]

    def zustand(self) -> dict:
        server = self._ionos("GET", self._server_pfad())
        volume = self._ionos("GET", self._volume_pfad())
        return {
            "server": {
                "name": server["properties"].get("name"),
                "vm_status": server["properties"].get("vmState"),
                "status": server["metadata"].get("state"),
            },
            "volume": {"groesse_gb": volume["properties"].get("size")},
            "snapshots": self.snapshots(),
            "grenzen": {
                "max_eigene_snapshots": self.konfig["max_eigene_snapshots"],
                "mindestabstand_s": self.konfig["mindestabstand_s"],
            },
            "verlauf": list(self.verlauf),
        }

    def fuehre_aus(self, methode: str, pfad: str, koerper: dict) -> dict:
        aktion = pfad.split("?", 1)[0].rstrip("/")
        if not aktion_erlaubt(methode, pfad):
            raise Verweigert(403, f"{methode} {aktion} steht nicht auf der Allowlist")
        if aktion == "/zustand":
            return self.zustand()
        with self._sperre:
            self._pruefe_abstand(aktion)
            if aktion == "/neustart":
                self._ionos("POST", self._server_pfad("/reboot"))
                return {"angestossen": "neustart"}
            if aktion == "/start":
                self._ionos("POST", self._server_pfad("/start"))
                return {"angestossen": "start"}
            if aktion == "/konsole":
                return {"url": self._ionos("GET", self._server_pfad("/remoteconsole"))["url"]}
            if aktion == "/snapshot":
                return self._snapshot()
            return self._zurueckspielen(str(koerper.get("snapshot", "")))

    def _snapshot(self) -> dict:
        geloescht = []
        for alt in zu_loeschen(self.snapshots(), self.konfig):
            self._ionos("DELETE", f"/snapshots/{alt['id']}")
            geloescht.append(alt["id"])
        name = self.konfig["snapshot_praefix"] + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        neu = self._ionos(
            "POST", self._volume_pfad("/create-snapshot"), form={"name": name}
        )
        return {"angestossen": "snapshot", "id": neu.get("id"), "name": name, "geloescht": geloescht}

    def _zurueckspielen(self, snapshot_id: str) -> dict:
        if not zurueckspielen_erlaubt(snapshot_id, self.snapshots(), self.konfig):
            raise Verweigert(403, "nur eigene oder geschuetzte Snapshots duerfen zurueck")
        self._ionos(
            "POST", self._volume_pfad("/restore-snapshot"), form={"snapshotId": snapshot_id}
        )
        return {"angestossen": "zurueckspielen", "snapshot": snapshot_id}

    def protokolliere(self, **zeile) -> None:
        zeile = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **zeile}
        if zeile.get("aktion") != "/zustand":
            self.verlauf.append(zeile)
        print(json.dumps(zeile), flush=True)


def baue_handler(proxy: Proxy) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _bediene(self, methode: str) -> None:
            laenge = int(self.headers.get("Content-Length") or 0)
            try:
                koerper = json.loads(self.rfile.read(laenge) or b"{}") if laenge else {}
                if not isinstance(koerper, dict):
                    raise ValueError
            except ValueError:
                koerper = {}
            try:
                status, antwort = 200, proxy.fuehre_aus(methode, self.path, koerper)
                proxy.protokolliere(entscheidung="erlaubt", aktion=self.path, methode=methode)
            except Verweigert as fehler:
                status, antwort = fehler.status, {"verweigert": fehler.grund}
                proxy.protokolliere(
                    entscheidung="verweigert", aktion=self.path, methode=methode, grund=fehler.grund
                )
            daten = json.dumps(antwort).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(daten)))
            self.end_headers()
            self.wfile.write(daten)

        def do_GET(self) -> None:
            self._bediene("GET")

        def do_POST(self) -> None:
            self._bediene("POST")

        def do_PUT(self) -> None:
            self._bediene("PUT")

        def do_DELETE(self) -> None:
            self._bediene("DELETE")

        def do_PATCH(self) -> None:
            self._bediene("PATCH")

        def log_message(self, *_args) -> None:
            pass

    return Handler


def starte(adresse: tuple[str, int], proxy: Proxy) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(adresse, baue_handler(proxy))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    konfig = lade_konfig(Path(os.environ.get("IONOS_PROXY_KONFIG", KONFIG_STANDARD)))
    passwort = Path(konfig["passwort_datei"]).expanduser().read_text().strip()
    proxy = Proxy(konfig, IonosKlient(konfig["benutzer"], passwort))
    adresse = os.environ.get("IONOS_PROXY_ADRESSE", "127.0.0.1")
    starte((adresse, port), proxy)
    proxy.protokolliere(entscheidung="bereit", adresse=adresse, port=port)
    threading.Event().wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
