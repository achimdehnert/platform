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
    assert "MODELLWECHSEL erkannt: claude-opus-5 → claude-fable-5" in r.stdout
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
