"""Fingerabdruck eines Secret-Werts — HMAC, nicht blankes SHA-256 (MT-8).

Ein ungesalzener SHA-256-Praefix ist bei niedrigentropischen Werten ein
Rate-Orakel: Benutzernamen, Hostnamen und kurze Passwoerter lassen sich gegen
den veroeffentlichten Praefix durchprobieren. Das Inventar fuehrt genau solche
Eintraege (``DEPLOY_USER``, ``HETZNER_HOST``). Deshalb HMAC mit einem
Werkzeug-Schluessel, der das Repo nie sieht.

Der Schluessel liegt in ``~/.secrets/rotation_hmac_key``. Fehlt er, ist das
**kein Grund, den Fingerabdruck wegzulassen**: ``pruefen`` laeuft weiter (es
liest nur), ``lauf`` bricht mit einer klaren Meldung ab. Ein Lauf ohne
Fingerabdruck waere ein Lauf ohne Nachweis — und Nachweis ist der ganze Zweck.

Jede Log-Zeile traegt ``fingerprint_alg``, damit ein spaeterer Wechsel des
Verfahrens oder des Schluessels alte Zeilen nicht stillschweigend
unvergleichbar macht.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

#: Wandert in jede Log-Zeile. Bei Schluessel- oder Verfahrenswechsel hochzaehlen.
ALGORITHMUS = "hmac-sha256/v1"

#: 16 Hex-Zeichen = 64 bit. Genug, um zwei Laeufe zu unterscheiden; zu wenig,
#: um daraus etwas zurueckzurechnen.
PRAEFIX_LAENGE = 16

SCHLUESSEL_PFAD = Path.home() / ".secrets" / "rotation_hmac_key"


class SchluesselFehlt(RuntimeError):
    """Der HMAC-Schluessel ist nicht lesbar."""


def lade_schluessel(pfad: Path | None = None) -> bytes:
    pfad = pfad or SCHLUESSEL_PFAD
    try:
        roh = pfad.read_bytes()
    except OSError as fehler:
        raise SchluesselFehlt(
            f"HMAC-Schluessel nicht lesbar: {pfad}\n"
            "Anlegen (Owner-Schritt, einmalig):\n"
            f"  umask 077 && head -c 32 /dev/urandom | base64 > {pfad}\n"
            "Danach als Zweitkopie in den Passwortspeicher — ein Verlust macht "
            "alle bisherigen Fingerabdruecke unvergleichbar (Inventar-Eintrag "
            "platform.ROTATION_HMAC_KEY)."
        ) from fehler
    schluessel = roh.strip()
    if len(schluessel) < 16:
        raise SchluesselFehlt(
            f"HMAC-Schluessel in {pfad} ist kuerzer als 16 Byte — zu schwach."
        )
    return schluessel


def schluessel_vorhanden(pfad: Path | None = None) -> bool:
    pfad = pfad or SCHLUESSEL_PFAD
    return pfad.is_file() and os.access(pfad, os.R_OK)


def fingerabdruck(wert: bytes, schluessel: bytes) -> str:
    """Praefix des HMAC-SHA256 ueber den Wert. Der Wert verlaesst die Funktion nicht."""
    if isinstance(wert, str):  # pragma: no cover - Aufrufer-Fehler, hier abgefangen
        wert = wert.encode("utf-8")
    return hmac.new(schluessel, wert, hashlib.sha256).hexdigest()[:PRAEFIX_LAENGE]


def datei_pruefsumme(pfad: Path) -> str:
    """SHA-256 einer Datei — fuer die Gleichheitspruefung vor dem Leeren der
    Schleuse. Hier ist kein HMAC noetig: die Pruefsumme wird nur im Speicher
    verglichen und nie geschrieben."""
    return hashlib.sha256(pfad.read_bytes()).hexdigest()
