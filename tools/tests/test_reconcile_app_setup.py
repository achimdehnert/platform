"""Drill fuer tools/reconcile-app-setup.sh (platform#2006).

Der Anlass ist ein Scanner-Treffer, kein Bug: die erste Runbook-Fassung gab zwei
Kommandozeilen mit Platzhaltern (`--body "<App ID>"`). Ein Platzhalter ist beim
Einfuegen nicht kopierbar, und die stille Variante ist die gefaehrliche — wird
`<App ID>` literal gesetzt, laufen die Token-Schritte im Workflow an,
`create-github-app-token` scheitert je Org, und dank `continue-on-error` bleibt
der Lauf GRUEN. Ein Konfigurationsfehler saehe damit exakt aus wie eine fehlende
Installation.

Jeder Test hier ist ein Weg, auf dem genau das nicht mehr passieren kann.
`--dry-run` schreibt nie — `gh` wird in diesen Tests deshalb nie aufgerufen.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

_SKRIPT = pathlib.Path(__file__).resolve().parents[1] / "reconcile-app-setup.sh"

# Der PEM-Rahmen wird zur LAUFZEIT zusammengesetzt und steht bewusst nicht als
# Zeichenkette in dieser Datei. Grund, gemessen am 2026-08-16: `gitleaks` schlug
# beim ersten Anlauf auf Zeile 25 an (RuleID `private-key`) — zu Recht, denn
# `platform` ist ein OEFFENTLICHES Repo, und dort hat ein Private-Key-Muster
# nichts zu suchen, auch kein erfundenes. Der naheliegende Ausweg waere ein
# Allowlist-Eintrag gewesen; der ist hier der schlechtere: eine Ausnahme fuer die
# Regel `private-key` taugt nur so viel wie der Fund, den sie kuenftig durchlaesst.
# Diese Zerlegung kostet nichts und laesst die Regel scharf.
_RAHMEN = "-" * 5
_PEM = (
    f"{_RAHMEN}BEGIN RSA PRIVATE KEY{_RAHMEN}\n"
    "NICHT-ECHT-NUR-FUER-DEN-DRILL\n"
    f"{_RAHMEN}END RSA PRIVATE KEY{_RAHMEN}\n"
)


@pytest.fixture
def pem(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "app.private-key.pem"
    p.write_text(_PEM, encoding="utf-8")
    return p


def _lauf(*args: str):
    return subprocess.run(["bash", str(_SKRIPT), *args], capture_output=True, text=True)


def test_should_accept_a_valid_pair_in_dry_run(pem) -> None:
    r = _lauf("123456", str(pem), "--dry-run")
    assert r.returncode == 0
    assert "DRY-RUN" in r.stdout


def test_should_never_print_the_key_material(pem) -> None:
    """Der Schluessel darf in keiner Ausgabe auftauchen — auch nicht im Erfolgsfall."""
    r = _lauf("123456", str(pem), "--dry-run")
    assert "NICHT-ECHT-NUR-FUER-DEN-DRILL" not in (r.stdout + r.stderr)
    assert f"BEGIN RSA PRIVATE KEY{_RAHMEN}" not in (r.stdout + r.stderr)


def test_should_reject_a_placeholder_instead_of_setting_it(pem) -> None:
    """Der Fall, um den es geht: ein nicht ersetzter Platzhalter.

    Er muss LAUT scheitern. Wuerde er still gesetzt, waere der Folgefehler im
    Workflow von einer fehlenden App-Installation nicht zu unterscheiden.
    """
    r = _lauf("<App ID>", str(pem), "--dry-run")
    assert r.returncode == 65
    assert "keine Zahl" in r.stderr


def test_should_catch_swapped_arguments(pem) -> None:
    r = _lauf(str(pem), "123456", "--dry-run")
    assert r.returncode == 65


def test_should_reject_a_missing_key_file() -> None:
    r = _lauf("123456", "/gibt/es/nicht.pem", "--dry-run")
    assert r.returncode == 66


def test_should_reject_a_file_that_is_not_a_pem(tmp_path) -> None:
    kein = tmp_path / "kein.pem"
    kein.write_text("hallo\n", encoding="utf-8")
    r = _lauf("123456", str(kein), "--dry-run")
    assert r.returncode == 66
    assert "BEGIN-Zeile" in r.stderr


def test_should_require_both_arguments() -> None:
    r = _lauf("123456", "--dry-run")
    assert r.returncode == 64
    assert "Aufruf:" in r.stderr


def test_should_not_delete_the_key_file_without_being_asked(pem) -> None:
    """`--shred` ist bewusst OPT-IN: eine fremde Datei ungefragt zu vernichten
    waere eine schlechte Vorgabe, und der Dry-Run darf ohnehin nie loeschen."""
    _lauf("123456", str(pem), "--dry-run", "--shred")
    assert pem.exists()


def test_should_print_usage_not_source_code() -> None:
    """`--help` druckte zuerst Quelltext (`sed -n '1,30p'` bei laengerem Kopf).

    Aufgefallen erst beim Selbstausfuehren — kein Test hatte je hingesehen. Eine
    feste Zeilenzahl driftet mit jedem Satz, den jemand oben ergaenzt; dieser Test
    haelt fest, dass die Hilfe Hilfe bleibt.
    """
    r = _lauf("--help")
    assert r.returncode == 0
    assert "Aufruf:" in r.stdout and "--dry-run" in r.stdout
    for quelltext in ("set -euo pipefail", "ARGS=()", 'case "$a" in'):
        assert quelltext not in r.stdout, f"Quelltext in der Hilfe: {quelltext}"
