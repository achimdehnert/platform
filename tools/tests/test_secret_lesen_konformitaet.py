"""Konformitaets-Tests fuer tolerante Secret-Leser gegen die zentrale Fixture.

Die Fixture ``tools/tests/fixtures/secret_lesen_konformitaet.json`` ist aus
``infra/lib/secrets.py::secret_wert`` gemessen (#3141) und beschreibt die 12
Faelle, die JEDE tolerante Secret-Leser-Implementierung bestehen muss — bare,
NAME=WERT, base64-Auffuellung, Anfuehrung, mehrere Variablen. Kopien in
anderen Repos vendoren diese Datei unveraendert; wer die Faelle aendert,
aendert sie hier UND aktualisiert die Quelle (Refs #3155).

Zwei Implementierungen laufen hier gegen dieselbe Fixture:

(a) ``infra.lib.secrets.secret_wert`` (Python, der kanonische Leser)
(b) ``tools/secret_lesen.sh`` (Shell, ruft (a) intern auf) — Positivkontrolle,
    dass Shell- und Python-Seite nicht auseinanderlaufen.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL))

from infra.lib.secrets import secret_wert  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "secret_lesen_konformitaet.json"
LESER_SH = WURZEL / "tools" / "secret_lesen.sh"

FAELLE: list[dict] = json.loads(FIXTURE.read_text(encoding="utf-8"))["faelle"]


def _fall_id(fall: dict) -> str:
    return fall["fall"]


@pytest.mark.parametrize("fall", FAELLE, ids=_fall_id)
def test_should_match_secret_wert_for_konformitaet_fall(
    tmp_path: Path, fall: dict
) -> None:
    pfad = tmp_path / "secret"
    pfad.write_text(fall["inhalt"], encoding="utf-8")

    if fall["fehler"]:
        with pytest.raises(ValueError):
            secret_wert(pfad, name=fall["name"])
    else:
        assert secret_wert(pfad, name=fall["name"]) == fall["erwartet"]


@pytest.mark.parametrize("fall", FAELLE, ids=_fall_id)
def test_should_match_secret_lesen_sh_for_konformitaet_fall(
    tmp_path: Path, fall: dict
) -> None:
    pfad = tmp_path / "secret"
    pfad.write_text(fall["inhalt"], encoding="utf-8")

    argv = [str(LESER_SH), str(pfad)]
    if fall["name"]:
        argv.append(fall["name"])
    ergebnis = subprocess.run(argv, capture_output=True, text=True, check=False)

    if fall["fehler"]:
        assert ergebnis.returncode != 0
        assert ergebnis.stdout == ""
    else:
        assert ergebnis.returncode == 0
        assert ergebnis.stdout.rstrip("\n") == fall["erwartet"]
