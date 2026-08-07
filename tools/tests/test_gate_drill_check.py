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


# ── Kopf-Konsistenz (KONZ-038 D8) ────────────────────────────────────────────


def _reg_mit(tmp_path, gate: dict) -> Path:
    """Registry mit EINEM Gate.

    Der Drill zeigt auf eine WEGWERF-Testdatei, nicht auf diese hier: sonst
    startet gate_drill_check.py pytest auf test_gate_drill_check.py, das erneut
    gate_drill_check.py startet — eine Endlosrekursion, die beim ersten Versuch
    genau so passiert ist (Lauf nach 6 Minuten abgebrochen).
    """
    trivial = tmp_path / "test_trivial_drill.py"
    trivial.write_text("def test_should_pass():\n    assert True\n", encoding="utf-8")
    reg = tmp_path / "reg.json"
    gate = {"drill": str(trivial), **gate}
    reg.write_text(json.dumps({"gates": [gate]}), encoding="utf-8")
    return reg


def test_should_fehlenden_gate_header_melden(tmp_path):
    """Ein Modul ohne GATE_HEADER ist der Fall, der bis 2026-08-06 unbemerkt blieb."""
    modul = tmp_path / "ohne_kopf.py"
    modul.write_text("print('ich bin ein Gate ohne Selbstauskunft')\n", encoding="utf-8")
    r = _run(_reg_mit(tmp_path, {"slug": "x", "mode": "advisory", "module": str(modul)}))
    assert r.returncode == 0
    assert "kein GATE_HEADER im Modul" in r.stdout, r.stdout


def test_should_unvollstaendigen_gate_header_feldweise_melden(tmp_path):
    modul = tmp_path / "halber_kopf.py"
    modul.write_text(
        'GATE_HEADER = {"slug": "x", "mode": "advisory"}\n', encoding="utf-8"
    )
    r = _run(_reg_mit(tmp_path, {"slug": "x", "mode": "advisory", "module": str(modul)}))
    assert "GATE_HEADER ohne `owner`" in r.stdout, r.stdout
    assert "GATE_HEADER ohne `last_drill_pass`" in r.stdout, r.stdout


def test_should_slug_drift_zwischen_kopf_und_registry_melden(tmp_path):
    """Laufen Kopf und Registry auseinander, zeigt der Report auf ein anderes Gate."""
    modul = tmp_path / "falscher_slug.py"
    modul.write_text(
        'GATE_HEADER = {"slug": "anderer", "mode": "advisory", "owner": "a", '
        '"last_drill_pass": "2026-01-01"}\n',
        encoding="utf-8",
    )
    r = _run(
        _reg_mit(tmp_path, {"slug": "erwartet", "mode": "advisory", "module": str(modul)})
    )
    assert "Slug im Kopf != Registry-Slug `erwartet`" in r.stdout, r.stdout


def test_should_meta_gate_ohne_modul_nicht_als_befund_melden(tmp_path):
    """`meta`-Gates drillen quer ueber alle Module und haben bewusst keins."""
    r = _run(_reg_mit(tmp_path, {"slug": "quer", "mode": "meta", "module": ""}))
    assert "Kopf nicht pruefbar" not in r.stdout, r.stdout
    assert "alle Gates tragen einen vollstaendigen Kopf" in r.stdout, r.stdout


def test_should_modullosem_nicht_meta_gate_widersprechen(tmp_path):
    """Gegenprobe: ausserhalb von `meta` bleibt ein fehlendes Modul ein Befund."""
    r = _run(_reg_mit(tmp_path, {"slug": "quer", "mode": "advisory", "module": ""}))
    assert "kein `module` in der Registry" in r.stdout, r.stdout
