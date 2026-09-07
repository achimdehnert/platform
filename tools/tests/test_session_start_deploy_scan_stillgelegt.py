"""Tests fuer die betriebsstatus-Filterung in Phase 0.7 (deploy-scan).

Wie bei `test_session_start_prod_wirkung.py`: das eigentliche Python-Schnipsel
lebt in einer Shell-Heredoc INNERHALB von `session_start_checks.sh`. `bash -n`
wuerde es durchwinken, selbst wenn das Python darin nicht laeuft oder die
falschen betriebsstatus-Werte durchlaesst. Getestet wird deshalb der
**ausgelieferte** Text, nicht eine Kopie im Test.

Anlass (platform, 2026-09-07): coach-hub ist seit 2026-08-30 `stillgelegt`
(Owner-Entscheid, Container gestoppt), sein letzter Deploy-Run bleibt
`failure` — der Scan meldete das trotzdem als Ausfall. `blockiert` gehoert
NICHT zu den Werten, die hier still gestellt werden: das soll noch laufen
und wartet nur auf eine Entscheidung (infra/ports.yaml §Lebenszyklus).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_SKRIPT = Path(__file__).resolve().parents[1] / "session_start_checks.sh"
_TOOLS_DIR = Path(__file__).resolve().parents[1]
_START_MARKER = 'DEPLOY_STILLGELEGT_REPOS=$(cd "$PLATFORM_DIR" && python3 -c "\n'
_END_MARKER = '\n" 2>/dev/null || true)'


def _schnipsel() -> str:
    """Das betriebsstatus-Filter-Python aus dem Shell-Skript schneiden."""
    text = _SKRIPT.read_text(encoding="utf-8")
    start = text.index(_START_MARKER) + len(_START_MARKER)
    end = text.index(_END_MARKER, start)
    return text[start:end]


def _stillgelegte_repos(tmp_path: Path, ports_yaml: str) -> list[str]:
    """Fuehrt das ausgelieferte Schnipsel gegen ein Test-`ports.yaml` aus.

    `tools/` wird verlinkt statt kopiert, damit `waisen_melder.py` +
    `betriebsstatus.py` das echte, ausgelieferte Vokabular bleiben — nur
    `infra/ports.yaml` ist hier die Test-Fixture.
    """
    (tmp_path / "tools").symlink_to(_TOOLS_DIR)
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "ports.yaml").write_text(ports_yaml, encoding="utf-8")

    ergebnis = subprocess.run(
        [sys.executable, "-c", _schnipsel()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert not ergebnis.stderr.strip(), ergebnis.stderr
    return ergebnis.stdout.strip().split()


def test_should_treat_stillgelegt_repo_as_kein_befund(tmp_path: Path):
    ports_yaml = """
services:
  coach-hub:
    domain_prod: coach-hub.iil.pet
    repo: achimdehnert/coach-hub
    betriebsstatus: stillgelegt
    betriebsstatus_grund: "Owner-Entscheid"
"""
    assert _stillgelegte_repos(tmp_path, ports_yaml) == ["coach-hub"]


def test_should_treat_ruhend_repo_as_kein_befund(tmp_path: Path):
    ports_yaml = """
services:
  odoo:
    domain_prod: odoo.iil.pet
    repo: achimdehnert/odoo-hub
    betriebsstatus: ruhend
    betriebsstatus_grund: "Owner-Entscheid"
"""
    assert _stillgelegte_repos(tmp_path, ports_yaml) == ["odoo-hub"]


def test_should_leave_a_normal_active_repo_as_befund(tmp_path: Path):
    """Positivkontrolle: ein ganz normales, aktives Repo bleibt ein Befund."""
    ports_yaml = """
services:
  bahn-hub:
    domain_prod: bahn.iil.pet
    repo: achimdehnert/bahn-hub
"""
    assert _stillgelegte_repos(tmp_path, ports_yaml) == []


def test_should_not_silence_a_blockiert_repo(tmp_path: Path):
    """`blockiert` heisst 'soll noch laufen' — kein kein-Befund-Fall."""
    ports_yaml = """
services:
  frist-hub:
    domain_prod: frist-hub.iil.pet
    repo: achimdehnert/frist-hub
    betriebsstatus: blockiert
    betriebsstatus_grund: "Owner-Entscheid"
"""
    assert _stillgelegte_repos(tmp_path, ports_yaml) == []
