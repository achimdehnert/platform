"""Tests für tools/handover_fleet_check.py (Flotten-Messung, platform#1945 Kriterium 1).

Getestet wird die reine Logik ohne Netz: Auswahl der aktiven Repos, Datums-Erkennung im
Stand-Block, Owner-Auflösung über `full_name` (Redirect-Falle), Erkennung der Gate-
Verdrahtung und die deterministische Ausgabe. Die HTTP-Schicht (`gh_api`) wird gemockt —
ein Test gegen die echte API wäre weder deterministisch noch offline lauffähig.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import handover_fleet_check as hfc  # noqa: E402


# ── aktive Repos ──────────────────────────────────────────────────────────────


def test_should_skip_archived_frozen_and_decommissioned_repos():
    canon = {
        "decommissioned": [{"name": "bfagent"}],
        "repos": {
            "risk-hub": {"lifecycle": "production"},
            "research-hub": {"lifecycle": "frozen"},
            "wedding-hub": {"lifecycle": "archived"},
            "bfagent": {"lifecycle": "production"},  # trotzdem raus: stillgelegt
            "promptfw": {},  # kein lifecycle = aktiv
        },
    }
    assert hfc.active_repos(canon) == ["promptfw", "risk-hub"]


def test_should_read_lifecycle_from_rich_block_when_toplevel_missing():
    """bfagent trägt lifecycle historisch nur unter `rich` — dieselbe Fallback-Regel
    wie in registry_api._lifecycle, sonst zählt ein archiviertes Repo als aktiv."""
    canon = {"repos": {"altlast": {"rich": {"lifecycle": "archived"}}}}
    assert hfc.active_repos(canon) == []


# ── Datum des Stand-Blocks ────────────────────────────────────────────────────


def test_should_find_newest_dated_heading():
    text = "# Titel\n\n## ⚡ Aktueller Stand (2026-08-11 — irgendwas)\n\n## ⚡ Vorheriger Stand (2026-08-10)\n"
    assert hfc.heading_date_from_text(text) == date(2026, 8, 11)


def test_should_accept_the_other_dialect():
    """Zweiter etablierter Dialekt der Flotte — die Messung darf nicht auf einen festlegen."""
    assert hfc.heading_date_from_text("## Current state (observed 2026-07-07)\n") == date(
        2026, 7, 7
    )


def test_should_ignore_dates_outside_the_head_window():
    text = "\n" * (hfc.HEAD_LINES + 1) + "## Aktueller Stand (2026-08-11)\n"
    assert hfc.heading_date_from_text(text) is None


def test_should_ignore_date_that_is_not_in_a_heading():
    assert hfc.heading_date_from_text("Stand vom 2026-08-11, siehe unten\n") is None


def test_should_ignore_unparsable_date():
    assert hfc.heading_date_from_text("## Stand (2026-13-45)\n") is None


# ── Owner-Auflösung ───────────────────────────────────────────────────────────


def test_should_take_owner_from_full_name_not_from_requested_path(monkeypatch):
    """GitHub folgt nach einem Transfer still einem Redirect: die Anfrage an die FALSCHE
    Org liefert 200. Der Owner muss deshalb aus `full_name` der Antwort kommen — sonst
    schreibt die Messung eine Fehlzuordnung fest (🌀 github_redirect_masks_org_hardcode)."""

    def fake(path, token, raw=False):
        if path == "/repos/achimdehnert/meiki-hub":  # Redirect-Antwort
            return {"full_name": "meiki-lra/meiki-hub", "default_branch": "main"}
        return None

    monkeypatch.setattr(hfc, "gh_api", fake)
    assert hfc.resolve_repo("meiki-hub", "t")["full_name"] == "meiki-lra/meiki-hub"


def test_should_return_none_when_repo_is_in_no_known_org(monkeypatch):
    monkeypatch.setattr(hfc, "gh_api", lambda *a, **k: None)
    assert hfc.resolve_repo("gibtsnicht", "t") is None


# ── Gate-Verdrahtung ──────────────────────────────────────────────────────────


def _gate_env(monkeypatch, listing, files):
    def fake(path, token, raw=False):
        if path.endswith("/contents/.github/workflows"):
            return listing
        for name, text in files.items():
            if path.endswith(f"/workflows/{name}"):
                return text
        return None

    monkeypatch.setattr(hfc, "gh_api", fake)


def test_should_detect_gate_wired_via_shared_ci(monkeypatch):
    """Der Gate-Workflow ist von platform nach iilgmbh/shared-ci gewandert. Eine Regex
    nur auf `platform` meldete die verdrahtete Hälfte der Flotte als „unklar"."""
    _gate_env(
        monkeypatch,
        [{"name": "handoff-banner-gate.yml"}],
        {
            "handoff-banner-gate.yml": "jobs:\n  g:\n    uses: iilgmbh/shared-ci/.github/workflows/handoff-banner-gate.yml@v1.1.1\n"
        },
    )
    assert hfc.gate_state("achimdehnert/apo-hub", "t") == "ja@v1.1.1"


def test_should_detect_gate_wired_via_platform(monkeypatch):
    _gate_env(
        monkeypatch,
        [{"name": "handover-gate.yaml"}],
        {
            "handover-gate.yaml": "uses: achimdehnert/platform/.github/workflows/handoff-banner-gate.yml@main\n"
        },
    )
    assert hfc.gate_state("achimdehnert/x", "t") == "ja@main"


def test_should_report_unklar_when_named_workflow_lacks_the_reference(monkeypatch):
    _gate_env(
        monkeypatch,
        [{"name": "handoff-something.yml"}],
        {"handoff-something.yml": "jobs:\n  x:\n    runs-on: ubuntu-latest\n"},
    )
    assert hfc.gate_state("achimdehnert/x", "t") == "unklar"


def test_should_report_nein_without_candidate_workflow(monkeypatch):
    _gate_env(monkeypatch, [{"name": "ci.yml"}], {})
    assert hfc.gate_state("achimdehnert/x", "t") == "nein"


def test_should_report_na_when_workflow_dir_unreadable(monkeypatch):
    monkeypatch.setattr(hfc, "gh_api", lambda *a, **k: None)
    assert hfc.gate_state("achimdehnert/x", "t") == "n/a"


# ── Messung + Ausgabe ─────────────────────────────────────────────────────────


def test_should_record_missing_repo_as_result_not_as_crash(monkeypatch):
    monkeypatch.setattr(hfc, "resolve_repo", lambda *a, **k: None)
    row = hfc.measure_repo("gibtsnicht", "t", with_gate=True)
    assert row["gefunden"] is False and row["handover"] is False and row["gate"] == "n/a"


def test_should_measure_repo_with_handover_and_log(monkeypatch):
    monkeypatch.setattr(
        hfc,
        "resolve_repo",
        lambda *a, **k: {
            "full_name": "achimdehnert/platform",
            "default_branch": "main",
            "gh_archived": False,
        },
    )

    def fake(path, token, raw=False):
        if path.endswith("/AGENT_HANDOVER.md"):
            return "## ⚡ Aktueller Stand (2026-08-11)\n"
        if path.endswith("/AGENT_HANDOVER_LOG.md"):
            return "### 2026-08-11 · Session\n"
        return None

    monkeypatch.setattr(hfc, "gh_api", fake)
    row = hfc.measure_repo("platform", "t", with_gate=False)
    assert (row["handover"], row["log"], row["stand"]) == (True, True, "2026-08-11")
    assert "gate" not in row  # ohne --gate keine Spalte


@pytest.mark.parametrize("with_gate", [False, True])
def test_should_render_table_identically_for_identical_input(with_gate):
    """Kriterium 1 verlangt zwei identische Läufe: die Ausgabe darf keinen Zeitstempel
    und keine unsortierte Menge enthalten."""
    rows = [
        {
            "repo": "b-hub",
            "owner": "achimdehnert",
            "gefunden": True,
            "handover": True,
            "log": False,
            "stand": "2026-08-11",
            "gate": "ja@v1.1.1",
        },
        {
            "repo": "a-hub",
            "owner": None,
            "gefunden": False,
            "handover": False,
            "log": False,
            "stand": None,
            "gate": "n/a",
        },
    ]
    assert hfc.render_table(rows, with_gate) == hfc.render_table(rows, with_gate)
    assert "nicht gefunden" in hfc.render_table(rows, with_gate)


def test_should_not_print_a_date_column_for_repo_without_handover_file():
    rows = [
        {
            "repo": "x",
            "owner": "achimdehnert",
            "gefunden": True,
            "handover": False,
            "log": False,
            "stand": None,
        }
    ]
    # ohne Datei ist "kein Datum" keine Aussage über den Stand, sondern Rauschen
    assert "kein Datum" not in hfc.render_table(rows, False)
