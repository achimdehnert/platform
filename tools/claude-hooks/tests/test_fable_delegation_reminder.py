"""Drill für fable_delegation_reminder.sh (#2750 K3).

Fable-Modell meldet die Delegationsregel, jedes andere Modell schweigt,
fehlende Settings/Policy/Marker sind fail-open. Vertrag: IMMER Exit 0.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fable_delegation_reminder.sh"

POLICY_BODY = """# Policy: Claude Code Session Routing

## Aufgabenklasse -> Tier (maschinenlesbar, #2750 K2)

Gilt in jeder Fable-Session ohne Zuruf: vor jeder Aufgabe ab Klasse "Umsetzung"
einen ausfuehrungsreifen Brief schreiben und mit explizitem model: delegieren.

<!-- routing-table:start -->
| Klasse | Kennzeichen | Beispiel | Tier | model |
|---|---|---|---|---|
| Trivial | klein | Tippfehler | inline | - |
| Mechanisch | Suchen | grep | T2 | haiku |
| Umsetzung | abgegrenzt | Hook + Tests | T3 | sonnet |
| Schwer | mehrere Module | Refactor | T4 | opus |
| Urteil | Synthese | ADR-Entwurf | T5 | inline |
<!-- routing-table:end -->
"""


def _run(tmp_path: Path, model: str | None, policy_body: str | None = POLICY_BODY):
    settings = tmp_path / "settings.json"
    if model is not None:
        settings.write_text(json.dumps({"model": model}), encoding="utf-8")
    policy = tmp_path / "policy.md"
    if policy_body is not None:
        policy.write_text(policy_body, encoding="utf-8")
    r = subprocess.run(
        ["bash", str(SCRIPT)],
        env={
            "CLAUDE_SETTINGS": str(settings),
            "POLICY_FILE": str(policy),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return r


def test_should_fable_mit_suffix_delegationsregel_melden(tmp_path):
    r = _run(tmp_path, "claude-fable-5-1[1m]")
    assert r.returncode == 0
    assert "Fable-Session — Delegationsregel (#2750 K3)" in r.stdout
    assert "| Umsetzung |" in r.stdout


def test_should_fable_ohne_suffix_delegationsregel_melden(tmp_path):
    r = _run(tmp_path, "claude-fable-5")
    assert r.returncode == 0
    assert "Fable-Session — Delegationsregel (#2750 K3)" in r.stdout
    assert "| Umsetzung |" in r.stdout


def test_should_bei_anderem_modell_schweigen(tmp_path):
    r = _run(tmp_path, "claude-sonnet-5")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_should_policy_ohne_marker_schweigen(tmp_path):
    r = _run(
        tmp_path,
        "claude-fable-5",
        policy_body="# Policy ohne Marker\n\nkein Inhalt hier.\n",
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_should_ohne_settings_fail_open(tmp_path):
    r = _run(tmp_path, None)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_should_marker_strings_nie_ausgeben(tmp_path):
    r = _run(tmp_path, "claude-fable-5")
    assert "routing-table:start" not in r.stdout
    assert "routing-table:end" not in r.stdout
