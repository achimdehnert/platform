#!/usr/bin/env python3
"""Befunde des Advocatus Diaboli ins Review-Ledger buchen (KONZ-070 Z3, Mandat #3903 WP4).

Liest eine JSON-Liste von Befunden, prueft sie gegen das Ledger-Schema (dev-hub
`review_ledger`, WP3), ergaenzt `quelle` und `modell` aus `registry/review-risiko.yaml`
und postet als Bulk (`POST <ledger_url>`, Liste ≤ ledger_bulk_max, ignore_conflicts
serverseitig per UniqueConstraint).

    python3 tools/advocatus_ledger_post.py befunde.json [--dry-run]
    python3 tools/advocatus_ledger_post.py --probe

Exit 0 = gebucht (oder --dry-run / leere Liste) · 1 = Schema- oder HTTP-Fehler
· 2 = Token fehlt. Der Token kommt NUR aus der Umgebungsvariable `routine.token_env`
und erscheint in keiner Ausgabe. Bei HTTP-Fehlern wird nur der Statuscode genannt,
nie der Antwort-Body.

`--probe` sendet ein GET ohne Daten an `ledger_url` und meldet nur, ob der Host antwortet:
jeder HTTP-Statuscode (auch 401/403/405) heisst erreichbar (Exit 0), ein Verbindungsfehler
heisst nicht erreichbar (Exit 1). Grund: aus der Cloud-Umgebung blockte die Netzwerk-Policy
den Ledger-Host (AD5, #3903, 2026-10-14), und ohne Kandidaten beweist kein Lauf den Weg.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_regeln as rr  # noqa: E402
import review_risiko as rk  # noqa: E402

RC_OK, RC_FEHLER, RC_KEIN_TOKEN = 0, 1, 2
OK_STATUS = (200, 201)
REPO_MUSTER = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_MUSTER = re.compile(r"^[0-9a-f]{7,40}$")
#: Laengen wie im dev-hub-Modell ReviewBefund (WP3).
MAX_LAENGE = {"repo": 200, "head_sha": 40, "regel_id": 64, "locator": 512, "modell": 100}
PFLICHT = ("repo", "pr_nummer", "head_sha", "klasse", "locator", "konfidenz", "begruendung")
OPTIONAL = ("regel_id", "kosten_usd", "quelle", "modell")
TIMEOUT_S = 30
PROBE_PRAEFIX = "LEDGER-PROBE:"


class BefundFehler(ValueError):
    def __init__(self, fehler: list[str]):
        self.fehler = fehler
        super().__init__("\n".join(fehler))


def _pruefe_einen(i: int, b: Any, konfig: dict) -> tuple[dict, list[str]]:
    r = konfig["routine"]
    wo = f"befunde[{i}]"
    if not isinstance(b, dict):
        return {}, [f"{wo}: kein Mapping"]
    fehler = [f"{wo}: Pflichtfeld fehlt: {f}" for f in PFLICHT if f not in b]
    fremd = sorted(set(b) - set(PFLICHT) - set(OPTIONAL))
    if fremd:
        fehler.append(f"{wo}: unbekannte Felder {fremd}")
    if fehler:
        return {}, fehler

    out = {
        "repo": b["repo"],
        "pr_nummer": b["pr_nummer"],
        "head_sha": b["head_sha"],
        "regel_id": b.get("regel_id") or "",
        "klasse": b["klasse"],
        "locator": b["locator"],
        "konfidenz": b["konfidenz"],
        "modell": b.get("modell") or r["modell"],
        "quelle": r["quelle_ledger"],
        "begruendung": b["begruendung"],
    }
    if not isinstance(out["repo"], str) or not REPO_MUSTER.match(out["repo"]):
        fehler.append(f"{wo}: repo muss owner/name sein")
    if not isinstance(out["pr_nummer"], int) or isinstance(out["pr_nummer"], bool) or out["pr_nummer"] < 1:
        fehler.append(f"{wo}: pr_nummer muss Ganzzahl >= 1 sein")
    if not isinstance(out["head_sha"], str) or not SHA_MUSTER.match(out["head_sha"]):
        fehler.append(f"{wo}: head_sha muss Hex-SHA (7..40) sein")
    if not isinstance(out["regel_id"], str) or (
        out["regel_id"] and not rr.ID_MUSTER.match(out["regel_id"])
    ):
        fehler.append(f"{wo}: regel_id muss leer oder RR-NNN sein")
    if out["klasse"] not in rr.KLASSEN:
        fehler.append(f"{wo}: klasse {out['klasse']!r} nicht in {rr.KLASSEN}")
    k = out["konfidenz"]
    if isinstance(k, bool) or not isinstance(k, (int, float)) or not 0.0 <= k <= 1.0:
        fehler.append(f"{wo}: konfidenz muss Zahl in 0..1 sein")
    if not isinstance(out["locator"], str) or not isinstance(out["begruendung"], str):
        fehler.append(f"{wo}: locator und begruendung muessen Strings sein")
    if "quelle" in b and b["quelle"] != r["quelle_ledger"]:
        fehler.append(f"{wo}: quelle ist fest {r['quelle_ledger']!r}, nicht {b['quelle']!r}")
    kosten = b.get("kosten_usd")
    if kosten is not None:
        if isinstance(kosten, bool) or not isinstance(kosten, (int, float)) or kosten < 0:
            fehler.append(f"{wo}: kosten_usd muss >= 0 oder null sein")
        else:
            out["kosten_usd"] = kosten
    for feld, maxlen in MAX_LAENGE.items():
        if isinstance(out.get(feld), str) and len(out[feld]) > maxlen:
            fehler.append(f"{wo}: {feld} laenger als {maxlen}")
    return out, fehler


def validiere(befunde: Any, konfig: dict) -> list[dict]:
    """Befunde pruefen und auf das Ledger-Schema normalisieren; wirft BefundFehler."""
    if not isinstance(befunde, list):
        raise BefundFehler(["Eingabe muss eine JSON-Liste sein"])
    out, fehler = [], []
    for i, b in enumerate(befunde):
        n, f = _pruefe_einen(i, b, konfig)
        fehler.extend(f)
        if not f:
            out.append(n)
    if fehler:
        raise BefundFehler(fehler)
    return out


def _chunks(liste: list, n: int):
    for i in range(0, len(liste), n):
        yield liste[i : i + n]


def poste(befunde: list[dict], konfig: dict, token: str) -> list[int]:
    """Bulk-POST je Chunk; Rueckgabe = Statuscodes. Wirft urllib.error.HTTPError."""
    r = konfig["routine"]
    codes = []
    for chunk in _chunks(befunde, int(r["ledger_bulk_max"])):
        req = urllib.request.Request(
            r["ledger_url"],
            data=json.dumps(chunk).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {token}",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as antwort:
            codes.append(antwort.status)
    return codes


def probe(konfig: dict, token: str) -> int:
    """GET ohne Daten an ledger_url; eine Zeile `LEDGER-PROBE: …` auf stdout.

    Erreichbar = irgendein HTTP-Status (Exit 0); Verbindungsfehler = Exit 1. Mit Token
    wird der Authorization-Header gesetzt, damit der Status auch die Auth-Lage zeigt;
    der Token-Wert erscheint in keiner Ausgabe.
    """
    r = konfig["routine"]
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(r["ledger_url"], method="GET", headers=headers)
    auth = "mit Token" if token else f"ohne Token ({r['token_env']} leer)"
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as antwort:
            status = antwort.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except urllib.error.URLError as exc:
        print(f"{PROBE_PRAEFIX} nicht erreichbar ({exc.reason}), {auth}")
        return RC_FEHLER
    print(f"{PROBE_PRAEFIX} erreichbar, HTTP {status}, {auth}")
    return RC_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("datei", nargs="?", help="JSON-Liste der Befunde")
    ap.add_argument(
        "--dry-run", action="store_true", help="Payload zeigen, nichts senden, kein Token noetig"
    )
    ap.add_argument(
        "--probe", action="store_true", help="nur Erreichbarkeit von ledger_url melden, nichts buchen"
    )
    a = ap.parse_args(argv)
    if bool(a.datei) == a.probe:
        ap.error("entweder <datei> oder --probe")

    try:
        konfig = rk.lade_risiko()
    except (rr.SchemaFehler, rk.SchemaFehler) as exc:
        for f in exc.fehler:
            print(f"SCHEMA: {f}", file=sys.stderr)
        return RC_FEHLER
    if a.probe:
        return probe(konfig, os.environ.get(konfig["routine"]["token_env"], "").strip())
    try:
        roh = json.loads(Path(a.datei).read_text(encoding="utf-8"))
        befunde = validiere(roh, konfig)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"EINGABE: {exc}", file=sys.stderr)
        return RC_FEHLER
    except BefundFehler as exc:
        for f in exc.fehler:
            print(f"BEFUND: {f}", file=sys.stderr)
        return RC_FEHLER

    r = konfig["routine"]
    if a.dry_run:
        print(f"DRY-RUN: {len(befunde)} Befund(e) → POST {r['ledger_url']} (Token aus {r['token_env']}, nicht gelesen)")
        print(json.dumps(befunde, ensure_ascii=False, indent=2))
        return RC_OK
    if not befunde:
        print("nichts zu buchen: leere Liste (leere Laeufe bleiben dem Ledger fern)")
        return RC_OK
    token = os.environ.get(r["token_env"], "").strip()
    if not token:
        print(f"TOKEN: Umgebungsvariable {r['token_env']} fehlt oder leer", file=sys.stderr)
        return RC_KEIN_TOKEN
    try:
        codes = poste(befunde, konfig, token)
    except urllib.error.HTTPError as exc:
        print(f"HTTP: Ledger antwortete {exc.code}", file=sys.stderr)
        return RC_FEHLER
    except urllib.error.URLError as exc:
        print(f"HTTP: Ledger nicht erreichbar ({exc.reason})", file=sys.stderr)
        return RC_FEHLER
    schlecht = [c for c in codes if c not in OK_STATUS]
    if schlecht:
        print(f"HTTP: unerwartete Statuscodes {schlecht}", file=sys.stderr)
        return RC_FEHLER
    print(f"gebucht: {len(befunde)} Befund(e) in {len(codes)} Anfrage(n), Status {codes}")
    return RC_OK


if __name__ == "__main__":
    raise SystemExit(main())
