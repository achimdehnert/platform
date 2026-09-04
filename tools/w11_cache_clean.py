#!/usr/bin/env python3
"""w11_cache_clean.py — Cache-Loeschung auf der GPU-Box, mit den Bedingungen im Werkzeug.

GATE_HEADER (KONZ-038 D8):
  "slug": "w11-cache-delete-without-content-check"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-03"
  "evidence": "tools/tests/test_w11_cache_clean.py"

Warum es dieses Werkzeug gibt
-----------------------------
Die Gate-1-Allowlist „Cache-Loeschung auf der GPU-Box" (policies/autonomy-gates.md,
Owner-Go 2026-09-03) haengt an sechs Bedingungen. Sie nur in den Skill zu schreiben
hiesse, sie der Disziplin des Agenten zu ueberlassen — und genau die hat am selben
Tag versagt: der Vorschlag lautete zuerst „den huggingface-Cache als Ganzes loeschen",
obwohl dort eine Zugangsdatei liegt. Gefunden hat das eine erzwungene Nachpruefung,
nicht die Analyse.

Deshalb prueft dieses Werkzeug die Bedingungen selbst und verweigert sonst den Lauf.
Vorbild: `~/.claude/bin/pr-merge-sa` — der Radius wird vom Werkzeug begrenzt, nicht
von der Selbstbeherrschung des Aufrufers.

Die sechs Bedingungen
---------------------
(a) Inhalt gesehen  — die oberste Ebene jedes Pfades wird gelistet und ausgegeben.
(b) Keine Zugangsdaten im Zielordner — sonst nur die Unterordner darunter.
(c) Verbotene Pfade — WSL-Distribution, Docker-Datenordner, Documents, OneDrive, github.
(d) Eigener Aufraeumbefehl zuerst — kennt das Werkzeug einen, nennt es ihn und lehnt ab.
(e) Endgueltiges Loeschen braucht ein eigenes Wort (`--endgueltig`); der Papierkorb
    gibt bei grossen Baeumen keinen Platz frei, deshalb ist er hier nicht der Default.
(f) Freigabe gilt der Liste — `--loeschen` braucht `--freigabe <Wortlaut>` und die
    exakten Pfade; abgeleitet wird nichts.

Exit-Codes
----------
0 = geprueft/geloescht wie verlangt · 1 = mindestens ein Pfad abgelehnt
2 = Werkzeugfehler (Box nicht erreichbar) — blind ist nicht gruen.

Usage
-----
    python3 tools/w11_cache_clean.py --pfad '<Windows-Pfad>'
    python3 tools/w11_cache_clean.py --pfad '<...>' --loeschen --freigabe '6 go' --endgueltig
"""

from __future__ import annotations

import argparse
import base64
import re
import subprocess
import sys

HOP = "root@88.198.191.108"
BOX = "achim@10.99.0.2"
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
TIMEOUT_S = 570

# (c) — auch mit Freigabe tabu. Kleingeschrieben verglichen.
VERBOTEN = (
    r"appdata\\local\\packages\\canonicalgrouplimited",
    r"appdata\\local\\docker",
    r"\\documents",
    r"\\onedrive",
    r"\\github",
)

# (b) — Dateinamen, die eine Loeschung des ELTERNORDNERS verbieten. Bewusst als
# Muster und nicht als Liste: die naechste Zugangsdatei heisst wieder anders.
GEHEIM = (
    re.compile(r"^token$", re.IGNORECASE),
    re.compile(r"^id_[a-z0-9_]+(\.pub)?$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"^credential", re.IGNORECASE),
    re.compile(r"^\.env$", re.IGNORECASE),
)

# (d) — wo ein eigener Aufraeumbefehl existiert, ist `rm` der falsche Weg.
EIGENER_BEFEHL = {
    r"appdata\\local\\uv": "uv cache clean",
    r"appdata\\local\\pip": "pip cache purge",
    r"\\\.ollama": "ollama list + ollama rm <modell>",
    r"appdata\\local\\docker": "docker system prune -a (erst nach docker volume ls)",
}


def _ps(script: str) -> list[str]:
    """PowerShell ueber zwei Hops. `-EncodedCommand`, weil Pipes und Anfuehrungs-
    zeichen sonst von `cmd` auf der Zwischenstation gefressen werden."""
    enc = base64.b64encode(script.encode("utf-16-le")).decode()
    innen = (
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 {BOX} "
        f"powershell -NoProfile -EncodedCommand {enc}"
    )
    return SSH + [HOP, innen]


def _lauf(cmd: list[str], timeout: int = TIMEOUT_S) -> tuple[int, str]:
    """Bewusst OHNE `text=True`: die Windows-Seite antwortet in cp850, nicht UTF-8.
    Mit Auto-Dekodierung stirbt der Aufruf an einem Umlaut in einer Fehlermeldung
    (`UnicodeDecodeError: 0x81`) — beim ersten echten Lauf 2026-09-03 gemessen."""
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        return p.returncode, p.stdout.decode("cp850", errors="replace")
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError as exc:
        return 127, str(exc)


def _saeubere(text: str) -> list[str]:
    """PowerShell haengt CLIXML-Fortschritt an — das ist keine Ausgabe."""
    raus = []
    for z in text.splitlines():
        z = z.rstrip()
        if not z or z.startswith(("#< CLIXML", "<Objs")):
            continue
        raus.append(z)
    return raus


def liste_inhalt(pfad: str, laeufer=None) -> list[str] | None:
    """(a) — oberste Ebene eines Pfades. `None` = Box nicht erreichbar."""
    laeufer = laeufer or _lauf
    skript = (
        f'if(-not (Test-Path -LiteralPath "{pfad}")){{ "__FEHLT__"; exit }}; '
        f'Get-ChildItem -LiteralPath "{pfad}" -Force -ErrorAction SilentlyContinue | '
        'ForEach-Object { $(if($_.PSIsContainer){"DIR "}else{"FILE"}) + " " + $_.Name }'
    )
    rc, out = laeufer(_ps(skript))
    if rc != 0:
        return None
    return _saeubere(out)


def pruefe_pfad(pfad: str, inhalt: list[str]) -> list[str]:
    """Alle Bedingungen ausser (a) und (f). Leere Liste = erlaubt."""
    befunde = []
    flach = pfad.replace("/", "\\").lower()

    for muster in VERBOTEN:
        if re.search(muster, flach):
            befunde.append(f"(c) verbotener Pfad — Muster `{muster}`")

    for muster, befehl in EIGENER_BEFEHL.items():
        if re.search(muster, flach):
            befunde.append(f"(d) eigener Aufraeumbefehl existiert: `{befehl}`")

    if inhalt == ["__FEHLT__"]:
        befunde.append("Pfad existiert nicht")
        return befunde

    for zeile in inhalt:
        if not zeile.startswith("FILE "):
            continue
        name = zeile[5:].strip()
        for muster in GEHEIM:
            if muster.search(name):
                befunde.append(
                    f"(b) Zugangsdatei `{name}` im Ordner — nur die Unterordner loeschen"
                )
    return befunde


def freier_platz(laeufer=None) -> float | None:
    laeufer = laeufer or _lauf
    rc, out = laeufer(
        _ps("[math]::Round((Get-Volume -DriveLetter C).SizeRemaining/1GB,1)")
    )
    if rc != 0:
        return None
    for z in _saeubere(out):
        try:
            return float(z.replace(",", "."))
        except ValueError:
            continue
    return None


def loesche(pfad: str, laeufer=None) -> bool:
    laeufer = laeufer or _lauf
    skript = (
        f'Remove-Item -LiteralPath "{pfad}" -Recurse -Force '
        f"-ErrorAction SilentlyContinue; "
        f'"NOCH_DA=" + (Test-Path -LiteralPath "{pfad}")'
    )
    rc, out = laeufer(_ps(skript))
    return rc == 0 and any("NOCH_DA=False" in z for z in _saeubere(out))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pfad", action="append", required=True, help="Windows-Pfad")
    ap.add_argument("--loeschen", action="store_true", help="wirklich loeschen")
    ap.add_argument("--freigabe", help="(f) Wortlaut der Owner-Freigabe")
    ap.add_argument(
        "--endgueltig", action="store_true", help="(e) endgueltig statt Papierkorb"
    )
    args = ap.parse_args(argv)

    if args.loeschen and not args.freigabe:
        print(
            "(f) `--loeschen` ohne `--freigabe <Wortlaut>` — abgelehnt.",
            file=sys.stderr,
        )
        return 1
    if args.loeschen and not args.endgueltig:
        print(
            "(e) Loeschen laeuft hier endgueltig; der Papierkorb gibt bei grossen "
            "Baeumen keinen Platz frei. `--endgueltig` ist dafuer das eigene Wort.",
            file=sys.stderr,
        )
        return 1

    abgelehnt = 0
    freigegeben: list[str] = []
    for pfad in args.pfad:
        inhalt = liste_inhalt(pfad)
        if inhalt is None:
            print(
                f"⛔ {pfad}: Box nicht erreichbar — blind ist nicht gruen.",
                file=sys.stderr,
            )
            return 2
        print(f"\n## {pfad}")
        for z in inhalt[:20]:
            print(f"   {z}")
        befunde = pruefe_pfad(pfad, inhalt)
        if befunde:
            abgelehnt += 1
            for b in befunde:
                print(f"   ⛔ {b}")
        else:
            freigegeben.append(pfad)
            print("   ✅ alle Bedingungen erfuellt")

    if not args.loeschen:
        print(f"\nTrockenlauf: {len(freigegeben)} freigegeben, {abgelehnt} abgelehnt.")
        return 1 if abgelehnt else 0

    vorher = freier_platz()
    for pfad in freigegeben:
        ok = loesche(pfad)
        print(f"{'✅' if ok else '⛔'} geloescht: {pfad}")
    nachher = freier_platz()
    if vorher is not None and nachher is not None:
        print(
            f"\nfrei vorher {vorher} GB → nachher {nachher} GB "
            f"(gewonnen {round(nachher - vorher, 1)} GB)"
        )
    else:
        print("\nGewinn NICHT messbar — kein Beleg, keine Entwarnung.", file=sys.stderr)
    return 1 if abgelehnt else 0


if __name__ == "__main__":
    sys.exit(main())
