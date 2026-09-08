"""Tests fuer tools/sharedci/pin_landschaft.py (platform#2944 Anschluss).

`gh` wird durch eine Attrappe ersetzt — kein Netz, kein `gh`-Login noetig.
Gegenprobe (wie beim Alarmweg-Melder): der simulierte Workflow-Inhalt traegt
einen echten Geheimnis-Marker; er darf in der Ergebnisdatei nicht auftauchen.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "sharedci"))
import melder_ergebnis as me  # noqa: E402
import pin_landschaft as pl  # noqa: E402

# Enthaelt einen "Webhook" mit Geheimnis-Marker — die Gegenprobe unten prueft,
# dass er trotz vollstaendigem Datei-Inhalt in der Attrappe NICHT durchsickert.
WORKFLOW_INHALT = (
    "jobs:\n"
    "  lint:\n"
    "    uses: iilgmbh/shared-ci/.github/workflows/lint.yml@v1.1.10\n"
    "    secrets:\n"
    "      DISCORD_WEBHOOK: https://discord.com/api/webhooks/geheim123\n"
)


def _fake_gh(monkeypatch):
    def gh(*a):
        if a[0] == "api" and a[1] == "repos/test/repo/contents/.github/workflows":
            return "lint.yml\n"
        if (
            a[0] == "api"
            and a[1] == "repos/test/repo/contents/.github/workflows/lint.yml"
        ):
            return base64.b64encode(WORKFLOW_INHALT.encode()).decode()
        return ""

    monkeypatch.setattr(pl, "gh", gh)
    monkeypatch.setattr(pl, "REPOS", ["test/repo"])


def test_should_behave_exactly_as_before_without_ergebnis_datei(monkeypatch, capsys):
    """Ohne --ergebnis-datei: gleiche Ausgabe (Report), gleicher Exit-Code (0)."""
    _fake_gh(monkeypatch)
    code = pl.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "=== lint.yml" in out
    assert "v1.1.10" in out
    assert "repo:lint.yml" in out


def test_should_write_machine_readable_result_per_repo(monkeypatch, tmp_path):
    _fake_gh(monkeypatch)
    ziel = tmp_path / "ergebnis.json"
    code = pl.main(["--ergebnis-datei", str(ziel)])
    assert code == 0

    daten = me.lies(ziel)
    assert daten is not None
    assert daten["melder"] == "pin_landschaft"
    assert [e["repo"] for e in daten["ergebnis"]] == ["test/repo"]
    pins = daten["ergebnis"][0]["pins"]
    assert pins == [{"workflow": "lint.yml", "version": "v1.1.10", "datei": "lint.yml"}]


def test_should_not_leak_workflow_file_content_into_the_result(monkeypatch, tmp_path):
    """Gegenprobe: der Webhook-Geheimnis-Marker steht im simulierten Dateiinhalt
    (oben), darf aber nicht in der Ergebnisdatei landen — nur Repo/Datei/Version."""
    _fake_gh(monkeypatch)
    ziel = tmp_path / "ergebnis.json"
    pl.main(["--ergebnis-datei", str(ziel)])

    roh = ziel.read_text(encoding="utf-8")
    assert "geheim123" not in roh
    assert "DISCORD_WEBHOOK" not in roh
    assert "discord.com" not in roh
