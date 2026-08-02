"""Aufrufpfad-Contract-Drill (Retro 287b23 Befund #1, KONZ-038 K4).

Der Realfall: Drills luden Hooks per importlib (Interpreter-Pfad), settings.json
ruft die Datei DIREKT auf — 2/5 Welle-1-Gates lagen mit Mode 100644 im Index und
waren real nicht ausführbar (Fix: fremder PR #1660). Dieser Test drillt ab jetzt
GENAU den echten Aufrufpfad für JEDES registrierte Gate-Modul: Executable-Bit im
Checkout + Direktaufruf via Shebang (Stop-Hooks zusätzlich mit leerem Event).
Ein neues Gate, das hier durchfällt, ist nach K4 nicht gebaut — egal was seine
importlib-Drills sagen.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / "docs" / "governance" / "gate-registry.json"

_gates = json.loads(REGISTRY.read_text(encoding="utf-8"))["gates"]
_modules = sorted(
    {g["module"] for g in _gates if g.get("module", "").startswith("tools/")}
)


@pytest.mark.parametrize("module", _modules)
def test_should_registrierte_module_executable_im_checkout_sein(module: str) -> None:
    full = REPO / module
    assert full.is_file(), f"Registry-Modul fehlt: {module}"
    assert os.access(full, os.X_OK), (
        f"{module} ist nicht executable (Index-Mode 100644?) — settings.json ruft "
        "die Datei DIREKT auf; git update-chmod vor Commit (Retro 287b23 #1)."
    )
    first = full.read_bytes()[:2]
    assert first == b"#!", (
        f"{module} hat keine Shebang-Zeile — Direktaufruf schlägt fehl"
    )


@pytest.mark.parametrize(
    "module",
    [m for m in _modules if m.endswith("_scanner.py")],
)
def test_should_stop_hooks_ueber_direktaufruf_laufen(module: str) -> None:
    """Exakt der settings.json-Pfad: Datei direkt, Event auf stdin, Exit 0."""
    r = subprocess.run(
        [str(REPO / module)],
        input="{}",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, (
        f"Direktaufruf {module} scheiterte (rc={r.returncode}): {r.stderr[:200]}"
    )
