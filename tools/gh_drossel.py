#!/usr/bin/env python3
"""gh_drossel.py — echte Drosselungs-Probe und Sperre gegen gleichzeitige Flotten-Laeufe.

GATE_HEADER (KONZ-038 D8):
  "slug": "throttled-api-read-as-empty-result"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-03"
  "evidence": "tools/tests/test_gh_drossel.py"

Anlass (platform#2735, gemessen 2026-09-02)
-------------------------------------------
`scripts/drift_check.py` lieferte fuer denselben Stand binnen Minuten 19, dann 10,
dann **0** Errors. Der Null-Lauf sah am besten aus und war der wertloseste: hinter
jedem der 26 Repos stand „Repo nicht gefunden oder privat". Ursache war das
**sekundaere** GitHub-Ratenlimit — sechs parallele Sitzungen an einem Token, dazu
drei gleichzeitige Flotten-Scans.

Zwei Lehren, die dieses Modul umsetzt:

1. **`gh api rate_limit` beantwortet die Frage NICHT.** Es meldete im selben Moment
   `core.remaining: 5000`, waehrend echte Aufrufe abgewiesen wurden — das
   Primaerlimit war unberuehrt. Die einzige belastbare Probe ist **ein echter
   Aufruf** gegen ein echtes Repo.
2. **Der Ausloeser war Gleichzeitigkeit.** Eine Sperre kostet nichts und nimmt dem
   Problem die Ursache, statt nur das Symptom ehrlich zu machen.

Beide Teile sind bewusst in EINEM Modul: ein Melder, der das eine nutzt, braucht
fast immer auch das andere.

Nutzung im Melder
-----------------
    from gh_drossel import DrosselFehler, probe, flotten_sperre

    with flotten_sperre("drift-check"):
        probe()                      # wirft DrosselFehler, wenn gedrosselt
        ...  # Flotten-Scan

Wer keine Ausnahme will:

    if not probe(werfen=False):
        return 2                     # „nicht messbar" — NICHT 0

Exit-Codes der CLI
------------------
0 = erreichbar · 2 = gedrosselt oder nicht erreichbar (nie 1: „gedrosselt" ist
kein Befund ueber die Welt, sondern ueber die Messung).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ein oeffentliches, langlebiges Repo der eigenen Org — die Probe soll an der
# Drosselung scheitern, nicht an fehlenden Rechten.
PROBE_REPO = "achimdehnert/platform"
SPERR_DATEI = Path(os.environ.get("HOME", "/tmp")) / ".claude" / "flotten-sperre.json"
SPERR_ALTER_S = 1800  # eine Sperre, die aelter ist, gehoert einem toten Lauf
WARTE_S = 5


class DrosselFehler(RuntimeError):
    """Die API antwortet nicht — blind ist nicht gruen."""


def _gh(pfad: str, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["gh", "api", pfad, "--jq", ".full_name"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as exc:
        return 127, str(exc)


def probe(repo: str = PROBE_REPO, werfen: bool = True, laeufer=None) -> bool:
    """EIN echter Aufruf. `True` = die API antwortet und liefert Daten.

    Bewusst nicht `gh api rate_limit`: das misst das Primaerlimit und meldete am
    2026-09-02 5000 freie Aufrufe, waehrend jeder echte Aufruf abgewiesen wurde.
    """
    laeufer = laeufer or _gh
    rc, aus = laeufer(f"repos/{repo}")
    if rc == 0 and repo.split("/")[-1] in aus:
        return True
    grund = "rate limit" if "rate limit" in aus.lower() else f"rc={rc}"
    if werfen:
        raise DrosselFehler(
            f"GitHub antwortet nicht auf `repos/{repo}` ({grund}). "
            "Das ist ein Werkzeugfehler, KEIN leeres Ergebnis. "
            "`gh api rate_limit` beantwortet die Frage nicht — es misst das "
            "Primaerlimit, gedrosselt wird sekundaer."
        )
    return False


def _sperre_lesen(pfad: Path) -> dict | None:
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def sperre_frei(pfad: Path | None = None, jetzt: float | None = None) -> bool:
    """Frei, wenn keine Sperre liegt ODER die liegende verwaist ist.

    Eine Sperre ohne Verfall waere schlimmer als keine: ein abgestuerzter Lauf
    wuerde die Flotte dauerhaft blockieren, und der naechste Mensch loescht die
    Datei blind — dann ist die Sperre wirkungslos UND niemand traut ihr mehr.
    """
    pfad = pfad or SPERR_DATEI
    jetzt = jetzt if jetzt is not None else time.time()
    if not pfad.exists():
        return True
    d = _sperre_lesen(pfad)
    if not d:
        return True
    return (jetzt - float(d.get("seit", 0))) > SPERR_ALTER_S


@contextlib.contextmanager
def flotten_sperre(name: str, pfad: Path | None = None, warten_s: int = 0):
    """Nur ein Flotten-Lauf gleichzeitig. `warten_s=0` = sofort aufgeben."""
    pfad = pfad or SPERR_DATEI
    pfad.parent.mkdir(parents=True, exist_ok=True)
    ende = time.time() + warten_s
    while not sperre_frei(pfad):
        if time.time() >= ende:
            d = _sperre_lesen(pfad) or {}
            raise DrosselFehler(
                f"Ein Flotten-Lauf laeuft bereits: `{d.get('name', '?')}` "
                f"seit {d.get('gestartet', '?')}. Gleichzeitige Scans waren am "
                "2026-09-02 die Ursache der Drosselung (platform#2735)."
            )
        time.sleep(min(WARTE_S, max(1, int(ende - time.time()))))
    pfad.write_text(
        json.dumps(
            {
                "name": name,
                "pid": os.getpid(),
                "seit": time.time(),
                "gestartet": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        ),
        encoding="utf-8",
    )
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            d = _sperre_lesen(pfad)
            if d and d.get("pid") == os.getpid():
                pfad.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=PROBE_REPO)
    ap.add_argument(
        "--sperre", action="store_true", help="nur den Sperr-Zustand zeigen"
    )
    args = ap.parse_args(argv)

    if args.sperre:
        frei = sperre_frei()
        d = _sperre_lesen(SPERR_DATEI) or {}
        print(
            "frei"
            if frei
            else f"belegt von `{d.get('name', '?')}` seit {d.get('gestartet', '?')}"
        )
        return 0 if frei else 2

    try:
        probe(args.repo)
    except DrosselFehler as exc:
        print(f"⛔ {exc}", file=sys.stderr)
        return 2
    print(f"✅ GitHub antwortet auf repos/{args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
