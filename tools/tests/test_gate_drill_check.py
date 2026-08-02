"""Drill des Drill-Prüfers selbst (KONZ-038 D8): grüne Registry meldet frisch,
rote/fehlende Drills werden K4-zurückgestuft, kaputte Registry ist laut."""

import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "gate_drill_check.py"


def _run(registry_path):
    return subprocess.run(
        [sys.executable, str(TOOL), "--registry", str(registry_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_should_echte_registry_komplett_gruen_drillen():
    r = _run(Path(TOOL).parents[1] / "docs" / "governance" / "gate-registry.json")
    assert r.returncode == 0, r.stderr
    assert "K4: NICHT GEBAUT" not in r.stdout, r.stdout
    assert "alle registrierten Gates Drill-frisch" in r.stdout


def test_should_fehlenden_drill_k4_zurueckstufen(tmp_path):
    reg = tmp_path / "reg.json"
    reg.write_text(
        json.dumps(
            {
                "gates": [
                    {"slug": "tot", "mode": "advisory", "drill": "gibt/es/nicht.py"}
                ]
            }
        ),
        encoding="utf-8",
    )
    r = _run(reg)
    assert r.returncode == 0
    assert "K4: NICHT GEBAUT" in r.stdout and "Drill-Datei fehlt" in r.stdout


def test_should_kaputte_registry_laut_melden(tmp_path):
    reg = tmp_path / "kaputt.json"
    reg.write_text("{nicht json", encoding="utf-8")
    r = _run(reg)
    assert r.returncode == 0
    assert "NICHT bewertbar" in r.stdout
