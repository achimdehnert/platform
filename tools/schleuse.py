#!/usr/bin/env python3
"""Die Schleuse (~/shared) aufraeumen — Regeln statt Gefuehl.

Die Schleuse ist ein **Foerderband, kein Regal**: alles darin ist unterwegs von
A nach B. Was liegen bleibt, ist entweder noch nicht angekommen oder gehoert an
einen anderen Ort. Ohne Verfallsregel wird daraus ein Lager — gemessen am
2026-08-18: 247 Eintraege, 3,5 GB, 113 davon aus dem Vormonat.

    python3 tools/schleuse.py                 # Bericht, aendert nichts
    python3 tools/schleuse.py --aufraeumen    # zeigt, was ins Archiv wandert
    python3 tools/schleuse.py --aufraeumen --apply
    python3 tools/schleuse.py --endgueltig --apply   # Archiv > 90 Tage loeschen

Zwei Stufen, mit Absicht: `--aufraeumen` **verschiebt** Faelliges nach
`_archiv/<datum>/`, es loescht nicht. Erst `--endgueltig` entfernt Archiviertes,
und auch das nur mit `--apply`. Ein Werkzeug, das in einem Schritt loescht, wird
irgendwann versehentlich gestartet.

Secrets sind ausgenommen: sie werden nie archiviert. Sie gehoeren nach der
Uebernahme sofort geloescht (~/.secrets ist der Zielort) und werden hier nur
gemeldet — sie liegen ohnehin unter der Aufsicht des Session-Start-Checks 0.5.1.
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import shutil
import sys

SCHLEUSE = pathlib.Path.home() / "shared"
ARCHIV = "_archiv"

# (Name der Klasse, Erkennung, Frist in Tagen, Zielort)
# Frist 0 = gehoert gar nicht in die Schleuse. None = kein Verfall, aber ab
# MELDE_TAGE als "unentschieden" gemeldet, damit es nicht stumm liegen bleibt.
REGELN = [
    (
        "Werkzeug-Rest",
        re.compile(r"^(__pycache__|stash-backup-.*|\.pytest_cache)$"),
        0,
        "gehoert nicht in die Schleuse — direkt weg",
    ),
    (
        "Box-Ergebnis",
        re.compile(r".*ERGEBNIS.*\.txt$|.*-ERGEBNIS$", re.I),
        30,
        "Erkenntnis gehoert in AGENT_HANDOVER / Konzept des Ziel-Repos",
    ),
    (
        "Box-Paket",
        re.compile(r"^(sprache|box-.*|gpu-.*|.*-tunnel-.*)$"),
        14,
        "Quelle ist box-setup/ im Repo — die Kopie hier ist Transport",
    ),
    (
        "Box-Skript",
        re.compile(
            r"^(box-|gpu-|ace-step|msst-|moss-|lokalen-|ollama-|windows-|home-4090).*\.(ps1|sh|cmd)$"
        ),
        14,
        "Quelle ist das Repo",
    ),
    (
        "ADR-Uebergabe",
        re.compile(r"^(adr-handoff-|charta-review-).*"),
        30,
        "gehoert an den ADR und nach Outline",
    ),
    (
        "Bericht",
        re.compile(
            r"^(repo-optimize-|platform-audit-|analyse-|review-|branch-cleanup-).*"
        ),
        30,
        "gehoert in docs/ des betroffenen Repos",
    ),
    (
        "Box-Lane",
        re.compile(r"^von-box$"),
        14,
        "Inhalte ins Ziel-Repo holen, dann leeren (box-schleuse.sh leere von-box)",
    ),
]

MELDE_TAGE = 30  # Die Schleuse ist ein Foerderband: was einen Monat liegt,
# ist entweder angekommen oder gehoert woanders hin.
SECRETS = "inbox/secrets"


def alter_tage(p: pathlib.Path, heute: datetime.date) -> int:
    stand = datetime.date.fromtimestamp(p.stat().st_mtime)
    return (heute - stand).days


def groesse(p: pathlib.Path) -> int:
    if p.is_file():
        return p.stat().st_size
    gesamt = 0
    for kind in p.rglob("*"):
        if kind.is_file():
            try:
                gesamt += kind.stat().st_size
            except OSError:
                pass
    return gesamt


def klasse_von(name: str):
    for bezeichnung, muster, frist, ziel in REGELN:
        if muster.match(name):
            return bezeichnung, frist, ziel
    return (
        "unklassifiziert",
        None,
        "Zielort entscheiden (Repo, Outline, Paperless) oder weg",
    )


def mb(b: int) -> str:
    return f"{b / 1e6:.1f} MB" if b < 1e9 else f"{b / 1e9:.2f} GB"


def sammeln(heute: datetime.date):
    if not SCHLEUSE.is_dir():
        print(f"Keine Schleuse unter {SCHLEUSE}")
        return []
    posten = []
    for p in sorted(SCHLEUSE.iterdir()):
        if p.name == ARCHIV:
            continue
        bezeichnung, frist, ziel = klasse_von(p.name)
        tage = alter_tage(p, heute)
        faellig = frist is not None and tage >= frist
        offen = frist is None and tage >= MELDE_TAGE
        posten.append(
            {
                "pfad": p,
                "klasse": bezeichnung,
                "frist": frist,
                "ziel": ziel,
                "tage": tage,
                "faellig": faellig,
                "unentschieden": offen,
            }
        )
    return posten


def bericht(posten, zeige_alle: bool) -> int:
    faellig = [x for x in posten if x["faellig"]]
    offen = [x for x in posten if x["unentschieden"]]
    ruhig = [x for x in posten if not x["faellig"] and not x["unentschieden"]]

    print(
        f"Schleuse {SCHLEUSE}: {len(posten)} Eintraege, "
        f"{mb(sum(groesse(x['pfad']) for x in posten))}"
    )
    print()

    if faellig:
        print(f"FAELLIG ({len(faellig)}) — Frist ueberschritten:")
        for x in sorted(faellig, key=lambda y: -y["tage"]):
            print(
                f"  {x['tage']:>4} Tage  [{x['klasse']}, Frist {x['frist']}]  "
                f"{x['pfad'].name}"
            )
            print(f"             -> {x['ziel']}")
        print()

    if offen:
        print(
            f"UNENTSCHIEDEN ({len(offen)}) — liegt seit >= {MELDE_TAGE} Tagen "
            f"ohne Regel:"
        )
        for x in sorted(offen, key=lambda y: -y["tage"])[:20]:
            print(
                f"  {x['tage']:>4} Tage  {mb(groesse(x['pfad'])):>10}  {x['pfad'].name}"
            )
        if len(offen) > 20:
            print(f"  ... und {len(offen) - 20} weitere")
        print()

    if zeige_alle and ruhig:
        print(f"IN FRIST ({len(ruhig)}):")
        for x in sorted(ruhig, key=lambda y: -y["tage"]):
            print(f"  {x['tage']:>4} Tage  [{x['klasse']}]  {x['pfad'].name}")
        print()

    geheim = SCHLEUSE / SECRETS
    if geheim.is_dir():
        n = len([p for p in geheim.iterdir()])
        if n:
            print(
                f"ACHTUNG: {n} Eintrag/Eintraege in {SECRETS} — Secrets werden "
                f"NIE archiviert. Nach ~/.secrets uebernehmen und hier loeschen."
            )
            print()

    print(
        f"Zusammenfassung: {len(faellig)} faellig, {len(offen)} unentschieden, "
        f"{len(ruhig)} in Frist."
    )
    return 0


def aufraeumen(posten, apply: bool, heute: datetime.date) -> int:
    faellig = [x for x in posten if x["faellig"]]
    if not faellig:
        print("Nichts faellig.")
        return 0
    ziel = SCHLEUSE / ARCHIV / heute.isoformat()
    print(f"{'VERSCHIEBE' if apply else 'WUERDE VERSCHIEBEN'} nach {ziel}:")
    for x in faellig:
        print(f"  {x['pfad'].name}  ({x['tage']} Tage, {x['klasse']})")
        if apply:
            ziel.mkdir(parents=True, exist_ok=True)
            neu = ziel / x["pfad"].name
            if neu.exists():
                neu = ziel / f"{x['pfad'].name}.{x['tage']}d"
            shutil.move(str(x["pfad"]), str(neu))
    if not apply:
        print("\nNichts geaendert. Mit --apply wirklich verschieben.")
    else:
        print(
            f"\n{len(faellig)} Eintraege archiviert. Geloescht wurde NICHTS — "
            f"dafuer gibt es --endgueltig."
        )
    return 0


def endgueltig(apply: bool, heute: datetime.date, tage: int) -> int:
    basis = SCHLEUSE / ARCHIV
    if not basis.is_dir():
        print("Kein Archiv vorhanden.")
        return 0
    alt = []
    for p in sorted(basis.iterdir()):
        try:
            stand = datetime.date.fromisoformat(p.name)
        except ValueError:
            continue  # nur datierte Ordner, sonst Finger weg
        if (heute - stand).days >= tage:
            alt.append(p)
    if not alt:
        print(f"Nichts im Archiv aelter als {tage} Tage.")
        return 0
    print(f"{'LOESCHE' if apply else 'WUERDE LOESCHEN'} (Archiv > {tage} Tage):")
    for p in alt:
        print(f"  {p.name}  {mb(groesse(p))}")
        if apply:
            shutil.rmtree(p)
    if not apply:
        print("\nNichts geaendert. Mit --apply wirklich loeschen.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--aufraeumen",
        action="store_true",
        help="Faelliges nach _archiv/<datum>/ verschieben",
    )
    ap.add_argument(
        "--endgueltig",
        action="store_true",
        help="Archiv-Ordner aelter als --tage loeschen",
    )
    ap.add_argument("--apply", action="store_true", help="wirklich tun")
    ap.add_argument("--alle", action="store_true", help="auch zeigen, was in Frist ist")
    ap.add_argument("--tage", type=int, default=90, help="Aufbewahrung im Archiv")
    a = ap.parse_args()

    heute = datetime.date.today()
    if a.endgueltig:
        return endgueltig(a.apply, heute, a.tage)
    posten = sammeln(heute)
    if a.aufraeumen:
        return aufraeumen(posten, a.apply, heute)
    return bericht(posten, a.alle)


if __name__ == "__main__":
    sys.exit(main())
