#!/usr/bin/env python3
"""Gate: ein Fix an EINER von mehreren gleichartigen Stellen — die Geschwister
bleiben stehen und werden gemeldet.

Retro-Muster `partial-fix-not-generalized-to-sibling-artifacts` (12 Vorkommen,
deckt sich mit `new-format-gate-no-existing-file-sweep`, 2 Vorkommen). Belegte
Realfaelle (Retro a84f71, 2026-08-23):
  (a) ein Default-Flip in `record()` wurde nur an den WARN-Zweigen nachgezogen;
      zwei praktisch identische PASS-Zweige derselben Datei blieben unveraendert
      und etikettierten fremde Repos weiter als `platform`.
  (b) eine Lane-Liste wurde um `skills` + `commands` erweitert, `hooks` blieb aus.

MECHANIK (bewusst eng — das Haus verlangt eine 0-FP-Baseline, und ein Melder,
der am ersten Tag Fehlalarme wirft, wird umgangen statt befolgt):
Fuer jede im PR geaenderte Datei werden die im Diff ENTFERNTEN Zeilen als
"Vorher-Form" der angefassten Stelle genommen. In der NEUEN Fassung derselben
Datei wird nach Zeilen gesucht, die dieser Vorher-Form sehr aehnlich sind
(difflib-Ratio >= 0.90 nach Whitespace-Normalisierung) und die selbst NICHT
angefasst wurden. Genau das ist der Zwilling, den der Fix vergessen hat.

Warum die Deckel (alle an einer Messung ueber die letzten 150 Nicht-Merge-
Commits von main kalibriert — ohne sie feuerte der Melder auf 18 von 150
Commits, fast ausschliesslich auf Struktur; mit ihnen auf 7):
  - < 25 Zeichen: `)`, `return None`, `import os` sind ueberall gleich und
    tragen keine Aussage darueber, ob hier etwas vergessen wurde.
  - Kommentar-/Leerzeilen, Zeilen ohne alphanumerisches Zeichen: dito.
  - Datenzeilen (weder `(` noch `=`): `ref: achimdehnert/bfagent`,
    `"configured_no_analysis",`, `betriebsstatus: blockiert`, Markdown-
    Tabellenzeilen. In der Messung war KEINE davon ein vergessener Fix —
    Daten wiederholen sich per Definition. Verhalten steht in Zeilen mit
    Aufruf oder Zuweisung.
  - Test- und Fixture-Dateien: wiederholte `assert`- und Fixture-Zeilen waren
    in der Messung die groesste Fehlalarm-Quelle (test_todo_board: 6 Treffer
    auf drei gleichen Assertions).
  - Nur .py .sh .yml .yaml .md .json: bei Binaerem/Generiertem ist eine
    Zeilen-Aehnlichkeit kein Signal.
  - Mehr als 2 aehnliche Geschwister zu EINER Vorher-Zeile: das ist eine
    Tabellen-/Listen-/Matrix-Struktur (Registry-Zeilen, Pin-Listen, Port-
    Tabellen, wiederholte Workflow-Steps). In der Messung war JEDE Gruppe ab
    drei Zwillingen Struktur, keine ein vergessener Fix — der Deckel halbierte
    die Trefferzahl. Preis: ein Fix mit drei oder mehr stehengebliebenen
    Zwillingen faellt durch; das ist bewusst gewaehlt (0-FP zuerst).
  - Hoechstens 5 Befunde je Datei; der Rest wird nur gezaehlt.

Was der Gate NICHT sieht (bleibt Judgment, nicht Automat):
  - semantische Geschwister in ANDEREN Dateien (die Lane-Liste aus Realfall (b)
    findet er nur, wenn der Zwilling in derselben Datei steht),
  - Geschwister, die sich zwar gleich verhalten, aber anders geschrieben sind
    (andere Variablennamen, andere Reihenfolge) — die Ratio bleibt darunter,
  - fehlende Stellen, die es noch gar nicht gibt (ein Fix, der ein neues Muster
    einfuehrt, ohne es auf den Bestand anzuwenden).

Exit: 0 = sauber · 1 = Befund (advisory — der CI-Step bleibt gruen, druckt aber
die Warnung) · 2 = Werkzeugfehler (git-Diff nicht bestimmbar; der CI-Step wird
ROT: ein Melder, der beim Ausfall schweigt, ist schlimmer als keiner).
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gegen
# docs/governance/gate-registry.json abgeglichen.
GATE_HEADER = {
    "slug": "geschwister-stellen-nicht-mitgezogen",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-07",
    "evidence": "tools/tests/test_geschwister_stellen_check.py",
}

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Deckel (Begruendung siehe Modul-Docstring) ------------------------------
AEHNLICHKEIT = 0.90
MIN_LAENGE = 25
MAX_GESCHWISTER = 2
MAX_BEFUNDE_JE_DATEI = 5
GEPRUEFTE_ENDUNGEN = (".py", ".sh", ".yml", ".yaml", ".md", ".json")
# Test-/Fixture-Dateien: dort ist Wiederholung die Norm, nicht der Befund.
TEST_MARKER = ("/tests/", "/fixtures/", "/testdata/")

# Zeilen, die nur Kommentar sind — in allen gepruesten Sprachen zusammen.
_KOMMENTAR = re.compile(r"^\s*(#|//|/\*|\*/|\*\s|<!--|--\s)")
_ALNUM = re.compile(r"[A-Za-z0-9]")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass
class Befund:
    """Eine stehengebliebene Geschwister-Stelle."""

    pfad: str
    zeile: int
    ratio: float
    text: str
    vorlage: str


@dataclass
class DateiDiff:
    """Was der Diff ueber EINE Datei sagt (git-frei konsumierbar)."""

    pfad: str
    entfernte: list[str] = field(default_factory=list)
    geaenderte_nummern: set[int] = field(default_factory=set)


def normalisieren(zeile: str) -> str:
    """Whitespace zusammenziehen — Einrueckungs-Unterschiede sind kein Signal."""
    return " ".join(zeile.split())


def ist_rauschen(norm: str) -> bool:
    """Zeilen, die ueberall gleich aussehen und darum nichts belegen."""
    if len(norm) < MIN_LAENGE:
        return True
    if not _ALNUM.search(norm):
        return True
    if _KOMMENTAR.match(norm):
        return True
    # Datenzeile: kein Aufruf, keine Zuweisung — Wiederholung ist dort Struktur.
    return "(" not in norm and "=" not in norm


def ist_pruefpflichtig(pfad: str) -> bool:
    """Nur Textdateien, bei denen Zeilen-Aehnlichkeit ueberhaupt etwas heisst —
    und keine Test-/Fixture-Datei (dort ist Wiederholung Absicht)."""
    if not pfad.endswith(GEPRUEFTE_ENDUNGEN):
        return False
    p = f"/{pfad}"
    if any(marker in p for marker in TEST_MARKER):
        return False
    name = pfad.rsplit("/", 1)[-1]
    return not (name.startswith("test_") or name == "conftest.py")


def befunde_fuer(
    entfernte_zeilen: list[str],
    neue_zeilen: list[str],
    geaenderte_nummern: set[int],
    pfad: str = "",
) -> list[Befund]:
    """Kernlogik, git-frei und damit drillbar.

    Eingabe: die im Diff entfernten Zeilen einer Datei, der Inhalt der NEUEN
    Fassung (zeilenweise, 1-basiert gezaehlt) und die Zeilennummern, die im Diff
    selbst angefasst wurden. Ausgabe: alle Zeilen, die einer Vorher-Zeile sehr
    aehnlich sind, aber unangetastet blieben — sortiert nach Zeilennummer, ohne
    Deckel auf die Anzahl (den setzt der Aufrufer, damit er den Rest zaehlen kann).
    """
    kandidaten: list[tuple[int, str]] = []
    for nr, roh in enumerate(neue_zeilen, start=1):
        if nr in geaenderte_nummern:
            continue
        norm = normalisieren(roh)
        if ist_rauschen(norm):
            continue
        kandidaten.append((nr, norm))
    if not kandidaten:
        return []

    # Zeilennummer -> (bester ratio, Vorlage). Eine Zeile kann zu mehreren
    # Vorher-Zeilen passen; gemeldet wird sie einmal, mit dem staerksten Treffer.
    treffer: dict[int, tuple[float, str]] = {}
    gesehen: set[str] = set()
    for entfernt in entfernte_zeilen:
        vorher = normalisieren(entfernt)
        if ist_rauschen(vorher) or vorher in gesehen:
            continue
        gesehen.add(vorher)
        matcher = difflib.SequenceMatcher(a=vorher, autojunk=False)
        aehnliche: list[tuple[int, str, float]] = []
        for nr, norm in kandidaten:
            matcher.set_seq2(norm)
            if matcher.real_quick_ratio() < AEHNLICHKEIT:
                continue
            if matcher.quick_ratio() < AEHNLICHKEIT:
                continue
            ratio = matcher.ratio()
            if ratio >= AEHNLICHKEIT:
                aehnliche.append((nr, norm, ratio))
        # Deckel: viele Zwillinge = Tabellen-/Listenstruktur, kein vergessener Fix.
        if len(aehnliche) > MAX_GESCHWISTER:
            continue
        for nr, norm, ratio in aehnliche:
            if nr not in treffer or ratio > treffer[nr][0]:
                treffer[nr] = (ratio, vorher)

    inhalt = {nr: norm for nr, norm in kandidaten}
    return [
        Befund(pfad=pfad, zeile=nr, ratio=r, text=inhalt[nr], vorlage=v)
        for nr, (r, v) in sorted(treffer.items())
    ]


def diff_dateien(bereich: str, repo_root: Path) -> list[DateiDiff] | None:
    """`git diff --unified=0` parsen; None = git-Fehler (nicht bewertbar)."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--unified=0",
                "--no-color",
                "--no-ext-diff",
                bereich,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return diff_parsen(out.stdout)


def diff_parsen(diff_text: str) -> list[DateiDiff]:
    """Reine Parse-Funktion (drillbar): unified=0-Diff -> DateiDiff je Datei."""
    dateien: list[DateiDiff] = []
    aktuell: DateiDiff | None = None
    for zeile in diff_text.splitlines():
        if zeile.startswith("+++ "):
            ziel = zeile[4:].strip()
            if ziel == "/dev/null":
                aktuell = None  # geloescht: es gibt keine neue Fassung
                continue
            pfad = ziel[2:] if ziel.startswith(("a/", "b/")) else ziel
            aktuell = DateiDiff(pfad=pfad)
            dateien.append(aktuell)
            continue
        if aktuell is None:
            continue
        if zeile.startswith("@@"):
            m = _HUNK.match(zeile)
            if m:
                start = int(m.group(1))
                anzahl = int(m.group(2)) if m.group(2) is not None else 1
                aktuell.geaenderte_nummern.update(range(start, start + anzahl))
            continue
        if zeile.startswith("-") and not zeile.startswith("---"):
            aktuell.entfernte.append(zeile[1:])
    return dateien


def bereichs_endpunkt(bereich: str) -> str:
    """Der Commit, dessen Fassung "die neue" ist: was hinter dem letzten `..` steht.

    Bewusst NICHT der Arbeitsbaum: gemessen 2026-09-07 an einem Lauf, bei dem
    `origin/main` dem ausgecheckten HEAD voraus war — die Zeilennummern aus dem
    Diff trafen dann auf eine andere Datei und der Melder erfand drei Befunde.
    Ein Gate, das nur stimmt, solange das Ziel zufaellig ausgecheckt ist, misst
    nicht den Pfad, den er behauptet zu messen.
    """
    for trenner in ("...", ".."):
        if trenner in bereich:
            return bereich.split(trenner)[-1].strip() or "HEAD"
    return bereich.strip() or "HEAD"


def neue_fassung(pfad: str, repo_root: Path, endpunkt: str) -> list[str] | None:
    """Fassung am Endpunkt des Bereichs lesen; None = nicht lesbar (uebergehen:
    geloescht, umbenannt oder binaer — kein Werkzeugfehler)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{endpunkt}:{pfad}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.splitlines()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Stehengebliebene Geschwister-Stellen im PR-Diff melden (advisory)"
    )
    ap.add_argument(
        "--range",
        required=True,
        help="git-Diff-Bereich, z.B. origin/main...HEAD",
    )
    ap.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repo-Wurzel (Default: Repo dieses Skripts)",
    )
    args = ap.parse_args()
    root = Path(args.repo_root)

    dateien = diff_dateien(args.range, root)
    if dateien is None:
        print(
            "⚠ git-Diff nicht bestimmbar — NICHT bewertbar (nie als sauber werten).",
            file=sys.stderr,
        )
        return 2

    endpunkt = bereichs_endpunkt(args.range)
    alle: list[tuple[str, list[Befund], int]] = []
    for datei in dateien:
        if not ist_pruefpflichtig(datei.pfad) or not datei.entfernte:
            continue
        neu = neue_fassung(datei.pfad, root, endpunkt)
        if neu is None:
            continue
        befunde = befunde_fuer(
            datei.entfernte, neu, datei.geaenderte_nummern, datei.pfad
        )
        if not befunde:
            continue
        sichtbar = befunde[:MAX_BEFUNDE_JE_DATEI]
        alle.append((datei.pfad, sichtbar, len(befunde) - len(sichtbar)))

    if not alle:
        print(
            "✅ Keine stehengebliebenen Geschwister-Stellen im Diff"
            " (oder es gab keine gepruefte Aenderung)."
        )
        return 0

    print(
        "⚠ Geschwister-Stellen, die der Fix nicht mitgezogen hat"
        " (Retro-Muster partial-fix-not-generalized-to-sibling-artifacts):"
    )
    for pfad, befunde, rest in alle:
        print(f"   {pfad}:")
        for b in befunde:
            print(f"     - Zeile {b.zeile} (Aehnlichkeit {b.ratio:.2f}): {b.text}")
            print(f"       geaendert wurde die fast gleiche Zeile: {b.vorlage}")
        if rest:
            print(f"     … und {rest} weitere in dieser Datei (nicht gelistet).")
    print(
        "   → Entweder die Geschwister mitziehen ODER im PR kurz begruenden, warum"
        " sie bewusst bleiben (das Gate ist advisory; Fehlalarm-Feedback fliesst"
        " in die Kalibrierung)."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
