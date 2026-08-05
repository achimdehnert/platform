"""Fuehrt die Bash-Selbsttests von block_unformatted_push.sh unter pytest aus.

Ohne diesen Wrapper laege die Suite zwar im Repo, wuerde aber nie laufen:
`tools/claude-hooks/tests/` wird per pytest eingesammelt, und pytest findet
keine `.sh`-Dateien. Ein Gate, dessen Test nicht ausgefuehrt wird, ist kein Gate.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SUITE = Path(__file__).parent / "test_block_unformatted_push.sh"


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff nicht installiert")
@pytest.mark.skipif(shutil.which("git") is None, reason="git nicht installiert")
def test_should_pass_all_bash_selftests_of_the_push_gate():
    """Alle Faelle der Bash-Suite muessen gruen sein (exit 0 = 0 Fehler).

    Enthaelt T10 als Regression zu platform#1754: ein Branch mit aufloesbarem
    origin/<default> und null geaenderten .py darf NICHT blockiert werden, auch
    wenn HEAD~1 unformatierte .py enthaelt.
    """
    res = subprocess.run(
        ["bash", str(SUITE)], capture_output=True, text=True, timeout=300
    )
    assert res.returncode == 0, (
        f"Bash-Suite meldet {res.returncode} rote Faelle:\n{res.stdout}\n{res.stderr}"
    )
    assert "ALLE TESTS GRÜN" in res.stdout, res.stdout
