"""Drill für model_change_detector.sh (KONZ-038 D7/K4).

Erst-Seed still, Wechsel meldet, gleichbleibend still, kaputte settings fail-open.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "model_change_detector.sh"


def _run(tmp_path: Path, model: str | None, seed: str | None = None):
    settings = tmp_path / "settings.json"
    if model is not None:
        settings.write_text(json.dumps({"model": model}), encoding="utf-8")
    state_dir = tmp_path / "state"
    if seed is not None:
        state_dir.mkdir(exist_ok=True)
        (state_dir / "model-id").write_text(seed, encoding="utf-8")
    r = subprocess.run(
        ["bash", str(SCRIPT)],
        env={
            "CLAUDE_SETTINGS": str(settings),
            "MODEL_STATE_DIR": str(state_dir),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    return r, (state_dir / "model-id")


def test_should_erst_seed_still_anlegen(tmp_path):
    r, state = _run(tmp_path, "claude-fable-5")
    assert r.returncode == 0
    assert r.stdout.strip() == ""
    assert state.read_text(encoding="utf-8") == "claude-fable-5"


def test_should_wechsel_melden_und_state_nachziehen(tmp_path):
    r, state = _run(tmp_path, "claude-fable-5", seed="claude-opus-5")
    assert r.returncode == 0
    assert "MODELLWECHSEL erkannt (MAJOR): claude-opus-5 → claude-fable-5" in r.stdout
    assert "Re-Qualifikation" in r.stdout
    assert "Smoke-Kalibrierung" in r.stdout
    assert state.read_text(encoding="utf-8") == "claude-fable-5"


def test_should_bei_gleichem_modell_schweigen(tmp_path):
    r, _ = _run(tmp_path, "claude-fable-5", seed="claude-fable-5")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_should_ohne_settings_fail_open(tmp_path):
    r, _ = _run(tmp_path, None)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_should_hauptversion_als_major_einstufen_und_loggen(tmp_path):
    r, state = _run(tmp_path, "claude-fable-6", seed="claude-fable-5-1[1m]")
    assert "MODELLWECHSEL erkannt (MAJOR)" in r.stdout
    log = (
        (state.parent / "model-changes.log")
        .read_text(encoding="utf-8")
        .strip()
        .split("\t")
    )
    assert log[1:] == ["claude-fable-5-1[1m]", "claude-fable-6", "MAJOR"]


def test_should_punkt_release_als_minor_einstufen(tmp_path):
    r, state = _run(tmp_path, "claude-fable-5-1", seed="claude-fable-5")
    assert "MODELLWECHSEL erkannt (MINOR)" in r.stdout
    assert "Vollmachten bleiben active" in r.stdout
    assert "MAJOR" not in r.stdout
    assert (
        (state.parent / "model-changes.log")
        .read_text(encoding="utf-8")
        .rstrip()
        .endswith("MINOR")
    )


def test_should_suffix_wechsel_still_aber_geloggt(tmp_path):
    r, state = _run(tmp_path, "claude-fable-5-1[1m]", seed="claude-fable-5-1")
    assert r.returncode == 0
    assert r.stdout.strip() == ""
    assert state.read_text(encoding="utf-8") == "claude-fable-5-1[1m]"
    assert (
        (state.parent / "model-changes.log")
        .read_text(encoding="utf-8")
        .rstrip()
        .endswith("SUFFIX")
    )


# --- Datums-Snapshot als eigene Dimension (Retro c36878, #2655) --------------
# Diese vier Faelle waren vor dem Fix rot bzw. nicht abgedeckt: die alte Regex
# schnitt nach der ersten Ziffernfolge ab, jede Datums-ID landete bei MINOR.


def test_should_datums_snapshot_als_major_werten(tmp_path):
    """Zwei Snapshots = zwei Gewichtsmatrizen (Charta Art. 2.5), auch bei
    identischer Versionsnummer."""
    r, state = _run(
        tmp_path, "claude-haiku-4-5-20260315", seed="claude-haiku-4-5-20251001"
    )
    assert "MODELLWECHSEL erkannt (MAJOR)" in r.stdout
    assert (
        (state.parent / "model-changes.log")
        .read_text(encoding="utf-8")
        .rstrip()
        .endswith("MAJOR")
    )


def test_should_zweite_versionsstelle_mit_datum_als_major_werten(tmp_path):
    """Der Originalbefund: haiku-4-5-<datum> -> haiku-4-9-<datum> ergab beidseitig
    `haiku-4` und wurde als MINOR eingestuft."""
    r, _ = _run(tmp_path, "claude-haiku-4-9-20260315", seed="claude-haiku-4-5-20251001")
    assert "MODELLWECHSEL erkannt (MAJOR)" in r.stdout
    assert "MINOR" not in r.stdout


def test_should_punkt_release_ohne_datum_weiter_als_minor_werten(tmp_path):
    """Gegenprobe: die ratifizierte MINOR-Definition aus Runbook §0 bleibt gueltig
    — sonst waere der Fix ein verkappter Klippen-Reset."""
    r, _ = _run(tmp_path, "claude-fable-5-1", seed="claude-fable-5")
    assert "MODELLWECHSEL erkannt (MINOR)" in r.stdout
    assert "Vollmachten bleiben active" in r.stdout


def test_should_unbekannte_form_weiter_als_major_werten(tmp_path):
    """Gegenprobe fail-loud: ein Provider-Praefix parst nicht und muss MAJOR
    bleiben, nicht durch die neue Datums-Dimension weicher werden."""
    r, _ = _run(tmp_path, "us.anthropic.claude-fable-5-1", seed="claude-fable-5-1")
    assert "MODELLWECHSEL erkannt (MAJOR)" in r.stdout
