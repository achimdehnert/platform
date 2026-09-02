#!/usr/bin/env python3
"""melder_register_check.py — Vorausschauende Wartung fuer die Session-Start-Melder (#2690 K3).

Drei Dinge, alle aus derselben Messung 2026-09-02 (Audit #2606-Muster): 33 Melder-
Phasen im Runner (`tools/session_start_checks.sh`), aber kein einziger trug eine
Trefferquote, eine Wiedervorlage-Frist oder einen benannten Leser AUSSER dort, wo
`.windsurf/workflows/session-start.md` es zufaellig in Prosa erwaehnte. Ein Melder
ohne Leser ist ein Melder, der niemanden erreicht — dieselbe Klasse wie ein rueck-
faelliges Gate (0.7.7), nur auf der Registrierungsseite.

`governance/melder-register.yaml` ist die Registry: ein Eintrag je Runner-Phase mit
`leser`, `wiedervorlage_tage`, `praezision_min`, `mindest_laeufe`, `runbook`. Dieses
Skript prueft die Registry gegen zwei Quellen und wandelt Befunde in Selbst-
Herabstufung um:

  --kurz               Runner-Phasen ohne Register-Eintrag + Eintraege mit
                        `leser: UNBENANNT` (= "Melder ohne Leser") sowie
                        Register-Eintraege ohne passende Runner-Phase
                        (Karteileiche). Eine Zeile fuer den Runner (Phase
                        0.7.23), Exit 1 bei jedem Treffer.
  --herabstufung        Liest `befund_journal.py --praezision --json`; ein Melder,
                        der ueber >= `mindest_laeufe` beurteilte Laeufe unter
                        `praezision_min` liegt, wird nach
                        ~/.claude/hooks/state/melder-herabgestuft.tsv geschrieben
                        (Pfad per --ziel-datei ueberschreibbar). Der Runner liest
                        diese Datei zu Beginn des NAECHSTEN Laufs (0.7.19 misst
                        spaet) und wandelt fuer gelistete Phasen WARN in HINWEIS.
  --ohne-entscheidung    Liest `befund_journal.py --bericht --json`; Befunde, die
                        weder verankert noch verzichtet sind und aelter als
                        `--tage` (Default 14) Tage, als eigener Block.

Bewusst NICHT hier drin: kein Anlegen von Issues, kein Netzzugriff. Wie
`befund_journal.py` ist dies ein Gedaechtnis- und Registry-Pruefer, kein Handelnder.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
PLATFORM_DIR = TOOLS_DIR.parent

DEFAULT_REGISTER = PLATFORM_DIR / "governance" / "melder-register.yaml"
DEFAULT_RUNNER = TOOLS_DIR / "session_start_checks.sh"
DEFAULT_BEFUND_JOURNAL = TOOLS_DIR / "befund_journal.py"
DEFAULT_HERABSTUFUNG_DATEI = Path.home() / ".claude" / "hooks" / "state" / "melder-herabgestuft.tsv"

#: Faellt fuer eine Registry-Zeile keine Zahl, gilt dieser Default (siehe
#: FRIST_VERANKERT_TAGE / PRAEZISION_SCHWELLE / MIN_URTEILE in befund_journal.py —
#: bewusst eigene Konstanten hier, damit die Registry das letzte Wort behaelt).
DEFAULT_WIEDERVORLAGE_TAGE = 14
DEFAULT_PRAEZISION_MIN = 0.6
DEFAULT_MINDEST_LAEUFE = 5
DEFAULT_OHNE_ENTSCHEIDUNG_TAGE = 14

#: Wert, der explizit "kein Leser hinterlegt" bedeutet — ehrlich lassen, nicht
#: erfinden (Auftrag #2690 K3).
UNBENANNT = "UNBENANNT"


def lade_register(pfad: Path) -> list[dict]:
    """Registry laden. Fehlt die Datei oder ist sie kaputt: leere Liste, kein Crash."""
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(daten, dict):
        return []
    eintraege = daten.get("melder")
    if not isinstance(eintraege, list):
        return []
    return [e for e in eintraege if isinstance(e, dict) and e.get("phase")]


def lade_runner_phasen(pfad: Path) -> set[str]:
    """Phasen-IDs aus dem Runner-Skript — dieselbe Regex wie die Session-Start-Doku.

    ``grep -oE 'record "[0-9][^"]*"' tools/session_start_checks.sh | sort -u``
    """
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(re.findall(r'record "([0-9][^"]*)"', text))


def register_zuordnung(register: list[dict]) -> dict[str, dict]:
    """Phase -> letzter Register-Eintrag (Duplikate: der letzte gewinnt, wie YAML es tut)."""
    return {e["phase"]: e for e in register}


def register_pruefen(
    register: list[dict], runner_phasen: set[str]
) -> tuple[list[str], list[str], list[str]]:
    """(fehlende Eintraege, UNBENANNT-Eintraege, Karteileichen) — je sortierte Liste.

    * fehlend: Runner-Phase ohne jeden Register-Eintrag.
    * unbenannt: Register-Eintrag mit ``leser: UNBENANNT`` (unabhaengig davon, ob
      die Phase noch im Runner steht — auch das ist ein Melder ohne Leser).
    * karteileiche: Register-Eintrag, dessen Phase der Runner nicht mehr kennt.
    """
    by_phase = register_zuordnung(register)
    fehlend = sorted(runner_phasen - set(by_phase))
    unbenannt = sorted(
        phase for phase, e in by_phase.items() if str(e.get("leser", "")).strip() == UNBENANNT
    )
    karteileiche = sorted(set(by_phase) - runner_phasen)
    return fehlend, unbenannt, karteileiche


def _liste_kurz(werte: list[str], zeige: int = 3) -> str:
    if not werte:
        return ""
    kopf = ", ".join(werte[:zeige])
    rest = len(werte) - zeige
    return kopf + (f" (+{rest} weitere)" if rest > 0 else "")


def kurz_bericht(register: list[dict], runner_phasen: set[str]) -> tuple[str, int]:
    """Eine-Zeile-Zusammenfassung (+ Detailzeilen) fuer den Runner. (text, exit_code)."""
    fehlend, unbenannt, karteileiche = register_pruefen(register, runner_phasen)
    ohne_leser = sorted(set(fehlend) | set(unbenannt))
    zeilen: list[str] = []
    if ohne_leser:
        zeilen.append(f"{len(ohne_leser)} Melder ohne Leser: {_liste_kurz(ohne_leser)}")
    if karteileiche:
        praefix = "" if ohne_leser else "0 Melder ohne Leser — "
        zeilen.append(
            f"{praefix}{len(karteileiche)} Karteileiche(n) im Register "
            f"ohne Runner-Phase: {_liste_kurz(karteileiche)}"
        )
    if not zeilen:
        return "", 0
    return "\n".join(zeilen), 1


def _befund_journal_json(
    befund_journal_py: Path, *args: str, journal_datei: Path | None, repo: str
) -> list[dict]:
    cmd = [sys.executable, str(befund_journal_py), *args, "--repo", repo]
    if journal_datei is not None:
        cmd += ["--datei", str(journal_datei)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        return []
    try:
        daten = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    return daten if isinstance(daten, list) else []


def herabstufungen(register: list[dict], praezisions_daten: list[dict], heute: str) -> list[dict]:
    """Melder, die ueber >= mindest_laeufe beurteilte Laeufe unter praezision_min liegen.

    ``praezisions_daten`` ist die Ausgabe von ``befund_journal.py --praezision --json``:
    je Melder ``{"phase", "echt", "falsch", "urteile", "praezision", "bewertbar"}``.
    """
    by_phase = register_zuordnung(register)
    ergebnis = []
    for z in praezisions_daten:
        phase = z.get("phase")
        laeufe = z.get("urteile") or 0
        quote = z.get("praezision")
        eintrag = by_phase.get(phase, {})
        mindest = eintrag.get("mindest_laeufe", DEFAULT_MINDEST_LAEUFE)
        schwelle = eintrag.get("praezision_min", DEFAULT_PRAEZISION_MIN)
        if quote is None or laeufe < mindest or quote >= schwelle:
            continue
        ergebnis.append(
            {"phase": phase, "quote": quote, "laeufe": laeufe, "datum": heute}
        )
    ergebnis.sort(key=lambda z: z["phase"])
    return ergebnis


def schreibe_herabstufung_tsv(zeilen: list[dict], ziel: Path) -> None:
    """Schreibt die aktuelle Herabstufungsliste komplett neu (kein Anhaengen —
    eine geheilte Phase soll aus der Datei verschwinden, nicht liegen bleiben)."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with ziel.open("w", encoding="utf-8") as f:
        for z in zeilen:
            f.write(f"{z['phase']}\t{z['quote']:.4f}\t{z['laeufe']}\t{z['datum']}\n")


def ohne_entscheidung_liste(bericht_daten: list[dict], tage: int, heute: date) -> list[dict]:
    """Befunde ohne Verankerung/Verzicht, aelter als ``tage`` Tage (nach ``erstmals``).

    ``bericht_daten`` ist die Ausgabe von ``befund_journal.py --bericht --json``.
    """
    ergebnis = []
    for e in bericht_daten:
        if e.get("artefakt") or e.get("verzicht"):
            continue
        erstmals = e.get("erstmals")
        if not erstmals:
            continue
        try:
            erstmals_datum = date.fromisoformat(str(erstmals))
        except ValueError:
            continue
        alter = (heute - erstmals_datum).days
        if alter > tage:
            ergebnis.append(
                {
                    "id": e.get("id"),
                    "phase": e.get("phase"),
                    "repo": e.get("repo"),
                    "alter_tage": alter,
                    "erstmals": erstmals,
                }
            )
    ergebnis.sort(key=lambda z: -z["alter_tage"])
    return ergebnis


def ohne_entscheidung_block(eintraege: list[dict], tage: int) -> str:
    kopf = f"⏳ ohne Entscheidung > {tage} d"
    if not eintraege:
        return f"{kopf}: keiner"
    zeilen = [f"{kopf} ({len(eintraege)}):"]
    for e in eintraege:
        zeilen.append(
            f"  {e['phase']} [{e['repo']}] — {e['alter_tage']} d alt, "
            f"erstmals {e['erstmals']}"
        )
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kurz", action="store_true", help="fehlende/UNBENANNT/Karteileiche, eine Zeile")
    p.add_argument("--herabstufung", action="store_true", help="Melder unter Schwelle in TSV schreiben")
    p.add_argument("--ohne-entscheidung", action="store_true", help="Befunde ohne Entscheidung > --tage")
    p.add_argument("--tage", type=int, default=DEFAULT_OHNE_ENTSCHEIDUNG_TAGE)
    p.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    p.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    p.add_argument("--befund-journal", type=Path, default=DEFAULT_BEFUND_JOURNAL)
    p.add_argument("--journal-datei", type=Path, default=None, help="Journal-Pfad (Tests)")
    p.add_argument("--ziel-datei", type=Path, default=DEFAULT_HERABSTUFUNG_DATEI)
    p.add_argument("--repo", default="platform")
    a = p.parse_args(argv)

    register = lade_register(a.register)

    if a.kurz:
        runner_phasen = lade_runner_phasen(a.runner)
        text, rc = kurz_bericht(register, runner_phasen)
        if text:
            print(text)
        return rc

    if a.herabstufung:
        praez = _befund_journal_json(
            a.befund_journal, "--praezision", "--json",
            journal_datei=a.journal_datei, repo=a.repo,
        )
        heute = datetime.now(timezone.utc).date().isoformat()
        gefunden = herabstufungen(register, praez, heute)
        schreibe_herabstufung_tsv(gefunden, a.ziel_datei)
        if gefunden:
            teile = ", ".join(
                f"{z['phase']} ({z['quote']:.0%} ueber {z['laeufe']} Laeufe)" for z in gefunden
            )
            print(f"{len(gefunden)} Melder herabgestuft -> {a.ziel_datei}: {teile}")
        else:
            print(f"kein Melder unter der Schwelle — {a.ziel_datei} geleert")
        return 0

    if a.ohne_entscheidung:
        bericht = _befund_journal_json(
            a.befund_journal, "--bericht", "--json",
            journal_datei=a.journal_datei, repo=a.repo,
        )
        heute = datetime.now(timezone.utc).date()
        eintraege = ohne_entscheidung_liste(bericht, a.tage, heute)
        print(ohne_entscheidung_block(eintraege, a.tage))
        return 0

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
