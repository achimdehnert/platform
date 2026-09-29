"""Tests fuer `_deploy_probe` in Phase 0.7 (deploy-scan).

Getestet wird die **ausgelieferte** Shell-Funktion aus `session_start_checks.sh`,
nicht eine Kopie. `gh` wird durch ein Stub-Skript ersetzt, das die Ausgabe
liefert, die das echte `gh --jq` fuer den jeweiligen Fall erzeugt — ein Run am
Environment-Gate hat `conclusion: ""` (nicht null), live belegt an
iilgmbh/risk-hub Run 36549529631.

Anlass (platform, 2026-09-29): das leere Feld liess `read` die Felder
verschieben; der Rejected-Zaehler "0" landete als Zeitstempel in W und meldete
ein 12 min altes Gate als "waiting>24h".
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

_SKRIPT = Path(__file__).resolve().parents[1] / "session_start_checks.sh"


def _funktion() -> str:
    text = _SKRIPT.read_text(encoding="utf-8")
    treffer = re.search(r"^_deploy_probe\(\) \{.*?^\}$", text, re.S | re.M)
    assert treffer, "_deploy_probe nicht im Skript gefunden"
    return treffer.group(0)


def _probe(tmp_path: Path, letzter_run: str, waiting_min: str) -> str:
    """`_deploy_probe` mit gh-Stub ausfuehren.

    `letzter_run` = Ausgabe der ersten Abfrage (conclusion|id), `waiting_min` =
    Ausgabe der `--status waiting`-Abfrage.
    """
    stub = tmp_path / "gh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'case " $* " in\n'
        f"  *' --status waiting '*) printf '%s\\n' '{waiting_min}' ;;\n"
        f"  *' run list '*) printf '%s\\n' '{letzter_run}' ;;\n"
        "  *) echo 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    ergebnis = subprocess.run(
        ["bash", "-c", f"{_funktion()}\n_deploy_probe iilgmbh risk-hub"],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
    return ergebnis.stdout.strip()


def test_should_keep_fields_aligned_when_latest_run_is_waiting(tmp_path: Path):
    ausgabe = _probe(tmp_path, "|36549529631", "2026-09-29T09:29:42Z")
    assert ausgabe == "none 36549529631 2026-09-29T09:29:42Z 0"


def test_should_report_conclusion_and_id_of_finished_run(tmp_path: Path):
    ausgabe = _probe(tmp_path, "success|35977677121", "none")
    assert ausgabe == "success 35977677121 none 0"


def test_should_report_none_when_repo_has_no_deploy_run(tmp_path: Path):
    ausgabe = _probe(tmp_path, "|", "none")
    assert ausgabe == "none none none 0"
