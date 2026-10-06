"""`flottenbild._lauf` darf an einem einzelnen Nicht-UTF-8-Byte nicht sterben.

Realfall 2026-09-23 06:13 (flottenbild.service, rc=1): die gpu-box antwortet
ueber Windows-OpenSSH aus cmd.exe in Latin-1 („ü" = 0xfc). `subprocess.run(...,
text=True)` decodierte strikt, warf UnicodeDecodeError — und der ganze Tageslauf
brach ab, obwohl nur ein Knoten unlesbar war. Die Folge im Sitzungsstart:
0.7.22 fand kein Flottenbild (SKIP), weil flottenbild-daily.sh die latest.*-
Symlinks auf nie geschriebene Dateien umgehaengt hatte.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flottenbild as fb  # noqa: E402


def test_should_survive_latin1_byte_in_remote_output() -> None:
    rc, out = fb._lauf(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'Gr\\xfcn\\n')"]
    )

    assert rc == 0
    assert out.startswith("Gr")
    assert "n" in out  # der Rest der Zeile ueberlebt, nur das eine Byte ist ersetzt


def test_should_keep_utf8_intact() -> None:
    rc, out = fb._lauf([sys.executable, "-c", "print('Grün')"])

    assert rc == 0
    assert out.strip() == "Grün"
