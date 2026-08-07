#!/usr/bin/env python3
"""Push-Gate: echte Mandantendaten duerfen nicht ins oeffentliche Repo.

`achimdehnert/platform` ist oeffentlich. Wer hier einen Mandantennamen, einen
Vorgangsschluessel oder einen Korrespondenten aus dem DMS in eine Testfixture
schreibt, veroeffentlicht eine Geschaeftsbeziehung. Das ist am 2026-08-07
passiert (platform#1834): ein echter Vorgangsschluessel und drei echte
Gegenueber-Namen standen in `tools/tests/test_todo_board.py`. Gitleaks hat den
Schluessel gemeldet — aber wegen seiner Entropie, nicht weil es Mandantendaten
kennt; die drei Namen lagen seit Monaten unbeanstandet daneben.

Der Gate vergleicht den Push gegen die **echten** Werte aus den lokalen Quellen:

    ~/.claude/mail-vorgaenge.json   Vorgangsschluessel, Gegenueber
    ~/.claude/mail-anker.json       Betreffs verankerter Mails
    docs.iil.pet (Paperless)        Korrespondenten und Schlagworte

Die Quellen liegen bewusst NICHT im Repo — ein CI-Job kann diesen Vergleich
darum nicht fuehren. Der Gate ist ein lokaler Riegel auf der Maschine, auf der
die Arbeit stattfindet (88.99.38.75); ein Push von einem anderen Rechner wird
nicht erfasst. Das ist eine bewusste Grenze, keine uebersehene.

    mandantendaten_gate.py sammle           Begriffe erheben -> ~/.claude/schutzbegriffe.json
    mandantendaten_gate.py bestandsaufnahme Repo einmal komplett pruefen (blockiert nichts)
    mandantendaten_gate.py diff [--basis R] nur neue Zeilen pruefen (Exit 1 blockiert)

Der Cache wird nie ins Repo geschrieben und nie ausgegeben — gemeldet wird immer
nur der EINE Treffer samt Fundstelle, nicht die Liste.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CACHE = Path.home() / ".claude" / "schutzbegriffe.json"
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
ANKER = Path.home() / ".claude" / "mail-anker.json"
AUSNAHMEN = Path(__file__).with_name("mandantendaten_ausnahmen.txt")

DOCHUB_HOST = "root@88.198.191.108"
# Nur Korrespondenten: Schlagworte sind Ordnungsbegriffe ('Rechnung', 'Option')
# und benennen keine Partei — sie waren in der ersten Fassung die Hauptquelle
# der Fehlalarme.
DOCHUB_SQL = "SELECT name FROM documents_correspondent;"

# Kuerzere Namen tragen zu wenig Kennzeichnungskraft — "Ulm" oder "AV" wuerden
# jeden Push blockieren, ohne etwas zu schuetzen.
MIN_LAENGE = 6

# Gattungsbegriffe: stehen IN echten Namen, benennen aber niemanden. Ein Name,
# der nach dem Abzug nur noch daraus besteht, ist kein Name.
GATTUNG = {
    "gmbh",
    "mbh",
    "ohg",
    "kgaa",
    "gbr",
    "verein",
    "stiftung",
    "holding",
    "institut",
    "systems",
    "service",
    "services",
    "group",
    "digital",
    "asset",
    "rechnung",
    "rechnungen",
    "vertrag",
    "vertraege",
    "angebot",
    "mahnung",
    "beschaffung",
    "ausschreibung",
    "abschlussarbeit",
    "betreuung",
    "postfach",
    "datenschutz",
    "loeschung",
    "pruefung",
    "ueberpruefung",
    "anfrage",
    "beispiel",
    "vorgang",
    "vorgaenge",
    "sonstiges",
    "privat",
    "intern",
    "option",
    "optional",
    "bitte",
    "sonstige",
    "allgemein",
    "unbekannt",
    # Aus der Bestandsaufnahme 2026-08-07: Woerter, die als Bestandteil echter
    # Namen auftauchen, im Repo aber ihre normale Bedeutung haben.
    "loeschung",
    "löschung",
    "lizenz",
    "lizenzen",
    "austausch",
    "folien",
    "versicherung",
    "deutsche",
    "deutscher",
    "deutschland",
    "bayern",
    "gemeinde",
    "finanzamt",
    "stadtwerke",
    "landratsamt",
    # Branchenwoerter: Bestandteil echter Firmennamen, benennen aber die Branche
    # und nicht die Partei. Der kennzeichnende Namensteil schuetzt weiterhin.
    "recycling",
    "apotheke",
    "logistik",
    "technik",
    "energie",
}

# Die eigene Identitaet ist kein Mandantendatum: sie steht zu Recht ueberall im
# Repo (CODEOWNERS, Branch-Namen, Signaturen) und wuerde jeden Push blockieren.
EIGEN = {"dehnert", "achim", "sabine", "iilgmbh", "institut", "informationslogistik"}

WORT = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9-]{3,}")


def namensteil(text: str) -> str:
    """Den fuehrenden Namen aus einem Ledger-Feld schaelen.

    'Muster-Werke Beispielstadt (Rechnung Juli, privat)' -> 'Muster-Werke Beispielstadt'
    Der Klammerzusatz ist Notiz, nicht Name, und traegt Gattungswoerter herein.

    Die Beispiele hier sind erfunden — auch dieses Modul steht im oeffentlichen
    Repo und faellt unter seine eigene Regel. Der erste Entwurf tat es nicht und
    wurde vom eigenen Drill gefangen.
    """
    kopf = re.split(r"[(/,]", text or "", maxsplit=1)[0]
    return " ".join(kopf.split()).strip(" -–")


def zerlege(text: str) -> set[str]:
    """Einen Namen zu schuetzenden Begriffen machen: der Name selbst und seine
    kennzeichnenden Bestandteile — nicht jedes Wort, das darin vorkommt."""
    name = namensteil(text)
    if not name:
        return set()
    treffer: set[str] = set()
    woerter = [w.lower().strip("-") for w in WORT.findall(name)]
    kennzeichnend = [w for w in woerter if w not in GATTUNG and w not in EIGEN]
    if not kennzeichnend:
        return set()
    # Der vollstaendige Name faengt den Copy-Paste-Fall; die kennzeichnenden
    # Einzelteile fangen die abgekuerzte Schreibweise ("musterwerke-av-2026").
    if len(name) >= MIN_LAENGE:
        treffer.add(name.lower())
    treffer |= {w for w in kennzeichnend if len(w) >= MIN_LAENGE}
    return treffer


def aus_ledger() -> set[str]:
    if not LEDGER.exists():
        return set()
    daten = json.loads(LEDGER.read_text(encoding="utf-8"))
    posten = daten.get("vorgaenge", daten) if isinstance(daten, dict) else daten
    begriffe: set[str] = set()
    for v in posten if isinstance(posten, list) else []:
        for feld in ("thread_key", "gegenueber"):
            begriffe |= zerlege(str(v.get(feld) or ""))
    return begriffe


def aus_anker() -> set[str]:
    """Betreffs sind Saetze, keine Namen — daraus wird nichts gewonnen.

    Ein Versuch, sie zu zerlegen, brachte Woerter wie 'bitte' in die Liste und
    haette jeden Push blockiert (Bestandsaufnahme 2026-08-07: 13478 Treffer).
    Der Anker bleibt als Quelle bewusst aussen vor; er benennt keine Partei,
    die nicht schon ueber das Ledger erfasst waere.
    """
    return set()


def aus_dochub(timeout: int = 25) -> set[str]:
    """Korrespondenten und Schlagworte aus docs.iil.pet.

    Faellt der Host aus, ist das ein Befund und kein stiller Nullwert: der
    Aufrufer erfaehrt es und der Cache bleibt unveraendert stehen.
    """
    ergebnis = subprocess.run(
        [
            "ssh",
            "-o",
            f"ConnectTimeout={timeout}",
            DOCHUB_HOST,
            f'docker exec iil_dochub_db psql -U paperless -d paperless -A -t -c "{DOCHUB_SQL}"',
        ],
        capture_output=True,
        text=True,
        timeout=timeout + 20,
        check=False,
    )
    if ergebnis.returncode != 0:
        raise RuntimeError(
            f"docs.iil.pet nicht erreichbar: {ergebnis.stderr.strip()[:160]}"
        )
    begriffe: set[str] = set()
    for zeile in ergebnis.stdout.splitlines():
        begriffe |= zerlege(zeile)
    return begriffe


def ausnahmen() -> set[str]:
    if not AUSNAHMEN.exists():
        return set()
    return {
        z.split("#", 1)[0].strip().lower()
        for z in AUSNAHMEN.read_text(encoding="utf-8").splitlines()
        if z.split("#", 1)[0].strip()
    }


def lade_cache() -> set[str]:
    if not CACHE.exists():
        sys.exit(
            "FEHLER: Begriffs-Cache fehlt. Einmal 'mandantendaten_gate.py sammle' laufen lassen."
        )
    daten = json.loads(CACHE.read_text(encoding="utf-8"))
    return set(daten.get("begriffe", [])) - ausnahmen()


def cmd_sammle(args: argparse.Namespace) -> int:
    begriffe = aus_ledger() | aus_anker()
    quellen = ["mail-vorgaenge.json", "mail-anker.json"]
    if not args.ohne_dochub:
        try:
            begriffe |= aus_dochub()
            quellen.append("docs.iil.pet")
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print(f"WARNUNG: {exc}", file=sys.stderr)
            print("         Cache wird OHNE docs.iil.pet geschrieben.", file=sys.stderr)
    CACHE.write_text(
        json.dumps(
            {"quellen": quellen, "begriffe": sorted(begriffe)},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    CACHE.chmod(0o600)
    # Bewusst nur die Anzahl: die Begriffe selbst sind der zu schuetzende Inhalt.
    print(f"OK: {len(begriffe)} Begriffe aus {', '.join(quellen)} -> {CACHE}")
    return 0


def _pruefe(
    zeilen: list[tuple[str, int, str]], begriffe: set[str]
) -> list[tuple[str, int, str]]:
    funde = []
    for datei, nr, text in zeilen:
        klein = text.lower()
        for b in begriffe:
            if b in klein:
                funde.append((datei, nr, b))
                break
    return funde


def _repo_zeilen() -> list[tuple[str, int, str]]:
    dateien = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()
    zeilen = []
    for d in dateien:
        p = Path(d)
        if p.suffix.lower() in {".png", ".jpg", ".pdf", ".zip", ".ico", ".woff2"}:
            continue
        try:
            for nr, text in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                zeilen.append((d, nr, text))
        except (OSError, UnicodeDecodeError):
            continue
    return zeilen


def _diff_zeilen(basis: str) -> list[tuple[str, int, str]]:
    roh = subprocess.run(
        ["git", "diff", "--unified=0", f"{basis}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    zeilen, datei, nr = [], "?", 0
    for z in roh.splitlines():
        if z.startswith("+++ b/"):
            datei = z[6:]
        elif z.startswith("@@"):
            treffer = re.search(r"\+(\d+)", z)
            nr = int(treffer.group(1)) if treffer else 0
        elif z.startswith("+") and not z.startswith("+++"):
            zeilen.append((datei, nr, z[1:]))
            nr += 1
    return zeilen


def _melde(funde: list[tuple[str, int, str]]) -> None:
    for datei, nr, begriff in funde[:20]:
        print(f"  {datei}:{nr} — enthaelt '{begriff}'")
    if len(funde) > 20:
        print(f"  … und {len(funde) - 20} weitere")


def cmd_bestandsaufnahme(_args: argparse.Namespace) -> int:
    funde = _pruefe(_repo_zeilen(), lade_cache())
    if not funde:
        print("Bestandsaufnahme: keine Mandantendaten im Repo gefunden.")
        return 0
    print(
        f"Bestandsaufnahme: {len(funde)} Fundstelle(n) — blockiert nichts, nur Befund:"
    )
    _melde(funde)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    funde = _pruefe(_diff_zeilen(args.basis), lade_cache())
    if not funde:
        print("Mandantendaten-Gate: sauber.")
        return 0
    print(f"⛔ Mandantendaten-Gate: {len(funde)} Fundstelle(n) in neuen Zeilen.")
    _melde(funde)
    print(
        "\nDas Repo ist oeffentlich. Testdaten werden erfunden, nicht kopiert.\n"
        f"Falscher Alarm? Begriff in {AUSNAHMEN.name} eintragen — eine Zeile je Begriff,\n"
        "mit Begruendung als Kommentar dahinter."
    )
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sammle", help="Begriffe aus allen Quellen erheben")
    s.add_argument("--ohne-dochub", action="store_true", dest="ohne_dochub")
    s.set_defaults(fn=cmd_sammle)
    b = sub.add_parser(
        "bestandsaufnahme", help="ganzes Repo pruefen, ohne zu blockieren"
    )
    b.set_defaults(fn=cmd_bestandsaufnahme)
    d = sub.add_parser("diff", help="nur neue Zeilen pruefen; Exit 1 blockiert")
    d.add_argument("--basis", default="origin/main")
    d.set_defaults(fn=cmd_diff)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
