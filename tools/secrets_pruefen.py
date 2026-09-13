#!/usr/bin/env python3
"""Prueft einen Schluessel unter ``~/.secrets``, ohne ihn je auszugeben (V4).

Anlass: Eine Secret-Datei lag in "nackter" Form vor (kein ``NAME=WERT``, nur
der Wert). Ein ``. datei``-Sourcing, gedacht fuer einen Hash-Vergleich,
fuehrte den Wert stattdessen als Kommando aus — die Shell schrieb ihn in die
eigene Fehlermeldung. Der bestehende argumentbasierte Secret-Leak-Guard
(faengt ``cat``/``head``/``tail``/``grep`` mit einer Secret-Datei als
Argument) hat dabei korrekt gefeuert; er sichert aber kein Sourcing ab.

Dieses Werkzeug ersetzt das Sourcen durch drei read-only Pruefungen:

1. ``--datei NAME``       — Form erkennen (``kv``/``bare``/``gemischt``),
                             je Wert nur Laenge + SHA-256-Praefix zeigen.
2. ``--http PROVIDER``    — den Wert einmal live gegen den Provider testen
                             (nur den HTTP-Code melden, nie den Wert).
3. ``--alle``             — alle Dateien der Basis auf ``bare``/``gemischt``
                             durchsuchen; genau diese Form haette das
                             Sourcing-Unglueck ermoeglicht.

Verwandte Werkzeuge (Namen/Konventionen von dort uebernommen, nichts
dupliziert): ``tools/secrets_inventory_check.py`` prueft das
YAML-Inventar (``infra/secrets-inventory.yaml``) gegen sein Schema und
zaehlt Konsumenten — andere Ebene, anderes Ziel. ``tools/secrets-flatten.py``
raeumt eine verschachtelte ``~/.secrets/.secrets/``-Struktur auf und nutzt
denselben Fingerabdruck-Ansatz (SHA-256, nie der Wert). ``tools/secrets.md``
ist die Doku fuer beide plus diesen neuen Abschnitt.

Werte werden an KEINER Stelle ausgegeben — auch nicht als Teilstring, auch
nicht im Fehlerfall.

Aufruf::

    python3 tools/secrets_pruefen.py --datei cloudflare_api_token
    python3 tools/secrets_pruefen.py --datei groq_api_key --http groq
    python3 tools/secrets_pruefen.py --alle
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

SECRETS = Path.home() / ".secrets"

USER_AGENT = "secrets_pruefen/1"

#: Nur diese drei Provider sind bekannt — ``PROVIDER ∈ {groq, openai,
#: anthropic}``. Fuer alle drei ausser ``anthropic`` gilt derselbe
#: ("sonst")-Zweig: ``Authorization: Bearer``.
PROVIDER_URLS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
}

ANTHROPIC_VERSION = "2023-06-01"


# ─── Form-Erkennung ────────────────────────────────────────────────────────


def erkenne_form(inhalt: str) -> tuple[str, list[tuple[str | None, str]]]:
    """(form, werte). form ist ``kv``/``bare``/``gemischt``/``leer``.

    ``werte`` ist eine Liste aus ``(name, wert)`` — bei ``bare`` ist der Name
    ``None``. Leere Zeilen und ``#``-Kommentare zaehlen nicht als Inhalt.
    """
    zeilen = [
        z for z in inhalt.splitlines() if z.strip() and not z.strip().startswith("#")
    ]
    if not zeilen:
        return "leer", []

    kv: list[tuple[str | None, str]] = []
    bare: list[tuple[str | None, str]] = []
    for z in zeilen:
        if "=" in z:
            name, _, wert = z.partition("=")
            kv.append((name.strip(), wert))
        else:
            bare.append((None, z))

    if kv and not bare:
        return "kv", kv
    if bare and not kv and len(bare) == 1:
        return "bare", bare
    return "gemischt", kv + bare


def ist_riskant(form: str) -> bool:
    """``bare``/``gemischt`` wuerden bei einem ``. datei``-Sourcing den Wert
    als Kommando ausfuehren — genau der Fehler vom Anlass."""
    return form in ("bare", "gemischt")


# ─── Dateiname / Pfad-Traversal ────────────────────────────────────────────


def validiere_dateiname(name: str) -> str | None:
    """``None`` = ok, sonst Fehlertext. NAME darf keinen Pfadanteil tragen."""
    if (
        not name
        or "/" in name
        or "\\" in name
        or ".." in name
        or name != Path(name).name
    ):
        return f"ungueltiger Dateiname (kein Pfadanteil erlaubt): {name!r}"
    return None


# ─── HTTP-Gegenprobe ───────────────────────────────────────────────────────


def baue_header(provider: str, wert: str) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if provider == "anthropic":
        headers["x-api-key"] = wert
        headers["anthropic-version"] = ANTHROPIC_VERSION
    else:
        headers["Authorization"] = f"Bearer {wert}"
    return headers


def http_get(url: str, headers: dict[str, str]) -> int:
    """Echter Netzwerkzugriff — in Tests durch eine Fake-Funktion ersetzt.

    Ein HTTP-Fehlercode (401/403/...) ist ein gueltiges Ergebnis und wird als
    Zahl zurueckgegeben, kein Ausnahmefall. Nur ein echter Netzfehler
    (Timeout, DNS, Verbindungsabbruch) propagiert als Exception.
    """
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code


def pruefe_http(provider: str, wert: str) -> int:
    url = PROVIDER_URLS[provider]
    headers = baue_header(provider, wert)
    try:
        code = http_get(url, headers)
    except Exception as exc:  # noqa: BLE001 - jede Netz-Ausnahmeklasse ist gewollt
        print(f"{provider} http fehler:{type(exc).__name__}")
        return 1
    print(f"{provider} http {code}")
    return 0 if code == 200 else 1


# ─── Wert-Auswahl fuer --http ──────────────────────────────────────────────


def waehle_wert(
    form: str, werte: list[tuple[str | None, str]], var: str | None
) -> str | None:
    if form == "bare":
        return werte[0][1]
    if var is None:
        return None
    for name, wert in werte:
        if name == var:
            return wert
    return None


# ─── Modi ──────────────────────────────────────────────────────────────────


def zeige_datei(name: str, form: str, werte: list[tuple[str | None, str]]) -> int:
    print(f"{name}: form={form}")
    for eig_name, wert in werte:
        anzeige = eig_name if eig_name else "<bare>"
        sha = hashlib.sha256(wert.encode("utf-8")).hexdigest()[:8]
        print(f"{anzeige} len={len(wert)} sha={sha}")
    return 0


def modus_alle(basis: Path) -> int:
    if not basis.is_dir():
        print(f"{basis} existiert nicht oder ist kein Verzeichnis", file=sys.stderr)
        return 1

    warnungen = 0
    for pfad in sorted(basis.iterdir()):
        if not pfad.is_file():
            continue
        try:
            inhalt = pfad.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            print(f"{pfad.name} form=unlesbar")
            continue
        form, _ = erkenne_form(inhalt)
        print(f"{pfad.name} form={form}")
        if ist_riskant(form):
            warnungen += 1
            print(
                f"  WARN {pfad.name} ohne NAME=-Form — Sourcing wuerde den Wert ausfuehren"
            )
    return 1 if warnungen else 0


def modus_datei(
    basis: Path, name: str, http_provider: str | None, var: str | None
) -> int:
    fehler = validiere_dateiname(name)
    if fehler:
        print(fehler, file=sys.stderr)
        return 2

    pfad = basis / name
    if not pfad.is_file():
        print(f"{pfad} existiert nicht", file=sys.stderr)
        return 1

    inhalt = pfad.read_text(encoding="utf-8", errors="replace")
    form, werte = erkenne_form(inhalt)

    if http_provider:
        wert = waehle_wert(form, werte, var)
        if wert is None:
            print(
                "kein passender Wert gefunden — bei 'kv'/'gemischt' --var setzen",
                file=sys.stderr,
            )
            return 2
        return pruefe_http(http_provider, wert)

    return zeige_datei(name, form, werte)


# ─── CLI ────────────────────────────────────────────────────────────────────


def bauen_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="secrets_pruefen.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Hinweis: 403 bei --http heisst meist Cloudflare (urllib-Standard-"
            "kennung wird geblockt), nicht ein falscher Schluessel — deshalb "
            "setzt dieses Werkzeug einen eigenen User-Agent."
        ),
    )
    p.add_argument(
        "--datei",
        metavar="NAME",
        help="Dateiname unter --basis, ohne Pfadanteil (kein '/', kein '..')",
    )
    p.add_argument(
        "--basis",
        type=Path,
        default=SECRETS,
        help=f"Basisverzeichnis (default {SECRETS})",
    )
    p.add_argument(
        "--var",
        metavar="NAME",
        help="Variablenname in einer kv-/gemischt-Datei, dessen Wert --http prueft",
    )
    p.add_argument(
        "--http",
        metavar="PROVIDER",
        choices=sorted(PROVIDER_URLS),
        help="HTTP-Gegenprobe gegen den Provider (braucht --datei); nur Code, nie der Wert",
    )
    p.add_argument(
        "--alle",
        action="store_true",
        help="alle Dateien der Basis mit ihrer Form auflisten (Sourcing-Melder)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    p = bauen_parser()
    args = p.parse_args(argv)

    if args.alle:
        return modus_alle(args.basis)

    if not args.datei:
        p.error("--datei oder --alle erforderlich")

    return modus_datei(args.basis, args.datei, args.http, args.var)


if __name__ == "__main__":
    sys.exit(main())
