#!/usr/bin/env python3
"""Gate: ein NEUES Werkzeug-Modul kommt mit einem Test — oder wird gemeldet.

Retro-Muster `untested-tool-module-green-gate` (platform#1650, Owner-Go
2026-08-12): `tools-tests.yml` prueft den BESTAND zuverlaessig (make test,
blockierend), aber nichts prueft NEUZUGAENGE — ein neues tools/*.py ohne jede
Testdatei laesst CI gruen. Der Workflow sagt es selbst (Ehrlichkeits-Hinweis:
~24 scripts/*.py ungetestet, "Gate laeuft gruen, ohne sie zu pruefen").

Bewusst NUR im PR HINZUGEFUEGTE Dateien (--diff-filter=A): die Altfaelle sind
Bestandsschutz — ein Gate, das am ersten Tag 24 fremde Befunde wirft, wird
umgangen statt befolgt (repo-health-Disziplin: 0-FP-Baseline zuerst).

Ein Modul gilt als getestet, wenn EINE der beiden Spuren existiert:
  1. eine Testdatei test_<stem>.py irgendwo unter tools/ oder tests/, ODER
  2. sein Stem kommt in einer Testdatei als BEZUG vor — Import, Pfad oder
     String-Literal (deckt Suites ab, die mehrere Module in einer Datei testen,
     z.B. test_block_unformatted_push_suite).

REV 2 (2026-09-07, platform#2374 — das Gate war rueckfaellig ×4). Zwei
Ausweitungen, beide aus den Rueckfaellen selbst:

(1) SPUR 2 WAR ZU WEICH. „Stem kommt woertlich vor" traf auch eine blosse
    Erwaehnung in einem Docstring oder Kommentar. Ein Modul galt damit als
    getestet, weil sein Name irgendwo in einer Testdatei STAND — genau die
    Verwechslung von Schreibweise und Sache, gegen die dieses Gate steht.
    Rueckfall 4b1399 #4: `link_pruefen.py` ohne Test und ohne CI-Einbindung.
    Jetzt zaehlt nur ein BEZUG: `import <stem>`, `from <stem>`, ein Pfad
    (`.../<stem>.py`) oder ein String-Literal mit dem Stem.

(2) DIE FAMILIE FEHLTE. Das Gate adressiert Werkzeug-MODULE; der Rueckfall
    cc4e11 #4 traf einen TEST, der selbst als Gate dient: das erste Klassen-Gate
    bestand seine eigene Gegenprobe nicht (ein 3000-Zeichen-Fenster griff in die
    Nachbarfunktion), und niemand haette es gemerkt, weil der Drill gruen war.
    Eine neu hinzugefuegte Testdatei, die sich im Text selbst als Gate-Drill
    ausweist (Gate / Klassen-Gate / Positivkontrolle / Drill), muss deshalb
    ihren FALSIFIKATIONSLAUF dokumentieren — eine Testfunktion oder eine Zeile,
    die den Gegenprobe-Fall benennt. Ehrlich benannte Grenze: das Gate erzwingt,
    dass die Gegenprobe DASTEHT, nicht dass sie richtig ist. Das ist der
    Unterschied zwischen „vergessen" und „falsch gemacht"; gegen das zweite hilft
    kein Scanner (siehe `test-asserts-the-case-in-mind-not-the-harmful-one` in
    der declined-Liste).

Exit: 0 = sauber · 1 = Befund (advisory — der CI-Step bleibt gruen, druckt aber
die Warnung) · 2 = Werkzeugfehler (der CI-Step wird ROT: ein Melder, der beim
Ausfall schweigt, ist schlimmer als keiner).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gegen
# docs/governance/gate-registry.json abgeglichen.
GATE_HEADER = {
    "slug": "untested-tool-module-green-gate",
    "mode": "advisory",  # blocking erst nach 0-FP-Kalibrierfenster (Registry-frozen_note)
    "owner": "achim",
    "last_drill_pass": "2026-09-07",
    "evidence": "tools/tests/test_check_new_module_tests.py",
}

REPO_ROOT = Path(__file__).resolve().parent.parent

# Nur diese Wurzeln werden auf ungetestete Neuzugaenge geprueft.
MODUL_WURZELN = ("tools/", "scripts/")
# Verzeichnisse, in denen nach Test-Spuren gesucht wird.
TEST_WURZELN = ("tools", "tests", "scripts")


def ist_pruefpflichtig(pfad: str) -> bool:
    """Neuzugang, der einen Test braucht: .py unter tools/ oder scripts/,
    aber keine Testdatei, kein __init__, kein conftest, kein tests/-Ordner."""
    if not pfad.endswith(".py"):
        return False
    if not pfad.startswith(MODUL_WURZELN):
        return False
    p = Path(pfad)
    if "tests" in p.parts:
        return False
    name = p.name
    return not (name.startswith("test_") or name in ("__init__.py", "conftest.py"))


def bezug_muster(stem: str) -> re.Pattern:
    """Spur 2 als BEZUG statt als blosse Erwaehnung (Rev 2).

    Getroffen wird: `import <stem>`, `from <stem>`, ein Pfad mit `<stem>.py`
    und ein String-Literal, das den Stem als ganzes Wort traegt (so rufen die
    Suiten ihre Skripte auf: `SCRIPT = REPO_ROOT / "tools" / "x.py"`,
    `subprocess.run([... "tools/x.py"])`). NICHT getroffen: der Stem in Prosa —
    ein Docstring, der ein Modul nur nennt, testet es nicht.
    """
    s = re.escape(stem)
    return re.compile(
        rf"(?:^|\W)(?:import|from)\s+{s}\b"
        rf"|{s}\.py\b"
        rf"|[\"']{s}[\"']"
        rf"|/{s}\b",
        re.M,
    )


def hat_test_spur(stem: str, repo_root: Path) -> bool:
    """Spur 1: test_<stem>.py existiert; Spur 2: Stem steht als BEZUG in einer Testdatei."""
    for wurzel in TEST_WURZELN:
        basis = repo_root / wurzel
        if not basis.is_dir():
            continue
        if any(basis.rglob(f"test_{stem}.py")):
            return True
    muster = bezug_muster(stem)
    for wurzel in TEST_WURZELN:
        basis = repo_root / wurzel
        if not basis.is_dir():
            continue
        for testdatei in basis.rglob("test_*.py"):
            try:
                if muster.search(testdatei.read_text(encoding="utf-8")):
                    return True
            except OSError:
                continue
    return False


#: Eine Testdatei weist sich SELBST als Gate-Drill aus, wenn eines dieser Woerter
#: in ihr steht. Bewusst am Text der Datei und nicht an der Registry: der Drill
#: entsteht im selben PR wie das Gate, die Registry-Zeile oft erst danach.
GATE_DRILL_MARKER = re.compile(
    r"\bKlassen-Gate\b|\bPositivkontrolle\b|\bGate\b|\bDrill\b", re.I
)

#: Der dokumentierte Falsifikationslauf: eine Testfunktion oder eine Zeile, die
#: den Gegenprobe-Fall benennt. Die Liste ist die im Haus tatsaechlich benutzte
#: Wortmenge, nicht eine erratene — sie stammt aus den bestehenden Drills.
FALSIFIKATION_MARKER = re.compile(
    r"falsifik\w*|gegenprobe|positivkontrolle|negativkontrolle"
    r"|def\s+test_should_(?:flag|fail|block|report|warn|refuse|reject|catch|melden|feuern)\w*",
    re.I,
)


def ist_gate_drill(text: str) -> bool:
    """Weist die Testdatei sich selbst als Gate-Drill aus?"""
    return bool(GATE_DRILL_MARKER.search(text))


def hat_falsifikationslauf(text: str) -> bool:
    """Steht die Gegenprobe DA? (nicht: ist sie richtig — s. Modulkopf)"""
    return bool(FALSIFIKATION_MARKER.search(text))


def ist_neue_testdatei(pfad: str) -> bool:
    """Neu hinzugefuegte Testdatei unter den Test-Wurzeln."""
    p = Path(pfad)
    return (
        pfad.endswith(".py")
        and p.name.startswith("test_")
        and p.parts
        and p.parts[0] in TEST_WURZELN
    )


def hinzugefuegte_dateien(bereich: str, repo_root: Path) -> list[str] | None:
    """--diff-filter=A ueber den Bereich; None = git-Fehler (nicht bewertbar)."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--name-only",
                "--diff-filter=A",
                bereich,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return [z.strip() for z in out.stdout.splitlines() if z.strip()]


def befunde_fuer(dateien: list[str], repo_root: Path) -> list[str]:
    """Kernlogik, git-frei und damit drillbar: neue Module ohne Test-Spur."""
    befunde = []
    for pfad in dateien:
        if not ist_pruefpflichtig(pfad):
            continue
        stem = Path(pfad).stem
        if not hat_test_spur(stem, repo_root):
            befunde.append(pfad)
    return befunde


def drill_befunde_fuer(dateien: list[str], repo_root: Path) -> list[str]:
    """Rev 2, zweite Familie: neue Gate-Drills ohne dokumentierten Falsifikationslauf."""
    befunde = []
    for pfad in dateien:
        if not ist_neue_testdatei(pfad):
            continue
        voll = Path(pfad) if Path(pfad).is_absolute() else repo_root / pfad
        try:
            text = voll.read_text(encoding="utf-8")
        except OSError:
            continue
        if ist_gate_drill(text) and not hat_falsifikationslauf(text):
            befunde.append(pfad)
    return befunde


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Neue tools/scripts-Module ohne Test melden (advisory)"
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

    dateien = hinzugefuegte_dateien(args.range, root)
    if dateien is None:
        print(
            "⚠ git-Diff nicht bestimmbar — NICHT bewertbar (nie als sauber werten).",
            file=sys.stderr,
        )
        return 2

    befunde = befunde_fuer(dateien, root)
    drills = drill_befunde_fuer(dateien, root)
    if not befunde and not drills:
        print(
            "✅ Neuzugaenge: jedes neue Modul hat eine Test-Spur, jeder neue "
            "Gate-Drill seinen Falsifikationslauf (oder es gab keine)."
        )
        return 0

    if befunde:
        print(
            "⚠ Neue Module OHNE Test-Spur (Retro-Muster untested-tool-module-green-gate):"
        )
        for b in befunde:
            print(
                f"   - {b} (weder test_{Path(b).stem}.py noch ein Bezug in einer Testdatei)"
            )
    if drills:
        print(
            "⚠ Neue Gate-Drills OHNE dokumentierten Falsifikationslauf "
            "(Rev 2, Realfall cc4e11 #4 — Klassen-Gate bestand die eigene Gegenprobe nicht):"
        )
        for d in drills:
            print(
                f"   - {d} (weist sich als Gate/Drill aus, nennt aber keine "
                "Gegenprobe/Positivkontrolle)"
            )
    print(
        "   → Testdatei bzw. Gegenprobe nachliefern ODER im PR kurz begruenden, warum nicht"
        " (Fehlalarm-Feedback fliesst in die Kalibrierung, das Gate ist advisory)."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
