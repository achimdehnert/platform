"""Deckblatt-Metazeilen des Print-Agents — Rollenzuweisung im iil-Template.

Hintergrund: ``_build_meta_rows`` haengte die Zeile „Auftragnehmer: IIL GmbH …"
bedingungslos an jedes iil-Dokument. Bei einem Dokument, in dem IIL selbst der
Auftraggeber ist (Pruefbogen an eigene Auftragsverarbeiter), stand damit die
falsche Rolle auf dem Deckblatt eines Datenschutz-Formulars.

CI-Hinweis: ``tools-tests.yml`` installiert nur pytest/pyyaml/pydantic. Der
Import von ``print_agent`` zieht weasyprint/litellm/markdown und wuerde die
Sammlung dort sprengen — deshalb ``importorskip``. Dieser Test laeuft lokal
(``make test``) echt, in der aktuellen CI-Umgebung wird er uebersprungen.
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("weasyprint")
pytest.importorskip("litellm")
pytest.importorskip("markdown")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "print_agent"))
import print_agent  # noqa: E402

IIL_DESIGN = {"meta_template": "iil"}


def _labels(meta):
    return [label for label, _ in print_agent._build_meta_rows(meta, IIL_DESIGN, "doc")]


def test_should_omit_auftragnehmer_row_without_angebots_context():
    """Ein iil-Dokument ohne Angebots-Merkmale bekommt keine Rollenzuweisung."""
    assert "Auftragnehmer" not in _labels({"status": "Entwurf"})


def test_should_keep_auftragnehmer_row_for_angebot():
    """Gegenprobe: mit Angebots-Nummer bleibt die Zeile erhalten."""
    labels = _labels({"angebot_nr": "2026-014"})
    assert "Auftragnehmer" in labels
    assert "Angebot-Nr." in labels


def test_should_keep_auftragnehmer_row_when_auftraggeber_named():
    """Ist ein Auftraggeber genannt, ist die Gegenrolle gewollt."""
    labels = _labels({"auftraggeber": "Beispiel GmbH"})
    assert labels == ["Auftraggeber", "Auftragnehmer"]


def test_should_keep_auftragnehmer_row_for_gueltig_bis():
    """Auch ein Gueltigkeitsdatum ist ein Angebots-Merkmal."""
    assert "Auftragnehmer" in _labels({"gueltig_bis": "31.12.2026"})
